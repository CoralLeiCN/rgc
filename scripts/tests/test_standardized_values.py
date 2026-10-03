"""Check canonical values and typed states independently of source extraction."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
from chocolate_standardization.values import (
    standardize_value,
    unknown_attribute,
    validate_product,
)
from dataset_contracts import resolve_contract_root

ROOT = Path(__file__).resolve().parents[2]


class ChocolateStandardizedValueTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        schema_root = resolve_contract_root(offline=True)
        self.profile = json.loads((schema_root / "profile.json").read_text())
        self.mappings = json.loads((schema_root / "source-mappings.json").read_text())

    def value(self, name, original, unit=None):
        return standardize_value(name, original, self.profile, self.mappings, unit)

    def product(self):
        return {
            "schema_version": self.profile["schema_version"],
            "dataset_version": "fixture-standardized-1",
            "source_dataset_version": "fixture-deduplicated-1",
            "listing_id": "fixture-listing",
            "source_listing_ids": ["fixture-listing"],
            "source_role": "retail",
            "source_key": "fixture-shop",
            "brand": None,
            "retailer": None,
            "review_status": "unreviewed",
            "unmapped_claims": [],
            "attributes": {
                name: unknown_attribute(definition)
                for name, definition in self.profile["attributes"].items()
            },
        }

    def known(self, name, value):
        attribute = unknown_attribute(self.profile["attributes"][name])
        attribute.update(
            value=value,
            status="known",
            review_status="reviewed",
            method="fixture_review",
            evidence=[
                {
                    "capture_id": "fixture-capture",
                    "pointer": "/raw_record/information/value",
                }
            ],
        )
        return attribute

    def test_mass_conversions_require_explicit_supported_units(self):
        assert self.value("quantity.total_edible_weight_g", "0.2", "kg") == 200
        assert self.value("quantity.total_edible_weight_g", 200000, "mg") == 200
        for original, unit in (
            (1, "lb"),
            (True, "g"),
            (0, "g"),
            (-1, "g"),
            (math.inf, "g"),
        ):
            with pytest.raises(ValueError):
                self.value("quantity.total_edible_weight_g", original, unit)

    def test_duration_and_temperature_convert_without_calendar_guessing(self):
        assert self.value("storage.temperature_max_c", 68, "degF") == 20
        assert self.value("storage.temperature_min_c", 32, "°F") == 0
        assert self.value("storage.shelf_life_days", 2, "weeks") == 14
        with pytest.raises(ValueError):
            self.value("storage.shelf_life_days", 1, "month")
        with pytest.raises(ValueError):
            self.value("storage.temperature_min_c", 273.15, "kelvin")

    def test_unicode_aliases_and_presence_do_not_guess_unknown_as_absent(self):
        assert (
            self.value("composition.chocolate_type", "ＤＡＲＫ ＣＨＯＣＯＬＡＴＥ")
            == "dark"
        )
        assert self.value("dietary.vegan_claim", "suitable_for_vegans") == "present"
        assert self.value("composition.nuts_presence", "ABSENT") == "absent"
        for original in (False, "unknown", "not mentioned", "may be present"):
            with pytest.raises(ValueError):
                self.value("composition.nuts_presence", original)

    def test_country_aliases_produce_one_canonical_country_without_losing_raw_evidence(
        self,
    ):
        original = ["ivory coast", "Ecuador", "ecuador"]
        before = deepcopy(original)
        assert self.value("origin.cocoa_countries", original) == [
            "Côte d'Ivoire",
            "Ecuador",
        ]
        assert original == before
        assert self.value("origin.manufacture_country", " UK ") == "United Kingdom"
        with pytest.raises(ValueError):
            self.value("origin.cocoa_countries", ["Unknown New Country"])

    def test_gtin_checks_digits_length_and_checksum(self):
        assert self.value("identity.gtin", "4006381333931") == "4006381333931"
        assert self.value("identity.gtin", "12345670") == "12345670"
        for original in (
            "4006381333932",
            "400638133",
            "４００６３８１３３３９３１",
            "1234567x",
        ):
            with pytest.raises(ValueError):
                self.value("identity.gtin", original)

    def test_date_values_require_valid_unambiguous_calendar_dates(self):
        assert self.value("storage.best_before_date", "2028-02-29") == "2028-02-29"
        for original in ("03/10/2026", "2026-02-29", "2026-13-01", "20261003"):
            with pytest.raises(ValueError):
                self.value("storage.best_before_date", original)

    def test_numeric_and_integer_types_respect_category_limits(self):
        assert self.value("composition.cocoa_percentage", "70.5") == 70.5
        assert self.value("quantity.pack_count", "3") == 3
        for name, original in (
            ("composition.cocoa_percentage", 101),
            ("composition.cocoa_percentage", -1),
            ("composition.cocoa_percentage", math.nan),
            ("quantity.pack_count", 2.5),
            ("quantity.pack_count", True),
        ):
            with pytest.raises(ValueError):
                self.value(name, original)

    def test_source_text_stays_verbatim_and_lists_canonicalize_recognized_labels(self):
        original = "  Ingrédients: chocolat noir; café.\n\tKeep this source wording. "
        assert self.value("composition.ingredients_text", original) == original
        assert self.value(
            "composition.nut_types", ["hazelnuts", "almond", "almonds"]
        ) == ["almond", "hazelnut"]
        with pytest.raises(ValueError):
            self.value("composition.nut_types", ["new unrecognized nut"])

    def test_runtime_validation_rejects_missing_extra_and_inconsistent_state(self):
        validate_product(self.product(), self.profile, self.mappings)
        cases = []
        product = self.product()
        del product["attributes"]["identity.name"]
        cases.append(product)
        product = self.product()
        product["attributes"]["undefined.category_attribute"] = unknown_attribute({})
        cases.append(product)
        product = self.product()
        product["attributes"]["dietary.vegan_claim"]["value"] = "absent"
        cases.append(product)
        product = self.product()
        product["attributes"]["dietary.vegan_claim"].update(
            status="known", value="present"
        )
        cases.append(product)
        product = self.product()
        product["attributes"]["dietary.vegan_claim"].update(status="conflict")
        cases.append(product)
        for index, product in enumerate(cases):
            with pytest.raises(ValueError):
                validate_product(product, self.profile, self.mappings)

    def test_known_output_values_must_use_canonical_typed_units_and_vocabulary(self):
        product = self.product()
        product["attributes"]["composition.chocolate_type"] = self.known(
            "composition.chocolate_type", "dark"
        )
        validate_product(product, self.profile, self.mappings)
        for name, value, changes in (
            ("composition.cocoa_percentage", "70", {}),
            ("composition.cocoa_percentage", True, {}),
            ("composition.cocoa_percentage", math.inf, {}),
            ("composition.chocolate_type", "dark chocolate", {}),
            ("quantity.total_edible_weight_g", 200, {"unit": "kg"}),
            ("composition.chocolate_type", "dark", {"scope": "invented_scope"}),
        ):
            product = self.product()
            product["attributes"][name] = self.known(name, value)
            product["attributes"][name].update(changes)
            with pytest.raises(ValueError):
                validate_product(product, self.profile, self.mappings)

    def test_explicit_conflict_and_not_applicable_require_evidence_and_null_value(self):
        for status in ("conflict", "not_applicable"):
            product = self.product()
            product["attributes"]["packaging.materials"].update(
                status=status,
                review_status="reviewed",
                evidence=[{"capture_id": "fixture-capture", "pointer": "/raw_record"}],
            )
            validate_product(product, self.profile, self.mappings)
            product["attributes"]["packaging.materials"]["value"] = []
            with pytest.raises(ValueError):
                validate_product(product, self.profile, self.mappings)
