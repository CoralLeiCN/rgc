"""Verify the evidence boundary from raw deduplication to chocolate model rows."""

import hashlib
import json
import math
import shutil
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import dataset_contracts as contract_module
import pytest
from chocolate_archive_fixture import ChocolateArchiveFixture
from chocolate_cleanup.core import pointer_value
from chocolate_cleanup.deduplication import build_deduplicated_dataset
from chocolate_model import fit_encoder, transform_rows
from chocolate_standardization.pipeline import build_standardized_dataset

ROOT = Path(__file__).resolve().parents[2]


class ChocolateStandardizationTests(ChocolateArchiveFixture):
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.initialize(tmp_path)

    def prepare(self, products=None):
        self.collect(products or [self.product()])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        return self.build()

    def build(self, reviews=None, output=None):
        return build_standardized_dataset(
            self.deduplicated, output or self.output, reviews=reviews, offline=True
        )

    def test_valid_category_value_outside_selected_model_domain_is_excluded(self):
        self.prepare()
        copied = self.base / "restricted-model-contracts"
        shutil.copytree(
            self.schema_root,
            copied,
            ignore=shutil.ignore_patterns("dataset-contract.json"),
        )
        path = copied / "model-design.json"
        design = json.loads(path.read_text())
        design["predictors"]["quantity.total_edible_weight_g"]["minimum"] = 1000
        path.write_text(json.dumps(design))
        report = build_standardized_dataset(
            self.deduplicated,
            self.output,
            reviews=self.reviews(),
            schema_root=copied,
            offline=True,
        )
        assert report["counts"]["eligible_model_inputs"] == 0
        assert (
            self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"][
                "value"
            ]
            == 200
        )
        assert (
            "model_predictor_outside_design_domain:quantity.total_edible_weight_g"
            in self.rows("training-candidates")[0]["exclusion_reasons"]
        )

    def test_unavailable_pinned_contract_cache_prevents_output_writes(self):
        self.collect([self.product()])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        before = self.snapshot(self.deduplicated)
        with patch.object(
            contract_module, "SCHEMA_CACHE", self.base / "missing-contract-cache"
        ):
            with patch(
                "category_processing.dataset_contracts._download",
                side_effect=AssertionError("Offline builds must not fetch contracts"),
            ):
                with pytest.raises(FileNotFoundError, match="not cached"):
                    self.build()
        assert not self.output.exists()
        assert self.snapshot(self.deduplicated) == before

    def rows(self, name="products", directory=None):
        return [
            json.loads(line)
            for line in ((directory or self.output) / (name + ".jsonl"))
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    def source_listing(self):
        return self.rows(directory=self.deduplicated)[0]

    def reviews(self):
        source = self.source_listing()
        captures = {capture["capture_id"]: capture for capture in source["captures"]}
        latest = captures[source["latest_capture_id"]]
        capture_id = latest["capture_id"]
        common = {
            "reviewed_by": "Fixture evidence reviewer",
            "reason": "Explicit product-specific fixture declaration reviewed.",
        }
        values = latest["raw_record"]["information"]["review_fixture"]
        attributes = {}
        for name in self.design["predictors"]:
            attributes[name] = {
                **common,
                "value": values[name],
                "status": "known",
                "scope": "product",
                "evidence": [
                    {
                        "capture_id": capture_id,
                        "pointer": "/raw_record/information/review_fixture/" + name,
                    }
                ],
            }
            if name == "composition.cocoa_percentage":
                attributes[name]["qualifier"] = "exact"
        product = {
            **common,
            "variant_id": "reviewed-fixture-variant",
            "family_id": "reviewed-fixture-family",
            "in_scope": True,
            "attributes": attributes,
            "evidence": [
                {"capture_id": capture_id, "pointer": "/raw_record/identity/name"}
            ],
        }
        prices = {}
        for price in self.rows("prices"):
            ref = price["evidence"][0]
            raw = captures[ref["capture_id"]]["raw_record"]
            prices[price["observation_id"]] = {
                **common,
                "regular_price": float(raw["information"]["selected_variant"]["price"]),
                "currency": "GBP",
                "tax_basis": "consumer_tax_included",
                "available": True,
                "observed_at": raw["information"]["catalogue_collected_at"],
                "evidence": [deepcopy(ref)],
            }
        return {
            "review_format_version": "chocolate-schema-reviews-1",
            "products": {source["listing_id"]: product},
            "prices": prices,
        }

    def test_standardization_preserves_raw_and_deduplicated_original_bytes(self):
        self.collect([self.product()])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        archive_before, dedup_before = (
            self.snapshot(self.archive),
            self.snapshot(self.deduplicated),
        )
        self.build()
        assert self.snapshot(self.archive) == archive_before
        assert self.snapshot(self.deduplicated) == dedup_before
        captured = self.source_listing()["captures"][0]["raw_record"]
        assert captured == self.product()
        assert captured["information"]["selected_variant"]["price"] == "04.00"
        assert "chocolat noir; café" in captured["information"]["body_html"]
        assert (
            self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"][
                "value"
            ]
            == 200
        )
        assert (
            self.rows("products")[0]["attributes"]["quantity.total_edible_weight_g"][
                "value"
            ]
            != 999
        )

    def test_every_listing_tracks_all_103_attributes_with_explicit_unknowns(self):
        report = self.prepare()
        product = self.rows()[0]
        assert len(product["attributes"]) == 103
        assert set(product["attributes"]) == set(self.profile["attributes"])
        unknown = product["attributes"]["packaging.materials"]
        assert unknown["status"] == "unknown"
        assert unknown["value"] is None
        assert unknown["evidence"] == []
        assert product["attributes"]["composition.nuts_presence"]["status"] == "unknown"
        assert report["counts"]["tracked_attributes"] == 103
        assert not report["release_ready"]
        assert self.rows("model-inputs") == []

    @pytest.mark.parametrize("name,expected", [
        ("Blonde Chocolate Bar 200g", "blonde"),
        ("Milk Chocolate and Dark Chocolate Selection 200g", "mixed"),
    ])
    def test_title_type_reaches_silver_with_original_evidence_and_review_gate(self, name, expected):
        original = self.product()
        original["identity"]["name"] = name
        self.prepare([original])
        row = self.rows()[0]
        attribute = row["attributes"]["composition.chocolate_type"]
        assert attribute["value"] == expected
        assert attribute["status"] == "known"
        assert attribute["review_status"] == "unreviewed"
        assert attribute["scope"] == "product"
        source = self.source_listing()
        capture = source["captures"][0]
        assert capture["raw_record"] == original
        assert attribute["evidence"] == [{"capture_id": capture["capture_id"],
                                         "pointer": "/raw_record/identity/name"}]
        candidate = self.rows("training-candidates")[0]
        assert candidate["predictors"]["composition.chocolate_type"] == expected
        assert not candidate["model_eligible"]
        assert self.rows("model-inputs") == []

    def test_same_product_remains_unique_at_brand_and_retail_sellers(self):
        first = self.product("brand-listing", "montezumas")
        second = self.product("retail-listing", "chocolate-shop")
        third = self.product("unknown-listing", "unresolved-shop")
        self.prepare([first, second, third])
        rows = {row["listing_id"]: row for row in self.rows()}
        assert len(rows) == 3
        for listing, role in (
            ("brand-listing", "brand"),
            ("retail-listing", "retail"),
            ("unknown-listing", "unknown"),
        ):
            assert rows[listing]["source_role"] == role
            assert [row["listing_id"] for row in self.rows(role + "/products")] == [
                listing
            ]
        assert rows["brand-listing"]["brand"] == rows["retail-listing"]["brand"]
        assert rows["retail-listing"]["retailer"] == "The Chocolate Shop"
        assert rows["retail-listing"]["retailer"] != rows["retail-listing"]["brand"]
        assert (
            rows["retail-listing"]["attributes"]["identity.retailer"]["value"]
            == "The Chocolate Shop"
        )
        assert self.rows("model-inputs") == []

    def test_rebuild_is_deterministic_and_manifest_hashes_outputs(self):
        first_report = self.prepare()
        before = self.snapshot(self.output)
        second_report = self.build()
        assert first_report == second_report
        assert self.snapshot(self.output) == before
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert (
            manifest["source_manifest_sha256"]
            == hashlib.sha256(
                (self.deduplicated / "manifest.json").read_bytes()
            ).hexdigest()
        )
        for name, metadata in manifest["managed_files"].items():
            data = (self.output / name).read_bytes()
            assert metadata["byte_length"] == len(data)
            assert metadata["sha256"] == hashlib.sha256(data).hexdigest()

    def test_all_assertion_evidence_resolves_to_preserved_capture_values(self):
        self.prepare()
        captures = {
            capture["capture_id"]: capture
            for capture in self.source_listing()["captures"]
        }
        for assertion in self.rows("assertions"):
            for ref in assertion["evidence"]:
                assert (
                    pointer_value(captures[ref["capture_id"]], ref["pointer"])
                    is not None
                )

    def test_conflicting_chocolate_type_keeps_evidence_and_selected_value_unknown(self):
        product = self.product()
        product["information"]["composition"] = {"chocolate_type": "Milk Chocolate"}
        self.prepare([product])
        attribute = self.rows()[0]["attributes"]["composition.chocolate_type"]
        assert attribute["status"] == "conflict"
        assert attribute["value"] is None
        assert len(attribute["evidence"]) >= 2
        assert any(
            row["attribute"] == "composition.chocolate_type"
            and row["reason"] == "conflict"
            for row in self.rows("review-queue")
        )

    def test_unmapped_structured_fields_remain_evidence_backed_review_items(self):
        product = self.product()
        product["information"]["composition"] = {
            "novel_source_claim": "Original unfamiliar claim: cacao azul"
        }
        self.prepare([product])
        row = self.rows()[0]
        unmapped = [
            item
            for item in row["unmapped_claims"]
            if item.get("attribute") == "composition.novel_source_claim"
        ]
        assert len(unmapped) == 1
        assert unmapped[0]["value"] == "Original unfamiliar claim: cacao azul"
        assert unmapped[0]["evidence"]
        ref = unmapped[0]["evidence"][0]
        capture = next(
            capture
            for capture in self.source_listing()["captures"]
            if capture["capture_id"] == ref["capture_id"]
        )
        assert pointer_value(capture, ref["pointer"]) == unmapped[0]["value"]

    def test_reviewed_attributes_use_aliases_and_yield_11_predictor_model_input(self):
        self.prepare()
        reviews = self.reviews()
        product_review = reviews["products"]["example"]
        product_review["attributes"]["composition.chocolate_type"]["value"] = (
            "DARK CHOCOLATE"
        )
        product_review["attributes"]["composition.cocoa_percentage"]["value"] = "70"
        report = self.build(reviews)
        assert report["counts"]["eligible_model_inputs"] == 1
        row = self.rows("model-inputs")[0]
        assert row["model_eligible"]
        assert len(row["predictors"]) == 11
        assert row["predictors"]["composition.chocolate_type"] == "dark"
        assert row["predictors"]["composition.cocoa_percentage"] == 70
        assert row["target"]["regular_price_per_100g_gbp"] == 2
        assert (
            round(
                abs((row["target"]["log_regular_price_per_100g_gbp"]) - (math.log(2))),
                7,
            )
            == 0
        )
        assert transform_rows([row], fit_encoder([row], self.design))["X"] == [[1.0]]
        assert not report["release_ready"]

    def test_price_review_alone_does_not_establish_feature_model_eligibility(self):
        self.prepare()
        reviews = self.reviews()
        del reviews["products"]["example"]["attributes"]["dietary.vegan_claim"]
        self.build(reviews)
        assert self.rows("model-inputs") == []
        assert (
            "model_predictor_unreviewed:dietary.vegan_claim"
            in self.rows("training-candidates")[0]["exclusion_reasons"]
        )

    def test_minimum_and_component_cocoa_cannot_supply_exact_whole_product_predictor(
        self,
    ):
        self.prepare()
        for scope, qualifier in (
            ("product", "minimum"),
            ("ingredient", "exact"),
            ("product", "source_stated"),
        ):
            reviews = self.reviews()
            review = reviews["products"]["example"]["attributes"][
                "composition.cocoa_percentage"
            ]
            review.update(scope=scope, qualifier=qualifier)
            self.build(reviews)
            assert self.rows("model-inputs") == []
            assert (
                "cocoa_percentage_basis_unsupported"
                in self.rows("training-candidates")[0]["exclusion_reasons"]
            )

    def test_conditional_or_ingredient_claims_do_not_become_product_indicators(self):
        self.prepare()
        for name, scope, qualifier in (
            ("dietary.vegan_claim", "product", "conditional"),
            ("certifications.organic_claim", "ingredient", "exact"),
        ):
            reviews = self.reviews()
            review = reviews["products"]["example"]["attributes"][name]
            review.update(value="present", scope=scope, qualifier=qualifier)
            self.build(reviews)
            assert self.rows("model-inputs") == []
            assert (
                "model_predictor_basis_unsupported:" + name
                in self.rows("training-candidates")[0]["exclusion_reasons"]
            )

    def test_unknown_reviewed_feature_is_retained_and_remains_excluded(self):
        self.prepare()
        reviews = self.reviews()
        review = reviews["products"]["example"]["attributes"]["dietary.vegan_claim"]
        review.update(status="unknown", value=None)
        self.build(reviews)
        attribute = self.rows()[0]["attributes"]["dietary.vegan_claim"]
        assert attribute["status"] == "unknown"
        assert attribute["review_status"] == "reviewed"
        assert attribute["value"] is None
        assert (
            self.rows("training-candidates")[0]["predictors"]["dietary.vegan_claim"]
            is None
        )
        assert self.rows("model-inputs") == []

    def test_shipping_grams_do_not_supply_missing_edible_mass(self):
        product = self.product()
        product["identity"]["name"] = "Fixture Dark Chocolate Bar"
        del product["information"]["review_fixture"]["quantity.total_edible_weight_g"]
        self.prepare([product])
        assert (
            self.rows()[0]["attributes"]["quantity.total_edible_weight_g"]["status"]
            == "unknown"
        )
        assert self.rows("prices")[0]["total_edible_weight_g"] is None
        assert self.rows("prices")[0]["displayed_price_per_100g_gbp"] is None
        assert self.rows("model-inputs") == []

    def test_latest_quantity_review_cannot_repair_unreviewed_historical_mass(self):
        self.collect(
            [self.product(weight=200, price="4.00", observed_at="2026-10-02T07:00:00Z")]
        )
        self.collect(
            [self.product(weight=100, price="3.00", observed_at="2026-10-03T07:00:00Z")]
        )
        build_deduplicated_dataset(self.archive, self.deduplicated)
        self.build()
        self.build(self.reviews())
        prices = {row["observed_at"]: row for row in self.rows("prices")}
        old = prices["2026-10-02T07:00:00Z"]
        latest = prices["2026-10-03T07:00:00Z"]
        assert old["total_edible_weight_g"] == 200
        assert not old["model_eligible"]
        assert "observation_edible_quantity_unreviewed" in old["exclusion_reasons"]
        assert latest["model_eligible"]
        assert latest["regular_price_per_100g_gbp"] == 3
        assert len(self.rows("model-inputs")) == 1

    def test_reviewed_latest_features_do_not_replace_historical_feature_basis(self):
        first = self.product(
            weight=200, price="4.00", observed_at="2026-10-02T07:00:00Z"
        )
        latest = self.product(
            weight=200, price="5.00", observed_at="2026-10-03T07:00:00Z"
        )
        latest["information"]["review_fixture"]["composition.cocoa_percentage"] = 80
        self.collect([first])
        self.collect([latest])
        build_deduplicated_dataset(self.archive, self.deduplicated)
        self.build()
        reviews = self.reviews()
        quantity = reviews["products"]["example"]["attributes"][
            "quantity.total_edible_weight_g"
        ]
        quantity["evidence"] = [
            {
                "capture_id": capture["capture_id"],
                "pointer": "/raw_record/information/review_fixture/quantity.total_edible_weight_g",
            }
            for capture in self.source_listing()["captures"]
        ]
        self.build(reviews)
        prices = {row["observed_at"]: row for row in self.rows("prices")}
        old = prices["2026-10-02T07:00:00Z"]
        assert old["quantity_status"] == "reviewed"
        assert not old["model_eligible"]
        assert (
            "model_predictor_observation_basis_unreviewed:composition.cocoa_percentage"
            in old["exclusion_reasons"]
        )
        assert prices["2026-10-03T07:00:00Z"]["model_eligible"]
        assert (
            self.rows("model-inputs")[0]["predictors"]["composition.cocoa_percentage"]
            == 80
        )

    def test_corrupt_deduplicated_table_and_wrong_layer_are_rejected_before_writes(
        self,
    ):
        self.prepare()
        target = self.deduplicated / "products.jsonl"
        original = target.read_bytes()
        target.write_bytes(original + b"\n")
        output = self.base / "rejected-output"
        with pytest.raises(ValueError, match="checksum mismatch"):
            self.build(output=output)
        assert not output.exists()
        target.write_bytes(original)
        manifest_path = self.deduplicated / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["manifest_format_version"] = "category-research-raw-1"
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="deduplicated raw snapshot"):
            self.build(output=output)
        assert not output.exists()

    def test_invalid_review_ids_evidence_values_and_context_are_rejected(self):
        self.prepare()
        originals = self.reviews()
        malformed = []
        reviews = deepcopy(originals)
        reviews["products"]["absent-listing"] = reviews["products"].pop("example")
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["evidence"][0]["capture_id"] = (
            "another-listing-capture"
        )
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["attributes"]["composition.chocolate_type"][
            "evidence"
        ][0]["pointer"] = "/missing/evidence"
        malformed.append(reviews)
        reviews = deepcopy(originals)
        reviews["products"]["example"]["attributes"]["composition.cocoa_percentage"][
            "value"
        ] = 101
        malformed.append(reviews)
        reviews = deepcopy(originals)
        next(iter(reviews["prices"].values()))["observed_at"] = "2026-10-03T07:00:00"
        malformed.append(reviews)
        reviews = deepcopy(originals)
        next(iter(reviews["prices"].values()))["available"] = "true"
        malformed.append(reviews)
        for index, reviews in enumerate(malformed):
            output = self.base / ("invalid-review-" + str(index))
            with pytest.raises(ValueError):
                self.build(reviews, output=output)
            assert not output.exists()

    def test_output_cannot_overwrite_or_contain_deduplicated_layer(self):
        self.prepare()
        for output in (
            self.deduplicated,
            self.deduplicated / "standardized",
            self.base,
        ):
            with pytest.raises(ValueError, match="overlap"):
                self.build(output=output)
