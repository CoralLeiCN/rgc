"""Fit only lightgbm_with_brand with frozen grouped validation and native TreeSHAP."""

import math
from collections import defaultdict
from statistics import median

from chocolate_experiment import (
    BASIS,
    BRAND,
    CLAIMS,
    COCOA,
    INCLUSION,
    MASS,
    RECIPE,
    RETAILER,
    TYPE,
    encode,
    family_weights,
    fit_preprocessing,
    folds,
    representatives,
    working_contract,
)
from chocolate_model import ModelContractError
from lightgbm.basic import LightGBMError

MODEL_ID = "lightgbm_with_brand"
VERSIONS = {"lightgbm": "4.6.0", "numpy": "2.2.6", "scipy": "1.15.3", "pyarrow": "21.0.0"}
PARAMETERS = {"objective": "regression", "metric": "None", "learning_rate": 0.03,
              "num_leaves": 15, "max_depth": 4, "min_data_in_leaf": 20, "lambda_l2": 1.0,
              "min_sum_hessian_in_leaf": 3.0, "seed": 1729, "deterministic": True, "force_col_wise": True, "num_threads": 1,
              "verbosity": -1, "feature_pre_filter": False}
SEARCH = [{}, {"num_leaves": 7, "max_depth": 3, "lambda_l2": 3.0}]
MAX_ITERATIONS = 2000
PATIENCE = 50


def runtime():
    from importlib import import_module

    modules = {name: import_module(name) for name in VERSIONS}
    for name, expected in VERSIONS.items():
        if modules[name].__version__ != expected:
            raise ModelContractError("use pinned runtime " + name + "==" + expected)
    return modules["numpy"], modules["lightgbm"]


def supported_matrix(rows, preprocessing):
    np, _ = runtime()
    accepted, matrix, rejected = [], [], []
    for row in rows:
        try:
            encoded = encode(row["predictors"], preprocessing)
        except ModelContractError as error:
            rejected.append({"observation_id": row["observation_id"], "reason": str(error)})
        else:
            accepted.append(row)
            matrix.append(encoded)
    return accepted, np.asarray(matrix, dtype=float), rejected


def dataset(rows, matrix, state, reference=None):
    _, lgb = runtime()
    return lgb.Dataset(matrix, label=[r["target"]["log_regular_price_per_100g_gbp"] for r in rows],
                       weight=family_weights(rows), categorical_feature=state["categorical_indices"],
                       feature_name=[f"feature_{i}" for i in range(len(state["columns"]))],
                       reference=reference, free_raw_data=False)


def weighted_unit_mae(predictions, data):
    np, _ = runtime()
    errors = np.abs(np.exp(predictions) - np.exp(data.get_label()))
    return "family_unit_mae", float(np.average(errors, weights=data.get_weight())), False


def leaf_support(booster, matrix, rows, tree_count):
    np, _ = runtime()
    leaves = np.asarray(booster.predict(matrix, pred_leaf=True, num_iteration=tree_count, num_threads=1))
    if leaves.ndim == 1:
        leaves = leaves[:, None]
    return [{str(int(leaf)): len({rows[i]["family_id"] for i in range(len(rows)) if leaves[i, t] == leaf})
             for leaf in sorted(set(leaves[:, t]))} for t in range(leaves.shape[1])]


def fit(rows):
    np, lgb = runtime()
    grouped_folds, assignment = folds(rows)
    trials = []
    for enriched in (False, True):
        for overrides in SEARCH:
            scores, iterations, details, failure = [], [], [], None
            for fitting, validation in grouped_folds:
                try:
                    state = fit_preprocessing(fitting, enriched)
                    train_rows, x, rejected_train = supported_matrix(fitting, state)
                    held_rows, v, rejected = supported_matrix(validation, state)
                    if len(train_rows) < 20 or not held_rows or len(held_rows) < 0.8 * len(validation):
                        raise ModelContractError("grouped fold has insufficient supported rows")
                    train = dataset(train_rows, x, state)
                    held = dataset(held_rows, v, state, train)
                    booster = lgb.train({**PARAMETERS, **overrides}, train, num_boost_round=MAX_ITERATIONS,
                                        valid_sets=[held], feval=weighted_unit_mae,
                                        callbacks=[lgb.early_stopping(PATIENCE, first_metric_only=True, verbose=False)])
                    tree_count = booster.best_iteration
                    prediction = booster.predict(v, num_iteration=tree_count, raw_score=True, num_threads=1)
                    actual = np.array([r["target"]["regular_price_per_100g_gbp"] for r in held_rows])
                    score = float(np.average(np.abs(np.exp(prediction) - actual), weights=family_weights(held_rows)))
                    scores.append(score)
                    iterations.append(tree_count)
                    details.append({"preprocessing": state, "score": score, "tree_count": tree_count,
                                    "fitting_ids": [r["observation_id"] for r in train_rows],
                                    "validation_ids": [r["observation_id"] for r in held_rows],
                                    "validation_rejections": rejected, "fitting_rejections": rejected_train,
                                    "fitting_weights": family_weights(train_rows), "validation_weights": family_weights(held_rows),
                                    "leaf_family_support": leaf_support(booster, x, train_rows, tree_count)})
                except (ModelContractError, LightGBMError) as error:
                    failure = str(error)
                    break
            trials.append({"enriched": enriched, "parameters": {**PARAMETERS, **overrides},
                           "folds": details, "failure": failure,
                           "score": float(np.mean(scores)) if failure is None else None,
                           "tree_count": max(1, int(median(iterations))) if failure is None else None})
    available = [t for t in trials if t["score"] is not None]
    if not available:
        raise ModelContractError("all grouped fitting trials unavailable: " + "; ".join(sorted({t["failure"] for t in trials})))
    best = min(available, key=lambda t: (t["score"], t["enriched"], t["parameters"]["num_leaves"]))
    state = fit_preprocessing(rows, best["enriched"])
    selected, x, rejected = supported_matrix(rows, state)
    if len(selected) < 20:
        raise ModelContractError("insufficient supported fitting observations")
    booster = lgb.train(best["parameters"], dataset(selected, x, state), num_boost_round=best["tree_count"])
    count = booster.current_iteration()
    bundle = {"model_id": MODEL_ID, "estimator": "lightgbm_squared_error_log_unit_price",
              "preprocessing": state, "parameters": best["parameters"], "tree_count": count,
              "package_versions": VERSIONS, "fitting_observation_ids": [r["observation_id"] for r in selected],
              "fitting_rejections": rejected, "family_weights": family_weights(selected),
              "leaf_family_support": leaf_support(booster, x, selected, count),
              "validation": {"family_fold_assignments": assignment, "trials": trials, "selected_score": best["score"],
                             "maximum_iterations": MAX_ITERATIONS, "early_stopping_patience": PATIENCE,
                             "selection": "lowest_mean_fold_family_weighted_unit_MAE_then_core_then_fewer_leaves"},
              "release_ready": False, "champion_selection": "pending_comparators"}
    return booster, bundle


def prediction(booster, bundle, predictors, explain=True):
    np, _ = runtime()
    state = bundle["preprocessing"]
    x = np.asarray([encode(predictors, state)], dtype=float)
    count = bundle["tree_count"]
    leaves = np.asarray(booster.predict(x, pred_leaf=True, num_iteration=count, num_threads=1)).reshape(-1)
    minimum = working_contract()["minimum_leaf_families"]
    if any(bundle["leaf_family_support"][t].get(str(int(leaf)), 0) < minimum for t, leaf in enumerate(leaves)):
        raise ModelContractError("prediction traverses a leaf with insufficient independent families")
    logged = float(booster.predict(x, raw_score=True, num_iteration=count, num_threads=1)[0])
    try:
        unit = math.exp(logged)
    except OverflowError as error:
        raise ModelContractError("price prediction overflow") from error
    if not math.isfinite(unit) or unit <= 0:
        raise ModelContractError("nonfinite or nonpositive price prediction")
    packet = {"model_id": MODEL_ID, "domain_membership": "supported_known_brand",
              "log_unit_price": logged, "unit_price_gbp_per_100g": unit,
              "pack_price_gbp": unit * predictors[MASS] / 100, "tree_count": count,
              "explanation_status": "unavailable", "attribution_units": "natural_log_GBP_per_100g",
              "limitations": "Conditional model associations; correlated inputs share information. No causal, unseen-brand, unseen-retailer or future-price claim."}
    if explain:
        try:
            # Native exact TreeSHAP supports categorical trees; no background or approximation.
            values = np.asarray(booster.predict(x, pred_contrib=True, num_iteration=count, num_threads=1))[0]
            if len(values) != len(state["columns"]) + 1 or not np.isfinite(values).all() or not math.isclose(
                    float(np.sum(values)), logged, abs_tol=1e-6, rel_tol=1e-5):
                raise ValueError("TreeSHAP raw-output reconstruction failed")
            packet.update(explanation_status="verified", reference_log_value=float(values[-1]),
                          reference_name="model explanation reference",
                          reference_convention="native_exact_tree_path_dependent_stored_path_counts_no_background",
                          shap_log_values={n: float(v) for n, v in zip(state["columns"], values[:-1])},
                          multiplicative_factors={n: math.exp(float(v)) for n, v in zip(state["columns"], values[:-1])},
                          reconstruction_error=abs(float(np.sum(values)) - logged))
        except (ValueError, RuntimeError, OverflowError, LightGBMError) as error:
            packet["explanation_failure"] = str(error)
    packet["narrative"] = f"The model predicts £{unit:.2f} per 100 g and £{packet['pack_price_gbp']:.2f} per pack within its fitting support."
    if packet["explanation_status"] == "verified":
        packet["narrative"] += " Signed log attributions reconstruct the prediction relative to the model explanation reference. They describe model associations."
    return packet


def predict_rows(rows, booster, bundle, explain=False):
    records = []
    for row in rows:
        record = {"observation_id": row["observation_id"], "family_id": row["family_id"],
                  "listing_id": row["listing_id"], "variant_id": row["variant_id"],
                  "predictors": row["predictors"], "target": row["target"]}
        try:
            record.update(prediction(booster, bundle, row["predictors"], explain))
        except ModelContractError as error:
            record.update(domain_membership="unsupported", rejection_reason=str(error), model_id=MODEL_ID)
        records.append(record)
    return records


def calibrate(rows, booster, bundle):
    selected = representatives(rows)
    records = predict_rows(selected, booster, bundle)
    calibration = {"coverage": 0.9, "selection_seed": 1729, "retailers": {},
                   "representative_observation_ids": [r["observation_id"] for r in selected],
                   "selection_rule": working_contract()["representative_selection"], "weighted_scores": False,
                   "rejections": [r for r in records if r["domain_membership"] == "unsupported"]}
    for retailer in working_contract()["retailers"]:
        supported = [r for r in records if r["predictors"][RETAILER] == retailer and r["domain_membership"] != "unsupported"]
        scores = sorted(abs(r["target"]["log_regular_price_per_100g_gbp"] - r["log_unit_price"]) for r in supported)
        k = math.ceil((len(scores) + 1) * 0.9)
        calibration["retailers"][retailer] = {"families": len(scores), "rank": k, "sorted_scores": scores,
                                             "quantile": scores[k - 1] if k <= len(scores) else None,
                                             "status": "finite" if k <= len(scores) else "unavailable_unbounded"}
    return calibration


def add_interval(record, calibration):
    spec = calibration["retailers"][record["predictors"][RETAILER]]
    q = spec["quantile"]
    record["interval_status"] = spec["status"]
    if q is not None:
        try:
            lo, hi = math.exp(record["log_unit_price"] - q), math.exp(record["log_unit_price"] + q)
        except OverflowError:
            record["interval_status"] = "unavailable_unbounded"
            record["interval_failure"] = "finite log interval overflows representable currency units"
            return record
        record["interval_unit_gbp_per_100g"] = [lo, hi]
        record["interval_pack_gbp"] = [v * record["predictors"][MASS] / 100 for v in (lo, hi)]
    return record


def metrics(records, listing_weighted=False):
    if not records:
        return None
    weights = [1.0] * len(records) if listing_weighted else family_weights(records)
    actual = [r["target"]["regular_price_per_100g_gbp"] for r in records]
    errors = [r["unit_price_gbp_per_100g"] - y for r, y in zip(records, actual)]
    total = sum(weights)
    pairs = sorted((abs(e) / y * 100, w) for e, y, w in zip(errors, actual, weights))
    cumulative, mdape = 0.0, None
    for value, w in pairs:
        cumulative += w
        if cumulative >= total / 2:
            mdape = value
            break
    return {"observations": len(records), "families": len({r["family_id"] for r in records}),
            "mae_gbp_per_100g": sum(abs(e) * w for e, w in zip(errors, weights)) / total,
            "mae_gbp_per_pack": sum(abs(e) * w * r["predictors"][MASS] / 100 for e, w, r in zip(errors, weights, records)) / total,
            "weighted_median_ape_percent": mdape,
            "signed_bias_gbp_per_100g": sum(e * w for e, w in zip(errors, weights)) / total,
            "signed_bias_gbp_per_pack": sum(e * w * r["predictors"][MASS] / 100 for e, w, r in zip(errors, weights, records)) / total,
            "sparse_stratum": len({r["family_id"] for r in records}) < 30}


def evaluate(rows, booster, bundle, calibration):
    records = predict_rows(rows, booster, bundle, explain=True)
    supported = [add_interval(r, calibration) for r in records if r["domain_membership"] != "unsupported"]
    breakdowns = {}
    getters = {"optional_unknown_claims": lambda r: str(sum(r["predictors"].get(n) == "unknown" for n in CLAIMS)),
               "cocoa_basis": lambda r: r["predictors"][BASIS],
               "retailer": lambda r: r["predictors"][RETAILER], "type": lambda r: r["predictors"][TYPE],
               "brand": lambda r: r["predictors"][BRAND],
               "size": lambda r: "up_to_50g" if r["predictors"][MASS] <= 50 else "51_to_100g" if r["predictors"][MASS] <= 100 else "over_100g",
               "missingness": lambda r: "cocoa_missing" if r["predictors"].get(COCOA) is None else "cocoa_observed"}
    for name, getter in getters.items():
        groups = defaultdict(list)
        for r in supported:
            groups[getter(r)].append(r)
        breakdowns[name] = {key: metrics(members) for key, members in sorted(groups.items())}
    representative_ids = {r["observation_id"] for r in representatives(rows)}
    intervals = {}
    for retailer in working_contract()["retailers"]:
        reps = [r for r in supported if r["observation_id"] in representative_ids and r["predictors"][RETAILER] == retailer]
        finite = [r for r in reps if r["interval_status"] == "finite"]
        n = len(finite)
        successes = sum(r["interval_unit_gbp_per_100g"][0] <= r["target"]["regular_price_per_100g_gbp"] <= r["interval_unit_gbp_per_100g"][1] for r in finite)
        coverage = successes / n if n else None
        wilson = None
        if n:
            z = 1.959963984540054
            center = (coverage + z * z / (2 * n)) / (1 + z * z / n)
            half = z * math.sqrt(coverage * (1 - coverage) / n + z * z / (4 * n * n)) / (1 + z * z / n)
            wilson = [center - half, center + half]
        intervals[retailer] = {"supported_representative_families": len(reps), "finite_intervals": n,
                               "coverage": coverage, "coverage_wilson_95": wilson,
                               "median_relative_width": median((r["interval_unit_gbp_per_100g"][1] - r["interval_unit_gbp_per_100g"][0]) / r["unit_price_gbp_per_100g"] for r in finite) if n else None}
    attribution_groups = {"size": [MASS], "type": [TYPE], "recipe_inclusion": [RECIPE, INCLUSION],
                          "brand": [BRAND], "retailer": [RETAILER], "cocoa": [BASIS, COCOA, COCOA + "__missing"],
                          "claims": list(CLAIMS)}
    explained = [r for r in supported if r["explanation_status"] == "verified"]
    importance = {}
    if explained:
        weights = family_weights(explained)
        for group, names in attribution_groups.items():
            importance[group] = sum(abs(sum(r["shap_log_values"].get(n, 0.0) for n in names)) * w
                                    for r, w in zip(explained, weights)) / sum(weights)
    return {"global_shap": {"groups": attribution_groups, "family_weighted_mean_absolute_group_log_contribution": importance,
                            "verified_observations": len(explained), "rule": "sum_signed_within_row_then_absolute_then_family_weighted_mean"},
            "family_weighted": metrics(supported), "listing_weighted_sensitivity": metrics(supported, True),
            "breakdowns": breakdowns, "interval_assessment": intervals,
            "test_representative_ids": sorted(representative_ids),
            "supported_observations": len(supported), "eligible_observations": len(rows),
            "release_ready": False, "baseline_relative_gate": "pending_comparators",
            "champion_selection": "pending_comparators"}, records
