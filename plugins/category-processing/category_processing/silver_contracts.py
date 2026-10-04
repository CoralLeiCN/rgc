"""Silver field contracts and migration from preserved category catalogs."""

import math
import re
from copy import deepcopy
from pathlib import Path

from .archive import digest, json_bytes, read_json, sha256
from .profiles import _pointer, resolve_profile, validate_attribute_contract
from .values import standardize_value

FORMAT = "category-silver-record-2"
STATES = {"parse_error", "inference_error", "unresolved", "conflict", "not_applicable"}
METHODS = {"parsed", "inferred", "reviewed"}
FILES = ("profile.json", "source-mappings.json", "product.schema.json", "pipeline.json")


def resolve_silver_profile(root=None, **options):
    return resolve_profile(root, required_files=FILES, reference_name="silver-dataset-contract.json", **options)


def column(name, definition):
    value = definition.get("column", name.replace(".", "_"))
    if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError("Silver column must use snake_case: " + str(value))
    return value


def meaning(definition):
    return digest({key: definition.get(key) for key in
                   ("type", "unit", "scope", "qualifier", "basis", "description", "allowed_values", "minimum", "maximum", "list_semantics")})


def result_state(value):
    return "missing" if value is None else value["state"] if isinstance(value, dict) and set(value) == {"state"} else "available"


def validate_result(name, value, profile, mappings):
    state = result_state(value)
    if state in STATES or state == "missing":
        return value
    if state != "available":
        raise ValueError("Unknown Silver result state.")
    normalized = standardize_value(name, value, profile, mappings)
    if normalized != value or type(normalized) is not type(value) and isinstance(value, bool):
        raise ValueError("Correction must use the standardized field type and vocabulary.")
    return normalized


def validator(profile):
    properties = {"subject_id": {"type": "string"}, "listing_id": {"type": "string"},
                  "source_key": {"type": "string"}, "capture_id": {"type": "string"}}
    for name, definition in sorted(profile["attributes"].items()):
        col = column(name, definition)
        kind = definition["type"]
        value = {"type": {"enum": "string", "string_list": "array"}.get(kind, kind)}
        if kind == "enum":
            value["enum"] = definition["allowed_values"]
        if kind == "string_list":
            value["items"] = {"type": "string"}
            value["uniqueItems"] = definition.get("list_semantics", "set") != "ordered"
            if definition.get("allowed_values"):
                value["items"]["enum"] = definition["allowed_values"]
        for bound in ("minimum", "maximum"):
            if bound in definition:
                value[bound] = definition[bound]
        properties[col] = {"anyOf": [value, {"type": "null"}, {
            "type": "object", "required": ["state"], "additionalProperties": False,
            "properties": {"state": {"enum": sorted(STATES)}}}]}
        properties[col + ".source"] = {"type": "array", "items": {"type": "object"}}
        properties[col + ".method"] = {"enum": [None, *sorted(METHODS)]}
        properties[col + ".contexts"] = {"type": "array"}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "record_format_version": FORMAT,
            "schema_version": profile["schema_version"], "type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": True}


def migrate_documents(profile, mappings, recipe):
    profile, mappings, recipe = deepcopy(profile), deepcopy(mappings), deepcopy(recipe)
    migrating = profile.get("record_format_version") != FORMAT
    if migrating:
        profile["source_schema_version"] = profile["schema_version"]
        profile["schema_version"] += ".silver-2"
        mappings["mapping_version"] += ".silver-2"
        recipe["pipeline_version"] += ".silver-2"
    profile["record_format_version"] = FORMAT
    for name, definition in profile["attributes"].items():
        definition["column"] = column(name, definition)
        for key in ("model_role", "model_transform"):
            definition.pop(key, None)
        if migrating and definition.get("qualifier") and len(definition["qualifier"]) > 60:
            definition["qualifier_rule"] = definition.pop("qualifier")
        if name.startswith("nutrition.") and "per_100g" in name:
            definition["basis"] = "per_100g"
    profile["missing_states"] = [None, *sorted(STATES)]
    profile["methods"] = sorted(METHODS)
    profile.pop("review_statuses", None)
    profile.pop("review_format_version", None)
    profile["policies"] = {
        "identity": "Persistent source subjects; aliases never merge different sellers.",
        "missingness": "Missing is null. Errors, unresolved, conflict and not_applicable are tagged states.",
        "precedence": "Reviewed, parsed, inferred for the same subject, time and semantic context.",
        "scope": "Keep scope, qualifier and measurement basis distinct.",
        "prices": "Retain displayed and reference observations. Gold owns target policy and eligibility.",
    }
    mappings["schema_version"] = profile["schema_version"]
    recipe["schema_version"] = profile["schema_version"]
    recipe["output_format"] = FORMAT
    recipe["derive_comparison_group"] = False
    recipe.get("price", {}).pop("target_policy", None)
    recipe.pop("legacy_chocolate_price_aliases", None)
    recipe.pop("review_format_version", None)
    recipe.pop("accepted_review_versions", None)
    return {"profile.json": profile, "source-mappings.json": mappings,
            "product.schema.json": validator(profile), "pipeline.json": recipe}


def load_silver_contracts(root):
    root = resolve_silver_profile(root)
    original = {name: read_json(root / name) for name in FILES}
    profile, mappings, validation, recipe = (original[name] for name in FILES)
    if recipe.get("adapter") not in ("structured", "chocolate"):
        raise ValueError("Unsupported Silver source adapter.")
    if any(recipe.get(key) != profile.get(key) for key in ("category", "market")):
        raise ValueError("Category and market must agree in the Silver contracts.")
    attributes = profile.get("attributes", {})
    if not attributes or len(attributes) != profile.get("attribute_count"):
        raise ValueError("Silver needs a complete attribute catalog.")
    columns = [column(name, definition) for name, definition in attributes.items()]
    if len(set(columns)) != len(columns) or set(columns) & {"subject_id", "listing_id", "source_key", "capture_id", "schema_version", "children"}:
        raise ValueError("Silver columns collide after normalization.")
    for name, definition in attributes.items():
        if definition.get("type") not in ("string", "enum", "number", "integer", "boolean", "string_list"):
            raise ValueError("Unsupported Silver field type: " + name)
        for key in ("minimum", "maximum"):
            if key in definition and (type(definition[key]) not in (int, float) or not math.isfinite(definition[key])):
                raise ValueError("Field bounds must be finite numbers.")
        for key in ("scope", "qualifier", "basis", "unit"):
            if definition.get(key) is not None and not isinstance(definition[key], str):
                raise ValueError("Field context and units must be text or null.")
        if definition.get("list_semantics", "set") not in ("set", "ordered"):
            raise ValueError("List semantics must be set or ordered.")
        allowed = definition.get("allowed_values")
        if allowed is not None or definition["type"] == "enum":
            if not isinstance(allowed, list) or not allowed or any(not isinstance(value, str) or not value for value in allowed) or len(set(allowed)) != len(allowed):
                raise ValueError("Field vocabulary requires distinct nonempty strings.")
        for value in mappings.get("aliases", {}).get(name, {}).values():
            if allowed is not None and value not in allowed:
                raise ValueError("Alias is outside the declared vocabulary: " + name)
    if profile.get("schema_version") != mappings.get("schema_version"):
        raise ValueError("Silver schema and mappings disagree.")
    validation_version = validation.get("schema_version", validation.get("properties", {}).get("schema_version", {}).get("const"))
    if recipe.get("schema_version") != profile["schema_version"] or validation_version != profile["schema_version"]:
        raise ValueError("Silver recipe and validator must match the schema version.")
    if profile.get("record_format_version") != FORMAT:
        for name, definition in attributes.items():
            validate_attribute_contract(name, definition, validation["properties"]["attributes"]["properties"][name])
    elif validation != validator(profile):
        raise ValueError("Silver validator disagrees with the field catalog.")
    for group in recipe.get("collections", []):
        if not all(group.get(key) for key in ("name", "pointer", "id_pointer", "fields")):
            raise ValueError("Repeated subjects require a collection, source pointer, stable key and fields.")
        if any(field.get("attribute") not in attributes for field in group["fields"]):
            raise ValueError("Repeated subject field is outside the catalog.")
        for pointer in (group["pointer"], group["id_pointer"], *(field["pointer"] for field in group["fields"])):
            _pointer(pointer, "Collection pointer")
    for field in recipe.get("fields", []):
        if field.get("attribute") not in attributes:
            raise ValueError("Source field is outside the catalog.")
        _pointer(field["pointer"], "Source pointer")
    for pointer in recipe.get("sections", {}):
        _pointer(pointer, "Section pointer")
    for values in mappings.get("unit_conversions", {}).values():
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in values.values()):
            raise ValueError("Unit conversion factors must be positive finite numbers.")
    documents = migrate_documents(profile, mappings, recipe)
    provenance = {name: sha256(root / name) for name in FILES}
    return documents, provenance


def export_contracts(source, destination):
    documents, provenance = load_silver_contracts(source)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, document in documents.items():
        (destination / name).write_bytes(json_bytes(document))
    return {"output": str(destination.resolve()), "source_contracts": provenance,
            "files": {name: sha256(destination / name) for name in FILES}}


def init_silver_profile(definition, destination):
    """Author field contracts without a target, predictor set or model design."""
    from tempfile import TemporaryDirectory
    if definition.get("definition_format_version") != "category-silver-definition-2":
        raise ValueError("Expected category-silver-definition-2.")
    if "model_design" in definition:
        raise ValueError("Model design belongs in Gold preparation.")
    versions = definition["versions"]
    context = {"category": definition["category"], "market": definition["market"], "schema_version": versions["schema"]}
    profile = {**context, "record_format_version": FORMAT, "attributes": definition["attributes"],
               "attribute_count": len(definition["attributes"]), "standardization_rules": definition.get("standardization_rules", {})}
    mappings = {**definition.get("mappings", {}), "schema_version": versions["schema"], "mapping_version": versions["mapping"]}
    recipe = {**definition["pipeline"], **context, "pipeline_version": versions["pipeline"]}
    recipe.setdefault("adapter", "structured")
    if recipe.get("price", {}).get("target_policy"):
        raise ValueError("Silver recipes retain source prices; Gold declares the target policy.")
    with TemporaryDirectory(prefix="silver-contracts-") as temporary:
        source = Path(temporary)
        documents = migrate_documents(profile, mappings, recipe)
        for name, value in documents.items():
            (source / name).write_bytes(json_bytes(value))
        load_silver_contracts(source)
        result = export_contracts(source, destination)
    return {**result, "status": "profile_initialized", "schema_version": versions["schema"]}
