"""Synthetic reviewed population for estimator checks; never market evidence."""

import math
import random

from chocolate_lightgbm_without_brand import (
    BASIS,
    COCOA,
    RECIPE,
    RETAILER,
    TYPE,
    WEIGHT,
)


def fixture_rows(families=180):
    generator = random.Random(481)
    rows = []
    for i in range(families):
        kind = ["dark", "milk", "white"][i % 3]
        recipe = ["plain", "inclusion", "filled"][(i // 3) % 3]
        for seller in ("Waitrose", "Ocado"):
            for mass in (50, 100, 150):
                identifier = f"fixture-{i}-{seller}-{mass}"
                attributes = random.Random(481 + i * 10000 + mass)
                nuts = attributes.choice(["present", "explicitly_absent", "unknown"])
                cocoa = None if i % 5 == 0 else (30 if mass == 50 else 70 if mass == 150 else 50)
                values = {WEIGHT: mass, TYPE: kind, RECIPE: recipe, RETAILER: seller, COCOA: cocoa,
                          BASIS: "whole_product", "identity.brand": f"Fixture Brand {i // 9 % 3}",
                          "identity.product_group": "bar", "identity.source_role": "retail",
                          "identity.study_cohort": "uk_supermarket_standard_single_pack_chocolate_bar",
                          "quantity.pack_count": 1, "composition.nuts_presence": nuts}
                for name in ("dietary.vegan_claim", "certifications.fairtrade_claim", "certifications.organic_claim"):
                    values[name] = attributes.choice(["present", "explicitly_absent", "unknown"])
                logged = 1.2 - 0.3 * math.log(mass / 100) + 0.2 * (seller == "Ocado") + 0.35 * (kind == "dark") + 0.2 * (recipe == "filled") + 0.15 * (nuts == "present") + generator.uniform(-0.04, 0.04)
                price = round(math.exp(logged), 8)
                rows.append({"observation_id": identifier, "listing_id": "listing-" + identifier,
                             "variant_id": f"variant-{i}-{mass}", "family_id": f"family-{i}",
                             "comparable_group": "bar", "source_role": "retail", "model_eligible": True,
                             "exclusion_reasons": [], "predictors": values,
                             "target": {"regular_price_per_100g_gbp": price, "log_regular_price_per_100g_gbp": math.log(price)},
                             "dataset_version": "silver-lightgbm-fixture", "source_dataset_version": "raw-synthetic-fixture",
                             "schema_version": "chocolate-schema-1"})
    return rows


def fixture_gold(root, *, eligible=True):
    from chocolate_gold import build_gold_dataset
    from dataset_contracts import resolve_contract_root
    from train_chocolate_model import CONTRACTS, checksum, json_bytes

    silver = root / "silver"
    silver.mkdir(parents=True)
    files = {name: (resolve_contract_root(offline=True) / name).read_bytes() for name in CONTRACTS}
    import json

    design = json.loads(files["model-design.json"])
    observations = fixture_rows()
    if not eligible:
        for row in observations:
            row["model_eligible"] = False
            row["exclusion_reasons"] = ["fixture_evidence_unreviewed"]
    for name in observations[0]["predictors"]:
        design["predictors"][name] = {"type": "numeric" if name in {WEIGHT, COCOA, "quantity.pack_count"} else "categorical",
                                      "required": True, "missing_policy": "reject", "reference": "training_mode"}
    files["model-design.json"] = json_bytes(design)
    files["quality-report.json"] = json_bytes({"dataset_version": "silver-lightgbm-fixture", "status": "complete_snapshot",
                                                "counts": {"training_candidates": len(observations), "eligible_model_inputs": len(observations) if eligible else 0}})
    def jsonl(values):
        return b"".join(json.dumps(r, sort_keys=True, allow_nan=False).encode() + b"\n" for r in values)
    files["training-candidates.jsonl"] = jsonl(observations)
    files["model-inputs.jsonl"] = jsonl(observations) if eligible else b""
    prices = [{**{name: row[name] for name in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")},
               "regular_price": row["target"]["regular_price_per_100g_gbp"] * row["predictors"][WEIGHT] / 100,
               "currency": "GBP", "tax_basis": "consumer_tax_included", "review_status": "reviewed", "quantity_status": "reviewed",
               "model_eligible": eligible, "available": True, "total_edible_weight_g": row["predictors"][WEIGHT],
               "observed_at": "2026-10-03T12:00:00+01:00"} for row in observations]
    files["prices.jsonl"] = jsonl(prices)
    manifest = {"manifest_format_version": "chocolate-silver-manifest-1", "schema_version": "chocolate-schema-1",
                "dataset_version": "silver-lightgbm-fixture", "source_dataset_version": "raw-synthetic-fixture",
                "contract_sha256": {n: checksum(files[n]) for n in CONTRACTS},
                "managed_files": {n: {"sha256": checksum(b), "byte_length": len(b)} for n, b in files.items()}}
    for name, data in files.items():
        (silver / name).write_bytes(data)
    (silver / "manifest.json").write_bytes(json_bytes(manifest))
    _, destination = build_gold_dataset(silver, root / "gold")
    return destination, design
