# Category Processing Agent Plugin

This package targets the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-processing/SKILL.md](skills/category-processing/SKILL.md), in the
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
native plugin installation is unavailable. The package version is `0.3.2`.

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
python3 <plugin-root>/cli.py prepare-model --silver-root <silver-root> --output <model-preparation-root> --validation-fraction 0.2
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
[model handoff](skills/category-processing/references/model-handoff.md).
Chocolate has a broad profile with 103 attributes and conservative source parsing;
coffee is a small starter for structured sources that demonstrates category
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
