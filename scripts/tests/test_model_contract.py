"""Protect training boundaries and interpretation without fitting fabricated data."""

import math
from copy import deepcopy
from pathlib import Path

import pytest
from chocolate_model import (
    ModelContractError,
    coefficient_percent,
    fit_encoder,
    prediction_contrast,
    split_by_family,
    transform_rows,
    validate_candidates,
)

ROOT = Path(__file__).resolve().parents[2]


class ChocolateModelContractTests:
    def design(self):
        return {
            "model_design_version": "chocolate-model-design-1",
            "schema_version": "chocolate-schema-1",
            "predictors": {
                "quantity.total_edible_weight_g": {
                    "type": "numeric",
                    "transform": "log",
                    "required": True,
                    "missing_policy": "reject",
                    "minimum": 0.01,
                    "unit": "g",
                },
                "identity.brand": {
                    "type": "categorical",
                    "required": True,
                    "missing_policy": "reject",
                    "reference": "training_mode",
                },
                "identity.chocolate_type": {
                    "type": "categorical",
                    "required": True,
                    "missing_policy": "reject",
                    "reference": "dark",
                    "allowed_values": ["dark", "milk", "white"],
                },
                "claims.vegan": {
                    "type": "presence",
                    "required": True,
                    "missing_policy": "reject",
                    "reference": "absent",
                    "allowed_values": ["present", "absent"],
                },
            },
        }

    def row(
        self, identifier="a", family="family-a", weight=50, brand="Brand A", **changes
    ):
        row = {
            "observation_id": identifier,
            "listing_id": "listing-" + identifier,
            "variant_id": "variant-" + identifier,
            "family_id": family,
            "comparable_group": "bar",
            "source_role": "retail",
            "model_eligible": True,
            "target": {
                "regular_price_per_100g_gbp": 2.0,
                "log_regular_price_per_100g_gbp": math.log(2.0),
            },
            "predictors": {
                "quantity.total_edible_weight_g": weight,
                "identity.brand": brand,
                "identity.chocolate_type": "dark",
                "claims.vegan": "absent",
            },
        }
        row.update(changes)
        return row

    def training(self):
        first = self.row()
        second = self.row("b", "family-b", 100, "Brand B")
        second["predictors"].update(
            {"identity.chocolate_type": "milk", "claims.vegan": "present"}
        )
        return [first, second]

    def test_empty_or_ineligible_rows_cannot_fit_encoder(self):
        with pytest.raises(ModelContractError, match="no reviewed eligible"):
            fit_encoder([], self.design())
        with pytest.raises(ModelContractError, match="eligibility gate"):
            fit_encoder([self.row(model_eligible=False)], self.design())

    def test_positive_price_and_consistent_log_target_are_required(self):
        for target in (
            {"regular_price_per_100g_gbp": 0, "log_regular_price_per_100g_gbp": 0},
            {"regular_price_per_100g_gbp": 2, "log_regular_price_per_100g_gbp": 2},
            {
                "regular_price_per_100g_gbp": math.inf,
                "log_regular_price_per_100g_gbp": math.inf,
            },
        ):
            with pytest.raises(ModelContractError):
                validate_candidates([self.row(target=target)], self.design())
        price = 0.5
        assert (
            len(
                validate_candidates(
                    [
                        self.row(
                            target={
                                "regular_price_per_100g_gbp": price,
                                "log_regular_price_per_100g_gbp": math.log(price),
                            }
                        )
                    ],
                    self.design(),
                )
            )
            == 1
        )

    def test_missing_unknown_and_untyped_values_are_not_absence(self):
        for name, value in (
            ("quantity.total_edible_weight_g", "50"),
            ("quantity.total_edible_weight_g", True),
            ("identity.brand", None),
            ("identity.chocolate_type", "unknown"),
            ("claims.vegan", "unknown"),
            ("claims.vegan", False),
        ):
            row = self.row()
            row["predictors"][name] = value
            with pytest.raises(ModelContractError):
                validate_candidates([row], self.design())

    def test_invalid_identity_and_duplicate_observations_are_rejected(self):
        for changes in (
            {"family_id": None},
            {"variant_id": "unknown"},
            {"source_role": "unknown"},
            {"listing_id": " padded "},
        ):
            with pytest.raises(ModelContractError):
                validate_candidates([self.row(**changes)], self.design())
        with pytest.raises(ModelContractError, match="duplicate observation"):
            validate_candidates([self.row(), self.row()], self.design())

    def test_same_physical_variant_cannot_have_conflicting_family_ids(self):
        first = self.row()
        other_seller = self.row("a-other-shop", "different-family")
        other_seller["variant_id"] = first["variant_id"]
        with pytest.raises(ModelContractError, match="cannot span validation families"):
            split_by_family([first, other_seller])

    def test_family_split_preserves_unique_seller_listings_and_prevents_leakage(self):
        first = self.row()
        other_seller = self.row("a-other-shop", first["family_id"])
        other_seller["variant_id"] = first["variant_id"]
        direct_brand = self.row("a-brand-shop", first["family_id"], source_role="brand")
        direct_brand["variant_id"] = first["variant_id"]
        rows = [
            first,
            other_seller,
            direct_brand,
            self.row("b", "family-b"),
            self.row("c", "family-c"),
            self.row("d", "family-d"),
        ]
        split = split_by_family(rows, validation_fraction=0.5)
        assert split == split_by_family(reversed(rows), validation_fraction=0.5)
        training_families = {row["family_id"] for row in split["train"]}
        validation_families = {row["family_id"] for row in split["validation"]}
        assert not training_families & validation_families
        partition = (
            split["train"]
            if first["family_id"] in training_families
            else split["validation"]
        )
        assert (
            len([row for row in partition if row["variant_id"] == first["variant_id"]])
            == 3
        )
        assert len(split["train"]) + len(split["validation"]) == len(rows)
        assert split["metadata"]["seller_listings_preserved"]

    def test_one_family_does_not_make_an_independent_holdout(self):
        with pytest.raises(ModelContractError, match="at least two reviewed families"):
            split_by_family([self.row(), self.row("other", "family-a")])
        for fraction in (0, 1, True, math.nan):
            with pytest.raises(ModelContractError):
                split_by_family(self.training(), validation_fraction=fraction)

    def test_encoder_uses_training_support_and_explicit_references(self):
        rows = self.training()
        original_rows, original_design = deepcopy(rows), self.design()
        fitted = fit_encoder(rows, original_design)
        assert fitted["predictors"]["identity.brand"]["reference"] == "Brand A"
        assert fitted["predictors"]["identity.chocolate_type"]["reference"] == "dark"
        assert fitted["predictors"]["identity.chocolate_type"]["training_levels"] == [
            "dark",
            "milk",
        ]
        assert fitted["predictors"]["identity.brand"]["family_support"] == {
            "Brand A": 1,
            "Brand B": 1,
        }
        assert fitted["training_observation_ids"] == ["a", "b"]
        assert not fitted["regression_fitted"]
        assert not fitted["release_ready"]
        assert rows == original_rows
        assert original_design == self.design()

    def test_holdout_only_level_cannot_change_the_fitted_encoder(self):
        fitted = fit_encoder(self.training(), self.design())
        original = deepcopy(fitted)
        holdout = self.row("new", "family-new", 75, "Holdout Brand")
        with pytest.raises(ModelContractError, match="unseen training level"):
            transform_rows([holdout], fitted)
        assert fitted == original
        assert (
            "Holdout Brand"
            not in fitted["predictors"]["identity.brand"]["training_levels"]
        )
        holdout["predictors"]["identity.brand"] = "Brand A"
        holdout["predictors"]["identity.chocolate_type"] = "white"
        with pytest.raises(ModelContractError, match="unseen training level"):
            transform_rows([holdout], fitted)

    def test_training_only_numeric_range_rejects_unsupported_holdout(self):
        fitted = fit_encoder(self.training(), self.design())
        assert (
            fitted["predictors"]["quantity.total_edible_weight_g"]["training_maximum"]
            == 100
        )
        with pytest.raises(ModelContractError, match="outside its training range"):
            transform_rows([self.row("large", "family-large", weight=1000)], fitted)
        assert (
            fitted["predictors"]["quantity.total_edible_weight_g"]["training_maximum"]
            == 100
        )

    def test_same_fitted_transform_encodes_training_and_supported_holdout(self):
        fitted = fit_encoder(self.training(), self.design())
        transformed = transform_rows(self.training(), fitted)
        expected_columns = [
            "intercept",
            "quantity.total_edible_weight_g",
            "identity.brand=Brand B",
            "identity.chocolate_type=milk",
            "claims.vegan=present",
        ]
        assert transformed["columns"] == expected_columns
        assert transformed["X"] == [
            [1.0, math.log(50), 0.0, 0.0, 0.0],
            [1.0, math.log(100), 1.0, 1.0, 1.0],
        ]
        holdout = transform_rows([self.row("new", "family-new", 75)], fitted)
        assert holdout["X"] == [[1.0, math.log(75), 0.0, 0.0, 0.0]]
        assert holdout["target_basis"] == "log_regular_price_per_100g_gbp"

    def test_no_target_information_is_learned_by_encoder(self):
        rows = self.training()
        fitted = fit_encoder(rows, self.design())
        for row in rows:
            row["target"] = {
                "regular_price_per_100g_gbp": 99,
                "log_regular_price_per_100g_gbp": math.log(99),
            }
        assert fitted == fit_encoder(rows, self.design())

    def test_constant_terms_are_reported_and_omitted(self):
        fitted = fit_encoder(
            [self.row(), self.row("same", "family-other")], self.design()
        )
        assert fitted["columns"] == ["intercept"]
        assert set(fitted["dropped_terms"]) == set(self.design()["predictors"])
        assert transform_rows([self.row()], fitted)["X"] == [[1.0]]

    def test_unobserved_reference_is_not_silently_replaced(self):
        design = self.design()
        design["predictors"]["identity.chocolate_type"]["reference"] = "white"
        with pytest.raises(
            ModelContractError, match="reference has no training support"
        ):
            fit_encoder(self.training(), design)

    def test_missingness_policy_and_transforms_must_be_explicit(self):
        for change in (
            {"missing_policy": "impute"},
            {"required": False},
            {"transform": "zscore"},
        ):
            design = self.design()
            design["predictors"]["quantity.total_edible_weight_g"].update(change)
            with pytest.raises(ModelContractError):
                fit_encoder(self.training(), design)

    def test_log_coefficient_and_context_contrast_use_multiplicative_scale(self):
        assert round(abs((coefficient_percent(math.log(1.2))) - (20)), 7) == 0
        assert round(abs((coefficient_percent(math.log(1.2), 2)) - (44)), 7) == 0
        assert round(abs((coefficient_percent(math.log(0.8))) - (-20)), 7) == 0
        contrast = prediction_contrast(math.log(2), math.log(3))
        assert round(abs((contrast["difference_per_100g_gbp"]) - (1)), 7) == 0
        assert round(abs((contrast["difference_percent"]) - (50)), 7) == 0
        assert contrast["estimate_type"] == "conditional_median_price"
        assert contrast["interpretation"] == "conditional_price_association"
        assert contrast["uncertainty"] is None
        assert contrast["support_evaluation_required"]

    def test_overflow_nan_and_price_underflow_are_rejected(self):
        for beta in (math.inf, math.nan, 1000, "0.2", True):
            with pytest.raises(ModelContractError):
                coefficient_percent(beta)
        for first, second in ((1000, 0), (0, -1000), (0, math.nan)):
            with pytest.raises(ModelContractError):
                prediction_contrast(first, second)
