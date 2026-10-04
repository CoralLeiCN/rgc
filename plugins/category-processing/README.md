# Category Processing Agent Plugin

## Standard Silver implementation, 4 October 2026

The default build now implements the revised Bronze-to-Silver contract. It uses
four field contracts, a durable SQLite source index, stable source and component
IDs, contextual facts with `.source` and `.method`, explicit states, persistent
human corrections and schema profiling on every build. It accepts an existing
103-field chocolate catalog through a deterministic migration and retains exact
input/effective contract hashes. Model policy and training preparation execute
in Gold. Historical formats remain available with `--legacy`.

See [standard Silver reference](skills/category-processing/references/standard-silver.md) for exact structures, commands,
report calculations, correction recovery and limitations. Published four-file
references are `profiles/<category>/silver-dataset-contract.json`, pinned at
`337fb7f3984ac648e67edd2cb47802f056193efc`. Historical five-file references retain
`dataset-contract.json`; coffee's separate Gold design uses
`profiles/coffee/gold-dataset-contract.json`. Pilot snapshots remain local.

## Historical compatibility interface

The descriptions below retain the published v1 contract and its helpers. Select
`process --legacy` for those outputs; default `process` uses v2.

Bronze indexes for new listings use
`<category>/<market>/products/<source_key>/<product_id>/product.json`, grouping
records from each website/storefront. Processing also reads legacy flat indexes
and mixed archives, verifies source-directory identity and reports duplicate
product IDs across directories. Stored history references and seller UIDs retain
their meanings. The category schema is shared; source mappings handle differences
between website structures.


This package targets the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable components are
[category-schema](skills/category-schema/SKILL.md) for schema design and
[category-processing](skills/category-processing/SKILL.md) for processing, in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation/discovery depend on the
client's format support.

The core uses Python 3.9+ and its standard library to process preserved
category/market archives with a versioned profile. It combines exact seller deduplication, stable
seller identity, typed schema/unit/vocabulary standardization, price/review
eligibility, a processing ledger and grouped artifacts for mapping review in one
silver dataset. The calling harness uses the skill and evidence batches to
prepare mapping changes; there is no external dispatcher or scheduler.

The package includes its engine, generic profile authoring, model-preparation
helpers and optional pinned chocolate/coffee example references in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Category JSON payloads are dataset artifacts rather than Git content. The plugin
uses a commit revision and per-file SHA-256/size checks, without repository sibling
modules or another plugin installation. Category-specific fields, units,
comparable groups and price bases belong to a supplied profile. It does not fit
a regression. Copy the whole package when moving it; run its CLI directly when
native plugin installation is unavailable. The package version is `0.4.0`.

Use the dedicated schema skill for initial creation of a new category schema.
It researches preserved raw data and creates the field catalog with meanings,
types, units, scopes, qualifiers, evidence, coverage and unresolved decisions.
Its standalone instructions need no processing runtime or model target.

Bronze is the preserved raw-data layer produced by collection. The workflow is
Bronze → Silver → Gold, with the generated schema applied during Bronze-to-Silver
processing. Existing raw format identifiers and storage paths refer to Bronze.

Category-processing starts after readable raw data and a generated schema are
available for the requested category/market. If the schema is missing, use
category-schema first; missing raw data routes to collection. Processing configures
mappings/extraction, applies the schema, reviews evidence and finishes at Silver.
Model design and model-input preparation belong to the downstream
[Silver-to-Gold stage](skills/category-processing/references/silver-to-gold.md).

Processing owns `init-profile` and its definition/validation references. The
existing runtime still requires five contracts including a legacy model design,
and writes training views during Silver builds. Do not invent modeling choices
or run `prepare-model` to complete the processing skill. Model-independent
runtime assembly/execution requires a future migration.
Existing-schema refresh, review and extension belong to processing maintenance.

Within an authorized study, the agent reviews, decides and applies supported
local schema, mapping and parser improvements without requiring user review,
confirmation or approval. Evidence justification, five-contract versioning,
relevant tests, impact comparison and model-eligibility checks still apply.
An identified agent may provide the required review decisions; missing evidence
remains unresolved until those checks are satisfied.
When a schema changes, finish local implementation, contracts, rebuild and
validation, then present a detailed summary for user review and wait for
authorization before committing to Hugging Face. Include field/contract changes,
evidence, mapping/unit/scope/price/predictor impacts, before/after counts and
eligibility, tests/gaps, and the exact dataset repository/revision, files and
manifest hashes. The calling harness owns this publication review step; the
plugin does not implement an uploader or automatic popup UI.

```text
python3 <plugin-root>/cli.py init-profile --input <category-definition.json> --output <profile-folder>
python3 <plugin-root>/cli.py process --archive-root <collections-root> --profile <profile-folder> --output <silver-root>
python3 <plugin-root>/cli.py process --archive-root <collections-root> --category chocolate --contracts-cache <cache-root> --output <silver-root> [--offline]
python3 <plugin-root>/cli.py summarize --silver-root <silver-root> --output <summary-output>
```

Choose exactly one of `--category` and `--profile`. `--category chocolate` and
`--category coffee` resolve the corresponding
`profiles/<category>/dataset-contract.json` reference. `--profile` also accepts a
reference directory or a custom local directory containing the five contracts.
Cache misses download the pinned bytes. Each resolution verifies the cache,
including its reference marker; corrupt or inconsistent content fails explicitly.
Processing reads local archives.

The default cache is `<plugin-root>/.contract-cache`, excluded from Git. Select a
writable location with `--contracts-cache <cache-root>` when the installed plugin
permits no writes. Add `--offline` to require a verified populated cache and prohibit
downloads. A full custom profile without a dataset reference needs no network.
Silver outputs preserve the five exact contract files and record their hashes,
repository, immutable revision and reference fingerprint.

Read the skill's references for the
[processing/archive contract](skills/category-processing/references/processing-contract.md),
[category definition](skills/category-processing/references/profile-definition.md),
[profile configuration](skills/category-processing/references/profile-contract.md),
[mapping maintenance](skills/category-processing/references/mapping-maintenance.md), and
[downstream Silver-to-Gold handoff](skills/category-processing/references/silver-to-gold.md).
Chocolate has a broad profile with 103 attributes and conservative source parsing.
Its adapter recognizes explicit blonde chocolate names and coordinated mixed
selections, such as "Milk Chocolate and Dark Chocolate Selection". Extracted
types retain original name evidence and require review for model use; see the
[profile contract](skills/category-processing/references/profile-contract.md).
Coffee is a small starter for structured sources that demonstrates category
independence, with extraction limited to configured inputs.

For a new category, define its attributes and structured source pointers, choose
an observed numeric quantity (item, pack, mass, volume, length or time), currency,
normalization base and reviewed tax basis, then run `init-profile`. This creates
all five aligned contracts and validates them before publishing a new directory;
an existing profile is never overwritten. Definitions use
`category-processing-definition-1`. No food attributes, grams, GBP, or assumed
item count are inserted. Declare multiplicative unit conversions in mappings.
For minor-unit prices, `price.minor_unit_factor` selects the explicit divisor
(legacy profiles default to 100). A design selects one reviewed tax basis through
`eligibility.allowed_tax_bases`; no currency or tax conversion is inferred.
Structured money uses plain decimal amounts with explicit currency; locale
punctuation or currency symbols do not establish a conversion. Existing £/GBP
prefixes are supported only for explicitly GBP observations.

New categories reuse the structured engine without editing its Python core.
Category/source-specific free-text extraction may still need prepared structured
evidence or an additional adapter. Generated contracts establish configuration,
not reviewed facts, complete source coverage, or a validated category model.

Processing also discovers meaningful raw fields outside configured extraction.
It writes full typed values and source pointers to `discovered-fields.jsonl`
(`category-unmapped-fields-1`) and an evidence/justification worksheet to
`schema-extension-review.md`. Known fields and exact archive/control metadata
are excluded; missing leaves are omitted, while zero, false and nested evidence
remain preserved. Optional recipe `discovery` controls raw roots, additional
ignored pointers or explicit disabling; the report records the effective policy.
Discovery is structural and leaves meaning, units and scope unresolved. It does
not infer concepts hidden within already-used prose or update schema/predictors.
The [discovery/proposal workflow](skills/category-processing/references/schema-discovery.md)
describes durable agent proposals, evidence review, contract impacts and tests.
`summarize` copies the new discovery artifacts from verified snapshots alongside
mapping review; older snapshots without them remain supported.
Reusing a packet for an older snapshot removes the two generated discovery files
if they are obsolete, retaining unrelated files. Displayed source data use escaped,
bounded JSON previews; complete evidence remains in JSONL.

Profile loading checks typed attributes, units, enum/list vocabularies and bounds
against the validator's supported template for nullable and known values, plus
category/market constants and selected predictor compatibility. Unsupported value
constraints fail explicitly; this runtime does not execute arbitrary JSON Schema.
Values valid for the category but outside a selected model domain remain in
silver, with candidate exclusion reasons rather than a failed build.

Source discovery, original source/image retrieval and import remain collection
responsibilities. The category-research collection package can produce the
common raw archive consumed here; any compatible producer works. There is no
runtime dependency on that package. Review examples and stable seller review
keys are in the profile reference.
Raw category/market directories use the collection format's case-folded,
hyphen-normalized slugs, with exact safe-name fallback for compatible producers.
Original envelope values and seller UID inputs remain exact.

Run development checks from the repository root:

```text
uv sync --locked
uv run pytest plugins/category-processing/tests
uv run ruff check .
```

For a copied package, install pytest in a development environment and run
`python3 -m pytest tests` from the package root. The runtime uses the standard
library; pytest and Ruff are development tools.

Bundled tests cover generic profile generation, non-food quantity/price bases,
discovery, typed-contract drift, selected-model domain exclusions, reference/cache
routing and isolated copied-plugin execution. Category integration
tests resolve the pinned contracts, requiring a populated default cache or access
to the public dataset on their first run. Resolver unit tests use mocked downloads
and synthetic references without category payload fixtures. These checks establish
package behavior; native installation in multiple harnesses remains unverified.

Dataset eligibility is separate from package correctness: unreviewed evidence and
unresolved price basis remain excluded. Current real chocolate has mapping gaps
and no eligible reviewed model inputs. Inspect generated reports rather than
treating successful processing as model readiness. No regression is fitted.

## Final price target

Every category pricing target uses `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price with reject fallback. Category currencies, quantities and transformations remain declared. Custom profile authoring retains this basis and rejects an excluded-tax target. Observed offers/tax evidence remain preserved; missing support yields no target. The candidate target stores its policy and normalization, and encoder version `category-processing-encoder-2` verifies/fixes that policy. Prepared bundled chocolate/coffee designs and recipes use version 2; dataset manifests update only after approved, verified publication.
