"""Portable local CLI for silver processing, mapping review and model preparation."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

from .model import fit_encoder, split_by_family, transform_rows, validate_candidates
from .review_batches import build_review_batches, render_summary
from .tracking import compare_ledgers


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()


def _jsonl_bytes(rows):
    return b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
                    for row in rows)


def _read_json(path):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(Path(path).read_bytes(), parse_constant=reject)


def _read_rows(path):
    return [_read_json_line(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_json_line(line):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(line, parse_constant=reject)


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def verified_silver(root):
    """Verify the published manifest before consuming any derived dataset."""
    root = Path(root).expanduser().resolve()
    manifest = _read_json(root / "manifest.json")
    if manifest.get("manifest_format_version") != "category-processing-silver-manifest-1":
        raise ValueError("Expected a category-processing silver manifest.")
    files = manifest.get("managed_files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Silver manifest has no managed file checksums.")
    required = {"quality-report.json", "profile.json", "source-mappings.json", "model-design.json",
                "product.schema.json", "pipeline.json", "review-queue.jsonl", "model-inputs.jsonl",
                "source-listings.jsonl", "processing-ledger.jsonl"}
    if required - set(files):
        raise ValueError("Silver manifest must cover every consumed contract and dataset.")
    for name, spec in files.items():
        path = root / name
        if (Path(name).is_absolute() or not _inside(path.resolve(), root) or path.is_symlink()
                or any(parent.is_symlink() for parent in path.parents if _inside(parent, root))):
            raise ValueError("Silver managed reference must stay within the dataset: " + name)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != spec.get("sha256") or len(content) != spec.get("byte_length"):
            raise ValueError("Silver managed file differs from its manifest: " + name)
    contracts = manifest.get("contract_sha256", {})
    expected_contracts = {"profile.json", "source-mappings.json", "model-design.json", "product.schema.json", "pipeline.json"}
    if set(contracts) != expected_contracts or any(files[name]["sha256"] != checksum for name, checksum in contracts.items()):
        raise ValueError("Silver contract fingerprints disagree with managed files.")
    profile = _read_json(root / "profile.json")
    if any(profile.get(name) != manifest.get(name) for name in ("category", "market", "schema_version")):
        raise ValueError("Silver profile context disagrees with its manifest.")
    return root, manifest


def _publish(output, files, source):
    requested = Path(output).expanduser().absolute()
    if requested.is_symlink():
        raise ValueError("Output directory must not be a symlink.")
    output = requested.resolve()
    if _inside(output, source) or _inside(source, output):
        raise ValueError("Derived output must be separate from the silver source.")
    for name in files:
        path = output / name
        if (not _inside(path.resolve(), output) or path.is_symlink() or path.is_dir()
                or any(parent.is_symlink() for parent in path.parents if _inside(parent, output))):
            raise ValueError("Derived output paths must stay within their output directory.")
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def summarize(silver_root, output):
    root, manifest = verified_silver(silver_root)
    profile = _read_json(root / "profile.json")
    mappings = _read_json(root / "source-mappings.json")
    context = {"category": profile["category"], "market": profile["market"],
               "schema_version": profile["schema_version"], "mapping_version": mappings["mapping_version"]}
    batches = build_review_batches(_read_rows(root / "review-queue.jsonl"), **context)
    _publish(output, {
        "mapping-review-batches.jsonl": _jsonl_bytes(batches),
        "mapping-review-summary.md": render_summary(batches, **context).encode(),
    }, root)
    return {"status": "review_packet_prepared", "dataset_version": manifest["dataset_version"],
            "batch_count": len(batches), "output": str(Path(output).resolve())}


def prepare_model(silver_root, output, validation_fraction=0.2):
    root, manifest = verified_silver(silver_root)
    quality = _read_json(root / "quality-report.json")
    if quality.get("status") != "complete_snapshot":
        raise ValueError("Model preparation requires a complete silver snapshot.")
    design = _read_json(root / "model-design.json")
    rows = validate_candidates(_read_rows(root / "model-inputs.jsonl"), design)
    split = split_by_family(rows, validation_fraction)
    fitted = fit_encoder(split["train"], design)
    matrices = []
    for partition in ("train", "validation"):
        matrix = transform_rows(split[partition], fitted)
        matrices.extend({"partition": partition, "observation_id": observation, "X": features, "y": target}
                        for observation, features, target in zip(matrix["observation_ids"], matrix["X"], matrix["y"]))
    report = {"report_format_version": "category-model-preparation-1", "status": "inputs_prepared",
              "source_dataset_version": manifest["dataset_version"],
              "schema_version": design["schema_version"], "model_design_version": design["model_design_version"],
              "target_definition": fitted["target_definition"], "split": split["metadata"],
              "columns": fitted["columns"], "dropped_terms": fitted["dropped_terms"],
              "regression_fitted": False, "release_ready": False,
              "limitations": ["No model coefficients or uncertainty estimates have been fitted.",
                              "Predictor overlap and sample sufficiency must be established before interpreting pricing insights."]}
    files = {"train.jsonl": _jsonl_bytes(split["train"]), "validation.jsonl": _jsonl_bytes(split["validation"]),
             "encoder.json": _json_bytes(fitted), "design-matrix.jsonl": _jsonl_bytes(matrices),
             "model-design.json": (root / "model-design.json").read_bytes()}
    report["managed_files"] = {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)}
                               for name, data in files.items()}
    files["preparation-report.json"] = _json_bytes(report)
    _publish(output, files, root)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    process = commands.add_parser("process", help="Build a seller-specific silver snapshot using a category profile.")
    process.add_argument("--archive-root", type=Path, required=True)
    process.add_argument("--profile", type=Path, required=True)
    process.add_argument("--output", type=Path, required=True)
    process.add_argument("--reviews", type=Path)
    for name, help_text in (("summarize", "Prepare a local mapping gap review packet."),
                            ("prepare-model", "Prepare reviewed family holdouts and a frozen predictor encoder.")):
        subparser = commands.add_parser(name, help=help_text)
        subparser.add_argument("--silver-root", type=Path, required=True)
        subparser.add_argument("--output", type=Path, required=True)
        if name == "prepare-model":
            subparser.add_argument("--validation-fraction", type=float, default=0.2)
    args = parser.parse_args(argv)
    try:
        if args.command == "process":
            from .pipeline import build_silver_dataset
            previous = []
            if (args.output / "manifest.json").exists():
                previous_root, unused_manifest = verified_silver(args.output)
                previous = _read_rows(previous_root / "processing-ledger.jsonl")
            result = build_silver_dataset(args.archive_root, args.output, args.profile, reviews=args.reviews)
            result = dict(result)
            result["processing_changes"] = compare_ledgers(_read_rows(args.output / "processing-ledger.jsonl"), previous)
            result["execution_strategy"] = "full_snapshot_rebuild"
        elif args.command == "summarize":
            result = summarize(args.silver_root, args.output)
        else:
            result = prepare_model(args.silver_root, args.output, args.validation_fraction)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False))
        return 1 if result.get("status") == "partial" else 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
