#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Build a separate immutable Parquet package for reviewed chocolate inference."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold_inferred import build_gold_inferred_dataset

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-root", type=Path, default=ROOT / "data/silver/chocolate/uk")
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/gold-inferred/chocolate/uk")
    args = parser.parse_args(argv)
    try:
        report, destination = build_gold_inferred_dataset(
            args.silver_root, args.output, args.decisions, args.provenance
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        print("Inferred Gold build could not complete: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({
        "dataset_version": report["dataset_version"],
        "counts": report["counts"],
        "eligibility_preserved": report["eligibility_preserved"],
        "unknown_values_preserved": report["unknown_values_preserved"],
        "release_ready": False,
        "output": str(destination),
        "manifest_path": str(destination / "manifest.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
