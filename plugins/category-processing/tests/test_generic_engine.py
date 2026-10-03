"""Exercise nonfood profiles with explicit item, currency and tax-price bases."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.model import validate_candidates
from category_processing.pipeline import build_silver_dataset
from category_processing.price_policy import TARGET_PRICE_POLICY
from category_processing.profiles import load_profile
from fixture_archive import import_document

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def attribute_schema(definition):
    value = {"type": "string" if definition["type"] == "enum" else definition["type"]}
    if definition["type"] == "enum":
        value["enum"] = definition["allowed_values"]
    if definition["type"] == "string":
        value["minLength"] = 1
    for bound in ("minimum", "maximum"):
        if bound in definition:
            value[bound] = definition[bound]
    properties = {
        "value": {"anyOf": [{"type": "null"}, deepcopy(value)]},
        "unit": {"const": definition.get("unit")},
        "status": {"enum": ["known", "unknown", "conflict", "not_applicable"]},
        "qualifier": {"type": ["string", "null"]},
        "scope": {"enum": ["product", "ingredient", "brand", "packaging", "packaging_component", "observation"]},
        "evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
        "method": {"type": "string", "minLength": 1},
        "review_status": {"enum": ["unreviewed", "reviewed", "needs_review"]},
    }
    return {"type": "object", "additionalProperties": False, "required": list(properties),
            "properties": properties, "allOf": [
                {"if": {"properties": {"status": {"const": "known"}}},
                 "then": {"properties": {"value": value, "evidence": {"minItems": 1}}}},
                {"if": {"properties": {"status": {"enum": ["unknown", "conflict", "not_applicable"]}}},
                 "then": {"properties": {"value": {"type": "null"}}}},
                {"if": {"properties": {"status": {"enum": ["conflict", "not_applicable"]}}},
                 "then": {"properties": {"evidence": {"minItems": 1}}}},
            ]}


class GenericCategoryEngineTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.archive = self.base / "collections"
        self.output = self.base / "silver"
        self.profile_root = self.base / "furniture-profile"

    def profile(self, currency="USD", price_unit="major", minor_unit_factor=None,
                allowed_tax_bases=None):
        attributes = {
            "identity.name": {"type": "string", "unit": None, "standardization_rule": "identity_text"},
            "furniture.group": {"type": "enum", "unit": None, "allowed_values": ["chair", "table"],
                                "standardization_rule": "controlled_vocabulary"},
            "quantity.item_count": {"type": "integer", "unit": "item", "minimum": 1,
                                    "standardization_rule": "explicit_item_count"},
            "furniture.material": {"type": "enum", "unit": None, "allowed_values": ["wood", "metal"],
                                   "standardization_rule": "controlled_vocabulary"},
            "furniture.width_m": {"type": "number", "unit": "m", "minimum": 0.001,
                                  "standardization_rule": "explicit_length"},
        }
        version = "furniture-schema-fixture-1"
        profile = {"schema_version": version, "category": "furniture", "market": "us",
                   "attribute_count": len(attributes), "attributes": attributes}
        mappings = {"schema_version": version, "mapping_version": "furniture-mappings-fixture-1",
                    "aliases": {}, "unit_conversions": {"m": {"cm": 0.01}}}
        design = {"schema_version": version, "model_design_version": "furniture-design-fixture-1",
                  "category": "furniture", "market": "us",
                  "target": {**TARGET_PRICE_POLICY, "name": "log_regular_unit_price", "currency": currency,
                             "unit": currency + "_per_item", "quantity_attribute": "quantity.item_count",
                             "base_quantity": 1},
                  "predictors": {
                      "furniture.material": {"type": "categorical", "required": True,
                                             "missing_policy": "reject", "reference": "wood",
                                             "allowed_values": ["wood", "metal"]},
                      "furniture.width_m": {"type": "numeric", "required": True,
                                            "missing_policy": "reject", "unit": "m"},
                  }}
        if allowed_tax_bases is not None:
            design["eligibility"] = {"allowed_tax_bases": allowed_tax_bases}
        recipe = {"schema_version": version, "pipeline_version": "furniture-pipeline-fixture-1",
                  "pipeline_format_version": "category-processing-profile-1", "category": "furniture",
                  "market": "us", "adapter": "structured", "group_attribute": "furniture.group",
                  "fields": [
                      {"attribute": "identity.name", "pointer": "/raw_record/identity/name"},
                      {"attribute": "furniture.group", "pointer": "/raw_record/information/group"},
                      {"attribute": "quantity.item_count", "pointer": "/raw_record/information/count", "unit": "item"},
                      {"attribute": "furniture.material", "pointer": "/raw_record/information/material"},
                      {"attribute": "furniture.width_m", "pointer": "/raw_record/information/width_cm", "unit": "cm"},
                  ],
                  "quantity": {"attribute": "quantity.item_count", "unit": "item", "base_quantity": 1},
                  "price": {"target_policy": dict(TARGET_PRICE_POLICY), "price_unit": price_unit, "amount_pointer": "/raw_record/information/price/amount",
                            "regular_price_pointer": "/raw_record/information/price/regular_amount",
                            "reference_price_pointer": "/raw_record/information/price/reference_amount",
                            "currency_pointer": "/raw_record/information/price/currency",
                            "observed_at_pointer": "/raw_record/information/price/observed_at",
                            "available_pointer": "/raw_record/information/price/available",
                            "tax_basis_pointer": "/raw_record/information/price/tax_basis"},
                  "source_roles": {"fixture-shop": {"source_role": "retail", "retailer": "Fixture Furniture Shop"}},
                  "review_format_version": "category-processing-reviews-1"}
        if minor_unit_factor is not None:
            recipe["price"]["minor_unit_factor"] = minor_unit_factor
        properties = {name: {"type": "string", "minLength": 1} for name in
                      ("dataset_version", "source_dataset_version", "listing_id", "seller_uid", "source_key")}
        properties.update({
            "schema_version": {"const": version}, "category": {"const": "furniture"}, "market": {"const": "us"},
            "source_listing_ids": {"type": "array", "minItems": 1, "uniqueItems": True,
                                   "items": {"type": "string", "minLength": 1}},
            "source_role": {"enum": ["brand", "retail", "unknown"]},
            "brand": {"type": ["string", "null"]}, "retailer": {"type": ["string", "null"]},
            "attributes": {"type": "object", "additionalProperties": False, "required": list(attributes),
                           "properties": {name: attribute_schema(definition) for name, definition in attributes.items()}},
            "unmapped_claims": {"type": "array", "items": {"type": "object"}},
            "review_status": {"enum": ["unreviewed", "reviewed", "needs_review"]},
        })
        validator = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
                     "additionalProperties": False, "properties": properties, "required": list(properties),
                     "$defs": {"evidence": {"type": "object", "additionalProperties": False,
                                            "required": ["capture_id", "pointer"],
                                            "properties": {"capture_id": {"type": "string", "minLength": 1},
                                                           "pointer": {"type": "string"}}}}}
        self.profile_root.mkdir(exist_ok=True)
        for filename, content in (("profile.json", profile), ("source-mappings.json", mappings),
                                  ("model-design.json", design), ("pipeline.json", recipe),
                                  ("product.schema.json", validator)):
            (self.profile_root / filename).write_text(json.dumps(content) + "\n", encoding="utf-8")

    def collect(self, amount=240, currency="USD", tax_basis="consumer_tax_included", count=2,
                regular_amount=None, reference_amount=None):
        raw = {"product_id": "fixture-chair", "source_key": "fixture-shop",
               "source_url": "https://fixture.example.test/products/chair",
               "identity": {"name": "Pair of oak chairs", "source_product_id": "chair", "source_variant_id": "oak"},
               "information": {"group": "chair", "material": "wood", "width_cm": 120,
                               "price": {"amount": amount, "regular_amount": amount if regular_amount is None else regular_amount,
                                         "reference_amount": reference_amount, "currency": currency,
                                         "observed_at": "2026-10-03T12:00:00Z", "available": True,
                                         "tax_basis": tax_basis}}}
        if count is not None:
            raw["information"]["count"] = count
        import_document({"study": {"category": "furniture", "market": "us"}, "products": [raw]}, self.archive)

    def rows(self, name):
        return [json.loads(line) for line in (self.output / (name + ".jsonl")).read_text().splitlines()]

    def build(self, reviews=None):
        return build_silver_dataset(self.archive, self.output, self.profile_root, reviews=reviews)

    def reviews(self):
        product = self.rows("products")[0]
        common = {"reviewed_by": "Fixture reviewer", "reason": "Explicit source evidence supports this fixture decision."}
        decision = {**common, "variant_id": "oak-chair", "family_id": "chair-family", "in_scope": True,
                    "evidence": deepcopy(product["attributes"]["identity.name"]["evidence"]),
                    "attributes": {name: {**common, "value": attribute["value"], "status": "known",
                                          "evidence": deepcopy(attribute["evidence"])}
                                   for name, attribute in product["attributes"].items() if attribute["status"] == "known"}}
        prices = {price["observation_id"]: {**common, "regular_price": price["regular_price"],
                                           "currency": price["currency"], "tax_basis": price["tax_basis"],
                                           "observed_at": price["observed_at"], "available": price["available"],
                                           "evidence": deepcopy(price["evidence"])} for price in self.rows("prices")}
        return {"review_format_version": "category-processing-reviews-1",
                "products": {product["seller_uid"]: decision}, "prices": prices}

    def test_nonfood_per_item_dollars_use_reviewed_explicit_tax_basis(self):
        self.profile(allowed_tax_bases=["consumer_tax_included"])
        self.collect(tax_basis="consumer_tax_included")
        original = {path: path.read_bytes() for path in self.archive.rglob("*") if path.is_file()}
        self.build()
        assert (self.rows("model-inputs")) == ([])
        self.build(self.reviews())
        row = self.rows("model-inputs")[0]
        assert (row["comparable_group"]) == ("chair")
        assert (row["predictors"]["furniture.width_m"]) == (1.2)
        assert (row["target"]["regular_unit_price"]) == (120)
        assert round(abs((row["target"]["log_regular_unit_price"]) - (math.log(120))), 7) == 0
        design = json.loads((self.profile_root / "model-design.json").read_text())
        assert (validate_candidates([row], design)) == ([row])
        assert (original) == ({path: path.read_bytes() for path in self.archive.rglob("*") if path.is_file()})
        assert not (any("coffee" in name or "cocoa" in name for name in self.rows("products")[0]["attributes"]))

    def test_explicit_minor_factors_support_three_and_zero_decimal_currencies(self):
        for currency, amount, factor, expected in (("KWD", 12345, 1000, 12.345), ("JPY", 12345, 1, 12345)):
            self.profile(currency=currency, price_unit="minor", minor_unit_factor=factor)
            self.collect(amount=amount, currency=currency)
            self.build()
            self.build(self.reviews())
            assert (self.rows("prices")[0]["regular_price"]) == (expected)
            assert round(abs((self.rows("model-inputs")[0]["target"]["regular_unit_price"]) - (expected / 2)), 7) == 0
            # Independent archives keep each reviewed study's currency separate.
            self.archive = self.base / (currency + "-next-collections")

    def test_existing_minor_default_and_major_amounts_are_preserved(self):
        self.profile(price_unit="minor")
        self.collect(amount=12345)
        self.build()
        assert (self.rows("prices")[0]["regular_price"]) == (123.45)
        self.profile(price_unit="major", minor_unit_factor=1000)
        self.build()
        assert (self.rows("prices")[0]["regular_price"]) == (12345)

    def test_symbols_do_not_infer_currency_or_relabel_gbp_as_dollars(self):
        self.profile()
        for index, amount in enumerate(("$240", "£240", "GBP 240", "240,00")):
            self.collect(amount=amount)
            self.build()
            assert (self.rows("prices")[0]["regular_price"]) is None
            assert (self.rows("model-inputs")) == ([])
            self.archive = self.base / ("invalid-money-" + str(index))
        self.profile(currency="GBP")
        self.archive = self.base / "gbp-collections"
        self.collect(amount="£240", currency="GBP")
        self.build()
        assert (self.rows("prices")[0]["regular_price"]) == (240)

    def test_gbp_regular_and_reference_prefixes_cannot_become_dollar_prices(self):
        self.profile()
        self.collect(regular_amount="£250", reference_amount="GBP 300")
        self.build()
        price = self.rows("prices")[0]
        assert (price["displayed_price"]) == (240)
        assert (price["regular_price"]) is None
        assert (price["reference_price"]) is None
        preserved = self.rows("source-listings")[0]["captures"][0]["raw_record"]["information"]["price"]
        assert (preserved["regular_amount"]) == ("£250")
        assert (preserved["reference_amount"]) == ("GBP 300")

    def test_invalid_minor_factors_fail_before_existing_output_changes(self):
        self.output.mkdir()
        marker = self.output / "prior-snapshot.txt"
        marker.write_bytes(b"Preserve the previous snapshot.\n")
        for factor in (0, -1, True, "100", math.inf, math.nan, [], {}):
            self.profile(price_unit="minor", minor_unit_factor=factor)
            with pytest.raises(ValueError):
                self.build()
            assert (list(self.output.iterdir())) == ([marker])
            assert (marker.read_bytes()) == (b"Preserve the previous snapshot.\n")

    def test_tax_policy_rejects_unresolved_mixed_and_conflicting_target_bases(self):
        for policy in ([], ["unknown"], ["unresolved"], ["not_applicable"], ["conflict"], [" "],
                       [True], "consumer_tax_included", ["consumer_tax_excluded", "consumer_tax_included"]):
            self.profile(allowed_tax_bases=policy)
            with pytest.raises(ValueError, match="select one resolved tax basis"):
                load_profile(self.profile_root)
        self.profile(allowed_tax_bases=["consumer_tax_included"])
        path = self.profile_root / "model-design.json"
        design = json.loads(path.read_text())
        design["target"]["tax_basis"] = "consumer_tax_excluded"
        path.write_text(json.dumps(design) + "\n")
        with pytest.raises(ValueError, match="tax_basis"):
            load_profile(self.profile_root)

    def test_tax_default_missing_item_count_and_partial_reviews_keep_rows_ineligible(self):
        self.profile()
        self.collect(tax_basis="consumer_tax_excluded", count=None)
        self.build()
        reviews = self.reviews()
        self.build(reviews)
        reasons = self.rows("training-candidates")[0]["exclusion_reasons"]
        assert ("observation_quantity_unreviewed") in (reasons)
        assert ("currency_or_tax_basis_unsupported") in (reasons)
        assert (self.rows("model-inputs")) == ([])
        assert (self.rows("products")[0]["attributes"]["quantity.item_count"]["value"]) is None
        self.archive = self.base / "complete-collections"
        self.collect()
        self.build()
        reviews = self.reviews()
        next(iter(reviews["prices"].values())).pop("tax_basis")
        self.build(reviews)
        assert ("regular_price_context_review_incomplete") in (self.rows("training-candidates")[0]["exclusion_reasons"])
        assert (self.rows("model-inputs")) == ([])
