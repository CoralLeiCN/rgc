#!/usr/bin/env python3
"""Train exactly lightgbm_with_brand from immutable verified Parquet Gold."""

import argparse
import json
import platform
import shlex
from collections import Counter
from datetime import datetime
from pathlib import Path

from chocolate_experiment import (
    RETAILER,
    partition,
    validate_population,
    validate_working_contract,
    working_contract,
)
from chocolate_gold import (
    CONTRACTS,
    read_managed,
    reject_output_links,
    row_bytes,
    verified_gold,
)
from chocolate_lightgbm import MODEL_ID, VERSIONS, calibrate, evaluate, fit, runtime
from chocolate_model import ModelContractError, validate_target_policy
from lightgbm.basic import LightGBMError
from train_chocolate_model import (
    checksum,
    json_bytes,
    read_json,
    rows,
    validate_price_targets,
    write_run,
)

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ("scripts/train_chocolate_lightgbm.py", "scripts/chocolate_lightgbm.py",
                  "scripts/chocolate_experiment.py", "scripts/train_chocolate_model.py",
                  "scripts/chocolate_model.py", "scripts/chocolate_gold.py", "scripts/chocolate_cleanup/core.py")


def build_run(gold_root, output, contract_path, window_start, window_end, *, fixture=False):
    source, output = Path(gold_root).resolve(), Path(output).absolute()
    reject_output_links(output)
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ValueError("model output must be separate from Gold")
    raw_contract = Path(contract_path).read_bytes()
    contract = read_json(raw_contract)
    contract_hash = validate_working_contract(contract)
    start, end = (datetime.fromisoformat(t.replace("Z", "+00:00")) for t in (window_start, window_end))
    if start.tzinfo is None or end.tzinfo is None or start > end:
        raise ValueError("price window requires ordered timezone-aware source dates")
    runtime()
    storage = (source / "manifest.json").read_bytes()
    silver, silver_bytes, inputs = verified_gold(source)
    gold = read_json(storage)
    if fixture != str(silver["source_dataset_version"]).startswith("raw-fixture"):
        raise ValueError("synthetic inputs require --fixture; real evidence cannot be labeled fixture")
    design = read_json(inputs["model-design.json"])
    validate_target_policy(design["target"])
    candidates, eligible = rows(inputs["training-candidates.jsonl"]), rows(inputs["model-inputs.jsonl"])
    price_index = validate_price_targets(eligible, rows(inputs["prices.jsonl"]))
    report = {"model_id": MODEL_ID, "status": "readiness_blocked", "implementation_status": "implemented",
              "fixture": fixture, "real_data_fitted": False, "regression_fitted": False, "calibrated": False,
              "release_ready": False, "blockers": [], "counts": {"candidates": len(candidates), "eligible": len(eligible),
              "candidates_with_family_id": sum(bool(r.get("family_id")) for r in candidates)},
              "exclusion_counts": dict(sorted(Counter(reason for r in candidates for reason in r["exclusion_reasons"]).items())),
              "upstream_design_version": design["model_design_version"],
              "contract_publication_status": "working_overlay_unpublished",
              "baseline_relative_gate": "pending_comparators", "champion_selection": "pending_comparators"}
    missing_contract_fields = sorted(set(contract["required_evidence_fields"]) - set(design["predictors"]))
    if missing_contract_fields:
        report["blockers"].append("Gold contract lacks shared population/feature fields: " + ", ".join(missing_contract_fields))
    if read_json(inputs["quality-report.json"]).get("status") != "complete_snapshot":
        report["blockers"].append("incomplete Silver source snapshot")
    if not eligible:
        report["blockers"].append("zero reviewed eligible observations; Gold review cannot supply missing evidence")
    selected = []
    outside = []
    for r in eligible:
        time = datetime.fromisoformat(price_index[r["observation_id"]]["observed_at"].replace("Z", "+00:00"))
        if r["source_role"] == "retail" and r["comparable_group"] == "bar" and r["predictors"].get(RETAILER) in contract["retailers"] and start <= time <= end:
            selected.append(r)
        else:
            outside.append(r["observation_id"])
    selected.sort(key=lambda r: r["observation_id"])
    context_failures = Counter()
    for row in selected:
        price = price_index[row["observation_id"]]
        for field, expected in contract["required_regular_price_context"].items():
            if price.get(field) != expected:
                context_failures[field] += 1
        if price.get("time_basis") not in {"source_catalogue_observation", "source_page_observation"}:
            context_failures["time_basis"] += 1
    if context_failures:
        report["blockers"].append("missing or unsupported reviewed regular price context")
        report["price_context_failure_counts"] = dict(sorted(context_failures.items()))
    report["counts"].update(selected=len(selected), selected_families=len({r["family_id"] for r in selected}),
                            outside_cohort_or_price_window=len(outside))
    implementation_names = (*IMPLEMENTATION, "scripts/chocolate_lightgbm_fixture.py") if fixture else IMPLEMENTATION
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in implementation_names}
    published_reference = read_json((ROOT / "schemas/chocolate/dataset-contract.json").read_bytes())
    experiment = {"format_version": "chocolate-frozen-experiment-1-working", "contract": contract,
                  "working_contract_sha256": contract_hash, "working_contract_file_sha256": checksum(raw_contract),
                  "gold_manifest_sha256": checksum(storage), "gold_dataset_version": gold["dataset_version"],
                  "silver_manifest_sha256": checksum(silver_bytes), "silver_dataset_version": silver["dataset_version"],
                  "published_base_contract_reference": published_reference,
                  "copied_contracts_match_current_pin": all(checksum(inputs[n]) == published_reference["files"][n]["sha256"] for n in CONTRACTS),
                  "contract_sha256": {n: checksum(inputs[n]) for n in CONTRACTS},
                  "price_window": {"start": window_start, "end": window_end, "source_observed_at_required": True},
                  "selected_rows_logical_sha256": checksum(row_bytes(selected)),
                  "selected_observation_ids": [r["observation_id"] for r in selected],
                  "outside_domain_observation_ids": outside, "split": None}
    files = {"inputs/" + n: b for n, b in inputs.items()}
    files["inputs/gold-manifest.json"] = storage
    files["inputs/silver-manifest.json"] = silver_bytes
    files["working-contract.json"] = raw_contract
    if not report["blockers"]:
        try:
            selected = validate_population(selected, contract)
            experiment["split"] = partition(selected)
        except ModelContractError as error:
            report["blockers"].append(str(error))
    if not report["blockers"]:
        assignment = experiment["split"]["family_assignments"]
        partitions = {name: [r for r in selected if assignment[r["family_id"]] == name]
                      for name in ("fitting", "calibration", "test")}
        for name, values in partitions.items():
            files[name + ".jsonl"] = row_bytes(values)
        try:
            booster, bundle = fit(partitions["fitting"])
            uncertainty = calibrate(partitions["calibration"], booster, bundle)
            evaluation, predictions = evaluate(partitions["test"], booster, bundle, uncertainty)
            # Save every calibration/test domain decision for later common-row comparisons.
            from chocolate_lightgbm import predict_rows
            calibration_predictions = predict_rows(partitions["calibration"], booster, bundle)
            files["booster.txt"] = booster.model_to_string(num_iteration=bundle["tree_count"]).encode()
            files["model.json"] = json_bytes(bundle)
            files["preprocessing.json"] = json_bytes(bundle["preprocessing"])
            files["support-rules.json"] = json_bytes({"leaf_family_support": bundle["leaf_family_support"],
                                                       "minimum_support_families": contract["minimum_support_families"],
                                                       "minimum_leaf_families": contract["minimum_leaf_families"],
                                                       "context_support": bundle["preprocessing"]["context_support"]})
            files["calibration.json"] = json_bytes(uncertainty)
            files["evaluation.json"] = json_bytes(evaluation)
            files["predictions.jsonl"] = row_bytes([{**r, "partition": "test"} for r in predictions]
                                                       + [{**r, "partition": "calibration"} for r in calibration_predictions])
            report.update(status="fixture_validated" if fixture else "experimental_real_data_fitted",
                          implementation_status="fixture_validated" if fixture else "real_data_fitted",
                          regression_fitted=True, real_data_fitted=not fixture,
                          calibrated=all(v["status"] == "finite" for v in uncertainty["retailers"].values()),
                          evaluation=evaluation, tree_count=bundle["tree_count"],
                          supported_fitting_observations=len(bundle["fitting_observation_ids"]))
        except (ModelContractError, LightGBMError) as error:
            report["blockers"].append(str(error))
    files["experiment.json"] = json_bytes(experiment)
    command = ["uv", "run", "python", "-B", "scripts/train_chocolate_lightgbm.py", "--gold-root", str(source),
               "--output", str(output), "--working-contract", str(Path(contract_path).absolute()),
               "--price-window-start", window_start, "--price-window-end", window_end]
    if fixture:
        command.append("--fixture")
    files["reproduce.sh"] = (shlex.join(command) + "\n").encode()
    identity = {"run_format_version": "chocolate-lightgbm-run-1", "model_id": MODEL_ID,
                "fixture": fixture, "experiment_sha256": checksum(files["experiment.json"]),
                "implementation_sha256": implementation, "package_versions": VERSIONS,
                "python_version": platform.python_version(), "lock_sha256": checksum((ROOT / "uv.lock").read_bytes()),
                "artifact_sha256": {n: checksum(b) for n, b in sorted(files.items()) if n not in {"reproduce.sh"}}}
    run_id = "lightgbm-run-" + checksum(json_bytes(identity))[:24]
    report.update(run_id=run_id, gold_dataset_version=gold["dataset_version"], experiment_sha256=identity["experiment_sha256"])
    files["report.json"] = json_bytes(report)
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
                                         "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}})
    if (Path(contract_path).read_bytes() != raw_contract or (source / "manifest.json").read_bytes() != storage
            or verified_gold(source)[1] != silver_bytes
            or any(checksum((ROOT / n).read_bytes()) != digest for n, digest in implementation.items())):
        raise ValueError("input or implementation changed during training")
    return report, write_run(output, run_id, files)


def load_run(path):
    """Verify artifact integrity and identity before loading the frozen booster."""
    from chocolate_lightgbm import add_interval, prediction

    _, lgb = runtime()
    root = Path(path).resolve()
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = read_json(manifest_bytes)
    identity_keys = ("run_format_version", "model_id", "fixture", "experiment_sha256", "implementation_sha256",
                     "package_versions", "python_version", "lock_sha256", "artifact_sha256")
    identity = {k: manifest[k] for k in identity_keys}
    if manifest["model_id"] != MODEL_ID or manifest["run_id"] != "lightgbm-run-" + checksum(json_bytes(identity))[:24]:
        raise ValueError("invalid model run identity")
    files = read_managed(root, manifest["managed_files"], "Model")
    if any(checksum(files[n]) != h for n, h in manifest["artifact_sha256"].items()):
        raise ValueError("model artifact identity mismatch")
    if checksum(files["experiment.json"]) != manifest["experiment_sha256"]:
        raise ValueError("model experiment identity mismatch")
    report = read_json(files["report.json"])
    if not report["regression_fitted"]:
        raise ModelContractError("readiness run contains no fitted booster")
    bundle = read_json(files["model.json"])
    booster = lgb.Booster(model_str=files["booster.txt"].decode())
    if bundle["model_id"] != MODEL_ID or bundle["tree_count"] != booster.current_iteration() or bundle["package_versions"] != VERSIONS:
        raise ValueError("frozen booster identity mismatch")
    if (root / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("model manifest changed during load")
    calibration = read_json(files["calibration.json"])
    experiment = read_json(files["experiment.json"])
    def predict(predictors):
        packet = prediction(booster, bundle, predictors)
        packet.update(run_id=manifest["run_id"], gold_dataset_version=experiment["gold_dataset_version"],
                      experiment_sha256=manifest["experiment_sha256"], feature_policy_version=experiment["contract"]["feature_policy_version"],
                      predictors=predictors, fixture=manifest["fixture"],
                      interval_scope="representative_families_in_declared_retailer_snapshot_population")
        return add_interval(packet, calibration)
    return predict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/chocolate/uk" / MODEL_ID)
    parser.add_argument("--working-contract", type=Path, required=True)
    parser.add_argument("--prepare-working-contract", action="store_true")
    parser.add_argument("--price-window-start")
    parser.add_argument("--price-window-end")
    parser.add_argument("--fixture", action="store_true", help="Label generated synthetic evidence runs explicitly")
    args = parser.parse_args(argv)
    if args.prepare_working_contract:
        if args.working_contract.exists() and args.working_contract.read_bytes() != json_bytes(working_contract()):
            parser.error("refusing to replace a different working contract")
        args.working_contract.parent.mkdir(parents=True, exist_ok=True)
        args.working_contract.write_bytes(json_bytes(working_contract()))
        print(args.working_contract)
        return 0
    if not args.gold_root or not args.price_window_start or not args.price_window_end:
        parser.error("training requires Gold and an explicit source-price window")
    try:
        report, destination = build_run(args.gold_root, args.output, args.working_contract,
                                        args.price_window_start, args.price_window_end, fixture=args.fixture)
    except (ValueError, OSError, KeyError, ImportError) as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 1
    print(json.dumps({"output": str(destination), **report}, indent=2))
    return 0 if report["regression_fitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
