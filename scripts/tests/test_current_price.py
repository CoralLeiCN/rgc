"""Check current-price arithmetic, historical isolation and model provenance."""

import json
import math
from copy import deepcopy

import pytest
from chocolate_current_price import (
    current_price_design,
    current_price_targets,
    validate_current_price_targets,
)
from chocolate_model import (
    CURRENT_PRICE_TARGET_POLICY,
    ModelContractError,
    validate_candidates,
)
from chocolate_regression import fit_regression
from test_model_contract import ChocolateModelContractTests as ModelFixture
from test_regression import ChocolateRegressionTests as RegressionFixture
from test_training_run import TrainingRunTests as TrainingFixture
from train_chocolate_model import build_model_run


def contract():
    return {"model_design_version": "synthetic-current-design-1",
            "target": {**CURRENT_PRICE_TARGET_POLICY, "name": "log_current_gbp_per_100g",
                       "currency": "GBP", "unit": "GBP_per_100g", "base_quantity": 100,
                       "quantity_attribute": "quantity.total_edible_weight_g"}}


def observation(row, amount=3.0):
    return {**{name: row.get(name) for name in ("observation_id", "listing_id", "source_role",
            "dataset_version", "source_dataset_version", "schema_version")}, "displayed_price": amount,
            "regular_price": None, "currency": "GBP", "tax_basis": "unknown",
            "promotion_status": "promotional", "review_status": "unreviewed", "model_eligible": False,
            "total_edible_weight_g": row["predictors"]["quantity.total_edible_weight_g"]}


def test_current_price_works_without_regular_price_review_or_tax_and_preserves_source():
    fixture = ModelFixture()
    row = fixture.row(weight=150)
    price = observation(row)
    before = deepcopy((row, price))
    prepared, report = current_price_targets([row], [price])
    design = current_price_design(fixture.design(), contract())
    assert validate_candidates(prepared, design) == prepared
    assert prepared[0]["target"]["current_price_per_100g_gbp"] == 2.0
    assert prepared[0]["target"]["log_current_price_per_100g_gbp"] == math.log(2)
    assert prepared[0]["target"]["regular_price_per_100g_gbp"] == 2.0
    assert report["counts"]["current_unit_price_targets"] == 1
    assert (row, price) == before
    assert validate_current_price_targets(prepared, [price])[row["observation_id"]] == price
    prepared[0]["target"]["current_price_per_100g_gbp"] = 3
    with pytest.raises(ModelContractError, match="normalized current"):
        validate_current_price_targets(prepared, [price])


@pytest.mark.parametrize("mutation,reason", [
    ({"displayed_price": None, "regular_price": 9.0}, "current_price_missing_or_invalid"),
    ({"displayed_price": True}, "current_price_missing_or_invalid"),
    ({"displayed_price": 0}, "current_price_missing_or_invalid"),
    ({"displayed_price": math.inf}, "current_price_missing_or_invalid"),
    ({"currency": "USD"}, "current_price_currency_not_gbp"),
    ({"total_edible_weight_g": 99}, "price_and_predictor_edible_weight_disagree"),
])
def test_invalid_current_inputs_stay_missing_without_fallback_or_exclusion(mutation, reason):
    row = ModelFixture().row()
    price = {**observation(row), **mutation}
    prepared, report = current_price_targets([row], [price])
    assert prepared[0]["model_eligible"] is True
    assert prepared[0]["target"]["current_price_per_100g_gbp"] is None
    assert report["target_failures"] == {reason: 1}


def test_missing_quantity_and_source_provenance_conflicts_are_explicit():
    row = ModelFixture().row(weight=None)
    price = observation(row)
    prepared, report = current_price_targets([row], [price])
    assert len(prepared) == 1 and prepared[0]["predictors"]["quantity.total_edible_weight_g"] is None
    assert report["target_failures"] == {"edible_weight_missing_or_invalid": 1}
    price["listing_id"] = "other-listing"
    with pytest.raises(ModelContractError, match="provenance"):
        current_price_targets([row], [price])
    with pytest.raises(ModelContractError, match="unique"):
        current_price_targets([row], [observation(row), observation(row)])


def test_current_regression_records_current_basis_and_fit_without_regular_observations():
    fixture = RegressionFixture()
    rows = fixture.training()
    for row in rows:
        row["predictors"]["quantity.total_edible_weight_g"] = 100.0
    prices = [observation(row, math.exp(0.2 + 0.012 * row["predictors"]["composition.cocoa_percentage"])) for row in rows]
    prepared, _ = current_price_targets(rows, prices)
    design = current_price_design(fixture.design(), contract())
    model = fit_regression(prepared, design, bootstrap_replicates=0)
    assert model["target_basis"] == "log_current_price_per_100g_gbp"
    assert model["price_target_policy"] == CURRENT_PRICE_TARGET_POLICY
    assert model["coefficients"][1]["beta"] == pytest.approx(0.012)
    assert all(price["regular_price"] is None for price in prices)


def test_current_training_command_saves_effective_contract_and_preserves_source(tmp_path):
    fixture = TrainingFixture()
    fixture.root, fixture.silver, fixture.output = tmp_path, tmp_path / "silver", tmp_path / "models"
    fixture.silver.mkdir()
    fixture.snapshot([fixture.observation(i) for i in range(1, 31)])
    prices = [json.loads(line) for line in (fixture.silver / "prices.jsonl").read_bytes().splitlines()]
    for price in prices:
        price.update(regular_price=None, tax_basis="unknown", review_status="unreviewed", model_eligible=False)
    fixture.replace_prices(prices)
    original = {path.name: path.read_bytes() for path in fixture.silver.iterdir()}
    report, destination = build_model_run(fixture.silver, fixture.output, "bar", current_price_target=True)
    assert report["regression_fitted"]
    assert report["price_target_policy"] == CURRENT_PRICE_TARGET_POLICY
    assert report["current_price_preparation"]["counts"]["current_unit_price_targets"] == 30
    model = json.loads((destination / "model.json").read_bytes())
    assert model["target_basis"] == "log_current_price_per_100g_gbp"
    assert (destination / "inputs/current-price-target-contract.json").is_file()
    assert {path.name: path.read_bytes() for path in fixture.silver.iterdir()} == original
