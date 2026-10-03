"""Refit an experimental LightGBM without brand from verified inferred Gold.

This explicit research adapter selects usable candidates without rewriting their
upstream eligibility. It uses the pinned current displayed-price study target.
"""

import argparse
import hashlib
import json
import math
import platform
from collections import Counter
from copy import deepcopy
from pathlib import Path
from statistics import median

from chocolate_current_price import LIMITATIONS, current_price_targets
from chocolate_gold import json_bytes, read_json, read_managed, verified_gold_storage
from chocolate_gold_inferred import verified_gold_inferred
from chocolate_gold_training import (
    POLICY_VERSION,
    training_rows,
    verified_training_gold,
)
from chocolate_lightgbm_without_brand import (
    MODEL_ID,
    PARAMETERS,
    SEED,
    VERSIONS,
    digest,
    family_weights,
    runtime,
    weighted_metrics,
)
from chocolate_model import ModelContractError
from dataset_contracts import CURRENT_PRICE_REFERENCE, SCHEMA_CACHE, resolve_contracts
from train_chocolate_model import checksum, rows, validate_price_targets, write_run

ROOT = Path(__file__).resolve().parents[1]
WEIGHT = "quantity.total_edible_weight_g"
RETAILER = "identity.retailer"
TYPE = "composition.chocolate_type"
CORE = [WEIGHT, RETAILER, TYPE]
FEATURES = CORE + ["composition.nuts_presence", "dietary.vegan_claim",
                   "certifications.fairtrade_claim", "certifications.organic_claim"]
IMPLEMENTATION = ["scripts/refit_chocolate_lightgbm_inferred.py", "scripts/chocolate_gold_inferred.py",
                  "scripts/chocolate_gold.py", "scripts/chocolate_gold_population.py", "scripts/chocolate_gold_training.py", "scripts/chocolate_current_price.py",
                  "scripts/chocolate_lightgbm_without_brand.py", "scripts/train_chocolate_model.py",
                  "pyproject.toml", "uv.lock"]


def prepare_rows(products, candidates, observations):
    """Join authoritative product cells and preserve source exclusions separately."""
    index = {product["listing_id"]: product for product in products}
    if len(index) != len(products):
        raise ModelContractError("inferred product listing IDs are duplicated")
    selected, exclusions = [], Counter()
    for original in training_rows(candidates):
        product = index.get(original["listing_id"])
        if product is None:
            raise ModelContractError("candidate has no inferred product")
        cells = product["attributes"]
        reasons = []
        retailer = cells[RETAILER]["value"]
        family = cells["identity.product_family_id"]["value"]
        mass = cells[WEIGHT]["value"]
        if retailer not in {"Waitrose", "Ocado"}:
            reasons.append("outside_waitrose_ocado")
        if cells["identity.product_group"]["value"] != "bar":
            reasons.append("outside_bar_group")
        if not family or cells["identity.product_family_id"]["status"] != "known":
            reasons.append("family_relationship_unresolved")
        if (type(mass) not in (int, float) or not math.isfinite(mass) or mass <= 0
                or cells[WEIGHT]["status"] != "known"):
            reasons.append("positive_edible_pack_weight_missing")
        if reasons:
            exclusions.update(reasons)
            continue
        row = deepcopy(original)
        row["family_id"] = family
        row["predictors"] = {name: cells[name]["value"] if cells[name]["status"] == "known" else None
                             for name in FEATURES}
        row["predictors"]["identity.brand"] = cells["identity.brand"]["value"]
        row["feature_evidence"] = {name: deepcopy(cells[name]) for name in FEATURES}
        row["source_model_eligible"] = original.get("source_model_eligible")
        row["source_exclusion_reasons"] = list(original.get("source_exclusion_reasons", []))
        selected.append(row)
    derived, report = current_price_targets(selected, observations)
    usable = []
    for row in derived:
        if row["target"]["current_price_per_100g_gbp"] is None:
            exclusions.update(["current_price_target_unavailable"])
        else:
            usable.append(row)
    usable.sort(key=lambda row: row["observation_id"])
    if len({row["listing_id"] for row in usable}) != len(usable):
        raise ModelContractError("one price observation per seller listing is required")
    return usable, dict(sorted(exclusions.items())), report


def partition_rows(values):
    """Reserve a family holdout with no outcome or brand dependence."""
    families = sorted({row["family_id"] for row in values}, key=lambda family:
                      (hashlib.sha256((str(SEED) + "\n" + family).encode()).hexdigest(), family))
    ntest = max(1, int(len(families) * 0.2 + 0.5))
    if len(families) - ntest < 10:
        raise ModelContractError("at least ten fitting families plus a family holdout are required")
    assignment = {family: "testing" if i < ntest else "fitting" for i, family in enumerate(families)}
    partitions = {name: [row for row in values if assignment[row["family_id"]] == name]
                  for name in ("fitting", "testing")}
    fitting = sorted(family for family in families if assignment[family] == "fitting")
    fitting.sort(key=lambda family: (digest([SEED, "fold", family]), family))
    folds = {family: i % 3 for i, family in enumerate(fitting)}
    return partitions, assignment, folds


def preprocessing(values, features):
    return {"features": list(features),
            "categories": {name: sorted({row["predictors"][name] for row in values
                                         if row["predictors"][name] is not None})
                           for name in features if name != WEIGHT},
            "weight_range_g": [min(row["predictors"][WEIGHT] for row in values),
                               max(row["predictors"][WEIGHT] for row in values)],
            "fitting_observation_ids": [row["observation_id"] for row in values],
            "missing_policy": "native_missing; unseen categories route as missing and are flagged",
            "weight_transform": "natural_log_grams"}


def transform(values, pre):
    import numpy as np

    return np.asarray([[math.log(row["predictors"][name]) if name == WEIGHT
                        else pre["categories"][name].index(row["predictors"][name])
                        if row["predictors"][name] in pre["categories"][name] else np.nan
                        for name in pre["features"]] for row in values], dtype=float).reshape(len(values), -1)


def fit(values, folds):
    np, lgb = runtime()
    search = []
    for features in (CORE, FEATURES):
        for update in ({}, {"num_leaves": 7, "max_depth": 3, "min_data_in_leaf": 5, "lambda_l2": 2},
                       {"num_leaves": 7, "max_depth": 3, "min_data_in_leaf": 10, "lambda_l2": 2}):
            reports = []
            for fold in range(3):
                train = [row for row in values if folds[row["family_id"]] != fold]
                valid = [row for row in values if folds[row["family_id"]] == fold]
                pre = preprocessing(train, features)
                training = lgb.Dataset(transform(train, pre),
                                       label=[row["target"]["log_current_price_per_100g_gbp"] for row in train],
                                       weight=family_weights(train), categorical_feature=list(range(1, len(features))),
                                       feature_name=["feature_" + str(i) for i in range(len(features))])
                validation = lgb.Dataset(transform(valid, pre),
                                         label=[row["target"]["log_current_price_per_100g_gbp"] for row in valid],
                                         weight=family_weights(valid), reference=training)

                def metric(predictions, data):
                    return "family_weighted_unit_MAE", float(np.average(
                        np.abs(np.exp(predictions) - np.exp(data.get_label())), weights=data.get_weight())), False

                booster = lgb.train({**PARAMETERS, **update}, training, num_boost_round=2000,
                                    valid_sets=[validation], feval=metric,
                                    callbacks=[lgb.early_stopping(50, verbose=False)])
                reports.append({"fold": fold, "MAE_GBP_per_100g": float(booster.best_score["valid_0"]["family_weighted_unit_MAE"]),
                                "tree_count": booster.best_iteration, "validation_families": len({r["family_id"] for r in valid}),
                                "preprocessing": pre,
                                "training_weights": dict(zip([r["observation_id"] for r in train], family_weights(train))),
                                "validation_weights": dict(zip([r["observation_id"] for r in valid], family_weights(valid)))})
            score = sum(r["MAE_GBP_per_100g"] * r["validation_families"] for r in reports) / sum(r["validation_families"] for r in reports)
            search.append({"features": features, "parameters": {**PARAMETERS, **update}, "score": score,
                           "tree_count": max(1, int(median(r["tree_count"] for r in reports))), "folds": reports})
    winner = min(search, key=lambda entry: (entry["score"], len(entry["features"]), entry["tree_count"]))
    pre = preprocessing(values, winner["features"])
    data = lgb.Dataset(transform(values, pre), label=[r["target"]["log_current_price_per_100g_gbp"] for r in values],
                       weight=family_weights(values), categorical_feature=list(range(1, len(pre["features"]))),
                       feature_name=["feature_" + str(i) for i in range(len(pre["features"]))])
    booster = lgb.train(winner["parameters"], data, num_boost_round=winner["tree_count"])
    return booster, pre, winner, search


def predict(values, booster, pre):
    np, _ = runtime()
    matrix = transform(values, pre)
    raw = booster.predict(matrix, raw_score=True, num_threads=1)
    shap = booster.predict(matrix, pred_contrib=True, num_threads=1)
    if not np.allclose(shap.sum(axis=1), raw, atol=1e-6, rtol=1e-5):
        raise ModelContractError("native TreeSHAP reconstruction failed")
    result = []
    for row, logged, contributions in zip(values, raw, shap):
        low, high = pre["weight_range_g"]
        reasons = []
        if not low <= row["predictors"][WEIGHT] <= high:
            reasons.append("outside_fitting_weight_range")
        for name, categories in pre["categories"].items():
            value = row["predictors"][name]
            if value is not None and value not in categories:
                reasons.append("unseen_category:" + name)
        observed = row["target"]["current_price_per_100g_gbp"]
        result.append({"observation_id": row["observation_id"], "listing_id": row["listing_id"], "family_id": row["family_id"],
                       "retailer": row["predictors"][RETAILER], "type": row["predictors"][TYPE],
                       "brand": row["predictors"]["identity.brand"], "weight_g": row["predictors"][WEIGHT],
                       "observed_unit": observed, "predicted_log": float(logged), "predicted_unit": math.exp(float(logged)),
                       "in_domain": not reasons, "support_reasons": reasons,
                       "explanation": {"reference_log": float(contributions[-1]),
                                       "features": dict(zip(pre["features"], map(float, contributions[:-1]))),
                                       "reconstruction_error_log": float(abs(sum(contributions) - logged)),
                                       "method": "native_lightgbm_tree_path_dependent_raw_log"},
                       "interval_unit": None, "release_ready": False})
    return result


def load_run(root):
    root = Path(root).resolve()
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("format") != "chocolate-lightgbm-inferred-run-1" or manifest.get("model_id") != MODEL_ID:
        raise ModelContractError("unsupported inferred LightGBM run")
    files = read_managed(root, manifest["managed_files"], "Model")
    model = read_json(files["model.json"])
    if (model["booster"] != files["booster.txt"].decode()
            or model["preprocessing"] != read_json(files["preprocessing.json"])
            or model["identity"] != {k: v for k, v in manifest.items() if k not in {"run_id", "managed_files"}}
            or model["experiment_sha256"] != digest(read_json(files["experiment.json"]))):
        raise ModelContractError("inferred model artifact identities disagree")
    _, lgb = runtime()
    booster = lgb.Booster(model_str=model["booster"])
    if booster.current_iteration() != model["tree_count"] or (root / "manifest.json").read_bytes() != manifest_bytes:
        raise ModelContractError("inferred model changed or tree count disagrees")
    return model, booster


def build_run(source, output):
    source, output = Path(source).resolve(), Path(output).absolute()
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ModelContractError("output must be separate from inferred Gold")
    manifest, products, training = verified_gold_inferred(source)
    _, _, source_inputs = verified_gold_storage(training)
    _, _, inputs = verified_training_gold(source)
    target_root = resolve_contracts(CURRENT_PRICE_REFERENCE, SCHEMA_CACHE, offline=True)
    target_bytes = (target_root / "model-design.json").read_bytes()
    target = read_json(target_bytes)
    values, exclusions, preparation = prepare_rows(products, rows(inputs["training-candidates.jsonl"]), rows(inputs["prices.jsonl"]))
    validate_price_targets(values, rows(inputs["prices.jsonl"]), target, require_price_eligibility=False)
    partitions, assignments, folds = partition_rows(values)
    identity = {"format": "chocolate-lightgbm-inferred-run-1", "model_id": MODEL_ID,
                "gold_inferred_dataset_version": manifest["dataset_version"],
                "gold_inferred_manifest_sha256": checksum((source / "manifest.json").read_bytes()),
                "target_contract_sha256": checksum(target_bytes), "seed": SEED,
                "implementation_sha256": {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION},
                "python_version": platform.python_version(), "platform": platform.platform(),
                "feature_policy_version": "chocolate-lightgbm-inferred-exploration-1"}
    experiment = {"identity": identity, "family_assignments": assignments, "fold_assignments": folds,
                  "selected_rows_sha256": digest(values), "partition": "80_percent_fitting_20_percent_testing_family_hash_seed_1729",
                  "calibration": "unavailable; no reserved calibration partition",
                  "selection": "bar; Waitrose/Ocado; established family; actual positive edible mass; actual positive GBP displayed price",
                  "eligibility": "all_gold_rows; numerical usability and model cohort are assessed separately",
                  "features": FEATURES, "omitted_features": {"identity.brand": "excluded_by_model_request",
                  "composition.recipe_class": "absent_shared_field", "quantity.pack_count": "mostly_missing; single_pack_status_unestablished",
                  "composition.cocoa_percentage": "percentage_basis_unestablished"},
                  "missingness": "unknown/conflict cells stay null; native missing routes; no inferred absence",
                  "weighting": "one_total_weight_per_family_recomputed_per_partition_and_fold",
                  "target": target["target"], "price_limitations": LIMITATIONS,
                  "publication": "local_unpublished_research_run", "gold_training_policy": POLICY_VERSION}
    booster, pre, winner, search = fit(partitions["fitting"], folds)
    predictions = {name: predict(part, booster, pre) for name, part in partitions.items()}
    tests = predictions["testing"]
    evaluation = {"all_test_rows": weighted_metrics(tests), "listing_weighted": weighted_metrics(tests, True),
                  "supported_test_rows": weighted_metrics([r for r in tests if r["in_domain"]]),
                  "test_rows": len(tests), "test_families": len({r["family_id"] for r in tests}),
                  "unsupported_test_rows": sum(not r["in_domain"] for r in tests),
                  "TreeSHAP_max_error_log": max(r["explanation"]["reconstruction_error_log"] for r in tests),
                  "intervals": "unavailable_no_calibration_partition", "champion_selection": "pending_comparators"}
    model = {"identity": identity, "model_id": MODEL_ID, "experiment_sha256": digest(experiment),
             "booster": booster.model_to_string(), "tree_count": booster.current_iteration(), "preprocessing": pre,
             "parameters": winner["parameters"], "target": target["target"], "versions": VERSIONS,
             "real_data_fitted": True, "calibrated": False, "release_ready": False,
             "estimate_type": "experimental_geometric_current_price_per_100g_benchmark"}
    report = {"status": "experimental_real_data_fitted", "model_id": MODEL_ID, "real_data_fitted": True,
              "calibrated": False, "release_ready": False, "counts": {"source_products": len(products),
              "training_candidates": len(rows(inputs["training-candidates.jsonl"])), "source_eligible_rows": len(rows(source_inputs["model-inputs.jsonl"])), "training_rows": len(rows(inputs["model-inputs.jsonl"])),
              "selected_rows": len(values), "selected_families": len(assignments)},
              "partitions": {name: {"rows": len(part), "families": len({r["family_id"] for r in part})} for name, part in partitions.items()},
              "selection_exclusion_counts": exclusions, "target_preparation": preparation,
              "tree_count": model["tree_count"], "selected_features": pre["features"], "evaluation": evaluation,
              "limitations": LIMITATIONS + ["All Gold rows are eligible for training; historical source decisions remain recorded as provenance. Curated attributes remain incomplete.",
              "Only established families with usable targets enter this experiment; selection bias is unresolved.",
              "Single-pack and recipe evidence are unestablished; cocoa percentage is omitted without a comparable basis.",
              "The small final family holdout cannot establish market accuracy; prediction intervals are unavailable.",
              "No held-out brand, future-price validation or comparator/champion decision is established."]}
    files = {"model.json": json_bytes(model), "booster.txt": model["booster"].encode(), "preprocessing.json": json_bytes(pre),
             "experiment.json": json_bytes(experiment), "report.json": json_bytes(report), "evaluation.json": json_bytes(evaluation),
             "tuning.json": json_bytes(search), "selected-rows.jsonl": b"".join(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b'\n' for r in values),
             "inputs/current-price-design.json": target_bytes, "inputs/gold-training-policy.json": inputs["gold-training-policy.json"],
             "inputs/current-price-reference.json": CURRENT_PRICE_REFERENCE.read_bytes(),
             "inputs/gold-inferred/manifest.json": (source / "manifest.json").read_bytes()}
    files.update({"inputs/gold-inferred/" + name: data for name, data in read_managed(source, manifest["managed_files"], "Inferred Gold").items()})
    for name, records in predictions.items():
        files["predictions/" + name + ".jsonl"] = b"".join(json.dumps(r, sort_keys=True, allow_nan=False).encode() + b'\n' for r in records)
    files["reproduce.json"] = json_bytes({"argv": ["uv", "run", "python", "scripts/refit_chocolate_lightgbm_inferred.py",
                                        "--gold-inferred-root", str(source), "--output", str(output)]})
    verified_gold_inferred(source)
    if checksum((source / "manifest.json").read_bytes()) != identity["gold_inferred_manifest_sha256"]:
        raise ModelContractError("inferred source manifest changed during fitting")
    if identity["implementation_sha256"] != {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}:
        raise ModelContractError("implementation changed during fitting")
    run_id = "model-run-" + digest({"identity": identity, "files": {k: checksum(v) for k, v in files.items()}})[:24]
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
                                        "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}})
    destination = write_run(output, run_id, files)
    load_run(destination)
    return report, destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-inferred-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/chocolate/uk/lightgbm_without_brand/inferred")
    args = parser.parse_args()
    report, destination = build_run(args.gold_inferred_root, args.output)
    print(json.dumps({"output": str(destination), **report}, indent=2))


if __name__ == "__main__":
    main()
