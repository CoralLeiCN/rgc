"""Verify matching, isolation, family balance, graph uncertainty and immutable runs."""

import copy
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from chocolate_gold import build_legacy_gold_dataset as build_gold_dataset
from chocolate_matched_retailer import (
    COMMON_POLICY,
    CURRENT_TARGET,
    EVIDENCE_FIELDS,
    build_matched_run,
    contemporaneous,
    context_from_gold,
    current_candidate_values,
    diagnostic_metrics,
    family_weights,
    fit_matched,
    frozen_split,
    overlap_graph,
    prepare_matches,
    reviewed_evidence,
    solve_component,
    verified_candidate_values,
    working_contract,
)
from chocolate_model import ModelContractError
from dataset_contracts import resolve_contract_root
from train_chocolate_model import CONTRACTS, checksum, json_bytes, read_json


def fixture_rows(families=20):
    result = []
    for f in range(families):
        for seller in ("Ocado", "Waitrose"):
            identifier = f"observation-{f}-{seller}"
            unit = round(math.exp(0.5 + f / 100 + (0.2 if seller == "Waitrose" else 0)), 8)
            predictors = {"identity.product_group": "bar", "identity.source_role": "retail",
                          "identity.brand": "Fixture Brand", "identity.retailer": seller,
                          "composition.chocolate_type": "dark", "composition.cocoa_percentage": 70.0,
                          "composition.nuts_presence": "absent", "dietary.vegan_claim": "present",
                          "certifications.fairtrade_claim": "present", "certifications.organic_claim": "absent",
                          "quantity.total_edible_weight_g": 80.0}
            result.append({"observation_id": identifier, "listing_id": "listing-" + identifier,
                           "variant_id": f"variant-{f}", "family_id": f"family-{f}", "source_role": "retail",
                           "comparable_group": "bar", "model_eligible": True, "exclusion_reasons": [],
                           "predictors": predictors, "target": {"regular_price_per_100g_gbp": unit,
                           "log_regular_price_per_100g_gbp": math.log(unit)}, "dataset_version": "silver-synthetic-matched",
                           "source_dataset_version": "raw-synthetic-matched", "schema_version": "chocolate-schema-1"})
    return result


def fixture_context(row):
    return {"cohort": COMMON_POLICY["cohort"], "formulation": row["variant_id"] + " recipe",
            "flavor": "plain", "edible_weight_g": 80.0, "pack_count": 1, "brand": "Fixture Brand",
            "chocolate_type": "dark", "observed_at": "2026-10-03T10:00:00+00:00",
            "observed_at_basis": "source_price_observation", "channel": "online",
            "location_scope": "same national online price scope", "membership": "public_non_member"}


def fixture_prices(observations):
    return [{**{n: r[n] for n in ("observation_id", "listing_id", "source_role", "dataset_version",
                                  "source_dataset_version", "schema_version")},
             "regular_price": r["target"]["regular_price_per_100g_gbp"] * 0.8,
             "displayed_price": 999, "reference_price": 888, "currency": "GBP",
             "tax_basis": "consumer_tax_included", "total_edible_weight_g": 80.0,
             "review_status": "reviewed", "quantity_status": "reviewed", "model_eligible": True,
             "available": True, "observed_at": fixture_context(r)["observed_at"]} for r in observations]


def numerical_rows(observations):
    return [{**r, "retailer": r["predictors"]["identity.retailer"], "match_context": fixture_context(r),
             "timestamp": fixture_context(r)["observed_at"]} for r in observations]


def fixture_snapshot(root, observations=None):
    """Explicitly synthetic evidence, never reused as real training data."""
    observations = fixture_rows() if observations is None else observations
    silver = root / "silver"
    silver.mkdir(parents=True)
    files = {n: (resolve_contract_root(offline=True) / n).read_bytes() for n in CONTRACTS}
    eligible = [r for r in observations if r["model_eligible"]]
    files["quality-report.json"] = json_bytes({"status": "complete_snapshot", "dataset_version": "silver-synthetic-matched",
                                             "counts": {"training_candidates": len(observations), "eligible_model_inputs": len(eligible)}})
    for name, records in (("training-candidates.jsonl", observations), ("model-inputs.jsonl", eligible),
                          ("prices.jsonl", fixture_prices(observations))):
        files[name] = b"".join(json_bytes(r).replace(b"\n", b" ") + b"\n" for r in records)
    manifest = {"manifest_format_version": "chocolate-silver-manifest-1", "schema_version": "chocolate-schema-1",
                "dataset_version": "silver-synthetic-matched", "source_dataset_version": "raw-synthetic-matched",
                "contract_sha256": {n: checksum(files[n]) for n in CONTRACTS},
                "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}}
    for name, data in files.items():
        (silver / name).write_bytes(data)
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    _, gold = build_gold_dataset(silver, root / "gold")
    contract = working_contract()
    contract["price_window"] = {"start": "2026-10-01T00:00:00Z", "end": "2026-10-05T00:00:00Z"}
    contract_path = root / "working-contract.json"
    contract_path.write_bytes(json_bytes(contract))
    evidence_dir = root / "review"
    evidence_dir.mkdir()
    review = {"format": "chocolate-exact-match-reviews-1", "synthetic_fixture": True,
              "gold_manifest_sha256": checksum((gold / "manifest.json").read_bytes()),
              "managed_files": {}, "reviews": {}}
    for row in observations:
        identifier = row["observation_id"]
        name = identifier + ".json"
        data = json_bytes(fixture_context(row))
        (evidence_dir / name).write_bytes(data)
        review["managed_files"][name] = {"sha256": checksum(data), "byte_length": len(data)}
        review["reviews"][identifier] = {"status": "reviewed", "reviewed_by": "synthetic_fixture_author",
            "fields": {f: {"value": fixture_context(row)[f], "evidence": [{"source_file": name, "pointer": "/" + f}]}
                       for f in EVIDENCE_FIELDS}}
    review_path = evidence_dir / "review.json"
    review_path.write_bytes(json_bytes(review))
    return gold, contract_path, review_path


def test_split_is_outcome_independent_and_keeps_whole_families():
    observations = fixture_rows()
    original = frozen_split(observations)
    changed = copy.deepcopy(observations)
    for row in changed:
        row["target"] = {"regular_price_per_100g_gbp": 99999}
        row["predictors"]["identity.brand"] = "A different brand"
    assert frozen_split(list(reversed(changed))) == original
    assert original["counts"] == {"fitting": 12, "calibration": 4, "testing": 4}
    assert len(original["assignments"]) == 20


def test_family_weighting_does_not_let_many_sizes_dominate():
    observations = numerical_rows(fixture_rows(2))
    # Family zero has three variants; family one only one. Contrasts differ.
    extra = []
    for row in observations[:2]:
        for i in (1, 2):
            extra.append({**row, "observation_id": row["observation_id"] + str(i), "variant_id": row["variant_id"] + str(i)})
    observations.extend(extra)
    for row in observations:
        effect = 0.2 if row["family_id"] == "family-0" else 0.8
        row["target"] = {"log_regular_price_per_100g_gbp": 1 + (effect if row["retailer"] == "Waitrose" else 0)}
    weights = family_weights(observations)
    for family in ("family-0", "family-1"):
        assert sum(w for w, r in zip(weights, observations) if r["family_id"] == family) == pytest.approx(1)
    model = solve_component(observations, ["Ocado", "Waitrose"])
    assert model["retailer_effects"]["Waitrose"] == pytest.approx(0.5)
    assert np.sum(family_weights(observations[:2])) == pytest.approx(1)


def test_fit_recovers_known_contrast_without_price_or_name_leakage():
    observations = numerical_rows(fixture_rows())
    model, uncertainty = fit_matched(observations, working_contract())
    contrast = model["contrasts"][0]
    assert contrast["log_unit_price_contrast"] == pytest.approx(0.2)
    assert contrast["percent_contrast"] == pytest.approx(100 * math.expm1(0.2))
    assert contrast["uncertainty_available"]
    assert len(uncertainty[0]["successful_log_contrasts"]) == 200
    assert max(abs(v - 0.2) for v in contrast["leave_one_family_out"].values()) < 1e-8
    for row in observations:
        row["predictors"]["name"] = "999 GBP"
        row["predictors"]["regular_price"] = -1000
    second, _ = fit_matched(observations, working_contract())
    assert second == model
    assert diagnostic_metrics(observations, model)["family_weighted_mae_gbp_per_pack"] < 1e-8


def test_graph_indirect_links_weak_bridges_and_disconnections():
    observations = numerical_rows(fixture_rows(2))
    for row in observations[2:]:
        row["retailer"] = "Waitrose" if row["retailer"] == "Ocado" else "Synthetic third retailer"
    graph = overlap_graph(observations)
    assert graph["weak_bridge_families"] == ["family-0", "family-1"]
    assert len(graph["components"]) == 1
    model, _ = fit_matched(observations, working_contract())
    indirect = next(c for c in model["contrasts"] if c["link"] == "indirect")
    assert indirect["bootstrap_disconnections"] > 0
    assert not indirect["uncertainty_available"]
    assert indirect["confidence_interval_log"] is None
    assert None in indirect["leave_one_family_out"].values()


def test_disconnected_components_have_separate_references():
    observations = numerical_rows(fixture_rows(4))
    for row in observations[4:]:
        row["retailer"] += " separate"
    model, _ = fit_matched(observations, working_contract())
    assert len(model["components"]) == 2
    assert len(model["contrasts"]) == 2
    assert all(c["link"] == "direct" for c in model["contrasts"])


@pytest.mark.parametrize("field,value", [("formulation", "other recipe"), ("flavor", "mint"),
                                         ("edible_weight_g", 90.0), ("brand", "Other brand")])
def test_family_matching_cannot_override_physical_evidence(field, value):
    observations = fixture_rows(2)
    reviews = {r["observation_id"]: fixture_context(r) for r in observations}
    reviews[observations[1]["observation_id"]][field] = value
    contract = working_contract()
    contract["price_window"] = {"start": "2026-10-01T00:00:00Z", "end": "2026-10-05T00:00:00Z"}
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    with pytest.raises(ModelContractError, match="disagrees|conflicting"):
        prepare_matches(observations, prices, reviews, contract)


@pytest.mark.parametrize("change,expected", [("time", "exceed_48"), ("location", "incomparable"), ("single", "no_other")])
def test_unmatched_dates_and_contexts_are_excluded(change, expected):
    observations = numerical_rows(fixture_rows(1))
    if change == "time":
        observations[1]["timestamp"] = (datetime(2026, 10, 3, tzinfo=timezone.utc) + timedelta(hours=59)).isoformat()
    elif change == "location":
        observations[1]["match_context"]["location_scope"] = "different location"
    else:
        observations.pop()
    selected, excluded = contemporaneous(observations)
    assert selected == []
    assert all(expected in reason for reason in excluded.values())


def test_immutable_run_is_fixture_labeled_and_heldout_predictions_unavailable(tmp_path):
    gold, contract, review = fixture_snapshot(tmp_path)
    report, destination = build_matched_run(gold, tmp_path / "models", contract, review)
    assert report["fixture_fitted"] and not report["real_data_fitted"]
    assert not report["release_ready"] and not report["calibrated"]
    predictions = [read_json(line) for line in (destination / "predictions.jsonl").read_bytes().splitlines()]
    assert all(p["in_domain"] == (p["partition"] == "fitting") for p in predictions)
    assert all(p["predicted_gbp_per_pack"] is None for p in predictions if p["partition"] != "fitting")
    manifest = read_json((destination / "manifest.json").read_bytes())
    for name, meta in manifest["managed_files"].items():
        assert checksum((destination / name).read_bytes()) == meta["sha256"]
    assert build_matched_run(gold, tmp_path / "models", contract, review)[1] == destination
    (destination / "model.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="immutable"):
        build_matched_run(gold, tmp_path / "models", contract, review)


def test_corrupt_evidence_and_gold_never_fit(tmp_path):
    gold, contract, review = fixture_snapshot(tmp_path)
    bundle = read_json(review.read_bytes())
    source_file = next(iter(bundle["managed_files"]))
    (review.parent / source_file).write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        reviewed_evidence(review)
    (gold / "model-inputs.parquet").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        build_matched_run(gold, tmp_path / "models", contract, review)
    assert not (tmp_path / "models").exists()


def test_missing_review_and_empty_eligible_rows_save_readiness(tmp_path):
    gold, contract, _ = fixture_snapshot(tmp_path, observations=[])
    report, destination = build_matched_run(gold, tmp_path / "models", contract)
    assert "no_complete_matched_model_inputs_in_verified_gold" in report["blockers"]
    assert not (destination / "model.json").exists()
    assert report["counts"]["training_rows"] == 0


@pytest.mark.parametrize("model_argument", [["--model-id", "matched_retailer"], ["--model-id=matched_retailer"]])
def test_integrated_cli_saves_matched_readiness(tmp_path, monkeypatch, model_argument):
    from train_chocolate_model import main

    gold, contract, _ = fixture_snapshot(tmp_path, observations=[])
    original = {str(path.relative_to(gold)): path.read_bytes() for path in gold.rglob("*") if path.is_file()}
    output = tmp_path / "models"
    monkeypatch.setattr("sys.argv", ["train_chocolate_model.py", *model_argument, "--gold-root", str(gold),
                                    "--working-contract", str(contract), "--group", "bar", "--output", str(output),
                                    "--verified-gold-candidates"])
    assert main() == 2
    report_path = next((output / "matched_retailer").glob("*/report.json"))
    report = read_json(report_path.read_bytes())
    assert report["model_id"] == "matched_retailer"
    assert not report["real_data_fitted"]
    assert not (report_path.parent / "model.json").exists()
    assert {str(path.relative_to(gold)): path.read_bytes() for path in gold.rglob("*") if path.is_file()} == original


@pytest.mark.parametrize("arguments", [
    ["--model-id", "experimental_ols", "--verified-gold-candidates"],
    ["--model-id", "matched_retailer", "--current-price-target", "--gold-root", "unused", "--working-contract", "unused"],
])
def test_integrated_cli_rejects_options_for_other_estimators(tmp_path, monkeypatch, arguments):
    from train_chocolate_model import main

    output = tmp_path / "models"
    monkeypatch.setattr("sys.argv", ["train_chocolate_model.py", *arguments, "--group", "bar", "--output", str(output)])
    assert main() == 1
    assert not output.exists()


def test_price_basis_and_forged_targets_are_rejected(tmp_path):
    observations = fixture_rows(3)
    observations[0]["target"]["log_regular_price_per_100g_gbp"] += 1
    gold, contract, review = fixture_snapshot(tmp_path, observations)
    with pytest.raises(ModelContractError, match="log target"):
        build_matched_run(gold, tmp_path / "models", contract, review)


def test_contract_cannot_change_admissible_features_or_train_comparator(tmp_path):
    gold, contract, review = fixture_snapshot(tmp_path)
    document = read_json(contract.read_bytes())
    document["common_policy"]["regression_core"].append("regular_price")
    contract.write_bytes(json_bytes(document))
    with pytest.raises(ModelContractError, match="common policy"):
        build_matched_run(gold, tmp_path / "models", contract, review)


@pytest.mark.parametrize("field,value", [("observed_at_basis", "cached_page_invocation"),
                                         ("membership", "members_only"), ("channel", "unknown")])
def test_invocation_dates_and_unresolved_context_do_not_enter_fit(field, value):
    observations = fixture_rows(2)
    reviews = {r["observation_id"]: fixture_context(r) for r in observations}
    for review in reviews.values():
        review[field] = value
    contract = working_contract()
    contract["price_window"] = {"start": "2026-10-01T00:00:00Z", "end": "2026-10-05T00:00:00Z"}
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    if field == "channel":
        with pytest.raises(ModelContractError, match="Unresolved"):
            prepare_matches(observations, prices, reviews, contract)
    else:
        accepted, domain = prepare_matches(observations, prices, reviews, contract)
        assert not accepted
        assert set(domain.values()) == {"unresolved_or_incomparable_price_context"}


def test_review_must_resolve_to_original_field_value(tmp_path):
    _, _, path = fixture_snapshot(tmp_path)
    bundle = read_json(path.read_bytes())
    review = next(iter(bundle["reviews"].values()))
    review["fields"]["formulation"]["value"] = "forged equal recipe"
    path.write_bytes(json_bytes(bundle))
    with pytest.raises(ModelContractError, match="differs from original"):
        reviewed_evidence(path)


def test_tax_fallback_is_rejected_even_with_reviewed_matching(tmp_path):
    from train_chocolate_model import validate_price_targets
    observations = fixture_rows(3)
    prices = fixture_prices(observations)
    prices[0]["tax_basis"] = "unknown"
    with pytest.raises(ModelContractError, match="tax-inclusive"):
        validate_price_targets(observations, prices)


def test_match_review_binds_gold_identity_and_output_rejects_links(tmp_path):
    gold, contract, path = fixture_snapshot(tmp_path)
    bundle = read_json(path.read_bytes())
    bundle["gold_manifest_sha256"] = "0" * 64
    path.write_bytes(json_bytes(bundle))
    with pytest.raises(ModelContractError, match="bind"):
        build_matched_run(gold, tmp_path / "models", contract, path)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "gold", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        build_matched_run(gold, link / "models", contract, path)


def test_task_verified_candidates_can_fit_without_rewriting_gold_flags(tmp_path):
    observations = fixture_rows()
    for row in observations:
        row["model_eligible"] = False
        row["exclusion_reasons"] = ["historical_unreviewed"]
        row["predictors"]["composition.cocoa_percentage"] = None
    gold, contract, review = fixture_snapshot(tmp_path, observations)
    before = {p.relative_to(gold).as_posix(): p.read_bytes() for p in gold.rglob("*") if p.is_file()}
    report, destination = build_matched_run(gold, tmp_path / "models", contract, review,
                                          verified_gold_candidates=True)
    assert report["fixture_fitted"]
    assert report["counts"]["training_rows"] == 40
    assert report["counts"]["candidates"] == 40
    assert report["counts"]["fitting_matched_rows"] == 24
    assert report["gold_verification_basis"] == "all_gold_rows"
    assert before == {p.relative_to(gold).as_posix(): p.read_bytes() for p in gold.rglob("*") if p.is_file()}
    original = [read_json(line) for line in (destination / "inputs/training-candidates.jsonl").read_bytes().splitlines()]
    assert all("model_eligible" not in r for r in original)
    assert all("exclusion_reasons" not in r for r in original)
    assert "--verified-gold-candidates" in read_json((destination / "reproduce.json").read_bytes())["argv"]


def test_verification_does_not_fill_null_target_variant_or_regular_price(tmp_path):
    observations = fixture_rows()
    for row in observations:
        row["model_eligible"] = False
        row["variant_id"] = None
        row["target"] = {"regular_price_per_100g_gbp": None, "log_regular_price_per_100g_gbp": None}
    prices = {p["observation_id"]: p for p in fixture_prices(fixture_rows())}
    for price in prices.values():
        price["regular_price"] = None
    selected, missing, domains = verified_candidate_values(observations, prices)
    assert selected == []
    assert missing["missing_regular_price"] == 40
    assert missing["missing_variant_id"] == 40
    assert missing["missing_regular_unit_price_target"] == 40
    assert len(domains) == 40


def test_gold_matching_context_uses_present_values_only():
    observations = fixture_rows()
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    assert context_from_gold(observations, prices) == {}
    for row in observations:
        prices[row["observation_id"]].update(fixture_context(row))
    assert context_from_gold(observations, prices) == {r["observation_id"]: fixture_context(r) for r in observations}


def test_verification_never_admits_conflicting_regular_target():
    observations = fixture_rows()
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    prices[observations[0]["observation_id"]]["regular_price"] = 1000
    with pytest.raises(ModelContractError, match="differs"):
        verified_candidate_values(observations, prices)


def test_promoted_gold_and_working_snapshot_contract_preserve_model_and_provenance(tmp_path):
    from chocolate_gold_eligibility import mark_gold_eligible
    observations = fixture_rows()
    for row in observations:
        row["model_eligible"] = False
        row["exclusion_reasons"] = ["original_review_status"]
    _, contract_path, review = fixture_snapshot(tmp_path, observations)
    # Storage uses a local copied design with a different model label. The
    # assigned estimator stays explicit and does not inherit that estimator.
    silver = tmp_path / "silver"
    copied = read_json((silver / "model-design.json").read_bytes())
    copied["model_design_version"] = "synthetic-storage-design-1"
    data = json_bytes(copied)
    (silver / "model-design.json").write_bytes(data)
    manifest = read_json((silver / "manifest.json").read_bytes())
    manifest["contract_sha256"]["model-design.json"] = checksum(data)
    manifest["managed_files"]["model-design.json"] = {"sha256": checksum(data), "byte_length": len(data)}
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    _, parent = build_gold_dataset(silver, tmp_path / "gold")
    _, promoted = mark_gold_eligible(parent, tmp_path / "gold", "Fixture User", "Promote all fixture candidates")
    bundle = read_json(review.read_bytes())
    bundle["gold_manifest_sha256"] = checksum((promoted / "manifest.json").read_bytes())
    review.write_bytes(json_bytes(bundle))
    with pytest.raises(ValueError, match="checksum"):
        build_matched_run(promoted, tmp_path / "models", contract_path, review, verified_gold_candidates=True)

    old = read_json(contract_path.read_bytes())
    config = working_contract(promoted)
    config["price_window"] = old["price_window"]
    contract_path.write_bytes(json_bytes(config))
    report, run = build_matched_run(promoted, tmp_path / "models", contract_path, review,
                                   verified_gold_candidates=True)
    assert report["counts"]["training_rows"] == 40
    assert report["counts"]["training_rows"] == 40
    assert report["counts"]["complete_required_inputs"] == 40
    assert report["fixture_fitted"]
    assert "eligibility_provenance" not in report
    artifact = read_json((run / "manifest.json").read_bytes())
    assert artifact["parent_gold_dataset_version"] == parent.name
    assert artifact["input_storage_model_design_version"] == "synthetic-storage-design-1"
    assert "eligibility_provenance" not in artifact
    model = read_json((run / "model.json").read_bytes())
    assert model["model_id"] == "matched_retailer"
    assert model["estimator"] == "weighted_exact_variant_plus_retailer_fixed_effects"
    config["input_gold_manifest_sha256"] = "0" * 64
    contract_path.write_bytes(json_bytes(config))
    with pytest.raises(ModelContractError, match="exact Gold"):
        build_matched_run(promoted, tmp_path / "models", contract_path, review, verified_gold_candidates=True)


def test_current_price_proxy_fits_promotional_unknown_tax_with_no_regular_values():
    observations = fixture_rows()
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    for row in observations:
        price = prices[row["observation_id"]]
        price["displayed_price"] = price["regular_price"]
        price["regular_price"] = None
        price["tax_basis"] = "unknown"
        price["promotion_status"] = "promotional"
        row["target"] = {"regular_price_per_100g_gbp": None, "log_regular_price_per_100g_gbp": None}
    before = copy.deepcopy(observations)
    selected, missing, domains, prepared, _ = current_candidate_values(observations, prices)
    assert observations == before
    assert not missing and not domains
    assert len(prepared) == 40
    enriched = numerical_rows(selected)
    model, _ = fit_matched(enriched, working_contract(current_price_proxy=True))
    assert model["contrasts"][0]["log_unit_price_contrast"] == pytest.approx(0.2)
    assert diagnostic_metrics(enriched, model)["family_weighted_mae_gbp_per_pack"] < 1e-8
    assert all(r["model_target"]["tax_basis"] == "unknown" for r in selected)
    assert all(r["model_target"]["promotion_status"] == "promotional" for r in selected)


def test_shared_current_price_keeps_missing_candidate_mass_and_identity():
    observations = fixture_rows(2)
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    for row in observations:
        row["variant_id"] = None
        row["predictors"]["quantity.total_edible_weight_g"] = None
        prices[row["observation_id"]]["displayed_price"] = 4.0
    selected, missing, _, prepared, _ = current_candidate_values(observations, prices)
    assert not selected
    assert missing == {"missing_variant_id": 4, "edible_weight_missing_or_invalid": 4}
    assert all(r["model_target"]["unit_gbp_per_100g"] is None for r in prepared.values())
    assert all(r["model_target"]["quantity_source"] is None for r in prepared.values())
    assert all(r["predictors"]["quantity.total_edible_weight_g"] is None for r in observations)


@pytest.mark.parametrize("field,value,reason", [("displayed_price", None, "current_price_missing_or_invalid"),
                                               ("total_edible_weight_g", None, "edible_weight_missing_or_invalid"),
                                               ("currency", "EUR", "current_price_currency_not_gbp")])
def test_current_proxy_still_rejects_missing_actual_prices_weights_and_currency(field, value, reason):
    observations = fixture_rows(1)
    prices = {p["observation_id"]: p for p in fixture_prices(observations)}
    observations[0]["predictors"]["quantity.total_edible_weight_g"] = None
    prices[observations[0]["observation_id"]][field] = value
    _, missing, _, _, _ = current_candidate_values(observations, prices)
    assert missing[reason] == 1


def test_current_proxy_run_persists_assumption_and_source_promotion_tax(tmp_path):
    gold, contract_path, review = fixture_snapshot(tmp_path)
    config = working_contract(gold, current_price_proxy=True)
    config["price_window"] = read_json(contract_path.read_bytes())["price_window"]
    contract_path.write_bytes(json_bytes(config))
    report, run = build_matched_run(gold, tmp_path / "models", contract_path, review,
                                   verified_gold_candidates=True)
    assert report["fixture_fitted"]
    assert report["price_target_policy"]["price_basis_contract_version"] == CURRENT_TARGET["price_basis_contract_version"]
    assert report["target_contract_reference"]["revision"] == "d743cb8dbca37f5241cccd444a16165523304f6c"
    assert report["counts"]["normalized_current_targets"] == 40
    assert CURRENT_TARGET["assumption"] in report["limitations"]
    prepared = [read_json(line) for line in (run / "prepared-current-inputs.jsonl").read_bytes().splitlines()]
    assert all(r["model_target"]["pack_price_gbp"] == 999 for r in prepared)
    assert all(r["target"]["current_price_per_100g_gbp"] == r["model_target"]["unit_gbp_per_100g"] for r in prepared)
    assert all(r["target"]["regular_price_per_100g_gbp"] == r["target"]["current_price_per_100g_gbp"] for r in prepared)
    assert (run / "inputs/current-price-contract/model-design.json").is_file()
    assert read_json((run / "preprocessing.json").read_bytes())["transform"] == "log_current_gbp_per_100g"
