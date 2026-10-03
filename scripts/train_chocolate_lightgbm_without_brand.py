"""Train only lightgbm_without_brand from an explicit verified immutable Gold."""

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

from chocolate_gold import read_managed, verified_gold
from chocolate_lightgbm_without_brand import (
    MODEL_ID,
    VERSIONS,
    calibrate,
    check_rows,
    digest,
    evaluate,
    experiment,
    fit,
    predict,
    runtime,
    validate_contract,
    working_contract,
)
from chocolate_model import ModelContractError, validate_target_policy
from train_chocolate_model import (
    checksum,
    json_bytes,
    read_json,
    rows,
    validate_price_targets,
    write_run,
)

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ["scripts/chocolate_lightgbm_without_brand.py", "scripts/train_chocolate_lightgbm_without_brand.py",
                  "scripts/train_chocolate_model.py", "scripts/chocolate_model.py", "scripts/chocolate_gold.py", "scripts/chocolate_gold_population.py",
                  "scripts/chocolate_cleanup/core.py", "pyproject.toml", "uv.lock"]


def load_model_run(root):
    """Validate the managed immutable bundle before returning the frozen model."""
    root = Path(root).resolve()
    original = (root / "manifest.json").read_bytes()
    manifest = read_json(original)
    if manifest.get("format") != "chocolate-lightgbm-run-1" or manifest.get("model_id") != MODEL_ID:
        raise ModelContractError("unsupported model run")
    files = read_managed(root, manifest["managed_files"], "Model")
    if "model.json" not in files:
        raise ModelContractError("readiness run has no fitted model")
    model = read_json(files["model.json"])
    if (files["booster.txt"].decode() != model["booster"]
            or model["identity"] != {k: v for k, v in manifest.items() if k not in {"run_id", "managed_files"}}
            or model["experiment_sha256"] != digest(read_json(files["experiment.json"]))
            or model["preprocessing"] != read_json(files["preprocessing.json"])
            or model["calibration"] != read_json(files["calibration.json"])
            or model["contract"] != read_json(files["working-contract.json"])):
        raise ModelContractError("fitted artifacts disagree with model identity")
    if (root / "manifest.json").read_bytes() != original:
        raise ModelContractError("run manifest changed during loading")
    return model


def build_run(gold_root, output, contract_path, *, experiment_path=None, fixture=False):
    source = Path(gold_root).expanduser().resolve()
    output = Path(output).absolute()
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ModelContractError("model output must be separate from Gold")
    gold_bytes = (source / "manifest.json").read_bytes()
    silver, silver_bytes, inputs = verified_gold(source)
    gold = read_json(gold_bytes)
    if not fixture and "fixture" in silver["source_dataset_version"].casefold():
        raise ModelContractError("synthetic source marker requires --fixture; cannot claim real-data fitting")
    contract_bytes = Path(contract_path).read_bytes()
    contract = read_json(contract_bytes)
    validate_contract(contract)
    design = read_json(inputs["model-design.json"])
    if contract["target"] != design["target"] or contract["source_design_version"] != design["model_design_version"]:
        raise ModelContractError("working contract target/source differs from copied Gold design")
    candidates = rows(inputs["training-candidates.jsonl"])
    eligible = rows(inputs["model-inputs.jsonl"])
    # Validate the actual study price basis for the complete Gold population.
    price_blocker = None
    try:
        prices = validate_price_targets(eligible, rows(inputs["prices.jsonl"]), require_price_eligibility=False)
    except ModelContractError as error:
        price_blocker, prices = str(error), {}
    selected = sorted([r for r in eligible if r["comparable_group"] == "bar" and r["source_role"] == "retail"
                       and r["predictors"].get("identity.retailer") in contract["allowed_retailers"]],
                      key=lambda r: r["observation_id"])
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    common_identity = {"gold_dataset_version": gold["dataset_version"], "gold_manifest_sha256": checksum(gold_bytes),
                       "silver_dataset_version": silver["dataset_version"], "silver_manifest_sha256": checksum(silver_bytes),
                       "source_dataset_version": silver["source_dataset_version"], "contract_sha256": gold["contract_sha256"]}
    identity_blocker = any(not isinstance(r.get("family_id"), str) or not r["family_id"].strip() for r in selected)
    frozen = experiment([] if identity_blocker else selected, common_identity, contract)
    frozen["considered_observation_ids"] = [r["observation_id"] for r in selected]
    if experiment_path:
        supplied = read_json(Path(experiment_path).read_bytes())
        if supplied != frozen:
            raise ModelContractError("frozen experiment differs from data, policy or deterministic assignments")
    identity = {"format": "chocolate-lightgbm-run-1", "model_id": MODEL_ID, **common_identity,
                "working_contract_sha256": checksum(contract_bytes), "experiment_sha256": digest(frozen),
                "implementation_sha256": implementation, "versions": VERSIONS,
                "python_version": platform.python_version(), "platform": platform.platform(),
                "fixture": fixture, "seed": contract["split_seed"]}
    report = {"model_id": MODEL_ID, "status": "readiness_blocked", "implemented": True,
              "fixture": fixture, "real_data_fitted": False, "fixture_fitted": False,
              "calibrated": False, "release_ready": False, "blockers": [],
              "counts": {"training_candidates": len(candidates), "training_rows": len(eligible),
                         "selected_rows": len(selected), "selected_families": len({r["family_id"] for r in selected})},
              "price_target_policy": validate_target_policy(contract["target"]),
              "contract_publication": "pending aligned dataset/portable release review; working configuration is local",
              "baseline_relative_gates": "pending_comparator_results", "champion_selection": "pending_comparator_results",
              "unseen_brand_and_future_validation": "pending separate designs",
              "gold_review_provenance": gold.get("review_provenance")}
    if price_blocker:
        report["blockers"].append(price_blocker)
    if identity_blocker:
        report["blockers"].append("selected_rows_missing_family_identity")
    files = {"inputs/" + name: data for name, data in inputs.items()}
    files.update({"inputs/gold-manifest.json": gold_bytes, "inputs/silver-manifest.json": silver_bytes,
                  "working-contract.json": contract_bytes, "experiment.json": json_bytes(frozen)})
    partitions = {name: [r for r in selected if frozen["row_partitions"].get(r["observation_id"]) == name]
                  for name in ("fitting", "calibration", "testing")}
    report["partition_counts"] = {name: {"rows": len(values), "families": len({r["family_id"] for r in values})}
                                  for name, values in partitions.items()}
    if not selected:
        report["blockers"].append("no_gold_supermarket_bar_rows")
    if read_json(inputs["quality-report.json"])["status"] != "complete_snapshot":
        report["blockers"].append("Silver snapshot is incomplete")
    required = set(contract["core_features"] + contract["optional_features"] +
                   [contract["cohort_field"], contract["pack_count_field"], "identity.brand"])
    missing = sorted(required - set(design["predictors"]))
    report["missing_shared_contract_fields"] = missing
    if missing:
        report["blockers"].append("Gold design lacks shared cohort/pack/recipe/cocoa-basis fields: " + ", ".join(missing))
    window = contract.get("price_window")
    try:
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            raise ValueError("declare an explicit source price window")
        start, end = (datetime.fromisoformat(window[k].replace("Z", "+00:00")) for k in ("start", "end"))
        if start.tzinfo is None or end.tzinfo is None or start > end:
            raise ValueError("source price window must be ordered aware times")
        if any(not start <= datetime.fromisoformat(prices[r["observation_id"]]["observed_at"].replace("Z", "+00:00")) <= end for r in selected):
            raise ValueError("eligible observation falls outside declared price window")
    except (ValueError, TypeError, KeyError) as error:
        report["blockers"].append(str(error))
    if report["partition_counts"]["fitting"]["families"] < 10:
        report["blockers"].append("fewer_than_ten_fitting_families")
    if not report["blockers"]:
        try:
            check_rows(selected, contract)
            model = fit(partitions["fitting"], contract)
            calibration_predictions = predict(partitions["calibration"], model)
            model["calibration"] = calibrate(calibration_predictions, contract)
            predictions = {name: predict(values, model) for name, values in partitions.items()}
            evaluation = evaluate(predictions["testing"], contract)
            report.update(status="fixture_fitted" if fixture else "experimental_real_data_fitted",
                          real_data_fitted=not fixture, fixture_fitted=fixture,
                          calibrated=all(v["quantile_log"] is not None for v in model["calibration"].values()),
                          tree_count=model["tree_count"], evaluation=evaluation)
            model.update(identity=identity, experiment_sha256=digest(frozen), input_kind="verified_gold")
            files["booster.txt"] = model["booster"].encode()
            files["model.json"] = json_bytes(model)
            files["preprocessing.json"] = json_bytes(model["preprocessing"])
            files["support.json"] = json_bytes({"leaf_support": model["leaf_support"], "minimum_leaf_families": contract["minimum_leaf_families"],
                                                "domain": model["preprocessing"], "release_ready": False})
            files["calibration.json"] = json_bytes(model["calibration"])
            files["evaluation.json"] = json_bytes(evaluation)
            files["tuning.json"] = json_bytes({"candidates": model["grouped_validation"], "fold_assignments": model["fold_assignments"]})
            for name, values in predictions.items():
                files["predictions/" + name + ".jsonl"] = b"".join(json.dumps(r, sort_keys=True, allow_nan=False).encode() + b"\n" for r in values)
        except (ModelContractError, OSError, ImportError) as error:
            report["blockers"].append(str(error))
    try:
        runtime()
        report["runtime_verified"] = True
    except (ModelContractError, OSError, ImportError) as error:
        report["runtime_verified"] = False
        report["blockers"].append("runtime: " + str(error))
    run_id = "model-run-" + digest({"identity": identity, "artifact_sha256": {k: checksum(v) for k, v in files.items()}, "report": report})[:24]
    report["run_id"] = run_id
    files["report.json"] = json_bytes(report)
    # Paths are local provenance, excluded from model identity. JSON argv retains
    # literal spaces and is safe to replay without shell substitution.
    files["reproduce.json"] = json_bytes({"argv": ["uv", "run", "python", "scripts/train_chocolate_model.py", "--model-id", MODEL_ID,
                                                   "--gold-root", str(source), "--working-contract", str(Path(contract_path).resolve()),
                                                   "--output", str(output.resolve())] + (["--fixture"] if fixture else [])})
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
                                        "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}})
    verified_gold(source)
    if (source / "manifest.json").read_bytes() != gold_bytes or Path(contract_path).read_bytes() != contract_bytes:
        raise ModelContractError("input changed during training")
    if {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION} != implementation:
        raise ModelContractError("implementation changed during training")
    destination = write_run(output, run_id, files)
    return report, destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--working-contract", type=Path)
    parser.add_argument("--prepare-working-contract", action="store_true")
    parser.add_argument("--experiment", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/chocolate/uk" / MODEL_ID)
    parser.add_argument("--fixture", action="store_true", help="Label synthetic input and fitted artifacts as fixtures")
    args = parser.parse_args(argv)
    try:
        storage = read_json((args.gold_root / "manifest.json").read_bytes())
        if storage.get("manifest_format_version") == "chocolate-gold-inferred-manifest-1" and args.working_contract is None:
            if args.prepare_working_contract or args.experiment or args.fixture:
                raise ModelContractError("inferred Gold refit uses its recorded current-price exploration policy")
            from refit_chocolate_lightgbm_inferred import build_run as refit
            report, destination = refit(args.gold_root, args.output / "inferred")
            print(json.dumps({"output": str(destination), "status": report["status"], "counts": report["counts"],
                              "evaluation": report["evaluation"], "release_ready": False}, indent=2))
            return 0
        if args.working_contract is None:
            raise ModelContractError("--working-contract is required for the historical working experiment")
        if args.prepare_working_contract:
            _, _, inputs = verified_gold(args.gold_root)
            if args.working_contract.exists():
                raise ModelContractError("working contract already exists; refusing replacement")
            args.working_contract.parent.mkdir(parents=True, exist_ok=True)
            args.working_contract.write_bytes(json_bytes(working_contract(read_json(inputs["model-design.json"]))))
            print(json.dumps({"working_contract": str(args.working_contract), "status": "prepared_local_unpublished"}))
            return 0
        report, destination = build_run(args.gold_root, args.output, args.working_contract,
                                        experiment_path=args.experiment, fixture=args.fixture)
        print(json.dumps({"output": str(destination), "status": report["status"], "counts": report["counts"],
                          "blockers": report["blockers"], "release_ready": False}, indent=2))
        return 0 if report["real_data_fitted"] or report["fixture_fitted"] else 2
    except (ValueError, OSError, ImportError, KeyError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
