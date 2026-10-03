"""Verify current-price provenance, quantities, usable samples and immutable runs."""

import json
from copy import deepcopy

import pytest
from chocolate_current_price import (
    current_price_targets,
    validate_current_price_targets,
)
from chocolate_gold import verified_gold
from chocolate_model import ModelContractError
from chocolate_retailer_target import current_contract_inputs, validate_pricing_policy
from prepare_chocolate_retailer_contract import working_design
from retailer_median_fixture import fixture_gold, fixture_rows, observation
from train_chocolate_model import checksum
from train_chocolate_retailer_median import build_run


def price_for(row, **changes):
    price = {name: row[name] for name in
             ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")}
    price.update(displayed_price=3, regular_price=99, reference_price=100,
                 total_edible_weight_g=row["predictors"]["quantity.total_edible_weight_g"],
                 currency="GBP", tax_basis="unknown", promotion_status="member_price",
                 review_status="unreviewed", quantity_status="known", available=None, model_eligible=False)
    price.update(changes)
    return price


def test_current_price_uses_displayed_amount_and_preserves_source_evidence():
    row = observation("a", "a", mass=50)
    source = price_for(row)
    before = deepcopy((row, source))
    prepared, report = current_price_targets([row], [source])
    assert prepared[0]["target"]["current_price_per_100g_gbp"] == 6
    assert prepared[0]["target"]["regular_price_per_100g_gbp"] == 6
    assert prepared[0]["model_eligible"] is True
    assert report["counts"]["current_unit_price_targets"] == 1
    assert validate_current_price_targets(prepared, [source]) == {"a": source}
    assert (row, source) == before


@pytest.mark.parametrize("changes,reason", [
    ({"displayed_price": None}, "current_price_missing_or_invalid"),
    ({"displayed_price": True}, "current_price_missing_or_invalid"),
    ({"displayed_price": 0}, "current_price_missing_or_invalid"),
    ({"currency": "EUR"}, "current_price_currency_not_gbp"),
    ({"total_edible_weight_g": None}, "price_and_predictor_edible_weight_disagree"),
    ({"total_edible_weight_g": 51}, "price_and_predictor_edible_weight_disagree"),
])
def test_current_price_never_falls_back_to_regular_or_guesses_mass(changes, reason):
    row = observation("a", "a", mass=50)
    prepared, report = current_price_targets([row], [price_for(row, **changes)])
    assert prepared[0]["target"]["current_price_per_100g_gbp"] is None
    assert report["target_failures"] == {reason: 1}
    with pytest.raises(ModelContractError, match="normalized current displayed price"):
        validate_current_price_targets(prepared, [price_for(row, **changes)])


def test_current_price_rejects_missing_quantity_provenance_and_altered_targets():
    row = observation("a", "a")
    source = price_for(row)
    row["predictors"]["quantity.total_edible_weight_g"] = None
    assert current_price_targets([row], [source])[1]["target_failures"] == {"edible_weight_missing_or_invalid": 1}
    with pytest.raises(ModelContractError, match="row provenance"):
        current_price_targets([row], [price_for(row, listing_id="different")])
    row = observation("a", "a")
    prepared, _ = current_price_targets([row], [price_for(row)])
    prepared[0]["target"]["current_price_per_100g_gbp"] = 99
    with pytest.raises(ModelContractError, match="normalized current displayed price"):
        validate_current_price_targets(prepared, [price_for(row)])


def test_published_current_contract_preserves_model_specific_predictors():
    contract, reference, inputs = current_contract_inputs()
    design = working_design(contract, current_price_proxy=True)
    assert json.loads(reference)["revision"] == "d743cb8dbca37f5241cccd444a16165523304f6c"
    assert checksum(inputs["model-design.json"]) == "c7b7f55d0424f8bdbef2fbc76e7b75475753eaad8021f7e1acd266de284ac8de"
    assert design["target"] == contract["target"]
    assert design["model"]["predictors"] == ["identity.retailer", "composition.chocolate_type"]
    assert validate_pricing_policy(design["target"])["price_basis_contract_version"] == "current-consumer-price-1"
    changed = deepcopy(design["target"])
    changed["tax_basis"] = "consumer_tax_included"
    with pytest.raises(ModelContractError, match="proxy policy"):
        validate_pricing_policy(changed)


def test_current_price_refit_binds_contract_and_keeps_gold_bytes(tmp_path):
    gold = fixture_gold(tmp_path / "fixture", current_price=True)
    before = {str(p.relative_to(gold)): checksum(p.read_bytes()) for p in gold.rglob("*") if p.is_file()}
    report, destination = build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True)
    assert report["fitted"] and report["fixture_run"] and not report["real_data_fitted"]
    assert report["counts"] == {"candidates": 100, "eligible": 100, "selected": 100, "selected_families": 50}
    assert report["blockers"] == []
    assert report["source_price_context"]["tax_basis"] == {"unknown": 100}
    assert report["source_price_context"]["promotion_status"] == {"promotional": 100}
    assert report["price_target_policy"]["price_basis_contract_version"] == "current-consumer-price-1"
    model = json.loads((destination / "model.json").read_bytes())
    assert model["price_target_policy"] == report["price_target_policy"]
    assert model["identity"]["price_window"]["scope"] == "all_immutable_snapshot_observations"
    manifest = json.loads((destination / "manifest.json").read_bytes())
    for name, metadata in manifest["managed_files"].items():
        assert checksum((destination / name).read_bytes()) == metadata["sha256"]
    original = verified_gold(gold)[2]
    assert (destination / "inputs/prices.jsonl").read_bytes() == original["prices.jsonl"]
    assert (destination / "inputs/model-inputs.jsonl").read_bytes() == original["model-inputs.jsonl"]
    assert json.loads((destination / "target-contract/dataset-contract.json").read_bytes())["revision"] == manifest["target_contract_revision"]
    assert {str(p.relative_to(gold)): checksum(p.read_bytes()) for p in gold.rglob("*") if p.is_file()} == before
    assert build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True) == (report, destination)


def test_current_price_fits_complete_subset_without_changing_eligibility(tmp_path):
    values = fixture_rows()
    values[0]["variant_id"] = None
    gold = fixture_gold(tmp_path / "fixture", values, current_price=True)
    report, destination = build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True)
    assert report["fitted"]
    assert report["counts"]["eligible"] == 100 and report["counts"]["selected"] == 99
    assert report["input_readiness_counts"] == {"missing:variant_id": 1}
    audit = [json.loads(line) for line in (destination / "input-readiness.jsonl").read_bytes().splitlines()]
    assert all(row["gold_model_eligible"] is True for row in audit)
    assert sum(row["selected"] for row in audit) == 99


def test_current_price_missing_ids_persists_actual_blockers(tmp_path):
    values = fixture_rows()
    for row in values:
        row["variant_id"] = None
    gold = fixture_gold(tmp_path / "fixture", values, current_price=True)
    report, destination = build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True)
    assert not report["fitted"]
    assert report["counts"]["eligible"] == 100
    assert report["missing_value_counts"]["target.current_price_per_100g_gbp"] == 0
    assert report["input_readiness_counts"] == {"missing:variant_id": 100}
    assert "no_complete_current_price_model_inputs" in report["blockers"]
    assert "explicit_source_price_window_required" not in report["blockers"]
    assert not (destination / "model.json").exists()


@pytest.mark.parametrize("valid_pin", [True, False])
def test_matching_gold_publication_is_bound_and_changed_pin_is_rejected(tmp_path, monkeypatch, valid_pin):
    import train_chocolate_retailer_median as trainer

    gold = fixture_gold(tmp_path / "fixture", current_price=True)
    fake_root = tmp_path / "repository"
    for name in (*trainer.IMPLEMENTATION, "uv.lock", "pyproject.toml"):
        path = fake_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((trainer.ROOT / name).read_bytes())
    storage_bytes = (gold / "manifest.json").read_bytes()
    storage = json.loads(storage_bytes)
    publication = {"dataset_version": storage["dataset_version"], "managed_files": storage["managed_files"],
                   "manifest_sha256": checksum(storage_bytes) if valid_pin else "0" * 64,
                   "repo_id": "CoralLeiCN/rgc-collections", "revision": "a" * 40,
                   "path": "gold/chocolate/uk/" + storage["dataset_version"]}
    reference = fake_root / "schemas/chocolate/gold-dataset.json"
    reference.parent.mkdir(parents=True)
    reference.write_text(json.dumps(publication) + "\n")
    monkeypatch.setattr(trainer, "ROOT", fake_root)
    if not valid_pin:
        with pytest.raises(ValueError, match="immutable publication pin"):
            trainer.build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True)
        assert not (tmp_path / "models").exists()
    else:
        report, destination = trainer.build_run(gold, tmp_path / "models", fixture=True, current_price_proxy=True)
        assert report["fitted"]
        assert (destination / "inputs/gold-dataset-reference.json").read_bytes() == reference.read_bytes()
        manifest = json.loads((destination / "manifest.json").read_bytes())
        assert manifest["gold_publication"]["revision"] == "a" * 40
        assert manifest["gold_publication"]["reference_sha256"] == checksum(reference.read_bytes())
