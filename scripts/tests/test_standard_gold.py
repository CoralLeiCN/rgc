"""Canonical Gold preparation consumes standard Silver without model policy upstream."""

import json
from copy import deepcopy

import pytest
from category_processing.archive import json_bytes
from category_processing.silver_contracts import validator
from test_standard_silver import fact
from test_standard_silver import study as study


def test_gold_owns_target_group_and_eligibility_and_parquet_is_verified(study):
    from chocolate_gold import build_gold_dataset, verified_gold
    profile = json.loads((study["profile"] / "profile.json").read_bytes())
    profile["attributes"]["quantity.total_edible_weight_g"] = {"type": "number", "unit": "g", "scope": "product"}
    profile["attribute_count"] += 1
    (study["profile"] / "profile.json").write_bytes(json_bytes(profile))
    (study["profile"] / "product.schema.json").write_bytes(json_bytes(validator(profile)))
    recipe = json.loads((study["profile"] / "pipeline.json").read_bytes())
    recipe["fields"].append({"attribute": "quantity.total_edible_weight_g", "pointer": "/raw_record/information/weight"})
    recipe["price"] = {"amount_pointer": "/raw_record/information/price", "price_unit": "major", "currency": "GBP",
                       "available_pointer": "/raw_record/information/available", "observed_at_pointer": "/raw_record/information/time"}
    recipe["source_roles"] = {"shop": {"source_role": "retail", "retailer": "Fixture Shop"}}
    (study["profile"] / "pipeline.json").write_bytes(json_bytes(recipe))
    raw = deepcopy(study["raw"])
    raw["identity"]["name"] = "Fixture Chocolate Bar"
    raw["information"].update(weight=100, price=4, available=True, time="2026-10-04T12:00:00Z")
    study["collect"](raw)
    root, _ = study["build"]()
    source = fact(root, "identity.name", None)
    relationships = {"format_version": "category-gold-relationships-1", "assignments": [{
        "subject_id": source["subject_id"], "family_id": "family-1", "variant_id": "variant-1", "name_guard": raw["identity"]["name"],
        "source": source["source"], "reviewed_by": "Fixture human", "reason": "Source confirms this recipe and unit."}]}
    design = {"schema_version": "original-study", "model_design_version": "fixture-design-1",
              "predictors": {"quantity.total_edible_weight_g": {"type": "numeric", "minimum": 0},
                             "identity.product_group": {"type": "categorical", "allowed_values": ["bar"]}},
              "target": {"price_basis_contract_version": "current-consumer-price-1", "quantity_attribute": "quantity.total_edible_weight_g",
                         "price_basis": "current_displayed", "tax_basis": "as_displayed", "promotion_basis": "as_displayed", "fallback_policy": "reject",
                         "base_quantity": 100, "currency": "GBP", "stored_target_fields": ["current_price_per_100g_gbp", "log_current_price_per_100g_gbp"]}}
    path = study["tmp"] / "model-design.json"
    path.write_bytes(json_bytes(design))
    report, gold = build_gold_dataset(root, study["tmp"] / "gold", model_design=path, relationships=relationships)
    assert report["counts"] == {"training_candidates": 1, "eligible_model_inputs": 1}
    context, _, inputs = verified_gold(gold)
    assert context["preparation_layer"] == "gold"
    rows = [json.loads(line) for line in inputs["model-inputs.jsonl"].splitlines()]
    assert rows[0]["target"]["current_price_per_100g_gbp"] == 4
    assert rows[0]["comparable_group"] == "bar"
    assert not (root / "model-design.json").exists()
    assert not (root / "model-inputs.jsonl").exists()
    reloaded, second = build_gold_dataset(root, study["tmp"] / "gold-from-contract",
                                         model_design=gold / "preparation/model-design.json", relationships=relationships)
    assert reloaded["counts"] == report["counts"]
    assert verified_gold(second)[2]["model-inputs.jsonl"] == inputs["model-inputs.jsonl"]
    from category_processing.gold_preparation import selected_value
    from category_processing.silver_snapshot import read_rows
    accepted = {**design, "accepted_silver_methods": ["reviewed"]}
    current = [row for row in read_rows(root / "facts.jsonl") if row["is_current"] and row["subject_kind"] == "listing"]
    assert selected_value(current, "quantity.total_edible_weight_g", design) == 100
    assert selected_value(current, "quantity.total_edible_weight_g", accepted) is None
    (gold / "model-inputs.parquet").write_bytes(b"invalid")
    with pytest.raises(ValueError, match="checksum"):
        verified_gold(gold)


@pytest.mark.parametrize("current_price_flag", [False, True])
def test_standard_gold_ols_preserves_population_source_quality_and_price_assumption(study, current_price_flag):
    from chocolate_gold import build_gold_dataset
    from dataset_contracts import resolve_current_price_contract_root
    from train_chocolate_model import build_model_run

    design_path = resolve_current_price_contract_root(offline=True) / "model-design.json"
    design = json.loads(design_path.read_bytes())
    values = {"identity.brand": "Fixture Brand", "identity.retailer": "Fixture Seller",
              "composition.chocolate_type": "dark", "composition.cocoa_percentage": 70,
              "composition.nuts_presence": "absent", "dietary.vegan_claim": "present",
              "certifications.fairtrade_claim": "present", "certifications.organic_claim": "present",
              "quantity.total_edible_weight_g": 100}
    profile = json.loads((study["profile"] / "profile.json").read_bytes())
    recipe = json.loads((study["profile"] / "pipeline.json").read_bytes())
    for name in values:
        definition = design["predictors"][name]
        profile["attributes"][name] = {**definition, "type": "number" if definition["type"] == "numeric" else "string", "scope": "product"}
        recipe["fields"].append({"attribute": name, "pointer": "/raw_record/information/" + name})
    profile["attribute_count"] = len(profile["attributes"])
    recipe["source_roles"] = {"shop": {"source_role": "retail", "retailer": "Fixture Seller"}}
    recipe["price"] = {"amount_pointer": "/raw_record/information/price", "price_unit": "major", "currency": "GBP",
                       "available_pointer": "/raw_record/information/available", "observed_at_pointer": "/raw_record/information/time"}
    for name, value in (("profile.json", profile), ("pipeline.json", recipe), ("product.schema.json", validator(profile))):
        (study["profile"] / name).write_bytes(json_bytes(value))
    raw = deepcopy(study["raw"])
    raw["identity"]["name"] = "Fixture Chocolate Bar"
    raw["information"].update(values, price=4, available=True, time="2026-10-04T12:00:00Z")
    other = deepcopy(raw)
    other.update(product_id="other-listing", source_url="https://shop.example/item/456")
    other["identity"].update(source_product_id="456", source_variant_id="v2")
    study["collect"](raw, other)
    root, _ = study["build"]()
    source = fact(root, "identity.name", None)
    relationships = {"format_version": "category-gold-relationships-1", "assignments": [{
        "subject_id": source["subject_id"], "family_id": "family-1", "variant_id": "variant-1", "name_guard": raw["identity"]["name"],
        "source": source["source"], "reviewed_by": "Fixture human", "reason": "Source confirms this recipe and unit."}]}
    _, gold = build_gold_dataset(root, study["tmp"] / "gold", model_design=design_path, relationships=relationships)
    report, run = build_model_run(None, study["tmp"] / "models", "bar", gold_root=gold, current_price_target=current_price_flag)
    assert report["blockers"] == ["fewer_than_two_reviewed_families_in_group"]
    assert report["population_selection"] == "gold_eligible_inputs"
    assert report["counts"]["training_candidates"] == 2
    assert report["counts"]["eligible_model_inputs"] == report["counts"]["selected_observations"] == 1
    assert report["exclusion_counts"] == {"product_family_unresolved": 1}
    assert report["selected_group_exclusion_counts"] == report["exclusion_counts"]
    assert report["price_target_policy"]["price_basis_contract_version"] == "current-consumer-price-1"
    assert any("regular-price proxy" in value for value in report["limitations"])
    assert (run / "inputs/silver-manifest.json").read_bytes() == (root / "manifest.json").read_bytes()
    assert (run / "inputs/quality-report.json").read_bytes() == (root / "quality-report.json").read_bytes()
    assert (run / "inputs/current-price-target-contract.json").read_bytes() == (gold / "preparation/model-design.json").read_bytes()
    assert not (run / "model.json").exists()
