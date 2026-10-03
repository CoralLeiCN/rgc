"""Build a portable evidence-backed silver snapshot from raw category captures."""

import hashlib
import json
import math
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

from .adapters import extract_capture
from .archive import (
    ARCHIVE_VERSION,
    aware_time,
    confirm_raw_snapshot,
    deduplicate_archive,
    digest,
    inside,
    json_bytes,
    load_raw_archive,
    normalized_price,
    pointer_value,
    positive,
    read_json,
    sha256,
)
from .discovery import discover_fields, discovery_policy
from .model import ModelContractError, _predictor_value
from .profiles import CONTRACT_FILES, load_profile, profile_provenance, resolve_profile
from .schema_suggestions import render_schema_suggestions
from .values import (
    standardize_value,
    unknown_attribute,
    validate_evidence,
    validate_product,
)

LAYER_VERSION = "category-processing-silver-1"


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return {"category_processing/" + path.name: sha256(path) for path in sorted(root.glob("*.py"))}


def _evidence(capture, pointer):
    pointer_value(capture, pointer)
    return {"capture_id": capture["capture_id"], "pointer": pointer}


def _reviews(reviews, recipe):
    if reviews is None:
        return {"review_format_version": recipe["review_format_version"], "products": {}, "prices": {}}
    document = deepcopy(reviews) if isinstance(reviews, dict) else read_json(Path(reviews).expanduser().resolve())
    accepted = [recipe["review_format_version"]] + recipe.get("accepted_review_versions", [])
    if not isinstance(document, dict) or document.get("review_format_version") not in accepted:
        raise ValueError("Reviews require a supported profile review_format_version.")
    for key in ("products", "prices"):
        if not isinstance(document.get(key, {}), dict):
            raise ValueError("Review " + key + " must be an object.")
    return document


def _validate_review(review, captures):
    if not isinstance(review, dict):
        raise ValueError("Review decisions must be objects.")
    for key in ("reviewed_by", "reason"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError("Every review requires a nonempty " + key)
    refs = review.get("evidence")
    validate_evidence(refs)
    if not refs:
        raise ValueError("Every review requires supporting capture evidence.")
    for ref in refs:
        if ref["capture_id"] not in captures:
            raise ValueError("Review cites a capture outside this seller listing.")
        try:
            pointer_value(captures[ref["capture_id"]], ref["pointer"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError("Review evidence pointer does not resolve.")


def _select(values, definition):
    if not values:
        return unknown_attribute(definition)
    meanings = {digest({name: value[name] for name in ("value", "scope", "qualifier")}) for value in values}
    if len(meanings) > 1:
        result = unknown_attribute(definition)
        result.update(status="conflict", method="conflicting_source_assertions", review_status="needs_review",
                      evidence=[ref for value in values for ref in value["evidence"]])
        return result
    result = deepcopy(values[0])
    refs = {(ref["capture_id"], ref["pointer"]): ref for value in values for ref in value["evidence"]}
    result["evidence"] = [refs[key] for key in sorted(refs)]
    return result


def _rows_bytes(rows):
    return b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8") for row in rows)


def _preflight(output, names):
    for name in names:
        target = output / name
        if (not inside(target.resolve(), output) or target.is_symlink() or target.is_dir()
                or any(parent.is_symlink() for parent in target.parents if inside(parent, output))):
            raise ValueError("Silver output paths must stay within the output directory without symlinks.")


def _publish(output, files):
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(prefix="." + target.name + ".", suffix=".tmp", dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            temporary.replace(target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def build_silver_dataset(archive_root, output, profile_root, reviews=None):
    """Verify raw evidence, deduplicate sellers, classify values and gate pricing.

    Category, market, dictionaries, source roles and structured mappings come
    from the supplied profile. No regression is fitted, and source evidence is
    never rewritten. Unchanged inputs and rules rebuild to identical bytes.
    """
    source = Path(archive_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    profile_root = resolve_profile(profile_root)
    if inside(output, source) or inside(source, output):
        raise ValueError("Silver output must be separate from the raw archive (no overlap).")
    if inside(output, profile_root) or inside(profile_root, output):
        raise ValueError("Silver output must be separate from the category profile.")
    profile, mappings, design, recipe, contracts = load_profile(profile_root)
    contract_source = profile_provenance(profile_root)
    category, market, schema = profile["category"], profile["market"], profile["schema_version"]
    decisions = _reviews(reviews, recipe)
    implementation = implementation_hashes()
    processing_fingerprint = digest({"contracts": contracts, "implementation": implementation, "reviews": decisions})
    archive = load_raw_archive(source, category, market)
    sources, aliases, deduplication = deduplicate_archive(archive, category, market, recipe.get("source_roles", {}))
    source_version = "raw-snapshot-" + digest({"archive_format": ARCHIVE_VERSION, "inputs": archive["inputs"],
                                              "inventory": sorted(archive["initial_locks"].items()),
                                              "archive_errors": archive["errors"], "unsupported_records": archive["unsupported"]})[:24]
    version = "silver-" + digest({"layer_version": LAYER_VERSION, "source_dataset_version": source_version,
                                  "processing_fingerprint": processing_fingerprint, "reviews": decisions})[:24]
    context = {"category": category, "market": market, "schema_version": schema, "dataset_version": version,
               "source_dataset_version": source_version}
    products, assertions, prices, candidates, queue, errors, field_failures = [], [], [], [], [], [], []
    discovered = []
    seen_prices, seen_reviews = set(), set()
    quantity_name, quantity_unit = recipe["quantity"]["attribute"], recipe["quantity"]["unit"]
    base_quantity = recipe["quantity"]["base_quantity"]
    target_currency = design.get("target", {}).get("currency") or recipe.get("price", {}).get("currency")
    allowed_tax_bases = design.get("eligibility", {}).get("allowed_tax_bases", ["consumer_tax_included"])
    group_name = recipe.get("group_attribute", "identity.product_group")

    for row in sources:
        row.update(context, layer_version=LAYER_VERSION)
        listing, uid = row["listing_id"], row["seller_uid"]
        captures = {capture["capture_id"]: capture for capture in row["captures"]}
        latest = captures[row["latest_capture_id"]]
        current, price_index, unmapped = defaultdict(list), {}, []
        row_context = {"listing_id": listing, "seller_uid": uid, "source_key": row["source_key"], "source_role": row["source_role"]}

        def retain(name, value, capture, pointer, reason, **extra):
            ref = _evidence(capture, pointer)
            text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
            if not text:
                return
            definition = profile["attributes"].get(name, {})
            metadata = {"unit": extra.get("unit", definition.get("unit")),
                        "scope": extra.get("scope", definition.get("scope", "product")),
                        "qualifier": extra.get("qualifier"), "source_format": recipe["adapter"]}
            claim = {"attribute": name, "value": text, "evidence": [ref], "reason": reason}
            claim["scope"] = metadata["scope"]
            unmapped.append(claim)
            queue.append({**row_context, **claim, **metadata, "raw_value": deepcopy(value),
                          "reason": "unmapped_claim", "unmapped_reason": reason})

        def add(item, capture):
            name, value, pointer = item["attribute"], item.get("value"), item["pointer"]
            if value is None or value == "unknown":
                return
            extra = {key: item[key] for key in ("unit", "scope", "qualifier") if key in item}
            if name not in profile["attributes"]:
                retain(name, value, capture, pointer, "profile_mapping_missing", **extra)
                return
            if value == []:
                retain(name, value, capture, pointer, "empty_list_does_not_establish_absence", **extra)
                return
            try:
                definition = profile["attributes"][name]
                value = standardize_value(name, value, profile, mappings, item.get("unit"))
                attribute = {"value": value, "status": "known", "unit": definition.get("unit"),
                             "qualifier": item.get("qualifier"), "scope": item.get("scope", definition.get("scope", "product")),
                             "evidence": [_evidence(capture, pointer)], "method": item["method"], "review_status": "unreviewed"}
                assertions.append({**context, **row_context, "attribute": name, **attribute,
                                   "is_current": capture["capture_id"] == row["latest_capture_id"], "raw_value": item["value"]})
                if capture["capture_id"] == row["latest_capture_id"]:
                    current[name].append(attribute)
            except (ValueError, TypeError, KeyError) as error:
                retain(name, item["value"], capture, pointer, "standardization_failed", **extra)
                failure = {**row_context, "capture_id": capture["capture_id"], "attribute": name,
                           "reason": "standardization_failed", "error": str(error), "raw_value": item["value"],
                           "evidence": [_evidence(capture, pointer)],
                           "scope": extra.get("scope", profile["attributes"][name].get("scope", "product")),
                           "unit": extra.get("unit", profile["attributes"][name].get("unit")),
                           "qualifier": extra.get("qualifier"), "source_format": recipe["adapter"]}
                field_failures.append(failure)

        for capture in captures.values():
            extracted = None
            try:
                extracted = extract_capture(capture, recipe)
            except (ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
                errors.append({**row_context, "capture_id": capture["capture_id"], "error": str(error)})
                queue.append({**row_context, "reason": "extraction_failed", "error": str(error),
                              "value": str(error), "scope": "observation", "source_format": recipe["adapter"],
                              "evidence": [_evidence(capture, "/raw_record")]})
            handled = []
            if extracted is not None:
                # Missing adapter features cite their enclosing raw object as
                # context; they do not establish coverage of that object. A
                # provisional group can also cite /raw_record when its name
                # is missing. Explicit configured fields remain covered by
                # discovery's recipe handling, including whole-object fields.
                handled.extend(item["pointer"] for item in extracted["attributes"]
                               if item.get("value") is not None and item.get("value") != "unknown"
                               and item.get("method") != "not_established_by_available_source_evidence"
                               and item["pointer"] not in (
                                   "/raw_record", "/raw_record/information", "/raw_record/identity"))
                handled.extend(item["pointer"] for name in ("quantities", "prices")
                               for item in extracted[name])
                handled.extend(extracted.get("handled_pointers", []))
            for item in discover_fields(capture, recipe, handled):
                pointer = item["field_pointer"]
                evidence = [_evidence(capture, pointer)]
                field_id = "source-field-" + digest({"category": category, "market": market,
                                                      "field_pointer": pointer})[:24]
                record = {"discovery_format_version": "category-unmapped-fields-1", **context, **row_context,
                          "mapping_version": mappings["mapping_version"], "field_id": field_id,
                          "capture_id": capture["capture_id"], **item, "evidence": evidence,
                          "scope": None, "unit": None, "qualifier": None,
                          "source_format": recipe["adapter"], "reason": "unconfigured_source_field"}
                discovered.append(record)
                queue.append({**row_context, "attribute": "source-field:" + pointer,
                              "field_id": field_id, "field_pointer": pointer,
                              "value": json.dumps(item["raw_value"], sort_keys=True, ensure_ascii=False, allow_nan=False),
                              "raw_value": deepcopy(item["raw_value"]), "evidence": evidence,
                              "scope": None, "unit": None, "qualifier": None,
                              "source_format": recipe["adapter"], "reason": "unmapped_claim",
                              "unmapped_reason": "unconfigured_source_field"})
            if extracted is None:
                continue
            for item in extracted["attributes"]:
                add(item, capture)
            for item in extracted["prices"]:
                quantity_candidates = item.get("quantity_candidates", extracted["quantities"])
                normalized_quantities = []
                for candidate in quantity_candidates:
                    try:
                        value = standardize_value(quantity_name, candidate["value"], profile, mappings, candidate.get("unit"))
                        if positive(value) is not None:
                            normalized_quantities.append((value, candidate["pointer"]))
                    except (ValueError, TypeError, KeyError):
                        continue
                weights = {value for value, pointer in normalized_quantities}
                amount = next(iter(weights)) if len(weights) == 1 else None
                price = {key: deepcopy(value) for key, value in item.items() if key not in ("pointer", "quantity_candidates")}
                price.update(seller_uid=uid, source_key=row["source_key"], source_role=row["source_role"],
                             brand=row.get("brand"), retailer=row.get("retailer"), quantity_value=amount,
                             quantity_unit=quantity_unit, base_quantity=base_quantity,
                             quantity_status="conflict" if len(weights) > 1 else "known" if weights else "unknown")
                signature = deepcopy(price)
                if not price.get("observed_at"):
                    signature["unknown_time_capture_id"] = capture["capture_id"]
                pid = "observation-" + digest(signature)[:24]
                if pid not in price_index:
                    price_index[pid] = {**price, "observation_id": pid, "listing_id": listing,
                                        "evidence": [], "quantity_evidence": []}
                price_index[pid]["evidence"].append(_evidence(capture, item["pointer"]))
                price_index[pid]["quantity_evidence"].extend(_evidence(capture, pointer) for value, pointer in normalized_quantities)

        raw = latest["raw_record"]
        pointer = "/raw_record/source_key" if "source_key" in raw else "/raw_record"
        if row["source_role"] == "unknown" and "source_key" in raw:
            retain("identity.source_role", raw["source_key"], latest, pointer,
                   "selling_source_role_unmapped", scope="product")
        for name, value in (("identity.retailer", row.get("retailer")), ("identity.source_role", row["source_role"]),
                            ("identity.brand", row.get("brand"))):
            if name in profile["attributes"]:
                brand_pointer = "/raw_record/identity/brand" if name == "identity.brand" and isinstance(raw.get("identity"), dict) and "brand" in raw["identity"] else pointer
                add({"attribute": name, "value": value, "pointer": brand_pointer, "method": "profile_selling_source_context"}, latest)
        attributes = {name: _select(current.get(name, []), definition) for name, definition in profile["attributes"].items()}
        # Stable seller UIDs may key reviews; current human listing IDs remain
        # accepted for compatibility. Two decisions for one listing are refused.
        product_decisions = decisions.get("products", {})
        keys = [key for key in sorted(set([listing, uid] + row["source_listing_ids"])) if key in product_decisions]
        if len({digest(product_decisions[key]) for key in keys}) > 1:
            raise ValueError("Conflicting product reviews address aliases of the same seller listing.")
        decision = product_decisions[keys[0]] if keys else None
        if keys:
            seen_reviews.update(keys)
        if keys:
            _validate_review(decision, captures)
            if set(decision) - {"variant_id", "family_id", "in_scope", "attributes", "reviewed_by", "reason", "evidence"}:
                raise ValueError("Unknown product review field.")
            for name in ("variant_id", "family_id"):
                if name in decision and (not isinstance(decision[name], str) or not decision[name].strip()):
                    raise ValueError("Reviewed physical/family identity must be nonempty.")
            if "in_scope" in decision and type(decision["in_scope"]) is not bool:
                raise ValueError("Reviewed in_scope must be boolean.")
            reviewed = decision.get("attributes", {})
            if not isinstance(reviewed, dict) or set(reviewed) - set(attributes):
                raise ValueError("Attribute review refers to undefined category fields.")
            for name, review in reviewed.items():
                _validate_review(review, captures)
                if set(review) - {"value", "status", "unit", "qualifier", "scope", "reviewed_by", "reason", "evidence"}:
                    raise ValueError("Unknown attribute review field.")
                status = review.get("status", "known")
                if status not in ("known", "unknown", "conflict", "not_applicable"):
                    raise ValueError("Invalid reviewed attribute state.")
                value = standardize_value(name, review.get("value"), profile, mappings, review.get("unit")) if status == "known" else None
                if status == "known" and value is None:
                    raise ValueError("Known attribute review requires a value.")
                attributes[name] = {"value": value, "status": status, "unit": profile["attributes"][name].get("unit"),
                                    "qualifier": review.get("qualifier"), "scope": review.get("scope", profile["attributes"][name].get("scope", "product")),
                                    "evidence": deepcopy(review["evidence"]), "method": "evidence_backed_review", "review_status": "reviewed"}
                assertions.append({**context, **row_context, "attribute": name, **deepcopy(attributes[name]),
                                   "is_current": True, "raw_value": review.get("value")})
            for field, name in (("variant_id", "identity.physical_product_id"), ("family_id", "identity.product_family_id")):
                if field in decision and name in attributes:
                    if name in reviewed and attributes[name]["value"] != decision[field]:
                        raise ValueError("Reviewed relationship contradicts its attribute.")
                    attributes[name] = {"value": decision[field], "status": "known", "unit": None, "qualifier": None,
                                        "scope": "product", "evidence": deepcopy(decision["evidence"]), "method": "evidence_backed_review", "review_status": "reviewed"}
            if "in_scope" in decision and "identity.boundary_status" in attributes:
                name = "identity.boundary_status"
                value = "in_scope" if decision["in_scope"] else "out_of_scope"
                if name in reviewed and attributes[name]["value"] != value:
                    raise ValueError("Reviewed category scope contradicts its boundary attribute.")
                attributes[name] = {"value": value, "status": "known", "unit": None, "qualifier": None,
                                    "scope": "product", "evidence": deepcopy(decision["evidence"]), "method": "evidence_backed_review", "review_status": "reviewed"}
        product = {**context, **row_context, "source_listing_ids": row["source_listing_ids"],
                   "brand": row.get("brand"), "retailer": row.get("retailer"), "attributes": attributes,
                   "unmapped_claims": unmapped, "review_status": "reviewed" if decision else "unreviewed"}
        validate_product(product, profile, mappings)
        products.append(product)
        for name, attribute in attributes.items():
            if attribute["status"] in ("unknown", "conflict"):
                item = {**row_context, "attribute": name, "reason": attribute["status"],
                              "scope": attribute["scope"], "unit": attribute["unit"], "qualifier": attribute["qualifier"],
                              "evidence": attribute["evidence"], "value": attribute["value"]}
                if attribute["status"] == "conflict":
                    item["raw_value"] = [pointer_value(captures[ref["capture_id"]], ref["pointer"])
                                         for ref in attribute["evidence"]]
                    item["source_format"] = recipe["adapter"]
                queue.append(item)
            elif name in design["predictors"] and attribute["review_status"] != "reviewed":
                queue.append({**row_context, "attribute": name, "reason": "attribute_unreviewed", "evidence": attribute["evidence"]})

        for price in price_index.values():
            pid = price["observation_id"]
            seen_prices.add(pid)
            review = decisions.get("prices", {}).get(pid)
            if pid in decisions.get("prices", {}):
                _validate_review(review, captures)
                if set(review) - {"regular_price", "currency", "tax_basis", "observed_at", "available", "reviewed_by", "reason", "evidence"}:
                    raise ValueError("Unknown price review field.")
                price_captures = {ref["capture_id"] for ref in price["evidence"]}
                if not any(ref["capture_id"] in price_captures for ref in review["evidence"]):
                    raise ValueError("Price review must cite the observation's capture.")
                if "regular_price" in review and positive(review["regular_price"]) is None:
                    raise ValueError("Reviewed regular price must be positive.")
                if "observed_at" in review and not aware_time(review["observed_at"]):
                    raise ValueError("Reviewed source observation time requires a timezone.")
                if "available" in review and type(review["available"]) is not bool:
                    raise ValueError("Reviewed availability must be boolean.")
                for name in ("regular_price", "currency", "tax_basis", "observed_at", "available"):
                    if name in review:
                        price[name] = review[name]
            quantity_attribute = attributes[quantity_name]
            observed_captures = {ref["capture_id"] for ref in price["evidence"]}
            if quantity_attribute["status"] == "known" and quantity_attribute["review_status"] == "reviewed" and observed_captures & {ref["capture_id"] for ref in quantity_attribute["evidence"]}:
                price["quantity_value"] = quantity_attribute["value"]
                price["quantity_status"] = "reviewed"
            supported_currency = bool(target_currency and price.get("currency") == target_currency)
            target = normalized_price(price.get("regular_price"), price["quantity_value"], base_quantity) if supported_currency else None
            price["displayed_unit_price"] = normalized_price(price.get("displayed_price"), price["quantity_value"], base_quantity) if supported_currency else None
            price["regular_unit_price"] = target
            reasons = []
            if not decision or decision.get("in_scope") is not True:
                reasons.append("category_scope_unreviewed_or_excluded")
            if not decision or not decision.get("variant_id") or not decision.get("family_id"):
                reasons.append("physical_identity_and_family_unreviewed")
            if price["quantity_status"] != "reviewed":
                reasons.append("observation_quantity_unreviewed")
            if not review or not {"regular_price", "currency", "tax_basis", "observed_at", "available"} <= set(review):
                reasons.append("regular_price_context_review_incomplete")
            if not supported_currency or price.get("tax_basis") not in allowed_tax_bases:
                reasons.append("currency_or_tax_basis_unsupported")
            if not aware_time(price.get("observed_at")) or price.get("available") is not True:
                reasons.append("observation_time_or_availability_unverified")
            if target is None:
                reasons.append("regular_unit_price_missing_or_invalid")
            if row["source_role"] not in ("brand", "retail"):
                reasons.append("selling_source_role_unknown")
            group = attributes.get(group_name, {})
            if group.get("status") != "known" or group.get("review_status") != "reviewed":
                reasons.append("comparable_group_unreviewed")
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
                if not observed_captures & {ref["capture_id"] for ref in attribute["evidence"]}:
                    reasons.append("model_predictor_observation_basis_unreviewed:" + name)
                policy = design.get("attribute_policies", {}).get(name)
                if name == "composition.cocoa_percentage" and "cocoa_percentage_policy" in design:
                    policy = design["cocoa_percentage_policy"]
                if policy:
                    if attribute["scope"] not in policy.get("supported_scopes", ["product"]) or attribute["qualifier"] not in policy.get("supported_qualifiers", [None, "exact", "unconditional"]):
                        reasons.append("model_predictor_basis_unsupported:" + name)
                elif attribute["scope"] != "product" or attribute["qualifier"] not in (None, "exact", "unconditional"):
                    reasons.append("model_predictor_basis_unsupported:" + name)
            if "identity.source_role" in predictors and predictors["identity.source_role"] != row["source_role"]:
                reasons.append("selling_source_role_conflicts_with_predictor")
            price.update(context, model_eligible=not reasons, exclusion_reasons=sorted(set(reasons)), review_status="reviewed" if review else "unreviewed")
            if recipe.get("legacy_chocolate_price_aliases"):
                price.update(total_edible_weight_g=price["quantity_value"], displayed_price_per_100g_gbp=price["displayed_unit_price"],
                             regular_price_per_100g_gbp=target)
            prices.append(price)
            candidates.append({**context, "observation_id": pid, "listing_id": listing, "seller_uid": uid,
                               "variant_id": decision.get("variant_id") if decision else None,
                               "family_id": decision.get("family_id") if decision else None,
                               "comparable_group": group.get("value"), "source_role": row["source_role"],
                               "model_eligible": not reasons, "exclusion_reasons": sorted(set(reasons)),
                               "target": {"regular_unit_price": target, "log_regular_unit_price": math.log(target) if target and target > 0 else None},
                               "predictors": predictors})

    if set(decisions.get("products", {})) - seen_reviews or set(decisions.get("prices", {})) - seen_prices:
        raise ValueError("Review IDs do not resolve in this category dataset.")
    eligible = [row for row in candidates if row["model_eligible"]]
    if eligible:
        from .model import validate_candidates
        validate_candidates(eligible, design)
    from .review_batches import build_review_batches, render_summary
    from .tracking import build_ledger
    ledger = build_ledger(sources, processing_fingerprint, failed_capture_ids=[error["capture_id"] for error in errors])
    batches = build_review_batches(queue, category, market, schema, mappings["mapping_version"])
    summary = render_summary(batches, category, market, schema, mappings["mapping_version"])
    discovered.sort(key=lambda row: (row["field_id"], row["seller_uid"], row["capture_id"], digest(row)))
    schema_review = render_schema_suggestions(discovered, category, market, schema, mappings["mapping_version"])
    counts = {"listings": len(products), "tracked_attributes": len(profile["attributes"]), "assertions": len(assertions),
              "price_observations": len(prices), "training_candidates": len(candidates), "eligible_model_inputs": len(eligible),
              "unmapped_claims": sum(len(row["unmapped_claims"]) for row in products), "review_items": len(queue),
              "extraction_errors": len(errors), "field_failures": len(field_failures), "product_folders": archive["product_folders"],
              "accepted_raw_listing_folders": sum(len(row["source_listing_ids"]) for row in sources),
              "captures": sum(len(row["captures"]) for row in sources), "duplicate_source_listings_removed": sum(len(row["source_listing_ids"]) - 1 for row in sources),
              "archive_errors": len(archive["errors"]), "unsupported_records": len(archive["unsupported"]),
              "mapping_review_batches": len(batches), "discovered_field_occurrences": len(discovered),
              "discovered_source_fields": len({row["field_id"] for row in discovered})}
    report = {"report_format_version": "category-processing-silver-report-1", "layer_version": LAYER_VERSION, **context,
              "mapping_version": mappings["mapping_version"], "model_design_version": design.get("model_design_version"),
              "processing_fingerprint": processing_fingerprint, "counts": counts,
              "field_discovery": {"discovery_format_version": "category-unmapped-fields-1",
                                  "policy": discovery_policy(recipe), "coverage": "structural raw fields; semantic meaning remains unreviewed"},
              "status": "partial" if archive["errors"] or archive["unsupported"] or errors else "complete_snapshot",
              "source_role_counts": dict(Counter(row["source_role"] for row in sources)), "deduplication": deduplication,
              "archive_errors": archive["errors"], "unsupported_records": archive["unsupported"],
              "extraction_errors": errors, "field_failures": field_failures,
              "known_attribute_listing_counts": dict(Counter(name for row in products for name, attr in row["attributes"].items() if attr["status"] == "known")),
              "conflicting_attribute_listing_counts": dict(Counter(name for row in products for name, attr in row["attributes"].items() if attr["status"] == "conflict")),
              "exclusion_counts": dict(Counter(reason for row in candidates for reason in row["exclusion_reasons"])),
              "release_ready": False,
              "limitations": ["Listing counts describe seller records, not market-wide distinct formulations.",
                              "Original index/history consistency is checked; source/image artifact bytes are not rehashed by this build.",
                              "Automatic extraction and mapping gaps remain separate from evidence review and model eligibility.",
                              "The processing ledger records attempts; current builds reprocess the full accepted snapshot rather than using a selective cache.",
                              "No regression, supported pricing prediction, certification audit or causal effect is produced."]}
    for row in aliases:
        row.update(context)
    products.sort(key=lambda row: row["listing_id"])
    sources.sort(key=lambda row: row["listing_id"])
    aliases.sort(key=lambda row: row["source_listing_id"])
    assertions.sort(key=lambda row: (row["listing_id"], row["attribute"], digest(row)))
    prices.sort(key=lambda row: row["observation_id"])
    candidates.sort(key=lambda row: row["observation_id"])
    queue.sort(key=lambda row: (row["listing_id"], row.get("attribute", ""), row["reason"], digest(row)))
    files = {"quality-report.json": json_bytes(report), "mapping-review-summary.md": summary.encode("utf-8"),
             "schema-extension-review.md": schema_review.encode("utf-8")}
    for name in CONTRACT_FILES:
        files[name] = (profile_root / name).read_bytes()
    tables = {"products": products, "source-listings": sources, "listing-aliases": aliases, "assertions": assertions,
              "prices": prices, "training-candidates": candidates, "model-inputs": eligible, "review-queue": queue,
              "processing-ledger": ledger, "mapping-review-batches": batches, "discovered-fields": discovered}
    for name, rows in tables.items():
        files[name + ".jsonl"] = _rows_bytes(rows)
    for role in ("brand", "retail", "unknown"):
        for name in ("products", "source-listings", "prices"):
            files[role + "/" + name + ".jsonl"] = _rows_bytes([row for row in tables[name] if row["source_role"] == role])
    manifest = {"manifest_format_version": "category-processing-silver-manifest-1", "layer_version": LAYER_VERSION, **context,
                "source_layer": "raw_collections", "source_archive_format": ARCHIVE_VERSION,
                "input_reference_base": "supplied raw collections root", "inputs": archive["inputs"],
                "input_inventory": archive["initial_locks"], "contract_sha256": contracts,
                "contract_source": contract_source,
                "implementation_sha256": implementation, "processing_fingerprint": processing_fingerprint,
                "reviews": decisions, "deduplication": deduplication,
                "evidence_reference_base": "capture IDs and JSON pointers resolve in source-listings.jsonl; original artifact/history paths resolve against the supplied raw collections root",
                "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    _preflight(output, files)
    confirm_raw_snapshot(archive)
    if (implementation_hashes() != implementation or load_profile(profile_root)[4] != contracts
            or profile_provenance(profile_root) != contract_source):
        raise RuntimeError("Processing implementation or category contracts changed during the build.")
    _publish(output, files)
    return report
