#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pandas==2.2.3"]
# ///
"""Build the combined chocolate silver layer directly from preserved raw data."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_silver import build_silver_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True,
                        help="Raw collections root containing chocolate/uk/products.")
    parser.add_argument("--output", type=Path, default=Path("data/silver/chocolate/uk"))
    parser.add_argument("--reviews", type=Path, help="Evidence-backed chocolate-schema-reviews-1 decisions.")
    parser.add_argument("--family-mappings", type=Path,
                        help="Reusable chocolate-family-mappings-1 identity decisions; defaults to the repository registry.")
    parser.add_argument("--schema-root", type=Path, help="Custom directory containing all four chocolate contract files.")
    parser.add_argument("--offline", action="store_true", help="Require the verified local contract cache; do not fetch contracts.")
    parser.add_argument("--legacy", action="store_true", help="Reproduce historical chocolate Silver with its fixed study contract.")
    parser.add_argument("--profile", type=Path, help="Four Silver field contracts; the packaged chocolate profile is the default.")
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--inferences", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.legacy:
            report = build_silver_dataset(args.archive_root, args.output, reviews=args.reviews,
                                         schema_root=args.schema_root, offline=args.offline,
                                         family_mappings=args.family_mappings, table_backend="pandas")
        else:
            if args.reviews or args.family_mappings or args.schema_root:
                raise ValueError("Historical review/model contracts require --legacy. Use --profile for Silver fields, --inferences for agent results, and durable review for human decisions.")
            from category_processing.silver_contracts import resolve_silver_profile
            from category_processing.standard_silver import build_standard_silver
            profile = resolve_silver_profile(args.profile, category=None if args.profile else "chocolate", offline=args.offline)
            report = build_standard_silver(args.archive_root, args.output, profile, state_db=args.state_db,
                                           inferences=args.inferences, backend="pandas")
        print(json.dumps({"dataset_version": report["dataset_version"], "status": report["status"],
                          "counts": report["counts"], "release_ready": report["release_ready"],
                          "output": report.get("output", str(args.output.resolve())),
                          "state_db": report.get("state_db"),
                          "report_path": str(Path(report.get("output", args.output)).resolve() / "quality-report.json")}))
        return 0 if report["status"] == "complete_snapshot" else 1
    except (ValueError, OSError, RuntimeError) as error:
        print("Silver build could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
