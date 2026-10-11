# Product evidence platform

The software connects preserved product evidence, analytical preparation,
validated models and an interactive explorer. It supports configurable categories
and keeps seller identity and original evidence throughout processing.

## Components

- Bronze import preserves original records, source artifacts and immutable captures.
- Silver applies verified analytical contracts, records uncertainty and supports
  durable corrections without rewriting source evidence.
- Gold prepares immutable Parquet inputs under a selected study contract.
- Model tools validate inputs, record assumptions and emit reproducible artifacts.
- The web app explores observed evidence and keeps proposed product drafts separate.

See [setup](README), [data interfaces](docs/data/spec.md),
[model interfaces](docs/model/spec.md) and [app interfaces](docs/app/spec.md).

## Limitations

Successful collection does not establish exhaustive coverage. A valid schema,
processed dataset or successful fit does not establish accuracy or readiness for
release. Missing evidence remains unknown; source claims remain attributed.

A selected study can explicitly use displayed prices as a target proxy. That
choice, its limitations and any historical price policy must be retained with
its dataset-owned model specification and run artifacts. The software must not
silently reinterpret an older snapshot under another policy.

Private research documents own the actual categories, source selection, observed
counts, experimental results and publication receipts. They are excluded from
Git. Dataset references identify exact artifacts needed by the implementation;
they do not publish an inventory of ongoing research.
