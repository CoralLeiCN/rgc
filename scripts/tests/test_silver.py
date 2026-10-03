"""Verify that one raw-input command creates a self-contained chocolate silver layer."""

from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "plugins/category-research"))
sys.path.insert(0, str(ROOT))

from chocolate_cleanup.core import pointer_value
from chocolate_silver import build_silver_dataset
import chocolate_silver as silver_module
from build_chocolate_silver import main as silver_main
import scripts.tests.test_standardization as standardization_fixtures


class ChocolateSilverTests(unittest.TestCase):
    def setUp(self):
        self.fixture = standardization_fixtures.ChocolateStandardizationTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.base = self.fixture.base
        self.archive = self.fixture.archive
        self.output = self.base / "silver"
        self.design = self.fixture.design

    def product(self, *args, **kwargs):
        return self.fixture.product(*args, **kwargs)

    def collect(self, products):
        return self.fixture.collect(products)

    def snapshot(self, directory):
        return self.fixture.snapshot(directory)

    def build(self, reviews=None, output=None):
        return build_silver_dataset(self.archive, output or self.output, reviews=reviews)

    def rows(self, name):
        return [json.loads(line) for line in (self.output / (name + ".jsonl")).read_text(encoding="utf-8").splitlines()]

    def reviews(self):
        source = self.rows("source-listings")[0]
        captures = {capture["capture_id"]: capture for capture in source["captures"]}
        latest = captures[source["latest_capture_id"]]
        capture_id = latest["capture_id"]
        common = {"reviewed_by": "Fixture evidence reviewer",
                  "reason": "Explicit product-specific fixture declaration reviewed."}
        values = latest["raw_record"]["information"]["review_fixture"]
        attributes = {}
        for name in self.design["predictors"]:
            attributes[name] = {
                **common, "value": values[name], "status": "known", "scope": "product",
                "evidence": [{"capture_id": capture_id, "pointer": "/raw_record/information/review_fixture/" + name}],
            }
            if name == "composition.cocoa_percentage":
                attributes[name]["qualifier"] = "exact"
        product = {**common, "variant_id": "reviewed-fixture-variant", "family_id": "reviewed-fixture-family",
                   "in_scope": True, "attributes": attributes,
                   "evidence": [{"capture_id": capture_id, "pointer": "/raw_record/identity/name"}]}
        prices = {}
        for price in self.rows("prices"):
            ref = price["evidence"][0]
            raw = captures[ref["capture_id"]]["raw_record"]
            prices[price["observation_id"]] = {
                **common, "regular_price": float(raw["information"]["selected_variant"]["price"]),
                "currency": "GBP", "tax_basis": "consumer_tax_included", "available": True,
                "observed_at": raw["information"]["catalogue_collected_at"], "evidence": [deepcopy(ref)],
            }
        return {"review_format_version": "chocolate-schema-reviews-1",
                "products": {source["listing_id"]: product}, "prices": prices}

    def test_raw_input_stays_immutable_and_needs_only_one_output_folder(self):
        self.collect([self.product()])
        raw_before = self.snapshot(self.archive)
        self.build()
        self.assertEqual(self.snapshot(self.archive), raw_before)
        self.assertEqual({path.name for path in self.base.iterdir()}, {"collections", "silver"})
        self.assertFalse((self.base / "deduplicated").exists())
        self.assertFalse((self.base / "standardized").exists())
        expected = {"quality-report.json", "manifest.json", "profile.json", "source-mappings.json", "model-design.json", "product.schema.json",
                    "products.jsonl", "assertions.jsonl", "prices.jsonl", "training-candidates.jsonl", "model-inputs.jsonl",
                    "review-queue.jsonl", "source-listings.jsonl", "listing-aliases.jsonl"}
        for role in ("brand", "retail", "unknown"):
            expected.update({role + "/products.jsonl", role + "/prices.jsonl", role + "/source-listings.jsonl"})
        self.assertEqual(set(self.snapshot(self.output)), expected)
        self.assertEqual(self.rows("source-listings")[0]["captures"][0]["raw_record"], self.product())

    def test_exact_same_seller_duplicates_merge_and_other_sellers_stay_unique(self):
        first = self.product("first-copy", "chocolate-shop")
        alias = self.product("second-copy", "chocolate-shop")
        brand = self.product("brand-listing", "montezumas")
        unknown = self.product("unknown-listing", "unresolved-shop")
        self.collect([first, alias, brand, unknown])
        self.build()
        sources = {row["listing_id"]: row for row in self.rows("source-listings")}
        self.assertEqual(set(sources), {"first-copy", "brand-listing", "unknown-listing"})
        self.assertEqual(sources["first-copy"]["source_listing_ids"], ["first-copy", "second-copy"])
        self.assertEqual(len(sources["first-copy"]["captures"]), 2)
        self.assertEqual({row["listing_id"] for row in self.rows("products")}, set(sources))
        aliases = {(row["source_listing_id"], row["listing_id"]) for row in self.rows("listing-aliases")}
        self.assertIn(("second-copy", "first-copy"), aliases)
        self.assertEqual(len(aliases), 4)
        for role, listing in (("brand", "brand-listing"), ("retail", "first-copy"), ("unknown", "unknown-listing")):
            self.assertEqual([row["listing_id"] for row in self.rows(role + "/source-listings")], [listing])
            self.assertEqual([row["listing_id"] for row in self.rows(role + "/products")], [listing])
        self.assertEqual(sources["first-copy"]["brand"], sources["brand-listing"]["brand"])
        self.assertNotEqual(sources["first-copy"]["retailer"], sources["brand-listing"]["retailer"])

    def test_captures_and_artifacts_resolve_from_silver_and_raw_after_build_returns(self):
        self.collect([self.product()])
        original_temporary_directory = silver_module.TemporaryDirectory
        scratch_paths = []

        def captured_scratch(*args, **kwargs):
            kwargs["dir"] = self.base
            temporary = original_temporary_directory(*args, **kwargs)
            scratch_paths.append(Path(temporary.name).resolve())
            return temporary

        with patch.object(silver_module, "TemporaryDirectory", side_effect=captured_scratch):
            self.build()
        sources = self.rows("source-listings")
        captures = {capture["capture_id"]: capture for source in sources for capture in source["captures"]}
        self.assertTrue(captures)
        for capture in captures.values():
            history = self.archive / capture["history_path"]
            self.assertTrue(history.is_file())
            self.assertEqual(json.loads(history.read_text()), capture)
            for artifact in capture["source_artifacts"]:
                path = self.archive / artifact["archive_relative_path"]
                self.assertEqual(path.read_text(), "Original wording: chocolat noir; café.\n")
        for assertion in self.rows("assertions"):
            for ref in assertion["evidence"]:
                pointer_value(captures[ref["capture_id"]], ref["pointer"])
        for product in self.rows("products"):
            for attribute in product["attributes"].values():
                for ref in attribute["evidence"]:
                    pointer_value(captures[ref["capture_id"]], ref["pointer"])
        for table in ("prices", "review-queue"):
            for row in self.rows(table):
                for ref in row.get("evidence", []):
                    pointer_value(captures[ref["capture_id"]], ref["pointer"])
        published = b"".join(self.snapshot(self.output).values())
        self.assertNotIn(str(self.base).encode(), published)
        self.assertTrue(scratch_paths)
        for scratch in scratch_paths:
            self.assertFalse(scratch.exists())
            self.assertNotIn(str(scratch).encode(), published)

    def test_parent_and_source_versions_are_consistent_and_all_outputs_hashed(self):
        self.collect([self.product()])
        report = self.build()
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertTrue(report["dataset_version"].startswith("silver-"))
        self.assertTrue(report["source_dataset_version"].startswith("raw-snapshot-"))
        self.assertEqual(manifest["dataset_version"], report["dataset_version"])
        self.assertEqual(manifest["source_dataset_version"], report["source_dataset_version"])
        for table in ("products", "assertions", "prices", "training-candidates", "model-inputs"):
            for row in self.rows(table):
                self.assertEqual(row["dataset_version"], report["dataset_version"])
                if "source_dataset_version" in row:
                    self.assertEqual(row["source_dataset_version"], report["source_dataset_version"])
        for table in ("source-listings", "listing-aliases", "retail/source-listings"):
            for row in self.rows(table):
                self.assertEqual(row["dataset_version"], report["dataset_version"])
                self.assertEqual(row["source_dataset_version"], report["source_dataset_version"])
        for name, metadata in manifest["managed_files"].items():
            data = (self.output / name).read_bytes()
            self.assertEqual(metadata["byte_length"], len(data))
            self.assertEqual(metadata["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(set(manifest["managed_files"]), set(self.snapshot(self.output)) - {"manifest.json"})
        self.assertEqual(len(manifest["managed_files"]), 22)
        self.assertEqual(set(manifest["contract_sha256"]),
                         {"profile.json", "source-mappings.json", "model-design.json", "product.schema.json"})
        for name, checksum in manifest["contract_sha256"].items():
            with self.subTest(contract=name):
                copied = (self.output / name).read_bytes()
                self.assertEqual(copied, (ROOT / "schemas/chocolate" / name).read_bytes())
                self.assertEqual(hashlib.sha256(copied).hexdigest(), checksum)

    def test_same_archive_and_reviews_rebuild_to_identical_bytes(self):
        self.collect([self.product()])
        first = self.build()
        before = self.snapshot(self.output)
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(self.snapshot(self.output), before)

    def test_reviews_reuse_stable_observation_ids_and_keep_source_snapshot_version(self):
        self.collect([self.product()])
        initial = self.build()
        ids = {row["observation_id"] for row in self.rows("prices")}
        reviewed = self.build(self.reviews())
        self.assertNotEqual(initial["dataset_version"], reviewed["dataset_version"])
        self.assertEqual(initial["source_dataset_version"], reviewed["source_dataset_version"])
        self.assertEqual({row["observation_id"] for row in self.rows("prices")}, ids)
        self.assertEqual(len(self.rows("model-inputs")), 1)
        row = self.rows("model-inputs")[0]
        self.assertEqual(row["target"]["regular_price_per_100g_gbp"], 2)
        self.assertAlmostEqual(row["target"]["log_regular_price_per_100g_gbp"], math.log(2))
        self.assertEqual(len(row["predictors"]), 11)
        self.assertFalse(reviewed["release_ready"])
        before = self.snapshot(self.output)
        self.assertEqual(self.build(self.reviews()), reviewed)
        self.assertEqual(self.snapshot(self.output), before)

    def test_partial_raw_input_quality_is_preserved_in_silver_report(self):
        self.collect([self.product()])
        folder = self.archive / "chocolate/uk/products/invalid"
        folder.mkdir(parents=True)
        (folder / "product.json").write_bytes(b'{"unfinished":')
        before = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["input_status"], "partial")
        self.assertEqual(report["input_quality_counts"]["archive_errors"], 1)
        self.assertEqual(len(self.rows("products")), 1)
        self.assertFalse(report["release_ready"])
        self.assertEqual(self.snapshot(self.archive), before)

    def assert_changed_source_identity_is_preserved_and_excluded(self, first, latest):
        self.collect([first])
        self.collect([latest])
        raw_index = self.archive / "chocolate/uk/products/example/product.json"
        captures = json.loads(raw_index.read_text())["captures"]
        self.assertEqual(len(captures), 2)
        for capture in captures:
            self.assertEqual(json.loads((self.archive / capture["history_path"]).read_text()), capture)
        before = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["counts"]["archive_errors"], 1)
        self.assertEqual(report["counts"]["listings"], 0)
        self.assertEqual(self.rows("source-listings"), [])
        self.assertEqual(self.rows("products"), [])
        self.assertEqual(self.rows("prices"), [])
        self.assertEqual(self.rows("model-inputs"), [])
        self.assertEqual(report["archive_errors"][0]["listing_id"], "example")
        self.assertIn("identity changes across captures", report["archive_errors"][0]["reason"])
        self.assertEqual(self.snapshot(self.archive), before)
        self.assertEqual({json.dumps(capture["raw_record"], sort_keys=True) for capture in captures},
                         {json.dumps(first, sort_keys=True), json.dumps(latest, sort_keys=True)})

    def test_one_raw_folder_cannot_reassign_historical_prices_to_a_different_seller(self):
        first = self.product(source="chocolate-shop", price="4.00", observed_at="2026-10-02T07:00:00Z")
        latest = self.product(source="waitrose", price="3.00", observed_at="2026-10-03T07:00:00Z")
        self.assert_changed_source_identity_is_preserved_and_excluded(first, latest)

    def test_one_raw_folder_cannot_mix_different_source_variant_identifiers(self):
        first = self.product(price="4.00", observed_at="2026-10-02T07:00:00Z")
        latest = self.product(price="3.00", observed_at="2026-10-03T07:00:00Z")
        latest["identity"]["source_variant_id"] = "different-source-variant"
        latest["information"]["selected_variant"]["id"] = "different-source-variant"
        self.assert_changed_source_identity_is_preserved_and_excluded(first, latest)

    def test_silver_output_cannot_overlap_raw_archive(self):
        self.collect([self.product()])
        before = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "silver", self.base):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.build(output=output)
        self.assertEqual(self.snapshot(self.archive), before)

    def test_raw_index_mutation_between_internal_steps_prevents_publication(self):
        self.collect([self.product()])
        original_standardizer = silver_module.build_standardized_dataset
        raw_index = self.archive / "chocolate/uk/products/example/product.json"

        def standardize_then_mutate(*args, **kwargs):
            report = original_standardizer(*args, **kwargs)
            raw_index.write_bytes(raw_index.read_bytes() + b"\n")
            return report

        with patch.object(silver_module, "build_standardized_dataset", side_effect=standardize_then_mutate):
            with self.assertRaisesRegex(RuntimeError, "Raw archive changed"):
                self.build()
        self.assertFalse(self.output.exists())

    def test_bad_output_symlink_is_rejected_before_any_output_is_overwritten(self):
        self.collect([self.product()])
        outside = self.base / "protected-product-table.jsonl"
        original = b"Keep this existing external result unchanged.\n"
        outside.write_bytes(original)
        self.output.mkdir()
        (self.output / "products.jsonl").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "output paths"):
            self.build()
        self.assertEqual(outside.read_bytes(), original)
        self.assertEqual({path.name for path in self.output.iterdir()}, {"products.jsonl"})
        self.assertTrue((self.output / "products.jsonl").is_symlink())

    def test_inside_output_partition_symlink_cannot_alias_another_partition(self):
        self.collect([self.product("brand-listing", "montezumas"), self.product("retail-listing", "chocolate-shop")])
        self.build()
        shutil.rmtree(self.output / "brand")
        (self.output / "brand").symlink_to("retail", target_is_directory=True)
        output_before, raw_before = self.snapshot(self.output), self.snapshot(self.archive)
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.snapshot(self.output), output_before)
        self.assertEqual(self.snapshot(self.archive), raw_before)
        self.assertTrue((self.output / "brand").is_symlink())

    def test_legacy_temporary_hardlink_cannot_overwrite_raw_source(self):
        self.collect([self.product()])
        raw_index = self.archive / "chocolate/uk/products/example/product.json"
        self.output.mkdir()
        legacy = self.output / ".products.jsonl.tmp"
        os.link(raw_index, legacy)
        original = raw_index.read_bytes()
        try:
            self.build()
        except ValueError:
            # Refusing the preexisting hardlink and ignoring it while publishing
            # through a unique temporary file both preserve the raw archive.
            pass
        self.assertEqual(raw_index.read_bytes(), original)
        self.assertEqual(legacy.read_bytes(), original)
        self.assertEqual(legacy.stat().st_ino, raw_index.stat().st_ino)

    def test_cli_builds_silver_directly_and_reports_partial_exit_status(self):
        self.collect([self.product()])
        arguments = ["--archive-root", str(self.archive), "--output", str(self.output)]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(silver_main(arguments), 0)
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["dataset_version"].startswith("silver-"))
        self.assertEqual(result["status"], "complete_snapshot")
        self.assertEqual(result["counts"]["listings"], 1)
        self.assertEqual(Path(result["report_path"]).resolve(), (self.output / "quality-report.json").resolve())
        invalid = self.archive / "chocolate/uk/products/invalid"
        invalid.mkdir(parents=True)
        (invalid / "product.json").write_bytes(b'{"unfinished":')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(silver_main(arguments), 1)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(silver_main(["--archive-root", str(self.archive), "--output", str(self.archive)]), 2)


if __name__ == "__main__":
    unittest.main()
