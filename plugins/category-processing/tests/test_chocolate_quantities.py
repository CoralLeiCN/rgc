"""Quantity attribution across selected offers and shared product descriptions."""

from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.adapters import extract_capture
from category_processing.archive import json_bytes, sha256
from category_processing.silver_chocolate import refine_quantities
from category_processing.silver_contracts import FORMAT, validator
from category_processing.silver_snapshot import read_rows
from category_processing.standard_silver import build_standard_silver
from fixture_archive import import_document

MASS_FIELD = "quantity.total_edible_weight_g"
COUNT_FIELD = "quantity.pack_count"
UNIT_FIELD = "quantity.unit_edible_weight_g"
RECIPE = {"adapter": "chocolate", "quantity": {"attribute": MASS_FIELD, "unit": "g"},
          "derive_comparison_group": False, "pack_count_attribute": COUNT_FIELD}


def nomo_capture(count):
    variants = [{"id": 55021781975419, "title": "38g / 12 Bars", "option1": "38g", "option2": "12 Bars",
                 "price": "20.00", "grams": 500},
                {"id": 55021782008187, "title": "38g / 24 Bars", "option1": "38g", "option2": "24 Bars",
                 "price": "36.00", "grams": 990}]
    selected = deepcopy(variants[0 if count == 12 else 1])
    return {"raw_record": {"source_key": "nomo", "product_id": "nomo-" + str(selected["id"]),
                           "source_url": "https://nomo.example/caramel?variant=" + str(selected["id"]),
                           "identity": {"name": "Caramel Chocolate Bars — 38g / " + str(count) + " Bars",
                                        "source_product_id": "5141180383368", "source_variant_id": str(selected["id"])},
                           "information": {"body_html": "<p>Weight : 38g X 24 bars</p>", "variants": variants,
                                           "selected_variant": selected, "source_price_currency": "GBP"}}}


def values(result, field):
    return {item["value"] for item in result["attributes"] if item["attribute"] == field}


@pytest.mark.parametrize("count", [12, 24])
def test_shared_body_is_attributed_to_its_variant(count):
    capture = nomo_capture(count)
    before = deepcopy(capture)
    extracted = extract_capture(capture, RECIPE)
    prior_rejection = {"pointer": "/raw_record", "reason": "prior_diagnostic"}
    extracted["rejected_candidates"] = [prior_rejection]
    result = refine_quantities(capture, extracted, RECIPE)
    assert values(result, COUNT_FIELD) == {count}
    assert values(result, MASS_FIELD) == {count * 38}
    assert values(result, UNIT_FIELD) == {38}
    assert {item["value"] for item in result["prices"][0]["quantity_candidates"]} == {count * 38}
    alternate = [item for item in result["rejected_candidates"] if item["reason"] == "quantity_refers_to_other_variant"]
    assert {item["attribute"] for item in alternate} == ({MASS_FIELD, COUNT_FIELD, UNIT_FIELD} if count == 12 else set())
    assert all(item["source_text"] == "Weight : 38g X 24 bars" for item in alternate)
    assert prior_rejection in result["rejected_candidates"]
    assert capture == before


@pytest.mark.parametrize("problem", ["missing_id", "wrong_id", "missing_variants", "duplicate_id", "different_title", "different_name"])
def test_uncertain_variant_identity_keeps_the_quantity_disagreement(problem):
    capture = nomo_capture(12)
    identity = capture["raw_record"]["identity"]
    information = capture["raw_record"]["information"]
    if problem == "missing_id":
        del identity["source_variant_id"]
    elif problem == "wrong_id":
        identity["source_variant_id"] = "unmatched"
    elif problem == "missing_variants":
        del information["variants"]
    elif problem == "duplicate_id":
        information["variants"].append(deepcopy(information["variants"][0]))
    elif problem == "different_title":
        information["selected_variant"]["title"] = "40g / 12 Bars"
    else:
        identity["name"] = "Caramel Chocolate Bars — 38g / 6 Bars"
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert 24 in values(result, COUNT_FIELD)
    assert len(values(result, COUNT_FIELD)) > 1
    assert 912 in values(result, MASS_FIELD)
    assert not any(item["reason"] == "quantity_refers_to_other_variant" for item in result["rejected_candidates"])


def test_matching_count_with_different_unit_mass_remains_a_conflict():
    capture = nomo_capture(12)
    capture["raw_record"]["information"]["body_html"] = "<p>Weight: 40g X 12 bars</p>"
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert values(result, COUNT_FIELD) == {12}
    assert values(result, MASS_FIELD) == {456, 480}
    assert values(result, UNIT_FIELD) == {38, 40}


def test_selected_title_supplies_quantity_when_listing_name_has_no_size():
    capture = nomo_capture(12)
    capture["raw_record"]["identity"]["name"] = "Caramel Chocolate Bars"
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert values(result, MASS_FIELD) == {456}
    assert values(result, COUNT_FIELD) == {12}
    assert all(item["pointer"] == "/raw_record/information/selected_variant/title"
               for item in result["attributes"] if item["attribute"] == MASS_FIELD)


def test_body_keeps_unclassified_nutrient_mass_diagnostic():
    capture = nomo_capture(24)
    capture["raw_record"]["information"]["body_html"] += "<p>Nutrition</p><p>Fat</p><p>31.9g</p>"
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert values(result, MASS_FIELD) == {912}
    assert any(item["value"] == 31.9 and item["reason"] == "mass_requires_explicit_pack_or_unit_basis"
               for item in result["rejected_candidates"])


def test_decimal_pack_mass_does_not_create_a_rounding_conflict():
    capture = nomo_capture(12)
    capture["raw_record"]["identity"]["name"] = "KitKat 12 x 20.7g"
    capture["raw_record"]["information"] = {}
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert values(result, MASS_FIELD) == {248.4}
    assert values(result, UNIT_FIELD) == {20.7}


def test_lolly_pack_and_contradictory_each_mass_have_distinct_bases():
    capture = nomo_capture(12)
    capture["raw_record"]["identity"]["name"] = "Kids Lollies — 12g / 72 lollies"
    capture["raw_record"]["information"]["selected_variant"]["title"] = "12g / 72 lollies"
    capture["raw_record"]["information"]["body_html"] = "<p>Each 11g lolly is wrapped.</p><p>Weight: 12g X 72 lollies</p>"
    result = refine_quantities(capture, extract_capture(capture, RECIPE), RECIPE)
    assert values(result, MASS_FIELD) == {864}
    assert values(result, COUNT_FIELD) == {72}
    assert values(result, UNIT_FIELD) == {11, 12}


def test_silver_build_keeps_both_seller_variants_and_resolves_quantities(tmp_path):
    attributes = {MASS_FIELD: {"type": "number", "unit": "g", "scope": "product"},
                  COUNT_FIELD: {"type": "integer", "unit": "count", "scope": "product"},
                  UNIT_FIELD: {"type": "number", "unit": "g", "scope": "selling_unit", "basis": "per_unit"}}
    profile = {"schema_version": "test-chocolate-1", "record_format_version": FORMAT, "category": "chocolate",
               "market": "uk", "attribute_count": len(attributes), "attributes": attributes}
    recipe = {**RECIPE, "schema_version": profile["schema_version"], "pipeline_version": "test-1",
              "category": "chocolate", "market": "uk"}
    profile_root = tmp_path / "profile"
    profile_root.mkdir()
    for name, document in (("profile.json", profile), ("pipeline.json", recipe),
                           ("source-mappings.json", {"schema_version": profile["schema_version"], "mapping_version": "test-1", "aliases": {}}),
                           ("product.schema.json", validator(profile))):
        (profile_root / name).write_bytes(json_bytes(document))
    raw = tmp_path / "bronze"
    import_document({"study": {"category": "chocolate", "market": "uk"},
                     "products": [nomo_capture(count)["raw_record"] for count in (12, 24)]}, raw)
    before = {str(path): sha256(path) for path in raw.rglob("*") if path.is_file()}
    report = build_standard_silver(raw, tmp_path / "silver", profile_root, state_db=tmp_path / "state.sqlite")
    root = Path(report["output"])
    products = read_rows(root / "products.jsonl")
    assert len(products) == 2
    assert len({row["subject_id"] for row in products}) == 2
    facts = [row for row in read_rows(root / "facts.jsonl") if row["is_current"]]
    for count in (12, 24):
        pack_fact = next(row for row in facts if row["field"] == COUNT_FIELD and row["result"] == count)
        mass_fact = next(row for row in facts if row["field"] == MASS_FIELD and row["subject_id"] == pack_fact["subject_id"])
        assert mass_fact["result"] == count * 38
        assert mass_fact["method"] == "parsed"
    assert any(row["reason"] == "quantity_refers_to_other_variant" for row in read_rows(root / "review-queue.jsonl"))
    assert before == {str(path): sha256(path) for path in raw.rglob("*") if path.is_file()}
