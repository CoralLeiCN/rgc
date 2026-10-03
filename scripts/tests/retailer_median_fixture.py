"""Synthetic evidence-shaped Gold for explicit fixture validation only."""

import math
from pathlib import Path

from chocolate_gold import build_gold_dataset
from dataset_contracts import resolve_contract_root
from prepare_chocolate_retailer_contract import working_design
from train_chocolate_model import CONTRACTS, checksum, json_bytes, read_json


def observation(identifier, family, price=2.0, *, retailer="Ocado", kind="dark", mass=100):
    return {"observation_id": identifier, "listing_id": "listing-" + identifier,
            "variant_id": "variant-" + identifier, "family_id": family, "comparable_group": "bar",
            "source_role": "retail", "model_eligible": True, "exclusion_reasons": [],
            "schema_version": "chocolate-schema-1", "dataset_version": "silver-retailer-fixture",
            "source_dataset_version": "raw-retailer-fixture",
            "predictors": {"identity.product_group": "bar", "identity.source_role": "retail",
                "identity.boundary_status": "in_scope", "identity.brand": "Fixture Brand",
                "identity.retailer": retailer, "composition.chocolate_type": kind,
                "quantity.total_edible_weight_g": mass, "quantity.pack_count": 1},
            "target": {"regular_price_per_100g_gbp": price, "log_regular_price_per_100g_gbp": math.log(price)}}


def fixture_rows():
    return [observation(f"fixture-{i:03d}-{seller}", f"family-{i:03d}",
                        1 + (i % 7) * 0.2 + seller * 0.15,
                        retailer="Ocado" if seller == 0 else "Waitrose",
                        kind="dark" if i % 2 else "milk", mass=50 if i % 2 else 100)
            for i in range(50) for seller in range(2)]


def fixture_gold(root, values=None, *, candidates=None, current_price=False):
    root = Path(root)
    silver = root / "silver"
    silver.mkdir(parents=True)
    contract = resolve_contract_root(offline=True)
    design = working_design(read_json((contract / "model-design.json").read_bytes()))
    values = fixture_rows() if values is None else values
    candidates = values if candidates is None else candidates
    files = {name: (contract / name).read_bytes() for name in CONTRACTS}
    files["model-design.json"] = json_bytes(design)
    files["quality-report.json"] = json_bytes({"status": "complete_snapshot", "dataset_version": "silver-retailer-fixture",
        "data_provenance": "synthetic_fixture",
        "counts": {"training_candidates": len(candidates), "eligible_model_inputs": len(values)}})
    for name, records in (("model-inputs.jsonl", values), ("training-candidates.jsonl", candidates)):
        files[name] = b"".join(json_bytes(r).replace(b"\n", b"") + b"\n" for r in records)
    prices = [{**{key: r[key] for key in ("observation_id", "listing_id", "source_role", "dataset_version", "source_dataset_version", "schema_version")},
        "regular_price": r["target"]["regular_price_per_100g_gbp"] * r["predictors"]["quantity.total_edible_weight_g"] / 100,
        "currency": "GBP", "tax_basis": "consumer_tax_included", "available": True,
        "total_edible_weight_g": r["predictors"]["quantity.total_edible_weight_g"],
        "review_status": "reviewed", "quantity_status": "reviewed", "model_eligible": r["model_eligible"],
        "observed_at": "2026-10-03T12:00:00Z"} for r in values]
    if current_price:
        for price in prices:
            price.update(displayed_price=price["regular_price"], regular_price=None, tax_basis="unknown",
                         promotion_status="promotional", review_status="unreviewed", quantity_status="known",
                         model_eligible=False, available=None)
    files["prices.jsonl"] = b"".join(json_bytes(p).replace(b"\n", b"") + b"\n" for p in prices)
    manifest = {"manifest_format_version": "chocolate-silver-manifest-1", "schema_version": "chocolate-schema-1",
        "dataset_version": "silver-retailer-fixture", "source_dataset_version": "raw-retailer-fixture",
        "contract_sha256": {name: checksum(files[name]) for name in CONTRACTS},
        "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    for name, data in files.items():
        (silver / name).write_bytes(data)
    return build_gold_dataset(silver, root / "gold")[1]
