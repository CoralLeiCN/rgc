"""Deterministic synthetic evidence for numerical checks; never real training data."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from chocolate_gold import build_gold_dataset
from chocolate_hedonic import (
    BASIS,
    BRAND,
    CLAIMS,
    COCOA,
    COHORT,
    COHORT_ID,
    NUTS,
    PACK_COUNT,
    RECIPE,
    RETAILER,
    TYPE,
    WEIGHT,
)
from dataset_contracts import resolve_contract_root
from train_chocolate_model import CONTRACTS, checksum, json_bytes


def synthetic_rows(families=600):
    rng = np.random.default_rng(9821)
    result = []
    for i in range(families):
        chocolate_type = ("dark", "milk", "white")[i % 3]
        recipe = ("plain", "inclusion", "filled")[(i // 3) % 3]
        nuts = ("present", "absent")[(i // 9) % 2]
        mass = (60, 100, 150, 200)[int(rng.integers(4))]
        brand = "Synthetic Brand " + str(int(rng.integers(3)))
        noise = float(rng.normal(0, 0.06))
        for retailer in ("Ocado", "Waitrose"):
            p = {WEIGHT: mass, TYPE: chocolate_type, RECIPE: recipe, NUTS: nuts,
                 RETAILER: retailer, BRAND: brand,
                 COHORT: COHORT_ID, PACK_COUNT: 1,
                 "identity.product_group": "bar", "identity.source_role": "retail",
                 COCOA: None if i % 5 == 0 else float(rng.integers(25, 80)),
                 BASIS: "whole_product", **{c: "unknown" for c in CLAIMS}}
            log_price = (1.6 - 0.18 * math.log(mass) + 0.17 * (chocolate_type == "dark")
                         + 0.08 * (chocolate_type == "white") + 0.13 * (recipe == "filled")
                         + 0.09 * (recipe == "inclusion") + 0.10 * (nuts == "present")
                         + 0.12 * (retailer == "Waitrose") + noise)
            identifier = f"synthetic-{i:05d}-{retailer}"
            unit_price = round(math.exp(log_price), 8)
            result.append({"observation_id": identifier, "listing_id": "listing-" + identifier,
                           "variant_id": f"synthetic-variant-{i}", "family_id": f"synthetic-family-{i}",
                           "comparable_group": "bar", "source_role": "retail", "model_eligible": True,
                           "exclusion_reasons": [], "predictors": p,
                           "target": {"regular_price_per_100g_gbp": unit_price,
                                      "log_regular_price_per_100g_gbp": math.log(unit_price)},
                           "dataset_version": "silver-synthetic-hedonic", "source_dataset_version": "raw-synthetic-hedonic",
                           "schema_version": "chocolate-schema-1"})
    return result


def fixture_gold(root, values):
    """Construct explicitly synthetic Silver and verified Parquet Gold."""
    silver = root / "silver"
    silver.mkdir(parents=True)
    files = {n: (resolve_contract_root(offline=True) / n).read_bytes() for n in CONTRACTS}
    design = json.loads(files["model-design.json"])
    design["model_design_version"] = "chocolate-supermarket-fixture-design-1"
    p = design["predictors"]
    for name in (RECIPE, COHORT, BASIS):
        p[name] = {"type": "categorical", "reference": "training_mode", "required": True, "missing_policy": "reject"}
    p[PACK_COUNT] = {"type": "numeric", "required": True, "missing_policy": "reject"}
    files["model-design.json"] = json_bytes(design)
    files["quality-report.json"] = json_bytes({"dataset_version": "silver-synthetic-hedonic", "status": "complete_snapshot",
                                             "fixture": True, "counts": {"training_candidates": len(values), "eligible_model_inputs": len(values)}})
    content = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in values)
    files["training-candidates.jsonl"] = content
    files["model-inputs.jsonl"] = content
    observations = []
    for row in values:
        price = {k: row[k] for k in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")}
        price.update(currency="GBP", tax_basis="consumer_tax_included", available=True,
                     regular_price=row["target"]["regular_price_per_100g_gbp"] * row["predictors"][WEIGHT] / 100,
                     total_edible_weight_g=row["predictors"][WEIGHT], review_status="reviewed", quantity_status="reviewed",
                     model_eligible=True, observed_at="2026-10-03T12:00:00+01:00", fixture=True)
        observations.append(price)
    files["prices.jsonl"] = b"".join(json.dumps(r).encode() + b"\n" for r in observations)
    manifest = {"manifest_format_version": "chocolate-silver-manifest-1", "dataset_version": "silver-synthetic-hedonic",
                "source_dataset_version": "raw-synthetic-hedonic", "schema_version": "chocolate-schema-1", "fixture": True,
                "contract_sha256": {n: checksum(files[n]) for n in CONTRACTS},
                "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}}
    for name, data in files.items():
        (silver / name).write_bytes(data)
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    return build_gold_dataset(silver, root / "gold")[1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--families", type=int, default=600)
    args = parser.parse_args()
    print(fixture_gold(args.output, synthetic_rows(args.families)))
