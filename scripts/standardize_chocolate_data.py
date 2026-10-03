#!/usr/bin/env python3
"""Apply the chocolate category schema to a deduplicated raw snapshot."""

import argparse
import json
from pathlib import Path
import sys

from chocolate_standardization import build_standardized_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deduplicated-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/standardized/chocolate/uk"))
    parser.add_argument("--reviews", type=Path, help="Evidence-backed schema and price reviews JSON.")
    args = parser.parse_args(argv)
    try:
        report = build_standardized_dataset(args.deduplicated_root, args.output, reviews=args.reviews)
        print(json.dumps({"dataset_version": report["dataset_version"], "counts": report["counts"],
                          "release_ready": report["release_ready"],
                          "report_path": str(args.output.resolve() / "quality-report.json")}))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print("Standardization could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
