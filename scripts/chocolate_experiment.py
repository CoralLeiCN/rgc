"""Frozen supermarket experiment preparation shared by independent estimators.

The explicit working contract is unpublished. Missing evidence fields block
readiness; this module never manufactures cohort membership or eligibility.
"""

import hashlib
import math
import random
from collections import Counter, defaultdict
from copy import deepcopy

from chocolate_model import (
    PRICE_TARGET_POLICY,
    ModelContractError,
    _validate_identity,
    validate_candidates,
)
from train_chocolate_model import checksum, json_bytes

SEED = 1729
POLICY_VERSION = "chocolate-supermarket-features-1-working"
MASS = "quantity.total_edible_weight_g"
BRAND = "identity.brand"
RETAILER = "identity.retailer"
TYPE = "composition.chocolate_type"
RECIPE = "composition.recipe_class"
INCLUSION = "composition.inclusion_class"
COCOA = "composition.cocoa_percentage"
BASIS = "composition.cocoa_basis"
CLAIMS = ("dietary.vegan_claim", "dietary.dairy_free_claim", "certifications.organic_claim",
          "certifications.fairtrade_claim", "origin.single_origin_claim")
CORE = (MASS, TYPE, RECIPE, INCLUSION, RETAILER, BRAND)
OPTIONAL = (BASIS, COCOA, *CLAIMS)
POPULATION = "standard_single_pack_supermarket_chocolate_bar"


def working_contract():
    """Generate an ignored release payload, keeping Git's published pins intact."""
    return {
        "contract_version": "chocolate-supermarket-experiment-1-working",
        "publication_status": "unpublished_working_contract",
        "feature_policy_version": POLICY_VERSION,
        "population": POPULATION,
        "retailers": ["Ocado", "Waitrose"],
        "types": ["dark", "milk", "white"],
        "target": {**PRICE_TARGET_POLICY, "name": "log_regular_gbp_per_100g", "currency": "GBP",
                   "unit": "GBP_per_100g", "quantity_attribute": MASS, "base_quantity": 100},
        "core_features": list(CORE), "optional_features": list(OPTIONAL),
        "required_evidence_fields": ["study.population", "quantity.pack_count", *CORE, *OPTIONAL],
        "required_regular_price_context": {"regular_price_membership_basis": "public_non_member",
                                           "regular_price_promotion_basis": "non_promotional",
                                           "regular_price_quantity_basis": "single_pack",
                                           "channel": "online", "price_scope": "national_online"},
        "categorical_missingness": "explicit_unknown_optional_categories_only",
        "numeric_missingness": "fitting_type_basis_median_then_fitting_global_median_with_indicator",
        "split": {"seed": SEED, "fractions": [0.6, 0.2, 0.2],
                  "algorithm": "sort_by_sha256_seed_colon_family_then_id; rounded_20_percent_calibration_and_test; remainder_fitting",
                  "brand_quotas": False},
        "validation_folds": 3, "minimum_support_families": 3,
        "minimum_leaf_families": 3,
        "representative_selection": "uniform_from_sorted_observation_ids_using_random_Random_sha256_seed_retailer_family",
        "conformal": {"coverage": 0.9, "selection_seed": SEED},
        "identification": "reference_dummies_and_log_size_full_rank_core; sequential_optional_rank_increment; constants_omitted",
        "release": {"champion_selection": "pending_comparators", "baseline_relative_gate": "pending_comparators"},
        "upstream_requirements": "New evidence fields require aligned original and portable schema/mapping/validator/design/recipe migration before publication and regenerated eligible Gold. Existing OLS contracts remain immutable.",
    }


def validate_working_contract(contract):
    # A new policy needs its own version and implementation, not free-form overrides.
    if contract != working_contract():
        raise ModelContractError("unsupported working experiment contract")
    return checksum(json_bytes(contract))


def rank_key(family, seed=SEED):
    return hashlib.sha256(f"{seed}:{family}".encode()).hexdigest(), family


def family_weights(rows):
    counts = Counter(row["family_id"] for row in rows)
    return [1.0 / counts[row["family_id"]] for row in rows]


def partition(rows, seed=SEED):
    families = sorted({row["family_id"] for row in rows}, key=lambda f: rank_key(f, seed))
    if len(families) < 5:
        raise ModelContractError("at least five reviewed families are required for three partitions")
    count = max(1, int(len(families) * 0.2 + 0.5))
    assignment = {f: ("calibration" if i < count else "test" if i < 2 * count else "fitting")
                  for i, f in enumerate(families)}
    return {"seed": seed, "algorithm": working_contract()["split"]["algorithm"],
            "family_assignments": dict(sorted(assignment.items())), "brand_quotas": False,
            "observation_assignments": {r["observation_id"]: assignment[r["family_id"]]
                                        for r in sorted(rows, key=lambda r: r["observation_id"])}}


def folds(rows, count=3):
    families = sorted({r["family_id"] for r in rows}, key=rank_key)
    if len(families) < count * 2:
        raise ModelContractError("insufficient fitting families for grouped validation")
    assignment = {f: i % count for i, f in enumerate(families)}
    return [([r for r in rows if assignment[r["family_id"]] != i],
             [r for r in rows if assignment[r["family_id"]] == i]) for i in range(count)], assignment


def validate_population(rows, contract):
    validate_working_contract(contract)
    definitions = {}
    for name in (MASS, BRAND, TYPE, RETAILER):
        definitions[name] = {"type": "numeric" if name == MASS else "categorical",
                             "required": True, "missing_policy": "reject", "reference": "training_mode"}
        if name == MASS:
            definitions[name].update(transform="log", minimum=0.01)
    validated = validate_candidates(rows, {"target": contract["target"], "predictors": definitions})
    listings = set()
    for row in validated:
        p = row["predictors"]
        missing = set(contract["required_evidence_fields"]) - set(p)
        if missing:
            raise ModelContractError("missing shared evidence fields: " + ", ".join(sorted(missing)))
        if (row["source_role"] != "retail" or row["comparable_group"] != "bar"
                or p["study.population"] != POPULATION or type(p["quantity.pack_count"]) not in (int, float)
                or p["quantity.pack_count"] != 1 or p[RETAILER] not in contract["retailers"]
                or p[TYPE] not in contract["types"]):
            raise ModelContractError("row outside declared single-pack supermarket population")
        if row["listing_id"] in listings:
            raise ModelContractError("repeated seller listing requires upstream observation selection")
        listings.add(row["listing_id"])
        if p[RECIPE] not in {"plain", "inclusion", "filled"}:
            raise ModelContractError("recipe class requires reviewed plain/inclusion/filled evidence")
        if p[INCLUSION] not in {"none", "nut", "fruit", "biscuit_cereal", "other", "mixed", "unknown"}:
            raise ModelContractError("invalid reviewed broad inclusion class")
        if p[BASIS] not in {"whole_product_exact", "chocolate_portion_exact", "unknown"}:
            raise ModelContractError("unsupported cocoa evidence basis")
        if p[COCOA] is not None:
            if type(p[COCOA]) not in (float, int) or not math.isfinite(p[COCOA]) or not 0 <= p[COCOA] <= 100:
                raise ModelContractError("invalid cocoa percentage")
            if p[BASIS] == "unknown":
                raise ModelContractError("numeric cocoa requires a supported evidence basis")
        for name in CLAIMS:
            if p[name] not in {"present", "explicitly_absent", "unknown"}:
                raise ModelContractError(name + " requires explicit reviewed missingness")
    return validated


def fit_preprocessing(rows, enriched=False):
    import numpy as np

    features = list(CORE) + (list(OPTIONAL) if enriched else [])
    state = {"feature_policy_version": POLICY_VERSION, "enriched": enriched, "features": features,
             "category_maps": {}, "ranges": {}, "cocoa_medians": {},
             "training_observation_ids": sorted(r["observation_id"] for r in rows),
             "support": {}, "context_support": {}, "omitted_optional_terms": {}}
    if not rows:
        raise ModelContractError("no fitting rows")
    for name in features:
        if name in (MASS, COCOA):
            values = [r["predictors"][name] for r in rows if r["predictors"][name] is not None]
            if values:
                state["ranges"][name] = [min(values), max(values)]
            if name == COCOA:
                if not values:
                    raise ModelContractError("no fitting cocoa values for imputation")
                state["cocoa_global_median"] = float(np.median(values))
                groups = defaultdict(list)
                for r in rows:
                    p = r["predictors"]
                    if p[COCOA] is not None:
                        groups[p[TYPE] + "|" + p[BASIS]].append(p[COCOA])
                state["cocoa_medians"] = {g: float(np.median(v)) for g, v in sorted(groups.items())}
        else:
            levels = sorted({r["predictors"][name] for r in rows})
            state["category_maps"][name] = {level: i for i, level in enumerate(levels)}
            state["support"][name] = {level: len({r["family_id"] for r in rows if r["predictors"][name] == level})
                                      for level in levels}
    for r in rows:
        p = r["predictors"]
        key = json_bytes([p[BRAND], p[RETAILER], p[TYPE]]).decode()
        state["context_support"].setdefault(key, set()).add(r["family_id"])
    state["context_support"] = {k: len(v) for k, v in sorted(state["context_support"].items())}
    # Check the shared known-brand linear identification without fitting a comparator.
    accepted, columns = [], [np.ones(len(rows))]
    ranks = []
    for name in features:
        if name in OPTIONAL and name in state["support"] and min(state["support"][name].values()) < 3:
            state["omitted_optional_terms"][name] = "fewer_than_three_fitting_families_for_category"
            continue
        if name == COCOA and BASIS in state["omitted_optional_terms"]:
            state["omitted_optional_terms"][name] = "cocoa_basis_not_admissible"
            continue
        if name == MASS:
            proposed = [np.array([math.log(r["predictors"][name]) for r in rows])]
        elif name == COCOA:
            proposed = [np.array([cocoa_value(r["predictors"], state) for r in rows]),
                        np.array([float(r["predictors"][name] is None) for r in rows])]
        else:
            levels = list(state["category_maps"][name])
            proposed = [np.array([float(r["predictors"][name] == level) for r in rows]) for level in levels[1:]]
        proposed = [v for v in proposed if float(np.max(v)) != float(np.min(v))]
        before = int(np.linalg.matrix_rank(np.column_stack(columns)))
        after = int(np.linalg.matrix_rank(np.column_stack(columns + proposed)))
        if after != before + len(proposed):
            if name in CORE:
                raise ModelContractError("shared known-brand core design is aliased: " + name)
            state["omitted_optional_terms"][name] = "aliased_in_fitting"
        else:
            columns.extend(proposed)
            accepted.append(name)
        ranks.append({"feature": name, "rank_before": before, "rank_after": after})
    state["features"] = accepted
    state["columns"] = [n for name in accepted for n in ([name, name + "__missing"] if name == COCOA else [name])]
    state["categorical_indices"] = [i for i, n in enumerate(state["columns"]) if n in state["category_maps"]]
    state["identification"] = {"checks": ranks, "rank": len(columns), "observations": len(rows),
                               "comparator_fitted": False}
    return state


def cocoa_value(p, state):
    return p[COCOA] if p[COCOA] is not None else state["cocoa_medians"].get(
        p[TYPE] + "|" + p[BASIS], state["cocoa_global_median"])


def encode(p, state):
    """Support checks precede native category routing; accepts prediction inputs only."""
    if not isinstance(p, dict):
        raise ModelContractError("predictors must be an object")
    if p.get("study.population") != POPULATION or type(p.get("quantity.pack_count")) not in (float, int) or p["quantity.pack_count"] != 1:
        raise ModelContractError("prediction outside declared single-pack population")
    minimum = working_contract()["minimum_support_families"]
    for name in (BRAND, RETAILER, TYPE):
        if not isinstance(p.get(name), str) or state["support"][name].get(p.get(name), 0) < minimum:
            raise ModelContractError("unsupported or insufficiently supported " + name)
    context = json_bytes([p[BRAND], p[RETAILER], p[TYPE]]).decode()
    if state["context_support"].get(context, 0) < minimum:
        raise ModelContractError("unsupported brand/retailer/type context")
    mass = p.get(MASS)
    if type(mass) not in (float, int) or not math.isfinite(mass) or not state["ranges"][MASS][0] <= mass <= state["ranges"][MASS][1] or mass <= 0:
        raise ModelContractError("edible weight outside fitting support")
    values = []
    for name in state["features"]:
        if name not in p:
            raise ModelContractError("missing input " + name)
        if name == MASS:
            values.append(math.log(mass))
        elif name == COCOA:
            value = p[name]
            if value is not None and (type(value) not in (float, int) or not math.isfinite(value)
                                      or not state["ranges"][name][0] <= value <= state["ranges"][name][1]):
                raise ModelContractError("cocoa outside fitting support")
            if value is not None and p.get(BASIS) == "unknown":
                raise ModelContractError("numeric cocoa requires evidence basis")
            values.extend([cocoa_value(p, state), float(value is None)])
        else:
            if not isinstance(p[name], str) or p[name] not in state["category_maps"][name]:
                raise ModelContractError("unseen feature category " + name)
            values.append(state["category_maps"][name][p[name]])
    return values


def representatives(rows, seed=SEED):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["predictors"][RETAILER], r["family_id"])].append(r)
    selected = []
    for (retailer, family), members in sorted(groups.items()):
        identities = sorted(members, key=lambda r: r["observation_id"])
        group_seed = int(hashlib.sha256(json_bytes([seed, retailer, family])).hexdigest(), 16)
        selected.append(random.Random(group_seed).choice(identities))
    return deepcopy(selected)


SPLIT_SEED = 1729
SPLIT_ALGORITHM = "sha256_json_seed_family_rank_round_60_20_remainder_v1"


def freeze_partitions(rows, seed=SPLIT_SEED):
    """Rank whole families without examining outcomes, brands, or row counts."""
    from train_chocolate_model import json_bytes

    rows = list(rows)
    _validate_identity(rows)
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ModelContractError("split seed must be an unsigned 32-bit integer")
    families = sorted({row["family_id"] for row in rows}, key=lambda family: (
        hashlib.sha256(json_bytes([seed, family])).hexdigest(), family))
    if len(families) < 3:
        raise ModelContractError("three partitions require at least three reviewed families")
    fitting = max(1, min(len(families) - 2, int(len(families) * 0.6 + 0.5)))
    calibration = max(1, min(len(families) - fitting - 1, int(len(families) * 0.2 + 0.5)))
    assignments = {family: ("fitting" if i < fitting else
                           "calibration" if i < fitting + calibration else "final_testing")
                   for i, family in enumerate(families)}
    partitions = {name: sorted((row for row in rows if assignments[row["family_id"]] == name),
                              key=lambda row: row["observation_id"])
                  for name in ("fitting", "calibration", "final_testing")}
    listings = {}
    for row in rows:
        partition = assignments[row["family_id"]]
        if listings.setdefault(row["listing_id"], partition) != partition:
            raise ModelContractError("seller listing spans family partitions")
    return partitions, {"algorithm": SPLIT_ALGORITHM, "seed": seed,
                        "requested_fractions": [0.6, 0.2, 0.2],
                        "within_brand_quotas": False, "family_assignments": assignments,
                        "ranked_families": families,
                        "observations": {key: len(value) for key, value in partitions.items()}}
