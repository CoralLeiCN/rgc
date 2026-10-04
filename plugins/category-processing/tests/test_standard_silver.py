"""Behavioral checks for source identity, contextual facts and persistent review."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.archive import json_bytes, sha256
from category_processing.silver_contracts import FORMAT, export_contracts, validator
from category_processing.silver_profile import statistics
from category_processing.silver_review import ReviewSession
from category_processing.silver_snapshot import read_rows, verified_snapshot
from category_processing.source_index import SourceIndex
from category_processing.standard_silver import build_standard_silver
from fixture_archive import import_document


@pytest.fixture
def study(tmp_path):
    attributes = {
        "identity.name": {"type": "string", "scope": "product"},
        "facts.percent": {"type": "number", "unit": "%", "minimum": 0, "maximum": 100, "scope": "product"},
        "facts.tags": {"type": "string_list", "allowed_values": ["a", "b", "c"], "scope": "product"},
        "facts.flag": {"type": "boolean", "scope": "product"},
        "facts.empty": {"type": "number", "scope": "product"},
    }
    profile = {"schema_version": "test-silver-2", "record_format_version": FORMAT, "category": "test", "market": "uk",
               "attribute_count": len(attributes), "attributes": attributes}
    recipe = {"schema_version": profile["schema_version"], "pipeline_version": "test-2", "category": "test", "market": "uk",
              "adapter": "structured", "fields": [
                  {"attribute": "identity.name", "pointer": "/raw_record/identity/name"},
                  {"attribute": "facts.percent", "pointer": "/raw_record/information/exact", "qualifier": "exact"},
                  {"attribute": "facts.percent", "pointer": "/raw_record/information/minimum", "qualifier": "minimum"},
                  {"attribute": "facts.tags", "pointer": "/raw_record/information/tags"},
                  {"attribute": "facts.flag", "pointer": "/raw_record/information/flag"}],
              "collections": [{"name": "component", "pointer": "/raw_record/information/components", "id_pointer": "/id",
                               "fields": [{"attribute": "facts.percent", "pointer": "/amount", "scope": "ingredient"}]}]}
    mappings = {"schema_version": profile["schema_version"], "mapping_version": "test-2", "aliases": {}}
    root = tmp_path / "profile"
    root.mkdir()
    for name, document in (("profile.json", profile), ("pipeline.json", recipe), ("source-mappings.json", mappings),
                           ("product.schema.json", validator(profile))):
        (root / name).write_bytes(json_bytes(document))
    raw = {"product_id": "z-listing", "source_key": "shop", "source_url": "https://shop.example/item/123",
           "identity": {"name": "Fixture", "source_product_id": "123", "source_variant_id": "v1"},
           "information": {"exact": 75, "minimum": 70, "tags": ["a", "a", "b"], "flag": False,
                           "components": [{"id": "c1", "amount": 40}, {"id": "c2", "amount": 60}]}}
    archive = tmp_path / "bronze"
    def collect(*values):
        return import_document({"study": {"category": "test", "market": "uk"}, "products": list(values)}, archive)
    collect(raw)
    def build(**kwargs):
        result = build_standard_silver(archive, tmp_path / "silver", root, state_db=tmp_path / "index.sqlite", **kwargs)
        return Path(result["output"]), result
    return {"raw": raw, "collect": collect, "build": build, "profile": root, "archive": archive,
            "db": tmp_path / "index.sqlite", "tmp": tmp_path}


def fact(root, field="facts.percent", qualifier="exact", kind="listing"):
    return next(item for item in read_rows(root / "facts.jsonl") if item["is_current"] and item["field"] == field
                and item["subject_kind"] == kind and item["context"]["qualifier"] == qualifier)


def request(item, result, previous=None):
    return {key: item[key] for key in ("subject_id", "field", "context")} | {
        "result": result, "reviewer": "Fixture human", "reason": "Compared with preserved source.", "expected_previous": previous}


def test_build_has_no_model_and_keeps_contexts_errors_missing_and_zero(study):
    before = {str(path): sha256(path) for path in study["archive"].rglob("*") if path.is_file()}
    root, report = study["build"]()
    assert report["status"] == "complete_snapshot"
    assert not (root / "model-design.json").exists()
    assert not (root / "model-inputs.jsonl").exists()
    assert fact(root)["result"] == 75
    assert fact(root, qualifier="minimum")["result"] == 70
    assert fact(root, "facts.flag", None)["result"] is False
    assert fact(root, "facts.empty", None)["result"] is None
    assert next(row for row in read_rows(root / "products.jsonl") if row["subject_kind"] == "listing")["facts_percent"] == {"state": "unresolved"}
    assert before == {str(path): sha256(path) for path in study["archive"].rglob("*") if path.is_file()}
    assert study["build"]()[0] == root
    assert verified_snapshot(study["tmp"] / "silver")[0] == root
    raw = deepcopy(study["raw"])
    raw["information"]["exact"] = "invalid"
    raw["information"]["minimum"] = 0
    study["collect"](raw)
    changed, _ = study["build"]()
    assert fact(changed)["result"] == {"state": "parse_error"}
    assert fact(changed, qualifier="minimum")["result"] == 0


def test_source_identity_survives_alias_archive_move_schema_change_and_reorder(study):
    root, _ = study["build"]()
    initial = {row["subject_id"] for row in read_rows(root / "subjects.jsonl")}
    raw = deepcopy(study["raw"])
    raw["product_id"] = "a-alias"
    raw["information"]["components"].reverse()
    study["collect"](raw)
    changed, _ = study["build"]()
    assert {row["subject_id"] for row in read_rows(changed / "subjects.jsonl")} == initial
    assert len(read_rows(changed / "source-listings.jsonl")) == 2
    moved = study["tmp"] / "relocated-bronze"
    shutil.copytree(study["archive"], moved)
    result = build_standard_silver(moved, study["tmp"] / "relocated-silver", study["profile"], state_db=study["db"])
    assert {row["subject_id"] for row in read_rows(Path(result["output"]) / "subjects.jsonl")} == initial
    other = deepcopy(raw)
    other["product_id"] = "other-seller"
    other["source_key"] = "other"
    study["collect"](other)
    latest, _ = study["build"]()
    assert len([row for row in read_rows(latest / "subjects.jsonl") if row["subject_kind"] == "listing"]) == 2


def test_review_replays_preserves_history_and_rejects_concurrent_writes(study):
    root, _ = study["build"]()
    original = fact(root)
    session = ReviewSession(root, study["db"], study["archive"])
    decision = session.save(request(original, 77))
    with pytest.raises(ValueError, match="changed since"):
        session.save(request(original, 78))
    rebuilt, _ = study["build"]()
    reviewed = fact(rebuilt)
    assert (reviewed["result"], reviewed["method"], reviewed["correction_id"]) == (77, "reviewed", decision["correction_id"])
    missing = ReviewSession(rebuilt, study["db"]).save(request(reviewed, None, decision["correction_id"]))
    again, _ = study["build"]()
    assert fact(again)["result"] is None
    assert fact(again)["method"] == "reviewed"
    with SourceIndex(study["db"]) as index:
        assert len(index.history()) == 2
        assert missing["supersedes"] == decision["correction_id"]
    raw = deepcopy(study["raw"])
    raw["information"]["exact"] = 80
    study["collect"](raw)
    changed, _ = study["build"]()
    assert fact(changed)["result"] == 80
    assert any(item["reason"] == "stale_correction" for item in read_rows(changed / "review-queue.jsonl"))


def test_parsed_wins_over_inferred_and_equal_priority_conflicts(study):
    root, _ = study["build"]()
    original = fact(root)
    inference = {"subject_id": original["subject_id"], "capture_id": original["capture_id"], "attribute": original["field"],
                 "pointer": "/raw_record/information/exact", "qualifier": "exact", "value": 85, "method": "reviewed"}
    changed, _ = study["build"](inferences=[inference])
    assert fact(changed)["result"] == 75
    assert fact(changed)["method"] == "parsed"
    assert any(item["method"] == "inferred" and item["result"] == 85 for item in read_rows(changed / "assertions.jsonl"))
    recipe = json.loads((study["profile"] / "pipeline.json").read_bytes())
    recipe["fields"].append({"attribute": "facts.percent", "pointer": "/raw_record/information/minimum", "qualifier": "exact"})
    (study["profile"] / "pipeline.json").write_bytes(json_bytes(recipe))
    conflict, _ = study["build"]()
    assert fact(conflict)["result"] == {"state": "conflict"}


def test_profile_denominators_lists_contexts_history_and_empty_fields(study):
    root, _ = study["build"]()
    report = json.loads((root / "schema-profile.json").read_bytes())
    fields = [item for item in report["fields"] if item["population"] == "current" and item["subject_kind"] == "listing" and item["source_key"] is None]
    for item in report["fields"]:
        assert sum(item["states"].values()) == item["N"]
    tags = next(item for item in fields if item["field"] == "facts.tags")
    assert [(item["value"], item["count"]) for item in tags["categorical"]["values"]] == [("a", 1), ("b", 1)]
    assert tags["categorical"]["unobserved_vocabulary"] == ["c"]
    assert [(item["context"]["qualifier"], item["numeric"]["minimum"]) for item in fields if item["field"] == "facts.percent"] == [("exact", 75), ("minimum", 70)]
    assert next(item for item in fields if item["field"] == "facts.empty")["numeric"]["median"] is None
    examples = [{"result": value, "method": "parsed", "subject_id": str(i), "capture_id": str(i), "source": []}
                for i, value in enumerate([0, 10, 20, 30, None, {"state": "parse_error"}])]
    for backend in ("python", "pandas"):
        stats = statistics(examples, {"type": "number"}, backend)
        assert stats["coverage"] == 4 / 6
        assert [stats["numeric"][key] for key in ("minimum", "q1", "median", "q3", "maximum")] == [0, 7.5, 15, 22.5, 30]
    empty = statistics([], {"type": "number"})
    assert empty["coverage"] is None and empty["numeric"]["minimum"] is None


def test_managed_integrity_and_state_location(study):
    root, _ = study["build"]()
    with pytest.raises(ValueError, match="outside"):
        build_standard_silver(study["archive"], study["tmp"] / "silver", study["profile"], state_db=root / "index.sqlite")
    (root / "products.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="changed"):
        verified_snapshot(root)


def test_migrate_packaged_chocolate_without_model_design(tmp_path):
    from category_processing.profiles import resolve_profile
    source = resolve_profile(category="chocolate", offline=True)
    copied = tmp_path / "four-contracts"
    copied.mkdir()
    for name in ("profile.json", "source-mappings.json", "pipeline.json", "product.schema.json"):
        shutil.copy(source / name, copied / name)
    result = export_contracts(copied, tmp_path / "release")
    assert len(result["files"]) == 4
    recipe = json.loads((tmp_path / "release/pipeline.json").read_bytes())
    assert "target_policy" not in recipe["price"]
    assert recipe["derive_comparison_group"] is False


def test_packaged_pin_resolves_offline_without_model_payload(tmp_path):
    from category_processing.dataset_contracts import cache_directory, load_manifest
    from category_processing.profiles import PLUGIN_ROOT
    from category_processing.silver_contracts import FILES, resolve_silver_profile
    source = resolve_silver_profile(category="coffee", offline=True)
    manifest = load_manifest(PLUGIN_ROOT / "profiles/coffee/silver-dataset-contract.json")
    destination = cache_directory(manifest, tmp_path / "cache")
    destination.mkdir(parents=True)
    for name in FILES:
        shutil.copy(source / name, destination / name)
    assert resolve_silver_profile(category="coffee", cache_root=tmp_path / "cache", offline=True) == destination
    assert not (destination / "model-design.json").exists()


def test_child_correction_survives_reorder_and_state_recovery(study):
    root, _ = study["build"]()
    child = fact(root, qualifier=None, kind="component")
    ReviewSession(root, study["db"]).save(request(child, 42))
    raw = deepcopy(study["raw"])
    raw["information"]["components"].reverse()
    study["collect"](raw)
    rebuilt, _ = study["build"]()
    corrected = next(item for item in read_rows(rebuilt / "facts.jsonl") if item["is_current"] and item["subject_id"] == child["subject_id"] and item["field"] == child["field"])
    assert corrected["result"] == 42 and corrected["method"] == "reviewed"
    recovered = study["tmp"] / "recovered.sqlite"
    ReviewSession(rebuilt, recovered)
    result = build_standard_silver(study["archive"], study["tmp"] / "recovered", study["profile"], state_db=recovered)
    assert any(item["result"] == 42 and item["method"] == "reviewed" for item in read_rows(Path(result["output"]) / "facts.jsonl"))


def test_silver_profile_authoring_needs_no_model_or_target(tmp_path):
    from category_processing.silver_contracts import init_silver_profile
    definition = {"definition_format_version": "category-silver-definition-2", "category": "widgets", "market": "gb",
                  "versions": {"schema": "widgets-1", "mapping": "widgets-map-1", "pipeline": "widgets-parser-1"},
                  "attributes": {"identity.name": {"type": "string", "unit": None, "scope": "product"}},
                  "pipeline": {"fields": [{"attribute": "identity.name", "pointer": "/raw_record/identity/name"}]}}
    result = init_silver_profile(definition, tmp_path / "fields")
    assert len(result["files"]) == 4
    assert not (tmp_path / "fields/model-design.json").exists()


@pytest.mark.parametrize("name,total,count", [
    ("Chocolate Bar 160g (Box of 19)", 3040, 19),
    ("Chocolate Bars — 32g / 12 Bars", 384, 12),
    ("Baking Chocolate Drops (100g) — Case of 10 X Bags", 1000, 10),
])
def test_pack_and_nutrition_semantics(name, total, count):
    from category_processing.adapters import extract_capture
    from category_processing.silver_chocolate import refine_quantities
    capture = {"raw_record": {"identity": {"name": name}, "information": {
        "body_html": "<table><tr><td>Fat</td><td>31.9g</td></tr><tr><td>Sugars</td><td>42.8g</td></tr></table>"}}}
    recipe = {"adapter": "chocolate", "quantity": {"attribute": "quantity.total_edible_weight_g", "unit": "g"},
              "derive_comparison_group": False, "pack_count_attribute": "quantity.pack_count"}
    result = refine_quantities(capture, extract_capture(capture, recipe), recipe)
    assert {item["value"] for item in result["attributes"] if item["attribute"] == "quantity.total_edible_weight_g"} == {total}
    assert {item["value"] for item in result["attributes"] if item["attribute"] == "quantity.pack_count"} == {count}
    assert all(item["value"] not in (31.9, 42.8) for item in result["attributes"])
