#!/usr/bin/env python3
"""Build a reviewed-analysis staging dataset from preserved UK chocolate records."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_cleanup import build_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True,
                        help="Collections root containing chocolate/uk/products.")
    parser.add_argument("--output", type=Path, default=Path("data/derived/chocolate/uk"))
    parser.add_argument("--reviews", type=Path, help="Evidence-backed review decisions JSON.")
    args = parser.parse_args(argv)
    try:
        report = build_dataset(args.archive_root, args.output, reviews=args.reviews)
        print(json.dumps({"dataset_version": report["dataset_version"],
                          "counts": report["counts"],
                          "release_ready": report["release_ready"],
                          "report_path": str(args.output.resolve() / "quality-report.json")}))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print("Cleaning could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
