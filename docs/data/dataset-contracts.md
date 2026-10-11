# Dataset-owned analytical contracts

Analytical schemas, mappings, validators, recipes and model designs belong in the
authoritative dataset identified by each Git manifest. Git retains small immutable
references and checksums; it must not contain copies of schema bodies or a research
field catalog. Generated snapshots retain exact contract copies and provenance.

## References and resolution

A reference specifies the dataset repository, immutable commit, contract set,
versions and managed file paths, byte lengths and SHA-256 hashes. Moving references
such as a branch tip are not accepted as reproducible contracts. Minimal category
and market metadata required by the resolver are implementation references,
not a catalog of researched sources or results.

```sh
python3 -B scripts/fetch_contracts.py --all
python3 -B scripts/fetch_contracts.py --all --offline
```

The `--all` option selects configured references. Standard Silver resolves four
field contracts; its optional historical model design is independent of the
selected Gold design. Legacy profiles retain their supported five-file interface.
Use `--help` for selecting individual references and custom cache roots.

Caches under `data/contract-cache/` and the portable package's `.contract-cache/`
are ignored. Verify every available cached file before reuse, including partial
caches. Offline use fails clearly when required files are missing; it must not
silently download or substitute a newer revision. Output snapshots retain exact
contract bytes and reference metadata for reproducibility.

## Maintenance and publication

Prepare a local working copy, preserve evidence, coordinate semantic versions and
validate schema, mapping, validator, recipe and design alignment. Research cases,
impact measurements and draft proposals belong in ignored local documents.
Complete the [release review](../decisions/agent-led-schema-maintenance.md) before
publishing changed schemas. Do not upload private research merely because it is
available locally.

`scripts/publish_contracts.py --help` describes the prepared-tree publisher.
Inspect its inventory before an authorized upload, verify remote bytes, then
synchronize local reference manifests. Preserve unrelated dataset files and
historical snapshots. A storage migration must preserve contract bytes and
versions unless a separately reviewed semantic change is intended.

## Verification

```sh
uv sync --locked
uv run pytest scripts/tests/test_dataset_contracts.py scripts/tests/test_documentation.py
uv run ruff check .
python3 -B scripts/check_documentation.py
```

Documentation checks run offline with no caches and validate any cached bodies
present. A passing local check does not prove remote availability or publication.
Model artifacts follow the [model maintenance workflow](../model-maintenance.md).
Actual dataset inventories, release receipts and research outcomes remain private.
