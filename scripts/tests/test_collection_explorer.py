"""Snapshot integrity, observation choice and evidence-preservation regression checks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from chocolate_standardization.values import unknown_attribute

SPEC = importlib.util.spec_from_file_location("collection_builder", Path(__file__).parents[1] / "build_collection_explorer.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CollectionExplorerTests(unittest.TestCase):
    def fixture(self, root):
        version = "silver-test"
        schema_root = Path(__file__).parents[2] / "schemas/chocolate"
        profile = json.loads((schema_root / "profile.json").read_text())
        attribute = {"value": "A" * 300, "status": "known", "unit": None, "scope": "product", "review_status": "unreviewed",
                     "method": "source_identity", "qualifier": None, "evidence": [{"capture_id": "capture-1", "pointer": "/name"}]}
        product = {"listing_id": "source-1", "source_listing_ids": ["source-1"], "dataset_version": version,
                   "source_key": "example-source", "source_role": "unknown", "review_status": "unreviewed",
                   "schema_version": profile["schema_version"], "source_dataset_version": "raw-test", "brand": None, "retailer": None, "unmapped_claims": [],
                   "attributes": {key: unknown_attribute(definition) for key, definition in profile["attributes"].items()}}
        product["attributes"]["identity.name"] = attribute
        dated = {"observation_id": "first", "listing_id": "source-1", "dataset_version": version, "observed_at": "2026-10-03T12:00:00Z",
                 "displayed_price": 2, "currency": "GBP", "total_edible_weight_g": 100, "quantity_status": "known", "model_eligible": False}
        observations = [dated, {**dated, "observation_id": "other", "observed_at": "2026-10-03T13:00:00+01:00", "displayed_price": 3},
                        {**dated, "observation_id": "zzz-undated", "observed_at": None, "displayed_price": 9}]
        for name in builder.FILES:
            (root / name).write_text("" if name.endswith(".jsonl") else "{}")
        (root / "products.jsonl").write_text(json.dumps(product) + "\n")
        (root / "prices.jsonl").write_text("".join(json.dumps(p) + "\n" for p in observations))
        for name in ("profile.json", "product.schema.json", "model-design.json", "source-mappings.json"):
            (root / name).write_bytes((schema_root / name).read_bytes())
        (root / "quality-report.json").write_text(json.dumps({"dataset_version": version, "counts": {"listings": 1, "price_observations": 3, "eligible_model_inputs": 0}, "source_role_counts": {"unknown": 1}, "exclusion_counts": {}}))
        manifest = {"dataset_version": version, "source_dataset_version": "raw-test", "managed_files": {name: {"byte_length": (root / name).stat().st_size, "sha256": builder.digest((root / name).read_bytes())} for name in builder.FILES}}
        (root / "manifest.json").write_text(json.dumps(manifest))
        (root / "latest.json").write_text(json.dumps({"dataset_version": version, "manifest_sha256": builder.digest((root / "manifest.json").read_bytes()), "snapshot_prefix": "silver/chocolate/uk/silver-test", "release_ready": False}))
        (root / "repo-metadata.json").write_text(json.dumps({"id": builder.REPO, "sha": "a" * 40, "lastModified": "2026-10-03T12:26:06Z"}))

    def update_inventory(self, root, filename):
        manifest = json.loads((root / "manifest.json").read_text())
        body = (root / filename).read_bytes()
        manifest["managed_files"][filename] = {"byte_length": len(body), "sha256": builder.digest(body)}
        (root / "manifest.json").write_text(json.dumps(manifest))
        latest = json.loads((root / "latest.json").read_text())
        latest["manifest_sha256"] = builder.digest((root / "manifest.json").read_bytes())
        (root / "latest.json").write_text(json.dumps(latest))

    def test_build_preserves_evidence_and_marks_same_time_price_conflicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            raw = (root / "products.jsonl").read_bytes()
            target = root / "output" / "collection-snapshot.js"
            report = builder.build(root, target)
            data = json.loads(target.read_text().split("window.RGCCollectionSnapshot = ", 1)[1].removesuffix(";\n"))
            product = data["products"][0]
            self.assertEqual(product["prices"][-1]["observation_id"], "zzz-undated")
            self.assertTrue(product["latestPriceConflict"])
            self.assertEqual(product["known"], 1)
            self.assertNotIn("composition.cocoa_percentage", product["attributes"])
            self.assertTrue(product["attributes"]["identity.name"]["truncated"])
            source = (target.parent / "collection-evidence/example-source.js").read_text()
            detail = json.loads(source.split('window.RGCCollectionEvidence["example-source"] = ', 1)[1].removesuffix(";\n"))
            self.assertEqual(detail["source-1"]["attributes"]["identity.name"]["value"], "A" * 300)
            self.assertEqual(detail["source-1"]["attributes"]["identity.name"]["evidence"][0]["capture_id"], "capture-1")
            self.assertEqual((root / "products.jsonl").read_bytes(), raw)
            self.assertEqual(report["counts"]["eligible_model_inputs"], 0)
            cocoa = next(field for field in data["fields"] if field["key"] == "composition.cocoa_percentage")
            self.assertEqual((cocoa["type"], cocoa["unit"], cocoa["minimum"], cocoa["maximum"]), ("number", "%", 0, 100))
            self.assertTrue(cocoa["numeric"])
            self.assertEqual(cocoa["numericKnown"], 0)
            self.assertTrue(cocoa["modelSelected"])
            sugar = next(field for field in data["fields"] if field["key"] == "nutrition.sugars_g_per_100g")
            self.assertFalse(sugar["modelSelected"])
            self.assertEqual(data["contract"]["schemaVersion"], "chocolate-schema-1")
            self.assertEqual(len(data["contract"]["selectedPredictors"]), 11)
            self.assertEqual(report["schemaValidatedListings"], 1)

    def test_tampered_download_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            (root / "prices.jsonl").write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "integrity check failed: prices.jsonl"):
                builder.build(root, root / "output.js")
            self.assertFalse((root / "output.js").exists())

    def test_server_export_preserves_full_evidence_and_hashes_every_asset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            server = root / "server-snapshot"
            (server / "evidence").mkdir(parents=True)
            (server / "evidence/obsolete-source.json").write_text("{}")
            (server / "evidence/README.txt").write_text("Keep local notes.")
            builder.build(root, root / "browser/snapshot.js", server)
            manifest = json.loads((server / "manifest.json").read_text())
            self.assertEqual(manifest["revision"], "a" * 40)
            self.assertEqual(manifest["schemaVersion"], "chocolate-schema-1")
            self.assertEqual(set(manifest["files"]), {"index.json", "evidence/example-source.json"})
            for name, expected in manifest["files"].items():
                body = (server / name).read_bytes()
                self.assertEqual(builder.digest(body), expected["sha256"])
                self.assertEqual(len(body), expected["byteLength"])
            index = json.loads((server / "index.json").read_text())
            evidence = json.loads((server / "evidence/example-source.json").read_text())["source-1"]
            self.assertTrue(index["products"][0]["attributes"]["identity.name"]["truncated"])
            self.assertEqual(evidence["attributes"]["identity.name"]["value"], "A" * 300)
            self.assertEqual(len(evidence["prices"]), 3)
            self.assertFalse((server / "evidence/obsolete-source.json").exists())
            self.assertTrue((server / "evidence/README.txt").exists())

    def test_mixed_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            (root / "manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Manifest hash mismatch"):
                builder.verify(root)

    def test_unknown_and_false_remain_distinct(self):
        self.assertIsNone(builder.compact_attribute({"status": "unknown", "value": None, "evidence": []}))
        present = builder.compact_attribute({"status": "known", "value": False, "evidence": [{"capture_id": "x"}]})
        self.assertIs(present["value"], False)
        self.assertEqual(present["status"], "known")

    def test_schema_invalid_listing_rejected_even_with_valid_checksums(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            product = json.loads((root / "products.jsonl").read_text())
            product["attributes"]["composition.cocoa_percentage"].update(value=101, status="known", evidence=[{"capture_id": "x", "pointer": "/cocoa"}])
            (root / "products.jsonl").write_text(json.dumps(product) + "\n")
            self.update_inventory(root, "products.jsonl")
            with self.assertRaisesRegex(ValueError, "Schema validation failed for source-1"):
                builder.build(root, root / "output.js")
            self.assertFalse((root / "output.js").exists())

    def test_profile_validator_drift_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            profile = json.loads((root / "profile.json").read_text())
            profile["attributes"]["composition.cocoa_percentage"]["maximum"] = 80
            (root / "profile.json").write_text(json.dumps(profile))
            self.update_inventory(root, "profile.json")
            with self.assertRaisesRegex(ValueError, "numeric bounds differ"):
                builder.build(root, root / "output.js")

    def test_reviewed_unknown_is_not_omitted(self):
        value = {"status": "unknown", "value": None, "review_status": "reviewed", "evidence": []}
        self.assertEqual(builder.compact_attribute(value)["review_status"], "reviewed")

    def test_timestamps_compare_instants_and_reject_ambiguous_times(self):
        self.assertEqual(builder.timestamp("2026-10-03T12:00:00Z"), builder.timestamp("2026-10-03T13:00:00+01:00"))
        self.assertEqual(builder.timestamp("2026-10-03T12:00:00"), float("-inf"))
        self.assertEqual(builder.timestamp("not a date"), float("-inf"))


if __name__ == "__main__":
    unittest.main()
