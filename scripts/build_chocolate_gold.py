#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Copy combined chocolate silver training values into an immutable Parquet gold layer."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold import build_gold_dataset

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-root", type=Path, default=ROOT / "data/silver/chocolate/uk")
    parser.add_argument("--output", type=Path, default=ROOT / "data/gold/chocolate/uk")
    args = parser.parse_args(argv)
    try:
        report, destination = build_gold_dataset(args.silver_root, args.output)
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
