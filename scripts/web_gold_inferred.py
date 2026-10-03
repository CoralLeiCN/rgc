"""Authenticate the published Gold inferred collection for the web projection."""

import json
import re
from pathlib import Path

from chocolate_gold import (
    checked_path,
    checksum,
    read_managed,
    row_bytes,
    rows,
    verified_gold,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "apps/web/collection-dataset.json"


def validate_reference(reference):
    if (reference.get("formatVersion") != 1
            or reference.get("repository") != "CoralLeiCN/rgc-collections"
            or not re.fullmatch(r"[a-f0-9]{40}", reference.get("revision", ""))
            or not re.fullmatch(r"gold-inferred-[a-f0-9]{24}", reference.get("datasetVersion", ""))
            or reference.get("snapshotPrefix") != "gold-inferred/chocolate/uk/" + reference["datasetVersion"]
            or not re.fullmatch(r"[a-f0-9]{64}", reference.get("manifestSha256", ""))):
        raise ValueError("Invalid Gold inferred dataset reference")


def sync(cache_root, download, read_json):
    reference = read_json(REFERENCE)
    validate_reference(reference)
    root = (cache_root / reference["revision"] / reference["datasetVersion"]).resolve()
    base = (f"https://huggingface.co/datasets/{reference['repository']}/resolve/"
            f"{reference['revision']}/{reference['snapshotPrefix']}")
    download(base + "/manifest.json", root / "manifest.json")
    manifest = read_json(root / "manifest.json")
    if checksum((root / "manifest.json").read_bytes()) != reference["manifestSha256"]:
        raise ValueError("Gold inferred manifest does not match the pinned reference")
    for name, expected in manifest["managed_files"].items():
        destination = checked_path(root, name, "Gold inferred")
        if (destination.exists() and destination.stat().st_size == expected["byte_length"]
                and checksum(destination.read_bytes()) == expected["sha256"]):
            continue
        download(base + "/" + name, destination)
    (root / "dataset-reference.json").write_bytes(REFERENCE.read_bytes())
    return root


def load(root, read_json):
    """Return complete product records and verified training/provenance inputs."""
    import pyarrow.parquet as pq

    root = root.resolve()
    reference = read_json(root / "dataset-reference.json")
    validate_reference(reference)
    # Offline rebuilds must use the committed immutable pin as well.
    if reference != read_json(REFERENCE):
        raise ValueError("Gold inferred cache differs from the app's dataset reference")
    manifest = read_json(root / "manifest.json")
    if (checksum((root / "manifest.json").read_bytes()) != reference["manifestSha256"]
            or manifest.get("manifest_format_version") != "chocolate-gold-inferred-manifest-1"
            or manifest.get("dataset_version") != reference["datasetVersion"]):
        raise ValueError("Gold inferred manifest disagrees with the pinned reference")
    files = read_managed(root, manifest["managed_files"], "Gold inferred")
    source, source_bytes, inputs = verified_gold(root / "training")
    if (files["inputs/silver-manifest.json"] != source_bytes
            or checksum(source_bytes) != manifest["source_silver_manifest_sha256"]
            or source["dataset_version"] != manifest["source_silver_dataset_version"]
            or source["source_dataset_version"] != manifest["source_dataset_version"]):
        raise ValueError("Gold inferred source provenance disagrees with its training data")
    training = read_json(root / "training/manifest.json")
    if (training["dataset_version"] != manifest["training_gold_dataset_version"]
            or checksum(files["training/manifest.json"]) != manifest["training_gold_manifest_sha256"]):
        raise ValueError("Gold inferred training identity mismatch")
    products = [json.loads(record) for record in pq.read_table(root / "products.parquet", columns=["record_json"])["record_json"].to_pylist()]
    if (len(products) != manifest["product_count"]
            or checksum(row_bytes(products)) != manifest["source_products_logical_sha256"]):
        raise ValueError("Gold inferred product logical checksum mismatch")
    report = read_json(root / "report.json")
    provenance = read_json(root / "inference/provenance.json")
    decisions = rows(files["inference/accepted-decisions.jsonl"])
    if (report.get("dataset_version") != manifest["dataset_version"]
            or report.get("source_silver_dataset_version") != source["dataset_version"]
            or report.get("record_json_is_authoritative") is not True
            or report.get("eligibility_preserved") is not True
            or report["counts"]["products"] != len(products)
            or len(decisions) != manifest["accepted_inference_decision_count"]
            or len(decisions) != report["counts"]["accepted_inference_decisions"]
            or checksum(files["inference/accepted-decisions.jsonl"]) != manifest["accepted_decisions_sha256"]
            or checksum(files["inference/provenance.json"]) != manifest["provenance_sha256"]
            or provenance["source_silver_manifest_sha256"] != checksum(source_bytes)):
        raise ValueError("Gold inferred report or inference provenance mismatch")
    return reference, manifest, source, inputs, products, report, provenance
