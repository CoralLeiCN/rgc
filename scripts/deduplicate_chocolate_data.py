#!/usr/bin/env python3
"""Build a separate raw, deduplicated UK chocolate data layer."""

import argparse
import json
import sys
from pathlib import Path

from chocolate_cleanup.deduplication import build_deduplicated_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True,
                        help="Raw collections root containing chocolate/uk/products.")
    parser.add_argument("--output", type=Path, default=Path("data/deduplicated/chocolate/uk"))
    args = parser.parse_args(argv)
    try:
        report = build_deduplicated_dataset(args.archive_root, args.output)
        print(json.dumps({"dataset_version": report["dataset_version"], "status": report["status"],
                          "counts": report["counts"],
                          "report_path": str(args.output.resolve() / "quality-report.json")}))
        return 0 if report["status"] == "complete_snapshot" else 1
    except (OSError, ValueError, RuntimeError) as error:
        print("Deduplication could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
