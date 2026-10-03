"""Verify Gold storage and expose the complete population without selection fields."""

from copy import deepcopy
from pathlib import Path

from chocolate_gold import (
    json_bytes,
    read_json,
    row_bytes,
    rows,
    verified_gold,
    verified_gold_storage,
)
from chocolate_gold_population import POPULATION_RULE

POLICY_VERSION = "chocolate-gold-training-all-rows-2"


def training_rows(candidates):
    """Remove selection fields and retain historical decisions as provenance."""
    result = []
    for original in candidates:
        row = deepcopy(original)
        if "model_eligible" in row:
            row.setdefault("source_model_eligible", row.pop("model_eligible"))
        if "exclusion_reasons" in row:
            row.setdefault("source_exclusion_reasons", row.pop("exclusion_reasons"))
        result.append(row)
    return result


def verified_training_gold(root):
    """Verify immutable source bytes, then admit every candidate.

    Historical selection counters remain provenance. Missing numerical inputs
    and grouping fields remain missing; admission does not synthesize them.
    """
    root = Path(root).resolve()
    storage = read_json((root / "manifest.json").read_bytes())
    if storage.get("manifest_format_version") == "chocolate-gold-inferred-manifest-1":
        from chocolate_gold_inferred import verified_gold_inferred
        _, _, child = verified_gold_inferred(root)
    else:
        child = root
    child_manifest = read_json((child / "manifest.json").read_bytes())
    verifier = verified_gold if child_manifest.get("processing_rule_version") == POPULATION_RULE else verified_gold_storage
    silver, silver_bytes, inputs = verifier(child)
    candidates = rows(inputs["training-candidates.jsonl"])
    historical_count = (None if child_manifest.get("processing_rule_version") == POPULATION_RULE
                        else len(rows(inputs["model-inputs.jsonl"])))
    admitted = row_bytes(training_rows(candidates))
    inputs["training-candidates.jsonl"] = admitted
    inputs["model-inputs.jsonl"] = admitted
    inputs["source-prices.jsonl"] = inputs["prices.jsonl"]
    inputs["prices.jsonl"] = row_bytes(training_rows(rows(inputs["prices.jsonl"])))
    inputs["gold-training-policy.json"] = json_bytes({"policy_version": POLICY_VERSION,
        "admission_basis": "all_gold_rows", "source_candidates": len(candidates),
        "historical_source_eligible_rows": historical_count, "training_rows": len(candidates),
        "source_dataset_version": storage["dataset_version"],
        "missing_values_preserved": True, "release_ready": False})
    return silver, silver_bytes, inputs
