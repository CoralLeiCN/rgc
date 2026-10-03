"""Shared regular consumer-price target contract for every category model."""

import math

TARGET_PRICE_POLICY = {
    "price_basis_contract_version": "regular-consumer-price-1",
    "price_basis": "regular",
    "tax_basis": "consumer_tax_included",
    "promotion_basis": "non_promotional",
    "fallback_policy": "reject",
}
TARGET_NORMALIZATION_FIELDS = ("currency", "unit", "quantity_attribute", "base_quantity")


def validate_price_policy(value, label="Model target"):
    """Reject missing or alternative monetary bases; never infer source facts."""
    if not isinstance(value, dict):
        raise ValueError(label + " requires the regular consumer-price target policy.")
    for key, expected in TARGET_PRICE_POLICY.items():
        if value.get(key) != expected:
            raise ValueError(label + " " + key + " must be " + expected + ".")


def validate_target_definition(target):
    """Validate policy and explicitly declared category normalization/log scale."""
    validate_price_policy(target)
    if target.get("name") != "log_regular_unit_price":
        raise ValueError("Model target must use log_regular_unit_price.")
    for key in TARGET_NORMALIZATION_FIELDS[:-1]:
        value = target.get(key)
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("Model target " + key + " must be explicit canonical text.")
    quantity = target.get("base_quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("Model target base_quantity must be finite and positive.")
