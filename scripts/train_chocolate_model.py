#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy==2.2.6", "pyarrow==21.0.0"]
# ///
"""Train an experimental chocolate regression from verified gold or silver data."""

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from chocolate_cleanup.core import aware_time, normalized, positive
from chocolate_model import (
    ModelContractError,
    regular_price_basis_supported,
    split_by_family,
    validate_candidates,
    validate_target_policy,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_FORMAT = "chocolate-model-run-1"
CONTRACTS = ("profile.json", "source-mappings.json", "product.schema.json", "model-design.json")
INPUTS = (*CONTRACTS, "quality-report.json", "model-inputs.jsonl", "training-candidates.jsonl", "prices.jsonl")
OPTIONAL_INPUTS = ("family-mappings.json",)
IMPLEMENTATION = ("scripts/train_chocolate_model.py", "scripts/chocolate_regression.py", "scripts/chocolate_model.py",
                  "scripts/chocolate_cleanup/core.py")


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def read_json(data):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(data, parse_constant=reject)


def verified_snapshot(root):
    """Read exact inputs and verify every managed file, including contracts."""
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("manifest_format_version") != "chocolate-silver-manifest-1":
        raise ValueError("Training requires a combined chocolate silver snapshot.")
    managed = manifest.get("managed_files")
    if not isinstance(managed, dict) or not set(INPUTS) <= set(managed):
        raise ValueError("Silver manifest is missing required modeling inputs.")
    inputs = {}
    for name, metadata in managed.items():
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or ".." in relative.parts or path.is_symlink()
                or root not in path.resolve().parents
                or any(parent.is_symlink() for parent in path.parents if parent != root and root in parent.parents)):
            raise ValueError("Silver managed path escapes its snapshot: " + name)
        data = path.read_bytes()
        if len(data) != metadata["byte_length"] or checksum(data) != metadata["sha256"]:
            raise ValueError("Silver checksum mismatch: " + name)
        if name in INPUTS or name in OPTIONAL_INPUTS:
            inputs[name] = data
    for name in CONTRACTS:
        if manifest.get("contract_sha256", {}).get(name) != checksum(inputs[name]):
            raise ValueError("Silver contract checksum mismatch: " + name)
    if (root / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Silver manifest changed during verification.")
    return manifest, manifest_bytes, inputs


def rows(data):
    # JSONL delimiters are actual LF bytes, not Unicode line separators.
    return [read_json(line) for line in data.split(b"\n") if line.strip()]


def validate_training_contract(design):
    validate_target_policy(design.get("target"))
    training = design.get("training", {})
    uncertainty = training.get("coefficient_uncertainty", {})
    if (design.get("model_design_version") not in ("chocolate-pricing-design-3", "chocolate-pricing-current-price-design-1")
            or training.get("training_contract_version") != "chocolate-ols-training-1"
            or training.get("estimator") != "ordinary_least_squares"
            or training.get("solver") != "numpy.linalg.lstsq"
            or training.get("numpy_version") != "2.2.6"
            or training.get("weighting") != "equal_seller_listing"
            or training.get("context_only_predictors") != ["identity.source_role"]
            or design.get("model", {}).get("context_only_predictors") != ["identity.source_role"]
            or uncertainty.get("method") != "family_cluster_percentile_bootstrap"
            or uncertainty.get("confidence_level") != 0.95
            or uncertainty.get("minimum_successful_replicates") != 20
            or uncertainty.get("minimum_success_fraction") != 0.8):
        raise ValueError("Unsupported experimental training contract; rebuild silver with the current design.")
    for name, minimum in (("replicates", 20), ("random_seed", 0)):
        value = uncertainty.get(name)
        if type(value) is not int or value < minimum:
            raise ValueError("Invalid bootstrap " + name)
    if uncertainty["random_seed"] > 2**32 - 1:
        raise ValueError("Invalid bootstrap random_seed")
    fraction = training.get("validation_fraction")
    if isinstance(fraction, bool) or not isinstance(fraction, (float, int)) or not 0 < fraction < 1:
        raise ValueError("Invalid family validation fraction.")
    return training


def validate_price_targets(candidates, observations, design=None, *, require_price_eligibility=True):
    """Bind accepted targets to the copied regular consumer price observations."""
    if design is not None and design["target"].get("price_basis_contract_version") == "current-consumer-price-1":
        from chocolate_current_price import validate_current_price_targets
        return validate_current_price_targets(candidates, observations)
    index = {}
    for price in observations:
        identifier = price.get("observation_id") if isinstance(price, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in index:
            raise ModelContractError("Price observations require unique observation IDs")
        index[identifier] = price
    for row in candidates:
        price = index.get(row["observation_id"])
        if price is None:
            raise ModelContractError("Training target has no matching regular price observation")
        if (not regular_price_basis_supported(price) or price.get("review_status") != "reviewed"
                or price.get("quantity_status") != "reviewed"
                or (require_price_eligibility and price.get("model_eligible") is not True)
                or not aware_time(price.get("observed_at")) or price.get("available") is not True):
            raise ModelContractError("Training target requires reviewed regular tax-inclusive consumer price context")
        for name in ("listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version"):
            if price.get(name) != row.get(name):
                raise ModelContractError("Training price observation disagrees with row provenance: " + name)
        mass = positive(price.get("total_edible_weight_g"))
        if mass is None or not math.isclose(mass, row["predictors"]["quantity.total_edible_weight_g"],
                                           rel_tol=1e-9, abs_tol=1e-9):
            raise ModelContractError("Training price observation disagrees with edible pack mass")
        expected = normalized(price["regular_price"], mass)
        if expected is None or expected <= 0 or not math.isclose(
                expected, row["target"]["regular_price_per_100g_gbp"], rel_tol=1e-9, abs_tol=1e-9):
            raise ModelContractError("Training target differs from the normalized regular consumer price")
    return index


def write_run(output, run_id, files):
    """Atomically publish an immutable run; an identical rerun only verifies it."""
    if output.is_symlink():
        raise ValueError("Model output must not use symlinked directories.")
    output = output.resolve()
    destination = output / run_id
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Model run destination must be an immutable directory.")
        actual = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file() or p.is_symlink()}
        if actual != set(files) or any((destination / n).is_symlink() or (destination / n).read_bytes() != b for n, b in files.items()):
            raise ValueError("Existing model run differs; refusing to overwrite an immutable snapshot.")
        return destination
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".model-run-", dir=output) as temporary:
        staging = Path(temporary) / run_id
        staging.mkdir()
        for name, data in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        os.rename(staging, destination)
    return destination


def build_model_run(silver_root, output, group, *, gold_root=None, current_price_target=False, target_contract_root=None):
    source = Path(gold_root if gold_root is not None else silver_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ValueError("Model output must be separate from silver or gold.")
    input_kind = "gold" if gold_root is not None else "silver"
    if gold_root is not None:
        from chocolate_gold import verified_gold
        verify_input = verified_gold
    else:
        verify_input = verified_snapshot
    storage_manifest_bytes = (source / "manifest.json").read_bytes()
    manifest, manifest_bytes, inputs = verify_input(source)
    design = read_json(inputs["model-design.json"])
    preparation = None
    target_contract_bytes = None
    if current_price_target:
        from dataset_contracts import (
            CURRENT_PRICE_REFERENCE,
            SCHEMA_CACHE,
            resolve_contracts,
        )
        target_root = Path(target_contract_root) if target_contract_root is not None else resolve_contracts(
            CURRENT_PRICE_REFERENCE, SCHEMA_CACHE)
        target_contract_bytes = (target_root / "model-design.json").read_bytes()
        design = read_json(target_contract_bytes)
    training = validate_training_contract(design)
    report_source = read_json(inputs["quality-report.json"])
    if (manifest.get("schema_version") != design.get("schema_version")
            or report_source.get("dataset_version") != manifest.get("dataset_version")):
        raise ValueError("Silver quality/design versions disagree with its manifest.")
    allowed_groups = design["predictors"]["identity.product_group"]["allowed_values"]
    if group not in allowed_groups:
        raise ValueError("Group is outside the declared chocolate study domain.")
    candidates, eligible = rows(inputs["training-candidates.jsonl"]), rows(inputs["model-inputs.jsonl"])
    if current_price_target:
        from chocolate_current_price import current_price_targets
        candidates, preparation = current_price_targets(candidates, rows(inputs["prices.jsonl"]))
        eligible = [row for row in candidates if row["model_eligible"] is True]
    for table in (candidates, eligible):
        ids = [r.get("observation_id") for r in table]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate modeling observation IDs in silver.")
        if any(r.get("dataset_version") != manifest["dataset_version"] or r.get("schema_version") != manifest["schema_version"] for r in table):
            raise ValueError("Modeling row versions disagree with the silver snapshot.")
    expected = {r["observation_id"]: r for r in candidates if r.get("model_eligible") is True}
    if expected != {r["observation_id"]: r for r in eligible}:
        raise ValueError("Model inputs differ from reviewed eligible silver candidates.")
    input_blocker = None
    if current_price_target:
        try:
            validate_candidates(eligible, design)
            price_observations = validate_price_targets(eligible, rows(inputs["prices.jsonl"]), design)
        except ModelContractError as error:
            input_blocker = str(error)
            price_observations = {}
    else:
        validate_candidates(eligible, design)
        price_observations = validate_price_targets(eligible, rows(inputs["prices.jsonl"]))
    if any(r["predictors"].get("identity.product_group") != r["comparable_group"]
           or r["predictors"].get("identity.source_role") != r["source_role"] for r in eligible):
        raise ValueError("Reviewed model predictors disagree with row group/source context.")
    selected = sorted((r for r in eligible if r["comparable_group"] == group), key=lambda r: r["observation_id"])
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    if gold_root is not None:
        implementation["scripts/chocolate_gold.py"] = checksum((ROOT / "scripts/chocolate_gold.py").read_bytes())
    if current_price_target:
        implementation["scripts/chocolate_current_price.py"] = checksum((ROOT / "scripts/chocolate_current_price.py").read_bytes())
    identity = {"run_format_version": RUN_FORMAT, "silver_manifest_sha256": checksum(manifest_bytes),
                "input_kind": input_kind, "input_manifest_sha256": checksum(storage_manifest_bytes),
                "group": group, "training_contract": training, "implementation_sha256": implementation,
                "python_version": platform.python_version(), "numpy_version": training["numpy_version"]}
    if current_price_target:
        identity["current_price_target_contract_sha256"] = checksum(target_contract_bytes)
        identity["model_design_sha256"] = checksum(json_bytes(design))
    if gold_root is not None:
        gold_manifest = read_json(storage_manifest_bytes)
        identity["gold_dataset_version"] = gold_manifest["dataset_version"]
    run_id = "model-run-" + checksum(json_bytes(identity))[:24]
    report = {"run_format_version": RUN_FORMAT, "run_id": run_id, "status": "unavailable",
              "dataset_version": manifest["dataset_version"], "source_dataset_version": manifest["source_dataset_version"],
              "schema_version": design["schema_version"], "mapping_version": read_json(inputs["source-mappings.json"])["mapping_version"],
              "model_design_version": design["model_design_version"], "group": group,
              "input_kind": input_kind,
              "price_target_policy": validate_target_policy(design["target"]),
              "counts": {"training_candidates": len(candidates), "eligible_model_inputs": len(eligible),
                         "selected_observations": len(selected), "selected_families": len({r["family_id"] for r in selected}),
                         "other_group_eligible_observations": len(eligible) - len(selected)},
              "exclusion_counts": dict(sorted(Counter(reason for r in candidates for reason in r.get("exclusion_reasons", [])).items())),
              "selected_group_exclusion_counts": dict(sorted(Counter(reason for r in candidates if r.get("comparable_group") == group for reason in r.get("exclusion_reasons", [])).items())),
              "blockers": [], "regression_fitted": False, "release_ready": False,
              "prediction_intervals_available": False,
              "limitations": ["Reviewed evidence and family identity are upstream prerequisites; a public dataset split is not a modeling approval.",
                              "Experimental coefficients describe conditional listing-price associations, not causal premiums.",
                              "Extraction evaluation, release thresholds and new-product prediction intervals remain outstanding."]}
    files = {"inputs/" + name: data for name, data in inputs.items()}
    if current_price_target:
        report["current_price_preparation"] = preparation
        report["limitations"].extend(preparation["limitations"])
        if input_blocker:
            report["blockers"].append(input_blocker)
        files["inputs/current-price-target-contract.json"] = target_contract_bytes
        files["model-design.json"] = json_bytes(design)
    files["inputs/silver-manifest.json"] = manifest_bytes
    if gold_root is not None:
        report["gold_dataset_version"] = identity["gold_dataset_version"]
        if "review_provenance" in gold_manifest:
            report["gold_review_provenance"] = gold_manifest["review_provenance"]
        if "eligibility_provenance" in gold_manifest:
            report["gold_eligibility_provenance"] = gold_manifest["eligibility_provenance"]
        files["inputs/gold-manifest.json"] = storage_manifest_bytes
    files["selected-inputs.jsonl"] = b"".join(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n" for r in selected)
    if report_source.get("status") != "complete_snapshot":
        report["blockers"].append("silver_snapshot_incomplete")
    if not selected:
        report["blockers"].append("no_reviewed_eligible_observations_in_group")
    if len({r["family_id"] for r in selected}) < 2:
        report["blockers"].append("fewer_than_two_reviewed_families_in_group")
    if len({r["listing_id"] for r in selected}) != len(selected):
        report["blockers"].append("repeated_listing_observations_require_reviewed_cross_sectional_selection")
    if not report["blockers"]:
        split = split_by_family(selected, training["validation_fraction"])
        report["split"] = split["metadata"]
        for partition in ("train", "validation"):
            files[partition + ".jsonl"] = b"".join(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n" for r in split[partition])
        files["split.json"] = json_bytes(split["metadata"])
        try:
            import numpy
            if numpy.__version__ != training["numpy_version"]:
                raise ValueError("Use the pinned NumPy runtime declared by the silver training contract.")
            from chocolate_regression import evaluate_regression, fit_regression
            uncertainty = training["coefficient_uncertainty"]
            model = fit_regression(split["train"], design, bootstrap_replicates=uncertainty["replicates"], random_seed=uncertainty["random_seed"])
            evaluation = evaluate_regression(split["validation"], model, split["train"])
            prices = price_observations
            times = sorted((prices[r["observation_id"]]["observed_at"] for r in selected),
                           key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")))
            report.update(status="experimental_fitted", regression_fitted=True, validation=evaluation,
                          observation_window={"first_observed_at": times[0], "last_observed_at": times[-1],
                                              "rule": "one reviewed observation per seller listing; no automated time selection"})
            model.update(run_id=run_id, dataset_version=manifest["dataset_version"],
                         source_dataset_version=manifest["source_dataset_version"], mapping_version=report["mapping_version"],
                         observation_window=report["observation_window"], validation_results=evaluation,
                         split_groups=split["metadata"], eligibility_rules=design["eligibility_gates"])
            model["input_kind"] = input_kind
            if gold_root is not None:
                model["gold_dataset_version"] = report["gold_dataset_version"]
                if "gold_review_provenance" in report:
                    model["gold_review_provenance"] = report["gold_review_provenance"]
            files["model.json"] = json_bytes(model)
        except ModelContractError as error:
            report["blockers"].append(str(error))
    files["report.json"] = json_bytes(report)
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id, "dataset_version": manifest["dataset_version"],
                                         "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}})
    if (verify_input(source)[1] != manifest_bytes or (source / "manifest.json").read_bytes() != storage_manifest_bytes
            or {name: checksum((ROOT / name).read_bytes()) for name in implementation} != implementation):
        raise ValueError("Input snapshot or modeling implementation changed during the run.")
    destination = write_run(output, run_id, files)
    return report, destination


def main():
    if any(a == "--model-id" or a.startswith("--model-id=") for a in sys.argv):
        arguments = sys.argv[1:]
        for i, value in enumerate(arguments):
            if value.startswith("--model-id="):
                arguments[i:i + 1] = ["--model-id", value.split("=", 1)[1]]
                break
        index = arguments.index("--model-id")
        if index + 1 >= len(arguments):
            print("--model-id requires a value.", file=sys.stderr)
            return 1
        if arguments[index + 1] == "lightgbm_without_brand":
            from train_chocolate_lightgbm_without_brand import main as lightgbm_main
            return lightgbm_main(arguments[:index] + arguments[index + 2:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=("experimental_ols", "hedonic_without_brand", "matched_retailer"), default="experimental_ols")
    parser.add_argument("--working-contract", type=Path, help="Explicit local working policy for the selected estimator")
    parser.add_argument("--prepare-working-contract", type=Path, help="Write the local hedonic policy and exit")
    parser.add_argument("--experiment-manifest", type=Path, help="Require an identical frozen experiment")
    parser.add_argument("--fixture", action="store_true", help="Label synthetic input fits; never report real-data fitting")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--silver-root", type=Path, help="Compatibility input: a combined silver snapshot")
    source.add_argument("--gold-root", type=Path, help="Input: an immutable Parquet gold snapshot directory")
    parser.add_argument("--match-review", type=Path, help="Reviewed exact-variant and observation-context evidence bundle")
    parser.add_argument("--verified-gold-candidates", action="store_true",
                        help="Use task-authorized verified Gold candidates without changing source eligibility flags")
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/chocolate/uk")
    parser.add_argument("--group", help="One reviewed comparable product group, such as bar")
    parser.add_argument("--current-price-target", action="store_true", help="Use collected displayed prices under current-consumer-price-1")
    parser.add_argument("--target-contract-root", type=Path, help="Prepared local current-price contract root before publication")
    args = parser.parse_args()
    try:
        if args.model_id != "matched_retailer" and (args.match_review or args.verified_gold_candidates):
            raise ValueError("Match review and verified Gold candidate options require --model-id matched_retailer")
        if args.prepare_working_contract:
            if args.model_id == "matched_retailer":
                raise ValueError("Prepare matched_retailer contracts with scripts/chocolate_matched_retailer.py")
            from chocolate_hedonic import working_contract
            data = json_bytes(working_contract())
            path = args.prepare_working_contract
            if path.exists() and path.read_bytes() != data:
                raise ValueError("Refusing to overwrite a different working contract")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print(json.dumps({"working_contract": str(path.resolve()), "sha256": checksum(data), "published": False}))
            return 0
        if not args.group:
            raise ValueError("--group is required for training")
        if args.model_id == "matched_retailer":
            from chocolate_matched_retailer import build_matched_run
            if args.gold_root is None or args.silver_root is not None or args.working_contract is None:
                raise ValueError("matched_retailer requires --gold-root and --working-contract")
            if args.current_price_target or args.target_contract_root or args.experiment_manifest or args.fixture:
                raise ValueError("matched_retailer uses its working contract and match review for target and experiment settings")
            report, destination = build_matched_run(args.gold_root, args.output / "matched_retailer",
                                                  args.working_contract, args.match_review, args.group,
                                                  verified_gold_candidates=args.verified_gold_candidates)
            print(json.dumps({"output": str(destination), **report}, indent=2))
            return 0 if report["real_data_fitted"] else 2
        if args.model_id == "hedonic_without_brand":
            from chocolate_hedonic import build_run
            if args.gold_root is None or args.working_contract is None or args.group != "bar":
                raise ValueError("hedonic_without_brand requires --gold-root, --working-contract and --group bar")
            if args.current_price_target or args.target_contract_root:
                raise ValueError("The hedonic working policy retains its historical regular-consumer-price-1 target")
            output = args.output if args.output != ROOT / "data/models/chocolate/uk" else args.output / args.model_id
            report, destination = build_run(args.gold_root, output, args.working_contract,
                                            args.experiment_manifest, fixture=args.fixture)
        else:
            if args.working_contract or args.experiment_manifest or args.fixture:
                raise ValueError("Working experiment options require --model-id hedonic_without_brand")
            report, destination = build_model_run(args.silver_root or ROOT / "data/silver/chocolate/uk",
                                                  args.output, args.group, gold_root=args.gold_root,
                                                  current_price_target=args.current_price_target,
                                                  target_contract_root=args.target_contract_root)
    except (OSError, ValueError, KeyError, ImportError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"output": str(destination), "status": report["status"], "counts": report["counts"],
                      "blockers": report["blockers"], "regression_fitted": report["regression_fitted"], "release_ready": False}, indent=2))
    return 0 if report["regression_fitted"] else 2


if __name__ == "__main__":
    sys.exit(main())
