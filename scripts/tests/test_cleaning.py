"""Exercise the chocolate interpretation boundary with preserved archive fixtures."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "plugins/category-research"))

from category_research import import_document
from chocolate_cleanup.core import build_dataset
from chocolate_cleanup.core import pointer_value


class ChocolateCleaningTests(unittest.TestCase):
    def test_review_pointers_use_portable_array_indexes_and_escapes(self):
        self.assertEqual(pointer_value({"values": ["first", "last"]}, "/values/1"), "last")
        for pointer in ("/values/-1", "/values/01", "/invalid~2escape"):
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                pointer_value({"values": ["first", "last"]}, pointer)

    def test_profile_types_match_emitted_feature_assertions(self):
        self.collect([self.product()])
        self.build()
        profile = json.loads((self.output / "profile.json").read_text())
        for row in self.rows("features"):
            self.assertEqual(profile["feature_types"][row["name"]], row["value_type"])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = self.base / "collections"
        self.output = self.base / "derived"

    def product(self, identifier="example", **changes):
        record = {
            "product_id": identifier,
            "source_key": "example-shop",
            "source_url": "https://example.test/products/" + identifier,
            "identity": {
                "name": "Example Dark Chocolate Bar 200g",
                "brand": "Example",
                "source_product_id": identifier,
                "source_variant_id": identifier + "-variant",
            },
            "information": {
                "selected_variant": {
                    "id": identifier + "-variant", "price": "4.00", "grams": 999,
                    "compare_at_price": None, "available": True, "title": "Default Title",
                },
                "catalogue_retrieval_currency": "GBP",
                "catalogue_collected_at": "2026-10-03T07:00:00Z",
                "body_html": "<p>Ingredients: cocoa butter, sugar.</p><p>May contain nuts.</p>",
                "product_type": "Bar",
            },
            "source_artifacts": [{
                "kind": "page", "content": "<p>Original wording: chocolat noir; café.</p>\n",
                "url": "https://example.test/products/" + identifier,
            }],
            "images": [],
        }
        record.update(changes)
        return record

    def collect(self, products):
        return import_document({
            "contract_version": "1",
            "study": {"study_id": "chocolate-test", "category": "chocolate", "market": "uk"},
            "products": products,
        }, self.archive, workers=1)

    def rows(self, name):
        return [json.loads(line) for line in (self.output / (name + ".jsonl")).read_text(encoding="utf-8").splitlines()]

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()}

    def build(self, reviews=None):
        return build_dataset(self.archive, self.output, reviews=reviews)

    def feature(self, name, listing_id=None):
        rows = [row for row in self.rows("features") if row["name"] == name
                and (listing_id is None or row["listing_id"] == listing_id)]
        self.assertEqual(len(rows), 1, name)
        return rows[0]

    def pointer_value(self, document, pointer):
        self.assertTrue(pointer.startswith("/"), pointer)
        value = document
        for token in pointer[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            value = value[int(token)] if isinstance(value, list) else value[token]
        return value

    def capture_lookup(self):
        captures = {}
        for path in self.archive.rglob("product.json"):
            for capture in json.loads(path.read_text(encoding="utf-8"))["captures"]:
                captures[capture["capture_id"]] = capture
        return captures

    def write_reviews(self, document):
        path = self.base / "reviews.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def reviewed_document(self):
        product = self.rows("products")[0]
        price = self.rows("prices")[0]
        capture_id = next(iter(self.capture_lookup()))
        product_evidence = [{"capture_id": capture_id, "pointer": "/raw_record/identity/name"}]
        price_evidence = [{"capture_id": capture_id, "pointer": "/raw_record/information/selected_variant/price"}]
        return {
            "review_format_version": "chocolate-reviews-1",
            "products": {product["listing_id"]: {
                "variant_id": "reviewed-example-200g", "family_id": "reviewed-example",
                "in_scope": True, "comparable_group": "bar",
                "total_edible_weight_g": 200, "pack_count": 1,
                "reviewed_by": "Fixture reviewer", "reason": "Reviewed selling unit and product identity.",
                "evidence": product_evidence,
            }},
            "prices": {price["price_id"]: {
                "regular_price": 4, "currency": "GBP", "tax_basis": "consumer_tax_included",
                "observed_at": "2026-10-03T07:00:00Z", "reviewed_by": "Fixture reviewer",
                "reason": "Reviewed a regular consumer price at the recorded time.",
                "evidence": price_evidence,
            }},
        }

    def test_preserves_archive_bytes_and_builds_deterministic_versioned_outputs(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        first_report = self.build()
        first = self.snapshot(self.output)
        expected = {"products.jsonl", "features.jsonl", "prices.jsonl", "model-inputs.jsonl",
                    "review-queue.jsonl", "capture-evidence.jsonl", "artifacts.jsonl",
                    "quality-report.json", "manifest.json", "profile.json", "study.json"}
        self.assertTrue(expected.issubset(first))
        self.assertEqual(self.snapshot(self.archive), original)
        second_report = self.build()
        self.assertEqual(second_report, first_report)
        self.assertEqual(self.snapshot(self.output), first)
        self.assertEqual(self.snapshot(self.archive), original)
        self.assertEqual(first_report["counts"]["source_listings"], 1)

    def test_rejects_output_overlapping_raw_archive(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "derived", self.base):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    build_dataset(self.archive, output)
        self.assertEqual(self.snapshot(self.archive), original)

    def test_normalizes_explicit_edible_weight_and_keeps_shipping_weight_separate(self):
        self.collect([self.product()])
        self.build()
        product = self.rows("products")[0]
        price = self.rows("prices")[0]
        self.assertEqual(product["total_edible_weight_g"], 200)
        self.assertEqual(price["total_edible_weight_g"], 200)
        self.assertEqual(Decimal(str(price["displayed_price"])), Decimal("4.00"))
        self.assertEqual(price["displayed_price_per_100g"], 2)
        self.assertNotEqual(product["total_edible_weight_g"], 999)
        self.assertFalse(price["model_eligible"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_shipping_grams_do_not_supply_missing_edible_quantity(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate Bar"
        self.collect([product])
        self.build()
        self.assertIsNone(self.rows("products")[0]["total_edible_weight_g"])
        price = self.rows("prices")[0]
        self.assertIsNone(price["displayed_price_per_100g"])
        self.assertFalse(price["model_eligible"])
        self.assertTrue(price["exclusion_reasons"])

    def test_compare_at_price_is_retained_without_inventing_a_regular_price(self):
        product = self.product()
        product["information"]["selected_variant"]["compare_at_price"] = "5.00"
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        self.assertEqual(Decimal(str(price["displayed_price"])), Decimal("4.00"))
        self.assertEqual(Decimal(str(price["reference_price"])), Decimal("5.00"))
        self.assertIsNone(price["regular_price"])
        self.assertIsNone(price["regular_price_per_100g"])
        self.assertFalse(price["model_eligible"])

    def test_missing_certification_is_unknown_and_allergen_warning_is_not_an_ingredient(self):
        self.collect([self.product()])
        self.build()
        for feature in ("fairtrade_claim", "organic_claim", "nuts_as_ingredient"):
            self.assertEqual(self.feature(feature)["status"], "unknown")
            self.assertIn(self.feature(feature)["value"], (None, "unknown"))
        self.assertIn(self.feature("may_contain_nuts")["value"], (True, "present"))
        self.assertIn("cocoa butter, sugar", self.feature("ingredients_text")["value"])
        self.assertIn("May contain nuts", self.feature("allergen_text")["value"])

    def test_repeated_identical_imports_deduplicate_prices_but_keep_both_evidence_references(self):
        product = self.product()
        first = self.collect([product])
        second = self.collect([deepcopy(product)])
        self.build()
        self.assertEqual(len(self.rows("products")), 1)
        prices = self.rows("prices")
        self.assertEqual(len(prices), 1)
        self.assertEqual({reference["capture_id"] for reference in prices[0]["evidence"]},
                         {first["products"][0]["capture_id"], second["products"][0]["capture_id"]})

    def test_historical_prices_use_the_quantity_in_their_own_capture(self):
        first = self.product()
        first["identity"]["name"] = "Example Dark Chocolate Bar 100g"
        first["information"]["catalogue_collected_at"] = "2026-10-02T07:00:00Z"
        self.collect([first])
        second = self.product()
        second["information"]["catalogue_collected_at"] = "2026-10-03T07:00:00Z"
        self.collect([second])
        self.build()
        prices = sorted(self.rows("prices"), key=lambda row: row["observed_at"])
        self.assertEqual(len(prices), 2)
        self.assertEqual([(row["total_edible_weight_g"], row["displayed_price_per_100g"]) for row in prices],
                         [(100, 4), (200, 2)])

    def test_changed_quantity_at_the_same_time_does_not_deduplicate_distinct_offers(self):
        first = self.product()
        first["identity"]["name"] = "Example Dark Chocolate Bar 100g"
        self.collect([first])
        self.collect([self.product()])
        self.build()
        prices = self.rows("prices")
        self.assertEqual(len(prices), 2)
        self.assertEqual({row["total_edible_weight_g"] for row in prices}, {100, 200})

    def test_zero_compare_at_is_not_a_regular_price_or_a_discount_reference(self):
        product = self.product()
        product["information"]["selected_variant"]["compare_at_price"] = "0.00"
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        self.assertIsNone(price["regular_price"])
        self.assertIsNone(price["reference_price"])

    def test_waitrose_offer_preserves_was_price_as_reference_and_uses_edible_weight(self):
        product = self.product("waitrose")
        product["source_key"] = "waitrose"
        product["source_url"] = "https://www.waitrose.com/ecom/products/example/123"
        product["identity"]["name"] = "Example Chocolate Bar 105g"
        product["information"] = {
            "source_weight_text": "105g", "source_price_currency": "GBP",
            "source_collected_at": "2026-10-03T07:00:00Z",
            "catalogue_archived_at": "2026-10-03T08:00:00Z",
            "catalogue_text_context": "Example Chocolate Bar\n105g\nSave 45p.Was £2.10\nItem price\n£1.65\nPrice per unit\n£15.72/kg\nAdd\n",
        }
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        self.assertEqual(Decimal(str(price["displayed_price"])), Decimal("1.65"))
        self.assertEqual(Decimal(str(price["reference_price"])), Decimal("2.10"))
        self.assertIsNone(price["regular_price"])
        self.assertEqual(price["total_edible_weight_g"], 105)
        self.assertAlmostEqual(price["displayed_price_per_100g"], 1.65 / 105 * 100)
        self.assertFalse(price["model_eligible"])

    def test_nonpositive_price_and_invalid_time_are_retained_for_review(self):
        product = self.product()
        product["information"]["selected_variant"]["price"] = "-4.00"
        product["information"]["catalogue_collected_at"] = "not-a-date"
        self.collect([product])
        report = self.build()
        self.assertEqual(report["counts"]["eligible_price_observations"], 0)
        price = self.rows("prices")[0]
        self.assertFalse(price["model_eligible"])
        self.assertTrue(price["exclusion_reasons"])
        self.assertTrue(self.rows("review-queue"))
        self.assertEqual(self.rows("model-inputs"), [])

    def test_conflicting_current_edible_weights_require_quantity_review(self):
        product = self.product()
        product["information"]["selected_variant"]["title"] = "100g"
        self.collect([product])
        self.build()
        product_row = self.rows("products")[0]
        self.assertIsNone(product_row["total_edible_weight_g"])
        self.assertEqual(product_row["quantity_status"], "conflict")
        self.assertIsNone(self.rows("prices")[0]["displayed_price_per_100g"])
        self.assertTrue(any("conflicting_edible_quantities" in row["reasons"]
                            for row in self.rows("review-queue")))

    def test_extreme_price_strings_never_produce_nonfinite_analytical_values(self):
        products = []
        for index, price in enumerate(("1e309", "1" + "0" * 400)):
            product = self.product("extreme-" + str(index))
            product["information"]["selected_variant"]["price"] = price
            products.append(product)
        self.collect(products)
        report = self.build()
        self.assertEqual(report["counts"]["eligible_price_observations"], 0)
        self.assertEqual(len(self.rows("prices")), 2)
        self.assertTrue(all(row["displayed_price_per_100g"] is None for row in self.rows("prices")))
        for content in self.snapshot(self.output).values():
            self.assertNotIn(b"Infinity", content)
            self.assertNotIn(b"NaN", content)

    def test_inconsistent_history_is_reported_without_cleaning_the_damaged_listing(self):
        collected = self.collect([self.product()])
        path = self.archive / collected["products"][0]["history_path"]
        history = json.loads(path.read_text(encoding="utf-8"))
        history["raw_record"]["information"]["selected_variant"]["price"] = "5.00"
        path.write_text(json.dumps(history), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertTrue(report["archive_errors"])
        self.assertEqual(report["counts"]["source_listings"], 0)
        self.assertEqual(self.rows("products"), [])
        self.assertEqual(self.snapshot(self.archive), original)

    def test_unsupported_legacy_records_are_reported_without_rewriting_them(self):
        folder = self.archive / "chocolate/uk/products/legacy"
        folder.mkdir(parents=True)
        (folder / "product.json").write_text(json.dumps({
            "product_id": "legacy", "name": "Legacy chocolate", "information": {"price": "4.00"},
        }), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertTrue(report["unsupported_records"])
        self.assertEqual(self.rows("products"), [])
        self.assertEqual(self.rows("prices"), [])
        self.assertEqual(self.snapshot(self.archive), original)

    def test_evidence_json_pointers_resolve_to_preserved_capture_values(self):
        self.collect([self.product()])
        self.build()
        captures = self.capture_lookup()
        for name in ("products", "features", "prices"):
            for row in self.rows(name):
                for reference in row.get("evidence", []):
                    with self.subTest(table=name, reference=reference):
                        self.assertIn(reference["capture_id"], captures)
                        self.pointer_value(captures[reference["capture_id"]], reference["pointer"])
        self.assertTrue(self.rows("prices")[0]["evidence"])
        self.assertTrue(self.feature("ingredients_text")["evidence"])

    def test_normalized_evidence_tables_join_rows_to_capture_history_and_artifact_metadata(self):
        self.collect([self.product()])
        report = self.build()
        capture_rows = {row["capture_id"]: row for row in self.rows("capture-evidence")}
        artifacts = {row["artifact_id"]: row for row in self.rows("artifacts")}
        self.assertEqual(len(capture_rows), 1)
        self.assertEqual(len(artifacts), 1)
        for table in ("products", "features", "prices"):
            for row in self.rows(table):
                for reference in row.get("evidence", []) + row.get("quantity_evidence", []):
                    with self.subTest(table=table, capture_id=reference["capture_id"]):
                        self.assertEqual(reference["artifact_metadata_table"], "capture-evidence.jsonl")
                        self.assertNotIn("artifacts", reference)
                        self.assertNotIn("raw_value", reference)
                        capture = capture_rows[reference["capture_id"]]
                        self.assertEqual(capture["listing_id"], reference["listing_id"])
                        self.assertEqual(capture["source_listing_id"], reference["source_listing_id"])
                        self.assertEqual(capture["history_path"], reference["history_path"])
                        history = json.loads((self.archive / capture["history_path"]).read_text(encoding="utf-8"))
                        self.assertEqual(history["capture_id"], capture["capture_id"])
                        self.pointer_value(history, reference["pointer"])
                        self.assertTrue(capture["artifact_ids"])
                        for artifact_id in capture["artifact_ids"]:
                            artifact = artifacts[artifact_id]
                            self.assertEqual(artifact["dataset_version"], report["dataset_version"])
                            self.assertTrue(artifact["available_locally"])
                            original = next(item for item in history["source_artifacts"]
                                            if item["archive_relative_path"] == artifact["archive_relative_path"])
                            self.assertEqual(artifact["sha256"], original["sha256"])

    def test_reference_only_image_without_local_path_has_deterministic_evidence_metadata(self):
        product = self.product()
        image_url = "https://example.test/images/front.png"
        product["images"] = [{"url": image_url, "alt": "Original front-pack reference"}]
        self.collect([product])
        original = self.snapshot(self.archive)
        first = self.build()
        outputs = self.snapshot(self.output)
        image = next(row for row in self.rows("artifacts") if row["artifact_group"] == "images")
        self.assertEqual(image["url"], image_url)
        self.assertEqual(image["status"], "reference_only")
        self.assertIsNone(image["archive_relative_path"])
        self.assertFalse(image["available_locally"])
        self.assertEqual(self.build(), first)
        self.assertEqual(self.snapshot(self.output), outputs)
        self.assertEqual(self.snapshot(self.archive), original)

    def test_optional_identity_and_arbitrary_source_information_do_not_abort_the_build(self):
        minimal = {"product_id": "minimal", "information": "Original source wording: chocolat."}
        self.collect([minimal, self.product("supported")])
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(report["archive_errors"], [])
        products = {row["listing_id"]: row for row in self.rows("products")}
        self.assertEqual(set(products), {"minimal", "supported"})
        self.assertIsNone(products["minimal"]["name"])
        self.assertIsNone(products["minimal"]["total_edible_weight_g"])
        self.assertEqual({row["listing_id"] for row in self.rows("prices")}, {"supported"})
        self.assertEqual(self.snapshot(self.archive), original)

    def test_malformed_nested_source_sections_are_reported_while_other_listings_continue(self):
        malformed = self.product("malformed")
        malformed["information"]["product_page_information"] = {"source_sections": 42}
        self.collect([malformed, self.product("supported")])
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertTrue(any(error["listing_id"] == "malformed" for error in report["archive_errors"]))
        self.assertEqual({row["listing_id"] for row in self.rows("prices")}, {"supported"})
        self.assertTrue(any(row["listing_id"] == "malformed" for row in self.rows("review-queue")))
        self.assertEqual(self.snapshot(self.archive), original)

    def test_a_tax_only_price_review_does_not_complete_the_regular_price_basis(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        review = next(iter(reviews["prices"].values()))
        for field in ("regular_price", "currency", "observed_at"):
            del review[field]
        report = self.build(self.write_reviews(reviews))
        self.assertEqual(report["counts"]["eligible_price_observations"], 0)
        price = self.rows("prices")[0]
        self.assertEqual(price["tax_basis"], "consumer_tax_included")
        self.assertIn("price_basis_review_incomplete", price["exclusion_reasons"])
        self.assertFalse(price["model_eligible"])
        self.assertEqual(self.rows("model-inputs"), [])

    def test_only_reviewed_identity_scope_quantity_and_price_basis_enter_model_inputs(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        original = self.snapshot(self.archive)
        report = self.build(self.write_reviews(reviews))
        self.assertEqual(report["counts"]["eligible_price_observations"], 1)
        self.assertFalse(report["release_ready"])
        price = self.rows("prices")[0]
        self.assertTrue(price["model_eligible"], price["exclusion_reasons"])
        self.assertEqual(price["regular_price_per_100g"], 2)
        self.assertEqual(price["variant_id"], "reviewed-example-200g")
        self.assertEqual(price["family_id"], "reviewed-example")
        self.assertEqual(len(self.rows("model-inputs")), 1)
        self.assertEqual(self.snapshot(self.archive), original)
        reviews["products"][next(iter(reviews["products"]))]["in_scope"] = False
        report = self.build(self.write_reviews(reviews))
        self.assertEqual(report["counts"]["eligible_price_observations"], 0)
        self.assertEqual(self.rows("model-inputs"), [])

    def test_review_rejects_unknown_identity_and_nonresolving_evidence(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        cases = []
        unknown = deepcopy(reviews)
        unknown["products"]["unknown-listing"] = unknown["products"].pop(next(iter(unknown["products"])))
        cases.append(unknown)
        unknown_price = deepcopy(reviews)
        unknown_price["prices"]["unknown-price"] = unknown_price["prices"].pop(next(iter(unknown_price["prices"])))
        cases.append(unknown_price)
        enormous_price = deepcopy(reviews)
        next(iter(enormous_price["prices"].values()))["regular_price"] = "1e309"
        cases.append(enormous_price)
        wrong_pointer = deepcopy(reviews)
        next(iter(wrong_pointer["prices"].values()))["evidence"][0]["pointer"] = "/missing-field"
        cases.append(wrong_pointer)
        naive_time = deepcopy(reviews)
        next(iter(naive_time["prices"].values()))["observed_at"] = "2026-10-03T07:00:00"
        cases.append(naive_time)
        original_outputs = self.snapshot(self.output)
        for document in cases:
            with self.subTest(reviews=document):
                with self.assertRaises(ValueError):
                    self.build(self.write_reviews(document))
                self.assertEqual(self.snapshot(self.output), original_outputs)

    def test_reviews_reject_evidence_from_a_different_source_listing(self):
        self.collect([self.product("first")])
        self.build()
        reviews = self.reviewed_document()
        self.collect([self.product("second")])
        self.build()
        foreign_capture = next(capture["capture_id"] for capture in self.capture_lookup().values()
                               if capture["raw_record"]["product_id"] == "second")
        for entity in ("products", "prices"):
            wrong = deepcopy(reviews)
            next(iter(wrong[entity].values()))["evidence"][0]["capture_id"] = foreign_capture
            with self.subTest(entity=entity):
                with self.assertRaises(ValueError):
                    self.build(self.write_reviews(wrong))

    def test_exact_duplicate_listings_within_one_seller_share_rows_and_keep_alias_evidence(self):
        original = self.product("first-copy")
        alias = deepcopy(original)
        alias["product_id"] = "second-copy"
        first = self.collect([original])
        second = self.collect([alias])
        self.build()
        products = self.rows("products")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["listing_id"], "first-copy")
        self.assertEqual(set(products[0]["source_listing_ids"]), {"first-copy", "second-copy"})
        self.assertEqual(len(self.rows("prices")), 1)
        self.assertEqual({reference["capture_id"] for reference in self.rows("prices")[0]["evidence"]},
                         {first["products"][0]["capture_id"], second["products"][0]["capture_id"]})

    def test_brand_and_retail_sources_are_partitioned_without_using_product_brand_as_seller(self):
        brand = self.product("brand-shop")
        brand["source_key"] = "montezumas"
        brand["identity"]["brand"] = "Montezuma's"
        retailer = self.product("retail-shop")
        retailer["source_key"] = "chocolate-shop"
        retailer["identity"]["brand"] = "Chocolate Tree"
        unknown = self.product("unknown-shop")
        self.collect([brand, retailer, unknown])
        self.build()
        products = {row["source_key"]: row for row in self.rows("products")}
        self.assertEqual(products["montezumas"]["source_role"], "brand")
        self.assertEqual(products["chocolate-shop"]["source_role"], "retail")
        self.assertEqual(products["example-shop"]["source_role"], "unknown")
        self.assertEqual(products["chocolate-shop"]["brand"], "Chocolate Tree")
        self.assertEqual(products["chocolate-shop"]["retailer"], "The Chocolate Shop")
        for source_role, source_key in (("brand", "montezumas"), ("retail", "chocolate-shop"),
                                        ("unknown", "example-shop")):
            with self.subTest(source_role=source_role):
                product_rows = self.rows(source_role + "/products")
                price_rows = self.rows(source_role + "/prices")
                self.assertEqual(len(product_rows), 1)
                self.assertEqual(len(price_rows), 1)
                self.assertEqual(product_rows[0]["source_key"], source_key)
                self.assertEqual(price_rows[0]["source_role"], source_role)

    def test_ambiguous_count_and_mass_require_quantity_review(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate 3 bars 150g"
        self.collect([product])
        self.build()
        self.assertIsNone(self.rows("products")[0]["total_edible_weight_g"])
        self.assertIsNone(self.rows("prices")[0]["displayed_price_per_100g"])
        self.assertTrue(self.rows("review-queue"))

    def test_explicit_multipack_sums_edible_mass(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate Bars 3 x 150g"
        self.collect([product])
        self.build()
        self.assertEqual(self.rows("products")[0]["total_edible_weight_g"], 450)
        self.assertEqual(self.rows("products")[0]["pack_count"], 3)
        self.assertEqual(self.rows("prices")[0]["displayed_price_per_100g"], round(4 / 450 * 100, 8))

    def test_two_retailer_listings_stay_separate_until_reviewed(self):
        first = self.product("first-retailer")
        second = self.product("second-retailer")
        second["source_key"] = "second-shop"
        second["source_url"] = "https://second.test/products/example"
        second["identity"] = deepcopy(first["identity"])
        self.collect([first, second])
        self.build()
        products = self.rows("products")
        self.assertEqual(len(products), 2)
        self.assertEqual(len({row["listing_id"] for row in products}), 2)
        self.assertEqual(len({row["variant_id"] for row in products}), 2)
        self.assertTrue(all(row["family_id"] is None for row in products))
        self.assertTrue(all(row["identity_status"] == "unresolved_source_listing" for row in products))
        self.assertEqual(self.rows("model-inputs"), [])


if __name__ == "__main__":
    unittest.main()
