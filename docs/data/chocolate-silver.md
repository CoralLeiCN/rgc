# Canonical Bronze and Silver workflow

The canonical builder processes original Bronze captures into combined Silver.
Source identities, original text, artifact links, corrections and provenance
remain available. Separate seller listings remain separate analytical records.
The standalone deduplication, standardization and cleanup tools support
compatibility and diagnostics.

```sh
uv run python scripts/build_chocolate_silver.py --archive-root /path/to/collections --output /path/to/silver --offline
```

Use the builder's `--help` for supported options and historical formats. Fetch the
pinned [dataset contracts](dataset-contracts.md) before offline execution. A
standard run owns no model design; selected downstream requirements belong to Gold.

## Evidence and derived facts

Preserve source identity and exact capture references. Resolve values with their
scope, units, qualifiers, variants and components. Missing is unknown, not zero or
false. Source claims remain claims. Conflicting source declarations remain
separately evidenced rather than silently reconciled.

Persistent corrections are stored separately and replayed against source identity.
Agent assertions retain their inferred method. Source changes require another
assessment. Reports expose profiling and unresolved evidence for review; actual
counts, source lists and examples belong in ignored local research documents.

## Integrity and downstream use

Validate source histories and artifact hashes, contract bytes, record schemas and
output manifests. Keep snapshot inputs immutable and record which source state
produced each result. Pass the verified result to [Gold](chocolate-gold.md) for a
selected comparison population, target and feature preparation.

See [portable processing](category-processing.md),
[deduplication](chocolate-deduplication.md) and
[cleanup](chocolate-cleaning.md) for related interfaces. This guide records the
implementation rather than the status or contents of a collected corpus.
