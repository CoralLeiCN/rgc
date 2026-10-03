"""Build deterministic derived tables without modifying source evidence."""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re

from .adapters import extract_capture
from .deduplication import confirm_raw_snapshot, deduplicate_listings, load_raw_archive
from .sources import SOURCES


PROFILE_VERSION = "uk-chocolate-clean-1"
ARCHIVE_VERSION = "category-research-raw-1"
REVIEW_VERSION = "chocolate-reviews-1"
GROUPS = ["bar", "assorted_box", "chocolate_pieces", "baking_chocolate", "hot_chocolate", "other"]
PROFILE = {
    "profile_version": PROFILE_VERSION, "category": "chocolate", "market": "uk",
    "status": "draft_mappings_pending_classification_validation",
    "currency": "GBP", "target": "regular_consumer_pack_price_per_100g",
    "quantity_unit": "g", "normalization": "pack_price / total_edible_weight_g * 100",
    "comparable_groups": GROUPS,
    "identity_rule": "Deduplicate exact source product/variant identifiers within a source and hostname. Listings at different selling sources always remain unique rows. Reviewed variant/family IDs may describe relationships without merging shops.",
    "source_roles": {key: {"source_role": role, "retailer": seller} for key, (role, seller) in SOURCES.items()},
    "variant_attributes": ["flavour", "composition", "edible_weight", "pack_configuration"],
    "unknown_rule": "Missing statements are unknown, never absent; retained source claims are not certification audits.",
    "quantity_rule": "Use explicit edible/net mass statements; Shopify grams/weight and source unit prices are not edible-mass evidence.",
    "price_rule": "Retain displayed, reference and ordinary prices separately; reference prices do not establish regular prices.",
    "eligibility_rule": "Require reviewed in-scope identity/family/group, positive edible mass, reviewed positive regular GBP pack price, consumer tax included, timezone-aware observation time, and available source listing.",
    "feature_types": {
        "name": "string", "brand": "string", "source_product_id": "string",
        "source_variant_id": "string", "gtin": "string", "ingredients_text": "string",
        "allergen_text": "string", "nutrition_text": "string", "claim_text": "string",
        "chocolate_type": "categorical", "cocoa_percentage": "number",
        "nuts_as_ingredient": "presence", "may_contain_nuts": "presence",
        "fairtrade_claim": "presence", "fair_trade_claim": "presence",
        "organic_claim": "presence", "vegan_claim": "presence",
    },
    "feature_units": {"cocoa_percentage": "%"},
    "presence_values": ["present", "absent", "unknown"],
    "limitations": ["A draft deterministic extraction profile, not a complete chocolate taxonomy.",
                    "Packaging images, origin and unfamiliar claims require evidence review and profile extension.",
                    "No model fitting, classification-accuracy validation or prediction release is performed."],
}


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def read_json(path):
    payload = path.read_bytes()
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(payload, parse_constant=reject), hashlib.sha256(payload).hexdigest()


def positive(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        result = float(number)
        return result if number.is_finite() and math.isfinite(result) and result > 0 else None
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None


def aware_time(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def pointer_value(document, pointer):
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("Evidence pointers must be JSON pointers rooted at a capture.")
    result = document
    if pointer:
        for token in pointer[1:].split("/"):
            if re.search(r"~(?:[^01]|$)", token):
                raise ValueError("Invalid JSON pointer escape.")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(result, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError("Invalid JSON pointer array index.")
                result = result[int(token)]
            else:
                result = result[token]
    return result


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def evidence_for(root, listing, capture, pointer, artifact_cache):
    try:
        pointer_value(capture, pointer)
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("Extraction returned an unresolved evidence pointer: " + str(pointer))
    cid = capture["capture_id"]
    if cid not in artifact_cache["captures"]:
        artifact_ids = []
        for group in ("source_artifacts", "source_catalogs", "images"):
            for item in capture.get(group, []):
                if not isinstance(item, dict):
                    continue
                ref = item.get("archive_relative_path")
                if ref not in artifact_cache["availability"]:
                    local = root / ref if isinstance(ref, str) else None
                    artifact_cache["availability"][ref] = bool(local and inside(local.resolve(), root) and local.is_file())
                metadata = {key: item.get(key) for key in (
                    "url", "archive_relative_path", "sha256", "status", "source_retrieval_status",
                    "retrieved_at", "retrieval_method", "content_type", "http_status")}
                metadata.update(artifact_group=group, available_locally=artifact_cache["availability"][ref])
                aid = "artifact-" + digest(metadata)[:24]
                artifact_cache["artifacts"][aid] = {"artifact_id": aid, **metadata}
                artifact_ids.append(aid)
        artifact_cache["captures"][cid] = {
            "capture_id": cid, "listing_id": listing,
            "source_listing_id": capture["raw_record"]["product_id"],
            "history_path": capture["history_path"], "artifact_ids": sorted(set(artifact_ids)),
        }
    return {"listing_id": listing, "source_listing_id": capture["raw_record"]["product_id"],
            "capture_id": cid, "history_path": capture["history_path"], "pointer": pointer,
            "source_url": capture["raw_record"].get("source_url"),
            "recorded_at": capture.get("recorded_at"),
            "artifact_metadata_table": "capture-evidence.jsonl"}


def review_decisions(reviews):
    if reviews is None:
        return {"review_format_version": REVIEW_VERSION, "products": {}, "prices": {}}
    document = reviews if isinstance(reviews, dict) else read_json(Path(reviews).expanduser().resolve())[0]
    if not isinstance(document, dict) or document.get("review_format_version") != REVIEW_VERSION:
        raise ValueError("Reviews must use review_format_version " + REVIEW_VERSION)
    for key in ("products", "prices"):
        if not isinstance(document.get(key, {}), dict):
            raise ValueError("reviews." + key + " must be an object.")
    return document


def validate_review(decision, captures, allowed):
    if not isinstance(decision, dict) or set(decision) - allowed - {"evidence", "reviewed_by", "reason"}:
        raise ValueError("Review has unsupported fields.")
    for key in ("reviewed_by", "reason"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError("Review requires a nonempty " + key)
    refs = decision.get("evidence")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Review requires supporting capture IDs and JSON pointers.")
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("capture_id") not in captures:
            raise ValueError("Review evidence capture does not resolve for this source listing.")
        try:
            pointer_value(captures[ref["capture_id"]], ref.get("pointer"))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError("Review evidence pointer does not resolve.")


def quantities(items):
    valid = [item for item in items if positive(item.get("total_edible_weight_g"))]
    weights = {positive(item["total_edible_weight_g"]) for item in valid}
    counts = {item.get("pack_count") for item in valid if item.get("pack_count") is not None}
    return (next(iter(weights)) if len(weights) == 1 else None,
            next(iter(counts)) if len(counts) == 1 else None,
            "conflict" if len(weights) > 1 or len(counts) > 1 else "known" if weights else "unknown")


def normalized(price, weight):
    price, weight = positive(price), positive(weight)
    if price is None or weight is None:
        return None
    result = float(Decimal(str(price)) * 100 / Decimal(str(weight)))
    return round(result, 8) if math.isfinite(result) else None


def build_dataset(archive_root, output, reviews=None):
    implementation_paths = tuple(Path(__file__).with_name(name) for name in
                                 ("core.py", "adapters.py", "deduplication.py", "sources.py"))
    implementation = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in implementation_paths}
    root = Path(archive_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if inside(output, root) or inside(root, output):
        raise ValueError("Derived output must be separate from the raw archive (no overlap).")
    product_root = root / "chocolate" / "uk" / "products"
    if not product_root.is_dir():
        raise ValueError("Expected chocolate/uk/products under --archive-root.")
    decisions = review_decisions(reviews)
    products, features, prices, queue, unsupported, errors, inputs = [], [], [], [], [], [], []
    artifact_cache = {"captures": {}, "artifacts": {}, "availability": {}}

    def evidence(listing, capture, pointer):
        return evidence_for(root, listing, capture, pointer, artifact_cache)

    input_price_candidates = 0
    study_ids, windows, source_coverage = set(), set(), Counter()
    counts = Counter({"product_folders": 0, "source_listings": 0, "captures": 0,
                      "price_observations": 0, "eligible_price_observations": 0})

    archive = load_raw_archive(root)
    listings, capture_lookup, current_captures = archive["listings"], archive["captures"], archive["latest"]
    inputs = archive["inputs"]
    errors.extend(archive["errors"])
    unsupported.extend(archive["unsupported"])
    counts["product_folders"] = archive["product_folders"]
    aliases, duplicate_groups, original_latest = deduplicate_listings(listings, capture_lookup, current_captures)
    unknown_products = set(decisions.get("products", {})) - set(listings)
    if unknown_products:
        raise ValueError("Review refers to unknown/unsupported products: " + ", ".join(sorted(unknown_products)))

    for listing, document in listings.items():
        captures = capture_lookup[listing]
        latest = captures[current_captures[listing]]
        identity = latest["raw_record"].get("identity") if isinstance(latest["raw_record"].get("identity"), dict) else {}
        source = latest["raw_record"].get("source_key") or "unknown"
        source_role, retailer = SOURCES.get(source, ("unknown", source))
        source_coverage[source] += 1
        counts["source_listings"] += 1
        counts["captures"] += len(captures)
        extracted, assertions, price_index = {}, {}, {}
        quantity_evidence = []
        for cid, capture in captures.items():
            study = capture.get("study") or {}
            if study.get("study_id"):
                study_ids.add(study["study_id"])
            if study.get("collection_window"):
                windows.add(json.dumps(study["collection_window"], sort_keys=True))
            try:
                result = extract_capture(capture)
            except (ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
                errors.append({"listing_id": listing, "capture_id": cid,
                               "code": "unsupported_source_field_shape", "reason": str(error)})
                result = {"features": [], "quantities": [], "prices": [],
                          "warnings": ["source_field_shapes_require_review"]}
            extracted[cid] = result
            for item in result.get("features", []):
                assertion = {"listing_id": listing, "profile_version": PROFILE_VERSION, **item,
                             "review_status": "unreviewed",
                             "is_current": cid == current_captures[listing]}
                pointer = assertion.pop("raw_pointer", "/raw_record/information")
                assertion["evidence"] = [evidence(listing, capture, pointer)]
                key = digest({k: v for k, v in assertion.items() if k not in ("evidence", "is_current")})
                if key in assertions:
                    assertions[key]["evidence"].extend(assertion["evidence"])
                    assertions[key]["is_current"] |= assertion["is_current"]
                else:
                    assertions[key] = assertion
            for item in result.get("quantities", []):
                if cid == current_captures[listing]:
                    quantity_evidence.append(evidence(listing, capture, item["raw_pointer"]))
            input_price_candidates += len(result.get("prices", []))
            for item in result.get("prices", []):
                weight, pack_count, qstatus = quantities(item.get("quantities", result.get("quantities", [])))
                row = {"listing_id": listing, "profile_version": PROFILE_VERSION, **item,
                       "total_edible_weight_g": weight, "pack_count": pack_count, "quantity_status": qstatus,
                       "review_status": "unreviewed"}
                row.pop("quantities", None)
                pointer = row.pop("raw_pointer")
                ev = evidence(listing, capture, pointer)
                row["evidence"] = [ev]
                row["quantity_evidence"] = [evidence(listing, capture, q["raw_pointer"])
                                            for q in item.get("quantities", result.get("quantities", []))]
                signature = {k: v for k, v in row.items() if k not in ("evidence", "quantity_evidence")}
                # Unknown observation times must not collapse independent captures.
                if not row.get("observed_at"):
                    signature["unknown_time_capture_id"] = cid
                key = digest(signature)
                row["price_id"] = "price-" + key[:24]
                if key in price_index:
                    price_index[key]["evidence"].append(ev)
                else:
                    price_index[key] = row
        result = extracted[current_captures[listing]]
        weight, pack_count, qstatus = quantities(result.get("quantities", []))
        group = result.get("group") or {}
        product = {"listing_id": listing, "source_listing_ids": aliases[listing],
                   "variant_id": listing, "family_id": None,
                   "identity_status": "unresolved_source_listing", "profile_version": PROFILE_VERSION,
                   "name": identity.get("name"), "brand": identity.get("brand"), "source_key": source,
                   "retailer": retailer, "source_role": source_role,
                   "source_product_id": identity.get("source_product_id"),
                   "source_variant_id": identity.get("source_variant_id"), "gtin": identity.get("gtin"),
                   "source_family_id": source + ":" + str(identity["source_product_id"]) if identity.get("source_product_id") else None,
                   "in_scope": None, "boundary_status": result.get("boundary_status", "unknown"),
                   "comparable_group": group.get("value"), "group_status": "unreviewed",
                   "total_edible_weight_g": weight, "pack_count": pack_count, "quantity_status": qstatus,
                   "evidence": [evidence(listing, captures[original_latest[alias]],
                                         "/raw_record/identity" if "identity" in captures[original_latest[alias]]["raw_record"] else "/raw_record")
                                for alias in aliases[listing]],
                   "quantity_evidence": quantity_evidence,
                   "review_status": "unreviewed", "review": None}
        decision = decisions.get("products", {}).get(listing)
        if decision:
            allowed = {"variant_id", "family_id", "in_scope", "comparable_group", "total_edible_weight_g", "pack_count"}
            validate_review(decision, captures, allowed)
            for key in ("variant_id", "family_id"):
                if key in decision and (not isinstance(decision[key], str) or not decision[key].strip()):
                    raise ValueError(key + " must be a nonempty reviewed identifier.")
            if "in_scope" in decision and not isinstance(decision["in_scope"], bool):
                raise ValueError("Reviewed in_scope must be boolean.")
            if "comparable_group" in decision and decision["comparable_group"] not in GROUPS:
                raise ValueError("Unsupported reviewed comparable_group.")
            if "total_edible_weight_g" in decision and positive(decision["total_edible_weight_g"]) is None:
                raise ValueError("Reviewed edible weight must be positive and finite.")
            if "pack_count" in decision and (type(decision["pack_count"]) is not int or decision["pack_count"] <= 0):
                raise ValueError("Reviewed pack_count must be a positive integer.")
            product.update({k: v for k, v in decision.items() if k in allowed})
            product.update({"review_status": "reviewed", "review": decision,
                            "identity_status": "reviewed" if {"variant_id", "family_id"} <= set(decision) else "unresolved_source_listing",
                            "group_status": "reviewed" if "comparable_group" in decision else "unreviewed"})
            if "total_edible_weight_g" in decision:
                product["quantity_status"] = "reviewed"
        products.append(product)
        features.extend(assertions.values())
        for row in price_index.values():
            row.update({"variant_id": product["variant_id"], "family_id": product["family_id"],
                        "comparable_group": product["comparable_group"], "brand": product["brand"],
                        "retailer": retailer, "source_role": source_role, "source_key": source})
            # A reviewed quantity applies only to observations backed by its capture.
            if decision and "total_edible_weight_g" in decision:
                reviewed_cids = {ref["capture_id"] for ref in decision["evidence"]}
                if any(ev["capture_id"] in reviewed_cids for ev in row["evidence"]):
                    row["total_edible_weight_g"] = product["total_edible_weight_g"]
                    row["pack_count"] = product["pack_count"]
                    row["quantity_status"] = "reviewed"
                    row["quantity_review"] = decision
            price_review = decisions.get("prices", {}).get(row["price_id"])
            if price_review:
                allowed = {"regular_price", "currency", "tax_basis", "observed_at"}
                validate_review(price_review, captures, allowed)
                observed_cids = {ev["capture_id"] for ev in row["evidence"]}
                if not any(ref["capture_id"] in observed_cids for ref in price_review["evidence"]):
                    raise ValueError("Price review must cite this observation's capture.")
                if "regular_price" in price_review and positive(price_review["regular_price"]) is None:
                    raise ValueError("Reviewed regular_price must be positive and finite.")
                if "observed_at" in price_review and not aware_time(price_review["observed_at"]):
                    raise ValueError("Reviewed observed_at must include a timezone.")
                if "tax_basis" in price_review and price_review["tax_basis"] != "consumer_tax_included":
                    raise ValueError("Reviewed tax_basis must be consumer_tax_included.")
                if "currency" in price_review and price_review["currency"] != "GBP":
                    raise ValueError("This analytical profile supports reviewed GBP prices only.")
                row.update({k: v for k, v in price_review.items() if k in allowed})
                row.update({"review_status": "reviewed", "review": price_review})
            row["displayed_price_per_100g"] = normalized(row.get("displayed_price"), row["total_edible_weight_g"]) if row.get("currency") == "GBP" else None
            row["regular_price_per_100g"] = normalized(row.get("regular_price"), row["total_edible_weight_g"]) if row.get("currency") == "GBP" else None
            reasons = []
            if product["in_scope"] is not True:
                reasons.append("category_scope_unreviewed" if product["in_scope"] is None else "outside_category_scope")
            if product["identity_status"] != "reviewed":
                reasons.append("variant_and_family_identity_unreviewed")
            if product["group_status"] != "reviewed":
                reasons.append("comparable_group_unreviewed")
            if row["quantity_status"] != "reviewed":
                reasons.append("edible_quantity_" + row["quantity_status"])
            if row.get("currency") != "GBP":
                reasons.append("currency_missing_or_unsupported")
            if positive(row.get("displayed_price")) is None:
                reasons.append("displayed_price_missing_or_invalid")
            if positive(row.get("regular_price")) is None:
                reasons.append("regular_price_unobserved_or_invalid")
            if row["review_status"] != "reviewed":
                reasons.append("price_basis_unreviewed")
            elif not {"regular_price", "currency", "tax_basis", "observed_at"} <= set(price_review):
                reasons.append("price_basis_review_incomplete")
            if row.get("tax_basis") != "consumer_tax_included":
                reasons.append("tax_basis_unknown_or_inconsistent")
            if not aware_time(row.get("observed_at")) or (row.get("time_basis") == "cached_web_representation" and not price_review):
                reasons.append("observation_time_unverified")
            if row.get("available") is not True:
                reasons.append("unavailable" if row.get("available") is False else "availability_unknown")
            if positive(row.get("regular_price")) and row["regular_price_per_100g"] is None:
                reasons.append("normalization_missing_or_out_of_range")
            row["model_eligible"] = not reasons
            row["exclusion_reasons"] = reasons
            prices.append(row)
            if reasons:
                queue.append({"entity_type": "price", "entity_id": row["price_id"], "listing_id": listing, "reasons": reasons})
        product_reasons = []
        if product["review_status"] != "reviewed":
            product_reasons.extend(["identity_scope_group_and_quantity_review_required"])
        if qstatus == "conflict":
            product_reasons.append("conflicting_edible_quantities")
        if result.get("warnings"):
            product_reasons.extend(result["warnings"])
        if not price_index:
            product_reasons.append("no_supported_price_extraction")
        if product_reasons:
            queue.append({"entity_type": "product", "entity_id": listing, "listing_id": listing, "reasons": sorted(set(product_reasons))})
    unknown_prices = set(decisions.get("prices", {})) - {row["price_id"] for row in prices}
    if unknown_prices:
        raise ValueError("Review refers to unknown price IDs: " + ", ".join(sorted(unknown_prices)))
    confirm_raw_snapshot(archive)
    inputs = sorted({item["path"]: item for item in inputs}.values(), key=lambda item: item["path"])
    if implementation != {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in implementation_paths}:
        raise RuntimeError("Cleaning implementation changed during the build; retry after edits finish.")
    version = "chocolate-" + digest({"profile": PROFILE, "implementation": implementation,
                                   "inputs": inputs, "reviews": decisions,
                                   "inventory": [path.relative_to(root).as_posix() for path in archive["inventory"]],
                                   "archive_errors": errors, "unsupported_records": unsupported,
                                   "artifact_availability": sorted(
                                       ({"path": path, "available": available}
                                        for path, available in artifact_cache["availability"].items()),
                                       key=lambda item: item["path"] or "")})[:24]
    products.sort(key=lambda row: row["listing_id"])
    features.sort(key=lambda row: (row["listing_id"], row["name"], digest(row)))
    prices.sort(key=lambda row: row["price_id"])
    eligible = [row for row in prices if row["model_eligible"]]
    counts.update({"price_observations": len(prices), "eligible_price_observations": len(eligible),
                   "feature_assertions": len(features), "unsupported_records": len(unsupported),
                   "archive_errors": len(errors), "review_items": len(queue),
                   "repeated_price_observations_removed": input_price_candidates - len(prices),
                   "duplicate_source_listings_removed": sum(len(ids) - 1 for ids in aliases.values()),
                   "reviewed_variant_ids": len({p["variant_id"] for p in products if p["identity_status"] == "reviewed"}),
                   "reviewed_family_ids": len({p["family_id"] for p in products if p["identity_status"] == "reviewed"})})
    exclusions = Counter(reason for row in prices for reason in row["exclusion_reasons"])
    missingness = Counter(row["name"] for row in features if row["is_current"] and (row.get("status") == "unknown" or row.get("value") in (None, "unknown")))
    support = defaultdict(lambda: defaultdict(set))
    for row in features:
        if row["is_current"] and row.get("value") not in (None, "unknown") and row.get("value_type") in ("category", "categorical", "presence"):
            support[row["name"]][str(row["value"])].add(row["listing_id"])
    brand_lookup = {row["listing_id"]: row["brand"] for row in products}
    single_brand_levels = []
    for name, levels in support.items():
        for value, ids in levels.items():
            brands = {brand_lookup[listing] for listing in ids if brand_lookup[listing]}
            if len(brands) == 1 and all(brand_lookup[listing] for listing in ids):
                single_brand_levels.append({"feature": name, "value": value,
                                            "brand": next(iter(brands)), "source_listing_count": len(ids)})
    report = {"report_format_version": "chocolate-quality-1", "profile_version": PROFILE_VERSION,
              "dataset_version": version, "counts": dict(counts), "source_listing_counts": dict(source_coverage),
              "source_role_counts": dict(Counter(p["source_role"] for p in products)),
              "deduplication": {"scope": "within_selling_source_only", "duplicate_groups": duplicate_groups,
                                "cross_source_merges": 0},
              "exclusion_counts": dict(exclusions), "unknown_feature_assertion_counts": dict(missingness),
              "feature_support_listing_counts": {name: {value: len(ids) for value, ids in values.items()} for name, values in support.items()},
              "single_brand_feature_levels": single_brand_levels,
              "quantity_status_counts": dict(Counter(p["quantity_status"] for p in products)),
              "group_listing_counts": dict(Counter(p["comparable_group"] or "unknown" for p in products)),
              "brands": sorted({p["brand"] for p in products if p["brand"]}),
              "observation_dates": sorted({p["observed_at"][:10] for p in prices if aware_time(p.get("observed_at"))}),
              "unsupported_records": unsupported, "archive_errors": errors,
              "release_ready": False,
              "readiness_status": "review_and_classification_validation_required",
              "limitations": PROFILE["limitations"] + [
                  "Counts describe source listings and assertions, not deduplicated market coverage.",
                  "Saved artifact hashes are retained as provenance; this cleaner checks history consistency, not all original artifact bytes.",
                  "model-inputs contains reviewed price/quantity staging rows, not a fitted training design matrix.",
                  "Rare feature levels and listing support require family/brand overlap checks before regression."]}
    study = {"study_format_version": "chocolate-derived-study-1", "profile_version": PROFILE_VERSION,
             "dataset_version": version, "category": "chocolate", "market": "uk",
             "source_study_ids": sorted(study_ids), "source_collection_windows": [json.loads(value) for value in sorted(windows)],
             "source_listing_counts": dict(source_coverage), "inclusion_policy": "Evidence-backed product scope reviews; unresolved listings retained for coverage.",
             "currency": "GBP", "price_basis": "reviewed ordinary consumer pack price including tax",
             "quantity_basis": "reviewed total edible mass in grams", "normalization_unit": "GBP per 100 g"}
    capture_evidence = sorted(artifact_cache["captures"].values(), key=lambda row: row["capture_id"])
    artifact_rows = sorted(artifact_cache["artifacts"].values(), key=lambda row: row["artifact_id"])
    for rows in (products, features, prices, eligible, queue, capture_evidence, artifact_rows):
        for row in rows:
            row["dataset_version"] = version
    files = {"profile.json": json_bytes(PROFILE), "study.json": json_bytes(study), "quality-report.json": json_bytes(report)}
    for name, rows in (("products", products), ("features", features), ("prices", prices), ("model-inputs", eligible), ("review-queue", queue), ("capture-evidence", capture_evidence), ("artifacts", artifact_rows)):
        files[name + ".jsonl"] = b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in rows)
    for role in ("brand", "retail", "unknown"):
        for name, rows in (("products", products), ("prices", prices)):
            files[role + "/" + name + ".jsonl"] = b"".join(
                (json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
                for row in rows if row["source_role"] == role)
    manifest = {"manifest_format_version": "chocolate-derived-manifest-1", "profile_version": PROFILE_VERSION,
                "dataset_version": version, "input_reference_base": "supplied collections root",
                "inputs": inputs, "reviews": decisions, "implementation_sha256": implementation,
                "managed_files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (output / name).parent.mkdir(parents=True, exist_ok=True)
        temporary = output / ("." + name + ".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        if not inside(temporary.resolve(), output) or temporary.is_symlink() or not inside((output / name).resolve(), output):
            raise ValueError("Derived output paths must not be symlinks outside the output directory.")
        temporary.write_bytes(data)
        temporary.replace(output / name)
    return report
