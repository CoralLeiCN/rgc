"""Validate and load an explicit category processing profile at runtime."""

from pathlib import Path
import math
import re

from .archive import positive, read_json, sha256
from .values import alias_key


PROFILE_FORMAT = "category-processing-profile-1"
CONTRACT_FILES = ("profile.json", "source-mappings.json", "model-design.json", "product.schema.json", "pipeline.json")
TYPES = {"string", "number", "integer", "boolean", "enum", "string_list"}
SCOPES = {"product", "ingredient", "brand", "packaging", "packaging_component", "observation"}
ANNOTATIONS = {"title", "description", "$comment", "examples"}


def _value_contract(name, definition, schema):
    """Compare the supported typed value schema with its normalization contract."""
    if not isinstance(schema, dict):
        raise ValueError("Product validator value contract is missing: " + name)
    kind = definition["type"]
    expected_type = {"enum": "string", "string_list": "array"}.get(kind, kind)
    if schema.get("type") != expected_type:
        raise ValueError("Product validator attribute type differs from the profile: " + name)
    supported = {"type"} | ANNOTATIONS
    if kind in ("number", "integer"):
        supported.update(("minimum", "maximum"))
        for bound in ("minimum", "maximum"):
            value = schema.get(bound)
            if (bound in schema) != (bound in definition) or value != definition.get(bound) or isinstance(value, bool):
                raise ValueError("Product validator numeric bounds differ from the profile: " + name)
    elif kind == "string":
        supported.add("minLength")
        if schema.get("minLength", 1) != 1:
            raise ValueError("Product validator string constraints differ from normalization: " + name)
    elif kind == "enum":
        supported.add("enum")
        labels = schema.get("enum")
        expected = definition["allowed_values"]
        if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels) or len(labels) != len(set(labels)) or set(labels) != set(expected):
            raise ValueError("Product validator vocabulary differs from the profile: " + name)
    elif kind == "string_list":
        supported.update(("items", "uniqueItems"))
        items = schema.get("items")
        if not isinstance(items, dict) or items.get("type") != "string" or items.get("minLength", 1) != 1:
            raise ValueError("Product validator list item type differs from the profile: " + name)
        labels = items.get("enum")
        expected = definition.get("allowed_values")
        if expected is not None and (not isinstance(expected, list) or not expected or any(not isinstance(label, str) or not label for label in expected) or len(expected) != len(set(expected))):
            raise ValueError("Profile list vocabulary requires unique nonempty labels: " + name)
        if (labels is None) != (expected is None) or (labels is not None and (not isinstance(labels, list) or any(not isinstance(label, str) for label in labels) or len(labels) != len(set(labels)) or set(labels) != set(expected))):
            raise ValueError("Product validator list vocabulary differs from the profile: " + name)
        if set(items) - ({"type", "minLength", "enum"} | ANNOTATIONS) or ("uniqueItems" in schema and type(schema["uniqueItems"]) is not bool):
            raise ValueError("Unsupported product validator list constraints: " + name)
    if set(schema) - supported:
        raise ValueError("Unsupported product validator value constraints: " + name)


def validate_attribute_contract(name, definition, schema):
    """Reject profile/validator drift before a derived snapshot can be published.

    The portable runtime supports explicit nullable typed value branches and a
    known-status conditional, as used by the bundled profile validators. This
    checks their declared semantics without claiming a general JSON Schema engine.
    """
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        raise ValueError("Product validator attribute envelope is missing: " + name)
    properties = schema["properties"]
    unit = properties.get("unit")
    if not isinstance(unit, dict) or "const" not in unit or unit["const"] != definition.get("unit") or set(unit) - ({"const"} | ANNOTATIONS):
        raise ValueError("Product validator attribute unit differs from the profile: " + name)
    value = properties.get("value")
    branches = value.get("anyOf") if isinstance(value, dict) else None
    if not isinstance(branches, list) or len(branches) != 2 or set(value) - ({"anyOf"} | ANNOTATIONS):
        raise ValueError("Product validator requires explicit nullable value branches: " + name)
    nulls = [branch for branch in branches if isinstance(branch, dict) and branch.get("type") == "null"]
    if len(nulls) != 1 or set(nulls[0]) - ({"type"} | ANNOTATIONS):
        raise ValueError("Product validator requires an unconstrained null branch: " + name)
    _value_contract(name, definition, next(branch for branch in branches if branch is not nulls[0]))
    conditions = schema.get("allOf")
    if not isinstance(conditions, list):
        raise ValueError("Product validator requires a known-status value condition: " + name)
    known = [condition for condition in conditions if isinstance(condition, dict) and condition.get("if", {}).get("properties", {}).get("status", {}).get("const") == "known"]
    if len(known) != 1:
        raise ValueError("Product validator requires one known-status value condition: " + name)
    _value_contract(name, definition, known[0].get("then", {}).get("properties", {}).get("value"))


def _pointer(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"(?:/(?:[^~/]|~[01])*)*", value):
        raise ValueError(label + " must be a capture-root JSON pointer.")


def load_profile(profile_root):
    root = Path(profile_root).expanduser().resolve()
    documents = {name: read_json(root / name) for name in CONTRACT_FILES}
    if any(not isinstance(doc, dict) for doc in documents.values()):
        raise ValueError("Category contracts must be JSON objects.")
    profile, mappings, design, validator, recipe = (documents[name] for name in CONTRACT_FILES)
    for key in ("category", "market"):
        value = profile.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) or value in (".", ".."):
            raise ValueError("Profile " + key + " must be a safe nonempty directory identifier.")
        if recipe.get(key) != value:
            raise ValueError("Pipeline recipe and profile " + key + " disagree.")
    version = profile.get("schema_version")
    if not isinstance(version, str) or not version:
        raise ValueError("Category profile requires a schema_version.")
    if any(doc.get("schema_version") != version for doc in (mappings, design)):
        raise ValueError("Profile, mapping and model design schema versions must agree.")
    if validator.get("properties", {}).get("schema_version", {}).get("const") != version:
        raise ValueError("Product validator schema version differs from the profile.")
    for key in ("category", "market"):
        if validator.get("properties", {}).get(key, {}).get("const") != profile[key]:
            raise ValueError("Product validator " + key + " differs from the profile.")
    if recipe.get("schema_version", version) != version:
        raise ValueError("Pipeline recipe schema version differs from the profile.")
    if recipe.get("pipeline_format_version") != PROFILE_FORMAT:
        raise ValueError("Pipeline recipe requires pipeline_format_version " + PROFILE_FORMAT)
    if not isinstance(recipe.get("pipeline_version"), str) or not recipe["pipeline_version"]:
        raise ValueError("Pipeline recipe requires a versioned pipeline_version.")
    if recipe.get("adapter") not in ("structured", "chocolate"):
        raise ValueError("The profile requires a supported bundled adapter.")
    attributes = profile.get("attributes")
    if not isinstance(attributes, dict) or not attributes or profile.get("attribute_count") != len(attributes):
        raise ValueError("Profile attribute_count must match its nonempty attribute catalog.")
    schema_attributes = validator.get("properties", {}).get("attributes", {})
    if set(schema_attributes.get("properties", {})) != set(attributes) or set(schema_attributes.get("required", [])) != set(attributes):
        raise ValueError("Product validator attribute catalog must match the profile.")
    rules = profile.get("standardization_rules")
    if rules is not None and not isinstance(rules, dict):
        raise ValueError("Profile standardization_rules must be an object.")
    for name, definition in attributes.items():
        if not isinstance(name, str) or not name or not isinstance(definition, dict) or definition.get("type") not in TYPES:
            raise ValueError("Every category attribute needs a supported declared type.")
        rule = definition.get("standardization_rule")
        if not isinstance(rule, str) or not rule or (rules is not None and rule not in rules):
            raise ValueError("Every category attribute needs a declared standardization rule: " + name)
        if definition.get("scope", "product") not in SCOPES:
            raise ValueError("Unsupported attribute scope: " + name)
        if definition.get("unit") is not None and not isinstance(definition["unit"], str):
            raise ValueError("Attribute unit must be text or null: " + name)
        if definition["type"] == "enum":
            allowed = definition.get("allowed_values")
            if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed) or len(set(allowed)) != len(allowed):
                raise ValueError("Enum attributes require unique nonempty canonical labels: " + name)
        for key in ("minimum", "maximum"):
            if key in definition and (isinstance(definition[key], bool) or not isinstance(definition[key], (int, float)) or not math.isfinite(definition[key])):
                raise ValueError("Numeric bounds must be numeric: " + name)
        if "minimum" in definition and "maximum" in definition and definition["minimum"] > definition["maximum"]:
            raise ValueError("Attribute numeric bounds are inverted: " + name)
        validate_attribute_contract(name, definition, schema_attributes["properties"][name])
    aliases = mappings.get("aliases", {})
    if not isinstance(aliases, dict) or set(aliases) - set(attributes):
        raise ValueError("Vocabulary mappings must reference declared attributes.")
    for name, table in aliases.items():
        if not isinstance(table, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in table.items()):
            raise ValueError("Vocabulary aliases must map text to canonical text.")
        allowed = attributes[name].get("allowed_values")
        if allowed and any(value not in allowed for value in table.values()):
            raise ValueError("Vocabulary aliases map outside the declared labels: " + name)
        normalized = {}
        for key, value in table.items():
            token = alias_key(key)
            if not token or (token in normalized and normalized[token] != value):
                raise ValueError("Normalized vocabulary alias collision: " + name)
            normalized[token] = value
    countries = mappings.get("country_aliases", {})
    if not isinstance(countries, dict):
        raise ValueError("Country aliases must be an object.")
    normalized = {}
    for key, value in countries.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
            raise ValueError("Country aliases must map nonempty text to canonical text.")
        token = alias_key(key)
        if token in normalized and normalized[token] != value:
            raise ValueError("Normalized country alias collision.")
        normalized[token] = value
    for name in ("quantity_units", "duration_units"):
        table = mappings.get(name, {})
        if not isinstance(table, dict) or any(not isinstance(key, str) or not key or isinstance(value, bool) or not isinstance(value, (int, float)) or positive(value) is None for key, value in table.items()):
            raise ValueError("Unit factors must be finite positive numbers: " + name)
    conversion_tables = mappings.get("unit_conversions", {})
    if not isinstance(conversion_tables, dict):
        raise ValueError("Unit conversions must be an object.")
    for name, table in conversion_tables.items():
        if not isinstance(name, str) or not name or not isinstance(table, dict) or any(not isinstance(key, str) or not key or isinstance(value, bool) or not isinstance(value, (int, float)) or positive(value) is None for key, value in table.items()):
            raise ValueError("Unit conversions require finite positive numeric factors.")
    predictors = design.get("predictors")
    if not isinstance(predictors, dict) or set(predictors) - set(attributes):
        raise ValueError("Model predictors must reference declared category attributes.")
    for name, predictor in predictors.items():
        if not isinstance(predictor, dict):
            raise ValueError("Model predictors require declared definitions: " + name)
        attribute = attributes[name]
        if predictor.get("type") == "numeric" and attribute["type"] not in ("number", "integer"):
            raise ValueError("Numeric model predictor requires a numeric category attribute: " + name)
        if predictor.get("type") in ("categorical", "presence") and attribute["type"] not in ("string", "enum"):
            raise ValueError("Categorical model predictor requires a text category attribute: " + name)
        if "unit" in predictor and predictor["unit"] != attribute.get("unit"):
            raise ValueError("Model predictor unit differs from the profile: " + name)
        labels = predictor.get("allowed_values")
        if labels is not None:
            if not isinstance(labels, list) or not labels or any(not isinstance(label, str) or not label for label in labels) or len(labels) != len(set(labels)):
                raise ValueError("Model predictor labels must be unique nonempty strings: " + name)
            if attribute["type"] == "enum" and not set(labels) <= set(attribute["allowed_values"]):
                raise ValueError("Model predictor vocabulary exceeds the profile: " + name)
    roles = recipe.get("source_roles", {})
    if not isinstance(roles, dict):
        raise ValueError("Pipeline source_roles must be an object.")
    for source, role in roles.items():
        if not isinstance(source, str) or not isinstance(role, dict) or role.get("source_role") not in ("brand", "retail", "unknown"):
            raise ValueError("Selling-source roles must use brand, retail or unknown.")
        if role.get("retailer") is not None and not isinstance(role["retailer"], str):
            raise ValueError("Selling-source retailer names must be text or null.")
    fields = recipe.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("Pipeline fields must be a list.")
    for field in fields:
        if not isinstance(field, dict) or field.get("attribute") not in attributes:
            raise ValueError("Pipeline field mappings must reference declared attributes.")
        _pointer(field.get("pointer"), "Pipeline field pointer")
        if field.get("scope", "product") not in SCOPES:
            raise ValueError("Unsupported pipeline field scope.")
        for key in ("unit", "qualifier"):
            if field.get(key) is not None and not isinstance(field[key], str):
                raise ValueError("Pipeline field " + key + " must be text or null.")
        if "skip_values" in field and not isinstance(field["skip_values"], list):
            raise ValueError("Pipeline field skip_values must be a list.")
    sections = recipe.get("sections", {})
    if not isinstance(sections, dict):
        raise ValueError("Pipeline sections must map pointers to attribute prefixes.")
    for pointer, prefix in sections.items():
        _pointer(pointer, "Pipeline section pointer")
        if not isinstance(prefix, str) or not prefix:
            raise ValueError("Pipeline section attribute prefixes must be nonempty text.")
    quantity = recipe.get("quantity")
    if not isinstance(quantity, dict) or quantity.get("attribute") not in attributes:
        raise ValueError("Pipeline quantity must reference a declared attribute.")
    definition = attributes[quantity["attribute"]]
    if definition["type"] not in ("number", "integer") or quantity.get("unit") != definition.get("unit") or positive(quantity.get("base_quantity")) is None:
        raise ValueError("Pipeline quantity needs a numeric attribute, matching unit and positive base_quantity.")
    target = design.get("target")
    if not isinstance(target, dict) or target.get("quantity_attribute") != quantity["attribute"] or target.get("base_quantity") != quantity["base_quantity"]:
        raise ValueError("Model target quantity_attribute and base_quantity must agree with the pipeline recipe.")
    if not isinstance(target.get("currency"), str) or not target["currency"].strip():
        raise ValueError("Model target currency must be explicit nonempty text.")
    price = recipe.get("price", {})
    if not isinstance(price, dict) or price.get("price_unit") not in ("major", "minor"):
        raise ValueError("Pipeline price requires an explicit major/minor representation.")
    for name, value in price.items():
        if name.endswith("_pointer"):
            _pointer(value, "Pipeline price " + name)
    if recipe["adapter"] == "structured" and "amount_pointer" not in price:
        raise ValueError("Structured price extraction needs amount_pointer.")
    if not isinstance(recipe.get("review_format_version"), str) or not recipe["review_format_version"]:
        raise ValueError("Pipeline requires a review_format_version.")
    return profile, mappings, design, recipe, {name: sha256(root / name) for name in CONTRACT_FILES}
