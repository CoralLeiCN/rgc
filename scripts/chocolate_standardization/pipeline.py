"""Build schema-governed attributes and reviewed pricing inputs after deduplication."""

import hashlib
import json
import math
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import dataset_contracts as contract_module
from chocolate_cleanup.adapters import extract_capture
from chocolate_cleanup.core import aware_time, normalized, pointer_value, positive
from chocolate_cleanup.deduplication import digest, inside, json_bytes
from chocolate_model import (
    ModelContractError,
    _predictor_value,
    regular_price_basis_supported,
    validate_target_policy,
)
from chocolate_tables import get_table_backend
from dataset_contracts import SCHEMA_REFERENCE, resolve_contract_root

from .identity import (
    MAPPING_VERSION,
    TAXONOMY_VERSION,
    IdentityMapper,
    load_identity_mappings,
)
from .values import (
    standardize_value,
    unknown_attribute,
    validate_attribute_contract,
    validate_evidence,
    validate_product,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "chocolate-schema-1"
REVIEW_VERSION = "chocolate-schema-reviews-1"
FEATURE_MAP = {
    "name": "identity.name", "brand": "identity.brand",
    "source_product_id": "identity.source_product_id", "source_variant_id": "identity.source_variant_id",
    "gtin": "identity.gtin", "chocolate_type": "composition.chocolate_type",
    "cocoa_percentage": "composition.cocoa_percentage", "nuts_as_ingredient": "composition.nuts_presence",
    "may_contain_nuts": "composition.may_contain_nuts_presence",
    "fairtrade_claim": "certifications.fairtrade_claim", "fair_trade_claim": "certifications.fair_trade_claim",
    "organic_claim": "certifications.organic_claim", "vegan_claim": "dietary.vegan_claim",
    "ingredients_text": "composition.ingredients_text", "allergen_text": "composition.allergen_text",
    "nutrition_text": "nutrition.source_text", "claim_text": "marketing.claim_text",
}


def read_json(path):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(path.read_bytes(), parse_constant=reject)


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def load_contract(schema_root=None, *, offline=False):
    schema_root = resolve_contract_root(schema_root, offline=offline)
    paths = {name: schema_root / name for name in ("profile.json", "source-mappings.json", "model-design.json", "product.schema.json")}
    documents = {name: read_json(path) for name, path in paths.items()}
    profile, mappings, design = (documents[name] for name in ("profile.json", "source-mappings.json", "model-design.json"))
    reference_path = schema_root / "dataset-contract.json"
    reference = contract_module.load_manifest(reference_path) if reference_path.is_file() else None
    if reference is None:
        pinned_reference = contract_module.load_manifest(SCHEMA_REFERENCE)
        if schema_root.resolve() == contract_module.cache_directory(pinned_reference, contract_module.SCHEMA_CACHE).resolve():
            reference = pinned_reference
    if reference is not None:
        if set(reference["files"]) != set(paths) or reference["contract_set"] != "chocolate":
            raise ValueError("The chocolate dataset reference must identify all four chocolate contracts.")
        metadata = {"category": profile.get("category"), "market": profile.get("market"),
                    "schema_version": profile.get("schema_version"), "attribute_count": profile.get("attribute_count"),
                    "mapping_version": mappings.get("mapping_version"),
                    "model_design_version": design.get("model_design_version")}
        for name, value in metadata.items():
            if reference.get(name) != value:
                raise ValueError("Category contracts differ from dataset reference metadata: " + name)
    if any(doc.get("schema_version") != SCHEMA_VERSION for doc in (profile, mappings, design)):
        raise ValueError("Category contracts must agree on " + SCHEMA_VERSION)
    if documents["product.schema.json"]["properties"]["schema_version"].get("const") != SCHEMA_VERSION:
        raise ValueError("Product validation contract disagrees with the profile.")
    attributes = profile["attributes"]
    validation_attributes = documents["product.schema.json"]["properties"]["attributes"]
    if profile.get("attribute_count") != len(attributes) or set(validation_attributes["properties"]) != set(attributes) or set(validation_attributes["required"]) != set(attributes):
        raise ValueError("Category profile and product validator attribute catalogs disagree.")
    if set(mappings.get("aliases", {})) - set(attributes) or set(design["predictors"]) - set(attributes):
        raise ValueError("Mappings and model predictors must reference declared attributes.")
    identity_contract = mappings.get("product_identity", {})
    if identity_contract.get("mapping_format_version") != MAPPING_VERSION or identity_contract.get("taxonomy_version") != TAXONOMY_VERSION:
        raise ValueError("Source mappings must declare the supported product identity taxonomy.")
    validate_target_policy(design.get("target"))
    if any(definition.get("standardization_rule") not in profile["standardization_rules"] for definition in attributes.values()):
        raise ValueError("Every tracked attribute needs a declared standardization rule.")
    for name, definition in attributes.items():
        validate_attribute_contract(name, definition, validation_attributes["properties"][name])
    return profile, mappings, design, {name: sha256(path) for name, path in paths.items()}


def verify_snapshot(root):
    path = root / "manifest.json"
    manifest = read_json(path)
    if manifest.get("manifest_format_version") != "chocolate-raw-deduplication-manifest-1":
        raise ValueError("Input must be a deduplicated raw snapshot, not a cleaned or raw archive.")
    files = manifest.get("managed_files")
    if not isinstance(files, dict) or "products.jsonl" not in files:
        raise ValueError("Deduplicated snapshot manifest has no product table.")
    for name, metadata in files.items():
        target = root / name
        if not inside(target.resolve(), root) or target.is_symlink():
            raise ValueError("Snapshot file reference escapes its root.")
        if target.stat().st_size != metadata["byte_length"] or sha256(target) != metadata["sha256"]:
            raise ValueError("Deduplicated snapshot checksum mismatch: " + name)
    return manifest, sha256(path)


def load_reviews(reviews):
    if reviews is None:
        return {"review_format_version": REVIEW_VERSION, "products": {}, "prices": {}}
    result = deepcopy(reviews) if isinstance(reviews, dict) else read_json(Path(reviews).resolve())
    if result.get("review_format_version") != REVIEW_VERSION:
        raise ValueError("Schema reviews require " + REVIEW_VERSION)
    for key in ("products", "prices"):
        if not isinstance(result.get(key, {}), dict):
            raise ValueError("Review " + key + " must be an object.")
    return result


def validate_review(review, captures):
    if not isinstance(review, dict):
        raise ValueError("Review decisions must be objects.")
    for key in ("reviewed_by", "reason"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError("Every review requires a nonempty " + key)
    refs = review.get("evidence")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Every review requires evidence within this listing's captures.")
    validate_evidence(refs)
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("capture_id") not in captures:
            raise ValueError("Review cites a capture outside this source listing.")
        try:
            pointer_value(captures[ref["capture_id"]], ref.get("pointer"))
        except (KeyError, IndexError, ValueError, TypeError):
            raise ValueError("Review evidence pointer does not resolve.")


def evidence(capture, pointer):
    pointer_value(capture, pointer)
    return {"capture_id": capture["capture_id"], "pointer": pointer}


def candidate_attribute(name, value, capture, pointer, method, profile, mappings, unit=None, qualifier=None, scope=None):
    normalized_value = standardize_value(name, value, profile, mappings, unit)
    return {"value": normalized_value, "status": "known", "unit": profile["attributes"][name].get("unit"),
            "qualifier": qualifier, "scope": scope or profile["attributes"][name].get("scope", "product"),
            "evidence": [evidence(capture, pointer)], "method": method, "review_status": "unreviewed"}


def selected_attribute(name, values, profile):
    if not values:
        return unknown_attribute(profile["attributes"][name])
    semantics = {digest({"value": item["value"], "qualifier": item["qualifier"], "scope": item["scope"]}) for item in values}
    if len(semantics) > 1:
        result = unknown_attribute(profile["attributes"][name])
        result.update(status="conflict", method="conflicting_source_assertions",
                      evidence=[ref for item in values for ref in item["evidence"]], review_status="needs_review")
        return result
    result = deepcopy(values[0])
    result["evidence"] = list({(ref["capture_id"], ref["pointer"]): ref for item in values for ref in item["evidence"]}.values())
    return result


def build_standardized_dataset(deduplicated_root, output, reviews=None, schema_root=None, offline=False,
                               family_mappings=None, *, table_backend="stdlib"):
    source = Path(deduplicated_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if inside(output, source) or inside(source, output):
        raise ValueError("Standardized output must not overlap the deduplicated input.")
    tables = get_table_backend(table_backend)
    runtime = tables.runtime()
    schema_root = resolve_contract_root(schema_root, offline=offline)
    profile, mappings, design, contract_hashes = load_contract(schema_root, offline=offline)
    manifest, manifest_hash = verify_snapshot(source)
    source_report = read_json(source / "quality-report.json") if "quality-report.json" in manifest["managed_files"] else {}
    decisions = load_reviews(reviews)
    identity_decisions = load_identity_mappings(family_mappings)
    identity_mapper = IdentityMapper(identity_decisions)
    implementation_paths = [Path(__file__), Path(__file__).with_name("values.py"),
                            Path(__file__).with_name("identity.py"),
                            ROOT / "scripts/chocolate_cleanup/adapters.py", ROOT / "scripts/chocolate_cleanup/core.py",
                            ROOT / "scripts/chocolate_cleanup/deduplication.py", ROOT / "scripts/chocolate_model.py",
                            ROOT / "scripts/chocolate_tables.py",
                            ROOT / "scripts/dataset_contracts.py",
                            ROOT / "plugins/category-processing/category_processing/dataset_contracts.py", SCHEMA_REFERENCE]
    implementation = {str(path.relative_to(ROOT)): sha256(path) for path in implementation_paths}
    version = "standardized-" + digest({"input_manifest": manifest_hash, "contracts": contract_hashes,
                                        "reviews": decisions, "identity_mappings": identity_decisions,
                                        "implementation": implementation, "processing_runtime": runtime})[:24]
    products, assertions, prices, candidates, queue = [], [], [], [], []
    seen_listings, seen_prices = set(), set()
    errors, unmapped_count = [], 0
    with (source / "products.jsonl").open(encoding="utf-8") as product_stream:
        for line in product_stream:
            row = json.loads(line)
            listing = row["listing_id"]
            if listing in seen_listings:
                raise ValueError("Deduplicated input has duplicate canonical listing IDs.")
            seen_listings.add(listing)
            captures = {cap["capture_id"]: cap for cap in row["captures"]}
            if len(captures) != len(row["captures"]) or row["latest_capture_id"] not in captures:
                raise ValueError("Deduplicated input has invalid capture IDs.")
            latest = captures[row["latest_capture_id"]]
            current = defaultdict(list)
            price_index, unmapped = {}, []

            def add(name, value, capture, pointer, method, **kwargs):
                if value is None or value == "unknown":
                    return
                if value == []:
                    retain_unmapped(name, value, capture, pointer, "empty_list_does_not_establish_absence")
                    return
                if name not in profile["attributes"]:
                    retain_unmapped(name, value, capture, pointer, "profile_mapping_missing")
                    return
                try:
                    attribute = candidate_attribute(name, value, capture, pointer, method, profile, mappings, **kwargs)
                    assertion = {"listing_id": listing, "attribute": name, **attribute,
                                 "is_current": capture["capture_id"] == row["latest_capture_id"],
                                 "raw_value": value, "schema_version": SCHEMA_VERSION, "dataset_version": version}
                    assertions.append(assertion)
                    if assertion["is_current"]:
                        current[name].append(attribute)
                except (ValueError, KeyError, TypeError) as error:
                    retain_unmapped(name, value, capture, pointer, "standardization_failed")
                    queue.append({"listing_id": listing, "attribute": name, "reason": "standardization_failed", "details": str(error),
                                  "raw_value": value, "evidence": [evidence(capture, pointer)]})

            def retain_unmapped(name, value, capture, pointer, reason):
                claim = {"attribute": name, "value": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False),
                         "evidence": [evidence(capture, pointer)], "reason": reason}
                if not claim["value"]:
                    return
                unmapped.append(claim)
                queue.append({"listing_id": listing, **claim, "reason": "unmapped_claim", "unmapped_reason": reason})

            for capture in captures.values():
                try:
                    extracted = extract_capture(capture)
                except (ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
                    errors.append({"listing_id": listing, "capture_id": capture["capture_id"], "error": str(error)})
                    continue
                for item in extracted.get("features", []):
                    name = FEATURE_MAP.get(item["name"])
                    if name:
                        scope = "ingredient" if item.get("scope") == "source_declared_chocolate" else None
                        add(name, item.get("value"), capture, item["raw_pointer"], item["method"],
                            unit=item.get("unit"), qualifier=item.get("qualifier"), scope=scope)
                group = extracted.get("group") or {}
                if group.get("value"):
                    add("identity.product_group", group["value"], capture, group["raw_pointer"], group["method"])
                for quantity in extracted.get("quantities", []):
                    add("quantity.total_edible_weight_g", quantity.get("total_edible_weight_g"), capture, quantity["raw_pointer"], quantity["method"], unit="g")
                    add("quantity.pack_count", quantity.get("pack_count"), capture, quantity["raw_pointer"], quantity["method"])
                raw = capture["raw_record"]
                information = raw.get("information") if isinstance(raw.get("information"), dict) else {}
                selected = information.get("selected_variant") if isinstance(information.get("selected_variant"), dict) else {}
                for key, name in (("sku", "identity.sku"), ("title", "identity.variant_name")):
                    value = selected.get(key)
                    if value and value != "Default Title":
                        add(name, str(value), capture, "/raw_record/information/selected_variant/" + key, "structured_variant_field")
                product = information.get("shopify_product", information)
                if isinstance(product, dict):
                    base = "/raw_record/information/shopify_product" if "shopify_product" in information else "/raw_record/information"
                    for key, name in (("product_type", "identity.source_product_type"), ("tags", "marketing.source_tags")):
                        if product.get(key):
                            add(name, product[key], capture, base + "/" + key, "structured_catalogue_field")
                # Recognized structured fields carry their own explicit semantics.
                direct_sections = (("nutrition_per_100g", "nutrition"), ("origin", "origin"), ("packaging", "packaging"), ("storage", "storage"), ("composition", "composition"), ("dietary", "dietary"), ("certifications", "certifications"), ("processing", "processing"), ("marketing", "marketing"))
                for section, family in direct_sections:
                    values = information.get(section)
                    if not isinstance(values, dict):
                        continue
                    for key, value in values.items():
                        name = family + "." + key
                        add(name, value, capture, "/raw_record/information/" + section + "/" + key, "explicit_structured_source_field")
                for item in extracted.get("prices", []):
                    qs = item.get("quantities", extracted.get("quantities", []))
                    weights = {positive(q.get("total_edible_weight_g")) for q in qs if positive(q.get("total_edible_weight_g")) is not None}
                    weight = next(iter(weights)) if len(weights) == 1 else None
                    price = {key: deepcopy(value) for key, value in item.items() if key not in ("raw_pointer", "quantities")}
                    price.update(listing_id=listing, source_key=row["source_key"], source_role=row["source_role"],
                                 brand=row.get("brand"), retailer=row.get("retailer"), total_edible_weight_g=weight,
                                 quantity_status="conflict" if len(weights) > 1 else "known" if weight else "unknown")
                    signature = deepcopy(price)
                    if not price.get("observed_at"):
                        signature["unknown_time_capture_id"] = capture["capture_id"]
                    pid = "observation-" + digest(signature)[:24]
                    if pid in price_index:
                        price_index[pid]["evidence"].append(evidence(capture, item["raw_pointer"]))
                    else:
                        price.update(observation_id=pid, evidence=[evidence(capture, item["raw_pointer"])],
                                     quantity_evidence=[evidence(capture, q["raw_pointer"]) for q in qs])
                        price_index[pid] = price
            identity_pointer = "/raw_record/source_key" if "source_key" in latest["raw_record"] else "/raw_record"
            for name, value in (("identity.retailer", row.get("retailer")), ("identity.source_role", row.get("source_role")), ("identity.brand", row.get("brand"))):
                add(name, value, latest, identity_pointer, "deduplicated_source_context")
            attributes = {name: selected_attribute(name, current.get(name, []), profile) for name in profile["attributes"]}
            mapped_attributes = identity_mapper.apply(row, captures)
            attributes.update(mapped_attributes)
            for name, attribute in mapped_attributes.items():
                assertions.append({"listing_id": listing, "attribute": name, **deepcopy(attribute),
                                   "is_current": True, "raw_value": attribute["value"],
                                   "schema_version": SCHEMA_VERSION, "dataset_version": version})
            decision = decisions.get("products", {}).get(listing)
            if decision:
                validate_review(decision, captures)
                permitted = {"variant_id", "family_id", "in_scope", "attributes", "reviewed_by", "reason", "evidence"}
                if set(decision) - permitted:
                    raise ValueError("Unknown schema product review field.")
                for identifier in ("variant_id", "family_id"):
                    if identifier in decision and (not isinstance(decision[identifier], str) or not decision[identifier].strip()):
                        raise ValueError("Reviewed product identity must be nonempty.")
                if "in_scope" in decision and type(decision["in_scope"]) is not bool:
                    raise ValueError("Reviewed in_scope must be boolean.")
                reviewed_attributes = decision.get("attributes", {})
                if not isinstance(reviewed_attributes, dict) or set(reviewed_attributes) - set(attributes):
                    raise ValueError("Attribute review refers to undefined category fields.")
                for name, review in reviewed_attributes.items():
                    validate_review(review, captures)
                    if set(review) - {"value", "status", "qualifier", "scope", "reviewed_by", "reason", "evidence"}:
                        raise ValueError("Unknown schema attribute review field.")
                    status = review.get("status", "known")
                    if status not in ("known", "unknown", "not_applicable", "conflict"):
                        raise ValueError("Invalid reviewed attribute state.")
                    value = standardize_value(name, review.get("value"), profile, mappings) if status == "known" else None
                    if status == "known" and value is None:
                        raise ValueError("Known attribute review requires a value.")
                    if status != "known" and review.get("value") is not None:
                        raise ValueError("Unresolved attribute review must not select a value.")
                    if name in mapped_attributes and mapped_attributes[name]["status"] == "known" and (status != "known" or value != mapped_attributes[name]["value"]):
                        raise ValueError("Attribute review contradicts its registered identity mapping.")
                    attributes[name] = {"value": value, "status": status, "unit": profile["attributes"][name].get("unit"),
                                        "qualifier": review.get("qualifier"), "scope": review.get("scope", profile["attributes"][name].get("scope", "product")),
                                        "evidence": deepcopy(review["evidence"]), "method": "evidence_backed_review",
                                        "review_status": "reviewed"}
                    assertions.append({"listing_id": listing, "attribute": name, **deepcopy(attributes[name]),
                                       "is_current": True, "raw_value": review.get("value"),
                                       "schema_version": SCHEMA_VERSION, "dataset_version": version})
                relationship_fields = (("variant_id", "identity.physical_product_id"), ("family_id", "identity.product_family_id"))
                for field, name in relationship_fields:
                    if field in decision:
                        if name in mapped_attributes and attributes[name]["status"] == "known" and attributes[name]["value"] != decision[field]:
                            raise ValueError("Product review contradicts its registered identity mapping.")
                        if name in reviewed_attributes and attributes[name]["value"] != decision[field]:
                            raise ValueError("Reviewed relationship IDs contradict the product attributes.")
                        attributes[name] = {"value": decision[field], "status": "known", "unit": None, "qualifier": None,
                                            "scope": "product", "evidence": deepcopy(decision["evidence"]),
                                            "method": "evidence_backed_review", "review_status": "reviewed"}
                if "in_scope" in decision:
                    name = "identity.boundary_status"
                    boundary = "in_scope" if decision["in_scope"] else "out_of_scope"
                    if name in reviewed_attributes and attributes[name]["value"] != boundary:
                        raise ValueError("Reviewed category scope contradicts the boundary attribute.")
                    attributes[name] = {"value": boundary, "status": "known", "unit": None, "qualifier": None,
                                        "scope": "product", "evidence": deepcopy(decision["evidence"]),
                                        "method": "evidence_backed_review", "review_status": "reviewed"}
            family = attributes["identity.product_family_id"]
            physical = attributes["identity.physical_product_id"]
            registered_physical = identity_decisions["physical_products"].get(physical["value"])
            if family["status"] == "known" and physical["status"] == "known" and registered_physical and registered_physical["family_id"] != family["value"]:
                raise ValueError("Reviewed identity attributes contradict the registered physical product family.")
            product = {"schema_version": SCHEMA_VERSION, "dataset_version": version,
                       "source_dataset_version": manifest["dataset_version"], "listing_id": listing,
                       "source_listing_ids": row["source_listing_ids"], "source_role": row["source_role"], "source_key": row["source_key"],
                       "brand": row.get("brand"), "retailer": row.get("retailer"), "attributes": attributes,
                       "unmapped_claims": unmapped, "review_status": "reviewed" if decision else "unreviewed"}
            validate_product(product, profile, mappings)
            identity_mapper.add_packet_member(row, captures, attributes)
            products.append(product)
            unmapped_count += len(unmapped)
            for name, attribute in attributes.items():
                if attribute["status"] in ("conflict", "unknown"):
                    queue.append({"listing_id": listing, "attribute": name, "reason": attribute["status"]})
                elif name in design["predictors"] and attribute["review_status"] != "reviewed":
                    queue.append({"listing_id": listing, "attribute": name, "reason": "active_predictor_unreviewed", "evidence": attribute["evidence"]})
            for price in price_index.values():
                pid = price["observation_id"]
                seen_prices.add(pid)
                review = decisions.get("prices", {}).get(pid)
                if review:
                    validate_review(review, captures)
                    if set(review) - {"regular_price", "currency", "tax_basis", "observed_at", "available", "reviewed_by", "reason", "evidence"}:
                        raise ValueError("Unknown schema price review field.")
                    observed = {ref["capture_id"] for ref in price["evidence"]}
                    if not any(ref["capture_id"] in observed for ref in review["evidence"]):
                        raise ValueError("Price review must cite the observation's capture.")
                    if "regular_price" in review and positive(review["regular_price"]) is None:
                        raise ValueError("Reviewed regular price must be positive.")
                    if "observed_at" in review and not aware_time(review["observed_at"]):
                        raise ValueError("Reviewed observation time requires a timezone.")
                    if "available" in review and type(review["available"]) is not bool:
                        raise ValueError("Reviewed availability must be boolean.")
                    for key in ("regular_price", "currency", "tax_basis", "observed_at", "available"):
                        if key in review:
                            price[key] = positive(review[key]) if key == "regular_price" else review[key]
                qty = attributes.get("quantity.total_edible_weight_g", {})
                if qty.get("review_status") == "reviewed" and qty.get("status") == "known":
                    supporting = {ref["capture_id"] for ref in qty["evidence"]}
                    if supporting & {ref["capture_id"] for ref in price["evidence"]}:
                        price["total_edible_weight_g"] = qty["value"]
                        price["quantity_status"] = "reviewed"
                price["displayed_price_per_100g_gbp"] = normalized(price.get("displayed_price"), price["total_edible_weight_g"]) if price.get("currency") == "GBP" else None
                target = normalized(price.get("regular_price"), price["total_edible_weight_g"]) if regular_price_basis_supported(price) else None
                reasons = []
                if not decision or decision.get("in_scope") is not True:
                    reasons.append("category_scope_unreviewed_or_excluded")
                relationship_attributes = [attributes[name] for name in ("identity.physical_product_id", "identity.product_family_id")]
                if any(item["status"] != "known" or item["review_status"] != "reviewed" for item in relationship_attributes):
                    reasons.append("physical_identity_and_family_unreviewed")
                if price["quantity_status"] != "reviewed":
                    reasons.append("observation_edible_quantity_unreviewed")
                if not review or not {"regular_price", "currency", "tax_basis", "observed_at", "available"} <= set(review):
                    reasons.append("regular_price_context_review_incomplete")
                if price.get("currency") != "GBP" or price.get("tax_basis") != "consumer_tax_included":
                    reasons.append("currency_or_tax_basis_unsupported")
                if not aware_time(price.get("observed_at")) or price.get("available") is not True:
                    reasons.append("observation_time_or_availability_unverified")
                if target is None or target <= 0:
                    reasons.append("regular_unit_price_missing_or_invalid")
                if row["source_role"] not in ("brand", "retail"):
                    reasons.append("selling_source_role_unknown")
                predictors = {}
                for name in design["predictors"]:
                    attribute = attributes[name]
                    predictors[name] = attribute["value"] if attribute["status"] == "known" else None
                    if attribute["status"] == "known":
                        try:
                            _predictor_value(attribute["value"], name, design["predictors"][name])
                        except ModelContractError:
                            reasons.append("model_predictor_outside_design_domain:" + name)
                    if attribute["status"] != "known" or attribute["review_status"] != "reviewed":
                        reasons.append("model_predictor_unreviewed:" + name)
                    if not {ref["capture_id"] for ref in attribute["evidence"]} & {ref["capture_id"] for ref in price["evidence"]}:
                        reasons.append("model_predictor_observation_basis_unreviewed:" + name)
                    if name == "composition.cocoa_percentage":
                        policy = design["cocoa_percentage_policy"]
                        if attribute.get("qualifier") not in policy["supported_qualifiers"] or attribute.get("scope") not in policy["supported_scopes"]:
                            reasons.append("cocoa_percentage_basis_unsupported")
                    elif attribute.get("scope") != "product" or attribute.get("qualifier") not in (None, "exact", "unconditional"):
                        reasons.append("model_predictor_basis_unsupported:" + name)
                if predictors.get("identity.source_role") != row["source_role"]:
                    reasons.append("selling_source_role_conflicts_with_predictor")
                price.update(schema_version=SCHEMA_VERSION, dataset_version=version, source_dataset_version=manifest["dataset_version"],
                             model_eligible=not reasons, exclusion_reasons=sorted(set(reasons)),
                             regular_price_per_100g_gbp=target, review_status="reviewed" if review else "unreviewed")
                prices.append(price)
                candidate = {"schema_version": SCHEMA_VERSION, "dataset_version": version,
                             "observation_id": pid, "listing_id": listing,
                             "variant_id": attributes["identity.physical_product_id"]["value"],
                             "family_id": attributes["identity.product_family_id"]["value"],
                             "comparable_group": attributes["identity.product_group"]["value"], "source_role": row["source_role"],
                             "model_eligible": not reasons, "exclusion_reasons": sorted(set(reasons)),
                             "target": {"regular_price_per_100g_gbp": target,
                                        "log_regular_price_per_100g_gbp": math.log(target) if target and target > 0 else None},
                             "predictors": predictors}
                candidates.append(candidate)
    if set(decisions.get("products", {})) - seen_listings or set(decisions.get("prices", {})) - seen_prices:
        raise ValueError("Review IDs do not resolve in this deduplicated dataset.")
    if verify_snapshot(source)[1] != manifest_hash:
        raise RuntimeError("Deduplicated snapshot changed during standardization.")
    if (load_contract(schema_root, offline=offline)[3] != contract_hashes
            or {str(path.relative_to(ROOT)): sha256(path) for path in implementation_paths} != implementation
            or tables.runtime() != runtime):
        raise RuntimeError("Standardization contracts or code changed during the build.")
    if load_identity_mappings(family_mappings) != identity_decisions:
        raise RuntimeError("Identity mapping decisions changed during the build.")
    eligible = tables.select(candidates, "model_eligible", True)
    if eligible:
        from chocolate_model import validate_candidates
        validate_candidates(eligible, design)
    known, conflicts = tables.attribute_counts(products)
    review_counts = tables.counts(queue, "reason")
    report = {"report_format_version": "chocolate-standardization-report-1", "schema_version": SCHEMA_VERSION,
              "dataset_version": version, "source_dataset_version": manifest["dataset_version"],
              "counts": {"listings": len(products), "tracked_attributes": len(profile["attributes"]),
                         "assertions": len(assertions), "price_observations": len(prices),
                         "training_candidates": len(candidates), "eligible_model_inputs": len(eligible),
                         "unmapped_claims": unmapped_count, "review_items": sum(review_counts.values()), "extraction_errors": len(errors)},
              "processing_runtime": runtime,
              "source_role_counts": tables.counts(products, "source_role"),
              "known_attribute_listing_counts": dict(known), "conflicting_attribute_listing_counts": dict(conflicts),
              "exclusion_counts": tables.exclusion_counts(candidates),
              "product_identity_mapping": identity_mapper.summary(),
              "extraction_errors": errors, "release_ready": False,
              "input_status": source_report.get("status", "not_declared"),
              "input_quality_counts": source_report.get("counts", {}),
              "limitations": ["The schema defines tracked information; automatic extraction does not establish complete labeling or certification.",
                              "Pricing training requires reviewed features, identities, quantities and regular consumer price context.",
                              "A training design contract is implemented; no regression or supported pricing insights have been fitted."]}
    products.sort(key=lambda row: row["listing_id"])
    assertions.sort(key=lambda row: (row["listing_id"], row["attribute"], digest(row)))
    prices.sort(key=lambda row: row["observation_id"])
    candidates.sort(key=lambda row: row["observation_id"])
    queue.sort(key=lambda row: (row["listing_id"], row.get("attribute", ""), row["reason"]))
    files = {"quality-report.json": json_bytes(report), "profile.json": json_bytes(profile),
             "source-mappings.json": json_bytes(mappings), "model-design.json": json_bytes(design),
             "family-mappings.json": json_bytes(identity_decisions)}
    for name, rows in (("products", products), ("assertions", assertions), ("prices", prices),
                       ("training-candidates", candidates), ("model-inputs", eligible), ("review-queue", queue)):
        files[name + ".jsonl"] = b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in rows)
    files["family-review-packets.jsonl"] = b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in identity_mapper.packets())
    for name, rows in (("products", products), ("prices", prices)):
        for role, partition in tables.partitions(rows).items():
            files[role + "/" + name + ".jsonl"] = b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in partition)
    output_manifest = {"manifest_format_version": "chocolate-standardized-manifest-1", "schema_version": SCHEMA_VERSION,
                       "dataset_version": version, "source_dataset_version": manifest["dataset_version"],
                       "source_manifest_sha256": manifest_hash, "contract_sha256": contract_hashes,
                       "implementation_sha256": implementation, "processing_runtime": runtime, "reviews": decisions,
                       "identity_mapping_format_version": MAPPING_VERSION,
                       "identity_taxonomy_version": TAXONOMY_VERSION,
                       "identity_mappings_sha256": hashlib.sha256(files["family-mappings.json"]).hexdigest(),
                       "evidence_reference_base": "capture IDs and JSON pointers in the supplied deduplicated products table; its artifact paths use the raw collections root",
                       "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(output_manifest)
    for name in files:
        target = output / name
        temporary = target.with_name("." + target.name + ".tmp")
        if not inside(target.resolve(), output) or not inside(temporary.resolve(), output) or temporary.is_symlink() or target.is_symlink():
            raise ValueError("Standardized output paths must stay within the output directory.")
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = output / name
        temporary = target.with_name("." + target.name + ".tmp")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(data)
        temporary.replace(target)
    return report
