"""Build one evidence-backed chocolate silver layer from the preserved archive."""

import hashlib
import json
from itertools import islice
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from chocolate_cleanup.deduplication import (
    build_deduplicated_dataset,
    digest,
    inside,
    json_bytes,
)
from chocolate_standardization.pipeline import (
    build_standardized_dataset,
    read_json,
    sha256,
)
from chocolate_tables import get_table_backend
from dataset_contracts import resolve_contract_root

ROOT = Path(__file__).resolve().parents[1]
LAYER_VERSION = "chocolate-silver-1"
IMPLEMENTATION_FILES = (
    "scripts/chocolate_silver.py", "scripts/build_chocolate_silver.py", "scripts/chocolate_tables.py",
    "scripts/chocolate_cleanup/deduplication.py",
    "scripts/chocolate_cleanup/sources.py", "scripts/chocolate_cleanup/adapters.py",
    "scripts/chocolate_cleanup/core.py", "scripts/chocolate_standardization/pipeline.py",
    "scripts/chocolate_standardization/values.py", "scripts/chocolate_model.py",
    "scripts/chocolate_standardization/identity.py",
    "scripts/dataset_contracts.py", "plugins/category-processing/category_processing/dataset_contracts.py",
    "schemas/chocolate/dataset-contract.json",
)


def implementation_hashes():
    return {name: sha256(ROOT / name) for name in IMPLEMENTATION_FILES}


def inventory(root):
    return {path.relative_to(root).as_posix(): (path.parent / ".import.lock").exists()
            for path in sorted((root / "chocolate/uk/products").glob("*/product.json"))}


def confirm_source(root, initial_inventory, inputs):
    """Detect imports or source-index/history changes across both internal steps."""
    if inventory(root) != initial_inventory:
        raise RuntimeError("Raw archive inventory or import locks changed during the silver build.")
    for item in inputs:
        path = root / item["path"]
        if not inside(path.resolve(), root) or path.is_symlink() or sha256(path) != item["sha256"]:
            raise RuntimeError("Raw archive changed during the silver build: " + item["path"])


def table_bytes(path, version, source_version, *, table_backend="stdlib"):
    """Rewrite derived row envelopes; leave nested original evidence untouched."""
    tables = get_table_backend(table_backend)
    lines = []
    with path.open(encoding="utf-8") as stream:
        rows = (json.loads(line) for line in stream)
        while batch := list(islice(rows, 1000)):
            for row in tables.envelopes(batch, version, source_version, LAYER_VERSION):
                lines.append((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode())
    return b"".join(lines)


def build_silver_dataset(archive_root, output, reviews=None, schema_root=None, offline=False,
                         family_mappings=None, *, table_backend="pandas"):
    """Deduplicate seller listings, standardize attributes, and gate model inputs.

    Intermediate tables are temporary implementation details. Published evidence
    resolves within source-listings.jsonl and the original raw artifact archive.
    """
    source = Path(archive_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if inside(output, source) or inside(source, output):
        raise ValueError("Silver output must be separate from the raw archive (no overlap).")
    tables = get_table_backend(table_backend)
    runtime = tables.runtime()
    schema_root = resolve_contract_root(schema_root, offline=offline)
    initial_inventory = inventory(source)
    implementation = implementation_hashes()
    with TemporaryDirectory(prefix="chocolate-silver-") as temporary:
        scratch = Path(temporary)
        deduplicated, standardized = scratch / "deduplicated", scratch / "standardized"
        dedup_report = build_deduplicated_dataset(source, deduplicated, table_backend=tables)
        report = build_standardized_dataset(deduplicated, standardized, reviews=reviews,
                                            schema_root=schema_root, offline=offline,
                                            family_mappings=family_mappings, table_backend=tables)
        dedup_manifest = read_json(deduplicated / "manifest.json")
        standard_manifest = read_json(standardized / "manifest.json")
        source_version = "raw-snapshot-" + digest({
            "archive_format": dedup_manifest["source_archive_format"], "inputs": dedup_manifest["inputs"],
            "inventory": initial_inventory, "archive_errors": dedup_report["archive_errors"],
            "unsupported_records": dedup_report["unsupported_records"],
        })[:24]
        version = "silver-" + digest({"layer_version": LAYER_VERSION, "source_dataset_version": source_version,
                                      "deduplication_step": dedup_manifest["dataset_version"],
                                      "standardization_step": standard_manifest["dataset_version"],
                                      "implementation": implementation, "processing_runtime": runtime})[:24]
        report.update(report_format_version="chocolate-silver-report-1", layer_version=LAYER_VERSION,
                      dataset_version=version, source_dataset_version=source_version, processing_runtime=runtime,
                      status="partial" if dedup_report["status"] != "complete_snapshot" or report["counts"]["extraction_errors"] else "complete_snapshot",
                      deduplication=dedup_report["deduplication"],
                      archive_errors=dedup_report["archive_errors"], unsupported_records=dedup_report["unsupported_records"])
        report["counts"].update({name: dedup_report["counts"][name] for name in
                                 ("product_folders", "accepted_raw_listing_folders", "captures", "duplicate_source_listings_removed", "archive_errors", "unsupported_records")})
        report["limitations"].extend(dedup_report["limitations"][-2:])
        files = {"quality-report.json": json_bytes(report)}
        for name in standard_manifest["managed_files"]:
            if name == "quality-report.json":
                continue
            path = standardized / name
            files[name] = table_bytes(path, version, source_version, table_backend=tables) if name.endswith(".jsonl") else path.read_bytes()
        for name in standard_manifest["contract_sha256"]:
            files[name] = (Path(schema_root).resolve() / name).read_bytes()
        files["source-listings.jsonl"] = table_bytes(deduplicated / "products.jsonl", version, source_version, table_backend=tables)
        files["listing-aliases.jsonl"] = table_bytes(deduplicated / "listing-aliases.jsonl", version, source_version, table_backend=tables)
        for role in ("brand", "retail", "unknown"):
            files[role + "/source-listings.jsonl"] = table_bytes(deduplicated / role / "products.jsonl", version, source_version, table_backend=tables)
        manifest = {
            "manifest_format_version": "chocolate-silver-manifest-1", "layer_version": LAYER_VERSION,
            "schema_version": standard_manifest["schema_version"], "dataset_version": version,
            "source_layer": "raw_collections", "source_dataset_version": source_version,
            "source_archive_format": dedup_manifest["source_archive_format"],
            "input_reference_base": "supplied raw collections root", "inputs": dedup_manifest["inputs"],
            "input_inventory": initial_inventory,
            "processing_steps": {
                "deduplication": {"fingerprint": dedup_manifest["dataset_version"], "rule": dedup_manifest["deduplication_rule"]},
                "standardization": {"fingerprint": standard_manifest["dataset_version"]},
            },
            "contract_sha256": standard_manifest["contract_sha256"], "implementation_sha256": implementation,
            "processing_runtime": runtime,
            "reviews": standard_manifest["reviews"],
            "identity_mapping_format_version": standard_manifest["identity_mapping_format_version"],
            "identity_taxonomy_version": standard_manifest["identity_taxonomy_version"],
            "identity_mappings_sha256": standard_manifest["identity_mappings_sha256"],
            "evidence_reference_base": "capture IDs and JSON pointers resolve in this silver dataset's source-listings.jsonl; original artifact and history paths resolve against the supplied raw collections root",
            "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)} for name, data in files.items()},
        }
        files["manifest.json"] = json_bytes(manifest)
        # Check every path before writing, so a bad destination cannot cause a
        # partial overwrite or follow a link outside the requested output.
        for name in files:
            target = output / name
            temporary_path = target.with_name("." + target.name + ".tmp")
            if (not inside(target.resolve(), output) or not inside(temporary_path.resolve(), output)
                    or target.is_symlink() or temporary_path.is_symlink() or target.is_dir() or temporary_path.is_dir()
                    or any(parent.is_symlink() for parent in target.parents if inside(parent, output))):
                raise ValueError("Silver output paths must stay within the output directory.")
        confirm_source(source, initial_inventory, dedup_manifest["inputs"])
        if implementation_hashes() != implementation or tables.runtime() != runtime:
            raise RuntimeError("Silver implementation changed during the build.")
        resolve_contract_root(schema_root, offline=offline)
        for name, checksum in standard_manifest["contract_sha256"].items():
            if sha256(Path(schema_root).resolve() / name) != checksum:
                raise RuntimeError("Category contracts changed during the silver build.")
        output.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = None
            try:
                with NamedTemporaryFile(prefix="." + target.name + ".", suffix=".tmp", dir=target.parent, delete=False) as stream:
                    temporary_path = Path(stream.name)
                    stream.write(data)
                temporary_path.replace(target)
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()
        return report
