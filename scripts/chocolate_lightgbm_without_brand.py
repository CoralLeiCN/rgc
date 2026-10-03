"""Independent experimental LightGBM without brand; never infer source evidence.

Native LightGBM TreeSHAP uses raw log output and stored path counts. A working
contract is an explicit local research configuration, not a published migration.
"""

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
from statistics import median

from chocolate_model import (
    ModelContractError,
    validate_candidates,
    validate_target_policy,
)

MODEL_ID = "lightgbm_without_brand"
VERSIONS = {"numpy": "2.2.6", "scipy": "1.15.3", "lightgbm": "4.6.0", "pyarrow": "21.0.0"}
SEED = 1729
WEIGHT = "quantity.total_edible_weight_g"
TYPE = "composition.chocolate_type"
RETAILER = "identity.retailer"
RECIPE = "composition.recipe_class"
BASIS = "composition.cocoa_percentage_basis"
COCOA = "composition.cocoa_percentage"
CORE = [WEIGHT, TYPE, RECIPE, "composition.nuts_presence", RETAILER]
OPTIONAL = [BASIS, COCOA, "dietary.vegan_claim", "certifications.fairtrade_claim",
            "certifications.organic_claim"]
ADMISSIBLE = set(CORE + OPTIONAL)
PARAMETERS = {"objective": "regression", "metric": "None", "learning_rate": 0.03,
              "num_leaves": 15, "max_depth": 4, "min_data_in_leaf": 20, "lambda_l2": 1,
              "verbosity": -1, "num_threads": 1, "deterministic": True,
              "force_col_wise": True, "seed": SEED, "feature_pre_filter": False}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def working_contract(design):
    """Prepare a local model configuration; absent required fields block training."""
    validate_target_policy(design["target"])
    return deepcopy({"format": "chocolate-lightgbm-working-1", "model_id": MODEL_ID,
            "published": False, "source_design_version": design["model_design_version"],
            "target": deepcopy(design["target"]), "feature_policy_version": "chocolate-common-input-1-local",
            "core_features": CORE, "optional_features": OPTIONAL,
            "cohort": "uk_supermarket_standard_single_pack_chocolate_bar",
            "cohort_field": "identity.study_cohort", "pack_count_field": "quantity.pack_count",
            "allowed_retailers": ["Waitrose", "Ocado"], "split_seed": SEED,
            "calibration_seed": SEED, "maximum_iterations": 2000, "patience": 50,
            "minimum_leaf_families": 5, "parameters": PARAMETERS,
            "tuning": [{}, {"num_leaves": 7, "max_depth": 3, "lambda_l2": 2}],
            "claims_values": ["present", "explicitly_absent", "unknown"],
            "cocoa_basis_values": ["whole_product", "chocolate_portion", "unknown"],
            "recipe_values": ["plain", "inclusion", "filled"],
            "price_window": None,
            "publication_requirement": "Aligned dataset and portable contracts plus reviewed regenerated Gold are required."})


def validate_contract(contract):
    if (contract.get("format") != "chocolate-lightgbm-working-1"
            or contract.get("model_id") != MODEL_ID):
        raise ModelContractError("unsupported LightGBM working contract")
    validate_target_policy(contract.get("target"))
    if contract.get("core_features") != CORE or contract.get("optional_features") != OPTIONAL:
        raise ModelContractError("unsupported common feature policy; identifiers and prices are excluded")
    for key in ("split_seed", "calibration_seed"):
        if type(contract.get(key)) is not int or not 0 <= contract[key] < 2**32:
            raise ModelContractError("invalid " + key)
    if (type(contract.get("maximum_iterations")) is not int
            or not 1 <= contract["maximum_iterations"] <= 2000
            or type(contract.get("patience")) is not int or contract["patience"] < 1
            or type(contract.get("minimum_leaf_families")) is not int
            or contract["minimum_leaf_families"] < 2):
        raise ModelContractError("invalid bounded tuning or leaf support policy")
    if contract.get("parameters") != PARAMETERS:
        raise ModelContractError("unsupported starting parameters")
    if contract.get("tuning") != [{}, {"num_leaves": 7, "max_depth": 3, "lambda_l2": 2}]:
        raise ModelContractError("unsupported bounded search")
    template = working_contract({"target": contract["target"], "model_design_version": contract.get("source_design_version")})
    for key in ("cohort", "cohort_field", "pack_count_field", "allowed_retailers", "claims_values",
                "recipe_values", "cocoa_basis_values", "feature_policy_version"):
        if contract.get(key) != template[key]:
            raise ModelContractError("unsupported domain policy: " + key)


def runtime():
    import importlib

    modules = {name: importlib.import_module(name) for name in VERSIONS}
    for name, version in VERSIONS.items():
        if modules[name].__version__ != version:
            raise ModelContractError("Use pinned " + name + "==" + version)
    return modules["numpy"], modules["lightgbm"]


def family_weights(rows):
    counts = Counter(row["family_id"] for row in rows)
    return [1 / counts[row["family_id"]] for row in rows]


def experiment(rows, identity, contract):
    """Hash ordered families with seed; no brand quotas or outcome dependence.

    Sort by SHA256(seed + LF + family ID), then allocate rounded 20% calibration,
    rounded 20% testing, and the remainder fitting. This works across runtimes.
    """
    validate_contract(contract)
    families = sorted({row["family_id"] for row in rows}, key=lambda family:
                      (hashlib.sha256((str(contract["split_seed"]) + "\n" + family).encode()).hexdigest(), family))
    n = len(families)
    count = int(n * 0.2 + 0.5)
    assignments = {family: ("calibration" if i < count else "testing" if i < count * 2 else "fitting")
                   for i, family in enumerate(families)}
    manifest = {"format": "chocolate-family-experiment-1", "identity": identity,
                "seed": contract["split_seed"], "algorithm": "sha256_seed_LF_family_sorted_round_half_up_20_20_remainder",
                "fractions": {"fitting": 0.6, "calibration": 0.2, "testing": 0.2},
                "brand_quotas": False, "family_assignments": dict(sorted(assignments.items())),
                "row_partitions": {r["observation_id"]: assignments[r["family_id"]]
                                   for r in sorted(rows, key=lambda r: r["observation_id"])},
                "selected_rows_sha256": digest(sorted(rows, key=lambda r: r["observation_id"])),
                "feature_policy_sha256": digest(contract), "price_window": contract["price_window"],
                "eligibility": "Silver reviewed model_eligible, verified regular consumer price and declared cohort",
                "weighting": "1/n_f_recomputed_within_each_partition_fold_and_stratum"}
    return manifest


def check_rows(rows, contract):
    """Validate identity/targets and required shared fields without inventing them."""
    validate_contract(contract)
    # Reuse identity/target gates with the one required numeric predictor. Optional
    # unknowns belong to this explicit working policy, not the old OLS encoder.
    validate_candidates(rows, {"target": contract["target"], "predictors": {
        WEIGHT: {"type": "numeric", "required": True, "missing_policy": "reject", "minimum": 0.01}}})
    if len({r["listing_id"] for r in rows}) != len(rows):
        raise ModelContractError("one reviewed observation per seller listing is required")
    for row in rows:
        values = row["predictors"]
        if row["source_role"] != "retail" or row["comparable_group"] != "bar":
            raise ModelContractError("outside standard supermarket bar population")
        if values.get(contract["cohort_field"]) != contract["cohort"] or values.get(contract["pack_count_field"]) != 1:
            raise ModelContractError("reviewed single-pack cohort evidence is required")
        brand = values.get("identity.brand")
        if not isinstance(brand, str) or not brand.strip() or brand.casefold() in {"unknown", "unresolved"}:
            raise ModelContractError("reviewed brand identity required for diagnostics")
        if values.get(RETAILER) not in contract["allowed_retailers"]:
            raise ModelContractError("unsupported retailer; Tesco requires separate evidence and validation")
        if values.get(TYPE) not in {"milk", "dark", "white"} or values.get(RECIPE) not in contract["recipe_values"]:
            raise ModelContractError("reviewed chocolate type and recipe are required")
        for name in OPTIONAL + ["composition.nuts_presence"]:
            if name not in values:
                raise ModelContractError("shared feature field absent: " + name)
            value = values[name]
            if name == COCOA:
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100):
                    raise ModelContractError("invalid optional numeric cocoa")
                if value is not None and values.get(BASIS) == "unknown":
                    raise ModelContractError("numeric cocoa requires reviewed percentage basis")
            elif name == BASIS:
                if value not in contract["cocoa_basis_values"]:
                    raise ModelContractError("unsupported cocoa percentage basis")
            elif value not in contract["claims_values"]:
                raise ModelContractError("optional evidence must retain present/explicitly_absent/unknown")


def fit_preprocessing(rows, features, contract):
    check_rows(rows, contract)
    if not rows or set(features) - ADMISSIBLE or not set(CORE) <= set(features):
        raise ModelContractError("invalid fitting rows or feature policy")
    result = {"features": list(features), "categories": {}, "ranges": {},
              "fitting_observation_ids": sorted(r["observation_id"] for r in rows),
              "combinations": sorted({(r["predictors"][RETAILER], r["predictors"][TYPE],
                                       r["predictors"][RECIPE]) for r in rows})}
    for name in features:
        values = [r["predictors"][name] for r in rows]
        if name in {WEIGHT, COCOA}:
            known = [v for v in values if v is not None]
            if name == COCOA and not known:
                raise ModelContractError("cocoa has no fitting evidence")
            result["ranges"][name] = [min(known), max(known)]
            if name == WEIGHT and min(known) == max(known):
                raise ModelContractError("required size term has no fitting variation")
        else:
            result["categories"][name] = sorted(set(values))
    result["cocoa_medians"] = {}
    if COCOA in features:
        result["cocoa_median"] = median(r["predictors"][COCOA] for r in rows if r["predictors"][COCOA] is not None)
        groups = defaultdict(list)
        for row in rows:
            v = row["predictors"]
            if v[COCOA] is not None:
                groups[json.dumps([v[TYPE], v[BASIS]])].append(v[COCOA])
        result["cocoa_medians"] = {k: median(v) for k, v in sorted(groups.items())}
    result["columns"] = list(features) + ([COCOA + ".missing"] if COCOA in features else [])
    result["categorical_indices"] = [i for i, name in enumerate(result["columns"]) if name in result["categories"]]
    return result


def transform(rows, preprocessing):
    import numpy as np

    matrix = []
    for row in rows:
        v = row["predictors"]
        if tuple([v[RETAILER], v[TYPE], v[RECIPE]]) not in {tuple(x) for x in preprocessing["combinations"]}:
            raise ModelContractError("unsupported retailer/type/recipe combination")
        encoded = []
        for name in preprocessing["features"]:
            value = v[name]
            if name in preprocessing["categories"]:
                levels = preprocessing["categories"][name]
                if value not in levels:
                    raise ModelContractError("unseen categorical level: " + name)
                encoded.append(levels.index(value))
            else:
                if value is None and name == COCOA:
                    value = preprocessing["cocoa_medians"].get(json.dumps([v[TYPE], v[BASIS]]), preprocessing["cocoa_median"])
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ModelContractError("invalid numeric input: " + name)
                low, high = preprocessing["ranges"][name]
                if not low <= value <= high:
                    raise ModelContractError("outside fitting range: " + name)
                encoded.append(math.log(value) if name == WEIGHT else value)
        if COCOA in preprocessing["features"]:
            encoded.append(float(v[COCOA] is None))
        matrix.append(encoded)
    return np.asarray(matrix, dtype=float).reshape(len(rows), len(preprocessing["columns"]))


def admissible_features(rows, features, contract):
    """Inspect known-brand linear identification without fitting a comparator."""
    import numpy as np

    selected, dropped = list(CORE), {}

    def rank(names):
        pre = fit_preprocessing(rows, names, contract)
        x = transform(rows, pre)
        columns = [np.ones(len(rows))]
        for i, name in enumerate(pre["columns"]):
            if i in pre["categorical_indices"]:
                columns.extend((x[:, i] == j).astype(float) for j in range(1, len(pre["categories"][name])))
            elif np.ptp(x[:, i]) > 0:
                columns.append(x[:, i])
        brands = sorted({r["predictors"]["identity.brand"] for r in rows})
        columns.extend(np.asarray([r["predictors"]["identity.brand"] == b for r in rows], dtype=float) for b in brands[1:])
        matrix = np.column_stack(columns)
        return np.linalg.matrix_rank(matrix) == matrix.shape[1]

    if not rank(selected):
        raise ModelContractError("required common core aliases known-brand design")
    for name in features:
        if name in selected:
            continue
        proposed = selected + ([BASIS, COCOA] if name == BASIS else [name])
        proposed = list(dict.fromkeys(proposed))
        if name == COCOA and BASIS not in selected:
            continue
        try:
            identified = rank(proposed)
        except ModelContractError:
            identified = False
        if identified:
            selected = proposed
        else:
            dropped[name] = "no_fitting_evidence_or_alias_in_known_brand_identification"
    return selected, dropped


def weighted_metrics(records, listing=False):
    if not records:
        return None
    weights = [1.0] * len(records) if listing else family_weights(records)
    total = math.fsum(weights)
    counts = Counter(r["family_id"] for r in records)
    median_weights = [Fraction(1) if listing else Fraction(1, counts[r["family_id"]]) for r in records]
    pairs = sorted((abs(r["predicted_unit"] / r["observed_unit"] - 1) * 100, w)
                   for r, w in zip(records, median_weights))
    accumulated = Fraction(0)
    midpoint = sum(median_weights) / 2
    for percentage, weight in pairs:
        accumulated += weight
        if accumulated >= midpoint:
            break
    return {"rows": len(records), "families": len({r["family_id"] for r in records}),
            "MAE_GBP_per_100g": math.fsum(w * abs(r["predicted_unit"] - r["observed_unit"]) for r, w in zip(records, weights)) / total,
            "MAE_GBP_per_pack": math.fsum(w * abs(r["predicted_unit"] - r["observed_unit"]) * r["weight_g"] / 100 for r, w in zip(records, weights)) / total,
            "weighted_median_absolute_percentage_error": percentage,
            "signed_bias_GBP_per_100g": math.fsum(w * (r["predicted_unit"] - r["observed_unit"]) for r, w in zip(records, weights)) / total,
            "signed_bias_GBP_per_pack": math.fsum(w * (r["predicted_unit"] - r["observed_unit"]) * r["weight_g"] / 100 for r, w in zip(records, weights)) / total}


def predict(rows, model, *, explanations=True):
    np, lgb = runtime()
    check_rows(rows, model["contract"])
    booster = lgb.Booster(model_str=model["booster"])
    if booster.current_iteration() != model["tree_count"]:
        raise ModelContractError("booster tree count differs from frozen model")
    if digest(model["booster"]) != model["booster_sha256"]:
        raise ModelContractError("booster integrity mismatch")
    results = []
    for row in rows:
        record = {"observation_id": row["observation_id"], "family_id": row["family_id"],
                  "listing_id": row["listing_id"], "in_domain": False, "model_id": MODEL_ID,
                  "retailer": row["predictors"][RETAILER], "type": row["predictors"][TYPE],
                  "brand": row["predictors"]["identity.brand"], "weight_g": row["predictors"][WEIGHT],
                  "missingness": "cocoa_unknown" if row["predictors"][COCOA] is None else "cocoa_known"}
        record["brand_represented_in_fitting"] = record["brand"] in model["fitting_brands"]
        try:
            x = transform([row], model["preprocessing"])
        except ModelContractError as error:
            results.append({**record, "reason": str(error)})
            continue
        raw = float(booster.predict(x, raw_score=True, num_iteration=model["tree_count"], num_threads=1)[0])
        if not math.isfinite(raw) or raw > 700 or raw < -700:
            raise ModelContractError("nonfinite or unrepresentable prediction")
        unit = math.exp(raw)
        leaf = np.asarray(booster.predict(x, pred_leaf=True, num_iteration=model["tree_count"], num_threads=1)).reshape(-1)
        minimum = min(model["leaf_support"][str(i)][str(int(value))] for i, value in enumerate(leaf))
        record.update(in_domain=True, predicted_log=raw, predicted_unit=unit,
                      predicted_pack=unit * record["weight_g"] / 100,
                      observed_unit=row["target"]["regular_price_per_100g_gbp"],
                      minimum_leaf_families=minimum,
                      support_status="experimental_sparse_leaf" if minimum < model["contract"]["minimum_leaf_families"] else "experimental",
                      interval_scope="representative_family_in_retailer_snapshot; no unseen-brand or future-price claim")
        q = model.get("calibration", {}).get(record["retailer"], {}).get("quantile_log")
        available = (q is not None and minimum >= model["contract"]["minimum_leaf_families"]
                     and record["brand_represented_in_fitting"] and -700 <= raw - q <= raw + q <= 700)
        record["interval_unit"] = [math.exp(raw - q), math.exp(raw + q)] if available else None
        record["interval_status"] = "finite_experimental" if available else "unavailable_unbounded_or_unsupported"
        record["interval_pack"] = [v * record["weight_g"] / 100 for v in record["interval_unit"]] if record["interval_unit"] else None
        explanation = {"available": False, "method": "native_exact_tree_path_dependent_raw_TreeSHAP",
                       "implementation": "lightgbm==4.6.0 Booster.predict(pred_contrib=True)",
                       "units": "log_GBP_per_100g", "reference": "stored_model_path_counts",
                       "tree_count": model["tree_count"], "approximate": False, "background": None}
        if explanations:
            try:
                values = np.asarray(booster.predict(x, pred_contrib=True, num_iteration=model["tree_count"], num_threads=1))[0]
                rebuilt = float(values.sum())
                if not np.isfinite(values).all() or not math.isclose(rebuilt, raw, rel_tol=1e-5, abs_tol=1e-6):
                    raise ModelContractError("TreeSHAP reconstruction failed")
                contributions = dict(zip(model["preprocessing"]["columns"], map(float, values[:-1])))
                groups = defaultdict(float)
                for name, value in contributions.items():
                    groups["cocoa" if name in {COCOA, COCOA + ".missing", BASIS} else name] += value
                explanation.update(available=True, model_explanation_reference=float(values[-1]),
                                   contributions=contributions, groups=dict(groups), reconstruction_log=rebuilt,
                                   reconstruction_error=rebuilt - raw,
                                   multiplicative_factors={k: math.exp(v) for k, v in groups.items()})
            except (ValueError, TypeError, OverflowError, lgb.basic.LightGBMError) as error:
                explanation["reason"] = str(error)
        record["explanation"] = explanation
        record["narrative"] = f"Experimental {record['retailer']} benchmark: GBP {unit:.2f} per 100 g; GBP {record['predicted_pack']:.2f} per pack."
        if explanation["available"]:
            largest = max(explanation["groups"], key=lambda k: abs(explanation["groups"][k]))
            record["narrative"] += f" Largest model attribution: {largest}, {explanation['groups'][largest]:+.3f} log units relative to the model explanation reference."
        record["narrative"] += " Support is experimental; attributions are associations."
        results.append(record)
    return results


def fit(rows, contract):
    """Tune only inside fitting families, then refit once with a fixed tree count."""
    np, lgb = runtime()
    check_rows(rows, contract)
    families = sorted({r["family_id"] for r in rows}, key=lambda f: (digest([contract["split_seed"], "fold", f]), f))
    if len(families) < 10:
        raise ModelContractError("at least ten fitting families required for grouped validation")
    folds = {f: i % 3 for i, f in enumerate(families)}
    search = []
    for requested in (CORE, CORE + OPTIONAL):
        for update in contract["tuning"]:
            scores, iterations, fold_reports = [], [], []
            for fold in range(3):
                training = [r for r in rows if folds[r["family_id"]] != fold]
                validation = [r for r in rows if folds[r["family_id"]] == fold]
                features, omitted = admissible_features(training, requested, contract)
                pre = fit_preprocessing(training, features, contract)
                supported = []
                for row in validation:
                    try:
                        transform([row], pre)
                        supported.append(row)
                    except ModelContractError:
                        pass
                # Candidates must cover identical fitting-validation observations.
                # An enriched feature set with reduced support cannot win by dropping
                # difficult rows. The core must also cover every validation row.
                if len(supported) != len(validation):
                    fold_reports.append({"fold": fold, "unavailable": "validation_domain_incomplete",
                                         "supported": len(supported), "total": len(validation)})
                    continue
                train_set = lgb.Dataset(transform(training, pre), label=[r["target"]["log_regular_price_per_100g_gbp"] for r in training],
                                        weight=family_weights(training), categorical_feature=pre["categorical_indices"],
                                        feature_name=["feature_" + str(i) for i in range(len(pre["columns"]))])
                valid_set = lgb.Dataset(transform(supported, pre), label=[r["target"]["log_regular_price_per_100g_gbp"] for r in supported],
                                        weight=family_weights(supported), reference=train_set)

                def metric(predictions, dataset):
                    score = np.average(np.abs(np.exp(predictions) - np.exp(dataset.get_label())), weights=dataset.get_weight())
                    return "family_weighted_unit_MAE", float(score), False

                booster = lgb.train({**PARAMETERS, **update}, train_set, num_boost_round=contract["maximum_iterations"],
                                    valid_sets=[valid_set], feval=metric,
                                    callbacks=[lgb.early_stopping(contract["patience"], verbose=False)])
                score = float(booster.best_score["valid_0"]["family_weighted_unit_MAE"])
                scores.append((score, len({r["family_id"] for r in supported})))
                iterations.append(booster.best_iteration)
                leaves = np.asarray(booster.predict(transform(training, pre), pred_leaf=True,
                                                    num_iteration=booster.best_iteration, num_threads=1)).reshape(len(training), -1)
                leaf_counts = [len({r["family_id"] for r, value in zip(training, leaves[:, i]) if value == leaf})
                               for i in range(leaves.shape[1]) for leaf in set(leaves[:, i])]
                fold_reports.append({"fold": fold, "MAE_GBP_per_100g": score, "tree_count": booster.best_iteration,
                                     "minimum_independent_leaf_families": min(leaf_counts),
                                     "leaves_below_family_support": sum(n < contract["minimum_leaf_families"] for n in leaf_counts),
                                     "preprocessing": pre, "omitted": omitted,
                                     "training_weights": dict(zip([r["observation_id"] for r in training], family_weights(training))),
                                     "validation_weights": dict(zip([r["observation_id"] for r in supported], family_weights(supported)))})
            search.append({"requested_features": list(requested), "parameters": {**PARAMETERS, **update},
                           "score": sum(s * n for s, n in scores) / sum(n for _, n in scores) if len(scores) == 3 else None,
                           "tree_count": max(1, int(median(iterations))) if len(iterations) == 3 else None,
                           "folds": fold_reports})
    available = [c for c in search if c["score"] is not None]
    if not available:
        raise ModelContractError("no tuning candidate has complete grouped validation support")
    winner = min(available, key=lambda c: (c["score"], len(c["requested_features"]), c["tree_count"]))
    # Only terms identified in every inner fold may enter the common final fit.
    common = set.intersection(*(set(f["preprocessing"]["features"]) for f in winner["folds"]))
    features, omitted = admissible_features(rows, [n for n in winner["requested_features"] if n in common], contract)
    pre = fit_preprocessing(rows, features, contract)
    x = transform(rows, pre)
    dataset = lgb.Dataset(x, label=[r["target"]["log_regular_price_per_100g_gbp"] for r in rows], weight=family_weights(rows),
                          categorical_feature=pre["categorical_indices"],
                          feature_name=["feature_" + str(i) for i in range(len(pre["columns"]))])
    booster = lgb.train(winner["parameters"], dataset, num_boost_round=winner["tree_count"])
    leaves = np.asarray(booster.predict(x, pred_leaf=True, num_threads=1)).reshape(len(rows), -1)
    support = {}
    for i in range(leaves.shape[1]):
        support[str(i)] = {str(int(leaf)): len({r["family_id"] for r, value in zip(rows, leaves[:, i]) if value == leaf})
                           for leaf in sorted(set(leaves[:, i]))}
    text = booster.model_to_string(num_iteration=booster.current_iteration())
    return {"model_id": MODEL_ID, "estimator": "lightgbm_squared_error_log_price", "contract": contract,
            "estimate_type": "geometric_unit_price_benchmark", "target": "log_regular_GBP_per_100g",
            "retransformation": "exp_raw_log_prediction_without_mean_correction",
            "fitting_brands": sorted({r["predictors"]["identity.brand"] for r in rows}),
            "preprocessing": pre, "selected_parameters": winner["parameters"], "tree_count": booster.current_iteration(),
            "booster": text, "booster_sha256": digest(text), "leaf_support": support,
            "grouped_validation": search, "fold_assignments": folds, "omitted_features": omitted,
            "known_brand_identification": "rank_check_in_every_fitting_fold; no comparator fitted",
            "versions": VERSIONS, "fitting_rows_sha256": digest(rows), "fitting_weights": family_weights(rows),
            "calibration": {}, "release_ready": False, "champion_selection": "pending_comparators"}


def representatives(records, seed):
    groups = defaultdict(list)
    for record in records:
        # Select from the entire retailer/family identity list before inspecting
        # domain membership. Reject an unsupported selected row without replacement.
        groups[(record["retailer"], record["family_id"])].append(record)
    selected = []
    for key, members in sorted(groups.items()):
        ordered = sorted(members, key=lambda r: r["observation_id"])
        generator = random.Random(digest([seed, *key]))
        selected.append(ordered[generator.randrange(len(ordered))])
    return selected


def calibrate(records, contract):
    result = {}
    for retailer in contract["allowed_retailers"]:
        chosen = [r for r in representatives(records, contract["calibration_seed"]) if r["retailer"] == retailer]
        supported = [r for r in chosen if r["in_domain"] and r["minimum_leaf_families"] >= contract["minimum_leaf_families"]
                     and r.get("brand_represented_in_fitting", False)]
        residuals = sorted(abs(math.log(r["observed_unit"]) - r["predicted_log"]) for r in supported)
        n = len(residuals)
        k = math.ceil((n + 1) * 0.9)
        result[retailer] = {"level": 0.9, "seed": contract["calibration_seed"],
                            "selection": "sorted_identity_uniform_random_per_retailer_family_no_replacement_on_domain_failure",
                            "selected_observation_ids": [r["observation_id"] for r in chosen],
                            "used_observation_ids": [r["observation_id"] for r in supported],
                            "residuals_log": residuals, "families": n, "order_statistic": k,
                            "quantile_log": residuals[k - 1] if k <= n else None,
                            "status": "finite_experimental" if k <= n else "unavailable_unbounded"}
    return result


def evaluate(records, contract):
    supported = [r for r in records if r["in_domain"]]
    result = {"domain_rows": len(records), "supported_rows": len(supported),
              "family_weighted": weighted_metrics(supported), "listing_weighted": weighted_metrics(supported, True),
              "breakdowns": {}, "intervals": {}, "release_ready": False,
              "baseline_relative_gate": "pending_comparator_results", "champion_selection": "pending_comparator_results"}
    for name in ("retailer", "type", "brand", "missingness", "size"):
        groups = defaultdict(list)
        for r in records:
            key = str(r[name]) if name != "size" else ("under_100g" if r["weight_g"] < 100 else "100g_to_200g" if r["weight_g"] <= 200 else "over_200g")
            groups[key].append(r)
        result["breakdowns"][name] = {k: {"domain_rows": len(v), "domain_families": len({r["family_id"] for r in v}),
                                          "supported_rows": sum(r["in_domain"] for r in v),
                                          "metrics": weighted_metrics([r for r in v if r["in_domain"]]),
                                          "listing_weighted": weighted_metrics([r for r in v if r["in_domain"]], True),
                                          "support_status": "sparse" if len({r["family_id"] for r in v if r["in_domain"]}) < 10 else "experimental"}
                                      for k, v in sorted(groups.items())}
    for retailer in contract["allowed_retailers"]:
        chosen = [r for r in representatives(records, contract["calibration_seed"]) if r["retailer"] == retailer]
        finite = [r for r in chosen if r["in_domain"] and r["interval_unit"] is not None]
        n = len(finite)
        hits = sum(r["interval_unit"][0] <= r["observed_unit"] <= r["interval_unit"][1] for r in finite)
        coverage = hits / n if n else None
        z = 1.6448536269514722
        lower = ((coverage + z*z/(2*n) - z*math.sqrt(coverage*(1-coverage)/n + z*z/(4*n*n))) / (1+z*z/n)) if n else None
        result["intervals"][retailer] = {"selected_families": len(chosen), "finite_intervals": n,
                                          "coverage": coverage, "one_sided_95_wilson_lower": lower,
                                          "median_relative_width": median((r["interval_unit"][1] - r["interval_unit"][0]) / r["predicted_unit"] for r in finite) if n else None,
                                          "selected_observation_ids": [r["observation_id"] for r in chosen]}
    groups = defaultdict(list)
    for r in supported:
        for name, value in r.get("explanation", {}).get("groups", {}).items():
            groups[name].append((abs(value), r))
    result["global_attribution"] = {name: math.fsum(value * weight for (value, _), weight in zip(values, family_weights([r for _, r in values]))) / math.fsum(family_weights([r for _, r in values])) for name, values in groups.items()}
    result["global_attribution_by_retailer"] = {}
    for retailer in contract["allowed_retailers"]:
        result["global_attribution_by_retailer"][retailer] = {}
        for name, values in groups.items():
            selected = [(v, r) for v, r in values if r["retailer"] == retailer]
            if selected:
                weights = family_weights([r for _, r in selected])
                result["global_attribution_by_retailer"][retailer][name] = math.fsum(v * w for (v, _), w in zip(selected, weights)) / math.fsum(weights)
    return result
