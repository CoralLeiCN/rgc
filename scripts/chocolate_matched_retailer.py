"""Fit exact-variant and retailer effects from reviewed, contemporaneous Gold.

This diagnostic estimates matched-assortment contrasts. Its identifiers define
fixed effects, never regression features or new-product prediction support.
Local working contracts are explicit unpublished dataset-contract proposals.
"""

import argparse
import itertools
import math
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from chocolate_current_price import (
    current_price_targets,
    validate_current_price_targets,
)
from chocolate_gold import (
    checked_path,
    read_managed,
    reject_output_links,
    verified_gold,
)
from chocolate_model import (
    ModelContractError,
    regular_price_basis_supported,
    validate_candidates,
    validate_target_policy,
)
from train_chocolate_model import (
    CONTRACTS,
    ROOT,
    checksum,
    json_bytes,
    read_json,
    rows,
    validate_price_targets,
    write_run,
)

VERSION = "chocolate-matched-retailer-design-1"
CURRENT_VERSION = "chocolate-matched-retailer-design-3"
CURRENT_TARGET = {
    "price_basis_contract_version": "current-consumer-price-1",
    "price_basis": "current_displayed", "tax_basis": "as_displayed",
    "promotion_basis": "as_displayed", "fallback_policy": "reject",
    "name": "log_current_gbp_per_100g", "currency": "GBP", "unit": "GBP_per_100g",
    "quantity_attribute": "quantity.total_edible_weight_g", "base_quantity": 100,
    "assumption": "Collected current/displayed price is the modeling target; promotion and tax context are retained limitations.",
}
SPLIT_ALGORITHM = "sha256(seed:family_id), lexicographic digest order; floor(0.6N), floor(0.2N), remainder"
COMMON_POLICY = {
    "version": "chocolate-comparison-policy-1",
    "cohort": "standard_single_pack_supermarket_chocolate_bar",
    "required": ["retailer", "reviewed_brand", "reviewed_type", "verified_edible_weight", "variant", "family"],
    "regression_core": ["log_edible_weight", "type", "recipe", "inclusion", "retailer"],
    "optional": ["cocoa_with_basis_and_missing_indicator", "reviewed_claims"],
    "optional_numeric_missingness": "fitting-only supported type/basis median; fitting-wide median fallback",
    "optional_categorical_missingness": "explicit_unknown",
    "feature_selection": "grouped fitting-partition validation; known-brand identification required for shared regression features",
    "exclude": ["identifiers", "names", "observed_prices", "price_derived_fields", "unrestricted_text"],
    "matched_exception": "exact_variant and retailer fixed effects only; no admissible regression feature fitting",
    "family_weighting": "1/n_f recomputed within each partition, component, diagnostic subset and bootstrap replicate",
    "brand_identification_status": "pending_regression_sessions; not_applicable_to_exact_variant_effects",
}
EVIDENCE_FIELDS = ("cohort", "formulation", "flavor", "edible_weight_g", "pack_count", "brand",
                   "chocolate_type", "observed_at", "observed_at_basis", "channel", "location_scope", "membership")
IMPLEMENTATION = ("scripts/chocolate_matched_retailer.py", "scripts/train_chocolate_model.py",
                  "scripts/chocolate_gold.py", "scripts/chocolate_gold_eligibility.py",
                  "scripts/chocolate_current_price.py", "scripts/dataset_contracts.py",
                  "scripts/chocolate_model.py", "scripts/chocolate_cleanup/core.py")


def target_policy(target):
    """Keep the explicit current proxy separate from historical regular prices."""
    policy = validate_target_policy(target)
    return dict(target) if policy["price_basis_contract_version"] == "current-consumer-price-1" else policy


def is_current_target(target):
    return isinstance(target, dict) and target.get("price_basis_contract_version") == "current-consumer-price-1"


def target_values(row):
    if "model_target" in row:
        return row["model_target"]["unit_gbp_per_100g"], row["model_target"]["log_unit_gbp_per_100g"]
    return row["target"].get("regular_price_per_100g_gbp"), row["target"].get("log_regular_price_per_100g_gbp")


def working_contract(gold_root=None, *, current_price_proxy=False):
    """Prepare a local contract from checksum-verified pinned target semantics."""
    from dataset_contracts import (
        CURRENT_PRICE_REFERENCE,
        SCHEMA_REFERENCE,
        load_manifest,
        resolve_contract_root,
        resolve_current_price_contract_root,
    )
    root = resolve_contract_root(offline=True)
    design = read_json((root / "model-design.json").read_bytes())
    validate_target_policy(design["target"])
    contract = {"model_design_version": VERSION, "model_id": "matched_retailer",
            "publication_status": "unpublished_working_contract", "base_reference": read_json(SCHEMA_REFERENCE.read_bytes()),
            "target": design["target"], "common_policy": COMMON_POLICY,
            "split_seed": 1729, "split_algorithm": SPLIT_ALGORITHM, "bootstrap_seed": 1729,
            "bootstrap_replicates": 200, "match_hours": 48,
            "minimum_independent_families": 2, "minimum_bootstrap_success_fraction": 0.8,
            "retailers": ["Ocado", "Waitrose"], "price_window": None,
            "prediction_task": "matched_assortment_contrasts_only"}
    if gold_root is not None:
        source = Path(gold_root).resolve()
        gold_bytes = (source / "manifest.json").read_bytes()
        _, _, inputs = verified_gold(source)
        design = read_json(inputs["model-design.json"])
        if not current_price_proxy:
            validate_target_policy(design["target"])
        contract.update(input_contract_basis="verified_gold_snapshot",
                        input_gold_manifest_sha256=checksum(gold_bytes),
                        input_contract_sha256={n: checksum(inputs[n]) for n in CONTRACTS},
                        input_storage_model_design_version=design["model_design_version"],
                        target=design["target"])
        if (source / "manifest.json").read_bytes() != gold_bytes:
            raise ModelContractError("Gold changed during working contract preparation")
    if current_price_proxy:
        target_root = resolve_current_price_contract_root(offline=True)
        target_design = read_json((target_root / "model-design.json").read_bytes())
        validate_target_policy(target_design["target"])
        contract["target"] = target_design["target"]
        contract["model_design_version"] = CURRENT_VERSION
        contract["target_reference"] = load_manifest(CURRENT_PRICE_REFERENCE)
        contract["target_contract_version"] = target_design["model_design_version"]
        contract["current_preparation_version"] = "chocolate-current-price-target-1"
    return contract


def validate_contract(contract):
    target_policy(contract.get("target"))
    expected_version = CURRENT_VERSION if is_current_target(contract.get("target")) else VERSION
    if (contract.get("model_design_version") != expected_version or contract.get("model_id") != "matched_retailer"
            or contract.get("publication_status") != "unpublished_working_contract"
            or contract.get("common_policy") != COMMON_POLICY or contract.get("split_seed") != 1729
            or contract.get("split_algorithm") != SPLIT_ALGORITHM
            or contract.get("retailers") != ["Ocado", "Waitrose"]
            or contract.get("prediction_task") != "matched_assortment_contrasts_only"):
        raise ModelContractError("Unsupported local matched-retailer contract or common policy")
    for field, minimum in (("bootstrap_seed", 0), ("bootstrap_replicates", 20), ("minimum_independent_families", 2)):
        if type(contract.get(field)) is not int or contract[field] < minimum:
            raise ModelContractError("Invalid " + field)
    if contract.get("match_hours") != 48 or contract.get("minimum_bootstrap_success_fraction") != 0.8:
        raise ModelContractError("Unsupported matching or bootstrap support policy")
    if contract.get("input_contract_basis", "published_reference") not in {"published_reference", "verified_gold_snapshot"}:
        raise ModelContractError("Unsupported working input contract basis")
    if contract.get("price_window") is not None:
        start, end = window_bounds(contract)
        if start > end:
            raise ModelContractError("Price window start exceeds end")


def time_value(value):
    if not isinstance(value, str):
        raise ModelContractError("Genuine aware observation time is required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ModelContractError("Invalid observation time") from error
    if result.tzinfo is None:
        raise ModelContractError("Observation time must include timezone")
    return result.astimezone(timezone.utc)


def window_bounds(contract):
    window = contract["price_window"]
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ModelContractError("Declare price_window start/end before matching")
    return time_value(window["start"]), time_value(window["end"])


def frozen_split(observations, seed=1729):
    """Prices and brands never influence random whole-family assignment."""
    families = sorted({r["family_id"] for r in observations},
                      key=lambda f: (checksum((str(seed) + ":" + f).encode()), f))
    n_fit, n_cal = int(len(families) * 0.6), int(len(families) * 0.2)
    assignments = {f: "fitting" if i < n_fit else "calibration" if i < n_fit + n_cal else "testing"
                   for i, f in enumerate(families)}
    return {"algorithm": SPLIT_ALGORITHM, "seed": seed, "family_order": families,
            "assignments": assignments, "within_brand_quotas": False,
            "counts": dict(Counter(assignments.values()))}


def family_weights(observations):
    counts = Counter(r["family_id"] for r in observations)
    return np.array([1 / counts[r["family_id"]] for r in observations])


def pointer_value(source, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ModelContractError("Evidence requires a JSON pointer")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        source = source[int(token)] if isinstance(source, list) else source[token]
    return source


def reviewed_evidence(path):
    """Copy hash-verified original evidence with field-level reviewed references."""
    reject_output_links(path)
    raw = path.read_bytes()
    bundle = read_json(raw)
    if (bundle.get("format") != "chocolate-exact-match-reviews-1" or not isinstance(bundle.get("reviews"), dict)
            or type(bundle.get("synthetic_fixture")) is not bool):
        raise ModelContractError("Unsupported exact-match evidence bundle")
    sources = read_managed(path.parent.resolve(), bundle.get("managed_files"), "Match evidence")
    files = {"inputs/match-review.json": raw, **{"evidence/" + n: b for n, b in sources.items()}}
    reviews = {}
    for identifier, review in bundle["reviews"].items():
        if (not isinstance(review, dict) or review.get("status") != "reviewed" or not isinstance(review.get("reviewed_by"), str)
                or not review["reviewed_by"].strip()):
            raise ModelContractError("Match review requires an identified reviewer")
        values = {}
        for field in EVIDENCE_FIELDS:
            item = review.get("fields", {}).get(field)
            if (not isinstance(item, dict) or not isinstance(item.get("evidence"), list)
                    or not item["evidence"] or item.get("value") is None):
                raise ModelContractError("Missing reviewed exact-match field: " + field)
            for ref in item["evidence"]:
                if not isinstance(ref, dict) or set(ref) != {"source_file", "pointer"}:
                    raise ModelContractError("Evidence reference requires source_file and pointer")
                try:
                    original = pointer_value(read_json(sources[ref["source_file"]]), ref["pointer"])
                except (KeyError, IndexError, TypeError, ValueError) as error:
                    raise ModelContractError("Unresolvable exact-match evidence") from error
                if original != item["value"] or type(original) is not type(item["value"]):
                    raise ModelContractError("Reviewed field differs from original evidence: " + field)
            values[field] = item["value"]
        reviews[identifier] = values
    return bundle, reviews, files


def prepare_matches(observations, prices, reviews, contract):
    """Refuse unresolved identity/context; exclude out-of-scope or unmatched rows."""
    start, end = window_bounds(contract)
    accepted, domain, variants = [], {}, {}
    seen, listings = set(), set()
    for row in sorted(observations, key=lambda r: r["observation_id"]):
        oid = row["observation_id"]
        if oid in seen or row["listing_id"] in listings:
            raise ModelContractError("Duplicate price occasion/listing requires upstream selection")
        seen.add(oid)
        listings.add(row["listing_id"])
        ev = reviews.get(oid)
        if ev is None:
            domain[oid] = "missing_reviewed_exact_variant_context"
            continue
        pred = row["predictors"]
        if (row["source_role"] != "retail" or row["comparable_group"] != "bar"
                or ev["cohort"] != COMMON_POLICY["cohort"] or type(ev["pack_count"]) is not int
                or ev["pack_count"] != 1 or pred["identity.retailer"] not in contract["retailers"]):
            domain[oid] = "outside_declared_cohort_or_retailers"
            continue
        for field in ("formulation", "flavor", "brand", "chocolate_type", "location_scope", "channel"):
            if not isinstance(ev[field], str) or not ev[field].strip() or ev[field].lower() == "unknown":
                raise ModelContractError("Unresolved reviewed context: " + field)
        if (ev["observed_at_basis"] != "source_price_observation" or ev["channel"] != "online"
                or ev["membership"] != "public_non_member"):
            domain[oid] = "unresolved_or_incomparable_price_context"
            continue
        if (type(ev["edible_weight_g"]) not in (float, int) or ev["edible_weight_g"] <= 0
                or not math.isfinite(ev["edible_weight_g"])
                or ev["edible_weight_g"] != pred["quantity.total_edible_weight_g"]
                or ev["brand"] != pred["identity.brand"] or ev["chocolate_type"] != pred["composition.chocolate_type"]
                or time_value(ev["observed_at"]) != time_value(prices[oid]["observed_at"])):
            raise ModelContractError("Exact variant/context evidence disagrees with Gold")
        timestamp = time_value(ev["observed_at"])
        if not start <= timestamp <= end:
            domain[oid] = "outside_price_window"
            continue
        signature = (row["family_id"], ev["formulation"], ev["flavor"], ev["edible_weight_g"],
                     ev["pack_count"], ev["brand"], ev["chocolate_type"])
        if variants.setdefault(row["variant_id"], signature) != signature:
            raise ModelContractError("Exact variant has conflicting formulation/flavor/weight/pack/family evidence")
        accepted.append({**row, "retailer": pred["identity.retailer"], "match_context": ev,
                         "timestamp": timestamp.isoformat()})
        domain[oid] = "evidence_ready"
    return accepted, domain


def contemporaneous(observations, hours=48):
    """Require one common context and a full variant window within the limit."""
    variants = defaultdict(list)
    for row in observations:
        variants[row["variant_id"]].append(row)
    result, excluded = [], {}
    for group in variants.values():
        retailers = [r["retailer"] for r in group]
        contexts = {(r["match_context"]["channel"], r["match_context"]["location_scope"],
                     r["match_context"]["membership"]) for r in group}
        dates = [time_value(r["timestamp"]) for r in group]
        reason = None
        if len(set(retailers)) < 2:
            reason = "no_other_retailer_for_exact_variant"
        elif len(set(retailers)) != len(retailers):
            reason = "duplicate_variant_retailer_observation"
        elif len(contexts) != 1:
            reason = "incomparable_channel_location_membership"
        elif (max(dates) - min(dates)).total_seconds() > hours * 3600:
            reason = "variant_observations_exceed_48_hours"
        if reason:
            excluded.update({r["observation_id"]: reason for r in group})
        else:
            result.extend(group)
    return sorted(result, key=lambda r: r["observation_id"]), excluded


def overlap_graph(observations):
    variant_rows, edges = defaultdict(list), defaultdict(lambda: {"variants": set(), "families": set()})
    adjacency = defaultdict(set)
    for row in observations:
        variant_rows[row["variant_id"]].append(row)
        adjacency[row["retailer"]]
    for variant, group in variant_rows.items():
        for left, right in itertools.combinations(sorted({r["retailer"] for r in group}), 2):
            adjacency[left].add(right)
            adjacency[right].add(left)
            edges[(left, right)]["variants"].add(variant)
            edges[(left, right)]["families"].update(r["family_id"] for r in group)
    components, seen = [], set()
    for retailer in sorted(adjacency):
        if retailer in seen:
            continue
        todo, found = [retailer], set()
        while todo:
            node = todo.pop()
            if node in found:
                continue
            found.add(node)
            todo.extend(adjacency[node] - found)
        seen.update(found)
        components.append(sorted(found))
    links = [{"retailers": list(pair), "variants": sorted(s["variants"]), "families": sorted(s["families"]),
              "independent_family_count": len(s["families"])} for pair, s in sorted(edges.items())]
    bridge_families = []
    for family in sorted({r["family_id"] for r in observations}):
        remaining = [r for r in observations if r["family_id"] != family]
        remaining_components = _components_with_nodes(remaining, set(adjacency))
        if len(remaining_components) > len(components):
            bridge_families.append(family)
    return {"retailer_variant_edges": [{"retailer": r["retailer"], "variant": r["variant_id"],
                                       "family": r["family_id"]} for r in observations],
            "components": components, "direct_links": links, "weak_bridge_families": bridge_families}


def _components_with_nodes(observations, nodes):
    # A small independent graph traversal avoids recursive bridge diagnostics.
    adjacency = {n: set() for n in nodes}
    variants = defaultdict(set)
    for row in observations:
        variants[row["variant_id"]].add(row["retailer"])
    for retailers in variants.values():
        for a, b in itertools.combinations(retailers, 2):
            adjacency[a].add(b)
            adjacency[b].add(a)
    result, seen = [], set()
    for n in sorted(nodes):
        if n in seen:
            continue
        group, todo = set(), [n]
        while todo:
            item = todo.pop()
            if item not in group:
                group.add(item)
                todo.extend(adjacency[item] - group)
        seen.update(group)
        result.append(sorted(group))
    return result


def solve_component(observations, retailers):
    variants = sorted({r["variant_id"] for r in observations})
    reference = retailers[0]
    columns = [("variant", v) for v in variants] + [("retailer", r) for r in retailers[1:]]
    matrix = np.array([[float(row["variant_id"] == value) if kind == "variant"
                        else float(row["retailer"] == value) for kind, value in columns] for row in observations])
    weights = family_weights(observations)
    weighted = matrix * np.sqrt(weights)[:, None]
    target = np.array([target_values(r)[1] for r in observations])
    params, _, rank, singular = np.linalg.lstsq(weighted, target * np.sqrt(weights), rcond=None)
    if rank != len(columns) or singular[0] / singular[-1] > 1e12:
        raise ModelContractError("Unidentified or ill-conditioned matched-retailer effects")
    return {"reference_retailer": reference, "retailers": retailers, "rank": int(rank),
            "condition_number": float(singular[0] / singular[-1]),
            "variant_effects": {v: float(params[i]) for i, v in enumerate(variants)},
            "retailer_effects": {reference: 0.0, **{r: float(params[len(variants) + i]) for i, r in enumerate(retailers[1:])}}}


def pair_effect(observations, pair):
    component = next((c for c in _components_with_nodes(observations, {r["retailer"] for r in observations})
                      if set(pair) <= set(c)), None)
    if component is None:
        return None
    subset = [r for r in observations if r["retailer"] in component]
    model = solve_component(subset, component)
    return model["retailer_effects"][pair[1]] - model["retailer_effects"][pair[0]]


def fit_matched(observations, contract):
    """Fit only this estimator; family bootstrap resamples complete families."""
    if not observations:
        raise ModelContractError("No contemporaneous exact variants in fitting partition")
    graph = overlap_graph(observations)
    models, contrasts, uncertainty = [], [], []
    rng = np.random.default_rng(contract["bootstrap_seed"])
    for retailers in graph["components"]:
        if len(retailers) < 2:
            continue
        subset = [r for r in observations if r["retailer"] in retailers]
        families = sorted({r["family_id"] for r in subset})
        model = solve_component(subset, retailers)
        models.append(model)
        for pair in itertools.combinations(retailers, 2):
            effect = model["retailer_effects"][pair[1]] - model["retailer_effects"][pair[0]]
            leave_out = {f: pair_effect([r for r in subset if r["family_id"] != f], pair) for f in families}
            draws, disconnected = [], 0
            for _ in range(contract["bootstrap_replicates"]):
                sample = []
                for index, family in enumerate(rng.choice(families, size=len(families), replace=True)):
                    # A repeated family is an independent sampled cluster instance;
                    # variant aliases preserve copies while recomputing 1/n_f.
                    sample.extend({**r, "family_id": f"draw-{index}", "variant_id": f"draw-{index}:" + r["variant_id"]}
                                  for r in subset if r["family_id"] == family)
                value = pair_effect(sample, pair)
                if value is None:
                    disconnected += 1
                else:
                    draws.append(value)
            supported = (len(families) >= contract["minimum_independent_families"]
                         and all(v is not None for v in leave_out.values())
                         and len(draws) >= 20
                         and len(draws) / contract["bootstrap_replicates"] >= contract["minimum_bootstrap_success_fraction"])
            interval = [float(v) for v in np.quantile(draws, [0.025, 0.975])] if supported else None
            direct = next((e for e in graph["direct_links"] if e["retailers"] == list(pair)), None)
            contrasts.append({"reference_retailer": pair[0], "compared_retailer": pair[1],
                              "log_unit_price_contrast": effect, "percent_contrast": 100 * math.expm1(effect),
                              "confidence_interval_log": interval, "uncertainty_available": supported,
                              "support_status": "experimental_supported" if supported else "weak_or_insufficient_family_support",
                              "link": "direct" if direct else "indirect", "component_families": len(families),
                              "direct_families": direct["independent_family_count"] if direct else 0,
                              "matched_variants": len(model["variant_effects"]),
                              "maximum_leave_one_family_out_log_change": max(
                                  (abs(v - effect) for v in leave_out.values() if v is not None), default=None),
                              "leave_one_family_out": leave_out, "bootstrap_disconnections": disconnected,
                              "bootstrap_successes": len(draws)})
            uncertainty.append({"retailers": list(pair), "successful_log_contrasts": draws,
                                "disconnections": disconnected, "leave_one_family_out": leave_out})
    return {"model_id": "matched_retailer", "estimator": "weighted_exact_variant_plus_retailer_fixed_effects",
            "fit_partition": "fitting", "components": models, "graph": graph, "contrasts": contrasts,
            "uncertainty_method": "family_cluster_percentile_bootstrap_95_percent",
            "prediction_intervals_available": False, "new_product_prediction_supported": False}, uncertainty


def fitted_log(row, model):
    for component in model["components"]:
        if row["variant_id"] in component["variant_effects"] and row["retailer"] in component["retailer_effects"]:
            return component["variant_effects"][row["variant_id"]] + component["retailer_effects"][row["retailer"]]
    return None


def diagnostic_metrics(observations, model):
    """In-sample residual diagnostics; these do not measure new-product quality."""
    if not observations:
        return None
    weights = family_weights(observations)
    actual = np.array([target_values(r)[0] for r in observations])
    predicted = np.exp([fitted_log(r, model) for r in observations])
    error = predicted - actual
    mass = np.array([r["predictors"]["quantity.total_edible_weight_g"] for r in observations]) / 100
    ape = np.abs(error) / actual * 100
    order = np.argsort(ape, kind="stable")
    median_index = np.searchsorted(np.cumsum(weights[order]), sum(weights) / 2)
    return {"rows": len(observations), "independent_families": len({r["family_id"] for r in observations}),
            "family_weighted_mae_gbp_per_100g": float(np.average(np.abs(error), weights=weights)),
            "family_weighted_mae_gbp_per_pack": float(np.average(np.abs(error) * mass, weights=weights)),
            "family_weighted_signed_bias_gbp_per_100g": float(np.average(error, weights=weights)),
            "family_weighted_signed_bias_gbp_per_pack": float(np.average(error * mass, weights=weights)),
            "weighted_median_absolute_percentage_error": float(ape[order[median_index]]),
            "listing_weighted_mae_gbp_per_100g": float(np.mean(np.abs(error))),
            "listing_weighted_mae_gbp_per_pack": float(np.mean(np.abs(error) * mass)),
            "listing_weighted_median_absolute_percentage_error": float(np.median(ape)),
            "listing_weighted_signed_bias_gbp_per_100g": float(np.mean(error)),
            "listing_weighted_signed_bias_gbp_per_pack": float(np.mean(error * mass)),
            "support_status": "sparse" if len(set(r["family_id"] for r in observations)) < 5 else "descriptive"}


def evaluation(observations, model):
    report = {"scope": "fitting_partition_residual_diagnostic_only", "overall": diagnostic_metrics(observations, model),
              "calibration": "not_applicable_to_matched_contrasts", "final_test": "no_new_product_prediction_task"}
    fields = {"retailer": lambda r: r["retailer"], "type": lambda r: r["predictors"]["composition.chocolate_type"],
              "brand": lambda r: r["predictors"]["identity.brand"],
              "size": lambda r: "under_100g" if r["predictors"]["quantity.total_edible_weight_g"] < 100 else "100g_or_more",
              "missingness": lambda r: "optional_missing" if any(v is None or v == "unknown" for v in r["predictors"].values()) else "complete"}
    for name, key in fields.items():
        groups = defaultdict(list)
        for row in observations:
            groups[str(key(row))].append(row)
        report[name] = {label: diagnostic_metrics(group, model) for label, group in sorted(groups.items())}
    return report


def verified_candidate_values(candidates, prices):
    """Accept the caller's verification; test actual inputs without editing flags."""
    selected, missing, reasons = [], Counter(), {}
    variants, listings = {}, {}
    for row in candidates:
        oid = row["observation_id"]
        price = prices.get(oid, {})
        failures = []
        for field in ("variant_id", "family_id"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                failures.append("missing_" + field)
        mass = row["predictors"].get("quantity.total_edible_weight_g")
        if type(mass) not in (int, float) or not math.isfinite(mass) or mass <= 0:
            failures.append("missing_positive_edible_weight")
        if not regular_price_basis_supported(price):
            if price.get("regular_price") is None:
                failures.append("missing_regular_price")
            if price.get("tax_basis") != "consumer_tax_included":
                failures.append("unresolved_tax_basis")
            if price.get("currency") != "GBP":
                failures.append("unsupported_currency")
        target = row["target"].get("regular_price_per_100g_gbp")
        logged = row["target"].get("log_regular_price_per_100g_gbp")
        if (type(target) not in (int, float) or not math.isfinite(target) or target <= 0
                or type(logged) not in (int, float) or not math.isfinite(logged)):
            failures.append("missing_regular_unit_price_target")
        for field in ("identity.brand", "identity.retailer", "composition.chocolate_type"):
            value = row["predictors"].get(field)
            if not isinstance(value, str) or not value.strip() or value.lower() == "unknown":
                failures.append("missing_" + field)
        if failures:
            missing.update(failures)
            reasons[oid] = ";".join(failures)
            continue
        if not math.isclose(math.log(target), logged, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelContractError("Verified Gold log target is inconsistent with its regular price")
        for field in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version"):
            if price.get(field) != row.get(field):
                raise ModelContractError("Verified Gold price provenance differs: " + field)
        if (price.get("total_edible_weight_g") != mass
                or not math.isclose(round(price["regular_price"] / mass * 100, 8), target, rel_tol=1e-9, abs_tol=1e-9)):
            raise ModelContractError("Verified Gold target differs from its regular price/edible weight")
        if variants.setdefault(row["variant_id"], row["family_id"]) != row["family_id"]:
            raise ModelContractError("A verified exact variant cannot span families")
        if row["listing_id"] in listings:
            raise ModelContractError("Repeated verified seller observations require occasion selection")
        listings[row["listing_id"]] = row["variant_id"]
        selected.append(row)
    return selected, dict(sorted(missing.items())), reasons


def context_from_gold(observations, prices):
    """Use existing values directly; absent matching/context fields stay absent."""
    contexts = {}
    for row in observations:
        price = prices[row["observation_id"]]
        context = {name: price.get(name) for name in EVIDENCE_FIELDS}
        context.update(edible_weight_g=row["predictors"]["quantity.total_edible_weight_g"],
                       brand=row["predictors"]["identity.brand"],
                       chocolate_type=row["predictors"]["composition.chocolate_type"])
        if all(context[n] is not None for n in EVIDENCE_FIELDS):
            contexts[row["observation_id"]] = context
    return contexts


def current_candidate_values(candidates, prices):
    """Use shared current-price arithmetic, then apply matched-model requirements."""
    derived, preparation = current_price_targets(candidates, list(prices.values()))
    selected, missing, domains, prepared = [], Counter(), {}, {}
    variants, listings = {}, set()
    for row in derived:
        oid = row["observation_id"]
        price = prices[oid]
        failures = []
        value = row["target"]["current_price_per_100g_gbp"]
        if value is None:
            if price.get("currency") != "GBP":
                failures.append("current_price_currency_not_gbp")
            elif type(price.get("displayed_price")) not in (int, float) or not math.isfinite(price["displayed_price"]) or price["displayed_price"] <= 0:
                failures.append("current_price_missing_or_invalid")
            else:
                mass = row["predictors"].get("quantity.total_edible_weight_g")
                observed_mass = price.get("total_edible_weight_g")
                if type(mass) not in (int, float) or not math.isfinite(mass) or mass <= 0:
                    failures.append("edible_weight_missing_or_invalid")
                elif (type(observed_mass) not in (int, float) or not math.isfinite(observed_mass) or observed_mass <= 0
                      or not math.isclose(mass, observed_mass, rel_tol=1e-9, abs_tol=1e-9)):
                    failures.append("price_and_predictor_edible_weight_disagree")
                else:
                    failures.append("current_unit_price_missing_or_invalid")
        for field in ("variant_id", "family_id"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                failures.append("missing_" + field)
        for field in ("identity.brand", "identity.retailer", "composition.chocolate_type"):
            field_value = row["predictors"].get(field)
            if not isinstance(field_value, str) or not field_value.strip() or field_value.lower() == "unknown":
                failures.append("missing_" + field)
        amount = price.get("displayed_price")
        valid_amount = price.get("currency") == "GBP" and type(amount) in (int, float) and math.isfinite(amount) and amount > 0
        row["model_target"] = {"basis": "current-consumer-price-1", "unit_gbp_per_100g": value,
                               "log_unit_gbp_per_100g": row["target"]["log_current_price_per_100g_gbp"],
                               "pack_price_gbp": amount if valid_amount else None,
                               "quantity_source": "candidate.quantity.total_edible_weight_g" if value is not None else None,
                               "promotion_status": price.get("promotion_status"), "tax_basis": price.get("tax_basis")}
        prepared[oid] = row
        if failures:
            missing.update(failures)
            domains[oid] = ";".join(failures)
            continue
        if variants.setdefault(row["variant_id"], row["family_id"]) != row["family_id"]:
            raise ModelContractError("A current-price exact variant cannot span families")
        if row["listing_id"] in listings:
            raise ModelContractError("Repeated current-price seller observations require occasion selection")
        listings.add(row["listing_id"])
        selected.append(row)
    validate_current_price_targets(selected, list(prices.values()))
    return selected, dict(sorted(missing.items())), domains, prepared, preparation


def build_matched_run(gold_root, output, contract_path, review_path=None, group="bar", *, verified_gold_candidates=False):
    source, output = Path(gold_root).resolve(), Path(output).absolute()
    reject_output_links(output)
    if np.__version__ != "2.2.6":
        raise ModelContractError("matched_retailer requires pinned NumPy 2.2.6")
    if source == output.resolve() or source in output.resolve().parents or output.resolve() in source.parents:
        raise ModelContractError("Model output must be separate from Gold")
    contract_path = Path(contract_path)
    contract_bytes = contract_path.read_bytes()
    contract = read_json(contract_bytes)
    validate_contract(contract)
    if group != "bar":
        raise ModelContractError("matched_retailer supports the declared bar cohort only")
    gold_bytes = checked_path(source, "manifest.json", "Gold").read_bytes()
    silver, silver_bytes, inputs = verified_gold(source)
    gold = read_json(gold_bytes)
    base = contract.get("base_reference", {})
    # The draft binds the exact published input contracts, never relabels OLS.
    if contract.get("input_contract_basis") == "verified_gold_snapshot":
        if (contract.get("input_gold_manifest_sha256") != checksum(gold_bytes)
                or contract.get("input_contract_sha256") != {n: checksum(inputs[n]) for n in CONTRACTS}
                or contract.get("input_storage_model_design_version") != read_json(inputs["model-design.json"])["model_design_version"]):
            raise ModelContractError("Working snapshot contract differs from exact Gold manifest or copied contracts")
    else:
        from dataset_contracts import verify_contract_directory
        verify_contract_directory(base, source / "inputs")
        if (not isinstance(base.get("revision"), str) or len(base["revision"]) != 40
                or any(base.get("files", {}).get(n, {}).get("sha256") != checksum(inputs[n]) for n in CONTRACTS)):
            raise ModelContractError("Working contract base differs from copied Gold contracts")
    copied_design = read_json(inputs["model-design.json"])
    current_proxy = is_current_target(contract["target"])
    target_files = {}
    if current_proxy:
        from dataset_contracts import (
            CURRENT_PRICE_REFERENCE,
            load_manifest,
            resolve_current_price_contract_root,
        )
        reference_bytes = CURRENT_PRICE_REFERENCE.read_bytes()
        reference = load_manifest(CURRENT_PRICE_REFERENCE)
        target_root = resolve_current_price_contract_root(offline=True)
        target_design = read_json((target_root / "model-design.json").read_bytes())
        if (contract.get("target_reference") != reference or contract["target"] != target_design["target"]
                or contract.get("target_contract_version") != target_design["model_design_version"]
                or contract.get("current_preparation_version") != "chocolate-current-price-target-1"):
            raise ModelContractError("Current target differs from the verified shared published contract")
        target_files = {"inputs/current-price-contract/" + n: (target_root / n).read_bytes() for n in CONTRACTS}
        target_files["inputs/current-price-contract-reference.json"] = reference_bytes
    if not current_proxy:
        validate_target_policy(copied_design["target"])
    source_eligible, candidates = rows(inputs["model-inputs.jsonl"]), rows(inputs["training-candidates.jsonl"])
    missing_values, missing_domains = {}, {}
    prepared_current, shared_preparation = {}, None
    if current_proxy:
        if not verified_gold_candidates:
            raise ModelContractError("Current-price proxy requires explicit task-verified candidate selection")
        prices = validate_price_targets([], rows(inputs["prices.jsonl"]))
        eligible, missing_values, missing_domains, prepared_current, shared_preparation = current_candidate_values(candidates, prices)
    elif verified_gold_candidates:
        prices = validate_price_targets([], rows(inputs["prices.jsonl"]))
        eligible, missing_values, missing_domains = verified_candidate_values(candidates, prices)
    else:
        eligible = source_eligible
        validate_candidates(eligible, copied_design)
        prices = validate_price_targets(eligible, rows(inputs["prices.jsonl"]))
    files = {"inputs/" + name: data for name, data in inputs.items()}
    files.update(target_files)
    files.update({"inputs/gold-manifest.json": gold_bytes, "inputs/silver-manifest.json": silver_bytes,
                  "inputs/working-contract.json": contract_bytes})
    blockers, reviews = [], {}
    bundle = None
    if review_path is not None:
        review_path = Path(review_path)
        bundle, reviews, evidence_files = reviewed_evidence(review_path)
        if bundle.get("gold_manifest_sha256") != checksum(gold_bytes):
            raise ModelContractError("Match reviews do not bind the verified Gold snapshot")
        files.update(evidence_files)
    elif verified_gold_candidates:
        reviews = context_from_gold(eligible, prices)
        if eligible and not reviews:
            blockers.append("missing_exact_variant_or_comparable_context_values_in_gold")
    else:
        blockers.append("missing_reviewed_exact_variant_context_bundle")
    if not eligible:
        blockers.append("no_complete_matched_model_inputs_in_verified_gold" if verified_gold_candidates
                        else "no_reviewed_eligible_gold_observations")
    if verified_gold_candidates and not eligible:
        blockers.extend(missing_values)
    if contract["price_window"] is None and eligible:
        blockers.append("missing_declared_genuine_price_window")
    elif contract["price_window"] is None and not verified_gold_candidates:
        blockers.append("missing_declared_genuine_price_window")
    if read_json(inputs["quality-report.json"]).get("status") != "complete_snapshot":
        blockers.append("incomplete_silver_source")
    # Assign common partitions on upstream eligible rows, before this diagnostic's
    # stricter matched domain. Missing matching evidence never changes the split.
    split_population = ([r for r in candidates if isinstance(r.get("family_id"), str) and r["family_id"].strip()]
                        if verified_gold_candidates else eligible)
    split = frozen_split(split_population, contract["split_seed"])
    domain = {r["observation_id"]: "readiness_blocked" for r in eligible}
    accepted, fitted_rows, excluded = [], [], {}
    if contract["price_window"] is not None:
        accepted, domain = prepare_matches(eligible, prices, reviews, contract)
        fit_partition = [r for r in accepted if split["assignments"][r["family_id"]] == "fitting"]
        fitted_rows, excluded = contemporaneous(fit_partition, contract["match_hours"])
        domain.update(excluded)
        if len({r["family_id"] for r in fitted_rows}) < 2:
            blockers.append("fewer_than_two_contemporaneous_exact_match_fitting_families")
    model, uncertainty, metrics = None, [], None
    if not blockers:
        try:
            model, uncertainty = fit_matched(fitted_rows, contract)
            metrics = evaluation(fitted_rows, model)
        except ModelContractError as error:
            blockers.append(str(error))
    predictions = []
    fitted_ids = {r["observation_id"] for r in fitted_rows}
    for source_row in candidates if verified_gold_candidates else eligible:
        row = prepared_current.get(source_row["observation_id"], source_row)
        partition = split["assignments"].get(row["family_id"])
        enriched = next((r for r in fitted_rows if r["observation_id"] == row["observation_id"]), None)
        logged = fitted_log(enriched, model) if enriched is not None and model is not None else None
        reason = ("fitted_matched_assortment" if logged is not None else
                  missing_domains.get(row["observation_id"], domain.get(row["observation_id"], "unavailable")))
        if partition in {"calibration", "testing"} and row["observation_id"] not in missing_domains:
            reason = "held_out_family_exact_variant_effect_unavailable"
        unit = math.exp(logged) if logged is not None else None
        predictions.append({"model_id": "matched_retailer", "observation_id": row["observation_id"],
                            "listing_id": row["listing_id"], "family_id": row["family_id"], "variant_id": row["variant_id"],
                            "retailer": row["predictors"]["identity.retailer"], "partition": partition,
                            "in_domain": logged is not None, "domain_reason": reason,
                            "fitting_match": row["observation_id"] in fitted_ids,
                            "observed_gbp_per_100g": target_values(row)[0],
                            "target_basis": contract["target"]["name"],
                            "predicted_log_gbp_per_100g": logged, "predicted_gbp_per_100g": unit,
                            "predicted_gbp_per_pack": unit * row["predictors"]["quantity.total_edible_weight_g"] / 100 if unit else None})
    implementation = {n: checksum((ROOT / n).read_bytes()) for n in IMPLEMENTATION}
    identity = {"model_id": "matched_retailer", "run_format": "chocolate-matched-run-1",
                "gold_manifest_sha256": checksum(gold_bytes), "gold_dataset_version": gold["dataset_version"],
                "silver_manifest_sha256": checksum(silver_bytes), "working_contract_sha256": checksum(contract_bytes),
                "copied_contract_sha256": silver["contract_sha256"],
                "experiment_sha256": checksum(json_bytes({"contract": contract, "split": split})),
                "common_policy_sha256": checksum(json_bytes(COMMON_POLICY)),
                "match_review_sha256": checksum(files["inputs/match-review.json"]) if bundle else None,
                "implementation_sha256": implementation, "python_version": platform.python_version(),
                "numpy_version": np.__version__, "pyarrow_version": gold["pyarrow_version"],
                "seeds": {"split": contract["split_seed"], "bootstrap": contract["bootstrap_seed"]}}
    identity["gold_verification_basis"] = "explicit_task_authorized_candidates" if verified_gold_candidates else "stored_eligibility"
    identity["eligibility_provenance"] = gold.get("eligibility_provenance")
    identity["parent_gold_dataset_version"] = gold.get("parent_gold_dataset_version")
    identity["input_storage_model_design_version"] = copied_design["model_design_version"]
    identity["price_target_policy"] = target_policy(contract["target"])
    identity["target_contract_reference"] = contract.get("target_reference")
    identity["target_contract_sha256"] = {n: checksum(b) for n, b in target_files.items()}
    identity["experiment_sha256"] = checksum(json_bytes({"contract": contract, "split": split,
                                                       "gold_verification_basis": identity["gold_verification_basis"]}))
    run_id = "matched-run-" + checksum(json_bytes(identity))[:24]
    report = {"model_id": "matched_retailer", "run_id": run_id,
              "status": "experimental_fitted" if model else "readiness_blocked",
              "implemented": True, "real_data_fitted": model is not None and not (bundle or {}).get("synthetic_fixture", False),
              "fixture_fitted": model is not None and (bundle or {}).get("synthetic_fixture") is True,
              "calibrated": False, "release_ready": False, "regression_fitted": False,
              "blockers": blockers, "gold_dataset_version": gold["dataset_version"],
              "gold_verification_basis": identity["gold_verification_basis"],
              "eligibility_provenance": identity["eligibility_provenance"],
              "price_target_policy": identity["price_target_policy"],
              "missing_required_value_counts": missing_values,
              "counts": {"candidates": len(candidates), "eligible": len(source_eligible),
                         "complete_required_inputs": len(eligible), "evidence_ready": len(accepted),
                         "source_eligible": len(source_eligible), "task_verified_candidates": len(candidates) if verified_gold_candidates else 0,
                         "fitting_matched_rows": len(fitted_rows), "fitting_matched_families": len({r["family_id"] for r in fitted_rows})},
              "exclusion_counts": dict(sorted(Counter(reason for r in candidates for reason in r["exclusion_reasons"]).items())),
              "match_exclusion_counts": dict(Counter(domain.values())),
              "limitations": ["Contrasts describe only the matched assortment; no new-product, future-price or causal interpretation.",
                              "No regression conformal interval applies to this diagnostic.",
                              "Common regression feature identification, comparator release gates and champion selection remain pending.",
                              "Reviewed source pointers preserve evidence; source semantics still require upstream reviewer judgment.",
                              "Working contract requires dataset publication review and portable alignment before production adoption."]}
    if current_proxy:
        report["counts"]["positive_current_pack_prices"] = sum(r["model_target"]["pack_price_gbp"] is not None for r in prepared_current.values())
        report["counts"]["normalized_current_targets"] = sum(target_values(r)[0] is not None for r in prepared_current.values())
        report["limitations"].append(CURRENT_TARGET["assumption"])
        report["limitations"].extend(shared_preparation["limitations"])
        report["shared_current_price_preparation"] = shared_preparation
        report["target_contract_reference"] = identity["target_contract_reference"]
        files["current-price-preparation.json"] = json_bytes(shared_preparation)
        files["prepared-current-inputs.jsonl"] = b"".join(json_bytes(r).replace(b"\n", b" ") + b"\n" for r in prepared_current.values())
    command = ["uv", "run", "python", "scripts/train_chocolate_model.py", "--model-id", "matched_retailer",
               "--gold-root", str(source), "--working-contract", str(contract_path.absolute()),
               "--group", "bar", "--output", str(output.parent)]
    if review_path is not None:
        command.extend(["--match-review", str(review_path.absolute())])
    if verified_gold_candidates:
        command.append("--verified-gold-candidates")
    files.update({"experiment.json": json_bytes({**identity, "contract": contract, "split": split}),
                  "split.json": json_bytes(split), "report.json": json_bytes(report),
                  "preprocessing.json": json_bytes({"transform": contract["target"]["name"],
                                                      "imputation": None, "feature_selection": None,
                                                      "fixed_effects": ["reviewed_exact_variant", "retailer"],
                                                      "category_order": "lexicographic within fitting component",
                                                      "retailer_reference": "lexicographically first per component",
                                                      "regularization": None, "tuning": None}),
                  "evaluation.json": json_bytes(metrics), "uncertainty.json": json_bytes(uncertainty),
                  "support-rules.json": json_bytes({"minimum_independent_families": contract["minimum_independent_families"],
                                                    "match_hours": 48, "scope": "connected_matched_assortment",
                                                    "cohort": COMMON_POLICY["cohort"], "retailers": contract["retailers"],
                                                    "required_review_fields": list(EVIDENCE_FIELDS),
                                                    "price_policy": target_policy(contract["target"]),
                                                    "prediction_intervals_available": False}),
                  "predictions.jsonl": b"".join(json_bytes(p).replace(b"\n", b" ") + b"\n" for p in predictions),
                  "reproduce.json": json_bytes({"argv": command})})
    if model is not None:
        files["model.json"] = json_bytes(model)
    files["manifest.json"] = json_bytes({**identity, "run_id": run_id,
                                         "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}})
    if ((source / "manifest.json").read_bytes() != gold_bytes or verified_gold(source)[1] != silver_bytes
            or contract_path.read_bytes() != contract_bytes
            or {n: checksum((ROOT / n).read_bytes()) for n in IMPLEMENTATION} != implementation):
        raise ModelContractError("Inputs or implementation changed during matched run")
    if review_path is not None and reviewed_evidence(review_path)[2] != evidence_files:
        raise ModelContractError("Matching evidence changed during run")
    if current_proxy:
        resolve_current_price_contract_root(offline=True)
        if (CURRENT_PRICE_REFERENCE.read_bytes() != reference_bytes
                or any((target_root / n).read_bytes() != target_files["inputs/current-price-contract/" + n] for n in CONTRACTS)):
            raise ModelContractError("Published current-price contract changed during run")
    return report, write_run(output, run_id, files)


def main():
    parser = argparse.ArgumentParser(description="Prepare an unpublished local matched-retailer contract")
    parser.add_argument("--prepare-working-contract", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, help="Bind an explicit local input contract to this exact verified Gold snapshot")
    parser.add_argument("--current-price-proxy", action="store_true", help="Use task-authorized collected current/displayed GBP prices")
    args = parser.parse_args()
    destination = args.prepare_working_contract
    if destination.exists():
        raise ModelContractError("Refusing to replace an existing working contract")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(json_bytes(working_contract(args.gold_root, current_price_proxy=args.current_price_proxy)))
    print(destination.absolute())
    return 0


if __name__ == "__main__":
    sys.exit(main())
