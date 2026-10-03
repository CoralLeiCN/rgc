"""Preserve raw captures in a separate, seller-specific deduplicated snapshot."""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from chocolate_tables import get_table_backend

from .sources import SOURCES

ARCHIVE_VERSION = "category-research-raw-1"
LAYER_VERSION = "chocolate-deduplicated-raw-1"
RULE = "Exact source key, source URL hostname, source product ID and nullable source variant ID; never merge selling sources."


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def source_identity(raw):
    """Return a precise source-local identity, or None when incomplete."""
    identity = raw.get("identity") if isinstance(raw.get("identity"), dict) else {}
    source, pid, vid = raw.get("source_key"), identity.get("source_product_id"), identity.get("source_variant_id")
    if not isinstance(source, str) or not source.strip():
        return None
    if isinstance(pid, bool) or not isinstance(pid, (str, int)) or not str(pid).strip():
        return None
    if vid is not None and (isinstance(vid, bool) or not isinstance(vid, (str, int))):
        return None
    try:
        hostname = urlsplit(raw.get("source_url") or "").hostname
    except (ValueError, TypeError, AttributeError):
        return None
    if not hostname:
        return None
    return source, hostname, str(pid), None if vid is None else str(vid)


def deduplicate_listings(listings, captures, latest, *, table_backend="stdlib"):
    """Group exact source identities, keeping every original capture unchanged.

    The supplied index dictionaries are updated in place. Canonical listing IDs
    are the first original folder IDs in lexical order. Returned aliases retain
    all original folder IDs, and original_latest retains each folder's pointer.
    """
    tables = get_table_backend(table_backend)
    identities = [(listing, source_identity(captures[listing][latest[listing]]["raw_record"]))
                  for listing in listings]
    original_latest, aliases, duplicate_groups = dict(latest), {}, []
    for ids in tables.identity_groups(identities):
        canonical = ids[0]
        aliases[canonical] = ids
        if len(ids) == 1:
            continue
        merged = {}
        for original in ids:
            for cid, capture in captures[original].items():
                if cid in merged and merged[cid] != capture:
                    raise ValueError("Conflicting capture ID across source listing aliases: " + cid)
                merged[cid] = capture
        captures[canonical] = merged
        latest[canonical] = max(merged, key=lambda cid: (merged[cid].get("recorded_at", ""), cid))
        for original in ids[1:]:
            del listings[original]
        duplicate_groups.append({"listing_id": canonical, "source_listing_ids": ids,
                                 "rule": "same_source_hostname_product_and_variant_identifiers"})
    return aliases, duplicate_groups, original_latest


def load_raw_archive(archive_root):
    """Read plugin indexes and confirm their original immutable histories."""
    root = Path(archive_root).expanduser().resolve()
    products = root / "chocolate" / "uk" / "products"
    if not products.is_dir():
        raise ValueError("Expected chocolate/uk/products under --archive-root.")
    inventory = sorted(products.glob("*/product.json"))
    result = {"root": root, "product_root": products, "inventory": inventory,
              "listings": {}, "captures": {}, "latest": {}, "snapshots": {},
              "inputs": [], "errors": [], "unsupported": [], "product_folders": len(inventory)}

    def read(path):
        if not inside(path.resolve(), root) or path.is_symlink():
            raise ValueError("Archive reference escapes root or uses a symlink: " + str(path))
        data = path.read_bytes()
        def reject(value):
            raise ValueError("Non-finite JSON value: " + value)
        checksum = hashlib.sha256(data).hexdigest()
        result["snapshots"][path] = checksum
        result["inputs"].append({"path": path.relative_to(root).as_posix(), "sha256": checksum})
        return json.loads(data, parse_constant=reject)

    for path in inventory:
        listing = path.parent.name
        if (path.parent / ".import.lock").exists():
            result["errors"].append({"listing_id": listing, "code": "import_in_progress"})
            continue
        try:
            document = read(path)
            if not isinstance(document, dict):
                raise ValueError("Product index must be an object.")
            if document.get("archive_format_version") != ARCHIVE_VERSION:
                result["unsupported"].append({"listing_id": listing, "archive_format_version": document.get("archive_format_version"),
                                              "reason": "unsupported_or_legacy_archive_not_interpreted"})
                continue
            if document.get("product_id") != listing or document.get("category") != "chocolate" or document.get("market") != "uk":
                raise ValueError("Product envelope does not match its source listing or study.")
            values = document.get("captures")
            if not isinstance(values, list) or not values:
                raise ValueError("Product has no captures.")
            lookup = {}
            for capture in values:
                if not isinstance(capture, dict) or not isinstance(capture.get("raw_record"), dict):
                    raise ValueError("Capture lacks an original raw record.")
                cid = capture.get("capture_id")
                if not isinstance(cid, str) or not cid or cid in lookup:
                    raise ValueError("Capture ID is missing or repeated.")
                if capture["raw_record"].get("product_id") != listing:
                    raise ValueError("Capture identity does not match source listing.")
                history = capture.get("history_path")
                if not isinstance(history, str) or Path(history).is_absolute():
                    raise ValueError("Capture lacks a relative history reference.")
                if read(root / history) != capture:
                    raise ValueError("Immutable history differs from indexed capture.")
                lookup[cid] = capture
            identities = {(source_identity(capture["raw_record"]), digest(capture["raw_record"].get("source_key")))
                          for capture in lookup.values()}
            if len(identities) > 1:
                raise ValueError("Seller-listing identity changes across captures; separate seller listings are required.")
            if document.get("latest_capture_id") not in lookup:
                raise ValueError("Latest capture ID does not resolve.")
            if (path.parent / ".import.lock").exists():
                raise ValueError("Product import is in progress.")
            result["listings"][listing] = document
            result["captures"][listing] = lookup
            result["latest"][listing] = document["latest_capture_id"]
        except (OSError, ValueError, TypeError, KeyError) as error:
            result["errors"].append({"listing_id": listing, "code": "invalid_archive_record", "reason": str(error)})
    result["inputs"] = sorted({item["path"]: item for item in result["inputs"]}.values(), key=lambda item: item["path"])
    return result


def confirm_raw_snapshot(archive):
    if sorted(archive["product_root"].glob("*/product.json")) != archive["inventory"]:
        raise RuntimeError("Raw archive listing inventory changed during the build; retry after imports finish.")
    for path, checksum in archive["snapshots"].items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise RuntimeError("Raw archive changed during the build; retry after imports finish.")
    for path in archive["inventory"]:
        if (path.parent / ".import.lock").exists() and path.parent.name in archive["latest"]:
            raise RuntimeError("Raw import started during the build; retry after imports finish.")


def build_deduplicated_dataset(archive_root, output, *, table_backend="stdlib"):
    root = Path(archive_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if inside(output, root) or inside(root, output):
        raise ValueError("Deduplicated output must be separate from the raw archive (no overlap).")
    tables = get_table_backend(table_backend)
    runtime = tables.runtime()
    implementation_paths = (Path(__file__), Path(__file__).with_name("sources.py"),
                            Path(__file__).resolve().parents[1] / "chocolate_tables.py")
    implementation = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in implementation_paths}
    archive = load_raw_archive(root)
    listings, captures, latest = archive["listings"], archive["captures"], archive["latest"]
    aliases, groups, original_latest = deduplicate_listings(listings, captures, latest, table_backend=tables)
    rows, alias_rows = [], []
    for listing in sorted(listings):
        current = captures[listing][latest[listing]]["raw_record"]
        identity = current.get("identity") if isinstance(current.get("identity"), dict) else {}
        source = current.get("source_key") if isinstance(current.get("source_key"), str) else "unknown"
        role, retailer = SOURCES.get(source, ("unknown", source))
        row = {"listing_id": listing, "source_listing_ids": aliases[listing],
               "source_key": source, "source_role": role, "brand": identity.get("brand"),
               "retailer": retailer, "name": identity.get("name"),
               "source_product_id": identity.get("source_product_id"),
               "source_variant_id": identity.get("source_variant_id"),
               "latest_capture_id": latest[listing],
               "captures": [captures[listing][cid] for cid in sorted(captures[listing])],
               "layer_version": LAYER_VERSION}
        rows.append(row)
        alias_rows.extend({"listing_id": listing, "source_listing_id": alias,
                           "source_key": source, "source_role": role,
                           "original_latest_capture_id": original_latest[alias]}
                          for alias in aliases[listing])
    confirm_raw_snapshot(archive)
    if implementation != {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in implementation_paths} or tables.runtime() != runtime:
        raise RuntimeError("Deduplication implementation changed during the build; retry after edits finish.")
    version = "deduplicated-" + digest({"layer_version": LAYER_VERSION, "inputs": archive["inputs"],
                                        "implementation": implementation, "processing_runtime": runtime, "rule": RULE,
                                        "inventory": [path.relative_to(root).as_posix() for path in archive["inventory"]],
                                        "archive_errors": archive["errors"],
                                        "unsupported_records": archive["unsupported"]})[:24]
    for row in rows + alias_rows:
        row["dataset_version"] = version
    counts = {"product_folders": archive["product_folders"], "source_listings": len(rows),
              "accepted_raw_listing_folders": sum(len(ids) for ids in aliases.values()),
              "captures": sum(len(row["captures"]) for row in rows),
              "duplicate_source_listings_removed": sum(len(ids) - 1 for ids in aliases.values()),
              "unsupported_records": len(archive["unsupported"]), "archive_errors": len(archive["errors"])}
    report = {"report_format_version": "chocolate-raw-deduplication-report-1", "layer_version": LAYER_VERSION,
              "dataset_version": version, "counts": counts,
              "processing_runtime": runtime,
              "source_role_counts": tables.counts(rows, "source_role"),
              "deduplication": {"scope": "within_selling_source_only", "rule": RULE,
                                "duplicate_groups": groups, "cross_source_merges": 0},
              "unsupported_records": archive["unsupported"], "archive_errors": archive["errors"],
              "status": "partial" if archive["errors"] or archive["unsupported"] else "complete_snapshot",
              "analytical_readiness": "not_evaluated_raw_source_values",
              "limitations": ["Raw source records are preserved without feature extraction or price normalization.",
                              "All capture and price history is retained; repeated capture observations are not discarded.",
                              "Counts describe seller-specific listings, not market-wide distinct formulations.",
                              "Original artifacts and immutable histories remain in the supplied raw collections root.",
                              "History consistency is checked, but original artifact bytes are not rehashed."]}
    files = {"quality-report.json": json_bytes(report)}
    for name, values in (("products.jsonl", rows), ("listing-aliases.jsonl", alias_rows)):
        files[name] = b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in values)
    for role, partition in tables.partitions(rows).items():
        files[role + "/products.jsonl"] = b"".join(
            (json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
            for row in partition)
    manifest = {"manifest_format_version": "chocolate-raw-deduplication-manifest-1", "layer_version": LAYER_VERSION,
                "dataset_version": version, "source_layer": "raw_collections", "source_archive_format": ARCHIVE_VERSION,
                "input_reference_base": "supplied collections root", "inputs": archive["inputs"],
                "implementation_sha256": implementation, "processing_runtime": runtime, "deduplication_rule": RULE,
                "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    output.mkdir(parents=True, exist_ok=True)
    for name in files:
        target = output / name
        temporary = target.with_name("." + target.name + ".tmp")
        if not inside(target.resolve(), output) or not inside(temporary.resolve(), output) or temporary.is_symlink():
            raise ValueError("Deduplicated output paths must not escape the output directory.")
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name("." + target.name + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(target)
    return report
