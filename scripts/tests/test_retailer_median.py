"""Verify baseline independence, domain rules, evidence gates, and immutable runs."""

import json
import math
from copy import deepcopy

import pytest
from chocolate_experiment import family_weights, freeze_partitions
from chocolate_model import ModelContractError
from chocolate_retailer_median import (
    MASS,
    TYPE,
    evaluate_retailer_median,
    fit_retailer_median,
    metrics,
    predict_retailer_median,
    weighted_median,
)
from dataset_contracts import resolve_contract_root
from prepare_chocolate_retailer_contract import working_design
from retailer_median_fixture import fixture_gold, fixture_rows, observation
from train_chocolate_model import checksum
from train_chocolate_retailer_median import build_run


@pytest.fixture
def design():
    return working_design(json.loads((resolve_contract_root(offline=True) / "model-design.json").read_bytes()))


def test_family_split_is_outcome_independent_and_preserves_sellers():
    rows = fixture_rows()
    partitions, manifest = freeze_partitions(rows)
    assert {name: len(value) for name, value in partitions.items()} == {"fitting": 60, "calibration": 20, "final_testing": 20}
    for name, members in partitions.items():
        assert all(manifest["family_assignments"][r["family_id"]] == name for r in members)
    changed = deepcopy(rows)
    for row in changed:
        row["target"] = {"regular_price_per_100g_gbp": 999, "log_regular_price_per_100g_gbp": math.log(999)}
        row["predictors"]["identity.brand"] = row["family_id"]
    assert freeze_partitions(reversed(changed))[1] == manifest
    assert not manifest["within_brand_quotas"]
    assert freeze_partitions(rows, seed=1730)[1] != manifest


def test_partition_weights_and_weighted_median_prevent_listing_dominance(design):
    rows = [observation(f"copy-{i}", "large-family", 9) for i in range(10)]
    rows += [observation("small-a", "small-a", 1), observation("small-b", "small-b", 2)]
    assert family_weights(rows) == [0.1] * 10 + [1, 1]
    model = fit_retailer_median(rows, design)
    assert model["retailers"]["Ocado"]["types"]["dark"]["unit_price_gbp"] == 2
    assert weighted_median([2, 4], [1, 1]) == 2
    assert family_weights(rows[:1]) == [1]


def test_group_medians_retain_partition_weights(design):
    rows = [observation("a-o", "a", 1), observation("a-w", "a", 99, retailer="Waitrose"),
            observation("b", "b", 3)]
    model = fit_retailer_median(rows, design)
    assert model["retailers"]["Ocado"]["unit_price_gbp"] == 3
    assert model["retailers"]["Ocado"]["balancing_mass"] == 1.5


def test_fallback_is_fitting_only_and_pack_size_is_conversion(design):
    rows = [observation("a", "a", 2, mass=50), observation("b", "b", 4, mass=100),
            observation("w", "w", 8, retailer="Waitrose", kind="milk", mass=100)]
    model = fit_retailer_median(rows, design)
    before = deepcopy(model)
    profile = deepcopy(rows[0]["predictors"])
    profile[TYPE] = "milk"
    profile[MASS] = 75
    result = predict_retailer_median(model, profile)
    assert result["retailer_wide_fallback"]
    assert result["predicted_unit_price_gbp"] == 2
    assert result["predicted_pack_price_gbp"] == 1.5
    heldout = observation("heldout", "new-family", 100, kind="milk", mass=75)
    evaluated = evaluate_retailer_median([heldout], model, rows)
    assert evaluated["fallback_observations"] == 1
    assert model == before
    profile[MASS] = 50
    assert predict_retailer_median(model, profile)["predicted_unit_price_gbp"] == 2


@pytest.mark.parametrize("field,value,reason", [
    ("identity.retailer", "Tesco", "unseen_retailer"), (TYPE, "white", "unseen_type"),
    (MASS, 1000, "mass_outside"), (MASS, 0, "invalid_edible_mass"),
    (MASS, float("nan"), "invalid_edible_mass"), (MASS, True, "invalid_edible_mass"),
    ("quantity.pack_count", 2, "population"), ("quantity.pack_count", True, "population"),
    ("cohort", "gift_boxes", "population"), ("identity.boundary_status", "boundary", "population")])
def test_unsupported_profiles_remain_outside_domain(design, field, value, reason):
    model = fit_retailer_median([observation("a", "a"), observation("b", "b", 3)], design)
    profile = deepcopy(observation("p", "p")["predictors"])
    profile[field] = value
    result = predict_retailer_median(model, profile)
    assert not result["domain_member"]
    assert reason in result["reason"]
    assert "predicted_pack_price_gbp" not in result


def test_baseline_brand_is_context_and_has_no_calibrated_new_brand_claim(design):
    model = fit_retailer_median([observation("a", "a")], design)
    profile = observation("new", "new")["predictors"]
    profile["identity.brand"] = "Unseen Brand"
    result = predict_retailer_median(model, profile)
    assert result["domain_member"] and not result["brand_context_supported"]
    assert result["prediction_interval"] is None
    assert model["predictors"] == ["identity.retailer", TYPE]


def test_family_listing_and_variant_leakage_is_rejected(design):
    training = [observation("a", "a"), observation("b", "b")]
    model = fit_retailer_median(training, design)
    with pytest.raises(ModelContractError, match="families overlap"):
        evaluate_retailer_median([observation("new", "a")], model, training)
    changed = observation("new", "new")
    changed["variant_id"] = training[0]["variant_id"]
    with pytest.raises(ModelContractError, match="cannot span validation families"):
        evaluate_retailer_median([changed], model, training)
    changed["variant_id"] = "unique-variant"
    changed["listing_id"] = training[0]["listing_id"]
    with pytest.raises(ModelContractError, match="seller listing cannot span"):
        evaluate_retailer_median([changed], model, training)
    altered = deepcopy(training)
    altered[0]["target"] = {"regular_price_per_100g_gbp": 5, "log_regular_price_per_100g_gbp": math.log(5)}
    with pytest.raises(ModelContractError, match="differ from frozen"):
        evaluate_retailer_median([], model, altered)


def test_balanced_metrics_and_listing_sensitivity():
    records = [{"family_id": family, "observed_unit_price_gbp": 2, "observed_pack_price_gbp": 1,
                "predicted_unit_price_gbp": price, "predicted_pack_price_gbp": price / 2}
               for family, price in [("a", 4), ("a", 4), ("b", 2)]]
    result = metrics(records)
    assert result["MAE_GBP_per_100g"] == 1
    assert result["MAE_GBP_per_pack"] == 0.5
    assert result["signed_bias_GBP_per_100g"] == 1
    assert result["median_absolute_percentage_error"] == 0
    assert metrics(records, listing_weighted=True)["MAE_GBP_per_100g"] == pytest.approx(4 / 3)


def test_gold_fixture_run_is_immutable_and_all_artifacts_are_bound(tmp_path):
    gold = fixture_gold(tmp_path / "fixture")
    args = {"window_start": "2026-10-03T00:00:00Z", "window_end": "2026-10-03T23:59:59Z", "fixture": True}
    report, destination = build_run(gold, tmp_path / "models", **args)
    assert report["fitted"] and report["fixture_run"] and not report["real_data_fitted"]
    assert not report["release_ready"] and not report["calibrated"]
    manifest = json.loads((destination / "manifest.json").read_bytes())
    assert manifest["model_id"] == "retailer_median"
    assert manifest["logical_row_digests"]["model-inputs.parquet"]["rows"] == 100
    assert len(manifest["feature_policy_sha256"]) == 64
    for name, metadata in manifest["managed_files"].items():
        assert checksum((destination / name).read_bytes()) == metadata["sha256"]
    assert build_run(gold, tmp_path / "models", **args) == (report, destination)
    predictions = [json.loads(line) for line in (destination / "predictions.jsonl").read_bytes().splitlines()]
    assert len(predictions) == 40 and {r["partition"] for r in predictions} == {"calibration", "final_testing"}
    (destination / "evaluation.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        build_run(gold, tmp_path / "models", **args)


def test_empty_gold_and_missing_gold_save_concrete_blockers(tmp_path):
    gold = fixture_gold(tmp_path / "empty", [])
    report, destination = build_run(gold, tmp_path / "models")
    assert report["counts"] == {"candidates": 0, "eligible": 0, "selected": 0, "selected_families": 0}
    assert "no_reviewed_eligible_observations" in report["blockers"]
    assert "explicit_source_price_window_required" in report["blockers"]
    assert not (destination / "model.json").exists()
    missing, path = build_run(tmp_path / "missing", tmp_path / "models")
    assert "immutable_gold_snapshot_missing" in missing["blockers"]
    assert (path / "report.json").exists()


def test_corrupt_gold_is_rejected_before_artifacts(tmp_path):
    gold = fixture_gold(tmp_path / "fixture")
    (gold / "model-inputs.parquet").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        build_run(gold, tmp_path / "models")
    assert not (tmp_path / "models").exists()


def test_fixture_cannot_be_reported_as_real_training(tmp_path):
    gold = fixture_gold(tmp_path / "fixture")
    report, destination = build_run(gold, tmp_path / "models", window_start="2026-10-03T00:00:00Z",
                                    window_end="2026-10-03T23:59:59Z")
    assert "synthetic_input_requires_explicit_fixture_label" in report["blockers"]
    assert not report["real_data_fitted"] and not (destination / "model.json").exists()


def test_missing_target_or_shared_population_context_cannot_fit(design):
    for field in ("quantity.pack_count", "identity.boundary_status", "identity.brand", TYPE):
        row = observation("a", "a")
        del row["predictors"][field]
        with pytest.raises(ModelContractError):
            fit_retailer_median([row], design)
    row = observation("a", "a")
    row["target"]["regular_price_per_100g_gbp"] = None
    with pytest.raises(ModelContractError):
        fit_retailer_median([row], design)


def test_old_ols_contract_is_not_relabelled(design):
    design["model_design_version"] = "chocolate-pricing-design-3"
    with pytest.raises(ModelContractError, match="old OLS"):
        fit_retailer_median([observation("a", "a")], design)


def test_invalid_weights_and_window_are_refused(tmp_path):
    for values, weights in [([], []), ([2], [0]), ([2], [math.nan]), ([True], [1])]:
        with pytest.raises(ModelContractError):
            weighted_median(values, weights)
    with pytest.raises(ValueError, match="timezone-aware"):
        build_run(tmp_path / "missing", tmp_path / "models", window_start="2026-10-03", window_end="2026-10-04")


def test_bulk_eligibility_retains_missing_input_counts_and_provenance(tmp_path):
    from chocolate_gold_eligibility import mark_gold_eligible

    row = observation("a", "a")
    row.update(model_eligible=False, variant_id=None, family_id=None,
               exclusion_reasons=["source_exclusion"],
               target={"regular_price_per_100g_gbp": None, "log_regular_price_per_100g_gbp": None})
    gold = fixture_gold(tmp_path / "fixture", [], candidates=[row])
    _, promoted = mark_gold_eligible(gold, tmp_path / "promoted", "task-user", "Every row is eligible.")
    report, destination = build_run(promoted, tmp_path / "models", fixture=True)
    assert report["counts"]["eligible"] == 1
    assert report["exclusion_counts"] == {}
    assert "no_reviewed_eligible_observations" not in report["blockers"]
    assert "required_model_inputs_missing" in report["blockers"]
    assert report["missing_value_counts"]["variant_id"] == 1
    assert report["missing_value_counts"]["target.regular_price_per_100g_gbp"] == 1
    assert report["gold_eligibility_provenance"]["eligibility_basis"] == "user_instruction"
    manifest = json.loads((destination / "manifest.json").read_bytes())
    assert manifest["gold_eligibility_provenance"] == report["gold_eligibility_provenance"]
    assert (destination / "inputs/parent-gold-manifest.json").read_bytes() == (gold / "manifest.json").read_bytes()
    assert not report["fitted"] and not (destination / "model.json").exists()


def test_bulk_override_ignores_only_auxiliary_eligibility_flags(tmp_path):
    from train_chocolate_model import json_bytes, validate_price_targets

    row = observation("a", "a")
    price = {**{key: row[key] for key in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")},
             "regular_price": 2, "currency": "GBP", "tax_basis": "consumer_tax_included",
             "total_edible_weight_g": 100, "review_status": "reviewed", "quantity_status": "reviewed",
             "model_eligible": False, "available": True, "observed_at": "2026-10-03T12:00:00Z"}
    original = json_bytes(price)
    assert validate_price_targets([row], [price], require_price_eligibility=False)["a"] == price
    assert json_bytes(price) == original
    with pytest.raises(ModelContractError, match="reviewed regular"):
        validate_price_targets([row], [price])
    price["tax_basis"] = "unknown"
    with pytest.raises(ModelContractError, match="reviewed regular"):
        validate_price_targets([row], [price], require_price_eligibility=False)
