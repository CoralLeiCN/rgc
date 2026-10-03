"""Protect training boundaries and interpretation without fitting fabricated data."""

from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from category_processing.model import (ModelContractError, coefficient_percent, fit_encoder,
                             prediction_contrast, split_by_family, transform_rows,
                             validate_candidates)


class CategoryModelContractTests(unittest.TestCase):
    def design(self):
        return {
            "model_design_version": "coffee-pricing-design-1",
            "schema_version": "coffee-schema-1",
            "category": "coffee", "market": "uk",
            "target": {"currency": "GBP", "unit": "GBP_per_100g", "base_quantity": 100},
            "predictors": {
                "quantity.net_weight_g": {
                    "type": "numeric", "transform": "log", "required": True,
                    "missing_policy": "reject", "minimum": 0.01, "unit": "g",
                },
                "identity.brand": {
                    "type": "categorical", "required": True,
                    "missing_policy": "reject", "reference": "training_mode",
                },
                "coffee.roast": {
                    "type": "categorical", "required": True, "missing_policy": "reject",
                    "reference": "dark", "allowed_values": ["dark", "medium", "light"],
                },
                "coffee.decaf_claim": {
                    "type": "presence", "required": True, "missing_policy": "reject",
                    "reference": "absent", "allowed_values": ["present", "absent"],
                },
            },
        }

    def row(self, identifier="a", family="family-a", weight=50, brand="Brand A", **changes):
        row = {
            "observation_id": identifier, "listing_id": "listing-" + identifier,
            "variant_id": "variant-" + identifier, "family_id": family,
            "comparable_group": "bar", "source_role": "retail", "model_eligible": True,
            "target": {"regular_unit_price": 2.0,
                       "log_regular_unit_price": math.log(2.0)},
            "predictors": {
                "quantity.net_weight_g": weight,
                "identity.brand": brand, "coffee.roast": "dark",
                "coffee.decaf_claim": "absent",
            },
        }
        row.update(changes)
        return row

    def training(self):
        first = self.row()
        second = self.row("b", "family-b", 100, "Brand B")
        second["predictors"].update({"coffee.roast": "medium", "coffee.decaf_claim": "present"})
        return [first, second]

    def test_empty_or_ineligible_rows_cannot_fit_encoder(self):
        with self.assertRaisesRegex(ModelContractError, "no reviewed eligible"):
            fit_encoder([], self.design())
        with self.assertRaisesRegex(ModelContractError, "eligibility gate"):
            fit_encoder([self.row(model_eligible=False)], self.design())

    def test_positive_price_and_consistent_log_target_are_required(self):
        for target in (
            {"regular_unit_price": 0, "log_regular_unit_price": 0},
            {"regular_unit_price": 2, "log_regular_unit_price": 2},
            {"regular_unit_price": math.inf, "log_regular_unit_price": math.inf},
        ):
            with self.subTest(target=target), self.assertRaises(ModelContractError):
                validate_candidates([self.row(target=target)], self.design())
        price = 0.5
        self.assertEqual(len(validate_candidates([self.row(target={
            "regular_unit_price": price, "log_regular_unit_price": math.log(price),
        })], self.design())), 1)

    def test_missing_unknown_and_untyped_values_are_not_absence(self):
        for name, value in (("quantity.net_weight_g", "50"),
                            ("quantity.net_weight_g", True),
                            ("identity.brand", None), ("coffee.roast", "unknown"),
                            ("coffee.decaf_claim", "unknown"), ("coffee.decaf_claim", False)):
            row = self.row()
            row["predictors"][name] = value
            with self.subTest(name=name, value=value), self.assertRaises(ModelContractError):
                validate_candidates([row], self.design())

    def test_invalid_identity_and_duplicate_observations_are_rejected(self):
        for changes in ({"family_id": None}, {"variant_id": "unknown"},
                        {"source_role": "unknown"}, {"listing_id": " padded "}):
            with self.subTest(changes=changes), self.assertRaises(ModelContractError):
                validate_candidates([self.row(**changes)], self.design())
        with self.assertRaisesRegex(ModelContractError, "duplicate observation"):
            validate_candidates([self.row(), self.row()], self.design())

    def test_same_physical_variant_cannot_have_conflicting_family_ids(self):
        first = self.row()
        other_seller = self.row("a-other-shop", "different-family")
        other_seller["variant_id"] = first["variant_id"]
        with self.assertRaisesRegex(ModelContractError, "cannot span validation families"):
            split_by_family([first, other_seller])

    def test_family_split_preserves_unique_seller_listings_and_prevents_leakage(self):
        first = self.row()
        other_seller = self.row("a-other-shop", first["family_id"])
        other_seller["variant_id"] = first["variant_id"]
        direct_brand = self.row("a-brand-shop", first["family_id"], source_role="brand")
        direct_brand["variant_id"] = first["variant_id"]
        rows = [first, other_seller, direct_brand, self.row("b", "family-b"),
                self.row("c", "family-c"), self.row("d", "family-d")]
        split = split_by_family(rows, validation_fraction=0.5)
        self.assertEqual(split, split_by_family(reversed(rows), validation_fraction=0.5))
        training_families = {row["family_id"] for row in split["train"]}
        validation_families = {row["family_id"] for row in split["validation"]}
        self.assertFalse(training_families & validation_families)
        partition = split["train"] if first["family_id"] in training_families else split["validation"]
        self.assertEqual(len([row for row in partition if row["variant_id"] == first["variant_id"]]), 3)
        self.assertEqual(len(split["train"]) + len(split["validation"]), len(rows))
        self.assertTrue(split["metadata"]["seller_listings_preserved"])

    def test_one_family_does_not_make_an_independent_holdout(self):
        with self.assertRaisesRegex(ModelContractError, "at least two reviewed families"):
            split_by_family([self.row(), self.row("other", "family-a")])
        for fraction in (0, 1, True, math.nan):
            with self.subTest(fraction=fraction), self.assertRaises(ModelContractError):
                split_by_family(self.training(), validation_fraction=fraction)

    def test_encoder_uses_training_support_and_explicit_references(self):
        rows = self.training()
        original_rows, original_design = deepcopy(rows), self.design()
        fitted = fit_encoder(rows, original_design)
        self.assertEqual(fitted["predictors"]["identity.brand"]["reference"], "Brand A")
        self.assertEqual(fitted["predictors"]["coffee.roast"]["reference"], "dark")
        self.assertEqual(fitted["predictors"]["coffee.roast"]["training_levels"], ["dark", "medium"])
        self.assertEqual(fitted["predictors"]["identity.brand"]["family_support"], {"Brand A": 1, "Brand B": 1})
        self.assertEqual(fitted["training_observation_ids"], ["a", "b"])
        self.assertFalse(fitted["regression_fitted"])
        self.assertFalse(fitted["release_ready"])
        self.assertEqual(rows, original_rows)
        self.assertEqual(original_design, self.design())

    def test_holdout_only_level_cannot_change_the_fitted_encoder(self):
        fitted = fit_encoder(self.training(), self.design())
        original = deepcopy(fitted)
        holdout = self.row("new", "family-new", 75, "Holdout Brand")
        with self.assertRaisesRegex(ModelContractError, "unseen training level"):
            transform_rows([holdout], fitted)
        self.assertEqual(fitted, original)
        self.assertNotIn("Holdout Brand", fitted["predictors"]["identity.brand"]["training_levels"])
        holdout["predictors"]["identity.brand"] = "Brand A"
        holdout["predictors"]["coffee.roast"] = "light"
        with self.assertRaisesRegex(ModelContractError, "unseen training level"):
            transform_rows([holdout], fitted)

    def test_training_only_numeric_range_rejects_unsupported_holdout(self):
        fitted = fit_encoder(self.training(), self.design())
        self.assertEqual(fitted["predictors"]["quantity.net_weight_g"]["training_maximum"], 100)
        with self.assertRaisesRegex(ModelContractError, "outside its training range"):
            transform_rows([self.row("large", "family-large", weight=1000)], fitted)
        self.assertEqual(fitted["predictors"]["quantity.net_weight_g"]["training_maximum"], 100)

    def test_same_fitted_transform_encodes_training_and_supported_holdout(self):
        fitted = fit_encoder(self.training(), self.design())
        transformed = transform_rows(self.training(), fitted)
        expected_columns = ["intercept", "quantity.net_weight_g", "identity.brand=Brand B",
                            "coffee.roast=medium", "coffee.decaf_claim=present"]
        self.assertEqual(transformed["columns"], expected_columns)
        self.assertEqual(transformed["X"], [[1.0, math.log(50), 0.0, 0.0, 0.0],
                                          [1.0, math.log(100), 1.0, 1.0, 1.0]])
        holdout = transform_rows([self.row("new", "family-new", 75)], fitted)
        self.assertEqual(holdout["X"], [[1.0, math.log(75), 0.0, 0.0, 0.0]])
        self.assertEqual(holdout["target_basis"], "log_regular_unit_price")

    def test_no_target_information_is_learned_by_encoder(self):
        rows = self.training()
        fitted = fit_encoder(rows, self.design())
        for row in rows:
            row["target"] = {"regular_unit_price": 99,
                             "log_regular_unit_price": math.log(99)}
        self.assertEqual(fitted, fit_encoder(rows, self.design()))

    def test_category_and_declared_price_unit_are_saved_without_chocolate_fields(self):
        design = self.design()
        design.update(category="coffee", market="uk", schema_version="coffee-schema-1")
        design["target"] = {"currency": "GBP", "unit": "GBP_per_100g", "base_quantity": 100}
        fitted = fit_encoder(self.training(), design)
        self.assertEqual(fitted["category"], "coffee")
        self.assertEqual(fitted["target_definition"], design["target"])
        self.assertEqual(transform_rows(self.training(), fitted)["target_definition"], design["target"])
        self.assertFalse(any("cocoa" in name or "nuts" in name for name in fitted["columns"]))
        contrast = prediction_contrast(math.log(2), math.log(3), target_definition=design["target"])
        self.assertEqual(contrast["target_definition"]["unit"], "GBP_per_100g")

    def test_constant_terms_are_reported_and_omitted(self):
        fitted = fit_encoder([self.row(), self.row("same", "family-other")], self.design())
        self.assertEqual(fitted["columns"], ["intercept"])
        self.assertEqual(set(fitted["dropped_terms"]), set(self.design()["predictors"]))
        self.assertEqual(transform_rows([self.row()], fitted)["X"], [[1.0]])

    def test_unobserved_reference_is_not_silently_replaced(self):
        design = self.design()
        design["predictors"]["coffee.roast"]["reference"] = "light"
        with self.assertRaisesRegex(ModelContractError, "reference has no training support"):
            fit_encoder(self.training(), design)

    def test_missingness_policy_and_transforms_must_be_explicit(self):
        for change in ({"missing_policy": "impute"}, {"required": False}, {"transform": "zscore"}):
            design = self.design()
            design["predictors"]["quantity.net_weight_g"].update(change)
            with self.subTest(change=change), self.assertRaises(ModelContractError):
                fit_encoder(self.training(), design)

    def test_log_coefficient_and_context_contrast_use_multiplicative_scale(self):
        self.assertAlmostEqual(coefficient_percent(math.log(1.2)), 20)
        self.assertAlmostEqual(coefficient_percent(math.log(1.2), 2), 44)
        self.assertAlmostEqual(coefficient_percent(math.log(0.8)), -20)
        contrast = prediction_contrast(math.log(2), math.log(3))
        self.assertAlmostEqual(contrast["difference_unit_price"], 1)
        self.assertAlmostEqual(contrast["difference_percent"], 50)
        self.assertEqual(contrast["estimate_type"], "conditional_median_price")
        self.assertEqual(contrast["interpretation"], "conditional_price_association")
        self.assertIsNone(contrast["uncertainty"])
        self.assertTrue(contrast["support_evaluation_required"])

    def test_overflow_nan_and_price_underflow_are_rejected(self):
        for beta in (math.inf, math.nan, 1000, "0.2", True):
            with self.subTest(beta=beta), self.assertRaises(ModelContractError):
                coefficient_percent(beta)
        for first, second in ((1000, 0), (0, -1000), (0, math.nan)):
            with self.subTest(first=first, second=second), self.assertRaises(ModelContractError):
                prediction_contrast(first, second)


if __name__ == "__main__":
    unittest.main()
