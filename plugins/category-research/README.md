# Category Research Agent Plugin

This package targets the [Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-research/SKILL.md](skills/category-research/SKILL.md), in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation and discovery depend on the
client's support for this format; native compatibility with particular harnesses
has not been demonstrated.

The standard-library Python core preserves supplied product records and original
source/image bytes. It can be invoked by another plugin through the CLI or
`category_research.import_document`. It has no dependency on a particular category
taxonomy and does not fit a model. Food, electronics, apparel, furniture and
other product categories use the same import envelope; category-specific source
retrieval remains the calling agent's responsibility. Python 3.9 or later is required; no package or
global installation is needed.

```text
python3 <plugin-root>/cli.py import --input <collection.json> --output <archive-root> --download-images --workers 4
```

Read the [import contract](skills/category-research/references/import-contract.md)
for input fields, local source/catalog preservation, API usage, transfer options,
and archive/report semantics. Products can be supplemented by subsequent imports:
raw artifacts and capture history remain immutable while `product.json` retains
every capture in its current index. Network transfer failures and source-field
observations remain visible. Version 0.2.0 defaults to description, prices and
availability observations. Optional `collection_sections` selects any other
field-key markers, or `{}` disables those heuristics. No ingredient, nutrition or
packaging section is assumed for an unspecified category. New captures and
reports label this behavior `category-research-sections-2`; the
`category-research-raw-1` evidence archive and earlier captures remain compatible
and unchanged. CLI summaries use `section_fields_unknown`; the legacy
`ingredient_fields_unknown` counter appears only when an `ingredients` section
is explicitly selected. These observations are advisory, not required fields or
claims of complete category coverage.
Markers support Unicode source keys through NFKC normalization and case-folding
for matching only; original keys, configured markers and evidence remain unchanged.

Collection preserves raw archives for later processing. The separate
category-processing package provides its own CLI and skill and consumes the
[archive format](skills/category-research/references/import-contract.md)
to build silver data with distinct seller rows, apply category profiles, summarize
mapping gaps and prepare reviewed model inputs. It runs independently of this
collection package's installation. Regression fitting belongs to later modeling.

Run development checks from the repository root:

```text
uv sync --locked
uv run pytest plugins/category-research/tests
uv run ruff check .
```

For a copied package, install pytest in a development environment and run
`python3 -m pytest tests` from the package root. The runtime uses the standard
library; pytest and Ruff are development tools.
