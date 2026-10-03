#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyarrow==21.0.0"]
# ///
"""Mark every Gold candidate model eligible under an explicit user instruction."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_gold_eligibility import mark_gold_eligible


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/gold/chocolate/uk")
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        report, destination = mark_gold_eligible(args.gold_root, args.output, args.authorized_by, args.reason)
    except (OSError, ValueError, KeyError, ImportError) as error:
        print("Gold eligibility could not complete: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"dataset_version": report["dataset_version"], "counts": report["counts"],
                      "source_counts": report["source_counts"], "output": str(destination),
                      "eligibility_provenance": report["eligibility_provenance"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
