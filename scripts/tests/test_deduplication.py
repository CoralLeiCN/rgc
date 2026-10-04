"""Verify that raw deduplication preserves evidence and seller boundaries."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from category_research import import_document
from chocolate_cleanup.deduplication import build_deduplicated_dataset

ROOT = Path(__file__).resolve().parents[2]


class ChocolateDeduplicationTests:
    def test_pending_import_and_empty_archive_have_different_versions(self):
        (self.archive / "chocolate/uk/products").mkdir(parents=True)
        empty = self.build()
        self.collect([self.product()])
        folder = self.archive / "chocolate/uk/products/example-shop/example"
        (folder / ".import.lock").write_text(
            "fixture import in progress\n", encoding="utf-8"
        )
        original = self.snapshot(self.archive)
        pending = self.build()
        assert empty["dataset_version"] != pending["dataset_version"]
        assert pending["status"] == "partial"
        assert pending["counts"]["source_listings"] == 0
        assert self.rows() == []
        assert any(
            error["code"] == "import_in_progress" for error in pending["archive_errors"]
        )
        assert self.snapshot(self.archive) == original

    def test_invalid_json_remains_hashed_and_reported(self):
        folder = self.archive / "chocolate/uk/products/invalid"
        folder.mkdir(parents=True)
        path = folder / "product.json"
        original = b'{"unfinished":'
        path.write_bytes(original)
        report = self.build()
        assert report["counts"]["archive_errors"] == 1
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert manifest["inputs"][0]["sha256"] == hashlib.sha256(original).hexdigest()
        assert path.read_bytes() == original

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.archive = self.base / "collections"
        self.output = self.base / "deduplicated"

    def product(
        self, listing="example", source="example-shop", hostname="example.test"
    ):
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
                    "id": "shared-variant",
                    "price": "04.00",
                    "grams": 999,
                    "compare_at_price": "5.00",
                    "available": True,
                    "title": "Default Title",
                },
                "body_html": "<p>Ingrédients: chocolat noir; café.</p>\n",
                "catalogue_retrieval_currency": "GBP",
                "catalogue_collected_at": "2026-10-03T07:00:00Z",
                "arbitrary_source_fields": {
                    "preserve_null": None,
                    "preserve_list": ["é", 0, False],
                    "uninterpreted_mass": "not a weight",
                },
            },
            "source_artifacts": [
                {
                    "kind": "page",
                    "content": "Original wording: chocolat noir; café.\n",
                    "url": "https://" + hostname + "/products/shared-product",
                }
            ],
            "images": [{"url": "https://" + hostname + "/image.png"}],
        }

    def collect(self, products):
        return import_document(
            {
                "contract_version": "1",
                "study": {
                    "study_id": "chocolate-dedup-test",
                    "category": "chocolate",
                    "market": "uk",
                },
                "products": products,
            },
            self.archive,
            workers=1,
        )

    def build(self):
        return build_deduplicated_dataset(self.archive, self.output)

    def rows(self, name="products"):
        return [
            json.loads(line)
            for line in (self.output / (name + ".jsonl"))
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    def snapshot(self, directory):
        return {
            str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file()
        }

    def captures(self):
        return {
            capture["capture_id"]: capture
            for path in self.archive.rglob("product.json")
            for capture in json.loads(path.read_text(encoding="utf-8"))["captures"]
        }

    def test_raw_archive_and_original_capture_values_remain_unchanged(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        original_captures = self.captures()
        self.build()
        assert self.snapshot(self.archive) == original
        row = self.rows()[0]
        assert {
            capture["capture_id"]: capture for capture in row["captures"]
        } == original_captures
        raw = row["captures"][0]["raw_record"]
        assert raw == self.product()
        assert raw["information"]["selected_variant"]["price"] == "04.00"
        assert raw["information"]["selected_variant"]["grams"] == 999
        for field in (
            "total_edible_weight_g",
            "displayed_price",
            "displayed_price_per_100g",
            "model_eligible",
            "comparable_group",
            "features",
        ):
            assert field not in row
        for table in ("prices.jsonl", "features.jsonl", "model-inputs.jsonl"):
            assert not (self.output / table).exists()

    def test_aliases_with_exact_seller_product_and_variant_merge_all_captures(self):
        first = self.product("first-copy")
        self.collect([first])
        self.collect([deepcopy(first)])
        alias = self.product("second-copy")
        alias["information"]["selected_variant"]["price"] = "03.50"
        self.collect([alias])
        original_captures = self.captures()
        report = self.build()
        assert len(self.rows()) == 1
        row = self.rows()[0]
        assert row["listing_id"] == "first-copy"
        assert row["source_listing_ids"] == ["first-copy", "second-copy"]
        assert {
            capture["capture_id"]: capture for capture in row["captures"]
        } == original_captures
        assert len(row["captures"]) == 3
        assert row["latest_capture_id"] in original_captures
        assert report["counts"]["source_listings"] == 1
        assert {
            (alias["source_listing_id"], alias["listing_id"])
            for alias in self.rows("listing-aliases")
        } == {("first-copy", "first-copy"), ("second-copy", "first-copy")}

    def test_products_at_different_sources_or_hostnames_remain_unique(self):
        products = [
            self.product("first-shop", source="chocolate-shop"),
            self.product("second-shop", source="waitrose"),
            self.product("other-host", source="chocolate-shop", hostname="other.test"),
        ]
        self.collect(products)
        self.build()
        assert {row["listing_id"] for row in self.rows()} == {
            product["product_id"] for product in products
        }
        assert all(len(row["source_listing_ids"]) == 1 for row in self.rows())

    def test_distinct_variants_at_the_same_seller_remain_unique(self):
        first = self.product("first-variant")
        second = self.product("second-variant")
        second["identity"]["source_variant_id"] = "different-variant"
        second["information"]["selected_variant"]["id"] = "different-variant"
        self.collect([first, second])
        self.build()
        assert len(self.rows()) == 2
        assert {row["source_variant_id"] for row in self.rows()} == {
            "shared-variant",
            "different-variant",
        }

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
        assert len(self.rows()) == len(products)

    def test_product_identifier_can_identify_unvarianted_seller_listings(self):
        first = self.product("first-copy", source="waitrose")
        second = self.product("second-copy", source="waitrose")
        for product in (first, second):
            del product["identity"]["source_variant_id"]
        self.collect([first, second])
        self.build()
        assert len(self.rows()) == 1
        assert self.rows()[0]["source_listing_ids"] == ["first-copy", "second-copy"]

    def test_brand_and_retailer_partitions_keep_brand_separate_from_seller(self):
        products = [
            self.product("brand-store", source="montezumas"),
            self.product("retailer", source="chocolate-shop"),
            self.product("unknown"),
        ]
        self.collect(products)
        self.build()
        rows = {row["listing_id"]: row for row in self.rows()}
        assert rows["brand-store"]["source_role"] == "brand"
        assert rows["retailer"]["source_role"] == "retail"
        assert rows["unknown"]["source_role"] == "unknown"
        assert rows["retailer"]["brand"] == "Example Chocolate Maker"
        assert rows["retailer"]["retailer"] == "The Chocolate Shop"
        for role, listing in (
            ("brand", "brand-store"),
            ("retail", "retailer"),
            ("unknown", "unknown"),
        ):
            assert self.rows(role + "/products") == [rows[listing]]

    def test_inconsistent_capture_history_is_reported_and_skipped(self):
        collected = self.collect([self.product("damaged"), self.product("valid")])
        history_path = self.archive / collected["products"][0]["history_path"]
        history = json.loads(history_path.read_text(encoding="utf-8"))
        history["raw_record"]["information"]["selected_variant"]["price"] = "9.00"
        history_path.write_text(json.dumps(history), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        assert [row["listing_id"] for row in self.rows()] == ["valid"]
        assert any(
            error["listing_id"] == "damaged" for error in report["archive_errors"]
        )
        assert self.snapshot(self.archive) == original

    def test_legacy_records_are_reported_and_preserved(self):
        folder = self.archive / "chocolate/uk/products/legacy"
        folder.mkdir(parents=True)
        (folder / "product.json").write_text(
            json.dumps(
                {
                    "product_id": "legacy",
                    "name": "Original legacy chocolat",
                    "information": {"price": "4.00"},
                }
            ),
            encoding="utf-8",
        )
        original = self.snapshot(self.archive)
        report = self.build()
        assert self.rows() == []
        assert report["unsupported_records"]
        assert self.snapshot(self.archive) == original

    def test_outputs_are_deterministic_and_manifest_hashes_match_saved_bytes(self):
        self.collect([self.product()])
        report = self.build()
        original_output = self.snapshot(self.output)
        assert self.build() == report
        assert self.snapshot(self.output) == original_output
        manifest = json.loads(
            (self.output / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["dataset_version"] == report["dataset_version"]
        for relative, metadata in manifest["managed_files"].items():
            content = (self.output / relative).read_bytes()
            assert metadata["sha256"] == hashlib.sha256(content).hexdigest()
            assert metadata["byte_length"] == len(content)
        for metadata in manifest["inputs"]:
            content = (self.archive / metadata["path"]).read_bytes()
            assert metadata["sha256"] == hashlib.sha256(content).hexdigest()
        for table in (
            "products",
            "listing-aliases",
            "brand/products",
            "retail/products",
            "unknown/products",
        ):
            for row in self.rows(table):
                assert row["dataset_version"] == manifest["dataset_version"]

    def test_output_cannot_overlap_the_raw_archive(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "deduplicated", self.base):
            with pytest.raises(ValueError):
                build_deduplicated_dataset(self.archive, output)
        assert self.snapshot(self.archive) == original
