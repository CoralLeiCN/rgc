"""Verify the evidence boundary from raw deduplication to chocolate model rows."""

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "plugins/category-research"))

from category_research import import_document
from chocolate_cleanup.deduplication import build_deduplicated_dataset
from chocolate_cleanup.core import pointer_value
from chocolate_model import fit_encoder, transform_rows
from chocolate_standardization.pipeline import build_standardized_dataset


class ChocolateStandardizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = self.base / "collections"
        self.deduplicated = self.base / "deduplicated"
        self.output = self.base / "standardized"
        self.profile = json.loads((ROOT / "schemas/chocolate/profile.json").read_text())
        self.design = json.loads((ROOT / "schemas/chocolate/model-design.json").read_text())

    def product(self, listing="example", source="chocolate-shop", weight=200, price="04.00",
                observed_at="2026-10-03T07:00:00Z"):
        return {
            "product_id": listing, "source_key": source,
            "source_url": "https://" + source + ".example.test/products/shared-product",
            "identity": {
                "name": "Fixture Dark Chocolate Bar " + str(weight) + "g",
                "brand": "Fixture Chocolate Maker", "source_product_id": "shared-product",
                "source_variant_id": "shared-variant",
            },
            "information": {
                "selected_variant": {
                    "id": "shared-variant", "price": price, "grams": 999,
                    "available": True, "compare_at_price": None, "title": "Default Title",
                },
                "catalogue_retrieval_currency": "GBP", "catalogue_collected_at": observed_at,
                "product_type": "Bar",
                "body_html": "<p>Original wording: chocolat noir; café.</p>\n",
                "review_fixture": {
                    "identity.product_group": "bar", "identity.source_role": "retail",
                    "identity.brand": "Fixture Chocolate Maker", "identity.retailer": "The Chocolate Shop",
                    "composition.chocolate_type": "dark", "composition.cocoa_percentage": 70,
                    "composition.nuts_presence": "absent", "dietary.vegan_claim": "present",
                    "certifications.fairtrade_claim": "absent", "certifications.organic_claim": "absent",
                    "quantity.total_edible_weight_g": weight,
                },
            },
            "source_artifacts": [{
                "kind": "page", "content": "Original wording: chocolat noir; café.\n",
                "url": "https://" + source + ".example.test/products/shared-product",
            }],
            "images": [],
        }

    def collect(self, products):
        return import_document({
            "contract_version": "1",
            "study": {"study_id": "chocolate-standardization-test", "category": "chocolate", "market": "uk"},
            "products": products,
        }, self.archive, workers=1)

    def prepare(self, products=None):
        self.collect(products or [self.product()])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        return self.build()

    def build(self, reviews=None, output=None):
        return build_standardized_dataset(self.deduplicated, output or self.output, reviews=reviews)

    def test_valid_category_value_outside_selected_model_domain_is_excluded(self):
        self.prepare()
        copied = self.base / "restricted-model-contracts"
        shutil.copytree(ROOT / "schemas/chocolate", copied)
        path = copied / "model-design.json"
        design = json.loads(path.read_text())
        design["predictors"]["quantity.total_edible_weight_g"]["minimum"] = 1000
        path.write_text(json.dumps(design))
        report = build_standardized_dataset(self.deduplicated, self.output, reviews=self.reviews(), schema_root=copied)
        self.assertEqual(report["counts"]["eligible_model_inputs"], 0)
        self.assertEqual(self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"]["value"], 200)
        self.assertIn("model_predictor_outside_design_domain:quantity.total_edible_weight_g", self.rows("training-candidates")[0]["exclusion_reasons"])

    def rows(self, name="products", directory=None):
        return [json.loads(line) for line in
                ((directory or self.output) / (name + ".jsonl")).read_text(encoding="utf-8").splitlines()]

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()}

    def source_listing(self):
        return self.rows(directory=self.deduplicated)[0]

    def reviews(self):
        source = self.source_listing()
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

    def test_standardization_preserves_raw_and_deduplicated_original_bytes(self):
        self.prepare()
        archive_before, dedup_before = self.snapshot(self.archive), self.snapshot(self.deduplicated)
        self.build()
        self.assertEqual(self.snapshot(self.archive), archive_before)
        self.assertEqual(self.snapshot(self.deduplicated), dedup_before)
        captured = self.source_listing()["captures"][0]["raw_record"]
        self.assertEqual(captured, self.product())
        self.assertEqual(captured["information"]["selected_variant"]["price"], "04.00")
        self.assertIn("chocolat noir; café", captured["information"]["body_html"])
        self.assertEqual(self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"]["value"], 200)
        self.assertNotEqual(self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"]["value"], 999)

    def test_every_listing_tracks_all_103_attributes_with_explicit_unknowns(self):
        report = self.prepare()
        product = self.rows()[0]
        self.assertEqual(len(product["attributes"]), 103)
        self.assertEqual(set(product["attributes"]), set(self.profile["attributes"]))
        unknown = product["attributes"]["packaging.materials"]
        self.assertEqual(unknown["status"], "unknown")
        self.assertIsNone(unknown["value"])
        self.assertEqual(unknown["evidence"], [])
        self.assertEqual(product["attributes"]["composition.nuts_presence"]["status"], "unknown")
        self.assertEqual(report["counts"]["tracked_attributes"], 103)
        self.assertFalse(report["release_ready"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_same_product_remains_unique_at_brand_and_retail_sellers(self):
        first = self.product("brand-listing", "montezumas")
        second = self.product("retail-listing", "chocolate-shop")
        third = self.product("unknown-listing", "unresolved-shop")
        self.prepare([first, second, third])
        rows = {row["listing_id"]: row for row in self.rows()}
        self.assertEqual(len(rows), 3)
        for listing, role in (("brand-listing", "brand"), ("retail-listing", "retail"), ("unknown-listing", "unknown")):
            self.assertEqual(rows[listing]["source_role"], role)
            self.assertEqual([row["listing_id"] for row in self.rows(role + "/products")], [listing])
        self.assertEqual(rows["brand-listing"]["brand"], rows["retail-listing"]["brand"])
        self.assertEqual(rows["retail-listing"]["retailer"], "The Chocolate Shop")
        self.assertNotEqual(rows["retail-listing"]["retailer"], rows["retail-listing"]["brand"])
        self.assertEqual(rows["retail-listing"]["attributes"]["identity.retailer"]["value"], "The Chocolate Shop")
        self.assertEqual(self.rows("model-inputs"), [])

    def test_rebuild_is_deterministic_and_manifest_hashes_outputs(self):
        self.prepare()
        before = self.snapshot(self.output)
        first_report = self.build()
        second_report = self.build()
        self.assertEqual(first_report, second_report)
        self.assertEqual(self.snapshot(self.output), before)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["source_manifest_sha256"], hashlib.sha256((self.deduplicated / "manifest.json").read_bytes()).hexdigest())
        for name, metadata in manifest["managed_files"].items():
            data = (self.output / name).read_bytes()
            self.assertEqual(metadata["byte_length"], len(data))
            self.assertEqual(metadata["sha256"], hashlib.sha256(data).hexdigest())

    def test_all_assertion_evidence_resolves_to_preserved_capture_values(self):
        self.prepare()
        captures = {capture["capture_id"]: capture for capture in self.source_listing()["captures"]}
        for assertion in self.rows("assertions"):
            for ref in assertion["evidence"]:
                self.assertIsNotNone(pointer_value(captures[ref["capture_id"]], ref["pointer"]))

    def test_conflicting_chocolate_type_keeps_evidence_and_selected_value_unknown(self):
        product = self.product()
        product["information"]["composition"] = {"chocolate_type": "Milk Chocolate"}
        self.prepare([product])
        attribute = self.rows()[0]["attributes"]["composition.chocolate_type"]
        self.assertEqual(attribute["status"], "conflict")
        self.assertIsNone(attribute["value"])
        self.assertGreaterEqual(len(attribute["evidence"]), 2)
        self.assertTrue(any(row["attribute"] == "composition.chocolate_type" and row["reason"] == "conflict"
                            for row in self.rows("review-queue")))

    def test_unmapped_structured_fields_remain_evidence_backed_review_items(self):
        product = self.product()
        product["information"]["composition"] = {"novel_source_claim": "Original unfamiliar claim: cacao azul"}
        self.prepare([product])
        row = self.rows()[0]
        unmapped = [item for item in row["unmapped_claims"] if item.get("attribute") == "composition.novel_source_claim"]
        self.assertEqual(len(unmapped), 1)
        self.assertEqual(unmapped[0]["value"], "Original unfamiliar claim: cacao azul")
        self.assertTrue(unmapped[0]["evidence"])
        ref = unmapped[0]["evidence"][0]
        capture = next(capture for capture in self.source_listing()["captures"] if capture["capture_id"] == ref["capture_id"])
        self.assertEqual(pointer_value(capture, ref["pointer"]), unmapped[0]["value"])

    def test_reviewed_attributes_use_aliases_and_yield_11_predictor_model_input(self):
        self.prepare()
        reviews = self.reviews()
        product_review = reviews["products"]["example"]
        product_review["attributes"]["composition.chocolate_type"]["value"] = "DARK CHOCOLATE"
        product_review["attributes"]["composition.cocoa_percentage"]["value"] = "70"
        report = self.build(reviews)
        self.assertEqual(report["counts"]["eligible_model_inputs"], 1)
        row = self.rows("model-inputs")[0]
        self.assertTrue(row["model_eligible"])
        self.assertEqual(len(row["predictors"]), 11)
        self.assertEqual(row["predictors"]["composition.chocolate_type"], "dark")
        self.assertEqual(row["predictors"]["composition.cocoa_percentage"], 70)
        self.assertEqual(row["target"]["regular_price_per_100g_gbp"], 2)
        self.assertAlmostEqual(row["target"]["log_regular_price_per_100g_gbp"], math.log(2))
        self.assertEqual(transform_rows([row], fit_encoder([row], self.design))["X"], [[1.0]])
        self.assertFalse(report["release_ready"])

    def test_price_review_alone_does_not_establish_feature_model_eligibility(self):
        self.prepare()
        reviews = self.reviews()
        del reviews["products"]["example"]["attributes"]["dietary.vegan_claim"]
        self.build(reviews)
        self.assertEqual(self.rows("model-inputs"), [])
        self.assertIn("model_predictor_unreviewed:dietary.vegan_claim", self.rows("training-candidates")[0]["exclusion_reasons"])

    def test_minimum_and_component_cocoa_cannot_supply_exact_whole_product_predictor(self):
        self.prepare()
        for scope, qualifier in (("product", "minimum"), ("ingredient", "exact"), ("product", "source_stated")):
            reviews = self.reviews()
            review = reviews["products"]["example"]["attributes"]["composition.cocoa_percentage"]
            review.update(scope=scope, qualifier=qualifier)
            with self.subTest(scope=scope, qualifier=qualifier):
                self.build(reviews)
                self.assertEqual(self.rows("model-inputs"), [])
                self.assertIn("cocoa_percentage_basis_unsupported", self.rows("training-candidates")[0]["exclusion_reasons"])

    def test_conditional_or_ingredient_claims_do_not_become_product_indicators(self):
        self.prepare()
        for name, scope, qualifier in (("dietary.vegan_claim", "product", "conditional"),
                                       ("certifications.organic_claim", "ingredient", "exact")):
            reviews = self.reviews()
            review = reviews["products"]["example"]["attributes"][name]
            review.update(value="present", scope=scope, qualifier=qualifier)
            with self.subTest(name=name, scope=scope, qualifier=qualifier):
                self.build(reviews)
                self.assertEqual(self.rows("model-inputs"), [])
                self.assertIn("model_predictor_basis_unsupported:" + name,
                              self.rows("training-candidates")[0]["exclusion_reasons"])

    def test_unknown_reviewed_feature_is_retained_and_remains_excluded(self):
        self.prepare()
        reviews = self.reviews()
        review = reviews["products"]["example"]["attributes"]["dietary.vegan_claim"]
        review.update(status="unknown", value=None)
        self.build(reviews)
        attribute = self.rows()[0]["attributes"]["dietary.vegan_claim"]
        self.assertEqual(attribute["status"], "unknown")
        self.assertEqual(attribute["review_status"], "reviewed")
        self.assertIsNone(attribute["value"])
        self.assertIsNone(self.rows("training-candidates")[0]["predictors"]["dietary.vegan_claim"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_shipping_grams_do_not_supply_missing_edible_mass(self):
        product = self.product()
        product["identity"]["name"] = "Fixture Dark Chocolate Bar"
        del product["information"]["review_fixture"]["quantity.total_edible_weight_g"]
        self.prepare([product])
        self.assertEqual(self.rows()[0]["attributes"]["quantity.total_edible_weight_g"]["status"], "unknown")
        self.assertIsNone(self.rows("prices")[0]["total_edible_weight_g"])
        self.assertIsNone(self.rows("prices")[0]["displayed_price_per_100g_gbp"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_latest_quantity_review_cannot_repair_unreviewed_historical_mass(self):
        self.collect([self.product(weight=200, price="4.00", observed_at="2026-10-02T07:00:00Z")])
        self.collect([self.product(weight=100, price="3.00", observed_at="2026-10-03T07:00:00Z")])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        self.build()
        self.build(self.reviews())
        prices = {row["observed_at"]: row for row in self.rows("prices")}
        old = prices["2026-10-02T07:00:00Z"]
        latest = prices["2026-10-03T07:00:00Z"]
        self.assertEqual(old["total_edible_weight_g"], 200)
        self.assertFalse(old["model_eligible"])
        self.assertIn("observation_edible_quantity_unreviewed", old["exclusion_reasons"])
        self.assertTrue(latest["model_eligible"])
        self.assertEqual(latest["regular_price_per_100g_gbp"], 3)
        self.assertEqual(len(self.rows("model-inputs")), 1)

    def test_reviewed_latest_features_do_not_replace_historical_feature_basis(self):
        first = self.product(weight=200, price="4.00", observed_at="2026-10-02T07:00:00Z")
        latest = self.product(weight=200, price="5.00", observed_at="2026-10-03T07:00:00Z")
        latest["information"]["review_fixture"]["composition.cocoa_percentage"] = 80
        self.collect([first])
        self.collect([latest])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        self.build()
        reviews = self.reviews()
        quantity = reviews["products"]["example"]["attributes"]["quantity.total_edible_weight_g"]
        quantity["evidence"] = [
            {"capture_id": capture["capture_id"], "pointer": "/raw_record/information/review_fixture/quantity.total_edible_weight_g"}
            for capture in self.source_listing()["captures"]
        ]
        self.build(reviews)
        prices = {row["observed_at"]: row for row in self.rows("prices")}
        old = prices["2026-10-02T07:00:00Z"]
        self.assertEqual(old["quantity_status"], "reviewed")
        self.assertFalse(old["model_eligible"])
        self.assertIn("model_predictor_observation_basis_unreviewed:composition.cocoa_percentage", old["exclusion_reasons"])
        self.assertTrue(prices["2026-10-03T07:00:00Z"]["model_eligible"])
        self.assertEqual(self.rows("model-inputs")[0]["predictors"]["composition.cocoa_percentage"], 80)

    def test_corrupt_deduplicated_table_and_wrong_layer_are_rejected_before_writes(self):
        self.prepare()
        target = self.deduplicated / "products.jsonl"
        original = target.read_bytes()
        target.write_bytes(original + b"\n")
        output = self.base / "rejected-output"
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.build(output=output)
        self.assertFalse(output.exists())
        target.write_bytes(original)
        manifest_path = self.deduplicated / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["manifest_format_version"] = "category-research-raw-1"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "deduplicated raw snapshot"):
            self.build(output=output)
        self.assertFalse(output.exists())

    def test_invalid_review_ids_evidence_values_and_context_are_rejected(self):
        self.prepare()
        originals = self.reviews()
        malformed = []
        reviews = deepcopy(originals)
        reviews["products"]["absent-listing"] = reviews["products"].pop("example")
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["evidence"][0]["capture_id"] = "another-listing-capture"
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["attributes"]["composition.chocolate_type"]["evidence"][0]["pointer"] = "/missing/evidence"
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["attributes"]["composition.cocoa_percentage"]["value"] = 101
        malformed.append(reviews)
        reviews = deepcopy(originals)
        next(iter(reviews["prices"].values()))["observed_at"] = "2026-10-03T07:00:00"
        malformed.append(reviews)
        reviews = deepcopy(originals)
        next(iter(reviews["prices"].values()))["available"] = "true"
        malformed.append(reviews)
        for index, reviews in enumerate(malformed):
            output = self.base / ("invalid-review-" + str(index))
            with self.subTest(case=index), self.assertRaises(ValueError):
                self.build(reviews, output=output)
            self.assertFalse(output.exists())

    def test_output_cannot_overwrite_or_contain_deduplicated_layer(self):
        self.prepare()
        for output in (self.deduplicated, self.deduplicated / "standardized", self.base):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "overlap"):
                self.build(output=output)


if __name__ == "__main__":
    unittest.main()
