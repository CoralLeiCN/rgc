"""Generate synthetic, explicitly labeled evidence for estimator acceptance checks."""

import argparse
import math
from pathlib import Path

from chocolate_experiment import (
    BASIS,
    BRAND,
    CLAIMS,
    COCOA,
    INCLUSION,
    MASS,
    POPULATION,
    RECIPE,
    RETAILER,
    TYPE,
    working_contract,
)
from chocolate_gold import CONTRACTS, build_gold_dataset, row_bytes
from dataset_contracts import resolve_contract_root
from train_chocolate_model import checksum, json_bytes, read_json


def fixture_rows(count=120):
    rows = []
    for i in range(count):
        for brand_index, brand in enumerate(("Fixture Brand A", "Fixture Brand B")):
            for retailer_index, retailer in enumerate(("Ocado", "Waitrose")):
                for type_index, chocolate_type in enumerate(("milk", "dark", "white")):
                    j = brand_index * 6 + retailer_index * 3 + type_index
                    identifier = f"fixture-{i:04d}-{j}"
                    weight = float(50 + (i % 7) * 10 + brand_index * 3 + type_index)
                    cocoa = float(40 + (i % 11) * 2 + type_index * 4)
                    p = {"study.population": POPULATION, "quantity.pack_count": 1.0, MASS: weight,
                         BRAND: brand, RETAILER: retailer, TYPE: chocolate_type,
                         RECIPE: ("plain", "inclusion", "filled")[i % 3],
                         INCLUSION: ("none", "nut", "fruit", "other")[(i // 3) % 4],
                         BASIS: "whole_product_exact", COCOA: None if i % 5 == 0 else cocoa,
                         **{name: ("present", "explicitly_absent", "unknown")[(i // (k + 2)) % 3]
                            for k, name in enumerate(CLAIMS)}}
                    logged = 1.0 + 0.5 * brand_index + 0.1 * retailer_index + 0.002 * cocoa - 0.1 * math.log(weight) + 0.03 * (i % 3) + 0.008 * math.sin(i + j)
                    rows.append({"observation_id": identifier, "listing_id": "seller-" + identifier,
                                 "variant_id": f"variant-{i}-{brand_index}-{type_index}", "family_id": f"family-{i}-{brand_index}",
                                 "comparable_group": "bar", "source_role": "retail", "model_eligible": True,
                                 "exclusion_reasons": [], "predictors": p,
                                 "target": {"regular_price_per_100g_gbp": round(math.exp(logged), 8),
                                            "log_regular_price_per_100g_gbp": math.log(round(math.exp(logged), 8))},
                                 "dataset_version": "silver-fixture-lightgbm-4",
                                 "source_dataset_version": "raw-fixture-lightgbm-4", "schema_version": "chocolate-schema-1"})
    return rows


def build_fixture(root, count=120):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    silver = root / "silver"
    silver.mkdir(exist_ok=True)
    records = fixture_rows(count)
    files = {n: (resolve_contract_root(offline=True) / n).read_bytes() for n in CONTRACTS}
    design = read_json(files["model-design.json"])
    design.update(model_design_version="chocolate-lightgbm-fixture-design-1", target=working_contract()["target"],
                  publication_status="synthetic_fixture_only")
    design["predictors"] = {name: {"type": "numeric" if name in (MASS, COCOA, "quantity.pack_count") else "categorical",
                                  "required": name not in (COCOA,), "missing_policy": "reject" if name != COCOA else "fitting_imputation"}
                            for name in records[0]["predictors"]}
    files["model-design.json"] = json_bytes(design)
    files["training-candidates.jsonl"] = files["model-inputs.jsonl"] = row_bytes(records)
    files["quality-report.json"] = json_bytes({"status": "complete_snapshot", "dataset_version": records[0]["dataset_version"],
                                               "counts": {"training_candidates": len(records), "eligible_model_inputs": len(records)}})
    prices = []
    for row in records:
        prices.append({**{n: row[n] for n in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")},
                       "regular_price": row["target"]["regular_price_per_100g_gbp"] * row["predictors"][MASS] / 100,
                       "time_basis": "source_catalogue_observation", **working_contract()["required_regular_price_context"],
                       "currency": "GBP", "tax_basis": "consumer_tax_included", "review_status": "reviewed",
                       "quantity_status": "reviewed", "model_eligible": True, "available": True,
                       "total_edible_weight_g": row["predictors"][MASS], "observed_at": "2026-10-03T12:00:00+01:00"})
    files["prices.jsonl"] = row_bytes(prices)
    manifest = {"manifest_format_version": "chocolate-silver-manifest-1", "schema_version": "chocolate-schema-1",
                "dataset_version": records[0]["dataset_version"], "source_dataset_version": records[0]["source_dataset_version"],
                "contract_sha256": {n: checksum(files[n]) for n in CONTRACTS},
                "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    for n, b in files.items():
        path = silver / n
        if path.exists() and path.read_bytes() != b:
            raise ValueError("refusing to overwrite different fixture inputs")
        path.write_bytes(b)
    _, gold = build_gold_dataset(silver, root / "gold")
    contract = root / "working-contract.json"
    contract.write_bytes(json_bytes(working_contract()))
    return gold, contract


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold, contract = build_fixture(args.output)
    print(gold)
    print(contract)
