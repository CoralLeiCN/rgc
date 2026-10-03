#!/usr/bin/env python3
"""Cache checksum-pinned Hugging Face contracts for reproducible offline use."""

import argparse
from pathlib import Path

from dataset_contracts import ROOT, SCHEMA_REFERENCE, SCHEMA_CACHE, resolve_contracts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Include portable chocolate and coffee profiles.")
    parser.add_argument("--offline", action="store_true", help="Verify caches without network access.")
    parser.add_argument("--cache-root", type=Path, help="Use one supplied cache root for all selected references.")
    args = parser.parse_args(argv)
    entries = [(SCHEMA_REFERENCE, args.cache_root or SCHEMA_CACHE)]
    if args.all:
        plugin = ROOT / "plugins/category-processing"
        for category in ("chocolate", "coffee"):
            entries.append((plugin / "profiles" / category / "dataset-contract.json",
                            args.cache_root or plugin / ".contract-cache"))
    for reference, cache in entries:
        print(resolve_contracts(reference, cache, offline=args.offline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
