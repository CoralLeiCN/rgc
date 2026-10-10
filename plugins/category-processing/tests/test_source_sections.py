"""Literal evidence collections must not suppress factual disagreements."""

from pathlib import Path

import pytest
from category_processing.adapters import extract_capture
from category_processing.archive import json_bytes, sha256
from category_processing.silver_contracts import (
    FORMAT,
    load_silver_contracts,
    validator,
)
from category_processing.silver_snapshot import read_rows
from category_processing.source_sections import ingredient_excerpt
from category_processing.standard_silver import build_standard_silver, select_result
from fixture_archive import import_document


def candidates(*values, method="parsed"):
    return [{"result": value, "method": method} for value in values]


def test_literal_collection_preserves_both_excerpts_and_review_priority():
    values = candidates("Contains milk.", "May contain nuts.", "Contains milk.")
    assert select_result(values) == ({"state": "conflict"}, "parsed")
    assert select_result(values, "collect_sections") == ("Contains milk.\nMay contain nuts.", "parsed")
    assert select_result(values + candidates("Reviewed section", method="reviewed"), "collect_sections") == (
        "Reviewed section", "reviewed")
    assert select_result(candidates("a", "b", method="inferred"), "collect_sections") == ({"state": "conflict"}, "inferred")


def test_format_equivalence_does_not_merge_recipes():
    original = "Ingredients\nIngredients: Cocoa mass,\n sugar."
    assert select_result(candidates(original, "COCOA MASS, SUGAR."), "equivalent_sections") == (original, "parsed")
    assert select_result(candidates("Ingredients: Cocoa mass, sugar.", "Ingredients: Cocoa mass, milk."),
                         "equivalent_sections") == ({"state": "conflict"}, "parsed")


def test_explicit_boundaries_keep_recipe_text_and_multiple_recipes():
    text = "Product description\nIngredients:\nRice flour, sugar.\nNutrition\nFat: 30g"
    assert ingredient_excerpt(text) == "Ingredients:\nRice flour, sugar."
    assert ingredient_excerpt("Cocoa butter, sugar.\nOrigin\nPeru\nNutritionals\nPer 100g...") == "Cocoa butter, sugar."
    mixed = "Ingredients: Sugar, milk.\nAllergens: Milk\nIngredients: Cocoa, nuts."
    assert ingredient_excerpt(mixed) == mixed


@pytest.mark.parametrize("constituent", ["butter", "mass", "powder", "beans"])
def test_constituent_percentage_cannot_become_total_cocoa(constituent):
    capture = {"raw_record": {"identity": {"name": "Chocolate"}, "information": {
        "product_page_information": {"ingredients_source_statement": "33.6% cocoa solids; 24% cocoa " + constituent}}}}
    result = extract_capture(capture, {"adapter": "chocolate", "derive_comparison_group": False,
                                      "feature_mappings": {"cocoa_percentage": "composition.cocoa_percentage"}})
    assert {item["value"] for item in result["attributes"]} == {33.6}
    assert {item["reason"] for item in result["rejected_candidates"]} == {"cocoa_constituent_is_not_total_cocoa"}


def test_finished_product_cocoa_is_distinct_from_component_cocoa():
    capture = {"raw_record": {"identity": {"name": "Chocolate block"}, "information": {
        "product_page_information": {"ingredients_source_statement":
            "Milk Chocolate contains: Cocoa Solids 42% minimum, Milk Solids 14% minimum, "
            "Finished Product contains: Cocoa Solids 26% minimum"}}}}
    result = extract_capture(capture, {"adapter": "chocolate", "derive_comparison_group": False,
                                      "feature_mappings": {"cocoa_percentage": "composition.cocoa_percentage"}})
    assert {(item["value"], item["scope"], item["qualifier"]) for item in result["attributes"]} == {
        (42, "ingredient", "minimum"), (26, "product", "minimum")}


def test_build_assembles_original_sections_and_retains_all_evidence(tmp_path):
    names = {"ingredients_text": "composition.ingredients_text", "allergen_text": "composition.allergen_text",
             "claim_text": "marketing.claim_text"}
    attributes = {name: {"type": "string", "scope": "product", "standardization_rule": "source_section"}
                  for name in names.values()}
    profile = {"schema_version": "test-1", "record_format_version": FORMAT, "category": "chocolate", "market": "uk",
               "attribute_count": len(attributes), "attributes": attributes}
    recipe = {"schema_version": "test-1", "pipeline_version": "test-1", "category": "chocolate", "market": "uk",
              "adapter": "chocolate", "derive_comparison_group": False, "feature_mappings": names,
              "source_section_parsing": "bounded_chocolate_sections",
              "source_text_resolution": {"composition.ingredients_text": "equivalent_sections",
                                         "composition.allergen_text": "collect_sections", "marketing.claim_text": "collect_sections"}}
    root = tmp_path / "profile"
    root.mkdir()
    for name, document in (("profile.json", profile), ("pipeline.json", recipe),
                           ("source-mappings.json", {"schema_version": "test-1", "mapping_version": "test-1", "aliases": {}}),
                           ("product.schema.json", validator(profile))):
        (root / name).write_bytes(json_bytes(document))
    raw = {"source_key": "ocado", "product_id": "chocolate-1", "source_url": "https://shop.example/1",
           "identity": {"name": "Chocolate", "source_product_id": "1"}, "information": {
               "product_page_information": {"ingredients_source_statement": "Ingredients: Sugar, cocoa mass."},
               "original_product_page_observations": [{"original_heading_sections": {
                   "Ingredients": [{"text": "Sugar,"}, {"text": "cocoa mass."}],
                   "Features": [{"text": "Vegetarian"}, {"text": "Ocado Price Promise"},
                                {"text": "\ue200cite\ue20239†Shop all Brand\ue201 "}],
                   "Allergen Information": [{"text": "Contains milk."}, {"text": "May contain nuts."}]}}]}}
    archive = tmp_path / "bronze"
    import_document({"study": {"category": "chocolate", "market": "uk"}, "products": [raw]}, archive)
    hashes = {str(path): sha256(path) for path in archive.rglob("*") if path.is_file()}
    built = build_standard_silver(archive, tmp_path / "silver", root, state_db=tmp_path / "state.sqlite")
    snapshot = Path(built["output"])
    facts = {row["field"]: row for row in read_rows(snapshot / "facts.jsonl")}
    assert facts["composition.ingredients_text"]["result"] == "Ingredients: Sugar, cocoa mass."
    assert len(facts["composition.ingredients_text"]["source"]) == 2
    assert facts["composition.allergen_text"]["result"] == "Contains milk.\nMay contain nuts."
    assert facts["marketing.claim_text"]["result"] == "Vegetarian"
    assert all(row["result"] != {"state": "conflict"} for row in facts.values())
    assert any(row["parser_method"] == "cached_source_heading_section" for row in read_rows(snapshot / "assertions.jsonl"))
    assert sum(row["reason"] == "retailer_navigation_is_not_product_claim"
               for row in read_rows(snapshot / "review-queue.jsonl")) == 2
    assert hashes == {str(path): sha256(path) for path in archive.rglob("*") if path.is_file()}
    recipe["source_text_resolution"]["composition.ingredients_text"] = "unknown_policy"
    (root / "pipeline.json").write_bytes(json_bytes(recipe))
    with pytest.raises(ValueError, match="literal source-section string"):
        load_silver_contracts(root)
    recipe["source_text_resolution"]["composition.ingredients_text"] = "collect_sections"
    profile["attributes"]["composition.ingredients_text"]["type"] = "number"
    (root / "pipeline.json").write_bytes(json_bytes(recipe))
    (root / "profile.json").write_bytes(json_bytes(profile))
    (root / "product.schema.json").write_bytes(json_bytes(validator(profile)))
    with pytest.raises(ValueError, match="literal source-section string"):
        load_silver_contracts(root)
