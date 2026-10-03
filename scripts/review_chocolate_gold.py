#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Annotate all Gold rows as reviewed on an explicit user instruction, preserving source values."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold import mark_gold_reviewed

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/gold/chocolate/uk")
    parser.add_argument("--reviewed-by", required=True, help="Identity of the user authorizing the annotation.")
    parser.add_argument("--reason", required=True, help="Explicit user request authorizing this bulk review annotation.")
    args = parser.parse_args(argv)
    try:
        report, destination = mark_gold_reviewed(args.gold_root, args.output, args.reviewed_by, args.reason)
    except (OSError, ValueError, KeyError, ImportError) as error:
        print("Gold bulk review could not complete: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"dataset_version": report["dataset_version"], "status": report["status"],
                      "counts": report["counts"],
                      "review_provenance": report["review_provenance"],
                      "release_ready": False, "output": str(destination),
                      "report_path": str(destination / "report.json")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
