"""Exercise actual native boosting, leakage boundaries, calibration and integrity."""

import math
from copy import deepcopy
from unittest.mock import patch

import numpy as np
import pytest
from chocolate_experiment import (
    BRAND,
    COCOA,
    MASS,
    POPULATION,
    RETAILER,
    encode,
    family_weights,
    fit_preprocessing,
    partition,
    representatives,
    validate_population,
    working_contract,
)
from chocolate_gold import build_gold_dataset
from chocolate_lightgbm import MODEL_ID, calibrate, metrics, prediction
from chocolate_lightgbm_fixture import build_fixture, fixture_rows
from chocolate_model import ModelContractError
from train_chocolate_lightgbm import build_run, load_run
from train_chocolate_model import json_bytes, read_json


@pytest.fixture(scope="module")
def fitted_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("native-lightgbm")
    gold, contract = build_fixture(root / "inputs", count=100)
    report, destination = build_run(gold, root / "runs", contract,
                                     "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)
    assert report["regression_fitted"], report["blockers"]
    import lightgbm as lgb
    bundle = read_json((destination / "model.json").read_bytes())
    booster = lgb.Booster(model_file=str(destination / "booster.txt"))
    return root, destination, report, booster, bundle


def test_family_assignment_and_weights_are_outcome_independent():
    rows = fixture_rows(30)
    split = partition(rows)
    assert split == partition(list(reversed(rows)))
    changed = deepcopy(rows)
    for row in changed:
        row["target"] = {"irrelevant": 999999}
        row["predictors"][BRAND] = "Changed Brand"
    assert partition(changed) == split
    assert set(split["family_assignments"].values()) == {"fitting", "calibration", "test"}
    for name in ("fitting", "calibration", "test"):
        members = [r for r in rows if split["family_assignments"][r["family_id"]] == name]
        totals = {}
        for row, weight in zip(members, family_weights(members)):
            totals[row["family_id"]] = totals.get(row["family_id"], 0) + weight
        assert all(math.isclose(w, 1) for w in totals.values())
    assert family_weights([rows[0], rows[1], rows[12]]) == [0.5, 0.5, 1.0]


def test_preprocessing_learns_no_holdout_categories_targets_or_imputation():
    fitting = fixture_rows(40)
    state = fit_preprocessing(fitting, True)
    changed = deepcopy(fitting)
    for r in changed:
        r["target"] = {"anything": 1000}
    assert state == fit_preprocessing(changed, True)
    original = deepcopy(state)
    p = deepcopy(fitting[0]["predictors"])
    p[BRAND] = "Holdout Brand"
    with pytest.raises(ModelContractError, match="unsupported"):
        encode(p, state)
    p = deepcopy(fitting[0]["predictors"])
    p[COCOA] = None
    encoded = encode(p, state)
    if COCOA in state["features"]:
        assert encoded[state["columns"].index(COCOA + "__missing")] == 1
    assert state == original
    assert not state["identification"]["comparator_fitted"]


def test_evidence_missingness_and_population_cannot_be_invented():
    rows = fixture_rows(10)
    for name, value in (("study.population", "gift"), ("quantity.pack_count", 2), (COCOA, "70")):
        changed = deepcopy(rows)
        changed[0]["predictors"][name] = value
        with pytest.raises(ModelContractError):
            validate_population(changed, working_contract())
    del rows[0]["predictors"]["study.population"]
    with pytest.raises(ModelContractError, match="missing shared evidence"):
        validate_population(rows, working_contract())


def test_booster_is_the_assigned_native_estimator_and_uses_known_brand(fitted_run):
    _, destination, report, booster, bundle = fitted_run
    assert bundle["model_id"] == MODEL_ID
    assert report["fixture"] and not report["real_data_fitted"] and not report["release_ready"]
    assert report["calibrated"]
    assert bundle["parameters"]["objective"] == "regression"
    assert bundle["tree_count"] == booster.current_iteration()
    assert bundle["preprocessing"]["categorical_indices"]
    p = deepcopy(fixture_rows()[0]["predictors"])
    low = prediction(booster, bundle, p)
    p[BRAND] = "Fixture Brand B"
    high = prediction(booster, bundle, p)
    assert high["unit_price_gbp_per_100g"] > 1.3 * low["unit_price_gbp_per_100g"]
    assert (destination / "calibration.json").exists()
    assert report["evaluation"]["family_weighted"]["mae_gbp_per_100g"] < 0.12


def test_tuning_and_fitted_vocabulary_never_use_calibration_or_test(fitted_run):
    _, destination, _, _, bundle = fitted_run
    experiment = read_json((destination / "experiment.json").read_bytes())
    fitting_ids = {i for i, name in experiment["split"]["observation_assignments"].items() if name == "fitting"}
    row_families = {r["observation_id"]: r["family_id"] for r in fixture_rows(100)}
    for trial in bundle["validation"]["trials"]:
        for fold in trial["folds"]:
            assert set(fold["fitting_ids"]) <= fitting_ids
            assert set(fold["validation_ids"]) <= fitting_ids
            assert not set(fold["fitting_ids"]) & set(fold["validation_ids"])
            assert set(fold["preprocessing"]["training_observation_ids"]) <= set(fold["fitting_ids"])
            fit_families = {row_families[i] for i in fold["fitting_ids"]}
            val_families = {row_families[i] for i in fold["validation_ids"]}
            assert not fit_families & val_families
    assert set(bundle["preprocessing"]["training_observation_ids"]) == fitting_ids


def test_tree_shap_reconstructs_native_predictions_and_pack_conversion(fitted_run):
    _, _, _, booster, bundle = fitted_run
    for row in fixture_rows(8)[::7]:
        p = row["predictors"]
        packet = prediction(booster, bundle, p)
        assert packet["explanation_status"] == "verified"
        assert math.isclose(packet["reference_log_value"] + sum(packet["shap_log_values"].values()), packet["log_unit_price"], abs_tol=1e-6)
        assert math.isclose(packet["pack_price_gbp"], packet["unit_price_gbp_per_100g"] * p[MASS] / 100)
        assert packet["reference_name"] == "model explanation reference"
    assert not hasattr(booster, "coef_")


def test_explanation_failure_retains_prediction_without_attribution(fitted_run):
    _, _, _, booster, bundle = fitted_run
    native = booster.predict
    def corrupted(data, **kwargs):
        if kwargs.get("pred_contrib"):
            return np.zeros((len(data), len(bundle["preprocessing"]["columns"]) + 1))
        return native(data, **kwargs)
    with patch.object(booster, "predict", side_effect=corrupted):
        packet = prediction(booster, bundle, fixture_rows()[0]["predictors"])
    assert packet["explanation_status"] == "unavailable"
    assert "shap_log_values" not in packet
    assert packet["unit_price_gbp_per_100g"] > 0
    assert "attribution" not in packet["narrative"]


def test_unseen_levels_population_size_and_sparse_leaves_reject(fitted_run):
    _, _, _, booster, bundle = fitted_run
    p = deepcopy(fixture_rows()[0]["predictors"])
    for name, value in ((BRAND, "Unknown Brand"), (BRAND, ["untyped"]), (RETAILER, "Tesco"), (MASS, 9999),
                        ("study.population", "assortment"), ("quantity.pack_count", 2)):
        changed = {**p, name: value}
        with pytest.raises(ModelContractError):
            prediction(booster, bundle, changed)
    sparse = deepcopy(bundle)
    sparse["leaf_family_support"] = [{k: 1 for k in leaves} for leaves in sparse["leaf_family_support"]]
    with pytest.raises(ModelContractError, match="insufficient independent families"):
        prediction(booster, sparse, p)


def test_conformal_selection_is_outcome_independent_and_rank_is_not_clipped(fitted_run):
    _, _, _, booster, bundle = fitted_run
    rows = [r for r in fixture_rows(8) if r["predictors"][BRAND] == "Fixture Brand A"]
    changed = deepcopy(rows)
    for r in changed:
        r["target"] = {"regular_price_per_100g_gbp": 1000, "log_regular_price_per_100g_gbp": math.log(1000)}
    assert [r["observation_id"] for r in representatives(rows)] == [r["observation_id"] for r in representatives(changed)]
    assert representatives(rows) == representatives(list(reversed(rows)))
    calibrated = calibrate(rows, booster, bundle)
    assert not calibrated["weighted_scores"]
    for spec in calibrated["retailers"].values():
        assert spec["families"] == 8
        assert spec["rank"] == 9 and spec["quantile"] is None
        assert spec["status"] == "unavailable_unbounded"
    finite = calibrate([r for r in fixture_rows(10) if r["predictors"][BRAND] == "Fixture Brand A"], booster, bundle)
    for spec in finite["retailers"].values():
        assert spec["quantile"] == sorted(spec["sorted_scores"])[spec["rank"] - 1]


def test_model_artifact_integrity_and_immutable_replay(fitted_run):
    _, destination, _, _, _ = fitted_run
    predict = load_run(destination)
    assert predict(fixture_rows()[0]["predictors"])["model_id"] == MODEL_ID
    path = destination / "booster.txt"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"damaged")
        with pytest.raises(ValueError, match="checksum mismatch"):
            load_run(destination)
    finally:
        path.write_bytes(original)


def test_metrics_reweight_families_and_convert_each_pack():
    rows = []
    for family, error, mass in (("a", 1, 50), ("a", 1, 50), ("b", 3, 100)):
        rows.append({"family_id": family, "target": {"regular_price_per_100g_gbp": 2},
                     "unit_price_gbp_per_100g": 2 + error, "predictors": {MASS: mass}})
    assert metrics(rows)["mae_gbp_per_100g"] == 2
    assert metrics(rows)["mae_gbp_per_pack"] == 1.75
    assert math.isclose(metrics(rows, True)["mae_gbp_per_100g"], 5 / 3)


def test_empty_verified_gold_saves_readiness_without_fitting(tmp_path):
    gold, contract = build_fixture(tmp_path / "fixture", count=10)
    silver = tmp_path / "fixture/silver"
    for name in ("model-inputs.jsonl", "training-candidates.jsonl", "prices.jsonl"):
        (silver / name).write_bytes(b"")
    quality = read_json((silver / "quality-report.json").read_bytes())
    quality["counts"] = {"eligible_model_inputs": 0, "training_candidates": 0}
    (silver / "quality-report.json").write_bytes(json_bytes(quality))
    from train_chocolate_model import checksum
    manifest = read_json((silver / "manifest.json").read_bytes())
    for name in manifest["managed_files"]:
        data = (silver / name).read_bytes()
        manifest["managed_files"][name] = {"sha256": checksum(data), "byte_length": len(data)}
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    _, gold = build_gold_dataset(silver, tmp_path / "empty-gold")
    with patch("train_chocolate_lightgbm.fit", side_effect=AssertionError("must not fit")):
        report, destination = build_run(gold, tmp_path / "runs", contract,
                                         "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)
        replay, same = build_run(gold, tmp_path / "runs", contract,
                                "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)
    assert report == replay and destination == same
    assert not report["regression_fitted"] and report["blockers"]
    with pytest.raises(ModelContractError, match="no fitted"):
        load_run(destination)
    (gold / "model-inputs.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_run(gold, tmp_path / "other", contract, "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)


def test_core_aliasing_blocks_identification_without_fitting_comparator():
    rows = fixture_rows(40)
    for r in rows:
        r["predictors"][BRAND] = r["predictors"][RETAILER]
    with pytest.raises(ModelContractError, match="aliased"):
        fit_preprocessing(rows)
    assert working_contract()["population"] == POPULATION


def test_fitted_run_replay_reproduces_immutable_artifacts(fitted_run):
    root, destination, expected, _, _ = fitted_run
    gold = next((root / "inputs/gold").iterdir())
    report, replay = build_run(gold, root / "runs", root / "inputs/working-contract.json",
                              "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)
    assert replay == destination
    assert report == expected


def test_pinned_runtime_and_feature_whitelist(fitted_run):
    import lightgbm
    from chocolate_lightgbm import runtime
    _, _, _, booster, bundle = fitted_run
    rows = fixture_rows()
    p = deepcopy(rows[0]["predictors"])
    original = encode(p, bundle["preprocessing"])
    p.update(observation_id="injected", name="Observed product name", regular_price=1000000, price_band="expensive")
    assert encode(p, bundle["preprocessing"]) == original
    with patch.object(lightgbm, "__version__", "unverified"):
        with pytest.raises(ModelContractError, match="pinned runtime"):
            runtime()


def test_member_offer_is_a_readiness_blocker_even_with_a_regular_amount(tmp_path):
    gold, contract = build_fixture(tmp_path / "fixture", count=10)
    silver = tmp_path / "fixture/silver"
    from chocolate_gold import rows
    from train_chocolate_model import checksum
    prices = rows((silver / "prices.jsonl").read_bytes())
    prices[0]["regular_price_membership_basis"] = "member_only"
    from chocolate_gold import row_bytes
    data = row_bytes(prices)
    (silver / "prices.jsonl").write_bytes(data)
    manifest = read_json((silver / "manifest.json").read_bytes())
    manifest["managed_files"]["prices.jsonl"] = {"sha256": checksum(data), "byte_length": len(data)}
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    _, gold = build_gold_dataset(silver, tmp_path / "member-gold")
    with patch("train_chocolate_lightgbm.fit", side_effect=AssertionError("member target must not fit")):
        report, destination = build_run(gold, tmp_path / "runs", contract,
                                         "2026-10-01T00:00:00+01:00", "2026-10-03T23:59:59+01:00", fixture=True)
    assert not report["regression_fitted"]
    assert report["price_context_failure_counts"]["regular_price_membership_basis"] == 1
    assert (destination / "report.json").is_file()


def test_native_attribution_error_uses_prediction_fallback(fitted_run):
    from lightgbm.basic import LightGBMError
    _, _, _, booster, bundle = fitted_run
    native = booster.predict
    def unavailable(data, **kwargs):
        if kwargs.get("pred_contrib"):
            raise LightGBMError("native contribution path unavailable")
        return native(data, **kwargs)
    with patch.object(booster, "predict", side_effect=unavailable):
        packet = prediction(booster, bundle, fixture_rows()[0]["predictors"])
    assert packet["explanation_status"] == "unavailable"
    assert "shap_log_values" not in packet
    assert packet["pack_price_gbp"] > 0
