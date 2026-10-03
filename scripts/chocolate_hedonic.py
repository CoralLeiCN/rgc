"""Independent family-weighted hedonic_without_brand experiment.

Working policies are local preparation artifacts until an approved dataset release.
Evidence and eligibility remain in Silver; this module cannot promote candidates.
"""

import hashlib
import math
import platform
import random
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
from chocolate_gold import checked_path, read_managed, verified_gold
from chocolate_model import (
    ModelContractError,
    validate_candidates,
    validate_target_policy,
)
from chocolate_regression import _fit_matrix
from train_chocolate_model import (
    CONTRACTS,
    ROOT,
    checksum,
    json_bytes,
    read_json,
    rows,
    validate_price_targets,
    write_run,
)

MODEL_ID = "hedonic_without_brand"
FORMAT = "chocolate-family-hedonic-1"
WEIGHT = "quantity.total_edible_weight_g"
RETAILER = "identity.retailer"
TYPE = "composition.chocolate_type"
RECIPE = "composition.recipe_class"
NUTS = "composition.nuts_presence"
BRAND = "identity.brand"
COCOA = "composition.cocoa_percentage"
BASIS = "composition.cocoa_basis"
COHORT = "study.cohort"
PACK_COUNT = "quantity.pack_count"
CORE = [WEIGHT, TYPE, RECIPE, NUTS, RETAILER]
CLAIMS = ["dietary.vegan_claim", "certifications.fairtrade_claim", "certifications.organic_claim"]
OPTIONAL = [COCOA, BASIS, *CLAIMS]
COHORT_ID = "uk-supermarket-single-pack-bars-1"
IMPLEMENTATION = ["scripts/chocolate_hedonic.py", "scripts/train_chocolate_model.py",
                  "scripts/chocolate_gold.py", "scripts/chocolate_model.py",
                  "scripts/chocolate_regression.py", "scripts/chocolate_cleanup/core.py"]


def working_contract():
    """Prepare an explicit local contract; never change the published OLS pin."""
    return {
        "contract_version": "chocolate-supermarket-hedonic-working-1",
        "publication_status": "local_unpublished",
        "model_id": MODEL_ID,
        "feature_policy_version": "chocolate-supermarket-features-1",
        "cohort": COHORT_ID,
        "retailers": ["Ocado", "Waitrose"],
        "core_features": CORE,
        "optional_features": OPTIONAL,
        "required_context": [BRAND, COHORT, PACK_COUNT],
        "categorical_unknown": "unknown",
        "claim_levels": ["present", "explicitly_absent", "unknown"],
        "cocoa_basis_levels": ["whole_product", "chocolate_portion", "unknown"],
        "recipe_levels": ["plain", "inclusion", "filled"],
        "type_levels": ["dark", "milk", "white"],
        "nuts_levels": ["present", "absent", "unknown"],
        "optional_numeric_policy": "fitting_median_by_type_and_basis_then_global_with_missing_indicator",
        "category_policy": "fitting_only_sorted_levels_family_weighted_mode_reference_ocado_for_retailer",
        "support_policy": "seen_category_combination_and_retailer_numeric_range",
        "minimum_cell_families_for_interval": 9,
        "split": {"seed": 1729, "fractions": [0.6, 0.2, 0.2],
                  "algorithm": "sha256_seed_colon_family_utf8_sort_round_half_up_calibration_then_test"},
        "validation_folds": 3,
        "interaction_candidates": ["none", "retailer_type", "retailer_weight", "both"],
        "interaction_minimum_improvement": 0.05,
        "interaction_stability": {"replicates": 30, "minimum_success_fraction": 0.8,
                                  "maximum_beta_standard_deviation": 1.0},
        "calibration": {"coverage": 0.9, "seed": 1729,
                        "selection": "sorted_observation_ids_random_choice_seeded_sha256_seed_retailer_family"},
        "bootstrap": {"replicates": 200, "seed": 1729, "minimum_successes": 20,
                      "minimum_success_fraction": 0.8},
        "price_target_policy": "regular-consumer-price-1",
        "release_ready": False,
    }


def validate_working_contract(contract):
    # Exact allowlist prevents names, IDs, price-derived fields and undeclared
    # optional inputs from entering an otherwise apparently compatible policy.
    if contract != working_contract():
        raise ModelContractError("unsupported working contract; prepare the declared local version")
    return contract


def fingerprint(value):
    return checksum(json_bytes(value))


def family_weights(values):
    counts = Counter(row["family_id"] for row in values)
    return np.asarray([1.0 / counts[row["family_id"]] for row in values])


def family_order(families, seed=1729):
    return sorted(set(families), key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f))


def partitions(values, seed=1729):
    ordered = family_order((r["family_id"] for r in values), seed)
    n = len(ordered)
    count = int(n * 0.2 + 0.5)
    assignment = {f: "calibration" if i < count else "test" if i < 2 * count else "fitting"
                  for i, f in enumerate(ordered)}
    result = {p: sorted((r for r in values if assignment[r["family_id"]] == p),
                        key=lambda r: r["observation_id"]) for p in ("fitting", "calibration", "test")}
    return result, dict(sorted(assignment.items()))


def _number(value, name, minimum=0, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ModelContractError("invalid numeric input: " + name)
    if maximum is not None and value > maximum:
        raise ModelContractError("numeric input exceeds allowed range: " + name)
    return float(value)


def candidate_value_audit(candidates, observations):
    """Inspect current values even when every persisted eligibility flag is false."""
    def positive(value):
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)
    return {"candidate_rows": len(candidates),
            "positive_regular_unit_targets": sum(positive(r["target"]["regular_price_per_100g_gbp"]) for r in candidates),
            "finite_log_targets": sum(finite(r["target"]["log_regular_price_per_100g_gbp"]) for r in candidates),
            "resolved_variant_ids": sum(bool(r["variant_id"]) for r in candidates),
            "resolved_family_ids": sum(bool(r["family_id"]) for r in candidates),
            "positive_edible_weight_values": sum(positive(r["predictors"].get(WEIGHT)) for r in candidates),
            "positive_regular_pack_price_observations": sum(positive(r.get("regular_price")) for r in observations),
            "consumer_tax_included_observations": sum(r.get("tax_basis") == "consumer_tax_included" for r in observations),
            "tax_basis_counts": dict(sorted(Counter(str(r.get("tax_basis")) for r in observations).items()))}


def _category(value, name, allowed=None):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ModelContractError("missing reviewed categorical input: " + name)
    if allowed is not None and value not in allowed:
        raise ModelContractError("unsupported categorical input: " + name)
    return value


def validate_features(features, contract, enriched=False, require_brand=False):
    p = features
    _number(p.get(WEIGHT), WEIGHT, minimum=1e-12)
    _category(p.get(TYPE), TYPE, contract["type_levels"])
    _category(p.get(RECIPE), RECIPE, contract["recipe_levels"])
    _category(p.get(NUTS), NUTS, contract["nuts_levels"])
    _category(p.get(RETAILER), RETAILER, contract["retailers"])
    _category(p.get(COHORT), COHORT, [contract["cohort"]])
    if type(p.get(PACK_COUNT)) not in (int, float) or p[PACK_COUNT] != 1:
        raise ModelContractError("population requires a reviewed single consumer pack")
    if require_brand or p.get(BRAND) is not None:
        _category(p.get(BRAND), BRAND)
        if p[BRAND].casefold() in {"unknown", "unresolved", "not_applicable"}:
            raise ModelContractError("reviewed brand identity is required")
    if enriched:
        _category(p.get(BASIS), BASIS, contract["cocoa_basis_levels"])
        if COCOA not in p:
            raise ModelContractError("optional cocoa requires an explicit value or null")
        if p[COCOA] is not None:
            _number(p[COCOA], COCOA, maximum=100)
            if p[BASIS] == "unknown":
                raise ModelContractError("observed cocoa requires a reviewed constituent basis")
        for name in CLAIMS:
            _category(p.get(name), name, contract["claim_levels"])


def validate_rows(values, contract, target):
    if target.get("price_basis_contract_version") != contract["price_target_policy"]:
        raise ModelContractError("working contract requires regular-consumer-price-1 target policy")
    identity_design = {"target": target, "predictors": {
        WEIGHT: {"type": "numeric", "transform": "log", "required": True,
                 "missing_policy": "reject", "minimum": 0},
        **{n: {"type": "categorical", "reference": "training_mode", "required": True,
               "missing_policy": "reject"} for n in (TYPE, RECIPE, NUTS, RETAILER, BRAND, COHORT)},
        PACK_COUNT: {"type": "numeric", "required": True, "missing_policy": "reject",
                     "minimum": 1, "maximum": 1},
    }}
    validate_candidates(values, identity_design)
    if len({r["listing_id"] for r in values}) != len(values):
        raise ModelContractError("reviewed cross-sectional selection requires one row per seller listing")
    variants = {}
    for row in values:
        if row["source_role"] != "retail" or row["comparable_group"] != "bar":
            raise ModelContractError("row is outside the supermarket chocolate-bar population")
        validate_features(row["predictors"], contract, require_brand=True)
        product = tuple(row["predictors"][n] for n in (WEIGHT, TYPE, RECIPE, NUTS, BRAND, PACK_COUNT))
        if variants.setdefault(row["variant_id"], product) != product:
            raise ModelContractError("exact variant has inconsistent reviewed product identity or core features")


def _weighted_median(values, weights):
    pairs = sorted(zip(values, weights))
    cumulative, half = 0.0, math.fsum(weights) / 2
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= half:
            return float(value)
    raise ModelContractError("cannot calculate median without support")


def fit_encoder(values, contract, enriched, interactions, reference_encoder=None, omit_retailer_terms=False):
    """Learn references, optional imputation and joint support on this fold only."""
    features = CORE + (OPTIONAL if enriched else [])
    for row in values:
        validate_features(row["predictors"], contract, enriched=enriched, require_brand=True)
    weights = family_weights(values)
    encoder = {"features": features, "enriched": enriched, "interactions": interactions,
               "columns": ["intercept", WEIGHT], "categories": {}, "numeric_ranges": {},
               "constant_categories": [], "training_family_ids": sorted({r["family_id"] for r in values})}
    categorical = [n for n in features if n not in (WEIGHT, COCOA)]
    for name in categorical:
        levels = sorted({r["predictors"][name] for r in values})
        totals = {v: math.fsum(w for r, w in zip(values, weights) if r["predictors"][name] == v) for v in levels}
        reference = "Ocado" if name == RETAILER and "Ocado" in levels else min(levels, key=lambda v: (-totals[v], v))
        if reference_encoder is not None:
            original = reference_encoder["categories"][name]
            if levels != original["levels"]:
                raise ModelContractError("bootstrap lacks levels of the fixed selected formula")
            reference = original["reference"]
        encoder["categories"][name] = {"levels": levels, "reference": reference,
            "family_support": {v: len({r["family_id"] for r in values if r["predictors"][name] == v}) for v in levels}}
        encoder["columns"].extend(name + "=" + v for v in levels if v != reference)
        if len(levels) == 1:
            encoder["constant_categories"].append(name)
    if enriched:
        observed = [r["predictors"][COCOA] for r in values if r["predictors"][COCOA] is not None]
        if not observed:
            raise ModelContractError("optional cocoa has no fitting evidence")
        global_median = float(np.median(observed))
        groups = defaultdict(list)
        for row in values:
            p = row["predictors"]
            if p[COCOA] is not None:
                groups[p[TYPE] + "|" + p[BASIS]].append(p[COCOA])
        encoder["cocoa_imputation"] = {"global": global_median,
            "groups": {g: float(np.median(v)) for g, v in sorted(groups.items())}}
        encoder["columns"].append(COCOA)
        missing = {r["predictors"][COCOA] is None for r in values}
        encoder["cocoa_missing_levels"] = sorted(missing)
        if len(missing) > 1:
            encoder["columns"].append(COCOA + ":missing")
    retailer_terms = [c for c in encoder["columns"] if c.startswith(RETAILER + "=")]
    if interactions in ("retailer_weight", "both"):
        encoder["columns"].extend(r + "*" + WEIGHT for r in retailer_terms)
    if interactions in ("retailer_type", "both"):
        encoder["columns"].extend(r + "*" + t for r in retailer_terms
                                  for t in list(encoder["columns"]) if t.startswith(TYPE + "="))
    if reference_encoder is not None and encoder["columns"] != reference_encoder["columns"]:
        raise ModelContractError("bootstrap lacks columns of the fixed selected formula")
    if omit_retailer_terms:
        encoder["columns"] = [c for c in encoder["columns"] if not c.startswith(RETAILER + "=")]
    encoder["retailer_terms_omitted_for_diagnostic"] = omit_retailer_terms
    # Numeric support is retailer-specific; the joint category filter includes
    # all fitted categorical terms, so unseen combinations are explicit failures.
    cells = defaultdict(set)
    for row in values:
        p = row["predictors"]
        cells[_cell(p, encoder)].add(row["family_id"])
    encoder["joint_family_support"] = {k: len(v) for k, v in sorted(cells.items())}
    for retailer in encoder["categories"][RETAILER]["levels"]:
        subset = [r for r in values if r["predictors"][RETAILER] == retailer]
        encoder["numeric_ranges"][retailer] = {WEIGHT: [min(r["predictors"][WEIGHT] for r in subset),
                                                      max(r["predictors"][WEIGHT] for r in subset)]}
        if enriched:
            cocoa = [r["predictors"][COCOA] for r in subset if r["predictors"][COCOA] is not None]
            encoder["numeric_ranges"][retailer][COCOA] = [min(cocoa), max(cocoa)] if cocoa else None
    return encoder


def _cell(p, encoder):
    # Canonical field order survives JSON's sorted-key serialization and reload.
    return fingerprint([p[n] for n in sorted(encoder["categories"])] +
                       ([p[COCOA] is None] if encoder["enriched"] else []))


def encode(p, encoder, contract, support=True):
    validate_features(p, contract, enriched=encoder["enriched"])
    result = {"intercept": 1.0, WEIGHT: math.log(p[WEIGHT])}
    for name, spec in encoder["categories"].items():
        if p[name] not in spec["levels"]:
            raise ModelContractError("unseen fitting level: " + name)
        result.update({name + "=" + v: float(p[name] == v) for v in spec["levels"] if v != spec["reference"]})
    if encoder["enriched"]:
        imputation = encoder["cocoa_imputation"]
        result[COCOA] = p[COCOA] if p[COCOA] is not None else imputation["groups"].get(
            p[TYPE] + "|" + p[BASIS], imputation["global"])
        result[COCOA + ":missing"] = float(p[COCOA] is None)
        if (p[COCOA] is None) not in encoder["cocoa_missing_levels"]:
            raise ModelContractError("unseen cocoa missingness pattern")
    if support:
        if _cell(p, encoder) not in encoder["joint_family_support"]:
            raise ModelContractError("unsupported fitted feature combination")
        for name, bounds in encoder["numeric_ranges"][p[RETAILER]].items():
            value = p[name]
            if value is not None and (bounds is None or not bounds[0] <= value <= bounds[1]):
                raise ModelContractError("outside retailer fitting range: " + name)
    for column in encoder["columns"]:
        if "*" in column:
            a, b = column.split("*", 1)
            result[column] = result[a] * result[b]
    return np.asarray([result[c] for c in encoder["columns"]])


def _fit(values, contract, enriched=False, interactions="none", probe=True, reference_encoder=None,
         omit_retailer_terms=False):
    if len({r["family_id"] for r in values}) < 2:
        raise ModelContractError("fitting requires independent families")
    encoder = fit_encoder(values, contract, enriched, interactions, reference_encoder, omit_retailer_terms)
    matrix = np.asarray([encode(r["predictors"], encoder, contract, support=False) for r in values])
    y = np.asarray([r["target"]["log_regular_price_per_100g_gbp"] for r in values])
    weights = family_weights(values)
    # Accelerate can leave floating-point status flags set on this platform.
    # The solver independently refuses every nonfinite input and output.
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        beta, _, _, rank = _fit_matrix(np, matrix * np.sqrt(weights[:, None]), y * np.sqrt(weights))
    identification = None
    if probe:
        brands = sorted({r["predictors"][BRAND] for r in values})
        brand_columns = np.asarray([[float(r["predictors"][BRAND] == b) for b in brands[1:]] for r in values])
        augmented = np.column_stack((matrix, brand_columns))
        singular = np.linalg.svd(augmented * np.sqrt(weights[:, None]), compute_uv=False)
        augmented_rank = int(np.linalg.matrix_rank(augmented * np.sqrt(weights[:, None])))
        condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else math.inf
        if augmented_rank != augmented.shape[1] or condition > 1e12 or len(values) <= augmented.shape[1]:
            raise ModelContractError("common known-brand identification probe failed; required or optional terms are aliased")
        identification = {"method": "weighted_design_rank_probe_without_fitting_brand_estimator",
                          "brands": brands, "columns": augmented.shape[1], "rank": augmented_rank,
                          "condition_number": condition, "reference_brand": brands[0]}
    model = {"model_id": MODEL_ID, "model_format_version": FORMAT, "estimator": "family_weighted_log_linear_least_squares",
             "weighting": "1/n_f_recomputed_in_partition_or_fold", "encoder": encoder,
             "coefficients": dict(zip(encoder["columns"], map(float, beta))), "rank_diagnostics": rank,
             "known_brand_identification": identification, "working_contract": deepcopy(contract),
             "training_brands": sorted({r["predictors"][BRAND] for r in values}),
             "training_family_ids": sorted({r["family_id"] for r in values}),
             "training_rows_sha256": fingerprint(values), "release_ready": False,
             "estimate_type": "geometric_price_benchmark", "retransformation": "exp_without_mean_correction"}
    return model


def _price(value):
    try:
        result = math.exp(float(value))
    except OverflowError as error:
        raise ModelContractError("prediction overflows the price scale") from error
    if not math.isfinite(result) or result <= 0:
        raise ModelContractError("prediction is not a finite positive price")
    return result


def predict(features, model, *, include_uncertainty=True):
    if model.get("model_id") != MODEL_ID or model.get("model_format_version") != FORMAT:
        raise ModelContractError("unsupported hedonic model")
    contract = validate_working_contract(model["working_contract"])
    matrix = encode(features, model["encoder"], contract)
    beta = np.asarray([model["coefficients"][c] for c in model["encoder"]["columns"]])
    logged = float(matrix @ beta)
    unit = _price(logged)
    cell_count = model["encoder"]["joint_family_support"][_cell(features, model["encoder"])]
    brand = features.get(BRAND)
    known = brand is None or brand in model["training_brands"]
    result = {"model_id": MODEL_ID, "predicted_log_price": logged, "predicted_price_per_100g_gbp": unit,
              "predicted_pack_price_gbp": unit * features[WEIGHT] / 100,
              "estimate_type": "geometric_price_benchmark", "point_supported": True,
              "cell_families": cell_count, "known_brand_context": known,
              "interval": None, "interval_status": "unavailable", "release_ready": False}
    calibration = model.get("calibration", {}).get("retailers", {}).get(features[RETAILER], {})
    if (include_uncertainty and known and cell_count >= contract["minimum_cell_families_for_interval"]
            and calibration.get("quantile") is not None):
        q = calibration["quantile"]
        try:
            endpoints = [_price(logged - q), _price(logged + q)]
        except ModelContractError:
            result["interval_status"] = "unbounded_price_scale"
        else:
            result["interval"] = {"coverage": 0.9, "unit_gbp_per_100g": endpoints,
                                  "pack_gbp": [v * features[WEIGHT] / 100 for v in endpoints],
                                  "scope": "retailer_snapshot_representative_family_marginal"}
            result["interval_status"] = "experimental_calibrated"
    if not known:
        result["interval_status"] = "unseen_brand_experimental_point_only"
    elif cell_count < contract["minimum_cell_families_for_interval"]:
        result["interval_status"] = "insufficient_joint_family_support"
    return result


def prediction_records(values, model):
    result = []
    for row in values:
        record = {k: row[k] for k in ("observation_id", "listing_id", "variant_id", "family_id")}
        record.update(retailer=row["predictors"][RETAILER], brand=row["predictors"][BRAND],
                      observed_price_per_100g_gbp=row["target"]["regular_price_per_100g_gbp"],
                      observed_log_price=row["target"]["log_regular_price_per_100g_gbp"],
                      edible_weight_g=row["predictors"][WEIGHT])
        try:
            record.update(predict(row["predictors"], model))
        except ModelContractError as error:
            record.update(point_supported=False, domain_reason=str(error))
        result.append(record)
    return result


def metrics(records, weighted=True):
    if not records:
        return None
    weights = family_weights(records) if weighted else np.ones(len(records))
    actual = np.asarray([r["observed_price_per_100g_gbp"] for r in records])
    error = np.asarray([r["predicted_price_per_100g_gbp"] for r in records]) - actual
    mass = np.asarray([r["edible_weight_g"] for r in records]) / 100
    total = weights.sum()
    return {"rows": len(records), "families": len({r["family_id"] for r in records}),
            "MAE_GBP_per_100g": float(weights @ np.abs(error) / total),
            "MAE_GBP_per_pack": float(weights @ (np.abs(error) * mass) / total),
            "signed_bias_GBP_per_100g": float(weights @ error / total),
            "signed_bias_GBP_per_pack": float(weights @ (error * mass) / total),
            "weighted_median_absolute_percentage_error": _weighted_median(100 * np.abs(error) / actual, weights)}


def bootstrap(values, contract, enriched, interactions, replicates, *, probe=False, reference_encoder=None):
    """Refit preprocessing and formula; each sampled family copy has weight one."""
    families = sorted({r["family_id"] for r in values})
    groups = {f: [r for r in values if r["family_id"] == f] for f in families}
    generator = np.random.default_rng(contract["bootstrap"]["seed"])
    models, failures = [], Counter()
    for _ in range(replicates):
        sampled = []
        for copy_index, family in enumerate(generator.choice(families, len(families), replace=True)):
            for row in groups[family]:
                sample = {**row, "family_id": f"bootstrap-copy-{copy_index}"}
                sampled.append(sample)
        try:
            models.append(_fit(sampled, contract, enriched, interactions, probe=probe,
                               reference_encoder=reference_encoder))
        except ModelContractError as error:
            failures[str(error)] += 1
    return models, dict(sorted(failures.items()))


def _coefficient_intervals(model, draws, contract):
    # A fixed formula retains its named contrasts; bootstrap preprocessing is
    # refitted, and draws missing any selected column are counted as failures.
    result = {}
    for column in model["coefficients"]:
        values = [d["coefficients"][column] for d in draws if column in d["coefficients"]]
        available = len(values) >= max(contract["bootstrap"]["minimum_successes"],
                                       contract["bootstrap"]["replicates"] * contract["bootstrap"]["minimum_success_fraction"])
        name, _, level = column.partition("=")
        reference = model["encoder"]["categories"].get(name, {}).get("reference")
        result[column] = {"beta": model["coefficients"][column], "reference": reference,
                          "comparison_level": level or None,
                          "contrast_units": "weight_ratio_e" if column == WEIGHT else "percentage_point" if column == COCOA else "named_formula_term",
                          "successful_comparable_draws": len(values),
                          "confidence_interval_95": list(map(float, np.quantile(values, [0.025, 0.975]))) if available else None}
    return result


def select_formula(values, contract):
    """Grouped fitting-only CV; held-out outcomes never enter formula selection."""
    families = family_order(r["family_id"] for r in values)
    folds = {f: i % contract["validation_folds"] for i, f in enumerate(families)}
    results, candidates = [], []
    for enriched in (False, True):
        for interactions in contract["interaction_candidates"]:
            record = {"enriched": enriched, "interactions": interactions, "folds": [], "accepted": False}
            combined = []
            try:
                for fold in range(contract["validation_folds"]):
                    train = [r for r in values if folds[r["family_id"]] != fold]
                    heldout = [r for r in values if folds[r["family_id"]] == fold]
                    fit = _fit(train, contract, enriched, interactions)
                    predictions = prediction_records(heldout, fit)
                    supported = [r for r in predictions if r["point_supported"]]
                    record["folds"].append({"fold": fold, "fitting_families": len({r["family_id"] for r in train}),
                                            "validation_families": len({r["family_id"] for r in heldout}),
                                            "rows": len(heldout), "supported": len(supported),
                                            "metrics": metrics(supported)})
                    if len(supported) != len(heldout):
                        raise ModelContractError("grouped validation candidate lacks complete common-row support")
                    combined.extend(supported)
                fit = _fit(values, contract, enriched, interactions)
                record["score"] = metrics(combined)["MAE_GBP_per_100g"]
                if interactions != "none":
                    stability = contract["interaction_stability"]
                    draws, failures = bootstrap(values, contract, enriched, interactions, stability["replicates"],
                                                probe=True, reference_encoder=fit["encoder"])
                    record["stability"] = {"successful_replicates": len(draws), "failures": failures}
                    if len(draws) < stability["replicates"] * stability["minimum_success_fraction"]:
                        raise ModelContractError("retailer interaction bootstrap is unstable")
                    for column in fit["coefficients"]:
                        if "*" in column:
                            comparable = [d["coefficients"][column] for d in draws if column in d["coefficients"]
                                          and all(d["encoder"]["categories"][n]["reference"] == fit["encoder"]["categories"][n]["reference"]
                                                  for n in (RETAILER, TYPE))]
                            if len(comparable) < stability["replicates"] * stability["minimum_success_fraction"] or np.std(comparable) > stability["maximum_beta_standard_deviation"]:
                                raise ModelContractError("retailer interaction coefficient lacks stable comparable support")
                record["accepted"] = True
                candidates.append((record["score"], enriched, interactions))
            except ModelContractError as error:
                record["reason"] = str(error)
            results.append(record)
    main = [c for c in candidates if c[2] == "none"]
    if not main:
        raise ModelContractError("no fully identified core formula with complete grouped-validation support")
    best_main = min(main)
    acceptable = [c for c in candidates if c[2] == "none" or
                  c[0] <= best_main[0] * (1 - contract["interaction_minimum_improvement"])]
    selected = min(acceptable)
    return _fit(values, contract, selected[1], selected[2]), {
        "fold_assignments": dict(sorted(folds.items())), "candidates": results,
        "selected": {"enriched": selected[1], "interactions": selected[2]},
        "selection_uses": "fitting_partition_only",
        "optional_alias_policy": "enriched_candidate_rejected_in_both_brand_and_no_brand_policy_if_probe_fails",
    }


def fitting_diagnostics(values, model, selection):
    """Refit only this estimator for training diagnostics, with no calibration claims."""
    contract = model["working_contract"]
    enriched, interactions = model["encoder"]["enriched"], model["encoder"]["interactions"]
    folds = selection["fold_assignments"]
    ablation, brand_holdout = [], []
    for fold in range(contract["validation_folds"]):
        train = [r for r in values if folds[r["family_id"]] != fold]
        heldout = [r for r in values if folds[r["family_id"]] == fold]
        record = {"fold": fold}
        try:
            fit = _fit(train, contract, enriched, "none", omit_retailer_terms=True)
            predictions = prediction_records(heldout, fit)
            supported = [r for r in predictions if r["point_supported"]]
            record.update(rows=len(heldout), supported_rows=len(supported), metrics=metrics(supported))
        except ModelContractError as error:
            record["unavailable_reason"] = str(error)
        ablation.append(record)
    for brand in model["training_brands"]:
        # Keep whole families out even when a reviewed family contains several
        # brand identities. Brand selection is based solely on fitting context.
        held_families = {r["family_id"] for r in values if r["predictors"][BRAND] == brand}
        train = [r for r in values if r["family_id"] not in held_families]
        heldout = [r for r in values if r["family_id"] in held_families and r["predictors"][BRAND] == brand]
        record = {"held_out_brand": brand, "held_out_families": len(held_families), "rows": len(heldout)}
        try:
            fit = _fit(train, contract, enriched, interactions)
            supported = [r for r in prediction_records(heldout, fit) if r["point_supported"]]
            record.update(supported_rows=len(supported), metrics=metrics(supported))
        except ModelContractError as error:
            record["unavailable_reason"] = str(error)
        brand_holdout.append(record)
    return {"uses": "fitting_partition_only_fixed_selected_formula", "no_retailer_ablation": ablation,
            "brand_held_out": brand_holdout, "new_brand_calibration_validated": False,
            "retailer_held_out_prediction": "unsupported_fixed_effect_domain"}


def representatives(values, seed):
    groups = defaultdict(list)
    for row in values:
        groups[row["predictors"][RETAILER], row["family_id"]].append(row)
    result = []
    for (retailer, family), members in sorted(groups.items()):
        members = sorted(members, key=lambda r: r["observation_id"])
        digest = fingerprint([seed, retailer, family])
        generator = random.Random(int(digest, 16))
        result.append(members[generator.randrange(len(members))])
    return result


def calibrate(values, model):
    if set(model["training_family_ids"]) & {r["family_id"] for r in values}:
        raise ModelContractError("calibration overlaps fitting families")
    contract = model["working_contract"]
    selected = representatives(values, contract["calibration"]["seed"])
    predictions = prediction_records(selected, model)
    retailers = {}
    for retailer in model["encoder"]["categories"][RETAILER]["levels"]:
        all_reps = [r for r in predictions if r["retailer"] == retailer]
        supported = [r for r in all_reps if r["point_supported"] and r["known_brand_context"]
                     and r["cell_families"] >= contract["minimum_cell_families_for_interval"]]
        scores = sorted(abs(r["observed_log_price"] - r["predicted_log_price"]) for r in supported)
        n = len(scores)
        k = math.ceil((n + 1) * contract["calibration"]["coverage"])
        retailers[retailer] = {"representative_families": len(all_reps), "supported_families": n,
                               "order_statistic": k, "quantile": scores[k - 1] if k <= n else None,
                               "interval_status": "finite" if k <= n else "unavailable_unbounded",
                               "residual_scores": scores,
                               "residual_records": [{"observation_id": r["observation_id"], "family_id": r["family_id"],
                                                     "observed_log_price": r["observed_log_price"],
                                                     "predicted_log_price": r["predicted_log_price"],
                                                     "absolute_log_residual": abs(r["observed_log_price"] - r["predicted_log_price"])}
                                                    for r in supported],
                               "representative_observation_ids": [r["observation_id"] for r in all_reps],
                               "supported_observation_ids": [r["observation_id"] for r in supported]}
    return {"method": "retailer_split_conformal_absolute_log_residual", "coverage": 0.9,
            "selection": contract["calibration"], "retailers": retailers,
            "scope": "representative_family_within_supported_retailer_snapshot",
            "unseen_brand_validated": False, "future_price_validated": False}


def _wilson_lower(successes, n):
    if n == 0:
        return None
    z = 1.6448536269514722
    p = successes / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)


def evaluate(values, model):
    if set(model["training_family_ids"]) & {r["family_id"] for r in values}:
        raise ModelContractError("evaluation overlaps fitting families")
    records = prediction_records(values, model)
    supported = [r for r in records if r["point_supported"]]
    lookup = {r["observation_id"]: r for r in values}
    variant_retailers = defaultdict(set)
    for r in values:
        variant_retailers[r["variant_id"]].add(r["predictors"][RETAILER])
    breakdowns = {}
    extractors = {
        "retailer": lambda p: p[RETAILER], "type": lambda p: p[TYPE],
        "recipe": lambda p: p[RECIPE], "brand": lambda p: p[BRAND],
        "size": lambda p: "under_75g" if p[WEIGHT] < 75 else "75_to_150g" if p[WEIGHT] <= 150 else "over_150g",
        "missingness": lambda p: "cocoa_missing" if p.get(COCOA) is None else "cocoa_observed",
    }
    for name, extract in extractors.items():
        groups = defaultdict(list)
        for record in records:
            groups[extract(lookup[record["observation_id"]]["predictors"])].append(record)
        breakdowns[name] = {}
        for key, group in sorted(groups.items()):
            valid = [r for r in group if r["point_supported"]]
            breakdowns[name][key] = {"rows": len(group), "families": len({r["family_id"] for r in group}),
                                     "supported_rows": len(valid), "family_weighted": metrics(valid),
                                     "listing_weighted": metrics(valid, weighted=False),
                                     "poorly_supported": len({r["family_id"] for r in valid}) < 9}
    breakdowns["assortment"] = {}
    for label in ("shared_across_retailers", "unique_to_retailer"):
        group = [r for r in records if (len(variant_retailers[r["variant_id"]]) > 1) == (label == "shared_across_retailers")]
        valid = [r for r in group if r["point_supported"]]
        breakdowns["assortment"][label] = {"rows": len(group), "supported_rows": len(valid),
                                           "family_weighted": metrics(valid), "listing_weighted": metrics(valid, weighted=False)}
    rep_ids = {r["observation_id"] for r in representatives(values, model["working_contract"]["calibration"]["seed"])}
    intervals = {}
    for retailer in model["encoder"]["categories"][RETAILER]["levels"]:
        selected = [r for r in records if r["retailer"] == retailer and r["observation_id"] in rep_ids]
        finite = [r for r in selected if r.get("interval")]
        hits = sum(r["interval"]["unit_gbp_per_100g"][0] <= r["observed_price_per_100g_gbp"] <=
                   r["interval"]["unit_gbp_per_100g"][1] for r in finite)
        widths = [(r["interval"]["unit_gbp_per_100g"][1] - r["interval"]["unit_gbp_per_100g"][0]) /
                  r["predicted_price_per_100g_gbp"] for r in finite]
        intervals[retailer] = {"representative_families": len(selected), "finite_intervals": len(finite),
                              "coverage": hits / len(finite) if finite else None,
                              "coverage_wilson_lower_95_one_sided": _wilson_lower(hits, len(finite)),
                              "median_relative_width": float(np.median(widths)) if widths else None}
    return {"rows": len(records), "families": len({r["family_id"] for r in records}),
            "supported_rows": len(supported), "unsupported_rows": len(records) - len(supported),
            "family_weighted": metrics(supported), "listing_weighted": metrics(supported, weighted=False),
            "breakdowns": breakdowns, "representative_family_intervals": intervals,
            "baseline_relative_gate": "pending_comparator_results", "champion_selection": "pending",
            "release_ready": False}, records


def scenario_contrast(a, b, model):
    """Paired family bootstrap for two complete supported price scenarios."""
    pa, pb = predict(a, model), predict(b, model)
    differences, percentages = [], []
    for draw in model.get("bootstrap_models", []):
        try:
            da, db = predict(a, draw), predict(b, draw)
        except ModelContractError:
            continue
        differences.append(db["predicted_pack_price_gbp"] - da["predicted_pack_price_gbp"])
        percentages.append(100 * (db["predicted_pack_price_gbp"] / da["predicted_pack_price_gbp"] - 1))
    required = max(model["working_contract"]["bootstrap"]["minimum_successes"],
                   model["working_contract"]["bootstrap"]["replicates"] * model["working_contract"]["bootstrap"]["minimum_success_fraction"])
    return {"model_id": MODEL_ID, "reference": pa, "comparison": pb,
            "difference_pack_gbp": pb["predicted_pack_price_gbp"] - pa["predicted_pack_price_gbp"],
            "difference_percent": 100 * (pb["predicted_pack_price_gbp"] / pa["predicted_pack_price_gbp"] - 1),
            "successful_supported_draws": len(differences),
            "confidence_interval_pack_gbp_95": list(map(float, np.quantile(differences, [0.025, 0.975]))) if len(differences) >= required else None,
            "confidence_interval_percent_95": list(map(float, np.quantile(percentages, [0.025, 0.975]))) if len(differences) >= required else None,
            "uncertainty": "paired_training_family_bootstrap_refitted_preprocessing_fixed_selected_formula",
            "interpretation": "conditional_association", "prediction_interval_for_difference": False}


def fit_model(fitting, calibration, test, contract, target):
    validate_working_contract(contract)
    family_sets = [{r["family_id"] for r in p} for p in (fitting, calibration, test)]
    if any(family_sets[i] & family_sets[j] for i in range(3) for j in range(i)):
        raise ModelContractError("fitting, calibration and test families must be disjoint")
    validate_rows(fitting + calibration + test, contract, target)
    model, selection = select_formula(fitting, contract)
    model["fitting_diagnostics"] = fitting_diagnostics(fitting, model, selection)
    model["price_target_policy"] = validate_target_policy(target)
    model["target"] = deepcopy(target)
    encoder = model["encoder"]
    draws, failures = bootstrap(fitting, contract, encoder["enriched"], encoder["interactions"],
                               contract["bootstrap"]["replicates"], reference_encoder=encoder)
    model["coefficient_uncertainty"] = _coefficient_intervals(model, draws, contract)
    model["bootstrap_models"] = draws
    model["bootstrap_report"] = {"replicates": contract["bootstrap"]["replicates"], "successful_replicates": len(draws),
                                 "failures": failures, "preprocessing": "refitted_each_family_draw",
                                 "family_copy_total_weight": 1, "formula_selection_uncertainty_included": False}
    model["feature_policy"] = {"version": contract["feature_policy_version"], "features": encoder["features"],
                               "interactions": encoder["interactions"], "brand_predictor": False,
                               "known_brand_probe": model["known_brand_identification"]}
    model["feature_policy_sha256"] = fingerprint(model["feature_policy"])
    model["calibration"] = calibrate(calibration, model)
    evaluation, predictions = evaluate(test, model)
    return model, selection, evaluation, predictions


def build_run(gold_root, output, contract_path, experiment_path=None, *, fixture=False):
    source = Path(gold_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ValueError("model output must be separate from Gold")
    contract_bytes = Path(contract_path).read_bytes()
    contract = validate_working_contract(read_json(contract_bytes))
    gold_bytes = (source / "manifest.json").read_bytes()
    silver, silver_bytes, inputs = verified_gold(source)
    design = read_json(inputs["model-design.json"])
    if design["target"].get("price_basis_contract_version") != contract["price_target_policy"]:
        raise ModelContractError("working contract requires regular-consumer-price-1 target policy")
    policy = validate_target_policy(design["target"])
    candidates, eligible = rows(inputs["training-candidates.jsonl"]), rows(inputs["model-inputs.jsonl"])
    quality = read_json(inputs["quality-report.json"])
    fixture = fixture or quality.get("fixture") is True or silver.get("fixture") is True
    observations = rows(inputs["prices.jsonl"])
    price_index = validate_price_targets(eligible, observations)
    gold = read_json(gold_bytes)
    source_pin = (ROOT / "schemas/chocolate/dataset-contract.json").read_bytes()
    pinned = read_json(source_pin)
    declarations = set(design["predictors"])
    missing = sorted(set(CORE + [COHORT, PACK_COUNT, BRAND]) - declarations)
    blockers = ["Gold contract lacks shared required field: " + n for n in missing]
    if not eligible:
        blockers.append("no_reviewed_eligible_observations")
    if read_json(inputs["quality-report.json"]).get("status") != "complete_snapshot":
        blockers.append("incomplete_source_snapshot")
    # Select only explicitly declared cohorts. Old bar-only rows cannot acquire
    # a supermarket/single-pack designation merely from their group label.
    selected = [r for r in eligible if r["predictors"].get(COHORT) == contract["cohort"]]
    invalid_rows = []
    for row in selected:
        try:
            validate_rows([row], contract, design["target"])
        except ModelContractError as error:
            invalid_rows.append({"observation_id": row["observation_id"], "reason": str(error)})
    if invalid_rows:
        blockers.append("selected_cohort_contains_invalid_required_inputs")
    if eligible and not selected:
        blockers.append("no_eligible_rows_in_declared_cohort")
    if not blockers:
        validate_rows(selected, contract, design["target"])
    split, assignments = partitions(selected, contract["split"]["seed"])
    times = sorted({price_index[r["observation_id"]]["observed_at"] for r in selected},
                   key=lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")))
    experiment = {"experiment_format_version": "chocolate-frozen-experiment-1", "cohort": contract["cohort"],
                  "gold_dataset_version": gold["dataset_version"], "gold_manifest_sha256": checksum(gold_bytes),
                  "gold_logical_tables": gold["tables"], "silver_manifest_sha256": checksum(silver_bytes),
                  "contract_sha256": silver["contract_sha256"], "working_contract_sha256": checksum(contract_bytes),
                  "feature_policy_version": contract["feature_policy_version"], "feature_policy_sha256": fingerprint(contract),
                  "source_price_window": {"start": times[0] if times else None, "end": times[-1] if times else None,
                                          "selection": "all_reviewed_cross_sectional_observations_in_explicit_snapshot_cohort"},
                  "eligibility": "Silver_model_eligible_and_explicit_reviewed_cohort_context",
                  "split": contract["split"], "family_assignments": assignments,
                  "partition_observation_ids": {p: [r["observation_id"] for r in rs] for p, rs in split.items()},
                  "calibration_selection": contract["calibration"], "fixture": fixture}
    if experiment_path and read_json(Path(experiment_path).read_bytes()) != experiment:
        raise ModelContractError("supplied frozen experiment differs from verified data or common policy")
    implementation = {n: checksum((ROOT / n).read_bytes()) for n in IMPLEMENTATION}
    import pyarrow
    identity = {"run_format_version": FORMAT, "model_id": MODEL_ID, "experiment_sha256": fingerprint(experiment),
                "implementation_sha256": implementation, "working_contract_sha256": checksum(contract_bytes),
                "dataset_pin_sha256": checksum(source_pin), "dataset_pin_revision": pinned["revision"],
                "package_versions": {"python": platform.python_version(), "numpy": np.__version__, "pyarrow": pyarrow.__version__},
                "parameters": contract, "fixture": fixture}
    if np.__version__ != "2.2.6" or pyarrow.__version__ != "21.0.0":
        raise ModelContractError("use the locked numerical runtime")
    run_id = "model-run-" + fingerprint(identity)[:24]
    report = {"model_id": MODEL_ID, "run_id": run_id, "status": "readiness_blocked",
              "implemented": True, "fixture": fixture, "fixture_validated": False,
              "real_data_fitted": False, "regression_fitted": False, "calibrated": False, "release_ready": False,
              "counts": {"training_candidates": len(candidates), "eligible_model_inputs": len(eligible),
                         "selected_rows": len(selected), "selected_families": len(assignments),
                         "partitions": {p: {"rows": len(rs), "families": len({r["family_id"] for r in rs})} for p, rs in split.items()}},
              "exclusion_counts": dict(sorted(Counter(e for r in candidates for e in r["exclusion_reasons"]).items())),
              "blockers": blockers, "invalid_rows": invalid_rows, "price_target_policy": policy,
              "candidate_value_audit": candidate_value_audit(candidates, observations),
              "gold_dataset_version": gold["dataset_version"], "silver_dataset_version": silver["dataset_version"],
              "copied_contract_matches_current_pin": {n: checksum(inputs[n]) == pinned["files"][n]["sha256"] for n in CONTRACTS},
              "experiment_sha256": identity["experiment_sha256"],
              "baseline_relative_release_gate": "pending_comparator_results", "champion_selection": "pending",
              "limitations": ["Unpublished working contract; existing dataset pins and historical snapshots are preserved.",
                              "No calibrated unseen-brand, unseen-retailer or future-price claim.",
                              "Geometric price associations do not establish causal premiums or arithmetic mean prices."]}
    files = {"inputs/" + n: b for n, b in inputs.items()}
    files.update({"inputs/gold-manifest.json": gold_bytes, "inputs/silver-manifest.json": silver_bytes,
                  "inputs/dataset-contract.json": source_pin, "working-contract.json": contract_bytes,
                  "experiment.json": json_bytes(experiment), "split.json": json_bytes(assignments)})
    for p, rs in split.items():
        files[p + ".jsonl"] = b"".join(json_bytes(r).replace(b"\n", b" ") + b"\n" for r in rs)
    if not blockers:
        try:
            model, selection, evaluation, predictions = fit_model(split["fitting"], split["calibration"], split["test"], contract, design["target"])
            model.update(run_id=run_id, experiment_sha256=identity["experiment_sha256"],
                         gold_dataset_version=gold["dataset_version"], source_price_window=experiment["source_price_window"])
            files["model.json"] = json_bytes(model)
            files["selection.json"] = json_bytes(selection)
            files["evaluation.json"] = json_bytes(evaluation)
            files["predictions.jsonl"] = b"".join(json_bytes(r).replace(b"\n", b" ") + b"\n" for r in predictions)
            files["calibration.json"] = json_bytes(model["calibration"])
            files["support-rules.json"] = json_bytes(model["encoder"])
            files["uncertainty.json"] = json_bytes({"coefficients": model["coefficient_uncertainty"], "bootstrap": model["bootstrap_report"]})
            files["fitting-diagnostics.json"] = json_bytes(model["fitting_diagnostics"])
            report.update(status="fixture_fitted" if fixture else "experimental_fitted", regression_fitted=True,
                          fixture_validated=fixture, real_data_fitted=not fixture,
                          calibrated=any(v["quantile"] is not None for v in model["calibration"]["retailers"].values()),
                          measured_results=evaluation, feature_policy_sha256=model["feature_policy_sha256"])
        except ModelContractError as error:
            report["blockers"].append(str(error))
    files["report.json"] = json_bytes(report)
    import shlex
    command = ["uv", "run", "python", "scripts/train_chocolate_model.py", "--model-id", MODEL_ID,
               "--gold-root", str(source), "--working-contract", str(Path(contract_path).resolve()), "--output", str(output), "--group", "bar"]
    if fixture:
        command.append("--fixture")
    files["reproduce.txt"] = (" ".join(map(shlex.quote, command)) + "\n").encode()
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
                                        "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}})
    if verified_gold(source)[1] != silver_bytes or (source / "manifest.json").read_bytes() != gold_bytes:
        raise ValueError("Gold changed during experiment")
    if Path(contract_path).read_bytes() != contract_bytes or any(checksum((ROOT / n).read_bytes()) != h for n, h in implementation.items()):
        raise ValueError("working contract or implementation changed during experiment")
    return report, write_run(output, run_id, files)


def load_model(run_root):
    """Verify all immutable run artifacts before loading fitted parameters."""
    root = Path(run_root).resolve()
    manifest_bytes = checked_path(root, "manifest.json", "Model").read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("model_id") != MODEL_ID or manifest.get("run_format_version") != FORMAT:
        raise ModelContractError("unsupported model run")
    data = read_managed(root, manifest["managed_files"], "Model")
    identity = {k: v for k, v in manifest.items() if k not in {"run_id", "managed_files"}}
    if "model-run-" + fingerprint(identity)[:24] != manifest["run_id"]:
        raise ModelContractError("model run identity mismatch")
    if fingerprint(read_json(data["experiment.json"])) != manifest["experiment_sha256"]:
        raise ModelContractError("model experiment identity mismatch")
    model = read_json(data["model.json"])
    if model.get("run_id") != manifest["run_id"] or model.get("experiment_sha256") != manifest["experiment_sha256"]:
        raise ModelContractError("fitted parameters disagree with model run identity")
    if checked_path(root, "manifest.json", "Model").read_bytes() != manifest_bytes:
        raise ModelContractError("model manifest changed during load")
    return model
