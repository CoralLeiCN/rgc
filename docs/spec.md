# Product Feature Classification and Pricing Specification

This specification defines data, modeling and acceptance requirements for the
scope in [intention](intention.md). The [lifecycle plan](lifecycle/plan.md) records
implementation and verification evidence.

## 1. Scope and delivery order

| Stage | Requested outcome | Implementation status |
| --- | --- | --- |
| 1 | Collect original product information, images and prices through a portable plugin; provide another plugin for processing within each seller, category profiles, mapping maintenance and model preparation; fit a regression explaining feature contributions. | Raw collection, combined chocolate silver/schema, model preparation and documentation maintenance are implemented and verified. The processing package passed package, isolated copy and collected data validation. Classification review/evaluation and model fitting/validation remain outstanding. |
| 2 | Let a brand test the price of a newly designed product using that model. | Application outstanding; requires a validated category model. |
| 3 | Score category value for money and assess brand premium. | Research only; scoring implementation is deferred. |

The product must support many categories over time. Chocolate sold in the United
Kingdom is the current collection study and an example for later categories.
The market describes where products are sold. Country of
manufacture is a separate attribute where relevant.

Collect broadly using the minimal identity and provenance envelope in section
3.1, then derive and extend the analytical schema in section 3.2. Each
category/market study has its own dataset, eligibility, validation and domain for
price testing. Adding a category may require source extractors and an analytical
profile while reusing the common collection core.

Deliver collection as an agent plugin usable across multiple harnesses. A
harness is the runtime that executes an agent and supplies its tools. Section
2.4 defines portability requirements and the current package.

Both plugins use generic cores with category-specific configuration. Collection
section tracking must not require food fields for non-food products. A new
processing profile must be authorable without copying a bundled chocolate or
coffee profile. Fields, source pointers, comparable groups, units, currency,
observed quantity and tax basis belong to each study. Supporting a category's
configuration does not establish complete source extraction or model readiness.


Follow [AGENTS.md](../AGENTS.md) for English authored content, writing style and
verbatim preservation of original source evidence.

## 2. Core workflows

### 2.1 Research a category

1. Define the category, market, category boundaries, collection period, and
   intended source coverage, using the minimal collection envelope.
2. Discover a broad set of products across sources, brands, product forms, sizes,
   attributes for the category, packaging, promotional claims, and price ranges.
3. Use the collection plugin to archive product records and original source/image
   evidence under section 3.1.
4. Within one silver build, verify raw captures/histories and group exact
   duplicate listings within each selling source; retain all original captures
   and keep different shops' listings unique.
5. After collecting many products, review the corpus and derive the analytical
   category schema. Apply its versioned types, units and vocabularies after
   deduplication within that same silver dataset. Classify features from preserved
   evidence and review ambiguous, missing or conflicting data.
6. Define comparable groups, price basis, normalization, and model eligibility;
   produce a coverage and quality report before fitting a model.

Collect as many distinct products and varieties as practicable. Report the
number found, sources searched, coverage gaps, failed extraction and exclusions.
Report seller listing counts and verified physical product coverage distinctly,
and qualify market coverage when the search is incomplete. Section 4 defines
readiness through independent variation and validation instead of a fixed count.

### 2.2 Fit and inspect a pricing model

1. Select the eligible observations and comparable product group.
2. Build model inputs from the reviewed feature schema.
3. Fit an interpretable regression and evaluate it on held out data.
4. Present feature estimates, reference levels, uncertainty, support counts,
   validation results, and limitations.

The output must distinguish an estimated conditional price association from a
causal effect. A coefficient cannot by itself establish that adding a claim or
ingredient causes the corresponding price change.

### 2.3 Test a newly designed product

1. A brand describes a proposed product using the model's feature schema.
2. The user selects supported market, product group and pricing context.
3. The model estimates a price and prediction interval, with feature comparisons
   and warnings about unsupported inputs.
4. If the user supplies a proposed selling price, compare it with the model's
   estimate in both currency and percentage terms.

This is a test against observed market pricing. It does not estimate demand,
profit or the price that maximizes revenue; those quantities require other data.

### 2.4 Agent plugin for collecting product information

The plugin covers discovery and collection of prices, product information and
features, packaging emphasis, promotional claims and their evidence. It produces
the raw bundles in section 3.1. Schema derivation, regression fitting, testing
prices for new products and deferred scoring use those bundles later.

The design has three parts:

| Part | Responsibility |
| --- | --- |
| Portable collection core | Apply study scope and the raw preservation contract; produce product JSON and the common collection result. |
| Standard plugin package | Expose a discoverable Agent Skill in the Agent Plugins format; the calling harness supplies discovery/retrieval tools and can invoke the bundled CLI or Python API. |
| Source extractors | Capture information and images, including unfamiliar fields; support new sources/categories through the common raw envelope. Later analytical profiles may guide derived extraction while preserving raw collection. |

#### Input and output contract

Use a versioned, structured request/result contract; JSON is the initial proposed
representation. Native tool names and packaging may differ between harnesses,
but the meanings of these inputs and outputs must be consistent.

| Direction | Content |
| --- | --- |
| Request | Envelope contract version, study identifier, category, market, category boundaries, source scope, collection window, requested information and coverage goals where defined. Analytical profiles or comparison bases are optional references; collection retains all relevant source fields. |
| Result metadata | Envelope contract version, study/category identifiers, collection run identifier, collection time, completion status, and declared tool/extraction capabilities used. |
| Result bundles | Product identity/provenance, JSON, timestamped original source/image evidence, artifact metadata and history under section 3.1. Later interpretations carry their own schema/version and evidence references. |
| Result report | Sources attempted and reached, unique product coverage, missingness, extraction limitations, inaccessible sources, failures, and reasons the study scope was only partially covered. |

Carry or explicitly reference study scope in the request. It must be usable
independently of previous conversation, internal harness session identifiers and
hardcoded local output paths. Supply evidence references that the consuming
application can resolve across hosts.

#### Compatibility and incomplete collection

Each integration declares its capabilities and delivery method. If source or
packaging/image extraction is unavailable, record the limitation, preserve
unknowns and return useful partial results with qualified completion status.
Missing capabilities and inaccessible sources must never produce invented data.

Validate integrations against the same request/result contract and supplied evidence
fixtures. Support must be demonstrated in at least two selected agent harnesses
before describing the plugin as compatible with multiple harnesses. Live search
can discover different products across hosts; conformance means compatible
envelope meanings, artifact preservation and evidence handling. Products found
through live search and their source fields can vary across hosts.

The implemented package at
[plugins/category-research](../plugins/category-research/README.md) follows the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification): a
root `plugin.json` manifest and `skills/category-research/SKILL.md` component.
The bundled core uses Python 3.9+ and its standard library, through a CLI or
`category_research.import_document`; another plugin can compose those entry
points directly. The package has no MCP component.

Discovery uses the agent's available tools for public sources.
The importer archives a supplied versioned raw collection document; current UK
chocolate inputs use `draft-raw-1`. The importer archives supplied records; market
discovery and its coverage report remain the calling agent's responsibility. Its
[import contract](../plugins/category-research/skills/category-research/references/import-contract.md)
defines the implemented envelope, exact preservation of source bytes, arbitrary
fields, failure reporting, image retrieval and adding captures to history. Native
installation and execution in multiple harnesses have not yet been tested.

Collection package `0.2.0` adds `category-research-sections-2` source-field
presence reporting. The caller can supply root `collection_sections`, a map of
section names to source information key markers; `{}` disables tracking. Omitted
configuration tracks description, prices and availability. Ingredients,
nutrition, materials, dimensions or other category sections are selected only
when applicable. Reports/captures save the chosen section configuration and
unknown statuses; a present field is not proof of complete or correct content.
This metadata does not filter raw fields or change the `category-research-raw-1`
archive layout, identities or original capture history. Legacy ingredient status
counters are emitted only for explicitly requested ingredient tracking.

## 3. Data contract

The raw archive, derived interpretations and normalized model inputs have distinct
contracts. A physical product can have multiple sources and prices across
retailers and dates; sections 3.1.2–3.3 define listing identity, relationships and
price context.

### 3.1 Raw archive for each product

The archive uses a current product index, immutable source/image artifacts, and
timestamped history. The implemented plugin layout is:

```text
collections/<category>/<market>/products/<product_id>/
    product.json
    sources/
        <capture_id>/<artifact_number>.<source_format>
    images/
        <capture_id>/<image_id>.<original_extension>
    history/
        <capture_id>.json
```

For the chocolate example, category and market directory identifiers may be
`chocolate` and `uk`. Equivalent bundles may be delivered by another harness;
the directory layout must not become a dependency on a particular host path.

`product.json` uses the minimal envelope below and extensible information that
can vary by product. Preserve conflicting source statements with their own
provenance. Identify normalized labels, visual interpretations, summaries, OCR
transcriptions and computed unit prices as derived, with supporting references;
retain the original text, reported prices and images alongside them.

Keep retrieved original pages or structured content in `sources/`. Captured text
may accompany it, labeled as original text or generated extraction. If only text
was accessible, preserve it and record the missing original page. Keep original
image bytes and formats, including available packaging panels, in `images/`. Record unavailable
images and panels explicitly; substitutions cannot establish original evidence.
SHA-256 is the proposed artifact hash algorithm.

Add immutable source/image artifacts and append timestamped collection records
in `history/`; `product.json` provides the current index. Preserve earlier
evidence and conflicts when adding captures or changing an analytical schema.
Capture timestamps describe collection activity, not how long a price was valid.
Retain any stated offer dates separately.

The [JSON illustration with five products](../examples/collections/uk-chocolate-five-products.json)
with `draft-1` fields is a narrow derived illustration, not a canonical raw
schema, complete taxonomy or implemented plugin contract. Its reconstruction
cannot establish original historical page/image captures.

| Collection record | Minimal content and preservation rule |
| --- | --- |
| Study envelope | Study ID, category, market, scope/boundaries, collection window, source scope, and envelope version. A complete analytical profile is not required. |
| Product envelope | Local product ID, category/market, available source identifiers and identity reported by the source, artifact references, and collection history. Keep identity matches provisional when ambiguous. |
| Product information | As much relevant source information as can be captured: original fields/sections, reported values/units, descriptions, ingredients or other category information, prices/offers, packaging and promotional claims, with source/section references. Preserve fields beyond current taxonomies and pricing predictors. |
| Raw source/image artifact | Original content, source or image URL, associated product/source, publisher/retailer, capture timestamp/timezone, retrieval method, content type, relative path, hash and declared capture limitations. |
| Collection record | Run ID, capture time, sources/artifacts added, outcomes, missing information or capabilities, and references to retained history. |

### 3.1.1 Public dataset publication policy

Raw collection uploads use the versioned `rgc-text-evidence-1` export policy.
This policy applies to every category/market under `data/collections/`, including
future studies; chocolate and the UK are examples, not export filters. Public
publication is a filtered derivative of the local raw archive. Local image and
source preservation requirements in section 3.1 continue to apply.

The Hugging Face dataset also hosts separately published silver snapshots and
analytical contracts. [Dataset contract storage](data/dataset-contracts.md) defines
their immutable references, caches and publication behavior. Contract publication
preserves existing raw export and silver files. It neither rebuilds silver nor
establishes reviewed observations or model readiness.

Silver snapshots use immutable `silver/chocolate/uk/<dataset-version>/` paths;
`silver/chocolate/uk/latest.json` selects one with its manifest checksum and
readiness state. Coverage/value-frequency and verification reports use
`analysis/chocolate/uk/<dataset-version>/` and record immutable input provenance.
Each snapshot keeps its exact contracts; a historical snapshot does not adopt
new contract releases. Publication verifies content hashes and preserves prior
raw exports and snapshots.

| Material | Publication rule |
| --- | --- |
| `products/*/product.json` | Include complete original records: source facts, prices, ingredients/nutrition where available, unknown fields and fields specific to a source, identities, and provenance. |
| `products/*/sources/` and `products/*/history/` | Include original text, HTML, JSON, and losslessly compressed text evidence and immutable capture histories. |
| `catalogs/`, `discovery/`, and `runs/` | Include text/structured discovery evidence, original catalogues, collection inputs, failure evidence, and run reports for reproducibility. Exclude executable collection scripts and runtime files. |
| Study `README.md`, `coverage.json`, and `archive-verification.json` | Include available descriptions, coverage/missingness, and original integrity reports. Label original archive checks as historical results, not validation of the filtered export. |
| Image URLs, captions, source roles, hashes, retrieval details, and recorded paths | Retain these metadata in original records; explicitly declare image files omitted. |
| `products/*/images/`, other image files, and image bodies disguised as responses | Exclude all image payloads, including failed response bodies inside image folders. |
| `transfers/` | Exclude the entire HTTP transfer cache, including cache metadata files; preserve retrieval details already present in product/source records and inventory omitted cache paths. |
| Hidden/runtime files, symlinks, credentials, executable code, unsupported binary/encoding formats, and other locations | Exclude from the evidence allowlist and record the omission reason. Never publish other files under `data/`, such as unrelated workbooks. |

The exporter validates supported evidence as UTF-8 text (or UTF-8 text compressed with gzip), rejecting binary content even when its extension looks textual.
It preserves accepted original bytes, wording, language, reported values, and
source URLs exactly. It does not translate evidence, silently fill missing
ingredients, normalize prices, deduplicate product identities, or rewrite local
raw records. Unsupported encodings stay local and are disclosed in the manifest;
they must not be silently represented as included evidence.

Publication consists of a root dataset card, a `products.jsonl` index, a root
export manifest, and losslessly compressed
`evidence/<category>/<market>.tar.gz` bundles. Each index row represents a source
product/variant record, not a verified distinct physical product. Category,
market, product ID, source/name/brand where available, capture metadata, original
record path, and bundle path are directly indexable. Arbitrary identity and
fields for the latest information are encoded as JSON strings to avoid imposing a
analytical schema for a specific category. Full captures and legacy fields remain in
the original records. The loader's `train` split name is a convention, not a
reviewed modeling split.

Each evidence bundle contains its own `export-manifest.json`: an inventory of
included paths, byte lengths, and SHA-256 hashes plus all omitted file paths,
sizes, and reasons. Preserve raw references without rewriting historical
evidence. Extract bundles under one collections root to resolve included
paths relative to the archive. Consumers must consult the manifest for deliberately
absent image/cache paths; historical discovery paths on a local host
record provenance and cannot supply portable download links. Original reports that count local images must not
be presented as counts of uploaded images. The dataset card describes these
limitations and does not invent a license for source material from third parties.

`scripts/publish_collections.py` implements this policy. It automatically
discovers category/market studies with product folders, builds a deterministic
export under ignored `data/huggingface-export/`, and uploads only its explicitly
managed files to a public Hugging Face **dataset** repository. Repeated exports
of unchanged collections produce identical bytes. Uploads use a cached Hugging Face token or one provided
through the environment; tokens must never be stored in source
files, manifests, or dataset cards. Validate local bundle contents, preservation,
omissions, and checksums before publication, then verify the remote managed files
and public visibility. Upload cadence is independent of this export policy;
publication follows the authorized task and no scheduled job is configured.
When a schema changes, the calling agent must finish the local versioned changes,
rebuild, validation and impact comparison, then present the detailed
[release review summary](decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
and wait for user review and authorization of that exact Hugging Face commit.
The summary covers contract/field changes, evidence and rationale, effects on
mappings/units/scopes/prices/predictors, before/after coverage and eligibility,
checks and limitations, and the target repository/revision and managed files/
hashes. Local schema decisions need no user sign-off. The calling harness owns
this review step; the current exporter does not implement a review UI or enforce
an approval gate.

### 3.1.2 Raw and combined silver responsibilities

Raw preservation and combined Silver own the processing responsibilities below.
The [stage descriptions and data flow](data/chocolate-silver.md#stage-descriptions)
use **bronze** as a presentation name for raw and show the implemented
immutable Parquet **Gold** training interface downstream of Silver. Section 10
and the [Gold guide](data/chocolate-gold.md) define its contracts and readiness
boundary; current chocolate has no eligible inputs or fitted model.

| Layer | Responsibility |
| --- | --- |
| Raw, `data/collections/chocolate/uk` | Preserve product indexes, arbitrary fields, source/image artifacts and immutable history under section 3.1. |
| Silver, `data/silver/chocolate/uk` | Verify raw index/history consistency; deduplicate exact seller listings; apply schema/unit/vocabulary standardization; normalize supported prices; apply reviews supported by evidence and model eligibility; report provenance, missingness, exclusions and readiness. |

`uv run --script scripts/build_chocolate_silver.py --archive-root data/collections`
builds silver in one command with pandas 2.2.3. Direct Python execution requires
that dependency in its interpreter. Deduplication and standardization are internal operations of
this layer. The build reads raw and writes one silver dataset directly.
The [silver guide](data/chocolate-silver.md) owns its CLI, output contract and evidence
resolution; the [schema guide](data/chocolate-schema.md) owns attribute meanings,
reviews and the pricing handoff.

Deduplicate exact `source_key` + source URL hostname + `source_product_id` +
`source_variant_id` matches within one selling source. Missing source identity
does not justify a match, and names, brands, GTINs or weights do not cause a
merge. Different shops retain unique listings and prices. Choose the first
member raw folder ID in sorted order as the canonical listing ID, retain all
members in `source_listing_ids`, and emit `listing-aliases.jsonl`.

The exact seller listing identity and `source_key` must stay consistent across
captures in one raw folder. Reject a folder with changed identity from accepted
inputs, report the invalid record and partial snapshot, and preserve its raw
evidence. Separate raw listings are required rather than assigning historical
captures to a different seller or product/variant. The shared integrity rule also
applies to standalone deduplication and cleanup helpers.

Silver `source-listings.jsonl` retains every original capture object, original
`raw_record.product_id`, source value, timestamp and history/artifact reference.
`products.jsonl` supplies the typed analytical interpretation rather than
replacing those captures. `brand/`, `retail/` and `unknown/` each expose products,
prices and source listings, independently of product brand identity.

Source/image bytes and immutable history files remain in raw. Resolve silver
assertions/prices through capture IDs and pointers in `source-listings.jsonl`,
then follow artifact/history paths against the raw collections root. Raw
snapshot and silver dataset versions remain distinct; the silver manifest
records input, contract, implementation, review and output fingerprints. Input
index/history consistency does not newly verify every original artifact byte.

The standalone deduplication and standardization CLIs, and the earlier cleanup,
provide compatibility and diagnostics with their own helper outputs. Report
seller counts and market coverage under section 2.1.

The canonical build uses pandas 2.2.3 for exact seller grouping, stable role
partitions, coverage/exclusion counts and derived row envelopes. Original source
values remain opaque Python objects; nullable seller keys keep their meaning.
The combined API defaults to pandas and the CLI selects it explicitly. Component
builders default to the standard library for compatibility; the portable package
keeps its independent runtime. Install the locked development environment for
direct Python calls, or use the CLI's PEP 723 dependency metadata through `uv`.

`processing_runtime` records backend, Python implementation/full version and
pandas/NumPy versions in the manifest and quality report. Runtime and table-helper
hashes contribute to derived fingerprints. A changed runtime produces a new
snapshot without rewriting original captures or previously published outputs.

### 3.2 Later analytical schema and feature classification

After broad collection, review fields, units, claims, product forms, identity and
missingness across the corpus. Derive a complete schema for that category scope
and its comparisons; version and extend profiles/mappings as new information
arrives. Preserve original fields and unclassified claims under section 3.1.

Keep derived product variants, classified features and price observations as
distinct records in the later analytical dataset:

| Record | Required content |
| --- | --- |
| Category profile | Category ID and profile version, typed attribute definitions, applicable units, identity and rules for product families, definitions of comparable groups, extraction guidance, and supported price/normalization bases. |
| Category study | Category/profile version, market, included/excluded product forms, comparable groups, collection window, currency and price definition, quantity/normalization basis, source coverage. |
| Product variant | Unique source listing ID, category/profile version, source identifiers where available, source role and seller identity separate from product brand, optional reviewed variant/family relationships, product name, variant, product form, and applicable selling unit/quantity information. Edible weight and pack count belong to profiles where relevant. |
| Product information | Derived attributes for the category with types, units, raw source references, and mapping/schema version. Ingredients, cocoa percentage, nutrition, and dietary information are chocolate examples. Missing information remains missing. |
| Source evidence | References to preserved source/image artifacts, source URL, collection time, and the location supporting each extracted feature. |
| Classified feature | Feature name, normalized value, value type, evidence reference, extraction method, review status, and schema version. |
| Price observation | Product ID, source/retailer, observation time, currency, displayed selling unit price, available regular price, promotional status/mechanics, applicable quantity and units, normalized price and basis where used, availability, and known tax basis. |
| Model version | Saved study, data, design, fitted parameters and evaluation under the release metadata contract in section 5.3. |

Follow the category profile for analytical identity. Chocolate variants differ
by flavor, ingredients, weight and pack configuration; other categories define
their own attributes. Use source identifiers and review ambiguous matches.
Apply the exact seller deduplication rule in section 3.1.2. Reviewed `variant_id`
and `family_id` can link designs and related sizes for validation while retaining
distinct seller rows.

Keep product brand separate from seller identity. Classify selling sources as
`source_role: brand`, `retail` or `unknown` and expose direct brand stores and
retailers separately. Resolve seller roles from source evidence; product brand alone cannot establish
them. Unresolved roles remain unknown.

The derived profile defines extensible feature types, units, vocabularies and
unknown rules; each dataset records its profile version. The following chocolate
families illustrate a category profile:

| Feature family | Examples and classification rules |
| --- | --- |
| Identity | Brand, product range, chocolate type, product form. |
| Composition | Cocoa percentage, nut presence and type, fillings, fruit, caramel, other inclusions. A "may contain nuts" allergen warning is separate from nuts as an ingredient. |
| Claims and certifications | Fairtrade or another specifically named scheme, organic, vegan, single origin. Keep general fair trade wording separate from a named certification mark. |
| Size and packaging | Net weight, pack count, wrapper/box format, visible material descriptions, gift presentation, packaging claims. Unknown material must not be guessed. |
| Promotional emphasis | Exact visible claims and their normalized themes, including origin, craftsmanship, sustainability, flavor, quality, or gifting when actually stated. |

Capture every identifiable packaging and promotional emphasis with supporting
text/image references. Retain new claims for review and schema extension.

For presence/absence attributes, distinguish `present`, `absent`, and `unknown`.
Missing text or unreadable packaging is `unknown`, not evidence of absence.
Record whether a claim appears on packaging, in retailer copy, or in other
promotional material. A seller's claim is an observed claim; it does not alone
verify certification, composition, or product quality.

Collection may combine structured source retrieval, page/text capture, and image
retrieval. Later analytical extraction may combine text extraction, image/OCR
extraction, classification, and manual review. Preserve the originals throughout.
The exact tools remain undecided. Classification accuracy must be evaluated
against a reviewed sample; a confidence score alone is insufficient.

#### Compatibility UK chocolate cleanup implementation

The earlier `scripts/clean_chocolate_data.py`, implemented in
`scripts/chocolate_cleanup/`, reads raw with draft profile `uk-chocolate-clean-1`
and writes a helper dataset for compatibility and diagnostics. The
[cleanup guide](data/chocolate-cleaning.md) owns its CLI, complete outputs, seller
partitions, evidence resolver, current/historical flags and review contract.
Repeated imports of an identical price observation combine its evidence.

Its optional `chocolate-reviews-1` decisions cover identity, scope, group,
quantity and prices. Initial eligible inputs require reviewed regular GBP
consumer prices on `consumer_tax_included` basis, observation time with timezone
and positive edible mass. Price review explicitly confirms `regular_price`,
`currency`, `tax_basis` and `observed_at`; incomplete reviews remain excluded.
Unknowns, unsupported source shapes, legacy records and unresolved decisions
remain in coverage/review outputs. The helper rejects overlapping raw/output
directories and preserves raw artifacts. It fits no regression; `release_ready`
stays false pending classification evaluation and modeling validation under
sections 3.2–5.

#### Defined chocolate schema inside silver

The initial schema is `chocolate-schema-1`. Its `profile.json`,
`source-mappings.json`, `product.schema.json` and `model-design.json` are
authoritative under `contracts/chocolate/` in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
The [dataset manifest](../schemas/chocolate/dataset-contract.json) pins an
immutable dataset commit, every file's SHA-256 and the contract versions. The
files define tracked attributes, source aliases/normalization, standardized shape
and the initial training/insight contract respectively. The
[schema guide](data/chocolate-schema.md) documents their application and extension.

Default builds resolve that pin into the ignored `data/contract-cache/`, verifying
file lengths and hashes before reuse. A cache miss requires network access;
`--offline` fails if pinned files are missing and never selects a moving revision.
An explicit `--schema-root` supports custom local contracts. See
[dataset contract storage](data/dataset-contracts.md) for fetching and provenance.

The schema tracks over 100 attributes across identity, composition, dietary claims,
certification claims, nutrition, origin, packaging, processing, storage,
marketing, and quantity. It defines types, units, controlled values, scope,
qualifiers, and standardization rules. This is a broad initial tracking schema,
not a claim that all fields can already be extracted accurately or used as
independent predictors.

Profile/validator attribute types, units, enum/list vocabularies and numeric
bounds must agree in nullable value branches and branches conditioned on known status. The runtimes
support the explicit typed template and reject unsupported value
constraints; they do not execute arbitrary JSON Schema. A known value valid for the category outside the selected model domain remains in silver, with its candidate
excluded as `model_predictor_outside_design_domain:<attribute>` rather than
aborting the build or coercing the value into a reference category.

Silver applies these contracts after the raw verification and deduplication in
section 3.1.2. The standalone `standardize_chocolate_data.py` helper accepts a
verified deduplicated snapshot for compatibility and diagnostics.

Every attribute has a typed value and explicit `known`, `unknown`,
`not_applicable`, or `conflict` status, declared unit/scope/qualifier, extraction
method, evidence references, and review status. Unknown and conflict values are
null. Presence and absence are supported values only when evidence establishes
them; missing source copy remains unknown. Source assertions, unmapped claims,
and history remain available for review instead of being silently dropped.

Standardization must distinguish nut ingredients from warnings about cross contact,
named certification claims from generic ethical wording, cocoa minimums from
exact percentages, percentages for the chocolate component from those for the
whole product, edible mass from shipping weight, source origin claims from the
sales market, and reference prices from regular selling prices. Unknown or
conflicting mappings enter the review queue. Production and packaging facts
require supporting evidence rather than deductions from quality adjectives.

The [silver guide](data/chocolate-silver.md) owns the complete output contract,
including products, assertions, observations, candidate/eligible rows, reviews,
quality/reproducibility reports and exact contract copies. Build coverage and
exclusion reasons belong in the quality report. Follow the
[documentation policy](documentation-policy.md): publish changed dataset
contracts, update manifest pins/versions and synchronize this specification,
schema/silver guides and lifecycle plan, including intention when scope changes.

The model design selects candidate predictors. Training inputs require reviewed scope,
comparison group, edible quantity, physical/family relationships, feature
interpretations, and regular GBP consumer prices with confirmed tax basis and
observation time. Selected predictor and mass reviews must cite evidence from
the price observation's capture, with supported product scope and qualifiers;
later recipe or claim statements do not automatically classify historical
observations. The `chocolate-schema-reviews-1` review format supplies
these decisions with reviewer, reason, and valid capture/pointer evidence.
Current facts derived from sources remain unreviewed and tax basis is unresolved, so
the initial build has no eligible training rows. Apply the readiness requirements
in sections 4–5 before fitting.

`scripts/analyze_chocolate_schema.py` provides a separate read-only pandas
analysis of a downloaded silver snapshot. It verifies the SHA-256 hashes of
`products.jsonl`, `profile.json` and `model-design.json` against that snapshot's
manifest and atomically writes a JSON report outside the silver input directory
and separate from any supplied profile or manifest. The caller supplies an
immutable dataset revision and can supply an analysis date; these provenance
labels do not independently establish a remote download. Every profile field
appears in coverage counts, with known, unknown, conflict and not-applicable
states and review status kept separate. Value frequencies count exact selected
known values and show both all-listing and known-listing denominators. Numeric
quantiles also retain scope and qualifier; text excerpts describe exact string
repetition rather than semantic ingredient or claim popularity.

Source coverage, variant repetition, unresolved aliases and extraction defects
limit descriptive frequencies. An unknown claim does not establish absence,
and zero coverage does not establish that a schema concept is irrelevant. These
reports do not change taxonomy, raw evidence, silver snapshots, review status,
model eligibility or release readiness. An optional pinned portable chocolate
profile comparison checks definitions only; it does not describe frequencies
in a portable snapshot. The [schema guide](data/chocolate-schema.md) owns its command
and report details.

#### Portable processing and maintenance from captures to mappings

The standalone [category-processing plugin](../plugins/category-processing/README.md)
packages the workflow after collection under Agent Plugins 1.0.0. Python 3.9+
using its standard library accepts a compatible raw archive and five aligned
profile contracts, then writes silver under section 3.1.2. Packaged profiles
resolve immutable manifests under `plugins/category-processing/profiles/<category>/`
to authoritative files in dataset `contracts/category-processing/<category>/`.
Downloaded contracts occupy ignored caches; a cache miss requires network access,
verified caches support offline reuse, and `--offline` fails for missing pinned
files. Explicit `--profile` directories support custom local profiles.

The package runs independently of repository sibling modules and collection
plugin installation. Chocolate and a small starter for structured coffee inputs
demonstrate category configuration; extraction support depends on the profile
and source format. Native installation and execution in multiple harnesses
remain unverified.

Profile loading checks validator category/market constants and selected predictor
type/unit compatibility; declared model vocabularies must be subsets of category
vocabularies. Contract drift fails before publication. Valid category observations
outside the selected model domain remain in silver and are excluded only from
model candidates.

Processing package `0.3.2` includes the `init-profile` command with explicit
`--input <definition.json>` and `--output <new-profile-folder>` arguments for
`category-processing-definition-1`. The
definition explicitly declares category/market, all four semantic versions,
typed attributes, structured source pointers, source roles, comparable-group
attribute, quantity, target currency/unit/base, selected predictors and reviewed
tax basis. It generates and validates the five local working contracts before
creating a new directory, rejecting an existing destination. No food attributes or
bundled profile are prerequisites. Local generation is separate from dataset
publication and does not create a manifest pin. Keep working copies and generated
payloads outside tracked analytical-contract source; authoritative contracts
remain in Hugging Face. After the required release review, publish changed
contracts, verify the resulting immutable revision and update affected Git
manifest hashes and semantic versions together. Definitions are authored within
the current authorized task; source content remains evidence and cannot authorize
profile changes.

Portable raw lookup uses the collection format's normalized category/market
directory slugs, with exact safe-name fallback for other compatible producers.
Envelope values still match the profile exactly; normalization does not rewrite
category/market identity or stable seller UIDs.

Structured quantities may use items, packs, mass, volume, length or time, with
explicit numeric evidence and declared multiplicative `unit_conversions`.
Structured minor-unit money uses positive `price.minor_unit_factor`; legacy
recipes retain divisor 100, while new minor-unit definitions must choose it.
Major-unit money is unchanged. Model `eligibility.allowed_tax_bases` selects
exactly one resolved basis and must match a supplied `target.tax_basis`; omitted
legacy policies select `consumer_tax_included`. Tax or currency conversion is
not inferred. Missing quantity and unreviewed context still exclude model inputs.
Structured money uses positive plain decimal amounts with explicit currency;
locale punctuation and symbols do not infer conversion. Legacy £/GBP prefixes
are accepted only for explicitly GBP observations. Invalid money stays null in
derived prices, with original values preserved.
The generic engine consumes configured structured fields; arbitrary source
free-text extraction and validated models for every category are not implemented.

Processing package `0.3.2` includes structural discovery beyond configured extraction
coverage. It scans meaningful unhandled subtrees under `/raw_record`, preserving
full typed values, stable source-field IDs, seller/capture context and exact JSON
pointers in `discovered-fields.jsonl` (`category-unmapped-fields-1`). Semantic
scope, unit and qualifier remain unresolved. Optional recipe `discovery` settings
control enabled status, roots and additive exact-path exclusions; identity and
provenance metadata have fixed exclusions. The quality report records effective
coverage and counts. Discovery also runs after a capture extraction error and
does not alter accepted product facts, eligibility or model predictors.

Discovered fields join evidence-backed mapping batches and a generated
`schema-extension-review.md` worksheet. The worksheet separates agent hypotheses,
competing interpretations, evidence, all five contracts, version effects and
accept/reject/defer decisions. `summarize` includes discovery artifacts when the
source snapshot's manifest covers them and remains compatible with older
snapshots. Reusing a packet for an older snapshot removes obsolete generated
discovery files; unrelated files are retained and unsafe paths fail before writes.
Source-derived labels and excerpts are escaped JSON code spans, while full typed
evidence remains in JSONL. Agent rationales belong in separate durable proposal documents,
preserving immutable generated evidence. The initial
[seller review metrics](data/schema-proposals/seller-review-metrics.md) and
[selling plan terms](data/schema-proposals/selling-plan-terms.md) proposals are pending
agent assessment; discovery alone accepts no schema extension. Automatic prose concept
investigation, a proposal/decision registry and cross-snapshot proposal comparison
remain future improvements.

Stable `seller_uid` derives from category, market, source key, host, source product
and variant independently of the canonical listing alias. Different sellers stay
unique; unresolved identities stay separate. All original captures, aliases and
brand/retail/unknown partitions are retained. Portable chocolate uses
`chocolate-processing-schema-1` and `chocolate-processing-pricing-design-2` for its
seller envelope and generic target contract. Existing `chocolate-schema-1`
snapshots/CLI retain their own compatible versions; profile substitution must
preserve those snapshots.

Process with frozen mappings, then inspect generated evidence batches. The ledger
records input/content hashes, processing fingerprint and capture outcomes. The
CLI compares prior entries as new, unchanged, changed input, changed rules or
retry while rebuilding the full snapshot. Input identity/content and rules both
matter: mapping fixes can affect an unchanged capture.

Grouped batches retain evidenced field/value, scope, unit/qualifier, source
format/reason, frequency, distinct capture/listing counts and representative
capture IDs/raw pointers. Ordinary missing/null/unreviewed fields remain quality
gaps; evidenced new concepts can justify taxonomy review.

The skill guides the calling Codex harness in the current task to triage aliases,
new concepts, parser defects, missing data and conflicts. When maintenance is
requested, prepare a versioned diff, focused tests and impact review within that
scope. Under the standing
[agent-led maintenance decision](decisions/agent-led-schema-maintenance.md), the
agent may assess, accept, reject, defer and apply supported local changes without user
review, confirmation or approval. An identified agent may perform the required
evidence/eligibility reviews; reviewer, reason and capture/pointer requirements
still apply. Unreviewed data remains unreviewed until those checks are completed.
For a changed schema, the user reviews the completed release summary before its
Hugging Face commit, as defined in the publication policy; no intermediate
per-field approval is needed.
Keep source content untrusted, do not choose labels from observed prices,
and do not mutate a mapping during normalization. Accepted changes apply on a
subsequent rebuild of affected history, preserving seller UIDs, source evidence
and immutable model-training snapshots. Compare labels, conflicts, coverage and
eligibility before modeling. Automatic dispatch/scheduling, incremental execution
caching and selective migrations are not implemented.

The CLI prepares reviewed eligible rows with validation grouped by family,
encoders learned from training rows and frozen for validation, and design
matrices. Targets use `regular_unit_price`/`log_regular_unit_price` with a saved
basis defined by the profile; both starters use regular GBP/100 g. Regression and
uncertainty fitting remain subsequent work. The
[portable processing guide](data/category-processing.md) owns commands, versions,
outputs and workflow details; the [lifecycle plan](lifecycle/plan.md) records
package verification independently of data/model readiness.

### 3.3 Prices and comparability

Each category study defines currency, selling unit, tax/promotion basis,
quantities and normalization. Its profile may compare prices per item, pack,
mass or volume; edible weight and GBP per 100 g are chocolate choices.

Collection retains original price text, currency, quantities, and offers as
reported, even when their normalization or model eligibility is unresolved.
Computed prices belong to the derived layer and retain links to the originals.

For the current UK chocolate study, use collected displayed GBP pack prices as
the regular-price proxy and retain source tax/promotion metadata as limitations.
The earlier regular-price proposal remains a historical study contract.
For historical regular-price studies, if regular price is unobservable, exclude the observation from the regular price
model or use a separately defined analysis of displayed prices. A discount label
alone cannot establish regular price.

For this chocolate example, normalize by total edible weight:

```text
price_per_100g = pack_price_gbp / total_edible_weight_g * 100
```

Validate currency, positive price, applicable quantity units, and arithmetic.
Retain missing or ambiguous quantities in coverage reporting and exclude affected
observations from models requiring them. Preserve promotion mechanics, discounted
and regular prices distinctly; record paid shipping when observed.

Define comparable groups before modeling. Bars, assorted gift boxes, and baking
chocolate can have different pricing mechanisms even after mass normalization.
Use separate group models or group terms and supported interactions; report the
chosen comparison boundary.

## 4. Dataset readiness

Before fitting, report:

- Unique variants, related product families, brands, retailers, dates, and
  comparable groups.
- Coverage across feature values for the category, applicable sizes/quantities,
  and price ranges.
- Missingness, unknown labels, disputed matches, and extraction review results.
- Exclusions and their reasons, including inconsistent price or quantity data.
- Rare features, correlated features, and combinations absent from the sample.

Readiness requires enough independent products and variation for the intended
comparisons, with acceptable validation and uncertainty. A row count alone is
insufficient. A feature seen only in one brand may be inseparable from that brand's
effect even with repeated retailer listings. Mark such estimates unsupported,
combine levels transparently or collect more varied products.

Sampling and retailer coverage determine what population the model describes.
Without sales data, the model describes sampled listings; estimating a market
average weighted by sales requires sales data.

## 5. Pricing regression

The [UK chocolate model design](data/chocolate-modeling-design.md) consolidates the
initial cohort, baseline, hedonic and LightGBM architecture, feature handling,
validation, uncertainty and prediction contract. The
[LightGBM and explanation design](data/analysis/lightgbm-shap-explanation-design.md)
specifies TreeSHAP and grounded AI interpretation. These remain designs; no
pricing model has been fitted.

### 5.1 Initial model proposal

Start with a hedonic regression relating observed prices to measured product
characteristics. Select target, normalization and terms using the category
profile and comparable groups, then validate for that study. The proposed UK
chocolate target is the log of regular GBP price per 100 g:

```text
log(price_per_100g_i) = intercept
    + product_feature_terms_i
    + brand_term_i
    + size_and_pack_terms_i
    + retailer_term_i
    + collection_period_term_i
    + error_i
```

Use available variation to choose terms; a constant collection period does not
need a fitted time effect. For chocolate, include pack size terms because unit
normalization does not remove quantity discounts. Use the applicable
quantity/size terms for each category. Add interactions only when there is
adequate support and an explicit reason. Compare against a simple category/group
baseline and keep the formula interpretable.

Treat retailer as an explicit pricing context. Compare the same reviewed variant
across retailers on consistent date, channel, tax, membership and promotion bases
to distinguish retailer differences from assortment differences. Use retailer
fixed effects and supported interactions when differences vary by product
profile. The UK chocolate design includes a retailer diagnostic using matched
variants, plus validation and prediction intervals for each retailer. Report
conditional retailer price associations; hypotheses about different target
audiences require additional shopper or choice evidence. An unseen retailer has
no supported coefficient until collection, fitting and validation establish its
domain.

Specify reference levels for categorical features. Review rank deficiency,
correlation, sparse levels, influential observations, residual behavior, and
stability across sources and reasonable model choices. Account for dependence
between observations of the same product when estimating uncertainty.

For an established statistical use of this method, see the
[BLS explanation of hedonic quality adjustment](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm).
Applying it to UK chocolate is this specification's proposal and requires its own
validation.

The current executable preparation contract, `chocolate-pricing-design-3`, is
in dataset `contracts/chocolate/model-design.json`, pinned by the
[dataset manifest](../schemas/chocolate/dataset-contract.json). It selects
features and preprocessing from the typed schema. Retain useful tracking evidence
even when a field is sparse, redundant, unsupported or descriptive and excluded
from the model. Save the fitted design under section 5.3; standardization alone
cannot establish coefficients or a price premium. The consolidated research
design proposes a subsequent version for separate models with and without brand,
handling of optional features and calibration. Existing preparation commands
retain the published OLS preparation rules. The independent
[`lightgbm_without_brand` implementation](data/analysis/lightgbm-without-brand-implementation.md)
adds local experimental training, calibration and native TreeSHAP with an explicit
working configuration. It has fixture validation; its historical regular-price
Gold attempt had zero eligible rows and lacked four selected shared fields.
The refreshed current-price Gold needs explicit migration in this trainer. Full comparison, aligned contract
migration and real-data validation remain pending.

The proposed comparison includes LightGBM candidates with and without brand,
using the same target of log price, reviewed features, retailer contexts, family
weights and grouped splits as their hedonic comparators. Select settings and the
prediction champion through validation within the fitting partition, then freeze
each model before separate calibration and final testing. Retain hedonic models
for coefficient comparisons. Nonlinear predictions do not resolve confounded
attributes or unsupported retailers.

### 5.2 Feature contributions

For an indicator coefficient `beta` in a model of log price, report the estimated
percentage difference from its reference as `100 * (exp(beta) - 1)`, holding other
terms fixed. Report continuous features with their unit or an explicit input
change. With interactions, calculate the contrast for the actual product context.

For another target scale, use the corresponding model interpretation and
prediction contrasts in its declared units. Record that interpretation in the
model metadata.

Each result must identify its reference, sample support, uncertainty, and
conditioning variables. Contributions on the log scale are additive in log space;
percentage effects are multiplicative. Do not present percentages or currency
contrasts as additive shares of the final selling price. Use the explicit
allocation below for percentages of the final predicted price.

For a supported product profile, also express a feature contrast as the
difference between two predicted prices with the feature changed and all other
inputs held fixed. State both profiles and the selling unit basis of that currency
difference.

If two attributes cannot be distinguished in the data, say so. A Fairtrade term
may capture correlated brand, origin, quality, or retail positioning that the
dataset does not adequately measure.

For LightGBM, use exact TreeSHAP verified for the pinned versions to explain the
model's raw output on the log price scale. For the same frozen model and tree
count, its base value plus signed contributions must numerically reconstruct the
raw prediction. Contributions allocate
that prediction relative to the model explanation reference; they are neither
additive GBP amounts, causal premiums nor uncertainty intervals. Keep scenario
contrasts using complete predictions distinct from attribution.

An AI narrative may interpret a validated packet of predictions, SHAP values,
feature evidence and support limits. Deterministic code owns arithmetic. Require
traceable claims and validate references, numbers, directions and meaning; use a
fixed template if validation fails. Retain limitations from correlated
retailer/brand/claims and missing evidence. SHAP cannot establish shopper
segments, quality, demand or optimal price.

#### 5.2.1 Trait and trait-family percentages of predicted price

For each supported product prediction, report individual trait contributions
and one signed percentage per trait family of the final predicted price.
A trait family groups related product attributes, such as composition, dietary
claims, certification claims or quantity. It is distinct from the product
`family_id` used for identity, validation splits and training weights.

Use a versioned, exhaustive mapping from fitted inputs to traits and from traits
to families. Combine a trait's categorical encodings, transformations and
missing indicators before reporting its contribution. Include modeled brand
and selling context in named families so every fitted term is accounted for.
Fields excluded from the fitted model have status `not_modeled`, rather than
an estimated zero contribution. A modeled family with a computed zero retains
its zero percentage. Preserve signed cancellation within a family.

Start from a validated additive log-price explanation: `L = b + sum_j phi_j`,
where `L` is the frozen model's log prediction, `b` is its explanation reference
and `phi_j` is a trait's signed log contribution. LightGBM uses its TreeSHAP
reference and values. An additive hedonic model uses an explicit supported
reference profile, with term contributions equal to the fitted term differences
from that profile. Split a hedonic interaction term equally among its distinct
participating traits, recording that allocation convention before grouping.

Define a proportional allocation along the exponential price transformation:

```text
P = exp(L)
P_reference = exp(b)
d = L - b
k = -expm1(-d) / d       if d != 0; otherwise k = 1
trait_contribution_percent_j = 100 * k * phi_j
family_contribution_percent_g = sum_j_in_family_g trait_contribution_percent_j
reference_contribution_percent = 100 * exp(-d)
reference_contribution_percent + sum_g family_contribution_percent_g = 100
```

Here `expm1(t)` means `exp(t) - 1`, evaluated stably near zero. This convention
allocates the price difference `P - P_reference` in proportion to signed log
contributions and retains their cancellation when `d = 0`. The denominator is
the final predicted price `P`. These are allocated shares of a model prediction;
they are not price-scale SHAP values, causal effects, ingredient costs, observed
price shares or the percentile pricing score. Keep coefficient contrasts and
`100 * (exp(phi_j) - 1)` distinct from this allocation.

Present each trait family as its label and percentage, alongside a separately
labeled model reference percentage. A positive family percentage adds to the
reference price and a negative one subtracts from it. The reference can exceed
100% when the final prediction is below the reference; do not clip, take absolute
values or renormalize families alone to 100%. Unit-price and pack-price shares
are identical when both prediction and reference use the same product's quantity
conversion; the conversion does not add a second quantity contribution.

Retain unrounded values, model/explainer identity, reference profile or base,
trait/family mapping version and allocation method in the explanation packet.
Check both log reconstruction and the reference-plus-family total before display;
use a numerical tolerance and disclose display rounding. Failed, nonfinite or
unsupported explanations return unavailable contributions. Global mean absolute
importance is a separate measure and must not populate local price percentages.
This is a proposed output requirement; implementation and validation remain
pending under the subsequent model contract release.

### 5.3 Validation and model release

Keep product families together in the split, including repeated retailer listings,
duplicate observations and closely related variants. Learn preprocessing from
training data only, then use the same fitted policy in validation and prediction.
Document unknown levels, imputation and rejection of missing required inputs.
Validate on a later collection period for claims about future prediction, and
hold brands out when evaluating support for unseen brands.

Save each model's category/profile, study and data versions, target price basis,
eligibility rules, actual fitted feature schema/list, missing value policy,
formula, fitted parameters, categorical reference levels, numeric scaling,
training/validation membership, supported ranges/domain, default prediction
context, target interpretation and evaluation. This metadata binds preparation,
prediction and insights to the released model.

Measure price error on the original scale and in the study's currency and target
units, for example MAE in GBP per 100 g for the UK chocolate study, and
relative error, alongside prediction interval coverage. Compare with the simple
baseline and report errors by supported group, size, brand, and retailer where
the sample permits. A high training R-squared is not a release criterion.

Exponentiating a log prediction does not automatically produce an expected
arithmetic price. Label the default exponentiated prediction as a geometric price
benchmark. A median
claim requires supporting assumptions; a mean requires a justified
retransformation adjustment and validation on the original scale.
Use prediction intervals for a new product, not only coefficient confidence
intervals.

Numeric release thresholds for coverage, extraction quality and prediction error
remain open decisions. Define them for the study before judging a model ready.
If the data or validation is inadequate, retain the dataset report and mark the
model experimental or unavailable for supported price testing.

## 6. Test the price of a new product

### 6.1 Inputs

Require category, market, comparable group, applicable selling unit/quantity
information, and the features required by the selected model. Use the same
category profile, vocabulary, and units as training.
Unknown values remain unknown. Optional inputs include an observed brand, a
supported retailer/time context, and a proposed selling price. When context is
omitted, use and display the model's documented default within its validated
domain. If no such default exists, require the relevant context before testing.

The proposed selling price uses the study's currency and declared selling unit,
on the same tax and promotion basis as the selected model. For UK chocolate this
is a GBP pack price for the described pack. Compare it with the corresponding
selling unit estimate; convert both prices consistently for comparisons of
normalized prices.

For an unknown brand, a proposed fallback is a separately fitted and validated
model without brand terms. Label it as a market benchmark with no specified
brand; other features can still absorb differences associated with brand. Use
the fitted term and state the reference for a known brand. Handle unsupported
brands, retailers, categories and feature levels explicitly; fabricated brand
coefficients or silent mapping to references are invalid.

### 6.2 Outputs

- Estimated price in the study's currency and target units, with the corresponding
  selling unit price and estimate type stated. For UK chocolate, this is GBP per
  100 g and the implied pack price.
- A prediction interval on the same price basis.
- Feature contrasts in the selected context relative to stated references.
- Individual trait contributions, one signed percentage of the final predicted
  price per modeled trait family, and a separate model reference percentage,
  using section 5.2.1's allocation and availability checks.
- When supplied, difference between proposed and predicted prices: `proposed - predicted`, and
  `100 * (proposed / predicted - 1)`.
- Data/model version, comparable group, and evidence/validation context.
- Flags for missing inputs, unseen levels, poorly supported combinations, and
  extrapolation beyond observed ranges.

Reject mathematically invalid inputs. For unsupported valid inputs, either
decline to produce a supported prediction or provide an explicitly experimental
estimate, depending on the model's documented domain policy. A design using
individually familiar features can still be an unsupported combination.

## 7. Deferred research on value for money and brand premium

Stage 3 begins with research into adjusted price comparisons. Consumer utility,
sensory quality and causal brand value require evidence beyond the planned
product/price dataset. Value for money and price differences associated with
brand are related, distinct quantities.

### 7.1 Methods to investigate

| Method | What it can estimate | Data required | Main limitation |
| --- | --- | --- | --- |
| Hedonic price regression | Conditional price differences associated with attributes and brands. | The planned product/price data, with comparable size, retailer, time, and selling conditions. | Omitted quality and correlated features affect estimates; a brand term is an association. [BLS](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm) provides a statistical application of hedonic regression. |
| Comparison of matched products | Price differences between products with similar measured attributes. | Products with overlapping features for the category and selling context; composition, claims, format, and size are chocolate examples. | Check balance and reject comparisons without overlap; unmeasured quality remains a possible explanation. This is a proposed product application of [Rosenbaum and Rubin's method for matched sampling](https://dash.harvard.edu/entities/publication/73120378-8487-6bd4-e053-0100007fdf3b). |
| Conjoint using choices / discrete choice experiment | Consumer willingness to pay for features and brand identities. | A separately collected consumer study with varied prices and attributes. | Sampling, experimental design, a meaningful option to make no purchase, and bias from hypothetical choices affect interpretation. See [Ben-Akiva, McFadden, and Train](https://eml.berkeley.edu/~train/papers/foundations.pdf). |
| Randomized experiment with brand information | The effect of disclosed brand information on preference or willingness to pay in the tested setting. | A new experiment holding the physical product constant while randomly varying brand information, with a monetary outcome if monetary premium is the target. | A blind taste ranking alone does not yield a monetary premium. Related evidence from a food category is [Bronnenberg, Dube, and Sanders' blind taste experiment with private labels](https://www.nber.org/papers/w25214). |

The last two options require new consumer or experimental data before use.

### 7.2 Candidate measures

In a model of log price with additive brand terms, the conditional price
difference associated with brand relative to an explicit reference brand is:

```text
brand_difference_percent = 100 * (exp(alpha_brand - alpha_reference) - 1)
```

This comparison needs adequate feature overlap and the same selling context.
With interactions, calculate the contrast at specified product attributes.
It is not proof of the price effect of renaming the same physical product.

A candidate indicator of adjusted price is:

```text
adjusted_price_indicator = log(benchmark_price / observed_price)
```

Define the benchmark using the same attributes and selling context, with an
explicit reference brand or stated brand distribution supported by the data.
Larger values mean a lower observed price relative to that benchmark. Use
predictions from models fitted without the evaluated rows, either with a held out
sample or across validation folds, so their own prices do not directly determine
their benchmark.

A percentile within a defined comparable cohort could map the indicator onto a
0-100 score. This is a proposed scoring convention, not a universal scientific
definition of value for money. The cohort, benchmark, price basis, and uncertainty
must be visible, and scores would be relative to that cohort.

Do not label `observed_price - predicted_price` as brand premium. That residual
also includes omitted attributes, selling conditions, and prediction error.
Refitting without brand does not create a price with brand value removed:
correlated attributes can retain differences associated with brand.

For a simple choice model with linear price utility, an attribute's marginal
willingness to pay can be estimated as:

```text
WTP_attribute = -beta_attribute / beta_price
```

This uses consumer choices rather than listed prices. The ratio requires an
identified price effect, uncertainty estimates, and an appropriate utility
specification; a price coefficient near zero makes it unstable. See the
[Goett, Hudson, and Train choice study](https://eml.berkeley.edu/~train/papers/RetailEnergy.pdf).

### 7.3 Research recommendation

Investigate prices adjusted for attributes and conditional brand comparisons
using the planned category dataset, matched product checks and uncertainty.
Assess price position with these methods. Design separate studies for consumer
value or causal effects of brand information, and keep scoring deferred until
its definition and evidence are agreed.

## 8. Acceptance scenarios for stages 1 and 2

The scenarios for chocolate illustrate one category profile. General
category and plugin conformance scenarios apply across supported studies.

| Scenario | Expected behavior |
| --- | --- |
| Collection starts before a complete category schema exists. | Accept minimal study scope, identity, and provenance; preserve broad source information and images without requiring a feature taxonomy. |
| A product page contains an unfamiliar relevant field or claim. | Preserve the original source and information specific to a source in the product bundle for later schema derivation. |
| A product is collected again with a changed price or claim. | Append timestamped source captures and collection history; preserve earlier evidence and identify the current JSON index. |
| A later schema normalizes a source field differently. | Create a versioned derived interpretation with evidence references; retain the original reported value and artifact. |
| A chocolate schema field cannot be supported by the available capture. | Emit its explicit unknown state and coverage/review information; do not infer absence or a feature value from missing evidence. |
| Raw chocolate records are processed into silver. | Verify the raw snapshot, deduplicate exact seller listings and standardize them in one build; retain original captures/aliases, preserve separate sellers and roles, and emit candidate rows separately from reviewed eligible inputs. |
| A schema, mapping, pricing gate, or model interpretation changes. | Update the affected machine contracts, version references, specification, schema/silver guides, and lifecycle plan together; run the documentation drift check. |
| A study uses a category whose comparison basis is price per item. | Preserve its original quantities and prices during collection; derive its analytical profile without requiring cocoa percentage, edible weight, or GBP per 100 g. |
| Another category is added. | Reuse the minimal collection/evidence envelope, then derive its own analytical profile, dataset, and validated model domain from collected information. |
| Furniture or another non-food category is collected. | Track general or explicitly selected source sections, preserve arbitrary specifications and evidence, and do not require ingredients or nutrition. |
| A new category needs processing contracts. | Generate and validate all five local working contracts from its explicit versioned definition without copying a bundled profile; preserve existing folders and publish authoritative contracts separately with immutable dataset references. |
| A category uses non-GBP per-item prices or a different minor-unit scale. | Use its declared currency, observed item count, normalization base and minor-unit factor; apply one reviewed tax basis and retain missing-context exclusions. |
| Any category's raw archive is published as a public dataset. | Apply `rgc-text-evidence-1`: include original product records, text evidence, history, catalogues, collection reports, and coverage; omit image bytes, transfer caches, and runtime files while retaining metadata and explicit omission manifests. |
| A binary image is stored with a filename that suggests text. | Exclude its bytes from public publication and record the reason; keep the original local evidence unchanged. |
| A public record references an omitted image or cache file. | Preserve the historical reference and provide its omission entry; do not claim the file is downloadable or that local archive verification verifies the public subset. |
| The same study request and evidence fixture are supplied through two supported harness adapters. | Both return valid collection envelopes and preserved raw bundles with compatible provenance meanings, original image/page handling, and explicit missingness; arbitrary fields specific to a source remain supported. |
| A harness cannot retrieve packaging images requested by the study. | Preserve packaging attributes supported by available text, mark unsupported attributes unknown, and declare the missing image capability/evidence and coverage limitation. |
| The same source product/variant is imported through multiple raw listing records. | Deduplicate the exact source_key + source URL hostname + source_product_id + source_variant_id match within that source; retain evidence and record the decision. |
| Silver groups duplicate raw listing folders. | Retain every original capture object, product ID, timestamp, source value and history/artifact reference in source-listings.jsonl, emit aliases, and keep typed interpretations and prices separate from those original captures. |
| The same physical variant appears at two retailers. | Preserve two unique analytical source listing records and their separate prices, even if an optional reviewed variant/family relationship links the design. |
| A brand's product is sold both directly and by a retailer. | Preserve distinct source listings and prices; expose partitions for direct brand stores and retailers while retaining product brand separately from seller identity. |
| A 200 g pack costs GBP 4.00. | Retain GBP 4.00 pack price and calculate GBP 2.00 per 100 g. |
| A listing supplies only a promotional price. | Preserve it as displayed price; do not invent a regular price. |
| Packaging is unavailable and retailer text omits Fairtrade. | Classify certification status as unknown. |
| A listing says "may contain nuts" but lists no nuts as an ingredient. | Preserve the allergen warning separately; do not infer a nut ingredient. |
| A visible packaging claim has no existing feature label. | Preserve the original image/text, claim, and source context for later schema derivation and classification review. |
| A certification appears only in one brand. | Flag identification/support limits; do not claim a separately established causal certification premium. |
| A dataset contains repeated offers and related sizes. | Keep product families together during validation on held out data. |
| A brand tests a supported new product. | Return price, prediction interval, feature references, and the selected model/context. |
| The design has an unseen brand or unsupported feature combination. | Use a validated, labeled fallback where available or report insufficient support. |
| A user supplies a proposed selling price. | Show its currency and percentage difference from the estimate. |
| A user supplies a GBP pack price while the model target is GBP per 100 g. | Convert consistently and compare pack price with the implied pack estimate on the same price basis. |
| A user omits optional selling context. | Display and use a validated documented default, or require context if none exists. |
| No reliable model passes the study's release criteria. | Show data/validation limitations and do not claim a supported price estimate. |

## 9. Decisions still to make

- The category boundaries and included product forms for the current UK chocolate
  study, and the category/market for subsequent studies.
- The first supported agent harnesses, adapter packaging, transport, capability
  mappings, and result/evidence delivery.
- Which sources are accessible and suitable, and what evidence can be retained
  under their access and usage conditions.
- The collection window and source/retailer coverage.
- Further chocolate schema extensions and extraction coverage, reviewed
  comparable groups, and confirmed quantity and consumer price basis before modeling.
- Coverage targets, extraction review plan, and numerical model release criteria.
- The delivery surface and implementation stack.
- Whether stage 3 will define value for money as a comparison of adjusted prices or
  include separately collected consumer utility/quality evidence.

Resolve these decisions before the corresponding implementation or release commitment.

## 10. Gold and the finalized training basis

The canonical chocolate architecture is raw → combined Silver → immutable Parquet Gold. Silver retains seller rows, evidence, reviews and eligibility. Gold copies `training-candidates.jsonl` to `training-data.parquet` and `model-inputs.jsonl` to `model-inputs.parquet`, with typed empty tables, Zstandard compression, manifests, logical row checks and exact contract/price/identity decision provenance. Existing snapshots cannot be overwritten with changed bytes. The [Gold guide](data/chocolate-gold.md) defines CLI, versions, review annotations and verified trainer handoff.

Historical regular-price models and the portable processing profiles use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive selling price, with `fallback_policy: reject`. Retain displayed/promotional/reference amounts as evidence; none substitutes for the target, and no tax guess or reverse discount is permitted. A separately evidenced regular amount alongside a promotional offer is supported. Chocolate normalizes GBP per 100g and logs it; other categories retain their declared currency and quantity basis. This fixed monetary basis supersedes earlier examples allowing excluded-tax model targets, without changing the preserved observations. Generated custom profiles retain this basis.

`chocolate-source-mappings-2` adds reusable `chocolate-product-identity-1` family taxonomy. Evidence-backed Codex assignments populate product and candidate IDs; related range grouping prevents validation leakage while seller rows and prices stay separate. Unknown/conflicting relationships remain in grouped review packets. Family assignment alone does not confer eligibility. Exact physical pack identity, reviewed scope, price/tax/time/availability, edible quantity and predictors remain separate requirements. [The schema guide](data/chocolate-schema.md) and [registry guide](../reviews/chocolate/README.md) own mapping details.

The experimental `chocolate-pricing-design-3` trainer reads verified Gold, with Silver compatibility, and saves immutable runs. It implements log-price OLS, family holdout, training-only encoders, support/rank/confounding gates and family-cluster bootstrap coefficient intervals. It validates eligible targets against the copied regular-price observations. Zero eligible rows yield a readiness report and no fitted artifact. This implemented experimental baseline does not establish release readiness or supersede the proposed LightGBM/SHAP research design. [The published contract release](data/analysis/gold-modeling-contract-release.md) documents the verified publication and exact changes.


Gold supports `chocolate-gold-bulk-eligibility-1` under an explicit user instruction.
Every candidate is emitted in both training views with `model_eligible: true`
and empty current exclusions. The exact parent snapshot retains the original
Silver decisions. Gold verifies all analytical values against that parent and
returns promoted flags to trainers. Original contract bodies, source evidence,
missing targets retain their source meaning. The current study derives a separate current-price target at training time under `current-consumer-price-1`. Gold's
report distinguishes override counts from original Silver quality counts and
records authorization without claiming evidence validation or fitted models.
See [bulk eligibility](data/chocolate-gold.md#make-every-gold-candidate-model-eligible).


## Current chocolate study price target

The user's 2026-10-03 instruction supersedes the regular-price requirement for
current chocolate training. Use `current-consumer-price-1`: collected current
displayed GBP price normalized by actual positive edible weight to GBP per 100 g,
with log scale for regression. Separate regular price, promotion classification,
review flags on the monetary observation and confirmed tax inclusion do not gate
target preparation. Original metadata stays preserved. The effective target is
recorded in model artifacts; no silent substitution into a historical study is
allowed. See the [modeling specification](data/chocolate-modeling-design.md#1-population-and-price-target)
and [project limitations](../PROJECT.md#limitations).

## Independent LightGBM with brand implementation

The [LightGBM with brand guide](data/chocolate-lightgbm-with-brand.md) owns the independent experimental trainer, explicit unpublished working experiment, grouped fitting selection, retailer calibration, native TreeSHAP and artifact integrity. The assigned estimator is implemented; fixture validation and real-data readiness are recorded in the lifecycle plan. Its historical rebuilt Gold has 2,134 candidates and zero eligible rows. The published current Gold marks every candidate eligible; this trainer requires migration to the current-price policy and shared handoff fields. Real fitting, authoritative handoff migration, comparator gates and supported release remain pending.

The user requested committing the task and publishing changed data. The Gold
publication contains 2,134 eligible candidates in both Parquet views, with its
full original parent. Immutable dataset revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7` and per-file checksums are recorded
in the [Gold reference](../schemas/chocolate/gold-dataset.json). All 25 files
were downloaded and byte/loader verified. Publication and fitting are separate;
current-price preparation remains the explicitly versioned training operation.

## Independent LightGBM without brand

The [without-brand implementation](data/analysis/lightgbm-without-brand-implementation.md)
provides its own regular-price working experiment, seeded family partitions,
family balancing, fitting-only grouped tuning, retailer calibration and native
raw-log TreeSHAP reconstruction. It saves immutable runs and supports verified
run loading. Synthetic validation is published separately from real fitting.
Current-price migration, full comparisons and released product scenario
interfaces remain pending. [Model maintenance](model-maintenance.md)
owns artifact storage in Hugging Face and immutable receipts in Git.

## 11. Independent family-weighted hedonic trainer

`--model-id hedonic_without_brand` selects an independent family-weighted log-linear estimator with an explicit local working contract and verified immutable Gold. It supports fitting-only grouped formula selection, known-brand rank probing without fitting another estimator, refitted family-bootstrap uncertainty, retailer-specific split conformal calibration, support rejection and final-test metrics. The existing equal-listing OLS command retains its contract. The [implementation record](data/analysis/hedonic-without-brand-implementation.md) defines the exact cohort, missingness, split, support, artifact and validation rules. The inspected historical regular-price Gold has 2,134 candidates and zero eligible rows; its contract also lacks three required cohort/core fields. No real fit or release is established. A coordinated dataset/portable producer migration and evidence reviews remain necessary before this working handoff can be supplied by the canonical pipeline.
