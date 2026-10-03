#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pandas==2.2.3"]
# ///
"""Describe a verified silver snapshot with pandas, preserving evidence states."""

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATES = ["known", "unknown", "conflict", "not_applicable"]
CELL_FIELDS = ["status", "review_status", "value", "scope", "qualifier", "method"]
LABEL_FIELDS = {"identity.brand", "identity.retailer", "identity.variant_name"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_inputs(silver_root):
    manifest = json.loads((silver_root / "manifest.json").read_text())
    hashes = {}
    for name in ("products.jsonl", "profile.json", "model-design.json"):
        hashes[name] = sha256(silver_root / name)
        if hashes[name] != manifest["managed_files"][name]["sha256"]:
            raise ValueError(f"Input SHA-256 mismatch: {name}")
    hashes["manifest.json"] = sha256(silver_root / "manifest.json")
    return manifest, hashes


def numeric_summary(values):
    if values.empty:
        return None
    quantiles = pd.to_numeric(values, errors="raise").quantile(
        [0, 0.25, 0.5, 0.75, 1], interpolation="linear"
    )
    return {
        **dict(zip(["min", "q1", "median", "q3", "max"],
                   [round(float(value), 6) for value in quantiles])),
        "n": len(values),
    }


def analyze_schema(products, profile, design):
    """Count seller listings and exact known values for every profile attribute."""
    catalog = profile["attributes"]
    required = {"listing_id", "source_key", "attributes"}
    if products.empty or not required.issubset(products.columns):
        raise ValueError("A nonempty silver products table is required")
    if products["listing_id"].isna().any() or products["listing_id"].duplicated().any():
        raise ValueError("Silver listing IDs must be present and unique")
    if products["source_key"].isna().any():
        raise ValueError("Each listing needs a source key")
    if not products["attributes"].map(lambda row: set(row) == set(catalog)).all():
        raise ValueError("Every listing must contain exactly the profile attributes")

    cells = products[["listing_id", "source_key", "attributes"]].copy()
    cells["attributes"] = cells["attributes"].map(lambda row: [
        {"attribute": name, **{key: row[name][key] for key in CELL_FIELDS}}
        for name in catalog
    ])
    cells = cells.explode("attributes", ignore_index=True)
    cells = pd.concat([cells.drop(columns="attributes"),
                       pd.DataFrame(cells["attributes"].tolist(), dtype=object)], axis=1)
    if not cells["status"].isin(STATES).all():
        raise ValueError("Unsupported attribute evidence state")
    if cells.loc[cells["status"].eq("known"), "value"].isna().any():
        raise ValueError("A known attribute must have a value")
    if cells.loc[~cells["status"].eq("known"), "value"].notna().any():
        raise ValueError("Unknown, conflict and not-applicable values must be null")
    cells["group"] = cells["attribute"].str.split(".", n=1).str[0]
    known = cells.loc[cells["status"].eq("known")].copy()
    known["qualifier"] = known["qualifier"].fillna("(none)")
    known["value_json"] = known["value"].map(
        lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    status_table = cells.groupby(["attribute", "status"], sort=False).size().unstack(fill_value=0)
    status_table = status_table.reindex(index=list(catalog), columns=STATES, fill_value=0)
    source_counts = products.groupby("source_key", sort=False).size()
    source_table = cells.groupby(["attribute", "source_key", "status"]).size().unstack(fill_value=0)
    source_table = source_table.reindex(columns=STATES, fill_value=0)
    group_rows = known.drop_duplicates(["listing_id", "group"]).groupby("group").size()
    n = len(products)
    attributes = []
    for name, definition in catalog.items():
        selected = known.loc[known["attribute"].eq(name)]
        all_cells = cells.loc[cells["attribute"].eq(name)]
        counts = {state: int(status_table.loc[name, state]) for state in STATES}
        k = counts["known"]
        frequencies = selected.groupby("value_json").size().rename("count").reset_index()
        frequencies = frequencies.sort_values(["count", "value_json"], ascending=[False, True])
        values = [{"value": json.loads(key), "count": int(count),
                   "percent_all": round(int(count) / n * 100, 4),
                   "percent_known": round(int(count) / k * 100, 4) if k else None}
                  for key, count in frequencies.itertuples(index=False, name=None)]
        kind = definition["type"]
        if kind == "enum":
            observed = {item["value"] for item in values}
            values.extend({"value": value, "count": 0, "percent_all": 0,
                           "percent_known": 0 if k else None}
                          for value in definition["allowed_values"] if value not in observed)
            mode = "complete_categorical_frequency"
        elif kind in ("number", "integer"):
            mode = "complete_exact_numeric_frequency"
        elif name in LABEL_FIELDS:
            mode = "complete_exact_label_frequency"
        elif kind == "string_list":
            mode = "exact_list_frequency"
        else:
            values = values[:10]
            for item in values:
                value = item.pop("value")
                item.update(value_excerpt=value[:240], value_sha256=hashlib.sha256(value.encode()).hexdigest(),
                            character_count=len(value), excerpt_truncated=len(value) > 240)
            mode = "top_10_exact_text_or_identifier_frequencies"
        numeric = kind in ("number", "integer")
        attributes.append({
            "attribute": name, "group": name.split(".")[0], "type": kind,
            "unit": definition.get("unit"), "selected_model_predictor": name in design["predictors"],
            "listing_count": n, "status_counts": counts, "known_percent": round(k / n * 100, 4),
            "review_status_counts": {key: int(value) for key, value in all_cells.groupby("review_status", sort=False).size().items()},
            "distinct_known_values": len(frequencies),
            **{f"known_{field}_counts": {key: int(value) for key, value in selected.groupby(field, sort=False).size().items()}
               for field in ("scope", "qualifier", "method")},
            "distribution_mode": mode, "value_frequencies": values,
            "numeric_summary": numeric_summary(selected["value"]) if numeric else None,
            "numeric_summary_by_basis": [
                {"scope": scope, "qualifier": qualifier, **numeric_summary(rows["value"])}
                for (scope, qualifier), rows in selected.groupby(["scope", "qualifier"], sort=False)
            ] if numeric else [],
            "coverage_by_source": {source: [int(value) for value in source_table.loc[(name, source)].tolist()]
                                   for source in sorted(source_counts.index)},
        })

    groups = []
    for group in profile["groups"]:
        members = status_table.loc[[name for name in catalog if name.split(".")[0] == group]]
        group_counts = {state: int(value) for state, value in members.sum().items()}
        covered = int(group_rows.get(group, 0))
        groups.append({"group": group, "attributes": len(members),
                       "attributes_with_known_values": int(members["known"].gt(0).sum()),
                       "listings_with_any_known_value": covered,
                       "listing_coverage_percent": round(covered / n * 100, 4),
                       "attribute_listing_cells": n * len(members), "status_counts": group_counts,
                       "known_cell_percent": round(group_counts["known"] / (n * len(members)) * 100, 4)})
    summary = {"listings": n, "attributes": len(catalog),
               "attributes_with_known_values": int(status_table["known"].gt(0).sum()),
               "attributes_without_known_values": int(status_table["known"].eq(0).sum()),
               "attribute_listing_cells": len(cells),
               "status_counts": {key: int(value) for key, value in cells.groupby("status", sort=False).size().items()},
               "review_status_counts": {key: int(value) for key, value in cells.groupby("review_status", sort=False).size().items()}}
    return {"coverage_by_source_state_columns": STATES, "summary": summary, "groups": groups,
            "source_listing_counts": {key: int(value) for key, value in source_counts.items()},
            "attributes": attributes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-root", required=True, type=Path)
    parser.add_argument("--dataset-revision", required=True, help="Immutable 40-character HF commit")
    parser.add_argument("--analysis-date", default=date.today().isoformat())
    parser.add_argument("--portable-profile", type=Path)
    parser.add_argument("--portable-manifest", type=Path,
                        default=ROOT / "plugins/category-processing/profiles/chocolate/dataset-contract.json")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.dataset_revision):
        parser.error("--dataset-revision must be an immutable 40-character commit")
    date.fromisoformat(args.analysis_date)
    inputs = [args.silver_root / name for name in ("products.jsonl", "profile.json", "model-design.json", "manifest.json")]
    inputs += [path for path in (args.portable_profile, args.portable_manifest) if path]
    if args.output.resolve().is_relative_to(args.silver_root.resolve()):
        parser.error("The output must be outside the silver input directory")
    if args.output.resolve() in {path.resolve() for path in inputs}:
        parser.error("The output must be separate from the input files")
    manifest, hashes = verified_inputs(args.silver_root)
    profile = json.loads((args.silver_root / "profile.json").read_text())
    design = json.loads((args.silver_root / "model-design.json").read_text())
    schemas = {"published_silver": profile["schema_version"]}
    if args.portable_profile:
        reference = json.loads(args.portable_manifest.read_text())
        portable = json.loads(args.portable_profile.read_text())
        hashes["portable_profile.json"] = sha256(args.portable_profile)
        if hashes["portable_profile.json"] != reference["files"]["profile.json"]["sha256"]:
            raise ValueError("Portable profile SHA-256 mismatch")
        schemas.update(portable_chocolate=portable["schema_version"],
                       attribute_catalog_and_definitions_identical=profile["attributes"] == portable["attributes"],
                       portable_snapshot_popularity="Frequency counts use the baseline silver products; the portable profile is compared for attribute definitions only.",
                       portable_profile_revision=reference["revision"])
    products = pd.read_json(args.silver_root / "products.jsonl", lines=True,
                            dtype=False, convert_dates=False, precise_float=True)
    report = {
        "analysis_date": args.analysis_date, "dataset_revision": args.dataset_revision,
        "silver_dataset_version": manifest["dataset_version"], "schemas": schemas,
        "processing": {"library": "pandas", "version": pd.__version__,
                       "python_version": sys.version.split()[0], "script_sha256": sha256(__file__)},
        "source_sha256": hashes,
        "definitions": {
            "field_popularity": f"Known-value count divided by all {len(products):,} seller/variant listings. Unknown, conflict and not_applicable remain separate.",
            "value_popularity": "Counts of exact selected values among status known. Both percent of all listings and percent of known listings are reported.",
            "numeric_quantiles": "Linear-interpolated quantiles of selected known numeric values, also separated by scope and qualifier.",
            "text_frequency": "Exact selected string repetition, not semantic ingredient or claim popularity. Noncategorical strings and identifiers list the top 10 repetitions with original-prefix excerpts and exact-value SHA-256 hashes.",
            "source_population": "Seller/variant listings, not distinct physical products, sales volume, consumer preference or UK market share.",
        },
        **analyze_schema(products, profile, design),
        "limitations": [
            "Known status does not establish reviewed accuracy; review-status counts remain explicit.",
            "Numeric scopes and minimum/source-stated qualifiers describe different bases.",
            "Source extraction defects remain in the snapshot and can affect frequency counts.",
            "Unknown dietary, nut and certification claims do not establish absence.",
            "Brand aliases remain separate exact labels; source coverage and variant/template duplication affect frequencies.",
            "Zero coverage does not establish that a schema concept is irrelevant.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Replace the output entry rather than modifying a possible hardlink target.
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
                                prefix="." + args.output.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        temporary.replace(args.output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print(json.dumps({"output": str(args.output), "processing": report["processing"], "summary": report["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
