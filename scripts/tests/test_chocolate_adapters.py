"""Regressions for conservative chocolate source interpretation."""

import pytest
from category_processing.adapters import (
    extract_chocolate_capture as portable_extract_capture,
)
from chocolate_cleanup.adapters import extract_capture, parse_weight


@pytest.mark.parametrize("extractor", [extract_capture, portable_extract_capture],
                         ids=["canonical", "portable"])
@pytest.mark.parametrize("name,expected", [
    ("Blonde Chocolate Bar", "blonde"),
    ("BLOND CHOCOLATE BAR", "blonde"),
    ("Milk Chocolate and Dark Chocolate Selection", "mixed"),
    ("Milk & Dark Chocolate Selection", "mixed"),
    ("Milk, Dark & White Chocolate Selection", "mixed"),
    ("Milk and Dark Chocolate Gift Bag", "mixed"),
    ("Blonde Chocolate & Ruby Chocolate Collection", "mixed"),
    ("Dark Chocolate and Dark Chocolate Selection", "dark"),
    ("Milk Chocolate Selection", "milk"),
    ("Dark Chocolate Bar with White Chocolate Chips", None),
    ("Milk Chocolate Selection with Dark Chocolate Chips", None),
    ("Milk Chocolate and Dark Chocolate Chips Bar", None),
    ("Milk Chocolate and Dark Chocolate Chips Selection", None),
    ("Milk & Dark Chocolate Chips Selection", None),
    ("Chocolate Selection", None),
    ("Blonde Caramel Gift Box", None),
    ("Cadbury Dairy Milk", None),
])
def test_chocolate_title_types_preserve_selection_scope_and_evidence(extractor, name, expected):
    result = extractor({"raw_record": {"identity": {"name": name}, "information": {}}})
    features = [feature for feature in result["features"] if feature["name"] == "chocolate_type"]
    assert len(features) == 1
    feature = features[0]
    assert feature["value"] == expected
    assert feature["status"] == ("known" if expected else "unknown")
    if expected:
        assert feature["raw_pointer"] == "/raw_record/identity/name"
        assert feature["raw_value"] == name
        assert feature["method"] == "explicit_product_name_type"


class ChocolateAdapterTests:
    def extract(self, text):
        return extract_capture(
            {
                "raw_record": {
                    "identity": {"name": "Chocolate"},
                    "information": {"body_html": "<p>" + text + "</p>"},
                }
            }
        )

    def values(self, result, name):
        return [
            feature["value"]
            for feature in result["features"]
            if feature["name"] == name
        ]

    def test_grouped_mass_never_becomes_numeric_suffix(self):
        assert parse_weight("Chocolate 1,200g") is None
        assert parse_weight("Chocolate 1, 200g") is None
        assert parse_weight("Chocolate 1200g")["total_edible_weight_g"] == 1200

    def test_generic_fair_trade_is_distinct_from_named_fairtrade(self):
        wording = "Fair Trade Verified to World Fair Trade Organisation Standard"
        result = self.extract(wording)
        assert self.values(result, "fairtrade_claim") == ["unknown"]
        assert self.values(result, "fair_trade_claim") == ["present"]
        assert wording in self.values(result, "claim_text")

    def test_named_fairtrade_claim_remains_recognized(self):
        result = self.extract("Fairtrade certified cocoa")
        assert self.values(result, "fairtrade_claim") == ["present"]
        assert self.values(result, "fair_trade_claim") == []

    def test_negated_vegan_suitability_is_not_an_affirmative_claim(self):
        for wording in (
            "Not suitable for vegan diets",
            "Not vegan",
            "Non-vegan",
            "May not be suitable for vegans",
        ):
            result = self.extract(wording)
            assert self.values(result, "vegan_claim") == ["unknown"]
            assert wording in self.values(result, "claim_text")

    def test_affirmative_vegan_suitability_is_recognized(self):
        result = self.extract("Suitable for vegans")
        assert self.values(result, "vegan_claim") == ["present"]

    def test_integer_shopify_price_without_unit_is_not_assumed_to_be_pounds(self):
        capture = {
            "raw_record": {
                "identity": {"name": "Chocolate 100g"},
                "information": {
                    "selected_variant": {"price": 1000},
                    "catalogue_retrieval_currency": "GBP",
                },
            }
        }
        result = extract_capture(capture)
        assert len(result["prices"]) == 1
        assert result["prices"][0]["displayed_price"] is None
        assert result["prices"][0]["raw_value"] == 1000
        assert any("major/minor" in warning for warning in result["warnings"])

    def test_explicit_minor_unit_prices_are_converted_and_original_is_retained(self):
        capture = {
            "raw_record": {
                "identity": {"name": "Chocolate"},
                "information": {
                    "selected_variant": {"price": 1000, "compare_at_price": 1200},
                    "source_price_unit": "minor",
                },
            }
        }
        result = extract_capture(capture)
        price = result["prices"][0]
        assert price["displayed_price"] == 10
        assert price["reference_price"] == 12
        assert price["raw_value"] == 1000
        assert price["reference_price_raw_value"] == 1200
