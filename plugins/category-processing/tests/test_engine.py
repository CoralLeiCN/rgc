"""Exercise category processing with preserved chocolate and coffee fixtures."""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from fixture_archive import import_document
from category_processing.pipeline import build_silver_dataset
from category_processing.tracking import compare_ledgers


class CategoryProcessingEngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = self.base / "collections"
        self.output = self.base / "silver"
        self.profile = PLUGIN_ROOT / "profiles/coffee"

    def product(self, listing="coffee-example", source="fixture-retailer", price=6.5,
                observed_at="2026-10-03T07:00:00Z"):
        return {
            "product_id": listing, "source_key": source,
            "source_url": "https://" + source + ".example.test/products/coffee",
            "identity": {"name": "Fixture Coffee 250g", "brand": "Fixture Coffee Maker",
                         "source_product_id": "coffee-product", "source_variant_id": "coffee-250g"},
            "information": {
                "product_group": "whole_bean", "net_weight_g": 250,
                "coffee": {"roast": "Medium Roast", "format": "whole beans", "decaf_claim": "caffeinated"},
                "origin": {"countries": ["colombia"]}, "packaging": {"type": "pouch"},
                "price": {"amount": price, "regular_amount": price, "currency": "GBP",
                          "observed_at": observed_at, "available": True, "tax_basis": "consumer_tax_included"},
            },
            "source_artifacts": [{"kind": "page", "content": "Original source: café colombiano; café en grains.\n",
                                  "url": "https://" + source + ".example.test/products/coffee"}],
            "images": [],
        }

    def collect(self, products, category="coffee"):
        return import_document({"contract_version": "1",
                                "study": {"study_id": category + "-processing-fixture", "category": category, "market": "uk"},
                                "products": products}, self.archive, workers=1)

    def build(self, reviews=None, profile=None, output=None):
        return build_silver_dataset(self.archive, output or self.output, profile or self.profile, reviews=reviews)

    def rows(self, name, output=None):
        return [json.loads(line) for line in ((output or self.output) / (name + ".jsonl")).read_text().splitlines()]

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob("*") if path.is_file()}

    def reviews(self):
        product = self.rows("products")[0]
        attributes = product["attributes"]
        design = json.loads((self.profile / "model-design.json").read_text())
        common = {"reviewed_by": "Fixture reviewer", "reason": "Explicit fixture evidence supports this reviewed decision."}
        reviewed_attributes = {
            name: {**common, "value": attributes[name]["value"], "status": "known", "scope": "product",
                   "evidence": deepcopy(attributes[name]["evidence"])}
            for name in design["predictors"]
        }
        product_review = {**common, "variant_id": "reviewed-coffee-250g", "family_id": "reviewed-coffee-family",
                          "in_scope": True, "attributes": reviewed_attributes,
                          "evidence": deepcopy(attributes["identity.name"]["evidence"])}
        price_reviews = {
            price["observation_id"]: {**common, "regular_price": 6.5, "currency": "GBP",
                                      "tax_basis": "consumer_tax_included", "available": True,
                                      "observed_at": "2026-10-03T07:00:00Z", "evidence": deepcopy(price["evidence"])}
            for price in self.rows("prices")
        }
        return {"review_format_version": "category-processing-reviews-1",
                "products": {product["listing_id"]: product_review}, "prices": price_reviews}

    def test_coffee_schema_is_independent_and_preserves_original_archive_bytes(self):
        original = self.product()
        self.collect([original])
        before = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(self.snapshot(self.archive), before)
        row = self.rows("products")[0]
        self.assertEqual(row["category"], "coffee")
        self.assertEqual(len(row["attributes"]), 12)
        self.assertEqual(row["attributes"]["coffee.roast"]["value"], "medium")
        self.assertEqual(row["attributes"]["coffee.format"]["value"], "whole_bean")
        self.assertEqual(row["attributes"]["coffee.decaf_claim"]["value"], "absent")
        self.assertEqual(row["attributes"]["coffee.arabica_percentage"]["status"], "unknown")
        self.assertIsNone(row["attributes"]["coffee.arabica_percentage"]["value"])
        self.assertFalse(any("cocoa" in name or "nuts" in name for name in row["attributes"]))
        self.assertEqual(self.rows("source-listings")[0]["captures"][0]["raw_record"], original)
        self.assertEqual(self.rows("model-inputs"), [])
        self.assertFalse(report["release_ready"])

    def test_exact_duplicates_merge_within_seller_and_other_sellers_remain_unique(self):
        self.collect([self.product("first-copy"), self.product("second-copy"),
                      self.product("brand-copy", "fixture-roaster")])
        self.build()
        sources = {row["listing_id"]: row for row in self.rows("source-listings")}
        self.assertEqual(set(sources), {"first-copy", "brand-copy"})
        self.assertEqual(sources["first-copy"]["source_listing_ids"], ["first-copy", "second-copy"])
        self.assertEqual(sources["first-copy"]["source_role"], "retail")
        self.assertEqual(sources["brand-copy"]["source_role"], "brand")
        self.assertNotEqual(sources["first-copy"]["seller_uid"], sources["brand-copy"]["seller_uid"])
        self.assertEqual(len(self.rows("retail/products")), 1)
        self.assertEqual(len(self.rows("brand/products")), 1)
        self.assertEqual(len(self.rows("unknown/products")), 0)

    def test_alias_addition_and_new_capture_preserve_existing_stable_identifiers(self):
        self.collect([self.product("middle-name")])
        self.build()
        uid = self.rows("products")[0]["seller_uid"]
        observations = {row["observation_id"] for row in self.rows("prices")}
        self.collect([self.product("aaa-new-alias")])
        self.build()
        self.assertEqual(self.rows("products")[0]["seller_uid"], uid)
        self.assertEqual(self.rows("products")[0]["listing_id"], "aaa-new-alias")
        self.assertEqual({row["observation_id"] for row in self.rows("prices")}, observations)
        self.collect([self.product("middle-name", price=7.0, observed_at="2026-10-04T07:00:00Z")])
        self.build()
        self.assertEqual(self.rows("products")[0]["seller_uid"], uid)
        self.assertTrue(observations < {row["observation_id"] for row in self.rows("prices")})

    def test_reviewed_coffee_rows_have_generic_unit_price_targets(self):
        self.collect([self.product()])
        self.build()
        ids = {row["observation_id"] for row in self.rows("prices")}
        self.build(self.reviews())
        eligible = self.rows("model-inputs")
        self.assertEqual(len(eligible), 1)
        self.assertAlmostEqual(eligible[0]["target"]["regular_unit_price"], 2.6)
        self.assertAlmostEqual(eligible[0]["target"]["log_regular_unit_price"], math.log(2.6))
        self.assertEqual(set(eligible[0]["target"]) & {"regular_price_per_100g_gbp", "log_regular_price_per_100g_gbp"}, set())
        self.assertEqual({row["observation_id"] for row in self.rows("prices")}, ids)

    def test_review_changes_invalidate_prior_processing_state(self):
        self.collect([self.product()])
        initial = self.build()
        prior_ledger = self.rows("processing-ledger")
        reviewed = self.build(self.reviews())
        self.assertNotEqual(reviewed["processing_fingerprint"], initial["processing_fingerprint"])
        self.assertEqual(compare_ledgers(self.rows("processing-ledger"), prior_ledger)["rules_changed"], 1)
        self.assertEqual(len(self.rows("model-inputs")), 1)

    def test_valid_category_value_outside_selected_model_domain_is_excluded(self):
        self.collect([self.product()])
        copied = self.base / "restricted-model-profile"
        shutil.copytree(self.profile, copied)
        path = copied / "model-design.json"
        design = json.loads(path.read_text())
        design["predictors"]["coffee.roast"]["allowed_values"] = ["light", "dark"]
        path.write_text(json.dumps(design))
        self.build(profile=copied)
        report = self.build(self.reviews(), profile=copied)
        self.assertEqual(report["status"], "complete_snapshot")
        self.assertEqual(self.rows("products")[0]["attributes"]["coffee.roast"]["value"], "medium")
        self.assertEqual(self.rows("model-inputs"), [])
        self.assertIn("model_predictor_outside_design_domain:coffee.roast", self.rows("training-candidates")[0]["exclusion_reasons"])

    def test_complete_reviewed_cli_handoff_preserves_families_and_no_fit_status(self):
        first = self.product("coffee-family-a")
        second = self.product("coffee-family-b")
        second["identity"]["source_product_id"] = "distinct-coffee-b"
        self.collect([first, second])
        self.build()
        template = next(iter(self.reviews()["products"].values()))
        reviews = {"review_format_version": "category-processing-reviews-1", "products": {}, "prices": {}}
        for product in self.rows("products"):
            decision = deepcopy(template)
            decision["variant_id"] = product["seller_uid"] + "-physical"
            decision["family_id"] = product["seller_uid"] + "-family"
            decision["evidence"] = deepcopy(product["attributes"]["identity.name"]["evidence"])
            for name, review in decision["attributes"].items():
                review["evidence"] = deepcopy(product["attributes"][name]["evidence"])
            reviews["products"][product["seller_uid"]] = decision
        for price in self.rows("prices"):
            reviews["prices"][price["observation_id"]] = {
                "reviewed_by": "Fixture reviewer", "reason": "Explicit complete observed price context.",
                "regular_price": 6.5, "currency": "GBP", "tax_basis": "consumer_tax_included",
                "observed_at": "2026-10-03T07:00:00Z", "available": True, "evidence": deepcopy(price["evidence"]),
            }
        self.build(reviews)
        destination = self.base / "prepared-model"
        command = [sys.executable, "-I", "-B", str(PLUGIN_ROOT / "cli.py"), "prepare-model",
                   "--silver-root", str(self.output), "--output", str(destination)]
        result = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((destination / "preparation-report.json").read_text())
        self.assertFalse(report["regression_fitted"])
        self.assertFalse(report["release_ready"])
        train, validation = self.rows("train", destination), self.rows("validation", destination)
        self.assertEqual(len(train), 1)
        self.assertEqual(len(validation), 1)
        self.assertFalse({row["family_id"] for row in train} & {row["family_id"] for row in validation})
        (self.output / "model-inputs.jsonl").write_text("{}\n")
        rejected = self.base / "tampered-preparation"
        command[command.index(str(destination))] = str(rejected)
        result = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("differs from its manifest", result.stderr)
        self.assertFalse(rejected.exists())

    def test_unknown_and_unmapped_values_stay_evidence_backed_without_fabricated_absence(self):
        product = self.product()
        product["information"]["coffee"].pop("decaf_claim")
        product["information"]["coffee"]["roast"] = "Novel Proprietary Roast"
        product["information"]["coffee"]["new_source_claim"] = "Original unfamiliar coffee claim"
        self.collect([product])
        self.build()
        row = self.rows("products")[0]
        self.assertEqual(row["attributes"]["coffee.decaf_claim"]["status"], "unknown")
        self.assertIsNone(row["attributes"]["coffee.decaf_claim"]["value"])
        claims = {claim["attribute"]: claim for claim in row["unmapped_claims"]}
        self.assertEqual(claims["coffee.new_source_claim"]["value"], "Original unfamiliar coffee claim")
        self.assertTrue(claims["coffee.roast"]["evidence"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_conflicting_mappings_keep_all_evidence_and_no_selected_value(self):
        product = self.product()
        product["information"]["alternate_roast"] = "Dark Roast"
        self.collect([product])
        copied = self.base / "coffee-profile"
        shutil.copytree(self.profile, copied)
        recipe_path = copied / "pipeline.json"
        recipe = json.loads(recipe_path.read_text())
        recipe["fields"].append({"attribute": "coffee.roast", "pointer": "/raw_record/information/alternate_roast"})
        recipe_path.write_text(json.dumps(recipe))
        self.build(profile=copied)
        attribute = self.rows("products")[0]["attributes"]["coffee.roast"]
        self.assertEqual(attribute["status"], "conflict")
        self.assertIsNone(attribute["value"])
        self.assertGreaterEqual(len(attribute["evidence"]), 2)
        conflicts = [row for row in self.rows("mapping-review-batches") if row["reason"] == "conflict"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(set(conflicts[0]["value"]), {"Medium Roast", "Dark Roast"})

    def test_new_seller_role_is_an_evidenced_mapping_gap(self):
        self.collect([self.product(source="unregistered-seller")])
        self.build()
        row = self.rows("products")[0]
        self.assertEqual(row["source_role"], "unknown")
        batches = [item for item in self.rows("mapping-review-batches") if item["reason"] == "selling_source_role_unmapped"]
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["value"], "unregistered-seller")
        self.assertEqual(batches[0]["scope"], "product")

    def test_malformed_source_context_remains_unresolved_with_original_facts(self):
        product = self.product(source="")
        product["identity"]["brand"] = 12345
        self.collect([product])
        self.build()
        row = self.rows("products")[0]
        self.assertEqual(row["source_key"], "unknown")
        self.assertEqual(row["source_role"], "unknown")
        self.assertIsNone(row["brand"])
        self.assertEqual(row["attributes"]["identity.brand"]["status"], "unknown")
        self.assertTrue(any(claim["attribute"] == "identity.brand" for claim in row["unmapped_claims"]))
        self.assertEqual(self.rows("source-listings")[0]["captures"][0]["raw_record"], product)
        self.assertEqual(self.rows("model-inputs"), [])

    def test_outputs_are_deterministic_and_contract_copies_match_recorded_hashes(self):
        self.collect([self.product()])
        first = self.build()
        before = self.snapshot(self.output)
        self.assertEqual(self.build(), first)
        self.assertEqual(self.snapshot(self.output), before)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertTrue(manifest["dataset_version"].startswith("silver-"))
        self.assertTrue(manifest["source_dataset_version"].startswith("raw-snapshot-"))
        for name, checksum in manifest["contract_sha256"].items():
            self.assertEqual((self.output / name).read_bytes(), (self.profile / name).read_bytes())
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), checksum)
        for name, metadata in manifest["managed_files"].items():
            data = (self.output / name).read_bytes()
            self.assertEqual(metadata["byte_length"], len(data))
            self.assertEqual(metadata["sha256"], hashlib.sha256(data).hexdigest())

    def test_changed_seller_identity_is_excluded_with_original_captures_preserved(self):
        self.collect([self.product()])
        self.collect([self.product(source="fixture-roaster")])
        before = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(self.rows("products"), [])
        self.assertEqual(self.rows("prices"), [])
        self.assertEqual(self.snapshot(self.archive), before)
        self.assertTrue(report["archive_errors"])

    def test_bad_reviews_and_unsafe_output_paths_fail_before_writes(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviews()
        reviews["products"]["coffee-example"]["evidence"][0]["pointer"] = "/does/not/resolve"
        rejected = self.base / "rejected"
        with self.assertRaises(ValueError):
            self.build(reviews, output=rejected)
        self.assertFalse(rejected.exists())
        for output in (self.archive, self.archive / "silver", self.base):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.build(output=output)

    def test_chocolate_profile_uses_the_same_generic_engine(self):
        chocolate = {
            "product_id": "chocolate-example", "source_key": "chocolate-shop",
            "source_url": "https://chocolate-shop.example.test/products/chocolate",
            "identity": {"name": "Fixture Dark Chocolate Bar 200g", "brand": "Fixture Maker",
                         "source_product_id": "chocolate-product", "source_variant_id": "200g"},
            "information": {"selected_variant": {"id": "200g", "price": "4.00", "available": True, "title": "Default Title"},
                            "product_type": "Bar", "catalogue_retrieval_currency": "GBP",
                            "catalogue_collected_at": "2026-10-03T07:00:00Z"},
            "source_artifacts": [{"kind": "page", "content": "Original chocolate source.\n",
                                  "url": "https://chocolate-shop.example.test/products/chocolate"}], "images": [],
        }
        self.collect([chocolate], category="chocolate")
        self.build(profile=PLUGIN_ROOT / "profiles/chocolate")
        row = self.rows("products")[0]
        self.assertEqual(row["category"], "chocolate")
        self.assertEqual(len(row["attributes"]), 103)
        self.assertIn("composition.cocoa_percentage", row["attributes"])
        self.assertNotIn("coffee.roast", row["attributes"])

    def test_copied_plugin_processes_coffee_in_isolated_python_without_sibling_modules(self):
        self.collect([self.product()])
        copied = self.base / "moved-processing-plugin"
        shutil.copytree(PLUGIN_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        destination = self.base / "isolated-silver"
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable, "-I", "-B", str(copied / "cli.py"), "process",
                                 "--archive-root", str(self.archive), "--profile", str(copied / "profiles/coffee"),
                                 "--output", str(destination)], cwd=self.base, env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.rows("products", output=destination)), 1)
        self.assertEqual(self.rows("products", output=destination)[0]["category"], "coffee")
        self.assertFalse((copied.parent / "category-research").exists())
        self.assertFalse((copied.parent / "scripts").exists())

    def test_model_preparation_refuses_empty_eligible_rows_without_fake_artifacts(self):
        self.collect([self.product()])
        self.build()
        destination = self.base / "model-preparation"
        result = subprocess.run([sys.executable, "-B", str(PLUGIN_ROOT / "cli.py"), "prepare-model",
                                 "--silver-root", str(self.output), "--output", str(destination)],
                                cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
