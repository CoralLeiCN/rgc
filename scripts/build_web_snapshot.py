#!/usr/bin/env python3
"""Download a pinned public silver snapshot and build the private web snapshot.

Raw files remain under ignored data/. Vercel receives an explicitly derived
projection with source statuses, review gates and evidence references preserved.
No missing attributes are inferred and no pricing model is fitted.
"""
import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from chocolate_standardization.values import (
    validate_attribute_contract,
    validate_product,
)

ROOT = Path(__file__).resolve().parents[1]
REPO = "CoralLeiCN/rgc-collections"
FILES = ("products.jsonl", "prices.jsonl", "training-candidates.jsonl", "model-inputs.jsonl",
         "quality-report.json", "product.schema.json", "profile.json", "model-design.json",
         "source-mappings.json", "listing-aliases.jsonl")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def reject_constant(value):
        raise ValueError("Non-finite JSON value: " + value)

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with urlopen(Request(url, headers={"User-Agent": "rgc-web-snapshot/1"}), timeout=90) as source, temporary.open("wb") as target:
            while block := source.read(1024 * 1024):
                target.write(block)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def sync(cache_root):
    # Resolve main once, then pin every download to the immutable repository SHA.
    with tempfile.TemporaryDirectory(prefix="rgc-sync-") as temporary:
        metadata_path = Path(temporary) / "repo-metadata.json"
        download(f"https://huggingface.co/api/datasets/{REPO}", metadata_path)
        metadata = read_json(metadata_path)
        revision = metadata["sha"]
        if not re.fullmatch(r"[a-f0-9]{40}", revision):
            raise ValueError("Invalid Hugging Face revision")
        root = cache_root / revision
        root.mkdir(parents=True, exist_ok=True)
        (root / "repo-metadata.json").write_bytes(metadata_path.read_bytes())
    base = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}"
    download(f"{base}/silver/chocolate/uk/latest.json", root / "latest.json")
    latest = read_json(root / "latest.json")
    prefix = latest["snapshot_prefix"]
    if not re.fullmatch(r"silver/chocolate/uk/silver-[a-f0-9]+", prefix):
        raise ValueError("Unexpected snapshot path")
    download(f"{base}/{prefix}/manifest.json", root / "manifest.json")
    if digest((root / "manifest.json").read_bytes()) != latest["manifest_sha256"]:
        raise ValueError("Manifest does not match the pinned latest pointer")
    manifest = read_json(root / "manifest.json")
    for name in FILES:
        expected = manifest["managed_files"][name]
        destination = root / name
        if destination.exists() and digest(destination.read_bytes()) == expected["sha256"]:
            continue
        download(f"{base}/{prefix}/{name}", destination)
    return root


def verify(root):
    latest, metadata = read_json(root / "latest.json"), read_json(root / "repo-metadata.json")
    if metadata.get("id") != REPO or not re.fullmatch(r"[a-f0-9]{40}", metadata.get("sha", "")):
        raise ValueError("Unexpected repository metadata")
    if digest((root / "manifest.json").read_bytes()) != latest["manifest_sha256"]:
        raise ValueError("Manifest hash mismatch")
    manifest = read_json(root / "manifest.json")
    if latest["dataset_version"] != manifest["dataset_version"]:
        raise ValueError("Mixed snapshot versions")
    for name in FILES:
        body = (root / name).read_bytes()
        expected = manifest["managed_files"][name]
        if len(body) != expected["byte_length"] or digest(body) != expected["sha256"]:
            raise ValueError(f"Snapshot integrity check failed: {name}")
    return latest, metadata, manifest


def load_snapshot_contract(root):
    """Validate the contracts already authenticated by this snapshot's manifest.

    This display adapter preserves the snapshot's model metadata. Current
    training taxonomy and target-policy gates belong to the training pipeline;
    applying them here would reinterpret historical snapshots.
    """
    names = ("profile.json", "source-mappings.json", "model-design.json", "product.schema.json")
    documents = {name: read_json(root / name) for name in names}
    profile, mappings, design, schema = (documents[name] for name in names)
    version = profile.get("schema_version")
    if version != "chocolate-schema-1" or any(document.get("schema_version") != version for document in (mappings, design)):
        raise ValueError("Snapshot contracts must agree on the supported chocolate schema version.")
    if schema["properties"]["schema_version"].get("const") != version:
        raise ValueError("Product validation contract disagrees with the snapshot profile.")
    attributes = profile["attributes"]
    validation = schema["properties"]["attributes"]
    if profile.get("attribute_count") != len(attributes) or set(validation["properties"]) != set(attributes) or set(validation["required"]) != set(attributes):
        raise ValueError("Snapshot profile and product validator attribute catalogs disagree.")
    if set(mappings.get("aliases", {})) - set(attributes) or set(design["predictors"]) - set(attributes):
        raise ValueError("Snapshot mappings and model predictors must reference declared attributes.")
    for name, definition in attributes.items():
        if definition.get("standardization_rule") not in profile["standardization_rules"]:
            raise ValueError("Every snapshot attribute needs a declared standardization rule.")
        validate_attribute_contract(name, definition, validation["properties"][name])
    return profile, mappings, design, {name: digest((root / name).read_bytes()) for name in names}


def timestamp(value):
    if not value:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # An undated/ambiguous observation never outranks a dated one.
        return parsed.timestamp() if parsed.tzinfo else float("-inf")
    except (ValueError, TypeError):
        return float("-inf")


def compact_attribute(attribute):
    # Only truly empty unknowns are omitted. The schema still defines every key;
    # UI omission means unknown, never absent/false or zero.
    if attribute["status"] == "unknown" and attribute.get("value") is None and not attribute.get("evidence") and attribute.get("review_status", "unreviewed") == "unreviewed":
        return None
    return {k: attribute.get(k) for k in ("value", "status", "unit", "qualifier", "scope", "review_status", "method", "evidence")}


def summary_attribute(attribute):
    value = attribute.get("value")
    rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    truncated = len(rendered) > 180
    return {"value": rendered[:180] + "…" if truncated else value, "status": attribute["status"],
            "unit": attribute.get("unit"), "scope": attribute.get("scope"),
            "qualifier": attribute.get("qualifier"), "reviewStatus": attribute.get("review_status", "unreviewed"), "truncated": truncated}


def write_server_snapshot(directory, payload, evidence_by_source):
    """Write the same validated projection as non-public Vercel function assets."""
    directory.mkdir(parents=True, exist_ok=True)
    assets = {"index.json": payload}
    assets.update({f"evidence/{source}.json": detail for source, detail in evidence_by_source.items()})
    files = {}
    for name, value in assets.items():
        body = (json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
        files[name] = {"sha256": digest(body), "byteLength": len(body)}
    # Remove only obsolete generated evidence shards, never arbitrary local files.
    for old in (directory / "evidence").glob("*.json"):
        if old.relative_to(directory).as_posix() not in files:
            old.unlink()
    manifest = {"formatVersion": 1, "revision": payload["meta"]["revision"],
                "datasetVersion": payload["meta"]["datasetVersion"],
                "schemaVersion": payload["meta"]["schemaVersion"], "files": files}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build(root, output):
    latest, metadata, manifest = verify(root)
    quality = read_json(root / "quality-report.json")
    schema = read_json(root / "product.schema.json")
    profile, mappings, design, contract_hashes = load_snapshot_contract(root)
    fields = schema["properties"]["attributes"]["properties"]
    version = manifest["dataset_version"]
    if quality["dataset_version"] != version:
        raise ValueError("Quality report belongs to another snapshot")
    if manifest.get("schema_version", profile["schema_version"]) != profile["schema_version"]:
        raise ValueError("Manifest and snapshot schema versions disagree")
    candidates = {r["observation_id"]: r for r in rows(root / "training-candidates.jsonl")}
    prices = defaultdict(list)
    observation_ids = set()
    for observation in rows(root / "prices.jsonl"):
        if observation["dataset_version"] != version or observation["observation_id"] in observation_ids:
            raise ValueError("Duplicate or mixed-version price observation")
        observation_ids.add(observation["observation_id"])
        candidate = candidates.get(observation["observation_id"])
        if candidate and candidate["listing_id"] != observation["listing_id"]:
            raise ValueError("Candidate/listing join mismatch")
        # Preserve all observation context and evidence, not just a headline price.
        prices[observation["listing_id"]].append(observation)
    listings, ids, known_counts, conflict_counts, numeric_counts = [], set(), Counter(), Counter(), Counter()
    evidence_by_source = defaultdict(dict)
    for product in rows(root / "products.jsonl"):
        listing_id = product["listing_id"]
        if product["dataset_version"] != version or listing_id in ids:
            raise ValueError("Duplicate or mixed-version listing")
        try:
            validate_product(product, profile, mappings)
        except ValueError as error:
            raise ValueError(f"Schema validation failed for {listing_id}: {error}") from error
        ids.add(listing_id)
        attributes = product["attributes"]
        if set(attributes) != set(fields):
            raise ValueError("Product attributes do not match the published schema")
        for key, value in attributes.items():
            if value["status"] == "known":
                known_counts[key] += 1
                if isinstance(value["value"], (float, int)) and not isinstance(value["value"], bool):
                    numeric_counts[key] += 1
            if value["status"] == "conflict":
                conflict_counts[key] += 1
        observations = sorted(prices.get(listing_id, []), key=lambda p: (timestamp(p.get("observed_at")), p["observation_id"]), reverse=True)
        latest_price = observations[0] if observations else None
        tied = [p for p in observations if timestamp(p.get("observed_at")) == timestamp(latest_price.get("observed_at"))] if latest_price else []
        price_conflict = len({(p.get("displayed_price"), p.get("currency"), p.get("total_edible_weight_g")) for p in tied}) > 1
        compact = {key: value for key, attribute in attributes.items() if (value := compact_attribute(attribute)) is not None}
        source = product["source_key"]
        if not re.fullmatch(r"[a-z0-9-]+", source):
            raise ValueError("Unsafe source key for local evidence asset")
        evidence_by_source[source][listing_id] = {"attributes": compact, "prices": observations}
        price_fields = ("observation_id", "observed_at", "currency", "displayed_price", "displayed_price_per_100g_gbp",
                        "total_edible_weight_g", "quantity_status", "model_eligible")
        listings.append({"id": listing_id, "name": attributes["identity.name"].get("value") or listing_id,
                         "brand": product.get("brand"), "retailer": product.get("retailer"),
                         "source": product["source_key"], "role": product["source_role"],
                         "reviewStatus": product["review_status"], "attributes": {k: summary_attribute(v) for k, v in compact.items()},
                         "known": sum(a["status"] == "known" for a in attributes.values()),
                         "conflicts": sum(a["status"] == "conflict" for a in attributes.values()),
                         "prices": [{k: p.get(k) for k in price_fields} for p in observations], "latestPriceConflict": price_conflict,
                         "sourceListingIds": product["source_listing_ids"]})
    if set(prices) - ids:
        raise ValueError("Price observations reference unknown listings")
    model_rows = list(rows(root / "model-inputs.jsonl"))
    expected = quality["counts"]
    if (len(listings), len(observation_ids), len(model_rows)) != (expected["listings"], expected["price_observations"], expected["eligible_model_inputs"]):
        raise ValueError("Downloaded row counts do not reconcile with the quality report")
    attributes = []
    for key, definition in profile["attributes"].items():
        attributes.append({"key": key, "label": key.split(".", 1)[1].replace("_", " ").capitalize(),
                           "group": key.split(".", 1)[0], "known": known_counts[key], "conflicts": conflict_counts[key],
                           "numeric": definition["type"] in ("number", "integer"), "numericKnown": numeric_counts[key],
                           "type": definition["type"], "unit": definition.get("unit"), "scope": definition.get("scope"),
                           "description": definition.get("description", ""), "qualifier": definition.get("qualifier", ""),
                           "minimum": definition.get("minimum"), "maximum": definition.get("maximum"),
                           "allowedValues": definition.get("allowed_values", []), "modelRole": definition.get("model_role"),
                           "modelSelected": key in design["predictors"], "modelDefinition": design["predictors"].get(key)})
    report = {"repository": REPO, "revision": metadata["sha"], "datasetVersion": version,
              "sourceDatasetVersion": manifest["source_dataset_version"], "lastModified": metadata.get("lastModified"),
              "schemaVersion": profile["schema_version"], "modelDesignVersion": design["model_design_version"],
              "schemaValidatedListings": len(listings), "contractHashes": contract_hashes,
              "snapshotPrefix": latest["snapshot_prefix"], "releaseReady": latest["release_ready"],
              "counts": expected, "sourceRoles": quality["source_role_counts"],
              "exclusionCounts": quality["exclusion_counts"], "verifiedFiles": list(FILES),
              "manifestSha256": latest["manifest_sha256"], "omittedHeavyFiles": ["assertions.jsonl", "source-listings.jsonl", "review-queue.jsonl", "raw evidence bundle"],
              "interpretation": "Source listings and unreviewed observations. No fitted pricing model. Latest dated observation selected; undated observations rank last. Same-time price conflicts are excluded from the price plot."}
    contract = {"schemaVersion": profile["schema_version"], "modelDesignVersion": design["model_design_version"],
                "category": profile["category"], "market": profile["market"], "groups": profile["groups"],
                "states": profile["missing_states"], "reviewStatuses": profile["review_statuses"],
                "modelTarget": design["target"], "selectedPredictors": list(design["predictors"])}
    payload = {"meta": report, "contract": contract, "fields": attributes, "products": listings}
    write_server_snapshot(output, payload, evidence_by_source)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Build offline from an already downloaded snapshot directory")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/hf-snapshot")
    parser.add_argument("--output", type=Path, default=ROOT / "apps/web/snapshot")
    args = parser.parse_args()
    root = args.snapshot or sync(args.cache)
    report = build(root, args.output)
    print(json.dumps({"snapshot": str(root), "server_data": str(args.output),
                      "revision": report["revision"], "counts": report["counts"]}, indent=2))


if __name__ == "__main__":
    main()
