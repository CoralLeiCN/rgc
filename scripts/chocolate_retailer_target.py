"""Explicit target policies for the retailer median's historical and proxy studies."""

import math
from copy import deepcopy

from chocolate_model import (
    ModelContractError,
    _number,
    _predictor_definitions,
    _predictor_value,
    _validate_identity,
    validate_target_policy,
)

CURRENT_PRICE_POLICY_VERSION = "current-consumer-price-1"
LEGACY_FIELDS = ("regular_price_per_100g_gbp", "log_regular_price_per_100g_gbp")
CURRENT_FIELDS = ("current_price_per_100g_gbp", "log_current_price_per_100g_gbp")
CURRENT_PRICE_TARGET_POLICY = {
    "price_basis_contract_version": CURRENT_PRICE_POLICY_VERSION,
    "price_basis": "current_displayed",
    "tax_basis": "as_displayed",
    "promotion_basis": "as_displayed",
    "fallback_policy": "reject",
}


def current_contract_inputs():
    """Read the immutable published target and verify every cached contract byte."""
    from dataset_contracts import ROOT, SCHEMA_CACHE, resolve_contracts
    from train_chocolate_model import CONTRACTS, read_json

    reference = ROOT / "schemas/chocolate/current-price/dataset-contract.json"
    root = resolve_contracts(reference, SCHEMA_CACHE, offline=True)
    inputs = {name: (root / name).read_bytes() for name in CONTRACTS}
    return read_json(inputs["model-design.json"]), reference.read_bytes(), inputs


def current_price_target():
    return deepcopy(current_contract_inputs()[0]["target"])


def is_current_price(design):
    return design.get("target", {}).get("price_basis_contract_version") == CURRENT_PRICE_POLICY_VERSION


def validate_pricing_policy(target):
    if not isinstance(target, dict) or target.get("price_basis_contract_version") != CURRENT_PRICE_POLICY_VERSION:
        return validate_target_policy(target)
    for name, expected in CURRENT_PRICE_TARGET_POLICY.items():
        if target.get(name) != expected:
            raise ModelContractError("unsupported current-price proxy policy: " + name)
    for name, expected in (("name", "log_current_gbp_per_100g"), ("currency", "GBP"),
                           ("unit", "GBP_per_100g"), ("quantity_attribute", "quantity.total_edible_weight_g")):
        if target.get(name) != expected:
            raise ModelContractError("unsupported current-price normalization: " + name)
    if type(target.get("base_quantity")) is not int or target["base_quantity"] != 100:
        raise ModelContractError("unsupported current-price normalization: base_quantity")
    if (target.get("stored_target_fields") != list(CURRENT_FIELDS)
            or target.get("legacy_alias_fields") != list(LEGACY_FIELDS)
            or target.get("regular_price_required") is not False):
        raise ModelContractError("current-price target requires explicit current fields and compatibility aliases")
    return deepcopy(CURRENT_PRICE_TARGET_POLICY)


def target_fields(design):
    validate_pricing_policy(design.get("target"))
    if is_current_price(design):
        return CURRENT_FIELDS
    return LEGACY_FIELDS


def validate_pricing_candidates(values, design):
    """Validate row structure, identity and the declared target without price inference."""
    definitions = _predictor_definitions(design)
    unit_field, log_field = target_fields(design)
    values = list(values)
    _validate_identity(values)
    for row in values:
        target = row.get("target")
        if not isinstance(target, dict):
            raise ModelContractError("target must declare its selected GBP/100g basis")
        unit = _number(target.get(unit_field), "selected GBP/100g price")
        logged = _number(target.get(log_field), "log selected GBP/100g price")
        if unit <= 0 or not math.isclose(math.log(unit), logged, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelContractError("selected target must be positive with a consistent log value")
        if not isinstance(row.get("predictors"), dict):
            raise ModelContractError("predictors must use declared attributes")
        for name, definition in definitions.items():
            _predictor_value(row["predictors"].get(name), name, definition)
    return deepcopy(values)


def observation_index(observations):
    index = {}
    for price in observations:
        identifier = price.get("observation_id") if isinstance(price, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in index:
            raise ModelContractError("price observations require unique observation IDs")
        index[identifier] = price
    return index


def derive_current_targets(values, observations, design):
    """Use the shared preparation without altering source evidence or eligibility."""
    from chocolate_current_price import current_price_targets

    if not is_current_price(design):
        raise ModelContractError("current-price derivation requires its explicit proxy policy")
    return current_price_targets(values, observations)[0]


def validate_current_targets(values, observations, design):
    from chocolate_current_price import validate_current_price_targets

    if not is_current_price(design):
        raise ModelContractError("current-price validation requires its explicit proxy policy")
    target_fields(design)
    return validate_current_price_targets(values, observations)
