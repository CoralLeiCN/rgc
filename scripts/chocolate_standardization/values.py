"""Typed vocabulary and unit standardization driven by the category profile."""

from decimal import Decimal, InvalidOperation
from datetime import date
import math
import re
import unicodedata


STATES = {"known", "unknown", "not_applicable", "conflict"}
SCOPES = {"product", "ingredient", "brand", "packaging", "packaging_component", "observation"}
REVIEWS = {"unreviewed", "reviewed", "needs_review"}


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

    The runtime supports explicit nullable typed value branches and a
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


def alias_key(value):
    return re.sub(r"[\s_-]+", " ", unicodedata.normalize("NFKC", value).strip().casefold())


def country(value, mappings):
    aliases = {alias_key(key): result for key, result in mappings.get("country_aliases", {}).items()}
    aliases.update({alias_key(value): value for value in aliases.values()})
    result = aliases.get(alias_key(value))
    if result is None:
        raise ValueError("Unmapped country name: " + value)
    return result


def standardize_value(name, value, profile, mappings, unit=None):
    definition = profile["attributes"][name]
    kind = definition["type"]
    rule = definition.get("standardization_rule", "")
    if value is None:
        return None
    if kind == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(name + " requires a nonempty string.")
        if rule == "source_section":
            return value
        result = re.sub(r"\s+", " ", value).strip()
        if rule == "country_labels":
            return country(result, mappings)
        if rule == "gtin":
            if not result.isascii() or not result.isdigit() or len(result) not in (8, 12, 13, 14):
                raise ValueError("GTIN must have a supported digit length.")
            checksum = sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(result[:-1])))
            if (10 - checksum % 10) % 10 != int(result[-1]):
                raise ValueError("GTIN check digit is invalid.")
        if rule == "iso_date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", result):
                raise ValueError("Date requires an unambiguous YYYY-MM-DD value.")
            date.fromisoformat(result)
        return result
    if kind == "enum":
        if not isinstance(value, str):
            raise ValueError(name + " requires a declared vocabulary value.")
        allowed = definition["allowed_values"]
        aliases = mappings.get("aliases", {}).get(name, {})
        normalized_aliases = {alias_key(key): val for key, val in aliases.items()}
        canonical = value if value in allowed else normalized_aliases.get(alias_key(value))
        if canonical is None:
            canonical = next((item for item in allowed if alias_key(item) == alias_key(value)), None)
        if canonical not in allowed:
            raise ValueError("Unmapped vocabulary for " + name + ": " + value)
        return canonical
    if kind == "boolean":
        if type(value) is not bool:
            raise ValueError(name + " requires a boolean, not inferred source wording.")
        return value
    if kind in ("number", "integer"):
        if isinstance(value, bool):
            raise ValueError(name + " rejects boolean numeric values.")
        try:
            number = Decimal(str(value))
            result = float(number)
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            raise ValueError(name + " requires a finite number.")
        if not number.is_finite() or not math.isfinite(result):
            raise ValueError(name + " requires a finite number.")
        expected = definition.get("unit")
        if unit and unit != expected:
            factors = mappings.get("quantity_units", {})
            if expected == "g" and unit in factors:
                result *= factors[unit]
            elif expected == "day" and unit in mappings.get("duration_units", {}):
                result *= mappings["duration_units"][unit]
            elif expected == "degC" and unit in ("degF", "°F"):
                result = (result - 32) * 5 / 9
            else:
                raise ValueError("Unsupported unit conversion for " + name)
        if not math.isfinite(result):
            raise ValueError("Unit conversion is out of range for " + name)
        if "minimum" in definition and result < definition["minimum"]:
            raise ValueError(name + " is below the permitted minimum.")
        if "maximum" in definition and result > definition["maximum"]:
            raise ValueError(name + " exceeds the permitted maximum.")
        if name.startswith("quantity.") and result <= 0:
            raise ValueError(name + " must be positive.")
        if kind == "integer":
            if not result.is_integer():
                raise ValueError(name + " requires an integer.")
            return int(result)
        return result
    if kind == "string_list":
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(name + " requires a list of nonempty strings.")
        aliases = {alias_key(key): val for key, val in mappings.get("aliases", {}).get(name, {}).items()}
        normalized = sorted(set(country(item, mappings) if rule == "country_labels" else aliases.get(alias_key(item), re.sub(r"\s+", " ", item).strip()) for item in value))
        allowed = definition.get("allowed_values")
        if allowed and any(item not in allowed for item in normalized):
            raise ValueError("Unmapped list vocabulary for " + name)
        return normalized
    raise ValueError("Unsupported schema type for " + name + ": " + str(kind))


def unknown_attribute(definition):
    return {"value": None, "status": "unknown", "unit": definition.get("unit"),
            "qualifier": None, "scope": definition.get("scope", "product"),
            "evidence": [], "method": "not_established_by_available_evidence", "review_status": "unreviewed"}


def validate_evidence(refs):
    if not isinstance(refs, list):
        raise ValueError("Evidence must be a list.")
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"capture_id", "pointer"}:
            raise ValueError("Evidence must contain only capture_id and pointer.")
        if not isinstance(ref["capture_id"], str) or not ref["capture_id"]:
            raise ValueError("Evidence capture ID must be nonempty.")
        if not isinstance(ref["pointer"], str) or not re.fullmatch(r"(?:/(?:[^~/]|~[01])*)*", ref["pointer"]):
            raise ValueError("Evidence pointer must be a valid JSON pointer.")


def validate_product(row, profile, mappings=None):
    required = {"schema_version", "dataset_version", "source_dataset_version", "listing_id", "source_listing_ids", "source_role", "source_key", "brand", "retailer", "attributes", "unmapped_claims", "review_status"}
    if not isinstance(row, dict) or required - set(row) or set(row) - required - {"category", "market"}:
        raise ValueError("Product envelope must match the category contract.")
    if row.get("schema_version") != profile["schema_version"]:
        raise ValueError("Product schema version does not match the profile.")
    for key in ("dataset_version", "source_dataset_version", "listing_id", "source_key"):
        if not isinstance(row[key], str) or not row[key]:
            raise ValueError("Product requires a nonempty " + key)
    if row["source_role"] not in ("brand", "retail", "unknown") or row["review_status"] not in REVIEWS:
        raise ValueError("Product context uses an unsupported controlled value.")
    for key in ("brand", "retailer"):
        if row[key] is not None and not isinstance(row[key], str):
            raise ValueError("Product " + key + " must be text or null.")
    if ("category" in row and row["category"] != "chocolate") or ("market" in row and row["market"] != "uk"):
        raise ValueError("Product category or market disagrees with the contract.")
    ids = row["source_listing_ids"]
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("Product source listing IDs must be nonempty unique strings.")
    if set(row.get("attributes", {})) != set(profile["attributes"]):
        raise ValueError("Product must track every defined category attribute exactly once.")
    for name, attribute in row["attributes"].items():
        if not isinstance(attribute, dict) or set(attribute) != {"value", "status", "unit", "qualifier", "scope", "evidence", "method", "review_status"}:
            raise ValueError("Attribute envelope does not match the contract: " + name)
        if attribute["scope"] not in SCOPES or attribute["review_status"] not in REVIEWS:
            raise ValueError("Unsupported attribute scope or review status: " + name)
        if attribute["qualifier"] is not None and not isinstance(attribute["qualifier"], str):
            raise ValueError("Attribute qualifier must be text or null: " + name)
        if not isinstance(attribute["method"], str) or not attribute["method"]:
            raise ValueError("Attribute method must be nonempty: " + name)
        validate_evidence(attribute["evidence"])
        if attribute.get("status") not in STATES:
            raise ValueError("Unsupported attribute state for " + name)
        if attribute.get("unit") != profile["attributes"][name].get("unit"):
            raise ValueError("Attribute unit disagrees with the profile: " + name)
        if attribute["status"] == "known":
            if attribute.get("value") is None or not attribute.get("evidence"):
                raise ValueError("Known attributes require evidence and a value: " + name)
            value = attribute["value"]
            kind = profile["attributes"][name]["type"]
            valid = {"string": isinstance(value, str), "enum": isinstance(value, str),
                     "number": type(value) in (int, float), "integer": type(value) is int,
                     "boolean": type(value) is bool, "string_list": isinstance(value, list)}
            if not valid.get(kind):
                raise ValueError("Attribute value has the wrong type: " + name)
            if mappings is not None:
                if standardize_value(name, value, profile, mappings) != value:
                    raise ValueError("Attribute value is not canonical: " + name)
            elif kind == "enum" and value not in profile["attributes"][name]["allowed_values"]:
                raise ValueError("Attribute uses an unsupported vocabulary: " + name)
        elif attribute.get("value") is not None:
            raise ValueError("Unresolved attributes must not carry a selected value: " + name)
        if attribute["status"] in ("conflict", "not_applicable") and not attribute["evidence"]:
            raise ValueError("Conflict and not-applicable states require evidence: " + name)
    if not isinstance(row["unmapped_claims"], list):
        raise ValueError("Unmapped claims must be a list.")
    for claim in row["unmapped_claims"]:
        if not isinstance(claim, dict) or {"value", "evidence", "reason"} - set(claim) or set(claim) - {"value", "evidence", "reason", "attribute", "scope"}:
            raise ValueError("Unmapped claim envelope does not match the contract.")
        if any(not isinstance(claim[key], str) or not claim[key] for key in ("value", "reason")):
            raise ValueError("Unmapped claims require original text and a reason.")
        validate_evidence(claim["evidence"])
        if not claim["evidence"] or ("scope" in claim and claim["scope"] not in SCOPES):
            raise ValueError("Unmapped claims require evidence and supported scope.")
        if "attribute" in claim and claim["attribute"] is not None and not isinstance(claim["attribute"], str):
            raise ValueError("Unmapped attribute must be text or null.")
