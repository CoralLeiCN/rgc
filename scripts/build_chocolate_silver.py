#!/usr/bin/env python3
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
    parser.add_argument("--schema-root", type=Path, help="Custom directory containing all four chocolate contract files.")
    parser.add_argument("--offline", action="store_true", help="Require the verified local contract cache; do not fetch contracts.")
    args = parser.parse_args(argv)
    try:
        report = build_silver_dataset(args.archive_root, args.output, reviews=args.reviews,
                                     schema_root=args.schema_root, offline=args.offline)
        print(json.dumps({"dataset_version": report["dataset_version"], "status": report["status"],
                          "counts": report["counts"], "release_ready": report["release_ready"],
                          "report_path": str(args.output.resolve() / "quality-report.json")}))
        return 0 if report["status"] == "complete_snapshot" else 1
    except (ValueError, OSError, RuntimeError) as error:
        print("Silver build could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
