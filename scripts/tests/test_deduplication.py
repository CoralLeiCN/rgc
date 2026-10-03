"""Verify that raw deduplication preserves evidence and seller boundaries."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "plugins/category-research"))

from category_research import import_document
from chocolate_cleanup.deduplication import build_deduplicated_dataset


class ChocolateDeduplicationTests(unittest.TestCase):
    def test_pending_import_and_empty_archive_have_different_versions(self):
        (self.archive / "chocolate/uk/products").mkdir(parents=True)
        empty = self.build()
        self.collect([self.product()])
        folder = self.archive / "chocolate/uk/products/example"
        (folder / ".import.lock").touch()
        pending = self.build()
        self.assertNotEqual(empty["dataset_version"], pending["dataset_version"])
        self.assertEqual(pending["status"], "partial")
        self.assertEqual(pending["counts"]["source_listings"], 0)

    def test_invalid_json_remains_hashed_and_reported(self):
        folder = self.archive / "chocolate/uk/products/invalid"
        folder.mkdir(parents=True)
        path = folder / "product.json"
        original = b'{"unfinished":'
        path.write_bytes(original)
        report = self.build()
        self.assertEqual(report["counts"]["archive_errors"], 1)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["inputs"][0]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(path.read_bytes(), original)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = self.base / "collections"
        self.output = self.base / "deduplicated"

    def product(self, listing="example", source="example-shop", hostname="example.test"):
        return {
            "product_id": listing,
            "source_key": source,
            "source_url": "https://" + hostname + "/products/shared-product",
            "identity": {
                "name": "Original chocolat noir 200g",
                "brand": "Example Chocolate Maker",
                "source_product_id": "shared-product",
                "source_variant_id": "shared-variant",
                "gtin": "0123456789012",
            },
            "information": {
                "selected_variant": {
                    "id": "shared-variant", "price": "04.00", "grams": 999,
                    "compare_at_price": "5.00", "available": True,
                    "title": "Default Title",
                },
                "body_html": "<p>Ingrédients: chocolat noir; café.</p>\n",
                "catalogue_retrieval_currency": "GBP",
                "catalogue_collected_at": "2026-10-03T07:00:00Z",
                "arbitrary_source_fields": {
                    "preserve_null": None, "preserve_list": ["é", 0, False],
                    "uninterpreted_mass": "not a weight",
                },
            },
            "source_artifacts": [{
                "kind": "page", "content": "Original wording: chocolat noir; café.\n",
                "url": "https://" + hostname + "/products/shared-product",
            }],
            "images": [{"url": "https://" + hostname + "/image.png"}],
        }

    def collect(self, products):
        return import_document({
            "contract_version": "1",
            "study": {"study_id": "chocolate-dedup-test", "category": "chocolate", "market": "uk"},
            "products": products,
        }, self.archive, workers=1)

    def build(self):
        return build_deduplicated_dataset(self.archive, self.output)

    def rows(self, name="products"):
        return [json.loads(line) for line in
                (self.output / (name + ".jsonl")).read_text(encoding="utf-8").splitlines()]

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()}

    def captures(self):
        return {capture["capture_id"]: capture
                for path in self.archive.rglob("product.json")
                for capture in json.loads(path.read_text(encoding="utf-8"))["captures"]}

    def test_raw_archive_and_original_capture_values_remain_unchanged(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        original_captures = self.captures()
        self.build()
        self.assertEqual(self.snapshot(self.archive), original)
        row = self.rows()[0]
        self.assertEqual({capture["capture_id"]: capture for capture in row["captures"]},
                         original_captures)
        raw = row["captures"][0]["raw_record"]
        self.assertEqual(raw, self.product())
        self.assertEqual(raw["information"]["selected_variant"]["price"], "04.00")
        self.assertEqual(raw["information"]["selected_variant"]["grams"], 999)
        for field in ("total_edible_weight_g", "displayed_price", "displayed_price_per_100g",
                      "model_eligible", "comparable_group", "features"):
            self.assertNotIn(field, row)
        for table in ("prices.jsonl", "features.jsonl", "model-inputs.jsonl"):
            self.assertFalse((self.output / table).exists())

    def test_aliases_with_exact_seller_product_and_variant_merge_all_captures(self):
        first = self.product("first-copy")
        self.collect([first])
        self.collect([deepcopy(first)])
        alias = self.product("second-copy")
        alias["information"]["selected_variant"]["price"] = "03.50"
        self.collect([alias])
        original_captures = self.captures()
        report = self.build()
        self.assertEqual(len(self.rows()), 1)
        row = self.rows()[0]
        self.assertEqual(row["listing_id"], "first-copy")
        self.assertEqual(row["source_listing_ids"], ["first-copy", "second-copy"])
        self.assertEqual({capture["capture_id"]: capture for capture in row["captures"]},
                         original_captures)
        self.assertEqual(len(row["captures"]), 3)
        self.assertIn(row["latest_capture_id"], original_captures)
        self.assertEqual(report["counts"]["source_listings"], 1)
        self.assertEqual({(alias["source_listing_id"], alias["listing_id"])
                          for alias in self.rows("listing-aliases")},
                         {("first-copy", "first-copy"), ("second-copy", "first-copy")})

    def test_products_at_different_sources_or_hostnames_remain_unique(self):
        products = [
            self.product("first-shop", source="chocolate-shop"),
            self.product("second-shop", source="waitrose"),
            self.product("other-host", source="chocolate-shop", hostname="other.test"),
        ]
        self.collect(products)
        self.build()
        self.assertEqual({row["listing_id"] for row in self.rows()},
                         {product["product_id"] for product in products})
        self.assertTrue(all(len(row["source_listing_ids"]) == 1 for row in self.rows()))

    def test_distinct_variants_at_the_same_seller_remain_unique(self):
        first = self.product("first-variant")
        second = self.product("second-variant")
        second["identity"]["source_variant_id"] = "different-variant"
        second["information"]["selected_variant"]["id"] = "different-variant"
        self.collect([first, second])
        self.build()
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual({row["source_variant_id"] for row in self.rows()},
                         {"shared-variant", "different-variant"})

    def test_missing_seller_or_product_identifiers_do_not_merge_similar_products(self):
        products = []
        for field in ("source_product_id", "source_key", "source_url"):
            for index in range(2):
                product = self.product(field + "-" + str(index))
                if field == "source_product_id":
                    del product["identity"][field]
                else:
                    del product[field]
                products.append(product)
        self.collect(products)
        self.build()
        self.assertEqual(len(self.rows()), len(products))

    def test_product_identifier_can_identify_unvarianted_seller_listings(self):
        first = self.product("first-copy", source="waitrose")
        second = self.product("second-copy", source="waitrose")
        for product in (first, second):
            del product["identity"]["source_variant_id"]
        self.collect([first, second])
        self.build()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["source_listing_ids"], ["first-copy", "second-copy"])

    def test_brand_and_retailer_partitions_keep_brand_separate_from_seller(self):
        products = [self.product("brand-store", source="montezumas"),
                    self.product("retailer", source="chocolate-shop"),
                    self.product("unknown")]
        self.collect(products)
        self.build()
        rows = {row["listing_id"]: row for row in self.rows()}
        self.assertEqual(rows["brand-store"]["source_role"], "brand")
        self.assertEqual(rows["retailer"]["source_role"], "retail")
        self.assertEqual(rows["unknown"]["source_role"], "unknown")
        self.assertEqual(rows["retailer"]["brand"], "Example Chocolate Maker")
        self.assertEqual(rows["retailer"]["retailer"], "The Chocolate Shop")
        for role, listing in (("brand", "brand-store"), ("retail", "retailer"),
                              ("unknown", "unknown")):
            with self.subTest(role=role):
                self.assertEqual(self.rows(role + "/products"), [rows[listing]])

    def test_inconsistent_capture_history_is_reported_and_skipped(self):
        collected = self.collect([self.product("damaged"), self.product("valid")])
        history_path = self.archive / collected["products"][0]["history_path"]
        history = json.loads(history_path.read_text(encoding="utf-8"))
        history["raw_record"]["information"]["selected_variant"]["price"] = "9.00"
        history_path.write_text(json.dumps(history), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual([row["listing_id"] for row in self.rows()], ["valid"])
        self.assertTrue(any(error["listing_id"] == "damaged" for error in report["archive_errors"]))
        self.assertEqual(self.snapshot(self.archive), original)

    def test_legacy_records_are_reported_and_preserved(self):
        folder = self.archive / "chocolate/uk/products/legacy"
        folder.mkdir(parents=True)
        (folder / "product.json").write_text(json.dumps({
            "product_id": "legacy", "name": "Original legacy chocolat",
            "information": {"price": "4.00"},
        }), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(self.rows(), [])
        self.assertTrue(report["unsupported_records"])
        self.assertEqual(self.snapshot(self.archive), original)

    def test_import_in_progress_is_reported_and_skipped(self):
        self.collect([self.product()])
        lock = self.archive / "chocolate/uk/products/example/.import.lock"
        lock.write_text("fixture import in progress\n", encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        self.assertEqual(self.rows(), [])
        self.assertTrue(any(error["code"] == "import_in_progress"
                            for error in report["archive_errors"]))
        self.assertEqual(self.snapshot(self.archive), original)

    def test_outputs_are_deterministic_and_manifest_hashes_match_saved_bytes(self):
        self.collect([self.product()])
        report = self.build()
        original_output = self.snapshot(self.output)
        self.assertEqual(self.build(), report)
        self.assertEqual(self.snapshot(self.output), original_output)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["dataset_version"], report["dataset_version"])
        for relative, metadata in manifest["managed_files"].items():
            with self.subTest(output=relative):
                content = (self.output / relative).read_bytes()
                self.assertEqual(metadata["sha256"], hashlib.sha256(content).hexdigest())
                self.assertEqual(metadata["byte_length"], len(content))
        for metadata in manifest["inputs"]:
            with self.subTest(input=metadata["path"]):
                content = (self.archive / metadata["path"]).read_bytes()
                self.assertEqual(metadata["sha256"], hashlib.sha256(content).hexdigest())
        for table in ("products", "listing-aliases", "brand/products", "retail/products",
                      "unknown/products"):
            for row in self.rows(table):
                self.assertEqual(row["dataset_version"], manifest["dataset_version"])

    def test_output_cannot_overlap_the_raw_archive(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "deduplicated", self.base):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build_deduplicated_dataset(self.archive, output)
        self.assertEqual(self.snapshot(self.archive), original)


if __name__ == "__main__":
    unittest.main()
