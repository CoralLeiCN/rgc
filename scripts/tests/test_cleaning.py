"""Exercise the chocolate interpretation boundary with preserved archive fixtures."""

import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from category_research import import_document
from chocolate_cleanup.core import build_dataset, pointer_value

ROOT = Path(__file__).resolve().parents[2]


class ChocolateCleaningTests:
    def test_review_pointers_use_portable_array_indexes_and_escapes(self):
        assert pointer_value({"values": ["first", "last"]}, "/values/1") == "last"
        for pointer in ("/values/-1", "/values/01", "/invalid~2escape"):
            with pytest.raises(ValueError):
                pointer_value({"values": ["first", "last"]}, pointer)

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
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
                    "id": identifier + "-variant",
                    "price": "4.00",
                    "grams": 999,
                    "compare_at_price": None,
                    "available": True,
                    "title": "Default Title",
                },
                "catalogue_retrieval_currency": "GBP",
                "catalogue_collected_at": "2026-10-03T07:00:00Z",
                "body_html": "<p>Ingredients: cocoa butter, sugar.</p><p>May contain nuts.</p>",
                "product_type": "Bar",
            },
            "source_artifacts": [
                {
                    "kind": "page",
                    "content": "<p>Original wording: chocolat noir; café.</p>\n",
                    "url": "https://example.test/products/" + identifier,
                }
            ],
            "images": [],
        }
        record.update(changes)
        return record

    def collect(self, products):
        return import_document(
            {
                "contract_version": "1",
                "study": {
                    "study_id": "chocolate-test",
                    "category": "chocolate",
                    "market": "uk",
                },
                "products": products,
            },
            self.archive,
            workers=1,
        )

    def rows(self, name):
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

    def build(self, reviews=None):
        return build_dataset(self.archive, self.output, reviews=reviews)

    def feature(self, name, listing_id=None):
        rows = [
            row
            for row in self.rows("features")
            if row["name"] == name
            and (listing_id is None or row["listing_id"] == listing_id)
        ]
        assert len(rows) == 1, name
        return rows[0]

    def pointer_value(self, document, pointer):
        assert pointer.startswith("/"), pointer
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
        product_evidence = [
            {"capture_id": capture_id, "pointer": "/raw_record/identity/name"}
        ]
        price_evidence = [
            {
                "capture_id": capture_id,
                "pointer": "/raw_record/information/selected_variant/price",
            }
        ]
        return {
            "review_format_version": "chocolate-reviews-1",
            "products": {
                product["listing_id"]: {
                    "variant_id": "reviewed-example-200g",
                    "family_id": "reviewed-example",
                    "in_scope": True,
                    "comparable_group": "bar",
                    "total_edible_weight_g": 200,
                    "pack_count": 1,
                    "reviewed_by": "Fixture reviewer",
                    "reason": "Reviewed selling unit and product identity.",
                    "evidence": product_evidence,
                }
            },
            "prices": {
                price["price_id"]: {
                    "regular_price": 4,
                    "currency": "GBP",
                    "tax_basis": "consumer_tax_included",
                    "observed_at": "2026-10-03T07:00:00Z",
                    "reviewed_by": "Fixture reviewer",
                    "reason": "Reviewed a regular consumer price at the recorded time.",
                    "evidence": price_evidence,
                }
            },
        }

    def test_preserves_archive_bytes_and_builds_deterministic_versioned_outputs(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        first_report = self.build()
        first = self.snapshot(self.output)
        expected = {
            "products.jsonl",
            "features.jsonl",
            "prices.jsonl",
            "model-inputs.jsonl",
            "review-queue.jsonl",
            "capture-evidence.jsonl",
            "artifacts.jsonl",
            "quality-report.json",
            "manifest.json",
            "profile.json",
            "study.json",
        }
        assert expected.issubset(first)
        profile = json.loads((self.output / "profile.json").read_text())
        for row in self.rows("features"):
            assert profile["feature_types"][row["name"]] == row["value_type"]
        assert self.snapshot(self.archive) == original
        second_report = self.build()
        assert second_report == first_report
        assert self.snapshot(self.output) == first
        assert self.snapshot(self.archive) == original
        assert first_report["counts"]["source_listings"] == 1

    def test_rejects_output_overlapping_raw_archive(self):
        self.collect([self.product()])
        original = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "derived", self.base):
            with pytest.raises(ValueError):
                build_dataset(self.archive, output)
        assert self.snapshot(self.archive) == original

    def test_normalizes_explicit_edible_weight_and_keeps_shipping_weight_separate(self):
        self.collect([self.product()])
        self.build()
        product = self.rows("products")[0]
        price = self.rows("prices")[0]
        assert product["total_edible_weight_g"] == 200
        assert price["total_edible_weight_g"] == 200
        assert Decimal(str(price["displayed_price"])) == Decimal("4.00")
        assert price["displayed_price_per_100g"] == 2
        assert product["total_edible_weight_g"] != 999
        assert not price["model_eligible"]
        assert self.rows("model-inputs") == []

    def test_shipping_grams_do_not_supply_missing_edible_quantity(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate Bar"
        self.collect([product])
        self.build()
        assert self.rows("products")[0]["total_edible_weight_g"] is None
        price = self.rows("prices")[0]
        assert price["displayed_price_per_100g"] is None
        assert not price["model_eligible"]
        assert price["exclusion_reasons"]

    def test_compare_at_price_is_retained_without_inventing_a_regular_price(self):
        product = self.product()
        product["information"]["selected_variant"]["compare_at_price"] = "5.00"
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        assert Decimal(str(price["displayed_price"])) == Decimal("4.00")
        assert Decimal(str(price["reference_price"])) == Decimal("5.00")
        assert price["regular_price"] is None
        assert price["regular_price_per_100g"] is None
        assert not price["model_eligible"]

    def test_missing_certification_is_unknown_and_allergen_warning_is_not_an_ingredient(
        self,
    ):
        self.collect([self.product()])
        self.build()
        for feature in ("fairtrade_claim", "organic_claim", "nuts_as_ingredient"):
            assert self.feature(feature)["status"] == "unknown"
            assert self.feature(feature)["value"] in ((None, "unknown"))
        assert self.feature("may_contain_nuts")["value"] in ((True, "present"))
        assert "cocoa butter, sugar" in self.feature("ingredients_text")["value"]
        assert "May contain nuts" in self.feature("allergen_text")["value"]

    def test_repeated_identical_imports_deduplicate_prices_but_keep_both_evidence_references(
        self,
    ):
        product = self.product()
        first = self.collect([product])
        second = self.collect([deepcopy(product)])
        self.build()
        assert len(self.rows("products")) == 1
        prices = self.rows("prices")
        assert len(prices) == 1
        assert {reference["capture_id"] for reference in prices[0]["evidence"]} == {
            first["products"][0]["capture_id"],
            second["products"][0]["capture_id"],
        }

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
        assert len(prices) == 2
        assert [
            (row["total_edible_weight_g"], row["displayed_price_per_100g"])
            for row in prices
        ] == [(100, 4), (200, 2)]

    def test_changed_quantity_at_the_same_time_does_not_deduplicate_distinct_offers(
        self,
    ):
        first = self.product()
        first["identity"]["name"] = "Example Dark Chocolate Bar 100g"
        self.collect([first])
        self.collect([self.product()])
        self.build()
        prices = self.rows("prices")
        assert len(prices) == 2
        assert {row["total_edible_weight_g"] for row in prices} == {100, 200}

    def test_zero_compare_at_is_not_a_regular_price_or_a_discount_reference(self):
        product = self.product()
        product["information"]["selected_variant"]["compare_at_price"] = "0.00"
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        assert price["regular_price"] is None
        assert price["reference_price"] is None

    def test_waitrose_offer_preserves_was_price_as_reference_and_uses_edible_weight(
        self,
    ):
        product = self.product("waitrose")
        product["source_key"] = "waitrose"
        product["source_url"] = "https://www.waitrose.com/ecom/products/example/123"
        product["identity"]["name"] = "Example Chocolate Bar 105g"
        product["information"] = {
            "source_weight_text": "105g",
            "source_price_currency": "GBP",
            "source_collected_at": "2026-10-03T07:00:00Z",
            "catalogue_archived_at": "2026-10-03T08:00:00Z",
            "catalogue_text_context": "Example Chocolate Bar\n105g\nSave 45p.Was £2.10\nItem price\n£1.65\nPrice per unit\n£15.72/kg\nAdd\n",
        }
        self.collect([product])
        self.build()
        price = self.rows("prices")[0]
        assert Decimal(str(price["displayed_price"])) == Decimal("1.65")
        assert Decimal(str(price["reference_price"])) == Decimal("2.10")
        assert price["regular_price"] is None
        assert price["total_edible_weight_g"] == 105
        assert (
            round(abs((price["displayed_price_per_100g"]) - (1.65 / 105 * 100)), 7) == 0
        )
        assert not price["model_eligible"]

    def test_nonpositive_price_and_invalid_time_are_retained_for_review(self):
        product = self.product()
        product["information"]["selected_variant"]["price"] = "-4.00"
        product["information"]["catalogue_collected_at"] = "not-a-date"
        self.collect([product])
        report = self.build()
        assert report["counts"]["eligible_price_observations"] == 0
        price = self.rows("prices")[0]
        assert not price["model_eligible"]
        assert price["exclusion_reasons"]
        assert self.rows("review-queue")
        assert self.rows("model-inputs") == []

    def test_conflicting_current_edible_weights_require_quantity_review(self):
        product = self.product()
        product["information"]["selected_variant"]["title"] = "100g"
        self.collect([product])
        self.build()
        product_row = self.rows("products")[0]
        assert product_row["total_edible_weight_g"] is None
        assert product_row["quantity_status"] == "conflict"
        assert self.rows("prices")[0]["displayed_price_per_100g"] is None
        assert any(
            "conflicting_edible_quantities" in row["reasons"]
            for row in self.rows("review-queue")
        )

    def test_extreme_price_strings_never_produce_nonfinite_analytical_values(self):
        products = []
        for index, price in enumerate(("1e309", "1" + "0" * 400)):
            product = self.product("extreme-" + str(index))
            product["information"]["selected_variant"]["price"] = price
            products.append(product)
        self.collect(products)
        report = self.build()
        assert report["counts"]["eligible_price_observations"] == 0
        assert len(self.rows("prices")) == 2
        assert all(
            row["displayed_price_per_100g"] is None for row in self.rows("prices")
        )
        for content in self.snapshot(self.output).values():
            assert b"Infinity" not in content
            assert b"NaN" not in content

    def test_inconsistent_history_is_reported_without_cleaning_the_damaged_listing(
        self,
    ):
        collected = self.collect([self.product()])
        path = self.archive / collected["products"][0]["history_path"]
        history = json.loads(path.read_text(encoding="utf-8"))
        history["raw_record"]["information"]["selected_variant"]["price"] = "5.00"
        path.write_text(json.dumps(history), encoding="utf-8")
        original = self.snapshot(self.archive)
        report = self.build()
        assert report["archive_errors"]
        assert report["counts"]["source_listings"] == 0
        assert self.rows("products") == []
        assert self.snapshot(self.archive) == original

    def test_unsupported_legacy_records_are_reported_without_rewriting_them(self):
        folder = self.archive / "chocolate/uk/products/legacy"
        folder.mkdir(parents=True)
        (folder / "product.json").write_text(
            json.dumps(
                {
                    "product_id": "legacy",
                    "name": "Legacy chocolate",
                    "information": {"price": "4.00"},
                }
            ),
            encoding="utf-8",
        )
        original = self.snapshot(self.archive)
        report = self.build()
        assert report["unsupported_records"]
        assert self.rows("products") == []
        assert self.rows("prices") == []
        assert self.snapshot(self.archive) == original

    def test_normalized_evidence_tables_join_rows_to_capture_history_and_artifact_metadata(
        self,
    ):
        self.collect([self.product()])
        report = self.build()
        captures = self.capture_lookup()
        capture_rows = {row["capture_id"]: row for row in self.rows("capture-evidence")}
        artifacts = {row["artifact_id"]: row for row in self.rows("artifacts")}
        assert len(capture_rows) == 1
        assert len(artifacts) == 1
        for table in ("products", "features", "prices"):
            for row in self.rows(table):
                for reference in row.get("evidence", []) + row.get(
                    "quantity_evidence", []
                ):
                    assert reference["capture_id"] in captures
                    self.pointer_value(
                        captures[reference["capture_id"]], reference["pointer"]
                    )
                    assert (
                        reference["artifact_metadata_table"] == "capture-evidence.jsonl"
                    )
                    assert "artifacts" not in reference
                    assert "raw_value" not in reference
                    capture = capture_rows[reference["capture_id"]]
                    assert capture["listing_id"] == reference["listing_id"]
                    assert (
                        capture["source_listing_id"] == reference["source_listing_id"]
                    )
                    assert capture["history_path"] == reference["history_path"]
                    history = json.loads(
                        (self.archive / capture["history_path"]).read_text(
                            encoding="utf-8"
                        )
                    )
                    assert history["capture_id"] == capture["capture_id"]
                    self.pointer_value(history, reference["pointer"])
                    assert capture["artifact_ids"]
                    for artifact_id in capture["artifact_ids"]:
                        artifact = artifacts[artifact_id]
                        assert artifact["dataset_version"] == report["dataset_version"]
                        assert artifact["available_locally"]
                        original = next(
                            item
                            for item in history["source_artifacts"]
                            if item["archive_relative_path"]
                            == artifact["archive_relative_path"]
                        )
                        assert artifact["sha256"] == original["sha256"]
        assert self.rows("prices")[0]["evidence"]
        assert self.feature("ingredients_text")["evidence"]

    def test_reference_only_image_without_local_path_has_deterministic_evidence_metadata(
        self,
    ):
        product = self.product()
        image_url = "https://example.test/images/front.png"
        product["images"] = [{"url": image_url, "alt": "Original front-pack reference"}]
        self.collect([product])
        original = self.snapshot(self.archive)
        first = self.build()
        outputs = self.snapshot(self.output)
        image = next(
            row for row in self.rows("artifacts") if row["artifact_group"] == "images"
        )
        assert image["url"] == image_url
        assert image["status"] == "reference_only"
        assert image["archive_relative_path"] is None
        assert not image["available_locally"]
        assert self.build() == first
        assert self.snapshot(self.output) == outputs
        assert self.snapshot(self.archive) == original

    def test_optional_identity_and_arbitrary_source_information_do_not_abort_the_build(
        self,
    ):
        minimal = {
            "product_id": "minimal",
            "information": "Original source wording: chocolat.",
        }
        self.collect([minimal, self.product("supported")])
        original = self.snapshot(self.archive)
        report = self.build()
        assert report["archive_errors"] == []
        products = {row["listing_id"]: row for row in self.rows("products")}
        assert set(products) == {"minimal", "supported"}
        assert products["minimal"]["name"] is None
        assert products["minimal"]["total_edible_weight_g"] is None
        assert {row["listing_id"] for row in self.rows("prices")} == {"supported"}
        assert self.snapshot(self.archive) == original

    def test_malformed_nested_source_sections_are_reported_while_other_listings_continue(
        self,
    ):
        malformed = self.product("malformed")
        malformed["information"]["product_page_information"] = {"source_sections": 42}
        self.collect([malformed, self.product("supported")])
        original = self.snapshot(self.archive)
        report = self.build()
        assert any(
            error["listing_id"] == "malformed" for error in report["archive_errors"]
        )
        assert {row["listing_id"] for row in self.rows("prices")} == {"supported"}
        assert any(
            row["listing_id"] == "malformed" for row in self.rows("review-queue")
        )
        assert self.snapshot(self.archive) == original

    def test_a_tax_only_price_review_does_not_complete_the_regular_price_basis(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        review = next(iter(reviews["prices"].values()))
        for field in ("regular_price", "currency", "observed_at"):
            del review[field]
        report = self.build(self.write_reviews(reviews))
        assert report["counts"]["eligible_price_observations"] == 0
        price = self.rows("prices")[0]
        assert price["tax_basis"] == "consumer_tax_included"
        assert "price_basis_review_incomplete" in price["exclusion_reasons"]
        assert not price["model_eligible"]
        assert self.rows("model-inputs") == []

    def test_only_reviewed_identity_scope_quantity_and_price_basis_enter_model_inputs(
        self,
    ):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        original = self.snapshot(self.archive)
        report = self.build(self.write_reviews(reviews))
        assert report["counts"]["eligible_price_observations"] == 1
        assert not report["release_ready"]
        price = self.rows("prices")[0]
        assert price["model_eligible"], price["exclusion_reasons"]
        assert price["regular_price_per_100g"] == 2
        assert price["variant_id"] == "reviewed-example-200g"
        assert price["family_id"] == "reviewed-example"
        assert len(self.rows("model-inputs")) == 1
        assert self.snapshot(self.archive) == original
        reviews["products"][next(iter(reviews["products"]))]["in_scope"] = False
        report = self.build(self.write_reviews(reviews))
        assert report["counts"]["eligible_price_observations"] == 0
        assert self.rows("model-inputs") == []

    def test_review_rejects_unknown_identity_and_nonresolving_evidence(self):
        self.collect([self.product()])
        self.build()
        reviews = self.reviewed_document()
        cases = []
        unknown = deepcopy(reviews)
        unknown["products"]["unknown-listing"] = unknown["products"].pop(
            next(iter(unknown["products"]))
        )
        cases.append(unknown)
        unknown_price = deepcopy(reviews)
        unknown_price["prices"]["unknown-price"] = unknown_price["prices"].pop(
            next(iter(unknown_price["prices"]))
        )
        cases.append(unknown_price)
        enormous_price = deepcopy(reviews)
        next(iter(enormous_price["prices"].values()))["regular_price"] = "1e309"
        cases.append(enormous_price)
        wrong_pointer = deepcopy(reviews)
        next(iter(wrong_pointer["prices"].values()))["evidence"][0]["pointer"] = (
            "/missing-field"
        )
        cases.append(wrong_pointer)
        naive_time = deepcopy(reviews)
        next(iter(naive_time["prices"].values()))["observed_at"] = "2026-10-03T07:00:00"
        cases.append(naive_time)
        original_outputs = self.snapshot(self.output)
        for document in cases:
            with pytest.raises(ValueError):
                self.build(self.write_reviews(document))
            assert self.snapshot(self.output) == original_outputs

    def test_reviews_reject_evidence_from_a_different_source_listing(self):
        self.collect([self.product("first")])
        self.build()
        reviews = self.reviewed_document()
        self.collect([self.product("second")])
        self.build()
        foreign_capture = next(
            capture["capture_id"]
            for capture in self.capture_lookup().values()
            if capture["raw_record"]["product_id"] == "second"
        )
        for entity in ("products", "prices"):
            wrong = deepcopy(reviews)
            next(iter(wrong[entity].values()))["evidence"][0]["capture_id"] = (
                foreign_capture
            )
            with pytest.raises(ValueError):
                self.build(self.write_reviews(wrong))

    def test_exact_duplicate_listings_within_one_seller_share_rows_and_keep_alias_evidence(
        self,
    ):
        original = self.product("first-copy")
        alias = deepcopy(original)
        alias["product_id"] = "second-copy"
        first = self.collect([original])
        second = self.collect([alias])
        self.build()
        products = self.rows("products")
        assert len(products) == 1
        assert products[0]["listing_id"] == "first-copy"
        assert set(products[0]["source_listing_ids"]) == {"first-copy", "second-copy"}
        assert len(self.rows("prices")) == 1
        assert {
            reference["capture_id"] for reference in self.rows("prices")[0]["evidence"]
        } == {first["products"][0]["capture_id"], second["products"][0]["capture_id"]}

    def test_brand_and_retail_sources_are_partitioned_without_using_product_brand_as_seller(
        self,
    ):
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
        assert products["montezumas"]["source_role"] == "brand"
        assert products["chocolate-shop"]["source_role"] == "retail"
        assert products["example-shop"]["source_role"] == "unknown"
        assert products["chocolate-shop"]["brand"] == "Chocolate Tree"
        assert products["chocolate-shop"]["retailer"] == "The Chocolate Shop"
        for source_role, source_key in (
            ("brand", "montezumas"),
            ("retail", "chocolate-shop"),
            ("unknown", "example-shop"),
        ):
            product_rows = self.rows(source_role + "/products")
            price_rows = self.rows(source_role + "/prices")
            assert len(product_rows) == 1
            assert len(price_rows) == 1
            assert product_rows[0]["source_key"] == source_key
            assert price_rows[0]["source_role"] == source_role

    def test_ambiguous_count_and_mass_require_quantity_review(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate 3 bars 150g"
        self.collect([product])
        self.build()
        assert self.rows("products")[0]["total_edible_weight_g"] is None
        assert self.rows("prices")[0]["displayed_price_per_100g"] is None
        assert self.rows("review-queue")

    def test_explicit_multipack_sums_edible_mass(self):
        product = self.product()
        product["identity"]["name"] = "Example Dark Chocolate Bars 3 x 150g"
        self.collect([product])
        self.build()
        assert self.rows("products")[0]["total_edible_weight_g"] == 450
        assert self.rows("products")[0]["pack_count"] == 3
        assert self.rows("prices")[0]["displayed_price_per_100g"] == round(
            4 / 450 * 100, 8
        )

    def test_two_retailer_listings_stay_separate_until_reviewed(self):
        first = self.product("first-retailer")
        second = self.product("second-retailer")
        second["source_key"] = "second-shop"
        second["source_url"] = "https://second.test/products/example"
        second["identity"] = deepcopy(first["identity"])
        self.collect([first, second])
        self.build()
        products = self.rows("products")
        assert len(products) == 2
        assert len({row["listing_id"] for row in products}) == 2
        assert len({row["variant_id"] for row in products}) == 2
        assert all(row["family_id"] is None for row in products)
        assert all(
            row["identity_status"] == "unresolved_source_listing" for row in products
        )
        assert self.rows("model-inputs") == []
