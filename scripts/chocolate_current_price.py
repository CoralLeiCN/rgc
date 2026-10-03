"""Derive current-price targets from unchanged Gold price observations."""

import math
from collections import Counter
from copy import deepcopy

from chocolate_model import (
    CURRENT_PRICE_TARGET_POLICY,
    ModelContractError,
    validate_target_policy,
)

PREPARATION_VERSION = "chocolate-current-price-target-1"
LIMITATIONS = [
    "Current displayed prices are used as the study's regular-price proxy; independently verified regular prices are not required.",
    "Displayed prices may include promotions, membership conditions or temporary offers; these effects are not separated from product or retailer associations.",
    "Tax inclusion is taken as displayed and is not independently verified or harmonized.",
    "Prices describe recorded source captures, not live quotes or a common observation date.",
    "GBP per 100 g targets require an actual positive edible pack weight; missing quantities remain missing.",
]


def current_price_design(source_design, target_contract):
    """Apply only a dataset-owned target definition to a model's selected predictors."""
    validate_target_policy(target_contract.get("target"))
    if target_contract["target"].get("price_basis_contract_version") != "current-consumer-price-1":
        raise ModelContractError("Current-price preparation requires a current-price target contract")
    design = deepcopy(source_design)
    design["model_design_version"] = source_design["model_design_version"] + "-current-price-1"
    design["target"] = deepcopy(target_contract["target"])
    design["target_contract_version"] = target_contract["model_design_version"]
    gates = {gate["id"]: gate for gate in target_contract.get("eligibility_gates", [])}
    design["eligibility_gates"] = [deepcopy(gates[gate["id"]]) if gate["id"] in ("price", "tax") else gate
                                   for gate in design.get("eligibility_gates", [])]
    design["price_target_limitations"] = list(LIMITATIONS)
    return design


def current_price_targets(candidates, observations):
    """Keep all rows, including null targets, and bind actual GBP prices to quantities."""
    index = {}
    for price in observations:
        identifier = price.get("observation_id") if isinstance(price, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in index:
            raise ModelContractError("Current-price observations require unique observation IDs")
        index[identifier] = price
    result, failures = [], Counter()
    for original in candidates:
        row = deepcopy(original)
        price = index.get(row.get("observation_id"))
        if price is None:
            raise ModelContractError("Current-price target has no matching source observation")
        for name in ("listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version"):
            if price.get(name) != row.get(name):
                raise ModelContractError("Current-price observation disagrees with row provenance: " + name)
        amount = price.get("displayed_price")
        mass = row.get("predictors", {}).get("quantity.total_edible_weight_g")
        price_mass = price.get("total_edible_weight_g")
        reason = None
        if price.get("currency") != "GBP":
            reason = "current_price_currency_not_gbp"
        elif type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
            reason = "current_price_missing_or_invalid"
        elif type(mass) not in (int, float) or not math.isfinite(mass) or mass <= 0:
            reason = "edible_weight_missing_or_invalid"
        elif (type(price_mass) not in (int, float) or not math.isfinite(price_mass) or price_mass <= 0
              or not math.isclose(mass, price_mass, rel_tol=1e-9, abs_tol=1e-9)):
            reason = "price_and_predictor_edible_weight_disagree"
        value = amount / mass * 100 if reason is None else None
        if value is not None and (not math.isfinite(value) or value <= 0):
            reason, value = "current_unit_price_missing_or_invalid", None
        if reason:
            failures[reason] += 1
        # The legacy aliases allow existing experimental trainers to consume
        # this explicitly recorded proxy; they do not assert a regular price.
        row["target"] = {"current_price_per_100g_gbp": value,
                         "log_current_price_per_100g_gbp": math.log(value) if value else None,
                         "regular_price_per_100g_gbp": value,
                         "log_regular_price_per_100g_gbp": math.log(value) if value else None}
        result.append(row)
    return result, {"preparation_version": PREPARATION_VERSION, "price_target_policy": dict(CURRENT_PRICE_TARGET_POLICY),
                    "counts": {"candidates": len(result), "current_unit_price_targets": len(result) - sum(failures.values())},
                    "target_failures": dict(sorted(failures.items())), "limitations": list(LIMITATIONS)}


def validate_current_price_targets(candidates, observations):
    expected, _ = current_price_targets(candidates, observations)
    for row, derived in zip(candidates, expected):
        for name in ("current_price_per_100g_gbp", "log_current_price_per_100g_gbp"):
            actual, value = row.get("target", {}).get(name), derived["target"][name]
            if (value is None or type(actual) not in (int, float) or not math.isfinite(actual)
                    or not math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-9)):
                raise ModelContractError("Training target differs from the normalized current displayed price")
    return {price["observation_id"]: price for price in observations}
