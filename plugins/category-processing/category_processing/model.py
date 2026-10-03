"""Prepare reviewed category rows for later regression; do not fit a model.

The schema layer owns evidence and eligibility review. This module validates
that boundary, keeps product families together, and learns predictor support
from training rows only. An encoder is a reproducible design contract, not a
pricing model or evidence of release readiness.
"""

import hashlib
import math
from collections import Counter
from copy import deepcopy

from .price_policy import (
    TARGET_NORMALIZATION_FIELDS,
    validate_price_policy,
    validate_target_definition,
)

ENCODER_VERSION = "category-processing-encoder-2"


class ModelContractError(ValueError):
    """A reviewed row or model design is outside the supported contract."""


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelContractError(label + " must be a typed numeric value")
    if not math.isfinite(value):
        raise ModelContractError(label + " must be finite")
    return float(value)


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ModelContractError(label + " must be a nonempty canonical string")
    if value.casefold() in {"unknown", "unresolved", "not_applicable"}:
        raise ModelContractError(label + " is unresolved")
    return value


def _predictor_definitions(design):
    if not isinstance(design, dict) or not isinstance(design.get("predictors"), dict):
        raise ModelContractError("model design requires a predictors object")
    if not design["predictors"]:
        raise ModelContractError("model design must declare its selected predictors")
    definitions = deepcopy(design["predictors"])
    for name, definition in definitions.items():
        _identifier(name, "predictor name")
        if not isinstance(definition, dict):
            raise ModelContractError(name + " requires a predictor definition")
        if definition.get("type") not in {"numeric", "categorical", "presence"}:
            raise ModelContractError(name + " has an unsupported predictor type")
        if definition.get("required") is not True or definition.get("missing_policy") != "reject":
            raise ModelContractError(name + " requires explicit required/reject missingness policy")
        transform = definition.get("transform", "identity")
        if transform not in {"identity", "log"}:
            raise ModelContractError(name + " has an unsupported transform")
        if definition["type"] != "numeric":
            if transform != "identity":
                raise ModelContractError(name + " categorical transforms must be identity")
            _identifier(definition.get("reference"), name + " reference")
            allowed = definition.get("allowed_values")
            if allowed is not None:
                if not isinstance(allowed, list) or not allowed:
                    raise ModelContractError(name + " allowed_values must be a nonempty list")
                for value in allowed:
                    _identifier(value, name + " allowed value")
                if len(set(allowed)) != len(allowed):
                    raise ModelContractError(name + " has duplicate allowed values")
            if definition["type"] == "presence" and allowed is not None and set(allowed) != {"present", "absent"}:
                raise ModelContractError(name + " presence predictor supports present and absent")
    return definitions


def _predictor_value(value, name, definition):
    if definition["type"] == "numeric":
        result = _number(value, name)
        if definition.get("minimum") is not None and result < definition["minimum"]:
            raise ModelContractError(name + " is below its declared minimum")
        if definition.get("maximum") is not None and result > definition["maximum"]:
            raise ModelContractError(name + " is above its declared maximum")
        if definition.get("transform", "identity") == "log" and result <= 0:
            raise ModelContractError(name + " must be positive for a log transform")
        return result
    result = _identifier(value, name)
    allowed = definition.get("allowed_values")
    if definition["type"] == "presence" and result not in {"present", "absent"}:
        raise ModelContractError(name + " requires reviewed present or absent")
    if allowed is not None and result not in allowed:
        raise ModelContractError(name + " is outside the schema vocabulary")
    return result


def _validate_identity(rows):
    seen = set()
    variant_families = {}
    listing_variants = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("model_eligible") is not True:
            raise ModelContractError("only rows passing the schema eligibility gate are accepted")
        for key in ("observation_id", "listing_id", "variant_id", "family_id", "comparable_group"):
            _identifier(row.get(key), key)
        if row.get("source_role") not in {"brand", "retail"}:
            raise ModelContractError("source_role must resolve the selling source")
        if row["observation_id"] in seen:
            raise ModelContractError("duplicate observation_id: " + row["observation_id"])
        seen.add(row["observation_id"])
        previous_family = variant_families.setdefault(row["variant_id"], row["family_id"])
        if previous_family != row["family_id"]:
            raise ModelContractError("a physical variant cannot span validation families")
        previous_variant = listing_variants.setdefault(row["listing_id"], row["variant_id"])
        if previous_variant != row["variant_id"]:
            raise ModelContractError("a seller listing cannot span reviewed physical variants")


def validate_candidates(rows, design):
    """Return validated copies; refuse ineligible, unknown, or invalid rows.

    The eligibility flag represents the upstream evidence review. This function
    cannot independently establish that a source supports a review decision.
    """
    try:
        validate_target_definition(design.get("target") if isinstance(design, dict) else None)
    except ValueError as error:
        raise ModelContractError(str(error)) from error
    definitions = _predictor_definitions(design)
    candidates = list(rows)
    _validate_identity(candidates)
    for row in candidates:
        target = row.get("target")
        if not isinstance(target, dict):
            raise ModelContractError("target must declare its regular unit-price basis")
        try:
            validate_price_policy(target, "Stored row target")
        except ValueError as error:
            raise ModelContractError(str(error)) from error
        for key in TARGET_NORMALIZATION_FIELDS:
            if (target.get(key) != design["target"][key]
                    or (key == "base_quantity" and isinstance(target.get(key), bool))):
                raise ModelContractError("stored row target " + key + " differs from the model design")
        price = _number(target.get("regular_unit_price"), "regular unit price")
        logged = _number(target.get("log_regular_unit_price"), "log regular unit price")
        if price <= 0:
            raise ModelContractError("regular unit price must be positive")
        if not math.isclose(math.log(price), logged, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelContractError("log target is inconsistent with its original price")
        predictors = row.get("predictors")
        if not isinstance(predictors, dict):
            raise ModelContractError("predictors must use the declared schema attributes")
        for name, definition in definitions.items():
            _predictor_value(predictors.get(name), name, definition)
    return deepcopy(candidates)


def split_by_family(rows, validation_fraction=0.2):
    """Make a deterministic family holdout without merging seller listings.

    At least two independently reviewed families are necessary to construct the
    split. This technical requirement does not establish statistical sufficiency.
    """
    candidates = list(rows)
    _validate_identity(candidates)
    fraction = _number(validation_fraction, "validation_fraction")
    if not 0 < fraction < 1:
        raise ModelContractError("validation_fraction must be between zero and one")
    families = sorted({row["family_id"] for row in candidates},
                      key=lambda value: (hashlib.sha256(value.encode("utf-8")).hexdigest(), value))
    if len(families) < 2:
        raise ModelContractError("a family holdout requires at least two reviewed families")
    count = max(1, min(len(families) - 1, int(len(families) * fraction + 0.5)))
    validation_families = set(families[:count])
    def key(row):
        return row["observation_id"]

    train = sorted((row for row in candidates if row["family_id"] not in validation_families), key=key)
    validation = sorted((row for row in candidates if row["family_id"] in validation_families), key=key)
    return {
        "train": deepcopy(train), "validation": deepcopy(validation),
        "metadata": {
            "strategy": "deterministic_reviewed_family_holdout",
            "validation_fraction_requested": fraction,
            "training_families": sorted(set(families) - validation_families),
            "validation_families": sorted(validation_families),
            "training_observations": len(train), "validation_observations": len(validation),
            "seller_listings_preserved": True,
        },
    }


def fit_encoder(train_rows, design):
    """Freeze predictor columns, references, and support using training only."""
    rows = validate_candidates(train_rows, design)
    if not rows:
        raise ModelContractError("no reviewed eligible training rows are available")
    definitions = _predictor_definitions(design)
    fitted = {
        "encoder_version": ENCODER_VERSION,
        "model_design_version": design.get("model_design_version", design.get("design_version")),
        "schema_version": design.get("schema_version"),
        "category": design.get("category"), "market": design.get("market"),
        "target_definition": deepcopy(design.get("target", {})),
        "columns": ["intercept"], "predictors": {}, "dropped_terms": {},
        "training_observation_ids": sorted(row["observation_id"] for row in rows),
        "training_family_ids": sorted({row["family_id"] for row in rows}),
        "regression_fitted": False, "release_ready": False,
    }
    for name, definition in definitions.items():
        values = [_predictor_value(row["predictors"][name], name, definition) for row in rows]
        spec = deepcopy(definition)
        if definition["type"] == "numeric":
            spec.update({"training_minimum": min(values), "training_maximum": max(values),
                         "training_observations": len(values)})
            if min(values) == max(values):
                fitted["dropped_terms"][name] = "constant_in_training"
            else:
                fitted["columns"].append(name)
        else:
            counts = Counter(values)
            reference = definition["reference"]
            if reference == "training_mode":
                reference = min(counts, key=lambda level: (-counts[level], level))
            if reference not in counts:
                raise ModelContractError(name + " reference has no training support")
            family_support = {
                level: len({row["family_id"] for row in rows if row["predictors"][name] == level})
                for level in sorted(counts)
            }
            spec.update({"reference": reference, "training_levels": sorted(counts),
                         "observation_support": dict(sorted(counts.items())),
                         "family_support": family_support})
            if len(counts) == 1:
                fitted["dropped_terms"][name] = "constant_in_training"
            else:
                fitted["columns"].extend(name + "=" + level for level in sorted(counts) if level != reference)
        fitted["predictors"][name] = spec
    return fitted


def transform_rows(rows, fitted):
    """Apply frozen encoding and refuse unsupported ranges or unseen levels.

    Returns X/y on the declared log target scale. Holdout rejection is a support
    limitation to report, not a reason to refit the encoder with holdout data.
    """
    if not isinstance(fitted, dict) or fitted.get("encoder_version") != ENCODER_VERSION:
        raise ModelContractError("unsupported fitted encoder")
    design = {"predictors": fitted.get("predictors"), "target": fitted.get("target_definition")}
    candidates = validate_candidates(rows, design)
    matrix, targets = [], []
    for row in candidates:
        encoded = {"intercept": 1.0}
        for name, spec in fitted["predictors"].items():
            value = _predictor_value(row["predictors"][name], name, spec)
            if spec["type"] == "numeric":
                if not spec["training_minimum"] <= value <= spec["training_maximum"]:
                    raise ModelContractError(name + " is outside its training range")
                encoded[name] = math.log(value) if spec.get("transform", "identity") == "log" else value
            else:
                if value not in spec["training_levels"]:
                    raise ModelContractError(name + " has an unseen training level: " + value)
                for level in spec["training_levels"]:
                    if level != spec["reference"]:
                        encoded[name + "=" + level] = float(value == level)
        matrix.append([encoded[column] for column in fitted["columns"]])
        targets.append(row["target"]["log_regular_unit_price"])
    return {"columns": deepcopy(fitted["columns"]), "X": matrix, "y": targets,
            "observation_ids": [row["observation_id"] for row in candidates],
            "target_basis": "log_regular_unit_price",
            "target_definition": deepcopy(fitted.get("target_definition", {}))}


def coefficient_percent(beta, input_change=1.0):
    """Convert an additive log contrast to a conditional percentage difference."""
    contrast = _number(beta, "beta") * _number(input_change, "input_change")
    try:
        result = 100.0 * math.expm1(contrast)
    except OverflowError as error:
        raise ModelContractError("log contrast cannot be represented on the price scale") from error
    if not math.isfinite(result):
        raise ModelContractError("log contrast must produce a finite percentage")
    return result


def prediction_contrast(reference_log_prediction, comparison_log_prediction, target_definition=None):
    """Describe two log-scale predictions on the median scale of the declared price unit.

    The caller must establish feature overlap and supply the two profiles,
    conditioning variables, support, and uncertainty in any published insight.
    No uncertainty or causal inference can be manufactured from two predictions.
    """
    reference_log = _number(reference_log_prediction, "reference log prediction")
    comparison_log = _number(comparison_log_prediction, "comparison log prediction")
    try:
        reference = math.exp(reference_log)
        comparison = math.exp(comparison_log)
    except OverflowError as error:
        raise ModelContractError("log predictions cannot be represented on the price scale") from error
    if min(reference, comparison) <= 0:
        raise ModelContractError("predicted price underflowed the positive price scale")
    return {
        "reference_median_unit_price": reference,
        "comparison_median_unit_price": comparison,
        "difference_unit_price": comparison - reference,
        "difference_percent": coefficient_percent(comparison_log - reference_log),
        "estimate_type": "conditional_median_price",
        "interpretation": "conditional_price_association",
        "uncertainty": None,
        "support_evaluation_required": True,
        "target_definition": deepcopy(target_definition or {}),
    }
