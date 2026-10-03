"""Fit and assess an experimental reviewed chocolate log-price regression.

Evidence review remains upstream. This module uses a frozen training encoder,
refuses unidentified ordinary least-squares effects, and never declares release
readiness or supplies a new-product prediction interval. NumPy is imported only
when numerical fitting or evaluation is requested.
"""

import hashlib
import json
import math
from collections import Counter, defaultdict
from copy import deepcopy
from statistics import median

from chocolate_model import (
    ModelContractError,
    coefficient_percent,
    fit_encoder,
    transform_rows,
    validate_candidates,
    validate_target_policy,
)

MODEL_FORMAT_VERSION = "chocolate-regression-2"
MAX_CONDITION_NUMBER = 1e12
CONFIDENCE_LEVEL = 0.95
MIN_BOOTSTRAP_SUCCESSES = 20
MIN_BOOTSTRAP_SUCCESS_FRACTION = 0.8
TARGET_BASIS = "log_regular_price_per_100g_gbp"
_CONTEXT_FIELDS = {"identity.source_role"}
_PRICE_FIELDS = {
    "displayed_price", "regular_price", "reference_price", "unit_price",
    "normalized_price", "target", "price_band", "value_for_money_score",
    "regular_price_per_100g_gbp", "log_regular_price_per_100g_gbp",
}


def _numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ModelContractError("Regression requires the declared NumPy modeling dependency") from error
    return np


def _designs(design):
    """Keep all eligibility fields while excluding explicit context from X."""
    if not isinstance(design, dict):
        raise ModelContractError("model design must be an object")
    # Validate the complete eligibility contract before reducing the fitted set.
    validate_candidates([], design)
    target = design.get("target", {})
    if not isinstance(target, dict):
        raise ModelContractError("model target must be an object")
    for key, expected in (("name", "log_regular_gbp_per_100g"), ("currency", "GBP"),
                          ("unit", "GBP_per_100g")):
        if key in target and target[key] != expected:
            raise ModelContractError("unsupported regression target " + key)
    specification = design.get("model", {})
    training_specification = design.get("training", {})
    if not isinstance(specification, dict) or not isinstance(training_specification, dict):
        raise ModelContractError("model specification must be an object")
    if (specification.get("estimator", "ordinary_least_squares") != "ordinary_least_squares"
            or training_specification.get("estimator", "ordinary_least_squares") != "ordinary_least_squares"):
        raise ModelContractError("unsupported regression estimator")
    contexts = specification.get("context_only_predictors", [])
    if (not isinstance(contexts, list) or any(not isinstance(name, str) for name in contexts)
            or len(set(contexts)) != len(contexts) or set(contexts) - _CONTEXT_FIELDS):
        raise ModelContractError("unsupported context-only predictor declaration")
    definitions = design.get("predictors")
    if not isinstance(definitions, dict) or set(contexts) - set(definitions):
        raise ModelContractError("context-only predictors must be declared eligibility predictors")
    excluded_prices = set(_PRICE_FIELDS)
    extra_exclusions = target.get("exclude_from_predictors", [])
    if not isinstance(extra_exclusions, list) or any(not isinstance(name, str) for name in extra_exclusions):
        raise ModelContractError("target predictor exclusions must be strings")
    excluded_prices.update(extra_exclusions)
    for name in definitions:
        if name in excluded_prices or name.rsplit(".", 1)[-1] in excluded_prices:
            raise ModelContractError("price-derived target fields cannot be predictors")
    for value in (design.get("interaction_terms"), specification.get("interaction_terms"),
                  design.get("interactions")):
        if value:
            raise ModelContractError("interaction terms are not implemented by this estimator")
    interactions = specification.get("interactions")
    if isinstance(interactions, (list, dict)) and interactions:
        raise ModelContractError("interaction terms are not implemented by this estimator")
    if specification.get("ridge_alpha", 0) != 0:
        raise ModelContractError("regularization is not implemented by this estimator")
    penalty = specification.get("regularization")
    if isinstance(penalty, (dict, list, bool, int, float)) and penalty:
        raise ModelContractError("regularization is not implemented by this estimator")
    encoder_design = deepcopy(design)
    encoder_design["predictors"] = {name: deepcopy(value) for name, value in definitions.items()
                                    if name not in contexts}
    active = specification.get("active_predictors")
    if active is not None and (not isinstance(active, list) or any(not isinstance(name, str) for name in active)
                               or len(active) != len(set(active))
                               or set(active) != set(encoder_design["predictors"])):
        raise ModelContractError("active predictors must match the declared fitted subset")
    return encoder_design, sorted(contexts)


def _reviewed_rows(rows, design):
    candidates = sorted(validate_candidates(rows, design), key=lambda row: row["observation_id"])
    listings = [row["listing_id"] for row in candidates]
    if len(set(listings)) != len(listings):
        raise ModelContractError("cross-sectional regression requires one observation per seller listing")
    for row in candidates:
        reviewed_role = row["predictors"].get("identity.source_role")
        if reviewed_role is not None and reviewed_role != row["source_role"]:
            raise ModelContractError("reviewed source-role predictor disagrees with observation context")
        reviewed_group = row["predictors"].get("identity.product_group")
        if reviewed_group is not None and reviewed_group != row["comparable_group"]:
            raise ModelContractError("reviewed product-group predictor disagrees with observation context")
    return candidates


def _fingerprint(rows):
    try:
        content = json.dumps(rows, sort_keys=True, ensure_ascii=True, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ModelContractError("training snapshot must be finite JSON data") from error
    return hashlib.sha256(content).hexdigest()


def _fit_matrix(np, features, targets):
    matrix = np.asarray(features, dtype=float)
    outcomes = np.asarray(targets, dtype=float)
    if matrix.ndim != 2 or outcomes.ndim != 1 or len(outcomes) != len(matrix):
        raise ModelContractError("regression requires matching two-dimensional X and one-dimensional y")
    n, p = matrix.shape
    if not p or n <= p:
        raise ModelContractError("regression requires more training observations than fitted columns")
    if not np.isfinite(matrix).all() or not np.isfinite(outcomes).all():
        raise ModelContractError("regression matrix and targets must be finite")
    try:
        coefficients, _, rank, singular_values = np.linalg.lstsq(matrix, outcomes, rcond=None)
    except np.linalg.LinAlgError as error:
        raise ModelContractError("least-squares decomposition failed") from error
    if int(rank) != p:
        raise ModelContractError("training design matrix is rank deficient; effects are not identifiable")
    condition = float(singular_values[0] / singular_values[-1])
    if not math.isfinite(condition) or condition > MAX_CONDITION_NUMBER:
        raise ModelContractError("training design matrix is numerically unstable")
    predicted = matrix @ coefficients
    residuals = outcomes - predicted
    if not all(np.isfinite(value).all() for value in (coefficients, predicted, residuals, singular_values)):
        raise ModelContractError("least-squares fit produced non-finite values")
    return coefficients, predicted, residuals, {
        "observations": n, "columns": p, "rank": int(rank), "residual_degrees_of_freedom": n - p,
        "singular_values": [float(value) for value in singular_values],
        "condition_number": condition, "maximum_condition_number": MAX_CONDITION_NUMBER,
        "rank_policy": "full_rank_required_no_automatic_term_removal",
    }


def _price(log_price):
    try:
        price = math.exp(float(log_price))
    except OverflowError as error:
        raise ModelContractError("log prediction cannot be represented on the price scale") from error
    if not math.isfinite(price) or price <= 0:
        raise ModelContractError("log prediction must produce a finite positive price")
    return price


def _metrics(records, prediction_key="predicted_median_price_per_100g_gbp"):
    if not records:
        return None
    absolute, squared, log_absolute, log_squared = [], [], [], []
    for record in records:
        actual = record["observed_price_per_100g_gbp"]
        predicted = record[prediction_key]
        error = predicted - actual
        absolute.append(abs(error))
        squared.append(error * error)
        log_error = math.log(predicted) - math.log(actual)
        log_absolute.append(abs(log_error))
        log_squared.append(log_error * log_error)
    result = {"observations": len(records), "MAE_GBP_per_100g": math.fsum(absolute) / len(records),
              "RMSE_GBP_per_100g": math.sqrt(math.fsum(squared) / len(records)),
              "MAE_log_price": math.fsum(log_absolute) / len(records),
              "RMSE_log_price": math.sqrt(math.fsum(log_squared) / len(records)),
              "prediction_interval_coverage": None}
    if any(not math.isfinite(value) for key, value in result.items() if value is not None):
        raise ModelContractError("price errors cannot be represented as finite metrics")
    return result


def _bootstrap(np, matrix, targets, rows, replicates, seed):
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 0:
        raise ModelContractError("bootstrap_replicates must be a nonnegative integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise ModelContractError("random_seed must be an integer between zero and 2**32 - 1")
    indices = defaultdict(list)
    for index, row in enumerate(rows):
        indices[row["family_id"]].append(index)
    families = sorted(indices)
    generator = np.random.default_rng(seed)
    successes, failures = [], Counter()
    for _ in range(replicates):
        drawn = generator.integers(0, len(families), size=len(families))
        sampled = [index for family_index in drawn for index in indices[families[int(family_index)]]]
        try:
            coefficients, _, _, _ = _fit_matrix(np, matrix[sampled], targets[sampled])
        except ModelContractError as error:
            failures[str(error)] += 1
            continue
        successes.append(coefficients)
    available = len(successes) >= MIN_BOOTSTRAP_SUCCESSES and len(successes) >= replicates * MIN_BOOTSTRAP_SUCCESS_FRACTION
    interval = np.quantile(np.asarray(successes), [0.025, 0.975], axis=0) if available else None
    report = {
        "method": "family_cluster_bootstrap_fixed_training_encoder_percentile",
        "confidence_level": CONFIDENCE_LEVEL, "random_seed": seed, "replicates": replicates,
        "successful_replicates": len(successes), "failed_replicates": replicates - len(successes),
        "failure_reasons": dict(sorted(failures.items())),
        "minimum_successful_replicates": MIN_BOOTSTRAP_SUCCESSES,
        "minimum_success_fraction": MIN_BOOTSTRAP_SUCCESS_FRACTION,
        "coefficient_confidence_intervals_available": available,
        "resampling_unit": "reviewed_family", "all_family_rows_resampled_together": True,
        "preprocessing": "fixed_outer_training_encoder",
        "prediction_intervals_available": False,
        "statistical_sufficiency_established": False,
    }
    return interval, report


def _column_context(column, encoder):
    if column == "intercept":
        return {"interpretation": "log_price_intercept", "predictor": None, "reference": None,
                "contrast": None}
    for name, specification in encoder["predictors"].items():
        if column == name and specification["type"] == "numeric":
            log_transform = specification.get("transform", "identity") == "log"
            contrast = {"input_ratio": math.e} if log_transform else {"input_change": 1.0}
            return {"interpretation": "conditional_price_association", "predictor": name,
                    "reference": None, "unit": specification.get("unit"),
                    "transform": specification.get("transform", "identity"), "contrast": contrast}
        if specification["type"] != "numeric":
            for level in specification["training_levels"]:
                if level != specification["reference"] and column == name + "=" + level:
                    return {"interpretation": "conditional_price_association", "predictor": name,
                            "reference": specification["reference"], "comparison_level": level,
                            "contrast": {"input_change": 1.0}}
    raise ModelContractError("coefficient column has no declared predictor meaning")


def fit_regression(train_rows, design, *, bootstrap_replicates=500, random_seed=1729):
    """Fit full-rank OLS and family-bootstrap coefficient intervals on training."""
    encoder_design, contexts = _designs(design)
    rows = _reviewed_rows(train_rows, design)
    families = sorted({row["family_id"] for row in rows})
    if len(families) < 2:
        raise ModelContractError("regression requires at least two reviewed training families")
    encoder = fit_encoder(rows, encoder_design)
    transformed = transform_rows(rows, encoder)
    np = _numpy()
    coefficients, predictions, residuals, rank = _fit_matrix(np, transformed["X"], transformed["y"])
    matrix, targets = np.asarray(transformed["X"], dtype=float), np.asarray(transformed["y"], dtype=float)
    intervals, uncertainty = _bootstrap(np, matrix, targets, rows, bootstrap_replicates, random_seed)
    coefficient_rows = []
    for index, (column, beta) in enumerate(zip(encoder["columns"], coefficients)):
        context = _column_context(column, encoder)
        intercept = column == "intercept"
        interval = [float(value) for value in intervals[:, index]] if intervals is not None else None
        coefficient_rows.append({
            "column": column, "beta": float(beta), **context,
            "conditional_difference_percent": None if intercept else coefficient_percent(float(beta)),
            "confidence_interval_beta": interval,
            "confidence_interval_percent": ([coefficient_percent(value) for value in interval]
                                             if interval is not None and not intercept else None),
        })
    training_residuals = [
        {"observation_id": row["observation_id"], "listing_id": row["listing_id"],
         "family_id": row["family_id"], "observed_log_price": float(target),
         "predicted_log_price": float(predicted), "residual_log_price": float(residual),
         "observed_price_per_100g_gbp": row["target"]["regular_price_per_100g_gbp"],
         "predicted_median_price_per_100g_gbp": _price(predicted)}
        for row, target, predicted, residual in zip(rows, targets, predictions, residuals)
    ]
    return {
        "model_format_version": MODEL_FORMAT_VERSION,
        "model_design_version": design.get("model_design_version", design.get("design_version")),
        "schema_version": design.get("schema_version"), "estimator": "ordinary_least_squares",
        "target_basis": TARGET_BASIS, "estimate_type": "conditional_median_price",
        "price_target_policy": validate_target_policy(design["target"]),
        "retransformation_method": "exp_log_prediction_without_mean_bias_correction",
        "weighting": "one_equal_weight_observation_per_seller_listing",
        "feature_subset": list(encoder_design["predictors"]), "context_only_predictors": contexts,
        "eligibility_design": deepcopy(design), "encoder": encoder, "columns": deepcopy(encoder["columns"]),
        "coefficients": coefficient_rows, "rank_diagnostics": rank,
        "training_support": {"observations": len(rows), "families": len(families),
                             "family_ids": families, "observation_ids": [row["observation_id"] for row in rows],
                             "listing_ids": sorted(row["listing_id"] for row in rows),
                             "by_source_role": dict(sorted(Counter(row["source_role"] for row in rows).items())),
                             "by_comparable_group": dict(sorted(Counter(row["comparable_group"] for row in rows).items())),
                             "predictors": deepcopy(encoder["predictors"]),
                             "dropped_constant_terms": deepcopy(encoder["dropped_terms"])},
        "training_rows_sha256": _fingerprint(rows), "training_metrics": _metrics(training_residuals),
        "training_residuals": training_residuals, "uncertainty": uncertainty,
        "regression_fitted": True, "prediction_intervals_available": False, "release_ready": False,
        "limitations": [
            "Experimental fit; numerical identifiability does not establish adequate independent support.",
            "Associations are conditional on the declared fitted terms and are not causal premiums.",
            "Bootstrap intervals condition on a fixed training encoder and do not include preprocessing selection uncertainty.",
            "Few independent families and sparse levels can make bootstrap uncertainty unreliable or unavailable.",
            "No new-product prediction intervals, future-period validation or release thresholds are established.",
            "Exponentiated log predictions are labeled conditional medians under the log-error formulation, not arithmetic means.",
        ],
    }


def _stratified(rows, predictions, key):
    partitions = defaultdict(list)
    for row in rows:
        value = key(row)
        if value is not None:
            partitions[value].append(row)
    results = {}
    for value, members in sorted(partitions.items()):
        supported = [predictions[row["observation_id"]] for row in members if row["observation_id"] in predictions]
        paired = [record for record in supported if "baseline_price_per_100g_gbp" in record]
        results[value] = {
            "validation_observations": len(members), "supported_observations": len(supported),
            "unsupported_observations": len(members) - len(supported), "coverage": len(supported) / len(members),
            "metrics": _metrics(supported), "baseline_supported_observations": len(paired),
            "baseline_metrics": _metrics(paired, "baseline_price_per_100g_gbp"),
            "model_metrics_on_baseline_supported_rows": _metrics(paired),
        }
    return results


def evaluate_regression(validation_rows, model, train_rows):
    """Score only supported held-out families and expose the full denominator."""
    if not isinstance(model, dict) or model.get("model_format_version") != MODEL_FORMAT_VERSION:
        raise ModelContractError("unsupported fitted regression model")
    design = model.get("eligibility_design")
    policy = validate_target_policy(design.get("target") if isinstance(design, dict) else None)
    if model.get("price_target_policy") != policy or model.get("encoder", {}).get("target") != design["target"]:
        raise ModelContractError("fitted model price target policy differs from its declared design")
    training = _reviewed_rows(train_rows, design)
    if _fingerprint(training) != model.get("training_rows_sha256"):
        raise ModelContractError("baseline training rows differ from the fitted immutable snapshot")
    rows = _reviewed_rows(validation_rows, design)
    # A separately validated partition cannot relabel a training variant into a
    # different family and thereby manufacture independence across partitions.
    validate_candidates(training + rows, design)
    training_families = set(model["training_support"]["family_ids"])
    if training_families & {row["family_id"] for row in rows}:
        raise ModelContractError("validation families overlap training families")
    if set(model["training_support"]["listing_ids"]) & {row["listing_id"] for row in rows}:
        raise ModelContractError("validation seller listings overlap training listings")
    by_group = defaultdict(list)
    for row in training:
        by_group[row["comparable_group"]].append(row["target"]["regular_price_per_100g_gbp"])
    medians = {group: median(prices) for group, prices in sorted(by_group.items())}
    np = _numpy()
    coefficients = np.asarray([value["beta"] for value in model["coefficients"]], dtype=float)
    if (len(coefficients) != len(model["encoder"]["columns"]) or not np.isfinite(coefficients).all()
            or [value["column"] for value in model["coefficients"]] != model["encoder"]["columns"]):
        raise ModelContractError("regression coefficients disagree with the frozen encoder")
    predictions, unsupported = [], []
    for row in rows:
        try:
            encoded = transform_rows([row], model["encoder"])
        except ModelContractError as error:
            reason = str(error)
            if " is outside its training range" not in reason and " has an unseen training level:" not in reason:
                raise
            unsupported.append({"observation_id": row["observation_id"], "family_id": row["family_id"],
                                "source_role": row["source_role"], "comparable_group": row["comparable_group"],
                                "reason": reason})
            continue
        log_prediction = float(np.asarray(encoded["X"][0], dtype=float) @ coefficients)
        record = {"observation_id": row["observation_id"], "family_id": row["family_id"],
                  "source_role": row["source_role"], "comparable_group": row["comparable_group"],
                  "observed_price_per_100g_gbp": row["target"]["regular_price_per_100g_gbp"],
                  "predicted_log_price": log_prediction,
                  "predicted_median_price_per_100g_gbp": _price(log_prediction),
                  "prediction_interval": None}
        if row["comparable_group"] in medians:
            record["baseline_price_per_100g_gbp"] = medians[row["comparable_group"]]
        predictions.append(record)
    paired = [record for record in predictions if "baseline_price_per_100g_gbp" in record]
    prediction_index = {record["observation_id"]: record for record in predictions}
    return {
        "status": "evaluated_supported_holdout" if predictions else "no_supported_holdout",
        "target_basis": TARGET_BASIS, "estimate_type": "conditional_median_price",
        "price_target_policy": policy,
        "validation_observations": len(rows), "supported_observations": len(predictions),
        "unsupported_observations": len(unsupported), "coverage": len(predictions) / len(rows) if rows else 0.0,
        "validation_families": len({row["family_id"] for row in rows}),
        "supported_families": len({record["family_id"] for record in predictions}),
        "unsupported": unsupported, "metrics": _metrics(predictions),
        "baseline": {"strategy": "training_comparable_group_regular_price_median",
                     "group_medians": medians, "supported_observations": len(paired),
                     "unsupported_observations": len(rows) - len(paired),
                     "metrics": _metrics(paired, "baseline_price_per_100g_gbp"),
                     "model_metrics_on_baseline_supported_rows": _metrics(paired)},
        "by_source_role": _stratified(rows, prediction_index, lambda row: row["source_role"]),
        "by_comparable_group": _stratified(rows, prediction_index, lambda row: row["comparable_group"]),
        "by_brand": _stratified(rows, prediction_index, lambda row: row["predictors"].get("identity.brand")),
        "by_retailer": _stratified(rows, prediction_index, lambda row: row["predictors"].get("identity.retailer")),
        "predictions": predictions, "prediction_intervals_available": False, "release_ready": False,
        "limitations": ["Held-out errors describe supported rows; rejection coverage uses every eligible validation row.",
                        "No prediction-interval coverage or release decision is available.",
                        "Family holdout does not establish future-period or unseen-brand prediction support."],
    }
