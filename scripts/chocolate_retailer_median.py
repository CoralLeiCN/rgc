"""Fit and evaluate the family-balanced retailer/type unit-price baseline."""

import math
from collections import defaultdict

from chocolate_experiment import family_weights
from chocolate_model import ModelContractError
from chocolate_retailer_target import (
    is_current_price,
    target_fields,
    validate_pricing_candidates,
    validate_pricing_policy,
)
from train_chocolate_model import checksum, json_bytes

MODEL_ID = "retailer_median"
DESIGN_VERSION = "chocolate-retailer-median-design-1"
CURRENT_DESIGN_VERSION = "chocolate-retailer-median-design-1-current-price-1"
RETAILER = "identity.retailer"
TYPE = "composition.chocolate_type"
MASS = "quantity.total_edible_weight_g"
CONTEXT = ("identity.brand", "identity.source_role", "identity.product_group",
           "identity.boundary_status", "quantity.pack_count", MASS)
PREDICTORS = (RETAILER, TYPE)


def weighted_median(values, weights):
    """Use the lower weighted median; ties at half mass choose the lower value."""
    if not values or len(values) != len(weights):
        raise ModelContractError("weighted median requires nonempty matching arrays")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values + weights):
        raise ModelContractError("weighted median values and weights must be finite numbers")
    if any(w <= 0 for w in weights):
        raise ModelContractError("weighted median requires positive weights")
    ordered = sorted(zip(values, weights))
    half = math.fsum(weights) / 2
    cumulative = []
    for value, weight in ordered:
        cumulative.append(weight)
        if math.fsum(cumulative) >= half:
            return value
    return ordered[-1][0]


def validate_design(design):
    validate_pricing_policy(design.get("target"))
    expected_version = CURRENT_DESIGN_VERSION if is_current_price(design) else DESIGN_VERSION
    if design.get("model_design_version") != expected_version:
        raise ModelContractError("working retailer median contract required; old OLS design cannot authorize this population")
    expected = set(PREDICTORS + CONTEXT)
    if set(design.get("predictors", {})) != expected:
        raise ModelContractError("retailer median contract has unexpected required fields")
    policy = design.get("comparison_experiment")
    from prepare_chocolate_retailer_contract import experiment_policy
    if policy != experiment_policy(current_price_proxy=is_current_price(design)):
        raise ModelContractError("unsupported comparison experiment policy")
    return policy


def reviewed_rows(rows, design):
    validate_design(design)
    rows = validate_pricing_candidates(rows, design)
    if len({row["listing_id"] for row in rows}) != len(rows):
        raise ModelContractError("one reviewed observation per seller listing is required")
    for row in rows:
        p = row["predictors"]
        if (row["source_role"] != "retail" or p["identity.source_role"] != "retail"
                or row["comparable_group"] != "bar" or p["identity.product_group"] != "bar"
                or p["identity.boundary_status"] != "in_scope" or p["quantity.pack_count"] != 1
                or p[RETAILER] not in {"Waitrose", "Ocado"}):
            raise ModelContractError("row is outside the reviewed standard single-pack supermarket bar population")
        if p[MASS] <= 0:
            raise ModelContractError("edible mass must be positive")
    return rows


def fit_retailer_median(rows, design):
    rows = sorted(reviewed_rows(rows, design), key=lambda row: row["observation_id"])
    if not rows:
        raise ModelContractError("no reviewed fitting observations")
    weights = family_weights(rows)
    unit_field, _ = target_fields(design)
    groups, retailers = defaultdict(list), defaultdict(list)
    for row, weight in zip(rows, weights):
        p = row["predictors"]
        item = (row, weight)
        groups[(p[RETAILER], p[TYPE])].append(item)
        retailers[p[RETAILER]].append(item)

    def summary(items):
        members = [row for row, _ in items]
        return {"unit_price_gbp": weighted_median(
            [row["target"][unit_field] for row in members],
            [weight for _, weight in items]),
            "observations": len(members), "families": len({r["family_id"] for r in members}),
            "balancing_mass": math.fsum(weight for _, weight in items)}

    return {"model_id": MODEL_ID, "model_format_version": "retailer-median-1",
            "design": design, "price_target_policy": validate_pricing_policy(design["target"]),
            "training_rows_sha256": checksum(json_bytes(rows)),
            "training_family_ids": sorted({row["family_id"] for row in rows}),
            "training_listing_ids": sorted(row["listing_id"] for row in rows),
            "training_variant_families": {row["variant_id"]: row["family_id"] for row in rows},
            "weighting": "1/n_f across the complete fitting partition; retain these weights inside median groups",
            "median_tie_rule": "lower_value_at_half_mass", "predictors": list(PREDICTORS),
            "type_levels": sorted({row["predictors"][TYPE] for row in rows}),
            "retailers": {retailer: {**summary(items),
                "minimum_mass_g": min(row["predictors"][MASS] for row, _ in items),
                "maximum_mass_g": max(row["predictors"][MASS] for row, _ in items),
                "brands": sorted({row["predictors"]["identity.brand"] for row, _ in items}),
                "types": {kind: summary(members) for (seller, kind), members in sorted(groups.items()) if seller == retailer}}
                for retailer, items in sorted(retailers.items())},
            "support_rules": {"unseen_retailer": "reject", "unseen_type": "reject",
                "missing_retailer_type_cell": "use_frozen_retailer_wide_median_and_flag",
                "mass": "positive_and_within_fitting_retailer_range; conversion_only",
                "unseen_brand": "experimental_baseline; no calibrated new-brand claim",
                "sparse_strata": "experimental; no statistical sufficiency claim"},
            "uncertainty": {"method": "none", "split_conformal_required": False,
                            "prediction_intervals_available": False}, "release_ready": False}


def predict_retailer_median(model, profile):
    """Prediction requires reviewed population context, but no observed price."""
    if model.get("model_format_version") != "retailer-median-1" or model.get("model_id") != MODEL_ID:
        raise ModelContractError("unsupported retailer median model")
    validate_design(model["design"])
    if model.get("price_target_policy") != validate_pricing_policy(model["design"]["target"]):
        raise ModelContractError("model target policy drift")
    if (profile.get("identity.product_group") != "bar" or profile.get("identity.source_role") != "retail"
            or profile.get("identity.boundary_status") != "in_scope"
            or type(profile.get("quantity.pack_count")) not in (int, float)
            or profile.get("quantity.pack_count") != 1
            or profile.get("cohort", model["design"]["comparison_experiment"]["cohort"])
            != model["design"]["comparison_experiment"]["cohort"]):
        return {"domain_member": False, "reason": "unsupported_or_unreviewed_population"}
    mass = profile.get(MASS)
    if type(mass) not in (int, float) or not math.isfinite(mass) or mass <= 0:
        return {"domain_member": False, "reason": "invalid_edible_mass"}
    retailer, kind = profile.get(RETAILER), profile.get(TYPE)
    if not isinstance(retailer, str) or not isinstance(kind, str):
        return {"domain_member": False, "reason": "invalid_retailer_or_type"}
    context = model["retailers"].get(retailer)
    if context is None:
        return {"domain_member": False, "reason": "unseen_retailer"}
    if kind not in model["type_levels"]:
        return {"domain_member": False, "reason": "unseen_type"}
    if not context["minimum_mass_g"] <= mass <= context["maximum_mass_g"]:
        return {"domain_member": False, "reason": "mass_outside_fitting_retailer_range"}
    fallback = kind not in context["types"]
    cell = context if fallback else context["types"][kind]
    unit = cell["unit_price_gbp"]
    if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
        raise ModelContractError("invalid fitted median")
    pack = unit * (mass / 100)
    if not math.isfinite(pack) or pack <= 0:
        raise ModelContractError("pack prediction cannot be represented")
    brand = profile.get("identity.brand")
    return {"domain_member": True, "predicted_unit_price_gbp": unit,
            "predicted_log_unit_price": math.log(unit), "predicted_pack_price_gbp": pack,
            "retailer_wide_fallback": fallback, "support_families": cell["families"],
            "brand_context_supported": brand in context["brands"],
            "status": "experimental", "prediction_interval": None}


def metrics(records, *, listing_weighted=False):
    if not records:
        return None
    weights = [1.0] * len(records) if listing_weighted else family_weights(records)
    total = math.fsum(weights)
    unit_errors = [r["predicted_unit_price_gbp"] - r["observed_unit_price_gbp"] for r in records]
    pack_errors = [r["predicted_pack_price_gbp"] - r["observed_pack_price_gbp"] for r in records]
    def mean(values):
        return math.fsum(w * v for w, v in zip(weights, values)) / total
    result = {"observations": len(records), "families": len({r["family_id"] for r in records}),
            "MAE_GBP_per_100g": mean([abs(e) for e in unit_errors]),
            "MAE_GBP_per_pack": mean([abs(e) for e in pack_errors]),
            "signed_bias_GBP_per_100g": mean(unit_errors), "signed_bias_GBP_per_pack": mean(pack_errors),
            "median_absolute_percentage_error": weighted_median(
                [100 * (abs(e) / r["observed_unit_price_gbp"]) for e, r in zip(unit_errors, records)], weights)}
    if any(not math.isfinite(value) for value in result.values()):
        raise ModelContractError("nonfinite evaluation metric")
    return result


def evaluate_retailer_median(rows, model, fitting_rows):
    fitting = reviewed_rows(fitting_rows, model["design"])
    if checksum(json_bytes(sorted(fitting, key=lambda r: r["observation_id"]))) != model["training_rows_sha256"]:
        raise ModelContractError("fitting rows differ from frozen model")
    rows = reviewed_rows(rows, model["design"])
    validate_pricing_candidates(fitting + rows, model["design"])
    if set(model["training_family_ids"]) & {r["family_id"] for r in rows}:
        raise ModelContractError("evaluation families overlap fitting")
    if set(model["training_listing_ids"]) & {r["listing_id"] for r in rows}:
        raise ModelContractError("evaluation listings overlap fitting")
    predictions = []
    unit_field, _ = target_fields(model["design"])
    for row in rows:
        p = row["predictors"]
        unit = row["target"][unit_field]
        record = {"observation_id": row["observation_id"], "listing_id": row["listing_id"],
                  "family_id": row["family_id"], "retailer": p[RETAILER], "type": p[TYPE],
                  "brand": p["identity.brand"], "observed_unit_price_gbp": unit,
                  "observed_pack_price_gbp": unit * (p[MASS] / 100),
                  "size": "up_to_50g" if p[MASS] <= 50 else "over_50_to_100g" if p[MASS] <= 100 else "over_100g",
                  "missingness": "all_required_baseline_fields_present",
                  "price_target_policy": model["price_target_policy"],
                  **predict_retailer_median(model, p)}
        predictions.append(record)
    supported = [r for r in predictions if r["domain_member"]]
    def support(members):
        accepted = [r for r in members if r["domain_member"]]
        return {"observations": len(members), "families": len({r["family_id"] for r in members}),
                "supported_observations": len(accepted), "supported_families": len({r["family_id"] for r in accepted}),
                "coverage": len(accepted) / len(members) if members else 0,
                "family_weighted": metrics(accepted), "listing_weighted": metrics(accepted, listing_weighted=True),
                "support_status": "experimental_statistical_sufficiency_unestablished"}
    breakdowns = {}
    for name in ("retailer", "type", "size", "brand", "missingness"):
        breakdowns[name] = {value: support([r for r in predictions if r[name] == value])
                            for value in sorted({r[name] for r in predictions})}
    return {**support(predictions), "predictions": predictions, "breakdowns": breakdowns,
            "price_target_policy": model["price_target_policy"],
            "fallback_observations": sum(r["retailer_wide_fallback"] for r in supported),
            "weighting": "recompute 1/n_f within each supported partition/stratum",
            "comparison_release_gates": "pending_comparator_runs", "release_ready": False,
            "optional_evidence_missingness": "unavailable_in_this_baseline_input_contract"}
