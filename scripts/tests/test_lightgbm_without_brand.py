"""Meaningful leakage, inference, calibration, and immutable artifact checks."""

import json
import math
from collections import defaultdict
from copy import deepcopy
from unittest.mock import patch

import numpy as np
import pytest
from chocolate_lightgbm_without_brand import (
    BASIS,
    COCOA,
    CORE,
    MODEL_ID,
    OPTIONAL,
    RETAILER,
    WEIGHT,
    calibrate,
    check_rows,
    evaluate,
    experiment,
    family_weights,
    fit,
    fit_preprocessing,
    predict,
    representatives,
    transform,
    validate_contract,
    weighted_metrics,
    working_contract,
)
from chocolate_model import ModelContractError
from dataset_contracts import resolve_contract_root
from lightgbm_fixture import fixture_gold, fixture_rows
from train_chocolate_lightgbm_without_brand import build_run, load_model_run
from train_chocolate_model import checksum, json_bytes


@pytest.fixture
def contract():
    design = json.loads((resolve_contract_root(offline=True) / "model-design.json").read_bytes())
    value = working_contract(design)
    value["maximum_iterations"] = 120
    value["patience"] = 15
    value["price_window"] = {"start": "2026-10-01T00:00:00Z", "end": "2026-10-04T00:00:00Z"}
    return value


@pytest.fixture(scope="module")
def fitted():
    design = json.loads((resolve_contract_root(offline=True) / "model-design.json").read_bytes())
    contract = working_contract(design)
    contract["maximum_iterations"] = 120
    contract["patience"] = 15
    all_rows = fixture_rows()
    manifest = experiment(all_rows, {"fixture": True}, contract)
    partitions = {key: [r for r in all_rows if manifest["row_partitions"][r["observation_id"]] == key]
                  for key in ("fitting", "calibration", "testing")}
    model = fit(partitions["fitting"], contract)
    model["calibration"] = calibrate(predict(partitions["calibration"], model), contract)
    return model, partitions


def test_family_split_is_independent_of_order_prices_and_brands(contract):
    rows = fixture_rows(20)
    first = experiment(rows, {"snapshot": "fixture"}, contract)
    changed = deepcopy(rows[::-1])
    for row in changed:
        row["target"] = {"arbitrary": 99}
        row["predictors"]["identity.brand"] = "Other Brand"
    second = experiment(changed, {"snapshot": "fixture"}, contract)
    assert first["family_assignments"] == second["family_assignments"]
    assert first["row_partitions"] == second["row_partitions"]
    assert CounterValues(first["family_assignments"]) == {"calibration": 4, "testing": 4, "fitting": 12}
    assert first["selected_rows_sha256"] != second["selected_rows_sha256"]


def test_working_configuration_cannot_mutate_estimator_or_global_feature_policy(contract):
    changed = deepcopy(contract)
    changed["parameters"]["objective"] = "regression_l1"
    with pytest.raises(ModelContractError, match="starting parameters"):
        validate_contract(changed)
    design = json.loads((resolve_contract_root(offline=True) / "model-design.json").read_bytes())
    first = working_contract(design)
    first["parameters"]["objective"] = "regression_l1"
    first["core_features"].append("target")
    second = working_contract(design)
    assert second["parameters"]["objective"] == "regression"
    assert "target" not in second["core_features"]
    validate_contract(second)


def CounterValues(values):
    from collections import Counter
    return dict(Counter(values.values()))


def test_weights_recompute_inside_each_partition():
    rows = [{"family_id": "a"}] * 4 + [{"family_id": "b"}]
    assert family_weights(rows) == [0.25] * 4 + [1.0]
    assert family_weights(rows[:2] + rows[-1:]) == [0.5, 0.5, 1.0]


def test_preprocessing_uses_only_fitting_evidence_and_rejects_price_identifiers(contract):
    rows = fixture_rows(20)
    pre = fit_preprocessing(rows, CORE + OPTIONAL, contract)
    assert "identity.brand" not in pre["columns"]
    assert "family_id" not in pre["columns"]
    missing = deepcopy(rows[0])
    missing["predictors"][COCOA] = None
    x = transform([missing], pre)
    assert x[0, pre["columns"].index(COCOA)] == pre["cocoa_medians"][json.dumps([missing["predictors"]["composition.chocolate_type"], missing["predictors"][BASIS]])]
    assert x[0, -1] == 1
    for name in ("target", "identity.brand", "family_id", "displayed_price"):
        with pytest.raises(ModelContractError, match="feature policy"):
            fit_preprocessing(rows, CORE + [name], contract)
    bad = deepcopy(rows[0])
    bad["predictors"][WEIGHT] = 1000
    with pytest.raises(ModelContractError, match="range"):
        transform([bad], pre)
    for value in ("Tesco", "New Seller"):
        bad["predictors"][RETAILER] = value
        with pytest.raises(ModelContractError, match="retailer"):
            check_rows([bad], contract)


def test_missing_shared_fields_and_unknown_tax_cannot_be_invented(contract):
    row = fixture_rows(1)[0]
    del row["predictors"][BASIS]
    with pytest.raises(ModelContractError, match="shared feature"):
        check_rows([row], contract)
    row = fixture_rows(1)[0]
    row["target"]["log_regular_price_per_100g_gbp"] = 123
    with pytest.raises(ModelContractError, match="inconsistent"):
        check_rows([row], contract)


def test_native_estimator_freezes_booster_and_reconstructs_categories_and_missingness(fitted):
    model, partitions = fitted
    records = predict(partitions["testing"], model)
    assert model["model_id"] == MODEL_ID
    assert model["estimator"] == "lightgbm_squared_error_log_price"
    assert not model["release_ready"]
    assert model["tree_count"] > 1
    assert {r["family_id"] for r in partitions["fitting"]}.isdisjoint({r["family_id"] for r in partitions["testing"]})
    for record in records:
        assert record["in_domain"]
        assert record["explanation"]["available"]
        assert record["explanation"]["reconstruction_log"] == pytest.approx(record["predicted_log"], abs=1e-6)
        assert record["predicted_pack"] == pytest.approx(record["predicted_unit"] * record["weight_g"] / 100)
    report = evaluate(records, model["contract"])
    assert report["family_weighted"]["MAE_GBP_per_100g"] < 1
    assert not report["release_ready"]
    assert all(v["quantile_log"] is not None for v in model["calibration"].values())
    assert report["intervals"]["Waitrose"]["finite_intervals"] == 36
    for candidate in model["grouped_validation"]:
        for fold in candidate["folds"]:
            training = set(fold["preprocessing"]["fitting_observation_ids"])
            validation = set(fold["validation_weights"])
            assert training.isdisjoint(validation)
            sums = defaultdict(float)
            for row in partitions["fitting"]:
                if row["observation_id"] in fold["training_weights"]:
                    sums[row["family_id"]] += fold["training_weights"][row["observation_id"]]
            assert all(v == pytest.approx(1) for v in sums.values())


def test_brand_is_not_a_predictor_and_corrupt_booster_is_refused(fitted):
    model, partitions = fitted
    row = partitions["testing"][0]
    alternative = deepcopy(row)
    alternative["predictors"]["identity.brand"] = "Unseen Brand"
    assert predict([row], model)[0]["predicted_log"] == predict([alternative], model)[0]["predicted_log"]
    assert predict([alternative], model)[0]["interval_unit"] is None
    changed = deepcopy(model)
    changed["booster_sha256"] = "wrong"
    with pytest.raises(ModelContractError, match="integrity"):
        predict([row], changed)


def test_explanation_failure_preserves_prediction_and_uses_template(fitted):
    import lightgbm

    model, partitions = fitted
    original = lightgbm.Booster.predict

    def broken(self, data, **kwargs):
        result = original(self, data, **kwargs)
        return np.zeros_like(result) if kwargs.get("pred_contrib") else result

    row = partitions["testing"][0]
    expected = predict([row], model)[0]["predicted_unit"]
    with patch.object(lightgbm.Booster, "predict", broken):
        record = predict([row], model)[0]
    assert record["predicted_unit"] == expected
    assert not record["explanation"]["available"]
    assert "attribution:" not in record["narrative"]
    assert "reconstruction failed" in record["explanation"]["reason"]


def test_conformal_rank_and_representatives_do_not_use_outcomes(contract):
    records = [{"observation_id": str(i), "family_id": "f" + str(i), "retailer": "Waitrose", "in_domain": True,
                "predicted_log": 0, "observed_unit": math.exp(i / 10), "minimum_leaf_families": 5,
                "brand_represented_in_fitting": True} for i in range(9)]
    short = calibrate(records[:8], contract)["Waitrose"]
    assert short["order_statistic"] == 9
    assert short["quantile_log"] is None
    sufficient = calibrate(records, contract)["Waitrose"]
    assert sufficient["order_statistic"] == 9
    assert sufficient["quantile_log"] == pytest.approx(0.8)
    duplicated = records + [{**r, "observation_id": r["observation_id"] + "b"} for r in records]
    selected = representatives(duplicated, 1729)
    changed = [{**r, "observed_unit": 999, "predicted_log": -9} for r in duplicated[::-1]]
    assert [r["observation_id"] for r in selected] == [r["observation_id"] for r in representatives(changed, 1729)]


def test_weighted_metrics_use_family_and_pack_scale():
    records = [{"family_id": "a", "predicted_unit": 4, "observed_unit": 2, "weight_g": 50}] * 3
    records += [{"family_id": "b", "predicted_unit": 2, "observed_unit": 2, "weight_g": 100}]
    assert weighted_metrics(records)["MAE_GBP_per_100g"] == pytest.approx(1)
    assert weighted_metrics(records)["MAE_GBP_per_pack"] == pytest.approx(0.5)
    assert weighted_metrics(records, True)["MAE_GBP_per_100g"] == pytest.approx(1.5)
    equal = [{"family_id": str(i // 6), "predicted_unit": 2 + i / 1000, "observed_unit": 2, "weight_g": 100}
             for i in range(216)]
    assert weighted_metrics(equal)["weighted_median_absolute_percentage_error"] == weighted_metrics(equal, True)["weighted_median_absolute_percentage_error"]


def test_gold_fixture_run_has_verified_immutable_artifacts_and_cannot_overwrite(tmp_path, contract):
    gold, _ = fixture_gold(tmp_path)
    path = tmp_path / "working.json"
    path.write_bytes(json_bytes(contract))
    report, destination = build_run(gold, tmp_path / "models", path, fixture=True)
    assert report["fixture_fitted"], report["blockers"]
    assert not report["real_data_fitted"]
    assert not report["release_ready"]
    with pytest.raises(ModelContractError, match="synthetic source marker"):
        build_run(gold, tmp_path / "unlabeled-models", path)
    assert load_model_run(destination)["model_id"] == MODEL_ID
    manifest = json.loads((destination / "manifest.json").read_bytes())
    for name, meta in manifest["managed_files"].items():
        assert checksum((destination / name).read_bytes()) == meta["sha256"]
    second, repeated = build_run(gold, tmp_path / "models", path, fixture=True)
    assert second == report
    assert repeated == destination
    (destination / "booster.txt").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        load_model_run(destination)
    with pytest.raises(ValueError, match="immutable snapshot"):
        build_run(gold, tmp_path / "models", path, fixture=True)
    # Corruption of Gold itself fails before a model directory is created.
    (gold / "model-inputs.parquet").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        build_run(gold, tmp_path / "other-models", path, fixture=True)
    assert not (tmp_path / "other-models").exists()


def test_excluded_gold_rows_save_readiness_and_never_fit(tmp_path, contract):
    gold, _ = fixture_gold(tmp_path, eligible=False)
    path = tmp_path / "working.json"
    path.write_bytes(json_bytes(contract))
    with patch("train_chocolate_lightgbm_without_brand.fit", side_effect=AssertionError("must not fit excluded rows")):
        report, destination = build_run(gold, tmp_path / "models", path, fixture=True)
    assert report["status"] == "readiness_blocked"
    assert report["counts"]["eligible_rows"] == 0
    assert report["counts"]["training_candidates"] == 1080
    assert "no_reviewed_eligible_supermarket_bar_rows" in report["blockers"]
    assert not (destination / "booster.txt").exists()
    with pytest.raises(ModelContractError, match="no fitted model"):
        load_model_run(destination)
    changed = deepcopy(contract)
    changed["target"]["tax_basis"] = "unknown"
    path.write_bytes(json_bytes(changed))
    with pytest.raises(ModelContractError, match="target policy"):
        build_run(gold, tmp_path / "other-models", path, fixture=True)
    assert not (tmp_path / "other-models").exists()
