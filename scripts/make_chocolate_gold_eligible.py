#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Migrate historical Gold to the training population without eligibility fields."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold_population import build_population


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/gold/chocolate/uk")
    parser.add_argument("--authorized-by", help=argparse.SUPPRESS)
    parser.add_argument("--reason", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        report, destination = build_population(args.gold_root, args.output, input_kind="gold")
    except (OSError, ValueError, KeyError, ImportError) as error:
        print("Gold migration could not complete: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"dataset_version": report["dataset_version"], "counts": report["counts"],
                      "output": str(destination), "gold_ready_for_loading": report["gold_ready_for_loading"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
