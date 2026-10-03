"""Exercise Gold inferred joins, preserved evidence and damaged input rejection."""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import web_gold_inferred
from build_web_snapshot import build, read_json
from chocolate_archive_fixture import ChocolateArchiveFixture
from chocolate_gold import build_gold_dataset, checksum, json_bytes, row_bytes
from chocolate_silver import build_silver_dataset


@pytest.fixture
def inferred(tmp_path, monkeypatch):
    fixture = ChocolateArchiveFixture()
    fixture.initialize(tmp_path)
    fixture.collect([fixture.product()])
    silver = tmp_path / "silver"
    build_silver_dataset(fixture.archive, silver, offline=True)
    root = tmp_path / "inferred"
    root.mkdir()
    _, training_root = build_gold_dataset(silver, tmp_path / "gold")
    shutil.copytree(training_root, root / "training")
    products = [json.loads(line) for line in (silver / "products.jsonl").read_text().splitlines()]
    pq.write_table(pa.table({"record_json": [json.dumps(p) for p in products]}), root / "products.parquet")
    (root / "inputs").mkdir()
    shutil.copyfile(silver / "manifest.json", root / "inputs/silver-manifest.json")
    source = read_json(silver / "manifest.json")
    training = read_json(root / "training/manifest.json")
    version = "gold-inferred-" + "a" * 24
    report = {"dataset_version": version, "source_silver_dataset_version": source["dataset_version"],
              "record_json_is_authoritative": True, "eligibility_preserved": True,
              "release_ready": False, "regular_price_basis_contract_version": "regular-consumer-price-1",
              "counts": {"products": 1, "price_observations": 1, "eligible_model_inputs": 0,
                         "accepted_inference_decisions": 0}}
    (root / "report.json").write_bytes(json_bytes(report))
    (root / "inference").mkdir()
    (root / "inference/accepted-decisions.jsonl").write_bytes(b"")
    provenance = {"source_silver_manifest_sha256": checksum((silver / "manifest.json").read_bytes()),
                  "accepted_attribute_cells": 0, "affected_attributes": 0, "affected_listings": 0,
                  "basis": "fixture", "model": "fixture", "public_evidence_lookup": {}}
    (root / "inference/provenance.json").write_bytes(json_bytes(provenance))
    manifest = {"manifest_format_version": "chocolate-gold-inferred-manifest-1", "dataset_version": version,
                "product_count": 1, "attribute_count": 103,
                "source_products_logical_sha256": checksum(row_bytes(products)),
                "source_silver_manifest_sha256": provenance["source_silver_manifest_sha256"],
                "source_silver_dataset_version": source["dataset_version"],
                "source_dataset_version": source["source_dataset_version"],
                "training_gold_dataset_version": training["dataset_version"],
                "training_gold_manifest_sha256": checksum((root / "training/manifest.json").read_bytes()),
                "accepted_inference_decision_count": 0, "accepted_decisions_sha256": checksum(b""),
                "provenance_sha256": checksum(json_bytes(provenance))}
    reference_path = tmp_path / "reference.json"
    monkeypatch.setattr(web_gold_inferred, "REFERENCE", reference_path)

    def seal():
        manifest["managed_files"] = {
            path.relative_to(root).as_posix(): {"sha256": checksum(path.read_bytes()), "byte_length": path.stat().st_size}
            for path in root.rglob("*") if path.is_file() and path.name not in ("dataset-reference.json",)
            and path != root / "manifest.json"
        }
        (root / "manifest.json").write_bytes(json_bytes(manifest))
        reference = {"formatVersion": 1, "repository": "CoralLeiCN/rgc-collections", "revision": "b" * 40,
                     "datasetVersion": version, "snapshotPrefix": "gold-inferred/chocolate/uk/" + version,
                     "manifestSha256": checksum((root / "manifest.json").read_bytes())}
        reference_path.write_bytes(json_bytes(reference))
        (root / "dataset-reference.json").write_bytes(json_bytes(reference))
    seal()
    return root, products, manifest, seal


def test_projection_preserves_complete_values_evidence_prices_and_eligibility(inferred, tmp_path):
    root, products, _, _ = inferred
    output = tmp_path / "web"
    meta = build(root, output)
    snapshot = read_json(output / "index.json")
    product = snapshot["products"][0]
    evidence = read_json(output / "evidence" / (product["source"] + ".json"))[product["id"]]
    assert meta["dataLayer"] == "gold-inferred"
    assert meta["datasetVersion"].startswith("gold-inferred-")
    assert meta["sourceSilverDatasetVersion"] == products[0]["dataset_version"]
    assert meta["counts"]["eligible_model_inputs"] == 0
    assert meta["counts"]["training_rows"] == 1
    assert len(snapshot["fields"]) == 103
    for key, attribute in evidence["attributes"].items():
        assert attribute == {name: products[0]["attributes"][key].get(name) for name in attribute}
    assert evidence["prices"] == [json.loads(line) for line in (root / "training/inputs/prices.jsonl").read_text().splitlines()]
    assert product["prices"][0]["model_eligible"] is False


def test_corrupt_parquet_is_rejected_before_writing(inferred, tmp_path):
    root, _, _, _ = inferred
    with (root / "products.parquet").open("ab") as stream:
        stream.write(b"changed")
    output = tmp_path / "web"
    with pytest.raises(ValueError, match="checksum mismatch"):
        build(root, output)
    assert not output.exists()


def test_logical_records_cannot_drift_from_source_hash(inferred):
    root, products, _, seal = inferred
    products[0]["attributes"]["identity.name"]["value"] = "Changed interpretation"
    pq.write_table(pa.table({"record_json": [json.dumps(p) for p in products]}), root / "products.parquet")
    seal()
    with pytest.raises(ValueError, match="logical checksum"):
        web_gold_inferred.load(root, read_json)


def test_mixed_source_versions_are_rejected(inferred):
    root, _, manifest, seal = inferred
    manifest["source_silver_dataset_version"] = "silver-other"
    seal()
    with pytest.raises(ValueError, match="source provenance"):
        web_gold_inferred.load(root, read_json)


def test_stale_cache_pin_is_rejected(inferred):
    root, _, _, _ = inferred
    reference = read_json(root / "dataset-reference.json")
    reference["revision"] = "c" * 40
    (root / "dataset-reference.json").write_bytes(json_bytes(reference))
    with pytest.raises(ValueError, match="dataset reference"):
        web_gold_inferred.load(root, read_json)
