#!/usr/bin/env python3
"""Prepare an unpublished dataset-owned contract migration for baseline research."""

import argparse
from copy import deepcopy
from pathlib import Path

from dataset_contracts import resolve_contract_root
from train_chocolate_model import CONTRACTS, checksum, json_bytes, read_json


def experiment_policy(*, current_price_proxy=False):
    policy = {"version": "chocolate-comparison-experiment-1",
            "cohort": "uk_standard_single_pack_supermarket_chocolate_bars",
            "population_review": "new design scope review excludes gifts, novelty and non-eating bars",
            "retailers": ["Ocado", "Waitrose"], "split_seed": 1729,
            "fractions": [0.6, 0.2, 0.2], "within_brand_quotas": False,
            "price_window_rule": "explicit inclusive UTC bounds; observation time only",
            "weighting": "1/n_f within each partition; recompute within evaluation strata",
            "required_context": ["brand", "variant_id", "family_id", "single_pack", "reviewed_population"],
            "baseline_predictors": ["identity.retailer", "composition.chocolate_type"],
            "common_regression_feature_policy": {
                "version": "chocolate-comparison-admissible-features-1",
                "core": ["log_edible_mass", "chocolate_type", "recipe", "broad_inclusion_classes", "retailer"],
                "optional": ["cocoa_percentage_and_basis", "named_claims"],
                "missingness": "explicit unknown optional categories; fitting-only cocoa median and indicator",
                "selection": "fitting-only grouped validation and known-brand identifiability",
                "exclude": ["identifiers", "names", "prices", "price_derived_fields"],
                "admissibility_status": "pending_regression_fitting_only_identification"},
            "baseline_tuning": "none", "calibration": "not_required_for_baseline",
            "release_gates": "pending_common_row_comparators_and_review"}
    if current_price_proxy:
        policy["version"] = "chocolate-comparison-experiment-2"
        policy["price_window_rule"] = "all observations in immutable snapshot; optional inclusive UTC bounds"
    return policy


def working_design(original, *, current_price_proxy=False):
    from chocolate_retailer_median import (
        CONTEXT,
        DESIGN_VERSION,
        PREDICTORS,
    )

    design = deepcopy(original)
    design["model_design_version"] = DESIGN_VERSION
    design["status"] = "unpublished_experimental_working_contract" if current_price_proxy else "unpublished_working_contract_fixture_validation_only"
    design["comparison_experiment"] = experiment_policy(current_price_proxy=current_price_proxy)
    design["model"] = {"estimator": "family_weighted_retailer_type_median",
                       "predictors": list(PREDICTORS), "context_only_predictors": list(CONTEXT)}
    design["training"] = {"estimator": "family_weighted_retailer_type_median", "size_effect": False,
                          "median_rule": "lower_weighted_median", "split_seed": 1729}
    categorical = {"identity.retailer": ["Ocado", "Waitrose"],
                   "composition.chocolate_type": original["predictors"]["composition.chocolate_type"]["allowed_values"],
                   "identity.source_role": ["retail"], "identity.product_group": ["bar"],
                   "identity.boundary_status": ["in_scope"], "identity.brand": None}
    definitions = {}
    for name, allowed in categorical.items():
        definitions[name] = {"type": "categorical", "required": True, "missing_policy": "reject",
                             "reference": "training_mode"}
        if allowed:
            definitions[name]["allowed_values"] = allowed
    definitions["quantity.total_edible_weight_g"] = {"type": "numeric", "required": True,
                                                    "missing_policy": "reject", "minimum": 0.01}
    definitions["quantity.pack_count"] = {"type": "numeric", "required": True,
                                          "missing_policy": "reject", "minimum": 1, "maximum": 1}
    design["predictors"] = definitions
    design["default_predictor_subset"] = list(PREDICTORS)
    if current_price_proxy:
        from chocolate_current_price import current_price_design
        from chocolate_retailer_target import current_contract_inputs
        design = current_price_design(design, current_contract_inputs()[0])
        design["purpose"] = "Estimate family-balanced retailer/type medians of collected current GBP per 100 g."
        requirements = {
            "identity": "Retain exact variant and family IDs for whole-family splits without merging seller listings.",
            "classification": "Require stored bar, in_scope, retail, Ocado/Waitrose and single-pack values.",
            "quantity": "Require actual positive edible pack weight matching the price observation; no quantity imputation.",
            "source_time": "Use every observation in the immutable snapshot unless explicit UTC bounds are supplied; those bounds require source observation time.",
            "availability": "Preserve source availability as metadata without excluding current displayed prices.",
            "feature_review": "Accept Gold eligibility provenance and validate actual predictor values against the model domain.",
        }
        for gate in design.get("eligibility_gates", []):
            if gate["id"] in requirements:
                gate["requirement"] = requirements[gate["id"]]
    return design


def prepare(output, *, current_price_proxy=False):
    root = resolve_contract_root(offline=True)
    files = {name: (root / name).read_bytes() for name in CONTRACTS}
    files["model-design.json"] = json_bytes(working_design(read_json(files["model-design.json"]),
                                                        current_price_proxy=current_price_proxy))
    files["working-contract.json"] = json_bytes({"status": "unpublished", "source": str(root),
        "source_contract_sha256": {name: checksum((root / name).read_bytes()) for name in CONTRACTS},
        "working_contract_sha256": {name: checksum(data) for name, data in files.items()},
        "review_required_before_hugging_face_contract_commit": True,
        "portable_profile": "existing prepare-only contract preserved; comparison migration not yet published"})
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = output / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError("working contract directory already contains different bytes")
        path.write_bytes(data)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--current-price-proxy", action="store_true")
    args = parser.parse_args()
    print(prepare(args.output, current_price_proxy=args.current_price_proxy))


if __name__ == "__main__":
    main()
