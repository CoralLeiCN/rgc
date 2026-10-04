#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Export category-independent text evidence for verified local storage."""

import argparse
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_VERSION = "rgc-text-evidence-1"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".html", ".htm", ".csv", ".tsv", ".xml"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg", ".bmp", ".tif", ".tiff", ".ico", ".image"}
SECTIONS = {"products", "catalogs", "discovery", "runs"}
ROOT_FILES = {"README.md", "coverage.json", "archive-verification.json"}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_image(header):
    return (header.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM", b"II*\x00", b"MM\x00*"))
            or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
            or (header[4:8] == b"ftyp" and header[8:12] in (b"avif", b"avis", b"heic", b"heix")))


def exclusion_reason(path, relative):
    """Allow evidence locations and text formats; never infer inclusion from size."""
    parts = relative.parts
    if path.is_symlink():
        return "symlink"
    if any(part.startswith(".") or part == "__pycache__" for part in parts):
        return "runtime_or_hidden_file"
    if parts[0] == "transfers":
        return "transfer_cache"
    if "images" in parts or path.suffix.lower() in IMAGE_SUFFIXES:
        return "image_bytes"
    if len(parts) == 1:
        if path.name not in ROOT_FILES:
            return "outside_evidence_allowlist"
    elif parts[0] not in SECTIONS:
        return "outside_evidence_allowlist"
    elif parts[0] == "products" and not (
            len(parts) == 3 and parts[2] == "product.json"
            or len(parts) >= 4 and parts[2] in {"sources", "history"}
            or len(parts) == 4 and parts[3] == "product.json"
            or len(parts) >= 5 and parts[3] in {"sources", "history"}):
        return "outside_evidence_allowlist"
    compressed = path.suffix.lower() == ".gz"
    if compressed and path.with_suffix("").suffix.lower() not in TEXT_SUFFIXES:
        return "unsupported_compressed_format"
    if path.suffix.lower() not in TEXT_SUFFIXES | {".gz", ".body", ".response"}:
        return "non_text_or_execution_file"
    # Check every byte, including disguised response bodies. Preserve accepted
    # bytes unchanged; decompression here is validation only.
    opener = gzip.open if compressed else open
    with opener(path, "rb") as stream:
        header = stream.read(512)
        if is_image(header) or b"\x00" in header:
            return "binary_content"
        stream.seek(0)
        import codecs
        decoder = codecs.getincrementaldecoder("utf-8")()
        try:
            while chunk := stream.read(1024 * 1024):
                if b"\x00" in chunk:
                    return "binary_content"
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            return "non_utf8_content"
    return None


def stable_bytes(path):
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"Source changed during export: {path}")
    return data


def add_tar_bytes(archive, name, data):
    entry = tarfile.TarInfo(name)
    entry.size = len(data)
    entry.mode = 0o644
    entry.mtime = 0
    archive.addfile(entry, io.BytesIO(data))


def product_row(document, relative, category, market):
    captures = document.get("captures", [])
    latest_id = document.get("latest_capture_id")
    latest = next((c for c in captures if c.get("capture_id") == latest_id), captures[-1] if captures else {})
    identity = document.get("identity", document.get("identity_hints", {}))
    return {
        "category": category, "market": market,
        "product_id": document.get("product_id", relative.parent.name),
        "name": identity.get("name"), "brand": identity.get("brand"),
        "source_url": latest.get("raw_record", {}).get("source_url"),
        "capture_count": len(captures), "latest_capture_id": latest.get("capture_id"),
        "record_path": relative.as_posix(),
        "identity_json": json.dumps(identity, ensure_ascii=False, sort_keys=True),
        "latest_information_json": json.dumps(latest.get("information"), ensure_ascii=False, sort_keys=True),
        "image_files_included": False,
    }


def build_export(collections_root, output):
    root = Path(collections_root).resolve()
    output = Path(output).expanduser().absolute()
    if output.is_symlink() or root == output.resolve() or root in output.resolve().parents or output.resolve() in root.parents:
        raise ValueError("Export output must be separate from the raw collections.")
    output = output.resolve()
    studies = sorted(p for p in root.glob("*/*") if p.is_dir() and (p / "products").is_dir())
    if not studies:
        raise ValueError("No category/market studies with product folders were found.")
    if any(p.is_symlink() or p.parent.is_symlink() for p in studies):
        raise ValueError("Symlinked category/market folders are not supported.")
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    rows = []
    managed_files = ["README.md", "products.jsonl", "export-manifest.json"]
    with tempfile.TemporaryDirectory(prefix="rgc-export-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for study in studies:
            category, market = study.relative_to(root).parts
            bundle = f"evidence/{category}/{market}.tar.gz"
            target = staging / bundle
            target.parent.mkdir(parents=True, exist_ok=True)
            included = []
            omitted = []
            with target.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w|") as archive:
                for path in sorted(study.rglob("*")):
                    if path.is_dir() and not path.is_symlink():
                        continue
                    relative = path.relative_to(study)
                    reason = exclusion_reason(path, relative)
                    collection_path = path.relative_to(root).as_posix()
                    if reason:
                        omitted.append({"path": collection_path, "reason": reason,
                                        "byte_length": path.lstat().st_size})
                        continue
                    data = stable_bytes(path)
                    add_tar_bytes(archive, collection_path, data)
                    included.append({"path": collection_path, "byte_length": len(data),
                                     "sha256": hashlib.sha256(data).hexdigest()})
                    if path.name == "product.json" and relative.parts[0] == "products":
                        row = product_row(json.loads(data), path.relative_to(root), category, market)
                        row["evidence_bundle"] = bundle
                        rows.append(row)
                manifest = {"policy_version": POLICY_VERSION, "category": category, "market": market,
                            "reference_base": "collections root after extracting bundles",
                            "image_files_included": False, "included_files": included, "omitted_files": omitted}
                add_tar_bytes(archive, "export-manifest.json", json_bytes(manifest))
            summaries.append({"category": category, "market": market, "bundle": bundle,
                              "included_files": len(included), "included_bytes": sum(i["byte_length"] for i in included),
                              "omitted_files": len(omitted), "omitted_bytes": sum(i["byte_length"] for i in omitted),
                              "omissions_by_reason": dict(Counter(i["reason"] for i in omitted)),
                              "bundle_bytes": target.stat().st_size,
                              "bundle_sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
            managed_files.append(bundle)
        (staging / "products.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
        manifest = {"policy_version": POLICY_VERSION, "image_files_included": False,
                    "product_rows": len(rows), "studies": summaries, "managed_files": managed_files}
        (staging / "export-manifest.json").write_bytes(json_bytes(manifest))
        lines = ["---", "pretty_name: RGC product collection evidence", "tags:", "- product-research", "- pricing", "- provenance", "configs:", "- config_name: default", "  data_files:", "  - split: train", "    path: products.jsonl", "---", "", "# RGC product collection evidence", "", f"Export policy: `{POLICY_VERSION}`. Image files and HTTP transfer caches are omitted.", "", "## Contents", "", f"`products.jsonl` indexes {len(rows):,} source product/variant records across {len(studies)} category/market studies.", "The split name `train` is a loader convention, not a reviewed modeling split.", "Source-specific identity and latest information are JSON strings to preserve arbitrary fields without forcing one category schema.", "Unknown fields remain unknown. Legacy records can have no latest information in this index; their complete records remain in the evidence bundles.", "", "Each `evidence/<category>/<market>.tar.gz` bundle contains original product JSON, histories, text/HTML/JSON source evidence, catalogues, discovery evidence, run inputs/reports, and available coverage/integrity reports.", "Files inside the bundles retain their exact original bytes and languages. No price normalization, identity deduplication, or ingredient inference is applied.", "", "## References and deliberate omissions", "", "Extract bundles to a common directory; original archive-relative paths resolve from that collections root.", "Each bundle's `export-manifest.json` inventories included files with SHA-256 checksums and omitted paths with reasons.", "Image URLs, captions, original checksums, retrieval metadata, and original paths remain in the raw records; referenced image/cache files are deliberately absent.", "Original host-local discovery paths are historical provenance, not downloadable links. Source HTML may link to external images; image payloads are not bundled.", "Raw reports describe the original collection, including local images; their integrity results are not a verification of this filtered export.", "", "## Coverage and reuse", "", "A row represents a source listing/variant, not necessarily a distinct physical product. Ingredient, nutrition, and source coverage can be incomplete.", "Read each study's original README, coverage report, source failures, and capture limitations before analysis.", "Source text and product metadata remain attributed to their publishers. This export does not grant a new license over third-party evidence.", "", "## Studies", "", "| Category | Market | Included evidence bytes | Bundle bytes |", "| --- | --- | ---: | ---: |"]
        lines.extend(f"| {s['category']} | {s['market']} | {s['included_bytes']:,} | {s['bundle_bytes']:,} |" for s in summaries)
        lines.extend(["", "## Storage", "", "Raw evidence exports remain local. Uploading them to Hugging Face is disabled."])
        (staging / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Replace only files produced by this export, preserving unrelated output files.
        for name in managed_files:
            destination = output / name
            if destination.is_symlink() or any(p.is_symlink() for p in destination.parents if p != output and output in p.parents):
                raise ValueError("Export destinations must not contain symlinks.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / name, destination)
    return manifest


def verify_export(output, manifest):
    """Verify all local export evidence bytes against the bundle inventories."""
    output = Path(output)
    for study in manifest["studies"]:
        bundle = output / study["bundle"]
        if hashlib.sha256(bundle.read_bytes()).hexdigest() != study["bundle_sha256"]:
            raise ValueError(f"Evidence bundle checksum mismatch: {bundle}")
        observed = {}
        inventory = None
        with tarfile.open(bundle, "r|gz") as archive:
            for entry in archive:
                if not entry.isfile() or Path(entry.name).is_absolute() or ".." in Path(entry.name).parts:
                    raise ValueError(f"Unsafe evidence bundle member: {entry.name}")
                body = archive.extractfile(entry).read()
                if entry.name == "export-manifest.json":
                    inventory = json.loads(body)
                else:
                    if entry.name in observed:
                        raise ValueError(f"Duplicate evidence bundle member: {entry.name}")
                    observed[entry.name] = (len(body), hashlib.sha256(body).hexdigest())
        if inventory is None or inventory.get("policy_version") != POLICY_VERSION:
            raise ValueError(f"Missing or incompatible bundle inventory: {bundle}")
        expected = {i["path"]: (i["byte_length"], i["sha256"]) for i in inventory["included_files"]}
        if observed != expected or any(i["path"] in observed for i in inventory["omitted_files"]):
            raise ValueError(f"Evidence inventory mismatch: {bundle}")
    # JSON strings can contain Unicode paragraph/line separators. Only actual
    # newline-delimited records separate JSONL rows; str.splitlines is too broad.
    with (output / "products.jsonl").open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    if len(rows) != manifest["product_rows"] or any(row["image_files_included"] for row in rows):
        raise ValueError("Product index does not match the export manifest.")


def upload_export(output, repo_id, manifest):
    """Reject the former upload API before any local or remote side effect."""
    raise ValueError("Raw collection evidence must remain local; uploading it is disabled.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collections-root", type=Path, default=PROJECT_ROOT / "data/collections")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/huggingface-export")
    parser.add_argument("--repo-id", help="Retired upload option; raw evidence must remain local.")
    parser.add_argument("--upload", action="store_true", help="Retired option; raw evidence uploads are disabled.")
    args = parser.parse_args(argv)
    if args.upload or args.repo_id is not None:
        parser.error("Raw collection evidence must remain local; uploading it is disabled.")
    manifest = build_export(args.collections_root, args.output)
    verify_export(args.output, manifest)
    report = {"output": str(args.output), **manifest,
              "export_bytes": sum((args.output / name).stat().st_size for name in manifest["managed_files"])}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
