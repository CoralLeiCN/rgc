#!/usr/bin/env python3
"""Train only retailer_median from immutable Gold, or persist its readiness blockers."""

import argparse
import platform
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from chocolate_experiment import freeze_partitions
from chocolate_gold import verified_gold
from chocolate_model import ModelContractError
from chocolate_retailer_median import (
    MODEL_ID,
    evaluate_retailer_median,
    fit_retailer_median,
    reviewed_rows,
    validate_design,
)
from chocolate_retailer_target import (
    current_contract_inputs,
    derive_current_targets,
    is_current_price,
    observation_index,
    target_fields,
    validate_current_targets,
    validate_pricing_policy,
)
from prepare_chocolate_retailer_contract import working_design
from train_chocolate_model import (
    ROOT,
    checksum,
    json_bytes,
    read_json,
    rows,
    validate_price_targets,
    write_run,
)

IMPLEMENTATION = ("scripts/train_chocolate_retailer_median.py", "scripts/chocolate_retailer_median.py",
                  "scripts/chocolate_experiment.py", "scripts/prepare_chocolate_retailer_contract.py",
                  "scripts/train_chocolate_model.py", "scripts/chocolate_model.py", "scripts/chocolate_gold.py",
                  "scripts/chocolate_cleanup/core.py", "scripts/chocolate_gold_eligibility.py",
                  "scripts/make_chocolate_gold_eligible.py", "scripts/chocolate_retailer_target.py",
                  "scripts/chocolate_current_price.py")


def missing_value_counts(values, design=None):
    """Report the actual required inputs, independently of administrative flags."""
    fields = ("family_id", "variant_id", "listing_id", "observation_id")
    result = {name: sum(row.get(name) is None for row in values) for name in fields}
    fields = target_fields(design) if design else ("regular_price_per_100g_gbp", "log_regular_price_per_100g_gbp")
    for name, label in zip(fields, ("current_price_per_100g_gbp", "log_current_price_per_100g_gbp")):
        key = label if design and is_current_price(design) else name
        result["target." + key] = sum(row.get("target", {}).get(name) is None for row in values)
    from chocolate_retailer_median import CONTEXT, PREDICTORS
    for name in CONTEXT + PREDICTORS:
        result["predictors." + name] = sum(row.get("predictors", {}).get(name) is None for row in values)
    return result


def json_lines(values):
    return b"".join(json_bytes(row).replace(b"\n", b"") + b"\n" for row in values)


def current_input_audit(eligible, observations, design, window_start, window_end):
    """Select complete actual inputs while retaining every Gold row and its audit."""
    prices = observation_index(observations)
    selected, audit = [], []
    start, end = (timestamp(window_start), timestamp(window_end)) if window_start else (None, None)
    for row in eligible:
        reasons = ["missing:" + name for name, count in missing_value_counts([row], design).items() if count]
        if not reasons:
            try:
                reviewed_rows([row], design)
                validate_current_targets([row], [prices[row["observation_id"]]], design)
                if start:
                    observed = prices[row["observation_id"]].get("observed_at")
                    if not isinstance(observed, str) or not start <= timestamp(observed) <= end:
                        reasons.append("outside_or_missing_observation_window")
            except (ModelContractError, ValueError, KeyError) as error:
                reasons.append("input_validation_failed: " + str(error))
        if not reasons:
            selected.append(row)
        audit.append({"observation_id": row["observation_id"], "gold_model_eligible": row["model_eligible"],
                      "selected": not reasons, "unusable_reasons": reasons})
    # Check identity consistency and duplicate listings across the complete selected view.
    reviewed_rows(selected, design)
    return selected, audit


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("price window requires timezone-aware bounds")
    return parsed


def build_run(gold_root, output, *, window_start=None, window_end=None, fixture=False, current_price_proxy=False):
    supplied_source = Path(gold_root).expanduser().absolute()
    source = supplied_source.resolve()
    output = Path(output).expanduser().absolute()
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ValueError("model output must be separate from Gold")
    if (window_start is None) != (window_end is None):
        raise ValueError("supply both price window bounds")
    if window_start and timestamp(window_start) > timestamp(window_end):
        raise ValueError("price window bounds are reversed")
    if (supplied_source.is_symlink() or any(p.is_symlink() for p in supplied_source.parents)
            or output.is_symlink() or any(p.is_symlink() for p in output.parents)):
        raise ValueError("input/output paths must not use symlink directories")
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    identity = {"run_format_version": "retailer-median-run-1", "model_id": MODEL_ID,
                "implementation_sha256": implementation, "python_version": platform.python_version(),
                "package_versions": {}, "environment_sha256": {
                    name: checksum((ROOT / name).read_bytes()) for name in ("uv.lock", "pyproject.toml")},
                "split_seed": 1729, "parameters": {"tuning": "none", "size_effect": False},
                "price_window": {"start": window_start, "end": window_end}, "fixture": fixture,
                "current_price_proxy_requested": current_price_proxy}
    from importlib.metadata import version
    identity["package_versions"] = {name: version(name) for name in ("numpy", "pyarrow")}
    files, blockers = {}, []
    candidates, eligible, selected = [], [], []
    missing_counts = {}
    input_audit, price_context, price_policy = [], {}, None
    manifest_bytes = None
    contract_valid = False
    if not (source / "manifest.json").is_file():
        blockers.append("immutable_gold_snapshot_missing")
        identity["requested_gold_path"] = str(source)
    else:
        storage_bytes = (source / "manifest.json").read_bytes()
        manifest, manifest_bytes, inputs = verified_gold(source)
        storage = read_json(storage_bytes)
        identity.update(gold_dataset_version=storage["dataset_version"], gold_manifest_sha256=checksum(storage_bytes),
                        silver_dataset_version=manifest["dataset_version"], source_dataset_version=manifest["source_dataset_version"],
                        silver_manifest_sha256=checksum(manifest_bytes), contract_sha256=manifest["contract_sha256"],
                        logical_row_digests=storage.get("logical_row_sha256", storage.get("tables")))
        files = {"inputs/" + name: data for name, data in inputs.items()}
        files["inputs/gold-manifest.json"] = storage_bytes
        files["inputs/silver-manifest.json"] = manifest_bytes
        publication_reference = ROOT / "schemas/chocolate/gold-dataset.json"
        if publication_reference.is_file():
            publication_bytes = publication_reference.read_bytes()
            publication = read_json(publication_bytes)
            if publication["dataset_version"] == storage["dataset_version"]:
                if (publication["manifest_sha256"] != checksum(storage_bytes)
                        or publication["managed_files"] != storage["managed_files"]):
                    raise ValueError("Gold snapshot differs from its immutable publication pin")
                files["inputs/gold-dataset-reference.json"] = publication_bytes
                identity["gold_publication"] = {"repo_id": publication["repo_id"],
                    "revision": publication["revision"], "path": publication["path"],
                    "reference_sha256": checksum(publication_bytes)}
        design = read_json(inputs["model-design.json"])
        candidates, eligible = rows(inputs["training-candidates.jsonl"]), rows(inputs["model-inputs.jsonl"])
        observations = rows(inputs["prices.jsonl"])
        if current_price_proxy:
            design = working_design(design, current_price_proxy=True)
            candidates = derive_current_targets(candidates, observations, design)
            eligible = derive_current_targets(eligible, observations, design)
        current_mode = is_current_price(design)
        price_policy = validate_pricing_policy(design["target"])
        identity["price_target_policy"] = price_policy
        identity["working_model_design_sha256"] = checksum(json_bytes(design))
        files["working-model-design.json"] = json_bytes(design)
        files["target-policy.json"] = json_bytes(design["target"])
        if current_mode:
            from chocolate_current_price import current_price_targets
            target_contract, target_reference_bytes, target_inputs = current_contract_inputs()
            if design["target"] != target_contract["target"]:
                raise ModelContractError("current-price working target differs from its immutable published contract")
            identity["target_contract_reference_sha256"] = checksum(target_reference_bytes)
            identity["target_contract_revision"] = read_json(target_reference_bytes)["revision"]
            files["target-contract/dataset-contract.json"] = target_reference_bytes
            files.update({"target-contract/" + name: data for name, data in target_inputs.items()})
            _, preparation = current_price_targets(eligible, observations)
            files["target-preparation.json"] = json_bytes(preparation)
            identity["price_window"]["scope"] = "explicit_observation_window" if window_start else "all_immutable_snapshot_observations"
            files["modeling-inputs.jsonl"] = json_lines(eligible)
            identity["modeling_inputs_sha256"] = checksum(files["modeling-inputs.jsonl"])
            price_context = {"observations": len(observations),
                "displayed_price_present": sum(p.get("displayed_price") is not None for p in observations),
                "tax_basis": dict(sorted(Counter(str(p.get("tax_basis")) for p in observations).items())),
                "promotion_status": dict(sorted(Counter(str(p.get("promotion_status")) for p in observations).items())),
                "review_status": dict(sorted(Counter(str(p.get("review_status")) for p in observations).items())),
                "preparation": preparation}
            files["source-price-context.json"] = json_bytes(price_context)
        missing_counts = missing_value_counts(eligible, design)
        files["missing-values.json"] = json_bytes(missing_counts)
        override = "eligibility_provenance" in storage
        if override:
            identity["gold_eligibility_provenance"] = storage["eligibility_provenance"]
            identity["parent_gold_dataset_version"] = storage["parent_gold_dataset_version"]
            files["inputs/parent-gold-manifest.json"] = (source / "inputs/parent-gold/manifest.json").read_bytes()
        prices = {}
        if current_mode:
            try:
                selected, input_audit = current_input_audit(eligible, observations, design, window_start, window_end)
                contract_valid = True
            except ModelContractError as error:
                blockers.append("model_input_validation_failed: " + str(error))
            if eligible and not selected:
                blockers.append("no_complete_current_price_model_inputs")
            files["input-readiness.jsonl"] = json_lines(input_audit)
        elif any(missing_counts.values()):
            blockers.append("required_model_inputs_missing")
        else:
            try:
                # Verified Gold supplies row eligibility. A user override supersedes
                # auxiliary Silver flags; the actual regular-price checks still apply.
                prices = validate_price_targets(eligible, observations,
                                                require_price_eligibility=not override)
            except ModelContractError as error:
                blockers.append("price_target_validation_failed: " + str(error))
        try:
            policy = validate_design(design)
            identity["experiment_policy_sha256"] = checksum(json_bytes(policy))
            identity["feature_policy_sha256"] = checksum(json_bytes(policy["common_regression_feature_policy"]))
            files["experiment-policy.json"] = json_bytes(policy)
            if not current_mode and not any(missing_counts.values()):
                reviewed_rows(eligible, design)
                contract_valid = True
        except ModelContractError as error:
            blockers.append(str(error))
        quality = read_json(inputs["quality-report.json"])
        if (quality.get("data_provenance") == "synthetic_fixture"
                or "fixture" in manifest["source_dataset_version"]):
            if not fixture:
                blockers.append("synthetic_input_requires_explicit_fixture_label")
        if quality.get("status") != "complete_snapshot":
            blockers.append("source_silver_snapshot_incomplete")
        if "review_provenance" in storage:
            identity["gold_review_provenance"] = storage["review_provenance"]
        if not current_mode and window_start and prices:
            start, end = timestamp(window_start), timestamp(window_end)
            selected = [r for r in eligible if start <= timestamp(prices[r["observation_id"]]["observed_at"]) <= end]
        elif not current_mode and not window_start:
            blockers.append("explicit_source_price_window_required")
    if not eligible:
        blockers.append("no_reviewed_eligible_observations")
    if len({r["family_id"] for r in selected}) < 3:
        blockers.append("fewer_than_three_usable_families_in_selected_sample" if price_context
                        else "fewer_than_three_reviewed_families_in_declared_window")
    from chocolate_experiment import SPLIT_ALGORITHM
    partitions, experiment = {}, {"status": "unavailable", "family_assignments": {},
                                 "split_algorithm": SPLIT_ALGORITHM, "split_seed": 1729,
                                 "requested_fractions": [0.6, 0.2, 0.2], "within_brand_quotas": False}
    if price_policy is not None:
        experiment["price_target_policy"] = price_policy
        experiment["price_window"] = identity["price_window"]
    if contract_valid and len({r["family_id"] for r in selected}) >= 3:
        partitions, split = freeze_partitions(selected)
        experiment = {"format": "chocolate-frozen-experiment-1", "data_identity": {
            key: identity[key] for key in ("gold_dataset_version", "gold_manifest_sha256", "contract_sha256")},
            "cohort": policy["cohort"], "price_window": identity["price_window"], "split": split,
            "policy_sha256": identity["experiment_policy_sha256"],
            "feature_policy_sha256": identity["feature_policy_sha256"],
            "price_target_policy": price_policy,
            "working_model_design_sha256": identity["working_model_design_sha256"],
            "eligibility": "Gold eligible view under new population contract; never promote candidates",
            "comparison_status": "baseline_cohort_only; shared regression feature evidence and identification pending",
            "selected_observation_ids": sorted(r["observation_id"] for r in selected)}
    files["experiment.json"] = json_bytes(experiment)
    identity["experiment_sha256"] = checksum(files["experiment.json"])
    run_id = "retailer-median-" + checksum(json_bytes(identity))[:24]
    report = {"model_id": MODEL_ID, "run_id": run_id, "status": "readiness_blocked",
              "implemented": True, "fixture_run": fixture, "fitted": False, "real_data_fitted": False,
              "calibrated": False, "release_ready": False, "blockers": blockers,
              "counts": {"candidates": len(candidates), "eligible": len(eligible), "selected": len(selected),
                         "selected_families": len({r["family_id"] for r in selected})},
              "missing_value_counts": missing_counts,
              "price_target_policy": price_policy, "source_price_context": price_context,
              "input_readiness_counts": dict(sorted(Counter(reason for row in input_audit for reason in row["unusable_reasons"]).items())),
              "exclusion_counts": dict(sorted(Counter(reason for r in candidates for reason in r["exclusion_reasons"]).items())),
              "comparison_release_gates": "pending_comparator_runs", "contract_publication": "separate_release_review_required",
              "comparison_readiness_blockers": ["shared_regression_feature_evidence_and_identification_pending",
                                                "common_applicable_row_comparison_pending", "comparator_results_unavailable"],
              "limitations": ["No validated future-price, unseen-brand or unseen-retailer claims.",
                              "Baseline does not identify adjusted retailer premiums.",
                              "Common regression feature admissibility remains pending fitting-only identification."]}
    if price_context:
        report["limitations"].extend(price_context["preparation"]["limitations"])
    if "gold_eligibility_provenance" in identity:
        report["gold_eligibility_provenance"] = identity["gold_eligibility_provenance"]
    evaluations = {}
    if not blockers:
        model = fit_retailer_median(partitions["fitting"], design)
        model["run_id"] = run_id
        model["identity"] = identity
        # The median has no tuning/calibration. Both held-out partitions remain separately labeled.
        for partition in ("calibration", "final_testing"):
            evaluations[partition] = evaluate_retailer_median(partitions[partition], model, partitions["fitting"])
        files["model.json"] = json_bytes(model)
        files["support-rules.json"] = json_bytes(model["support_rules"])
        files["uncertainty.json"] = json_bytes(model["uncertainty"])
        files["evaluation.json"] = json_bytes(evaluations)
        prediction_rows = [{**r, "partition": name} for name, evaluation in evaluations.items() for r in evaluation["predictions"]]
        files["predictions.jsonl"] = json_lines(prediction_rows)
        report.update(status="fixture_fitted" if fixture else "experimental_real_data_fitted", fitted=True,
                      real_data_fitted=not fixture, evaluation=evaluations)
    for name, values in partitions.items():
        files["partitions/" + name + ".jsonl"] = json_lines(values)
    command = ["uv", "run", "python", "scripts/train_chocolate_retailer_median.py", "--gold-root", str(source), "--output", str(output)]
    if window_start:
        command += ["--window-start", window_start, "--window-end", window_end]
    if fixture:
        command.append("--fixture")
    if current_price_proxy:
        command.append("--current-price-proxy")
    files["command.json"] = json_bytes(command)
    files["report.json"] = json_bytes(report)
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
        "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}})
    if manifest_bytes is not None and (verified_gold(source)[1] != manifest_bytes
                                      or (source / "manifest.json").read_bytes() != storage_bytes):
        raise ValueError("Gold input changed during training")
    if price_context:
        _, final_reference, final_contracts = current_contract_inputs()
        if (final_reference != target_reference_bytes or final_contracts != target_inputs):
            raise ValueError("current-price target contract changed during training")
    if {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION} != implementation:
        raise ValueError("model implementation changed during training")
    return report, write_run(output, run_id, files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/chocolate/uk/retailer_median")
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--fixture", action="store_true", help="Label synthetic validation; never a real-data fit")
    parser.add_argument("--current-price-proxy", action="store_true", help="Use displayed GBP price and actual edible mass; preserve source inputs")
    args = parser.parse_args(argv)
    try:
        report, destination = build_run(args.gold_root, args.output, window_start=args.window_start,
                                        window_end=args.window_end, fixture=args.fixture,
                                        current_price_proxy=args.current_price_proxy)
    except (ValueError, OSError, KeyError, ImportError) as error:
        print(json_bytes({"status": "integrity_or_input_error", "error": str(error)}).decode(), file=sys.stderr)
        return 1
    print(json_bytes({"output": str(destination), **report}).decode())
    return 0 if report["fitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
