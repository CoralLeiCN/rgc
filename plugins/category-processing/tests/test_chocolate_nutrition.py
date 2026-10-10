"""Nutrition evidence must retain its column, units, qualifiers and subject."""

from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.archive import json_bytes
from category_processing.chocolate_nutrition import extract_nutrition
from category_processing.silver_contracts import (
    FORMAT,
    load_silver_contracts,
    validator,
)
from category_processing.silver_snapshot import read_rows, verified_snapshot
from category_processing.standard_silver import build_standard_silver
from fixture_archive import import_document


@pytest.fixture
def recipe():
    labels = {
        "energy": {"energy": True},
        "energy kj": {"energy": True},
        "energy kcal": {"energy": True},
        "fat": {"attribute": "nutrition.fat_g_per_100g"},
        "salt": {"attribute": "nutrition.salt_g_per_100g"},
        "total carbohydrate": {"attribute": "nutrition.carbohydrate_g_per_100g"},
        "available carbohydrate": {"attribute": "nutrition.available_carbohydrate_g_per_100g"},
        "of which polyols": {"attribute": "nutrition.polyols_g_per_100g"},
        "sodium": {"attribute": "nutrition.sodium_mg_per_100g"},
    }
    return {"nutrition_tables": {"labels": labels,
            "energy": {"kj": "nutrition.energy_kj_per_100g", "kcal": "nutrition.energy_kcal_per_100g"},
            "sections": [{"pointer": "/raw_record/information/body_html", "format": "text"}]}}


def capture(text):
    return {"raw_record": {"source_key": "shop", "identity": {"source_product_id": "1"},
                           "information": {"body_html": text}}}


def numbers(attributes):
    return {item["attribute"]: item for item in attributes if item["attribute"] != "nutrition.source_text"}


def test_cached_columns_and_unlabelled_energy_continuation(recipe):
    raw = capture("L91: 32g = 1 bar | Per 100g | Per 32g\n"
                  "L92: Energy | 2293kJ | 733kJ\nL93: 550kcal | 176kcal\n"
                  "L94: Fat | 34g | 11g\nL95: Salt | 0.29g | 0.09g")
    original = deepcopy(raw)
    attributes, issues, handled = extract_nutrition(raw, recipe)
    values = numbers(attributes)
    assert {name: item["value"] for name, item in values.items()} == {
        "nutrition.energy_kj_per_100g": 2293, "nutrition.energy_kcal_per_100g": 550,
        "nutrition.fat_g_per_100g": 34, "nutrition.salt_g_per_100g": 0.29}
    assert all(item["basis"] == "per_100g" for item in values.values())
    assert issues == [] and handled == ["/raw_record/information/body_html"]
    assert raw == original


def test_html_blank_columns_and_available_total_carbohydrate_are_distinct(recipe):
    text = "<table><tr><th>Typical values</th><th>per 100g</th><th></th><th>29g</th><th>% 29g</th></tr>"
    text += "<tr><td>Available Carbohydrate</td><td>59g</td><td></td><td>17g</td><td>6%</td></tr>"
    text += "<tr><td>Total Carbohydrate</td><td>61g</td><td></td><td>17.6g</td><td>6%</td></tr>"
    text += "<tr><td>Sodium</td><td>141mg</td><td></td><td>41.1mg</td><td></td></tr></table>"
    values = numbers(extract_nutrition(capture(text), recipe)[0])
    assert values["nutrition.available_carbohydrate_g_per_100g"]["value"] == 59
    assert values["nutrition.carbohydrate_g_per_100g"]["value"] == 61
    assert values["nutrition.sodium_mg_per_100g"]["value"] == 141
    assert values["nutrition.sodium_mg_per_100g"]["unit"] == "mg_per_100g"


def test_zero_and_inequality_are_not_absence_or_exact_values(recipe):
    values = numbers(extract_nutrition(capture("Typical values | Per 100g\n"
                     "of which polyols (g) | 0\nSalt (g) | <0.5g\nFat (g) | ~30g"), recipe)[0])
    assert values["nutrition.polyols_g_per_100g"]["value"] == 0
    assert values["nutrition.salt_g_per_100g"]["qualifier"] == "upper_bound_exclusive"
    assert values["nutrition.salt_g_per_100g"]["value"] == 0.5
    assert values["nutrition.fat_g_per_100g"]["qualifier"] == "approximate"


@pytest.mark.parametrize("text", [
    "Typical values | Per 25g\nFat | 8g",
    "Typical values | Per 100g prepared\nFat | 8g",
    "Typical values | Per 100g | Per 100g\nFat | 8g | 30g",
    "Creamy bar | Per 100g\nFat | 8g\nCaramel bar | Per 100g\nFat | 30g",
])
def test_unresolved_basis_and_component_panels_produce_no_product_values(text, recipe):
    attributes, _, handled = extract_nutrition(capture(text), recipe)
    assert attributes == [] and handled == []


def test_missing_units_ranges_and_unmapped_labels_remain_diagnostics(recipe):
    attributes, issues, _ = extract_nutrition(capture("Typical values | Per 100g\n"
                             "Fat | 27.00\nSalt (g) | 0.1–0.2g\nNiacin (mg) | 5mg"), recipe)
    assert attributes == []
    assert {item["reason"] for item in issues} == {
        "nutrition_value_or_unit_unresolved", "nutrition_label_requires_mapping"}


def test_conflicting_source_attribution_and_recipe_opt_in(recipe):
    raw = capture("Typical values | Per 100g\nFat | 34g")
    recipe["nutrition_tables"]["excluded_source_products"] = {"shop": ["1"]}
    attributes, issues, handled = extract_nutrition(raw, recipe)
    assert attributes == [] and handled == []
    assert issues[0]["reason"] == "nutrition_source_product_attribution_unresolved"
    assert extract_nutrition(raw, {}) == ([], [], [])


@pytest.mark.parametrize("second", ["0.2g", "<0.23g"])
def test_internal_panel_disagreement_cannot_bypass_subject_guard(second, recipe):
    recipe["nutrition_tables"]["require_single_product_panel"] = True
    raw = capture("Typical values | Per 100g\nFat | 34g\nSalt | 0.23g\nSalt | " + second)
    before = deepcopy(raw)
    attributes, issues, handled = extract_nutrition(raw, recipe)
    assert attributes == [] and handled == []
    assert {item["reason"] for item in issues} == {"nutrition_inconsistent_rows_within_panel"}
    assert raw == before


def test_identical_repeated_rows_are_compatible(recipe):
    recipe["nutrition_tables"]["require_single_product_panel"] = True
    values = numbers(extract_nutrition(capture("Typical values | Per 100g\nSalt | 0.23g\nSalt | 0.23g"), recipe)[0])
    assert values["nutrition.salt_g_per_100g"]["value"] == 0.23


def test_separate_component_sections_cannot_become_product_values(recipe):
    config = recipe["nutrition_tables"]
    config["require_single_product_panel"] = True
    config["sections"] = [{"pointer": "/raw_record/information/panels", "format": "section_array", "text_key": "text"}]
    raw = capture("")
    raw["raw_record"]["information"]["panels"] = [
        {"text": "Typical values | Per 100g\nFat | 34g"},
        {"text": "Typical values | Per 100g\nFat | 18g"}]
    attributes, issues, _ = extract_nutrition(raw, recipe)
    assert attributes == []
    assert {item["reason"] for item in issues} == {"nutrition_requires_component_or_conflict_resolution"}
    # Repeated representations of the same declared panel retain both references.
    raw["raw_record"]["information"]["panels"][1]["text"] = raw["raw_record"]["information"]["panels"][0]["text"]
    attributes, issues, _ = extract_nutrition(raw, recipe)
    assert numbers(attributes)["nutrition.fat_g_per_100g"]["value"] == 34
    assert issues == []


def test_explicit_distinct_component_ids_need_subjects_even_when_values_match(recipe):
    recipe["nutrition_tables"]["require_single_product_panel"] = True
    table = "<table><tr><th>Typical values</th><th>per 100g</th></tr><tr><td>Fat</td><td>34g</td></tr></table>"
    raw = capture('<div class="gtin_number-1234567890123">' + table + '</div>' +
                  '<div class="gtin_number-9876543210987">' + table + '</div>')
    attributes, issues, _ = extract_nutrition(raw, recipe)
    assert attributes == []
    assert issues[0]["reason"] == "nutrition_requires_component_or_conflict_resolution"


@pytest.fixture
def profile(tmp_path, recipe):
    definitions = {name: {"type": "number", "unit": unit, "basis": "per_100g", "scope": "product", "minimum": 0}
                   for name, unit in [("nutrition.energy_kj_per_100g", "kJ_per_100g"),
                                      ("nutrition.energy_kcal_per_100g", "kcal_per_100g"),
                                      ("nutrition.fat_g_per_100g", "g_per_100g"),
                                      ("nutrition.salt_g_per_100g", "g_per_100g"),
                                      ("nutrition.carbohydrate_g_per_100g", "g_per_100g"),
                                      ("nutrition.available_carbohydrate_g_per_100g", "g_per_100g"),
                                      ("nutrition.polyols_g_per_100g", "g_per_100g"),
                                      ("nutrition.sodium_mg_per_100g", "mg_per_100g")]}
    definitions["nutrition.source_text"] = {"type": "string", "unit": None, "scope": "product", "standardization_rule": "source_section"}
    catalog = {"schema_version": "nutrition-test-1", "record_format_version": FORMAT, "category": "test",
               "market": "uk", "attribute_count": len(definitions), "attributes": definitions}
    pipeline = {**recipe, "adapter": "chocolate", "category": "test", "market": "uk",
                "schema_version": "nutrition-test-1", "pipeline_version": "nutrition-test-parser-1"}
    mappings = {"schema_version": "nutrition-test-1", "mapping_version": "nutrition-test-mapping-1",
                "nutrition_label_aliases": deepcopy(recipe["nutrition_tables"]["labels"])}
    root = tmp_path / "profile"
    root.mkdir()
    for name, document in [("profile.json", catalog), ("pipeline.json", pipeline),
                           ("source-mappings.json", mappings), ("product.schema.json", validator(catalog))]:
        (root / name).write_bytes(json_bytes(document))
    return root


def test_new_field_contract_builds_typed_silver_and_preserves_missing_units(tmp_path, profile):
    raw = capture("Typical values | Per 100g | Per 25g\n"
                  "of which polyols (g) | 0 | 0\nSodium (mg) | 141 | 35\nFat | 27 | 7")["raw_record"]
    raw.update(product_id="nutrition-item", source_url="https://shop.example/item/1")
    raw["identity"]["name"] = "Chocolate"
    archive = tmp_path / "bronze"
    import_document({"study": {"category": "test", "market": "uk"}, "products": [raw]}, archive)
    result = build_standard_silver(archive, tmp_path / "silver", profile, state_db=tmp_path / "state.sqlite")
    root, _ = verified_snapshot(Path(result["output"]))
    product = read_rows(root / "products.jsonl")[0]
    assert product["nutrition_polyols_g_per_100g"] == 0
    assert product["nutrition_sodium_mg_per_100g"] == 141
    assert product["nutrition_fat_g_per_100g"] is None
    assert product["nutrition_sodium_mg_per_100g.method"] == "parsed"
    assert product["nutrition_sodium_mg_per_100g.source"][0]["pointer"] == "/raw_record/information/body_html"
    assert any(row["reason"] == "nutrition_value_or_unit_unresolved" for row in read_rows(root / "review-queue.jsonl"))


def test_alias_contract_drift_is_rejected_before_processing(profile):
    import json
    path = profile / "source-mappings.json"
    mappings = json.loads(path.read_bytes())
    mappings["nutrition_label_aliases"]["sodium"] = {"attribute": "nutrition.salt_g_per_100g"}
    path.write_bytes(json_bytes(mappings))
    with pytest.raises(ValueError, match="Nutrition labels must agree"):
        load_silver_contracts(profile)


def test_energy_ranges_and_embedded_numbers_remain_unresolved(recipe):
    for cell in ("100-200kJ", "100 to 200kJ", "about 200kJ", "200kJ (10% RI)"):
        attributes, issues, _ = extract_nutrition(capture("Typical values | Per 100g\nEnergy | " + cell), recipe)
        assert numbers(attributes) == {}
        assert issues[0]["reason"] == "nutrition_value_or_unit_unresolved"
    values = numbers(extract_nutrition(capture("Typical values | Per 100g\nEnergy | 2000kJ / 480kcal"), recipe)[0])
    assert values["nutrition.energy_kj_per_100g"]["value"] == 2000
    assert values["nutrition.energy_kcal_per_100g"]["value"] == 480


def test_nutrition_panel_is_retained_beside_unrelated_html_tables(recipe):
    other = '<table><tr><td>Pack</td><td>12 bars</td></tr></table>'
    panel = '<table><tr><th>Typical values</th><th>Per 100g</th></tr><tr><td>Fat</td><td>30g</td></tr></table>'
    attributes, issues, handled = extract_nutrition(capture(other + panel), recipe)
    assert numbers(attributes)['nutrition.fat_g_per_100g']['value'] == 30
    assert next(item['value'] for item in attributes if item['attribute'] == 'nutrition.source_text') == panel
    assert issues == [] and handled == ['/raw_record/information/body_html']


def test_parenthesized_labels_and_stacked_serving_basis_keep_meaning(recipe):
    recipe['nutrition_tables']['labels']['of which saturates'] = {'attribute': 'nutrition.saturates_g_per_100g'}
    recipe['nutrition_tables']['labels']['of which sugars'] = {'attribute': 'nutrition.sugars_g_per_100g'}
    raw = capture(' | Per 100g:\nFat g | 41.5\n(of which saturates) g | 26.6\n'
                  '(of which sugars) g | 28.5\n | Per 1/2 pack:\nFat g | 14.6\n'
                  '(of which saturates) g | 9.4\n(of which sugars) g | 10')
    attributes, issues, _ = extract_nutrition(raw, recipe)
    assert {name: value['value'] for name, value in numbers(attributes).items()} == {
        'nutrition.fat_g_per_100g': 41.5, 'nutrition.saturates_g_per_100g': 26.6, 'nutrition.sugars_g_per_100g': 28.5}
    assert issues == []


def test_stacked_32g_serving_header_ends_per_100g_panel(recipe):
    raw = capture('Typical Values | Per 100g\nFat | 30g\nTypical Values | Per 32g\nFat | 9.6g')
    values = numbers(extract_nutrition(raw, recipe)[0])
    assert values['nutrition.fat_g_per_100g']['value'] == 30


def test_mass_and_energy_units_cannot_supply_each_others_fields(recipe):
    attributes, issues, _ = extract_nutrition(capture('Typical values | Per 100g\nFat (g) | 30kcal\nEnergy (kJ) | 500g'), recipe)
    assert numbers(attributes) == {}
    assert [item['reason'] for item in issues] == ['nutrition_value_or_unit_unresolved'] * 2
