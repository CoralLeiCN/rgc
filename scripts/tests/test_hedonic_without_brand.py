"""Verify weighting, leakage boundaries, calibration and immutable hedonic runs."""

import json
from copy import deepcopy

import numpy as np
import pytest
from chocolate_hedonic import (
    BASIS,
    BRAND,
    CLAIMS,
    COCOA,
    COHORT,
    NUTS,
    PACK_COUNT,
    RECIPE,
    RETAILER,
    TYPE,
    WEIGHT,
    _fit,
    bootstrap,
    build_run,
    calibrate,
    encode,
    evaluate,
    family_weights,
    fit_encoder,
    fit_model,
    load_model,
    metrics,
    partitions,
    predict,
    representatives,
    scenario_contrast,
    validate_working_contract,
    working_contract,
)
from chocolate_model import ModelContractError
from dataset_contracts import resolve_contract_root
from hedonic_fixture import fixture_gold, synthetic_rows
from train_chocolate_model import json_bytes


@pytest.fixture
def contract():
    return working_contract()


@pytest.fixture
def target():
    design = json.loads((resolve_contract_root(offline=True) / "model-design.json").read_bytes())
    return design["target"]


@pytest.fixture
def sample():
    return synthetic_rows(180)


@pytest.fixture
def fitted(sample, contract):
    return _fit(sample, contract)


def test_family_weights_and_duplicate_listing_sensitivity(sample, contract):
    model = _fit(sample, contract)
    expanded = deepcopy(sample)
    for row in sample[:2]:
        for i in range(4):
            expanded.append({**row, "observation_id": row["observation_id"] + str(i), "listing_id": row["listing_id"] + str(i)})
    weights = family_weights(expanded)
    assert sum(w for r, w in zip(expanded, weights) if r["family_id"] == sample[0]["family_id"]) == pytest.approx(1)
    repeated = _fit(expanded, contract)
    assert list(repeated["coefficients"].values()) == pytest.approx(list(model["coefficients"].values()))
    matrix = np.asarray([encode(r["predictors"], model["encoder"], contract) for r in sample])
    y = np.asarray([r["target"]["log_regular_price_per_100g_gbp"] for r in sample])
    assert list(model["coefficients"].values()) == pytest.approx(np.linalg.lstsq(matrix * np.sqrt(family_weights(sample)[:, None]), y * np.sqrt(family_weights(sample)), rcond=None)[0])


def test_no_brand_or_target_leakage(sample, contract):
    original = _fit(sample, contract)
    changed = deepcopy(sample)
    for row in changed:
        row["predictors"]["prices.regular_price"] = 999999
        row["predictors"]["identity.name"] = "Target encoded product name"
        row["predictors"]["family_id"] = row["target"]["log_regular_price_per_100g_gbp"]
    assert _fit(changed, contract)["coefficients"] == original["coefficients"]
    assert BRAND not in original["encoder"]["features"]
    p = sample[0]["predictors"]
    assert predict({**p, BRAND: "New Brand"}, original)["predicted_price_per_100g_gbp"] == predict(p, original)["predicted_price_per_100g_gbp"]
    contaminated = deepcopy(contract)
    contaminated["core_features"].append("prices.regular_price")
    with pytest.raises(ModelContractError, match="unsupported working contract"):
        validate_working_contract(contaminated)


def test_shared_feature_identification_refuses_brand_aliasing(sample, contract):
    for row in sample:
        row["predictors"][BRAND] = row["predictors"][TYPE]
    with pytest.raises(ModelContractError, match="known-brand identification"):
        _fit(sample, contract)


def test_rank_failure_does_not_silently_drop_size(sample, contract):
    for row in sample:
        row["predictors"][WEIGHT] = 100
    with pytest.raises(ModelContractError, match="rank deficient"):
        _fit(sample, contract)


def test_split_and_representatives_ignore_outcomes_and_listing_order(sample):
    splits, assignments = partitions(sample)
    changed = deepcopy(sample[::-1])
    for row in changed:
        row["target"] = {"regular_price_per_100g_gbp": 1e9, "log_regular_price_per_100g_gbp": 20.7232658369}
    assert partitions(changed)[1] == assignments
    assert [r["observation_id"] for r in representatives(sample, 1729)] == [r["observation_id"] for r in representatives(changed, 1729)]
    sets = [{r["family_id"] for r in splits[p]} for p in ("fitting", "calibration", "test")]
    assert all(not sets[i] & sets[j] for i in range(3) for j in range(i))
    assert [len(s) for s in sets] == [108, 36, 36]


def test_imputation_is_learned_only_from_fitting_and_retains_missingness(sample, contract):
    encoder = fit_encoder(sample, contract, True, "none")
    row = deepcopy(sample[0]["predictors"])
    assert row[COCOA] is None
    vector = encode(row, encoder, contract)
    assert vector[encoder["columns"].index(COCOA)] == encoder["cocoa_imputation"]["groups"][row[TYPE] + "|" + row[BASIS]]
    assert vector[encoder["columns"].index(COCOA + ":missing")] == 1
    before = deepcopy(encoder)
    row[COCOA] = 100
    with pytest.raises(ModelContractError, match="range"):
        encode(row, encoder, contract)
    assert encoder == before
    for name in CLAIMS:
        assert encoder["categories"][name]["levels"] == ["unknown"]


@pytest.mark.parametrize("changes", [
    {RETAILER: "Tesco"}, {TYPE: "ruby"}, {WEIGHT: 0}, {WEIGHT: 9000},
    {PACK_COUNT: 2}, {COHORT: None}, {RECIPE: "gift_box"}, {NUTS: "may_contain"},
])
def test_unsupported_profiles_raise(fitted, sample, changes):
    with pytest.raises(ModelContractError):
        predict({**sample[0]["predictors"], **changes}, fitted)


def independent_rows(sample, families=8):
    result = deepcopy(sample[:families * 2])
    for row in result:
        for field in ("family_id", "variant_id", "listing_id", "observation_id"):
            row[field] = "heldout-" + row[field]
    return result


def test_conformal_small_sample_unavailable_and_retailer_specific(fitted, sample):
    calibration = independent_rows(sample, 8)
    report = calibrate(calibration, fitted)
    assert all(v["order_statistic"] == 9 and v["quantile"] is None for v in report["retailers"].values())
    calibration = independent_rows(sample, 10)
    # Outcome shifts are separate per retailer; representative selection stays fixed.
    for row in calibration:
        row["target"]["log_regular_price_per_100g_gbp"] += 0.4 if row["predictors"][RETAILER] == "Waitrose" else 0.02
    report = calibrate(calibration, fitted)
    assert report["retailers"]["Waitrose"]["quantile"] > report["retailers"]["Ocado"]["quantile"]
    fitted["calibration"] = report
    point = predict(sample[0]["predictors"], fitted)
    assert point["interval"]["pack_gbp"] == pytest.approx([v * sample[0]["predictors"][WEIGHT] / 100 for v in point["interval"]["unit_gbp_per_100g"]])
    assert predict({**sample[0]["predictors"], BRAND: "Unseen Brand"}, fitted)["interval"] is None
    with pytest.raises(ModelContractError, match="overlaps"):
        calibrate(sample, fitted)


def test_bootstrap_refits_preprocessing_and_preserves_draw_multiplicity(sample, contract, fitted):
    draws, failures = bootstrap(sample, contract, False, "none", 25, reference_encoder=fitted["encoder"])
    assert len(draws) + sum(failures.values()) == 25
    assert len(draws) >= 20
    assert all(len(m["training_family_ids"]) == 180 for m in draws)
    assert len({m["coefficients"][WEIGHT] for m in draws}) > 1
    fitted["bootstrap_models"] = draws
    # This small diagnostic has fewer draws than the contract's 200; uncertainty
    # remains unavailable instead of quietly lowering the success requirement.
    contrast = scenario_contrast(sample[0]["predictors"], sample[1]["predictors"], fitted)
    assert contrast["difference_percent"] == pytest.approx(100 * (np.exp(fitted["coefficients"][RETAILER + "=Waitrose"]) - 1))
    assert contrast["confidence_interval_pack_gbp_95"] is None


def test_evaluation_weights_recomputed_inside_retailer(fitted, sample):
    rows = independent_rows(sample, 18)
    evaluation, predictions = evaluate(rows, fitted)
    assert evaluation["supported_rows"] == len(rows)
    assert evaluation["breakdowns"]["retailer"]["Ocado"]["family_weighted"] == metrics([r for r in predictions if r["retailer"] == "Ocado"])
    assert evaluation["baseline_relative_gate"] == "pending_comparator_results"
    assert not evaluation["release_ready"]
    with pytest.raises(ModelContractError, match="overlaps"):
        evaluate(sample, fitted)


def test_partition_leakage_rejected_before_fit(sample, contract, target):
    split, _ = partitions(sample)
    with pytest.raises(ModelContractError, match="disjoint"):
        fit_model(split["fitting"], split["calibration"] + split["fitting"][:2], split["test"], contract, target)


def test_empty_verified_gold_has_immutable_readiness_run(tmp_path, contract):
    gold = fixture_gold(tmp_path / "input", [])
    policy = tmp_path / "working.json"
    policy.write_bytes(json_bytes(contract))
    report, destination = build_run(gold, tmp_path / "runs", policy, fixture=True)
    assert report["counts"]["eligible_model_inputs"] == 0
    assert report["candidate_value_audit"]["positive_regular_unit_targets"] == 0
    assert not report["regression_fitted"]
    assert "no_reviewed_eligible_observations" in report["blockers"]
    assert not (destination / "model.json").exists()
    assert build_run(gold, tmp_path / "runs", policy, fixture=True)[1] == destination
    (destination / "report.json").write_text("corrupt")
    with pytest.raises(ValueError, match="immutable"):
        build_run(gold, tmp_path / "runs", policy, fixture=True)


def test_full_fixture_run_integrity_and_frozen_manifest(tmp_path, contract):
    gold = fixture_gold(tmp_path / "input", synthetic_rows(600))
    policy = tmp_path / "working.json"
    policy.write_bytes(json_bytes(contract))
    report, destination = build_run(gold, tmp_path / "runs", policy, fixture=True)
    assert report["fixture_validated"], report["blockers"]
    assert report["calibrated"]
    assert not report["real_data_fitted"]
    assert report["measured_results"]["family_weighted"]["MAE_GBP_per_100g"] < 0.15
    assert load_model(destination)["model_id"] == "hedonic_without_brand"
    assert (destination / "predictions.jsonl").exists()
    assert (destination / "selection.json").exists()
    # The synthetic source flag is inherited when the caller omits --fixture.
    replay, replay_path = build_run(gold, tmp_path / "runs", policy, destination / "experiment.json")
    assert replay_path == destination
    assert replay["fixture_validated"] and not replay["real_data_fitted"]
    fitted = load_model(destination)
    assert fitted["bootstrap_report"]["successful_replicates"] >= 160
    assert fitted["coefficient_uncertainty"]["intercept"]["confidence_interval_95"] is not None
    assert fitted["fitting_diagnostics"]["no_retailer_ablation"]
    assert fitted["fitting_diagnostics"]["brand_held_out"]
    saved_predictions = [json.loads(line) for line in (destination / "predictions.jsonl").read_text().splitlines()]
    observed = next(r for r in saved_predictions if r["point_supported"])
    test_rows = [json.loads(line) for line in (destination / "test.jsonl").read_text().splitlines()]
    profile = next(r["predictors"] for r in test_rows if r["observation_id"] == observed["observation_id"])
    assert predict(profile, fitted)["predicted_price_per_100g_gbp"] == observed["predicted_price_per_100g_gbp"]
    changed = json.loads((destination / "experiment.json").read_bytes())
    changed["split"]["seed"] = 123
    other = tmp_path / "other-experiment.json"
    other.write_bytes(json_bytes(changed))
    with pytest.raises(ModelContractError, match="frozen experiment"):
        build_run(gold, tmp_path / "runs", policy, other, fixture=True)
    (destination / "model.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_model(destination)


def test_target_policy_and_exact_variant_consistency(sample, contract, target):
    from chocolate_hedonic import validate_rows
    mismatched = deepcopy(sample)
    mismatched[1]["predictors"][BRAND] = "Different exact-product brand"
    with pytest.raises(ModelContractError, match="inconsistent reviewed product"):
        validate_rows(mismatched, contract, target)
    for name, value in (("fallback_policy", "displayed"), ("tax_basis", "unknown")):
        unsupported = {**target, name: value}
        with pytest.raises(ModelContractError, match="target policy"):
            validate_rows(sample, contract, unsupported)
    from chocolate_model import CURRENT_PRICE_TARGET_POLICY
    current = {**target, **CURRENT_PRICE_TARGET_POLICY, "name": "log_current_gbp_per_100g"}
    with pytest.raises(ModelContractError, match="regular-consumer-price-1"):
        validate_rows(sample, contract, current)


def test_gold_corruption_cannot_become_a_readiness_or_fitted_run(tmp_path, contract):
    gold = fixture_gold(tmp_path / "input", [])
    policy = tmp_path / "working.json"
    policy.write_bytes(json_bytes(contract))
    (gold / "model-inputs.parquet").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_run(gold, tmp_path / "runs", policy, fixture=True)
    assert not (tmp_path / "runs").exists()


def test_calibration_and_final_outcomes_cannot_change_selection(sample, contract, target):
    splits, _ = partitions(sample)
    model, selection, _, _ = fit_model(splits["fitting"], splits["calibration"], splits["test"], contract, target)
    for partition in ("calibration", "test"):
        for row in splits[partition]:
            row["target"]["regular_price_per_100g_gbp"] = 1e10
            row["target"]["log_regular_price_per_100g_gbp"] = np.log(1e10)
    replay, replay_selection, _, _ = fit_model(splits["fitting"], splits["calibration"], splits["test"], contract, target)
    assert replay["coefficients"] == model["coefficients"]
    assert replay["encoder"] == model["encoder"]
    assert replay_selection == selection


@pytest.mark.parametrize("model_argument", [["--model-id", "hedonic_without_brand"], ["--model-id=hedonic_without_brand"]])
def test_integrated_cli_can_prepare_and_select_hedonic(tmp_path, monkeypatch, model_argument):
    from train_chocolate_model import main
    policy = tmp_path / "working.json"
    monkeypatch.setattr("sys.argv", ["train_chocolate_model.py", *model_argument, "--prepare-working-contract", str(policy)])
    assert main() == 0
    assert json.loads(policy.read_bytes())["model_id"] == "hedonic_without_brand"
    gold = fixture_gold(tmp_path / "input", [])
    output = tmp_path / "models"
    monkeypatch.setattr("sys.argv", ["train_chocolate_model.py", *model_argument, "--gold-root", str(gold),
                                    "--working-contract", str(policy), "--group", "bar", "--output", str(output)])
    assert main() == 2
    report = json.loads(next(output.glob("*/report.json")).read_bytes())
    assert report["model_id"] == "hedonic_without_brand"
    assert "no_reviewed_eligible_observations" in report["blockers"]


@pytest.mark.parametrize("model_argument", [["--model-id", "lightgbm_without_brand"], ["--model-id=lightgbm_without_brand"]])
def test_integrated_cli_preserves_lightgbm_dispatch(monkeypatch, model_argument):
    import train_chocolate_lightgbm_without_brand
    from train_chocolate_model import main
    received = []
    def dispatch(arguments):
        received.append(arguments)
        return 7
    monkeypatch.setattr(train_chocolate_lightgbm_without_brand, "main", dispatch)
    monkeypatch.setattr("sys.argv", ["train_chocolate_model.py", *model_argument, "--gold-root", "declared-gold"])
    assert main() == 7
    assert received == [["--gold-root", "declared-gold"]]
