#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Prepare immutable chocolate Gold from Silver and the selected study contract."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold import build_gold_dataset

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--silver-root", type=Path, default=ROOT / "data/silver/chocolate/uk")
    source.add_argument("--gold-root", type=Path, help="Migrate a verified existing Gold snapshot.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/gold/chocolate/uk")
    parser.add_argument("--model-design", type=Path, help="Gold study contract; defaults to the pinned current-price chocolate design.")
    parser.add_argument("--relationships", type=Path, help="Evidence-backed stable family/physical-product assignments for Silver v2.")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.gold_root is not None:
            from chocolate_gold_population import build_population
            report, destination = build_population(args.gold_root, args.output, input_kind="gold")
        else:
            report, destination = build_gold_dataset(args.silver_root, args.output, model_design=args.model_design,
                                                     relationships=args.relationships, offline=args.offline)
    except (OSError, ValueError, KeyError, ImportError) as error:
        print("Gold build could not complete: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"dataset_version": report["dataset_version"], "status": report["status"],
                      "counts": report["counts"], "gold_ready_for_loading": report["gold_ready_for_loading"],
                      "release_ready": False, "output": str(destination),
                      "report_path": str(destination / "report.json")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
