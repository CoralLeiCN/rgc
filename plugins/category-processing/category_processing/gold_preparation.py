"""Apply an explicit study contract to verified Silver facts downstream in Gold."""

import hashlib
import math
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from .adapters import _group
from .archive import aware_time, digest, inside, json_bytes, read_json, sha256
from .model import _predictor_value
from .silver_contracts import METHODS, result_state
from .silver_snapshot import no_links, publish, read_rows, row_bytes, verified_snapshot
from .source_index import encoded

FORMAT = "category-gold-preparation-2"


def selected_value(facts, field, design):
    selector = design.get("silver_contexts", {}).get(field, {"scope": "product", "qualifier": None})
    selected = [item for item in facts if item["field"] == field
                and all(item["context"].get(key) == value for key, value in selector.items())]
    if (len(selected) != 1 or result_state(selected[0]["result"]) != "available"
            or selected[0]["method"] not in design.get("accepted_silver_methods", METHODS)):
        return None
    return selected[0]["result"]


def prepare_values(root, manifest, design, relationships):
    profile = read_json(root / "profile.json")
    if design.get("schema_version") != profile["schema_version"]:
        raise ValueError("Gold design must explicitly select this Silver schema version.")
    target = design["target"]
    basis = target.get("price_basis_contract_version")
    if basis not in ("current-consumer-price-1", "regular-consumer-price-1"):
        raise ValueError("Gold requires an explicit supported current or regular price policy.")
    expected_policy = {"price_basis": "current_displayed", "tax_basis": "as_displayed", "promotion_basis": "as_displayed", "fallback_policy": "reject"} if basis == "current-consumer-price-1" else {
        "price_basis": "regular", "tax_basis": "consumer_tax_included", "promotion_basis": "non_promotional", "fallback_policy": "reject"}
    if any(target.get(key) != value for key, value in expected_policy.items()):
        raise ValueError("Gold target policy metadata disagrees with its selected price basis.")
    quantity = target["quantity_attribute"]
    base = target["base_quantity"]
    if type(base) not in (int, float) or not math.isfinite(base) or base <= 0 or quantity not in profile["attributes"]:
        raise ValueError("Gold requires a positive unit normalization and a Silver quantity field.")
    if not design.get("predictors"):
        raise ValueError("Gold requires explicit predictor definitions.")
    methods = design.get("accepted_silver_methods", sorted(METHODS))
    if not isinstance(methods, list) or not methods or any(method not in METHODS for method in methods):
        raise ValueError("Gold must explicitly accept supported Silver methods.")
    facts = read_rows(root / "facts.jsonl")
    by_subject = defaultdict(list)
    for fact in facts:
        if fact["is_current"] and fact["subject_kind"] == "listing":
            by_subject[fact["subject_id"]].append(fact)
    prices = defaultdict(list)
    for price in read_rows(root / "prices.jsonl"):
        if price["is_current"]:
            prices[price["subject_id"]].append(price)
    assignments = {}
    if relationships.get("format_version") != "category-gold-relationships-1":
        raise ValueError("Gold relationships require their versioned evidence contract.")
    for item in relationships.get("assignments", []):
        subject = item["subject_id"]
        required = ("family_id", "variant_id", "reason", "reviewed_by", "name_guard")
        if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required) or not item.get("source"):
            raise ValueError("Gold relationships require stable IDs, source evidence and a recorded decision.")
        if subject in assignments:
            raise ValueError("Conflicting Gold relationship assignments require resolution.")
        assignments[subject] = item
    source_roles = read_json(root / "pipeline.json").get("source_roles", {})
    candidates, observations, audit = [], [], []
    for subject, current in sorted(by_subject.items()):
        name = selected_value(current, "identity.name", design)
        relationship = assignments.get(subject)
        refs = {encoded(ref) for item in facts if item["subject_id"] == subject for ref in item["source"]}
        if relationship and (relationship["name_guard"] != name or any(encoded(ref) not in refs for ref in relationship["source"])):
            raise ValueError("Gold relationship no longer matches this subject's source evidence.")
        source_role = current[0]["source_role"]
        comparison = selected_value(current, design.get("group_attribute", "identity.product_group"), design)
        if comparison is None and design.get("comparison_rule") == "chocolate_name_group-1":
            comparison = _group(name or "", "", "")["value"]
        retailer = source_roles.get(current[0]["source_key"], {}).get("retailer")
        features = {}
        for field in design["predictors"]:
            value = selected_value(current, field, design)
            if field == "identity.source_role":
                value = source_role
            elif field == "identity.product_group":
                value = comparison
            elif field == "identity.retailer" and value is None:
                value = retailer
            features[field] = value
        mass = selected_value(current, quantity, design)
        source_prices = defaultdict(list)
        for price in prices[subject]:
            source_prices[price["observation_id"]].append(price)
        if not source_prices:
            source_prices["missing-price-" + digest([subject, current[0]["capture_id"]])[:32]] = []
        for observation, alternatives in sorted(source_prices.items()):
            exclusions = []
            if not relationship:
                exclusions.append("product_family_unresolved")
            if not comparison:
                exclusions.append("comparison_group_unresolved")
            if len(source_prices) != 1:
                exclusions.append("multiple_current_price_observations")
            for field, definition in design["predictors"].items():
                try:
                    _predictor_value(features[field], field, definition)
                except (ValueError, TypeError):
                    exclusions.append("predictor_unresolved:" + field)
            semantics = {encoded({key: price.get(key) for key in ("displayed_price", "regular_price", "currency", "observed_at", "available", "tax_basis")})
                         for price in alternatives}
            price = deepcopy(alternatives[0]) if alternatives else {}
            if len(semantics) > 1:
                exclusions.append("price_conflict")
                price["displayed_price"] = price["regular_price"] = None
            amount = price.get("displayed_price" if basis == "current-consumer-price-1" else "regular_price")
            def valid(value):
                return type(value) in (int, float) and math.isfinite(value) and value > 0
            normalized = amount / mass * base if valid(amount) and valid(mass) and price.get("currency") == target["currency"] else None
            if normalized is None or not math.isfinite(normalized) or normalized <= 0:
                normalized = None
                exclusions.append("price_or_quantity_unresolved")
            if basis == "regular-consumer-price-1" and price.get("tax_basis") != "consumer_tax_included":
                exclusions.append("regular_price_tax_basis_unresolved")
            if design.get("require_observation_time", True) and not aware_time(price.get("observed_at")):
                exclusions.append("observation_time_unresolved")
            if design.get("require_available", True) and price.get("available") is not True:
                exclusions.append("availability_unresolved")
            unit_field = "current_price_per_100g_gbp" if basis == "current-consumer-price-1" else "regular_price_per_100g_gbp"
            # Portable contracts can declare their own physical quantity and currency names.
            unit_field = target.get("normalized_field", unit_field if target["currency"] == "GBP" and base == 100 else "normalized_unit_price")
            log_field = target.get("log_field", "log_" + unit_field)
            targets = {unit_field: normalized, log_field: math.log(normalized) if normalized else None}
            if target.get("legacy_alias_fields"):
                targets.update(dict(zip(target["legacy_alias_fields"], [normalized, math.log(normalized) if normalized else None])))
            row = {"observation_id": observation, "listing_id": subject,
                   "variant_id": relationship["variant_id"] if relationship else None,
                   "family_id": relationship["family_id"] if relationship else None,
                   "comparable_group": comparison, "source_role": source_role,
                   "dataset_version": manifest["dataset_version"], "source_dataset_version": manifest["identity"]["raw_inputs_sha256"],
                   "schema_version": profile["schema_version"], "predictors": features, "target": targets}
            candidates.append(row)
            observations.append({**price, **{key: row[key] for key in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")},
                                 "total_edible_weight_g": mass, "normalized_price": normalized})
            audit.append({"observation_id": observation, "eligible": not exclusions, "exclusion_reasons": sorted(set(exclusions))})
    eligible_ids = {item["observation_id"] for item in audit if item["eligible"]}
    return candidates, [row for row in candidates if row["observation_id"] in eligible_ids], observations, audit


def prepare_gold(silver_root, output, model_design, relationships=None):
    root, manifest = verified_snapshot(silver_root)
    output = no_links(output)
    if inside(output, root) or inside(root, output):
        raise ValueError("Gold output must be separate from Silver.")
    if read_json(root / "quality-report.json")["status"] != "complete_snapshot":
        raise ValueError("Gold requires a complete Silver build.")
    design = read_json(model_design) if isinstance(model_design, (str, Path)) else deepcopy(model_design)
    relations = (read_json(relationships) if isinstance(relationships, (str, Path)) else deepcopy(relationships)) or {
        "format_version": "category-gold-relationships-1", "assignments": []}
    candidates, selected, prices, audit = prepare_values(root, manifest, design, relations)
    identity = {"format_version": FORMAT, "silver_manifest_sha256": sha256(root / "manifest.json"),
                "model_design_sha256": digest(design), "relationships_sha256": digest(relations),
                "implementation_sha256": {path.name: sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))}}
    version = "gold-preparation-" + digest(identity)[:24]
    report = {"format_version": FORMAT, "dataset_version": version, "silver_dataset_version": manifest["dataset_version"],
              "schema_version": design["schema_version"], "status": "inputs_prepared", "release_ready": False,
              "counts": {"training_candidates": len(candidates), "eligible_model_inputs": len(selected)},
              "exclusion_counts": dict(Counter(reason for item in audit for reason in item["exclusion_reasons"])),
              "price_target_policy": design["target"], "limitations": design.get("price_target_limitations", [])}
    files = {"inputs/silver-manifest.json": (root / "manifest.json").read_bytes(),
             "model-design.json": json_bytes(design), "relationships.json": json_bytes(relations),
             "training-candidates.jsonl": row_bytes(candidates), "model-inputs.jsonl": row_bytes(selected),
             "prices.jsonl": row_bytes(prices), "eligibility.jsonl": row_bytes(audit), "report.json": json_bytes(report)}
    # Keep all Silver inputs available for independent semantic replay without Bronze or mutable caches.
    files.update({"inputs/silver/" + name: (root / name).read_bytes() for name in manifest["managed_files"]})
    files["inputs/silver/manifest.json"] = files["inputs/silver-manifest.json"]
    metadata = {"manifest_format_version": FORMAT, "dataset_version": version, "identity": identity,
                "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)}
                                  for name, data in files.items()}}
    files["manifest.json"] = json_bytes(metadata)
    verified_snapshot(root)
    destination = publish(output, version, files)
    return {**report, "output": str(destination)}
