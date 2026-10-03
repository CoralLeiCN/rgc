"""Author aligned category contracts from an explicit, category-neutral definition."""

import json
import math
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from .model import _predictor_definitions
from .profiles import CONTRACT_FILES, PROFILE_FORMAT, TYPES, load_profile
from .values import REVIEWS, SCOPES, STATES

DEFINITION_FORMAT = "category-processing-definition-1"
REVIEW_FORMAT = "category-processing-reviews-1"


def _object(value, label, allowed=None, required=()):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object.")
    if set(required) - set(value):
        raise ValueError(label + " requires: " + ", ".join(sorted(set(required) - set(value))))
    if allowed is not None and set(value) - set(allowed):
        raise ValueError(label + " has unsupported fields: " + ", ".join(sorted(set(value) - set(allowed))))
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be explicit nonempty text.")


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + " must be a finite positive number.")


def _value_schema(attribute):
    kind = attribute["type"]
    result = {"type": {"enum": "string", "string_list": "array"}.get(kind, kind)}
    if kind in ("number", "integer"):
        result.update({key: attribute[key] for key in ("minimum", "maximum") if key in attribute})
    elif kind == "enum":
        result["enum"] = deepcopy(attribute["allowed_values"])
    elif kind == "string":
        result["minLength"] = 1
    elif kind == "string_list":
        result["items"] = {"type": "string", "minLength": 1}
        if "allowed_values" in attribute:
            result["items"]["enum"] = deepcopy(attribute["allowed_values"])
        result["uniqueItems"] = True
    return result


def _attribute_schema(attribute):
    value = _value_schema(attribute)
    properties = {
        "value": {"anyOf": [{"type": "null"}, value]},
        "status": {"enum": sorted(STATES)},
        "unit": {"const": attribute["unit"]},
        "qualifier": {"type": ["string", "null"]},
        "scope": {"enum": sorted(SCOPES)},
        "evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
        "method": {"type": "string", "minLength": 1},
        "review_status": {"enum": sorted(REVIEWS)},
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": list(properties), "properties": properties,
        "allOf": [
            {"if": {"properties": {"status": {"const": "known"}}},
             "then": {"properties": {"value": deepcopy(value), "evidence": {"minItems": 1}}}},
            {"if": {"properties": {"status": {"enum": ["unknown", "conflict", "not_applicable"]}}},
             "then": {"properties": {"value": {"type": "null"}}}},
            {"if": {"properties": {"status": {"enum": ["conflict", "not_applicable"]}}},
             "then": {"properties": {"evidence": {"minItems": 1}}}},
        ],
    }


def _product_schema(profile):
    nonempty = {"type": "string", "minLength": 1}
    properties = {key: {"const": profile[key]} for key in ("schema_version", "category", "market")}
    properties.update({key: deepcopy(nonempty) for key in
                       ("dataset_version", "source_dataset_version", "listing_id", "seller_uid", "source_key")})
    properties.update({
        "source_listing_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": deepcopy(nonempty)},
        "source_role": {"enum": ["brand", "retail", "unknown"]},
        "brand": {"type": ["string", "null"]}, "retailer": {"type": ["string", "null"]},
        "attributes": {"type": "object", "additionalProperties": False,
                       "required": list(profile["attributes"]),
                       "properties": {name: _attribute_schema(attribute)
                                      for name, attribute in profile["attributes"].items()}},
        "unmapped_claims": {"type": "array", "items": {"$ref": "#/$defs/unmapped"}},
        "review_status": {"enum": sorted(REVIEWS)},
    })
    evidence = {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/evidence"}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": profile["category"] + " standardized seller listing",
        "type": "object", "additionalProperties": False,
        "required": list(properties), "properties": properties,
        "$defs": {
            "evidence": {"type": "object", "additionalProperties": False,
                         "required": ["capture_id", "pointer"],
                         "properties": {"capture_id": deepcopy(nonempty),
                                        "pointer": {"type": "string", "pattern": "^(?:/(?:[^~/]|~[01])*)*$"}}},
            "unmapped": {"type": "object", "additionalProperties": False,
                         "required": ["value", "evidence", "reason"],
                         "properties": {"attribute": {"type": ["string", "null"]},
                                        "value": deepcopy(nonempty), "evidence": evidence,
                                        "reason": deepcopy(nonempty), "scope": {"enum": sorted(SCOPES)}}},
        },
    }


def build_contracts(definition):
    """Build five contracts without loading a bundled category or executing code.

    The caller supplies policy. Generated status records an unreviewed definition;
    producing a profile establishes neither source coverage nor model readiness.
    ``init_profile`` additionally validates the generated runtime contracts.
    """
    required = {"definition_format_version", "category", "market", "versions", "attributes",
                "standardization_rules", "mappings", "pipeline", "model_design"}
    optional = {"purpose", "category_boundaries"}
    _object(definition, "Profile definition", required | optional, required)
    if definition["definition_format_version"] != DEFINITION_FORMAT:
        raise ValueError("Profile definition requires definition_format_version " + DEFINITION_FORMAT)
    versions = _object(definition["versions"], "Definition versions",
                       {"schema", "mapping", "pipeline", "model_design"},
                       {"schema", "mapping", "pipeline", "model_design"})
    for name, value in versions.items():
        _text(value, "Definition " + name + " version")
    attributes = _object(definition["attributes"], "Definition attributes")
    if not attributes:
        raise ValueError("Definition attributes must be nonempty.")
    for name, attribute in attributes.items():
        _text(name, "Attribute name")
        _object(attribute, "Attribute " + name,
                {"type", "unit", "scope", "standardization_rule", "minimum", "maximum", "allowed_values",
                 "description", "model_role"}, {"type", "unit", "scope", "standardization_rule"})
        if attribute["type"] not in TYPES:
            raise ValueError("Attribute requires a supported declared type: " + name)
        if attribute["type"] == "enum" and "allowed_values" not in attribute:
            raise ValueError("Enum attribute requires allowed_values: " + name)
        if attribute["type"] not in {"number", "integer"} and {"minimum", "maximum"} & set(attribute):
            raise ValueError("Numeric bounds require a numeric attribute: " + name)
        if attribute["type"] not in {"enum", "string_list"} and "allowed_values" in attribute:
            raise ValueError("Vocabulary requires an enum or string_list attribute: " + name)
    rules = _object(definition["standardization_rules"], "Definition standardization_rules")
    for name, rule in rules.items():
        _text(name, "Standardization rule name")
        _text(rule, "Standardization rule description")
    mappings = _object(definition["mappings"], "Definition mappings",
                       {"aliases", "country_aliases", "quantity_units", "duration_units", "unit_conversions", "safety_rules"})
    pipeline = _object(definition["pipeline"], "Definition pipeline",
                       {"fields", "sections", "price", "quantity", "source_roles", "group_attribute", "discovery"},
                       {"fields", "sections", "price", "quantity", "source_roles", "group_attribute"})
    group = pipeline["group_attribute"]
    if not isinstance(group, str) or group not in attributes or attributes[group]["type"] not in {"string", "enum"}:
        raise ValueError("Pipeline group_attribute must reference a declared string or enum attribute.")
    for field in pipeline["fields"] if isinstance(pipeline["fields"], list) else []:
        _object(field, "Pipeline field", {"attribute", "pointer", "unit", "scope", "qualifier", "skip_values"},
                {"attribute", "pointer"})
    quantity = _object(pipeline["quantity"], "Pipeline quantity", {"attribute", "unit", "base_quantity"},
                       {"attribute", "unit", "base_quantity"})
    _positive(quantity["base_quantity"], "Pipeline quantity base_quantity")
    price = _object(pipeline["price"], "Pipeline price",
                    {"amount_pointer", "regular_price_pointer", "reference_price_pointer", "currency_pointer",
                     "observed_at_pointer", "available_pointer", "tax_basis_pointer", "currency", "price_unit", "minor_unit_factor"},
                    {"amount_pointer", "price_unit"})
    if "currency_pointer" not in price and "currency" not in price:
        raise ValueError("Pipeline price requires explicit currency or currency_pointer.")
    if "currency" in price:
        _text(price["currency"], "Pipeline price currency")
    if "minor_unit_factor" in price:
        _positive(price["minor_unit_factor"], "Pipeline price minor_unit_factor")
    elif price["price_unit"] == "minor":
        raise ValueError("Minor-unit authoring requires explicit price.minor_unit_factor.")
    for role in pipeline["source_roles"].values() if isinstance(pipeline["source_roles"], dict) else []:
        _object(role, "Pipeline source role", {"source_role", "retailer"}, {"source_role"})
    model = _object(definition["model_design"], "Definition model_design",
                    {"target", "predictors", "eligibility", "attribute_policies", "preprocessing", "validation", "interpretation"},
                    {"target", "predictors"})
    target = _object(model["target"], "Model target",
                     {"name", "currency", "unit", "quantity_attribute", "base_quantity", "price_basis", "tax_basis"},
                     {"name", "currency", "unit", "quantity_attribute", "base_quantity", "price_basis", "tax_basis"})
    for key in ("name", "currency", "unit", "quantity_attribute", "price_basis", "tax_basis"):
        _text(target[key], "Model target " + key)
    if target["name"] != "log_regular_unit_price" or target["price_basis"] != "regular":
        raise ValueError("Model target currently supports log_regular_unit_price with regular price_basis.")
    _positive(target["base_quantity"], "Model target base_quantity")
    for name, predictor in _object(model["predictors"], "Model predictors").items():
        _object(predictor, "Model predictor " + name,
                {"type", "required", "missing_policy", "transform", "reference", "allowed_values", "unit", "minimum", "maximum"},
                {"type", "required", "missing_policy", "transform"})
        for bound in ("minimum", "maximum"):
            if bound in predictor:
                value = predictor[bound]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Model predictor bounds must be finite numeric values: " + name)
        if "minimum" in predictor and "maximum" in predictor and predictor["minimum"] > predictor["maximum"]:
            raise ValueError("Model predictor bounds are inverted: " + name)
    _predictor_definitions(model)
    if "eligibility" in model:
        eligibility = _object(model["eligibility"], "Model eligibility", {"allowed_tax_bases"}, {"allowed_tax_bases"})
        tax_bases = eligibility["allowed_tax_bases"]
        if tax_bases != [target["tax_basis"]]:
            raise ValueError("Model allowed_tax_bases must contain only the explicit target tax_basis.")
    if "attribute_policies" in model:
        for name, policy in _object(model["attribute_policies"], "Model attribute_policies").items():
            if name not in attributes:
                raise ValueError("Model attribute policies must reference declared attributes: " + name)
            _object(policy, "Model attribute policy " + name, {"supported_scopes", "supported_qualifiers"},
                    {"supported_scopes", "supported_qualifiers"})
            if (not isinstance(policy["supported_scopes"], list) or not policy["supported_scopes"]
                    or any(scope not in SCOPES for scope in policy["supported_scopes"])):
                raise ValueError("Model attribute policies require supported scopes: " + name)
            qualifiers = policy["supported_qualifiers"]
            if not isinstance(qualifiers, list) or not qualifiers or any(value is not None and not isinstance(value, str) for value in qualifiers):
                raise ValueError("Model attribute policies require text or null qualifiers: " + name)
    for name in ("preprocessing", "validation", "interpretation"):
        if name in model:
            _object(model[name], "Model " + name)
    if model.get("interpretation", {}).get("regression_fitted", False) is not False:
        raise ValueError("Profile authoring cannot declare a fitted regression.")
    context = {"category": definition["category"], "market": definition["market"], "schema_version": versions["schema"]}
    profile = {**context, "status": "authored_profile_pending_evidence_review", "attribute_count": len(attributes),
               "attributes": deepcopy(attributes), "standardization_rules": deepcopy(rules)}
    profile.update({key: deepcopy(definition[key]) for key in optional if key in definition})
    design = {**deepcopy(model), **context, "model_design_version": versions["model_design"], "status": "specified_not_trained"}
    design.setdefault("eligibility", {"allowed_tax_bases": [target["tax_basis"]]})
    return {
        "profile.json": profile,
        "source-mappings.json": {**deepcopy(mappings), "schema_version": versions["schema"], "mapping_version": versions["mapping"]},
        "model-design.json": design,
        "product.schema.json": _product_schema(profile),
        "pipeline.json": {**deepcopy(pipeline), **context, "pipeline_version": versions["pipeline"],
                          "pipeline_format_version": PROFILE_FORMAT, "review_format_version": REVIEW_FORMAT, "adapter": "structured"},
    }


def init_profile(definition, output):
    """Validate then publish a new profile folder; never replace existing contracts."""
    requested = Path(output).expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise ValueError("Profile output already exists; choose a new versioned folder.")
    contracts = build_contracts(definition)
    output = requested.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".category-profile-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for name, value in contracts.items():
            (staging / name).write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n",
                                        encoding="utf-8")
        profile, unused_mappings, unused_design, unused_recipe, fingerprints = load_profile(staging)
        try:
            output.mkdir(exist_ok=False)
        except FileExistsError as error:
            raise ValueError("Profile output already exists; choose a new versioned folder.") from error
        published = []
        try:
            for name in CONTRACT_FILES:
                (staging / name).rename(output / name)
                published.append(output / name)
        except OSError:
            for path in published:
                path.unlink()
            output.rmdir()
            raise
    return {"status": "profile_initialized", "category": profile["category"], "market": profile["market"],
            "schema_version": profile["schema_version"], "attribute_count": profile["attribute_count"],
            "contract_sha256": fingerprints, "output": str(output)}
