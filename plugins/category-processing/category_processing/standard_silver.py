"""Bronze to reusable Silver facts, identities, corrections and profiles."""

import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from .adapters import extract_capture
from .archive import (
    confirm_raw_snapshot,
    deduplicate_archive,
    digest,
    inside,
    json_bytes,
    load_raw_archive,
    pointer_value,
    read_json,
    sha256,
    source_identity,
)
from .discovery import discover_fields
from .profiles import profile_provenance
from .silver_chocolate import refine_quantities
from .silver_contracts import (
    FILES,
    STATES,
    column,
    load_silver_contracts,
    meaning,
    resolve_silver_profile,
    result_state,
    validate_result,
)
from .silver_profile import build_profile, render_profile
from .silver_snapshot import MANIFEST, no_links, publish, row_bytes, verified_snapshot
from .source_index import SourceIndex, encoded
from .values import standardize_value


def checksum(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def context_for(definition, item):
    return {key: item.get(key, definition.get(key)) for key in ("scope", "qualifier", "basis")}


def select_result(candidates):
    """Resolve only candidates for the same subject, observation, field and context."""
    if not candidates:
        return None, None
    for method in ("reviewed", "parsed", "inferred"):
        selected = [item for item in candidates if item["method"] == method]
        usable = [item for item in selected if result_state(item["result"]) == "available"]
        if usable:
            unique = {encoded(item["result"]): item["result"] for item in usable}
            return (next(iter(unique.values())) if len(unique) == 1 else {"state": "conflict"}), method
        if selected and method == "reviewed":
            return selected[-1]["result"], method
    # A failed higher priority attempt is retained but cannot suppress an available result.
    for method in ("parsed", "inferred"):
        selected = [item for item in candidates if item["method"] == method]
        if selected:
            return selected[0]["result"], method
    return None, None


def reference(capture, pointer):
    pointer_value(capture, pointer)
    return {"capture_id": capture["capture_id"], "bronze_path": capture["history_path"],
            "capture_sha256": digest(capture), "pointer": pointer}


def extract_subjects(capture, recipe, index, listing_id, namespace, issues):
    """A repeated component needs an explicit source key, never its array position."""
    result = []
    for collection in recipe.get("collections", []):
        try:
            members = pointer_value(capture, collection["pointer"])
        except (KeyError, IndexError, TypeError):
            issues.append({"subject_id": listing_id, "capture_id": capture["capture_id"],
                           "reason": "missing_child_collection", "collection": collection["name"]})
            continue
        if not isinstance(members, list):
            issues.append({"subject_id": listing_id, "reason": "invalid_child_collection", "collection": collection["name"]})
            continue
        keys = []
        for member in members:
            try:
                key = pointer_value(member, collection["id_pointer"])
                keys.append(key if type(key) in (str, int) and str(key).strip() else None)
            except (KeyError, IndexError, TypeError):
                keys.append(None)
        counts = Counter(encoded(key) for key in keys)
        for position, (member, key) in enumerate(zip(members, keys)):
            base = collection["pointer"] + "/" + str(position)
            if key is None or counts[encoded(key)] != 1:
                issues.append({"subject_id": listing_id, "reason": "ambiguous_child_identity",
                               "collection": collection["name"], "source": [reference(capture, base)]})
                continue
            subject = index.assign(collection["name"], [*namespace, key], parent=listing_id)
            items = []
            for field in collection["fields"]:
                try:
                    value = pointer_value(member, field["pointer"])
                except (KeyError, IndexError, TypeError):
                    continue
                items.append({**field, "value": value, "pointer": base + field["pointer"],
                              "evidence_key": field["pointer"], "method": "structured_child_field"})
            result.append((subject, collection["name"], items))
    return result


def build_standard_silver(archive_root, output, profile_root, *, state_db=None, inferences=None, backend="python"):
    profile_root = resolve_silver_profile(profile_root)
    source, output, profile_root = (no_links(path) for path in (archive_root, output, profile_root))
    state_db = no_links(state_db or output.parent / ".silver-state" / (output.name + ".sqlite"))
    for left, right in ((source, output), (profile_root, output)):
        if inside(left, right) or inside(right, left):
            raise ValueError("Silver output must be separate from Bronze and contracts.")
    if any(inside(state_db, path) for path in (source, output, profile_root)):
        raise ValueError("Persistent source index must live outside Bronze, contracts and generated snapshots.")
    documents, original_hashes = load_silver_contracts(profile_root)
    profile, mappings, recipe = (documents[name] for name in ("profile.json", "source-mappings.json", "pipeline.json"))
    category, market = profile["category"], profile["market"]
    archive = load_raw_archive(source, category, market)
    sellers, aliases, deduplication = deduplicate_archive(archive, category, market, recipe.get("source_roles", {}))
    for alias in aliases:
        alias["listing_id"] = alias["seller_uid"]
    inference_input = read_json(inferences) if isinstance(inferences, (str, Path)) else deepcopy(inferences or [])
    if not isinstance(inference_input, list):
        raise ValueError("Inferences must be an array of assertions with subject_id, capture_id, attribute, pointer and value.")
    inference_groups = defaultdict(list)
    for item in inference_input:
        inference_groups[(item["subject_id"], item["capture_id"])].append(item)
    used_inferences = set()
    assertions, facts, products, subjects, prices, discovered, issues = [], [], [], {}, [], [], []
    implementation = {path.name: sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))}
    with SourceIndex(state_db) as index:
        assigned = set()
        for seller in sellers:
            latest = next(cap for cap in seller["captures"] if cap["capture_id"] == seller["latest_capture_id"])
            identity = source_identity(latest["raw_record"])
            key = [category, market, list(identity) if identity else {"archive_record": seller["listing_id"]}]
            preserved = index.lookup_alias([category, market, seller["source_key"]], seller["listing_id"]) if identity is None else None
            listing = preserved or index.assign("listing", key, preferred=seller["seller_uid"])
            if listing in assigned:
                raise ValueError("Unresolved source aliases need explicit archive identity reconciliation before they can be combined.")
            assigned.add(listing)
            for alias in seller["source_listing_ids"]:
                index.alias([category, market, seller["source_key"]], alias, listing)
                for source_row in aliases:
                    if source_row["source_listing_id"] == alias:
                        source_row["listing_id"] = source_row["seller_uid"] = listing
            if identity is None:
                issues.append({"subject_id": listing, "reason": "source_identity_requires_review",
                               "source": [reference(latest, "/raw_record")]})
            for capture in seller["captures"]:
                cid = capture["capture_id"]
                observation = index.assign("observation", [category, market, cid], parent=listing)
                try:
                    extracted = refine_quantities(capture, extract_capture(capture, recipe), recipe)
                except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
                    extracted = {"attributes": [], "prices": [], "extraction_failed": True}
                    issues.append({"subject_id": listing, "capture_id": cid, "reason": "extraction_failed",
                                   "error": str(error), "source": [reference(capture, "/raw_record")]})
                for rejected in extracted.get("rejected_candidates", []):
                    issues.append({**rejected, "subject_id": listing, "capture_id": cid,
                                   "source": [reference(capture, rejected["pointer"])]})
                for price in extracted["prices"]:
                    price_id = index.assign("price", [cid, price["pointer"]], parent=listing)
                    prices.append({**price, "subject_id": listing, "listing_id": listing, "seller_uid": listing,
                                   "source_key": seller["source_key"], "source_role": seller["source_role"],
                                   "capture_id": cid, "observation_id": price_id,
                                   "is_current": cid == seller["latest_capture_id"],
                                   "source": [reference(capture, price["pointer"])], "method": "parsed",
                                   "parser_method": price["method"]})
                    if price.get("displayed_price") is None and price.get("raw_value") is not None:
                        prices[-1]["displayed_price"] = {"state": "parse_error"}
                        issues.append({"subject_id": listing, "capture_id": cid, "reason": "price_parse_error",
                                       "raw_value": price["raw_value"], "source": prices[-1]["source"]})
                handled = [item["pointer"] for item in extracted["attributes"] if item.get("value") is not None]
                handled += [price["pointer"] for price in extracted["prices"]]
                handled += extracted.get("handled_pointers", [])
                for item in discover_fields(capture, recipe, handled):
                    discovered.append({**item, "subject_id": listing, "capture_id": cid,
                                       "source": [reference(capture, item["field_pointer"])]})
                children = extract_subjects(capture, recipe, index, listing, [category, market], issues)
                for subject, kind, items in [(listing, "listing", extracted["attributes"]), *children]:
                    current = cid == seller["latest_capture_id"]
                    envelope = {"subject_id": subject, "listing_id": listing, "seller_uid": listing,
                                "subject_kind": kind, "source_key": seller["source_key"],
                                "source_role": seller["source_role"], "capture_id": cid, "observation_id": observation,
                                "is_current": current, "capture_recorded_at": capture.get("recorded_at"),
                                "category": category, "market": market}
                    subjects[subject] = {"subject_id": subject, "listing_id": listing, "subject_kind": kind,
                            "source_key": seller["source_key"], "category": category, "market": market}
                    candidates = defaultdict(list)
                    inferred = inference_groups.get((subject, cid), [])
                    if inferred:
                        used_inferences.add((subject, cid))
                    for item, method in [(item, "parsed") for item in items] + [(item, "inferred") for item in inferred]:
                        name, raw_value = item["attribute"], item.get("value")
                        if raw_value is None or raw_value == "unknown":
                            continue
                        ref = reference(capture, item["pointer"])
                        if name not in profile["attributes"]:
                            issues.append({**envelope, "field": name, "reason": "unmapped_field", "source": [ref], "raw_value": raw_value})
                            continue
                        definition = profile["attributes"][name]
                        context = context_for(definition, item)
                        diagnostic = None
                        try:
                            result = standardize_value(name, raw_value, profile, mappings, item.get("unit"))
                            if result == []:
                                result = {"state": "unresolved"}
                        except (ValueError, TypeError, KeyError, OverflowError) as error:
                            result = {"state": "parse_error" if method == "parsed" else "inference_error"}
                            diagnostic = str(error)
                        assertion = {**envelope, "field": name, "context": context, "result": result, "method": method,
                                     "parser_method": item.get("method"), "source": [ref], "raw_value": raw_value,
                                     "evidence_key": item.get("evidence_key", item["pointer"]),
                                     "diagnostic": diagnostic, "evidence_value": pointer_value(capture, item["pointer"])}
                        assertions.append(assertion)
                        candidates[(name, encoded(context))].append(assertion)
                        if result_state(result) != "available":
                            issues.append({**assertion, "reason": result_state(result)})
                    for name, definition in profile["attributes"].items():
                        contexts = {key[1] for key in candidates if key[0] == name}
                        if not contexts:
                            contexts = {encoded(context_for(definition, {}))}
                        for context_key in sorted(contexts):
                            values = candidates[(name, context_key)]
                            result, method = select_result(values)
                            if not values and extracted.get("extraction_failed") and kind == "listing":
                                result, method = {"state": "parse_error"}, "parsed"
                            refs = {encoded(ref): ref for item in values for ref in item["source"]}
                            # Applicability follows evidence content and meaning, not parser version or folder order.
                            evidence = sorted({encoded({"pointer": item["evidence_key"], "value": item["evidence_value"]})
                                               for item in values})
                            fact = {**envelope, "field": name, "column": column(name, definition),
                                    "context": json.loads(context_key), "result": result, "method": method,
                                    "source": [refs[key] for key in sorted(refs)] or ([reference(capture, "/raw_record")] if extracted.get("extraction_failed") else []),
                                    "definition_hash": meaning(definition),
                                    "evidence_hash": digest(evidence), "prior_result": result, "correction_id": None}
                            if result_state(result) == "conflict":
                                issues.append({**fact, "reason": "conflict"})
                            facts.append(fact)
        if set(inference_groups) - used_inferences:
            raise ValueError("Inference subjects/captures do not resolve in this Bronze archive.")
        active = index.active(subjects)
        matched = set()
        for fact in facts:
            if not fact["is_current"]:
                continue
            key = (fact["subject_id"], fact["field"], encoded(fact["context"]))
            decision = active.get(key)
            if decision is None:
                continue
            matched.add(key)
            current_refs = {encoded(ref) for candidate in facts if candidate["is_current"] and candidate["subject_id"] == fact["subject_id"]
                            for ref in candidate["source"]}
            if (any(fact[name] != decision[name] for name in ("definition_hash", "evidence_hash"))
                    or any(encoded(ref) not in current_refs for ref in decision.get("additional_source", []))):
                issues.append({**fact, "reason": "stale_correction", "correction": decision})
                continue
            validate_result(fact["field"], decision["result"], profile, mappings)
            fact.update(result=decision["result"], method="reviewed", correction_id=decision["correction_id"])
            fact["source"] = list({encoded(ref): ref for ref in [*fact["source"], *decision["source"]]}.values())
        for key in active.keys() - matched:
            issues.append({"reason": "stale_correction", "correction": active[key]})
        by_subject = defaultdict(list)
        for fact in facts:
            if fact["is_current"]:
                by_subject[fact["subject_id"]].append(fact)
        for subject, values in sorted(by_subject.items()):
            row = {**subjects[subject], "capture_id": values[0]["capture_id"], "schema_version": profile["schema_version"]}
            by_field = defaultdict(list)
            for fact in values:
                by_field[fact["field"]].append(fact)
            for name, definition in profile["attributes"].items():
                col, selected = column(name, definition), by_field[name]
                if len(selected) == 1:
                    row[col], row[col + ".method"] = selected[0]["result"], selected[0]["method"]
                else:
                    row[col], row[col + ".method"] = {"state": "unresolved"}, None
                row[col + ".source"] = list({encoded(ref): ref for item in selected for ref in item["source"]}.values())
                row[col + ".contexts"] = [{key: item[key] for key in ("context", "result", "method", "source", "correction_id")}
                                           for item in selected]
            products.append(row)
        children_by_parent = defaultdict(list)
        for row in products:
            if row["subject_kind"] != "listing":
                children_by_parent[row["listing_id"]].append(deepcopy(row))
        for row in products:
            if row["subject_kind"] == "listing":
                row["children"] = sorted(children_by_parent[row["subject_id"]], key=lambda child: child["subject_id"])
        subject_ids = set(subjects) | {item["observation_id"] for item in facts} | {item["observation_id"] for item in prices}
        source_index = index.snapshot(subject_ids)
        corrections = [item for item in index.history() if item["subject_id"] in subjects]
    files = {name: json_bytes(value) for name, value in documents.items()}
    files.update({"source-index.json": json_bytes(source_index), "corrections.jsonl": row_bytes(corrections),
                  "raw-inputs.json": json_bytes(archive["inputs"]), "inferences.json": json_bytes(inference_input)})
    identity = {"format": MANIFEST, "contract_sha256": {name: checksum(files[name]) for name in FILES},
                "input_contract_sha256": original_hashes, "implementation_sha256": implementation,
                "source_index_sha256": checksum(files["source-index.json"]),
                "corrections_sha256": checksum(files["corrections.jsonl"]),
                "raw_inputs_sha256": checksum(files["raw-inputs.json"]), "inferences_sha256": digest(inference_input),
                "report_backend": backend}
    version = "silver-" + digest(identity)[:24]
    provenance = {**identity, "silver_dataset_version": version, "bronze_snapshot_id": digest(archive["inputs"])}
    report = build_profile(facts, list(subjects.values()), profile, provenance, backend)
    quality = {"status": "partial" if archive["errors"] or archive["unsupported"] or any(item["reason"] == "extraction_failed" for item in issues) else "complete_snapshot",
               "dataset_version": version, "release_ready": False,
               "counts": {"source_aliases": len(aliases), "listings": len(sellers), "subjects": len(subjects),
                          "captures": len({(item["listing_id"], item["capture_id"]) for item in facts}),
                          "facts": len(facts), "issues": len(issues), "unmapped_fields": len(discovered)},
               "archive_errors": archive["errors"], "unsupported": archive["unsupported"],
               "issue_counts": dict(Counter(item["reason"] for item in issues)), "deduplication": deduplication,
               "schema_version": profile["schema_version"],
               "limitations": ["Source coverage and successful parsing do not establish semantic correctness.",
                               "Comparison groups, target policies, eligibility and model inputs are prepared in Gold.",
                               "Repeated subjects require source-specific stable keys in the recipe."]}
    dictionary = {"format_version": "silver-data-dictionary-2", "schema_version": profile["schema_version"],
                  "missing": None, "states": sorted(STATES),
                  "method_precedence": ["reviewed", "parsed", "inferred"],
                  "source_reference": "Immutable Bronze history path, capture hash and JSON pointer; arrays retain every reference.",
                  "contexts": "scope, qualifier and basis; multiple contexts remain separately addressable in facts.jsonl.",
                  "attributes": profile["attributes"]}
    for name, values in (("products", products), ("subjects", list(subjects.values())), ("facts", facts),
                         ("assertions", assertions), ("prices", prices), ("review-queue", issues),
                         ("source-listings", aliases), ("discovered-fields", discovered)):
        files[name + ".jsonl"] = row_bytes(values)
    files.update({"schema-profile.json": json_bytes(report), "schema-profile.md": render_profile(report).encode(),
                  "quality-report.json": json_bytes(quality), "data-dictionary.json": json_bytes(dictionary)})
    manifest = {"manifest_format_version": MANIFEST, "dataset_version": version, "category": category, "market": market,
                "schema_version": profile["schema_version"], "identity": identity,
                "contract_source": profile_provenance(profile_root),
                "contract_sha256": identity["contract_sha256"],
                "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    confirm_raw_snapshot(archive)
    if original_hashes != {name: sha256(profile_root / name) for name in FILES} or implementation != {
            path.name: sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))}:
        raise ValueError("Contracts or implementation changed during the build.")
    destination = publish(output, version, files)
    verified_snapshot(destination)
    return {**quality, "output": str(destination), "state_db": str(state_db)}
