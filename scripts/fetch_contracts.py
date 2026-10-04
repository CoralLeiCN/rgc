#!/usr/bin/env python3
"""Cache checksum-pinned Hugging Face contracts for reproducible offline use."""

import argparse
from pathlib import Path

from dataset_contracts import (
    CURRENT_PRICE_REFERENCE,
    ROOT,
    SCHEMA_CACHE,
    SCHEMA_REFERENCE,
    STANDARD_GOLD_REFERENCE,
    resolve_contracts,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Include all current and historical chocolate and coffee contracts.")
    parser.add_argument("--offline", action="store_true", help="Verify caches without network access.")
    parser.add_argument("--current-price", action="store_true", help="Include the published current-price target overlay.")
    parser.add_argument("--cache-root", type=Path, help="Use one supplied cache root for all selected references.")
    args = parser.parse_args(argv)
    plugin = ROOT / "plugins/category-processing"
    entries = [(SCHEMA_REFERENCE, args.cache_root or SCHEMA_CACHE),
               (plugin / "profiles/chocolate/silver-dataset-contract.json", args.cache_root or plugin / ".contract-cache"),
               (STANDARD_GOLD_REFERENCE, args.cache_root or SCHEMA_CACHE)]
    if args.current_price or args.all:
        entries.append((CURRENT_PRICE_REFERENCE, args.cache_root or SCHEMA_CACHE))
    if args.all:
        for category in ("chocolate", "coffee"):
            entries.append((plugin / "profiles" / category / "dataset-contract.json",
                            args.cache_root or plugin / ".contract-cache"))
        for name in ("silver-dataset-contract.json", "gold-dataset-contract.json"):
            entries.append((plugin / "profiles/coffee" / name, args.cache_root or plugin / ".contract-cache"))
    for reference, cache in entries:
        print(resolve_contracts(reference, cache, offline=args.offline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
