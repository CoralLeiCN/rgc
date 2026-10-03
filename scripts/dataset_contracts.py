"""Repository entry point for dataset-owned analytical contract resolution."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins/category-processing"
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from category_processing.dataset_contracts import (  # noqa: E402
    cache_directory,
    load_manifest,
    resolve_contracts,
    verify_contract_directory,
)

SCHEMA_REFERENCE = ROOT / "schemas/chocolate/dataset-contract.json"
SCHEMA_CACHE = ROOT / "data/contract-cache"
CURRENT_PRICE_REFERENCE = ROOT / "schemas/chocolate/current-price/dataset-contract.json"


def resolve_contract_root(schema_root=None, *, offline=False):
    """Use the dataset pin by default; preserve explicit custom contract roots."""
    if schema_root is None:
        return resolve_contracts(SCHEMA_REFERENCE, SCHEMA_CACHE, offline=offline)
    directory = Path(schema_root)
    manifest = load_manifest(SCHEMA_REFERENCE)
    if directory.resolve() == cache_directory(manifest, SCHEMA_CACHE).resolve():
        verify_contract_directory(manifest, directory)
    elif (directory / "dataset-contract.json").is_file():
        reference = load_manifest(directory / "dataset-contract.json")
        if all((directory / name).is_file() for name in reference["files"]):
            verify_contract_directory(reference, directory)
        else:
            return resolve_contracts(directory / "dataset-contract.json", SCHEMA_CACHE, offline=offline)
    return directory
