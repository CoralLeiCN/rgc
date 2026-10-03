"""Check Gold admission, leakage boundaries, missingness and model integrity."""

from copy import deepcopy

import numpy as np
import pytest
from chocolate_gold import json_bytes, row_bytes
from chocolate_gold_training import training_rows, verified_training_gold
from chocolate_lightgbm_without_brand import runtime
from chocolate_model import ModelContractError
from refit_chocolate_lightgbm_inferred import (
    CORE,
    FEATURES,
    WEIGHT,
    load_run,
    partition_rows,
    predict,
    preprocessing,
    transform,
)
from test_gold import GoldFixture
from train_chocolate_model import checksum


class GoldTrainingPolicyTests(GoldFixture):
    def test_verified_gold_admits_excluded_rows_without_changing_source(self):
        row = self.observation(1, eligible=False)
        self.snapshot([row], [])
        from chocolate_gold import build_legacy_gold_dataset as build_gold_dataset
        from chocolate_gold import verified_gold_storage as verified_gold
        _, root = build_gold_dataset(self.silver, self.output)
        manifest_bytes = (root / "manifest.json").read_bytes()
        _, _, admitted = verified_training_gold(root)
        import json
        candidate = json.loads(admitted["model-inputs.jsonl"])
        assert "model_eligible" not in candidate
        assert "exclusion_reasons" not in candidate
        assert candidate["source_model_eligible"] is False
        assert candidate["source_exclusion_reasons"] == row["exclusion_reasons"]
        assert admitted["source-prices.jsonl"] == verified_gold(root)[2]["prices.jsonl"]
        assert candidate["target"] == row["target"]
        assert candidate["predictors"] == row["predictors"]
        assert (root / "manifest.json").read_bytes() == manifest_bytes
        assert verified_gold(root)[2]["model-inputs.jsonl"] == b""

    def test_current_population_has_no_historical_selection_counter(self):
        from chocolate_gold import build_gold_dataset, verified_gold

        self.snapshot([self.observation(1, eligible=False)], [])
        _, root = build_gold_dataset(self.silver, self.output)
        _, _, population = verified_gold(root)
        _, _, admitted = verified_training_gold(root)
        import json
        candidate = json.loads(admitted["model-inputs.jsonl"])
        assert candidate == json.loads(population["model-inputs.jsonl"])
        assert "model_eligible" not in candidate
        assert "source_model_eligible" not in candidate
        policy = json.loads(admitted["gold-training-policy.json"])
        assert policy["historical_source_eligible_rows"] is None
        assert policy["training_rows"] == 1


def observations():
    return [{"observation_id": f"observation-{i}", "listing_id": f"listing-{i}", "family_id": f"family-{i // 2}",
             "model_eligible": False, "exclusion_reasons": ["unreviewed"],
             "predictors": {WEIGHT: 50 + i, "identity.retailer": "Waitrose",
                            "composition.chocolate_type": "milk" if i % 2 else None,
                            "identity.brand": "Brand", "composition.nuts_presence": None,
                            "dietary.vegan_claim": None, "certifications.fairtrade_claim": None,
                            "certifications.organic_claim": None},
             "target": {"current_price_per_100g_gbp": 2.0, "log_current_price_per_100g_gbp": np.log(2.0)}}
            for i in range(40)]


def test_gold_admission_preserves_missing_values_and_is_idempotent():
    source = observations()
    original = deepcopy(source)
    admitted = training_rows(source)
    assert source == original
    assert all("model_eligible" not in row and "exclusion_reasons" not in row for row in admitted)
    assert all(row["predictors"]["composition.nuts_presence"] is None for row in admitted)
    assert training_rows(admitted) == admitted
    assert row_bytes(admitted) != row_bytes(source)


def test_family_partitions_ignore_outcomes_brand_and_order():
    source = observations()
    first, assignments, folds = partition_rows(source)
    changed = deepcopy(source[::-1])
    for row in changed:
        row["target"] = {"arbitrary": 10000}
        row["predictors"]["identity.brand"] = "Changed"
    _, changed_assignments, changed_folds = partition_rows(changed)
    assert assignments == changed_assignments
    assert folds == changed_folds
    assert {r["family_id"] for r in first["fitting"]}.isdisjoint(r["family_id"] for r in first["testing"])


def test_preprocessing_uses_fitting_data_and_preserves_native_missing():
    source = observations()
    pre = preprocessing(source[:10], CORE)
    changed = deepcopy(source[10:11])
    changed[0]["predictors"]["composition.chocolate_type"] = "white"
    changed[0]["predictors"][WEIGHT] = 10000
    matrix = transform(changed, pre)
    assert np.isnan(matrix[0, 2])
    assert pre["categories"]["composition.chocolate_type"] == ["milk"]
    assert pre["weight_range_g"] == [50, 59]
    assert "identity.brand" not in FEATURES
    assert not any("price" in name or "family" in name for name in FEATURES)


def test_verified_model_reload_reconstructs_shap_and_rejects_tamper(tmp_path):
    _, lgb = runtime()
    source = observations()
    pre = preprocessing(source, CORE)
    booster = lgb.train({"objective": "regression", "num_threads": 1, "verbosity": -1, "min_data_in_leaf": 2},
                        lgb.Dataset(transform(source, pre), label=[r["target"]["log_current_price_per_100g_gbp"] for r in source],
                                    categorical_feature=[1, 2]), num_boost_round=3)
    records = predict(source, booster, pre)
    assert max(r["explanation"]["reconstruction_error_log"] for r in records) < 1e-6
    identity = {"format": "chocolate-lightgbm-inferred-run-1", "model_id": "lightgbm_without_brand"}
    from chocolate_lightgbm_without_brand import digest
    model = {"identity": identity, "booster": booster.model_to_string(), "tree_count": booster.current_iteration(),
             "preprocessing": pre, "experiment_sha256": digest({"fixture": True})}
    files = {"model.json": json_bytes(model), "booster.txt": model["booster"].encode(),
             "preprocessing.json": json_bytes(pre), "experiment.json": json_bytes({"fixture": True})}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    (tmp_path / "manifest.json").write_bytes(json_bytes({**identity, "run_id": "fixture", "managed_files": {
        name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}}))
    loaded, frozen = load_run(tmp_path)
    assert loaded == model
    assert predict(source, frozen, loaded["preprocessing"]) == records
    (tmp_path / "booster.txt").write_text("tampered")
    with pytest.raises((ValueError, ModelContractError), match="checksum"):
        load_run(tmp_path)
