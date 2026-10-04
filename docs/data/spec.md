# Data specification

This specification owns collection, evidence preservation, processing, data
interfaces and publication requirements for the [data intention](intent.md).
The [overall specification](../spec.md) connects the feature specifications;
[model requirements](../model/spec.md) and [application requirements](../app/spec.md)
own their respective consumers. The [lifecycle plan](../lifecycle/plan.md)
records implementation and verification evidence.

The revised data preparation workflow from 4 October 2026 remains proposed.
Section 3.2 records the executed initial schema research and its unvalidated
proposal; no analytical schema or contract changed in that exercise. Existing
requirements, implementation results and historical snapshots below remain their
recorded operational
context while the approach is reassessed. Model planning remains outside that
data reassessment; the model specification retains the wider modeling scope.

Numbered sections retain their earlier identifiers for references. Initial build
and historical contract results refer to their recorded snapshots; subsequent
training results belong to the model specification. Follow
[AGENTS.md](../../AGENTS.md) for English authored content, writing style and
verbatim preservation of original source evidence.

## 1. Scope and delivery order

| Stage | Requested data outcome | Implementation status |
| --- | --- | --- |
| 1 | Collect original product information, images and prices through a portable plugin; provide another plugin for processing within each seller, category profiles, mapping maintenance and model preparation. | Raw collection, combined chocolate Silver/schema, model preparation and documentation maintenance are implemented and verified. The processing package passed package, isolated copy and collected data validation. Classification review/evaluation remains outstanding; model fitting and validation status belong to the model specification. |

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


Follow [AGENTS.md](../../AGENTS.md) for English authored content, writing style and
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
and qualify market coverage when the search is incomplete.
[Model dataset readiness](../model/spec.md#4-dataset-readiness) defines
readiness through independent variation and validation instead of a fixed count.

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
[plugins/category-research](../../plugins/category-research/README.md) follows the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification): a
root `plugin.json` manifest and `skills/category-research/SKILL.md` component.
The bundled core uses Python 3.9+ and its standard library, through a CLI or
`category_research.import_document`; another plugin can compose those entry
points directly. The package has no MCP component.

Discovery uses the agent's available tools for public sources.
The importer archives a supplied versioned raw collection document; current UK
chocolate inputs use `draft-raw-1`. The importer archives supplied records; market
discovery and its coverage report remain the calling agent's responsibility. Its
[import contract](../../plugins/category-research/skills/category-research/references/import-contract.md)
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

### 3.1 Bronze: the raw data layer

Bronze is the canonical raw-data layer: original collected records, source text,
images and other artifacts, source identities, timestamps and immutable capture
history. Collection writes Bronze; schema research reads its evidence; category
processing applies a generated schema to Bronze and produces reviewed Silver.
The layer sequence is **Bronze → Silver → Gold**. Existing raw archive paths and
format identifiers refer to Bronze, including `data/collections/` and
`category-research-raw-1`; layer naming requires no data migration.

The archive uses a current product index, immutable source/image artifacts, and
timestamped history. The implemented plugin layout is:

```text
collections/<category>/<market>/products/<source_key>/<product_id>/
    product.json
    sources/
        <capture_id>/<artifact_number>.<source_format>
    images/
        <capture_id>/<image_id>.<original_extension>
    history/
        <capture_id>.json
```

The collector groups known websites/storefronts by a stable source key, using 1–200
lowercase ASCII letters, digits, hyphens or underscores and beginning with a
letter or digit. It uses this key verbatim as the website directory. Missing,
null or empty keys retain their original JSON under `_unknown`. Product IDs
remain unique across the study. New listings use the grouped layout; imports
append existing legacy `products/<product_id>/` indexes in place. Readers,
verification and evidence export accept both layouts. Processing and archive
verification validate source-directory identity and report duplicate indexes;
processing excludes ambiguous listings.
The UK chocolate corpus was physically reorganized on 4 October 2026 at the
user's request. Complete product folders, including histories, source files and
images, now sit under their website directory. The move updates archive-managed
paths directly in product indexes, history metadata and run reports. Original
raw records and source/image bytes retain their content; index/history JSON
hashes change where their storage paths change. The active archive uses the new
locations directly, with no symlinks, redirects or lookup table for old paths.
Earlier exports or research inputs that recorded the old paths/hashes describe
the pre-move snapshot and require a fresh inventory to work with this archive.
Source grouping supports inspection and source mappings under the category's
shared analytical schema.

#### Why Bronze is grouped by website

Raw JSON structure follows the website and collection method. In the reviewed
chocolate records, Chococo combines Shopify variant objects with ingredient text,
Waitrose retains catalogue fields such as `source_weight_text` alongside product
page evidence, and ASDA retains labelled `source_sections`. A concept such as
weight or cocoa percentage therefore appears at different paths and in different
representations across websites.

Grouping product folders by their website/storefront supports three activities:

- **Schema research:** inspect representative records from every source, compare
  the concepts they contain, and propose common field meanings. Source groups
  help keep a large retailer's repeated structure from dominating the sample.
- **Extraction and review:** develop and test mappings against records with
  related structures, then inspect missing values and parsing failures for the
  affected source. Stored evidence remains available to distinguish a missing
  source statement from an extraction failure.
- **Maintenance:** when a website changes its pages or feed, locate the relevant
  records, compare captures and assess which mappings need revision. The same
  directory convention supports additional websites and product categories.

Use the website/storefront's `source_key` for this grouping. Product brands and
seller identities remain recorded separately. Research must sample different
product types, variants, collection methods and capture dates within each source
before reusing a mapping: a website can expose several structures over time.
The category analytical schema defines shared meanings; source mappings connect
each representation to those meanings. Directory grouping provides an inspection
boundary, while schema design, extraction and semantic validation remain explicit
steps in their respective workflows.

#### Product records and source evidence

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

The [JSON illustration with five products](../../examples/collections/uk-chocolate-five-products.json)
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

The [UK cat litter study](cat-litter-raw.md) uses this same raw archive
contract under `data/collections/cat-litter/uk/`. It retains seller listings,
native pack variants and attributed manufacturer pages with original prices,
availability and source claims. Source catalogue traversal and retrieval gaps
are reported separately from storage integrity. The study uses no analytical
profile and disables source-field heuristics with `collection_sections: {}`.
Image references remain in the raw evidence; image bytes were not collected.
The study's local text export follows section 3.1.1.

The capture predates integration of the source directory convention and uses
the supported flat `products/<product_id>/` layout. Its source keys and immutable
paths retain their original values; readers and verification accept that layout.

### 3.1.1 Public dataset publication policy

Raw collection evidence stays in local files under `data/collections/`.
The user requested local storage on 2026-10-03 and explicitly limited remote
removal to raw files. The `rgc-text-evidence-1` policy defines a verified local
text export for every category/market, including future studies. Local image
and source preservation requirements in section 3.1 continue to apply.

Hugging Face hosts derived Silver and Gold snapshots, analysis, model artifacts
and analytical contracts. Silver source-listings retain embedded original
captures by the user's explicit choice. [Dataset contract storage](dataset-contracts.md)
defines immutable references, caches and publication behavior. Contract
publication preserves other current dataset files; it does not rebuild Silver
or establish reviewed observations or model readiness.

Silver snapshots use immutable `silver/chocolate/uk/<dataset-version>/` paths;
`silver/chocolate/uk/latest.json` selects one with its manifest checksum and
readiness state. Coverage/value-frequency and verification reports use
`analysis/chocolate/uk/<dataset-version>/` and record immutable input provenance.
Each snapshot keeps its exact contracts; a historical snapshot does not adopt
new contract releases. The separately authorized original Silver retirement is
recorded below. Raw archive bundles, the root raw `products.jsonl` index and
root `export-manifest.json` were removed from the current public tree at
`06680d7248ccc4487726b9a97e59aa8f586fb54e`. The
[local storage receipt](analysis/chocolate-local-raw-storage-2026-10-03.json)
records exact paths, preserved local file hashes and verification of retained
content. The verified dataset card defaults to the existing Gold
`training-data.parquet` table, replacing the removed raw index. Its `train` split
remains a loader convention; model readiness and evidence review require their
own checks.

| Material | Local text export rule |
| --- | --- |
| `products/<source>/<product>/product.json` and legacy flat indexes | Include complete original records: source facts, prices, ingredients/nutrition where available, unknown fields and fields specific to a source, identities, and provenance. |
| Product `sources/` and `history/` directories in either layout | Include original text, HTML, JSON, and losslessly compressed text evidence and immutable capture histories. |
| `catalogs/`, `discovery/`, and `runs/` | Include text/structured discovery evidence, original catalogues, collection inputs, failure evidence, and run reports for reproducibility. Exclude executable collection scripts and runtime files. |
| Study `README.md`, `coverage.json`, and `archive-verification.json` | Include available descriptions, coverage/missingness, and original integrity reports. Label original archive checks as historical results, not validation of the filtered export. |
| Image URLs, captions, source roles, hashes, retrieval details, and recorded paths | Retain these metadata in original records; explicitly declare image files omitted. |
| Product `images/` directories in either layout, other image files, and image bodies disguised as responses | Exclude all image payloads, including failed response bodies inside image folders. |
| `transfers/` | Exclude the entire HTTP transfer cache, including cache metadata files; preserve retrieval details already present in product/source records and inventory omitted cache paths. |
| Hidden/runtime files, symlinks, credentials, executable code, unsupported binary/encoding formats, and other locations | Exclude from the evidence allowlist and record the omission reason. Keep unrelated files under `data/`, such as workbooks, outside the export. |

The exporter validates supported evidence as UTF-8 text (or UTF-8 text compressed with gzip), rejecting binary content even when its extension looks textual.
It preserves accepted original bytes, wording, language, reported values, and
source URLs exactly. It does not translate evidence, silently fill missing
ingredients, normalize prices, deduplicate product identities, or rewrite local
raw records. Unsupported encodings stay local and are disclosed in the manifest;
they must not be silently represented as included evidence.

The local export consists of a README, a `products.jsonl` index, a root
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
be presented as counts of exported images. The local README describes these
limitations and does not invent a license for source material from third parties.

`scripts/publish_collections.py` implements the local export policy. It
automatically discovers category/market studies with product folders and builds
a deterministic export under ignored `data/huggingface-export/`. Repeated exports
of unchanged collections produce identical bytes. It verifies bundle contents,
preservation, omissions and checksums and reports `export_bytes` as the total
managed output length. The former `--upload`, `--repo-id` and `upload_export`
interfaces reject raw publication before any side effect. The script has no
Hugging Face client dependency.

When a schema changes, the calling agent must finish the local versioned changes,
rebuild, validation and impact comparison, then present the detailed
[release review summary](../decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
and wait for user review and authorization of that exact Hugging Face commit.
The summary covers contract/field changes, evidence and rationale, effects on
mappings/units/scopes/prices/predictors, before/after coverage and eligibility,
checks and limitations, and the target repository/revision and managed files/
hashes. Local schema decisions need no user sign-off. The calling harness owns this review step for analytical dataset releases.

### 3.1.2 Bronze and combined Silver responsibilities

Bronze preservation and combined Silver own the processing responsibilities below.
The [stage descriptions and data flow](chocolate-silver.md#stage-descriptions)
show Bronze as the raw-data layer and the implemented immutable Parquet Gold
training interface downstream of Silver. Section 10
and the [Gold guide](chocolate-gold.md) define its contracts and readiness
boundary. The original chocolate snapshot had no eligible inputs or fitted
model; subsequent training status belongs to the
[model specification](../model/spec.md).

| Layer | Responsibility |
| --- | --- |
| Bronze (raw), `data/collections/chocolate/uk` | Preserve product indexes, arbitrary fields, source/image artifacts and immutable history under section 3.1. |
| Silver, `data/silver/chocolate/uk` | Verify raw index/history consistency; deduplicate exact seller listings; apply schema/unit/vocabulary standardization; normalize supported prices; apply reviews supported by evidence and model eligibility; report provenance, missingness, exclusions and readiness. |

`uv run --script scripts/build_chocolate_silver.py --archive-root data/collections`
builds silver in one command with pandas 2.2.3. Direct Python execution requires
that dependency in its interpreter. Deduplication and standardization are internal operations of
this layer. The build reads raw and writes one silver dataset directly.
The [silver guide](chocolate-silver.md) owns its CLI, output contract and evidence
resolution; the [schema guide](chocolate-schema.md) owns attribute meanings,
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

The dedicated [category-schema skill](../../plugins/category-processing/skills/category-schema/SKILL.md)
owns raw research, field meanings, uncertainty and semantic checks for initial
creation of a new analytical schema. It delivers the field catalog, source
references, rationale, coverage and unresolved decisions. It can propose or
finalize the initial schema according to the task; no processing runtime, model
specification or fixed file count is required.

The [2026-10-04 Bronze reconstruction](schema-proposals/chocolate-bronze-reconstruction-2026-10-04.md)
records an executed initial-creation exercise: 3,743 latest captures from 24 sources
inventoried, 97 distinct listing summaries/targeted examples inspected, a fresh
75-field proposal frozen before reading the existing profile, and all 103 old
attributes compared. The proposal has documented omissions and lacks executable
contracts or extraction validation. Existing contract versions remain in force.

Category-processing begins after two inputs are available for the same category
and market: readable preserved raw records and a generated initial schema catalog.
If raw data exists and the schema is missing, invoke category-schema and complete
that handoff first. If raw data is unavailable, route to collection. An empty
raw directory or a schema-design plan does not satisfy the entry conditions.

Processing configures mappings/extraction and serializes the generated catalog
into `profile.json` and `product.schema.json`. It owns executable validation,
evidence review, mapping/parser maintenance and the reviewed Silver output.
Model design, predictor selection, training-input preparation, family splits,
encoders and design matrices belong to the subsequent Silver-to-Gold stage.
The [downstream procedure](../../plugins/category-processing/skills/category-processing/references/silver-to-gold.md)
owns those steps, with model consumer requirements in the
[model specification](../model/spec.md). Silver retains existing evidence review
and eligibility decisions.

The portable generator and loader still require all five aligned files, including
`model-design.json`, and its Silver runtime writes legacy training views.
`prepare-model` remains a compatibility command for downstream use and does not
export Parquet Gold. These are implementation limitations, not additional skill
entry conditions. Reuse existing authorized profiles when available; do not
invent a model target or predictors to begin processing. A new schema without the
legacy design needs a future runtime migration before that engine can apply it.
No analytical payload or runtime format changed in this workflow revision.

The schema skill and its raw-research reference are the canonical initial-creation
procedure. Processing and discovery guides route new-schema work to it.
Refreshing, reviewing and extending an existing schema use processing maintenance.
The repository skill owns maintained instructions; installed copies are
synchronized distributions. Published executable contracts remain dataset-owned.

Inventory the supplied raw corpus, distinguish mechanical counts from sampled
semantic review, and investigate structured fields and source prose. Proposed
fields include meanings, types, units, scopes, qualifiers, evidence, coverage,
rationale and unresolved alternatives. Candidate source paths and aliases inform
later implementation; their discovery does not establish tested extraction.
A task requesting the full workflow can continue into processing and model
steps using its existing authorization.

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
| Model version | Saved study, data, design, fitted parameters and evaluation under the [model release metadata contract](../model/spec.md#53-validation-and-model-release). |

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
[cleanup guide](chocolate-cleaning.md) owns its CLI, complete outputs, seller
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
section 3.2 and the [model readiness and regression requirements](../model/spec.md#4-dataset-readiness).

#### Defined chocolate schema inside silver

The initial schema is `chocolate-schema-1`. Its `profile.json`,
`source-mappings.json`, `product.schema.json` and `model-design.json` are
authoritative under `contracts/chocolate/` in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
The [dataset manifest](../../schemas/chocolate/dataset-contract.json) pins an
immutable dataset commit, every file's SHA-256 and the contract versions. The
files define tracked attributes, source aliases/normalization, standardized shape
and the initial training/insight contract respectively. The
[schema guide](chocolate-schema.md) documents their application and extension.

Default builds resolve that pin into the ignored `data/contract-cache/`, verifying
file lengths and hashes before reuse. A cache miss requires network access;
`--offline` fails if pinned files are missing and never selects a moving revision.
An explicit `--schema-root` supports custom local contracts. See
[dataset contract storage](dataset-contracts.md) for fetching and provenance.

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

The [silver guide](chocolate-silver.md) owns the complete output contract,
including products, assertions, observations, candidate/eligible rows, reviews,
quality/reproducibility reports and exact contract copies. Build coverage and
exclusion reasons belong in the quality report. Follow the
[documentation policy](../documentation-policy.md): publish changed dataset
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
in the [model specification](../model/spec.md#4-dataset-readiness) before fitting.

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
in a portable snapshot. The [schema guide](chocolate-schema.md) owns its command
and report details.

#### Portable processing and maintenance from captures to mappings

The standalone [category-processing plugin](../../plugins/category-processing/README.md)
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

Processing package `0.3.3` includes the `init-profile` command with explicit
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

Processing package `0.3.3` includes structural discovery beyond configured extraction
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
[seller review metrics](schema-proposals/seller-review-metrics.md) and
[selling plan terms](schema-proposals/selling-plan-terms.md) proposals are pending
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
[agent-led maintenance decision](../decisions/agent-led-schema-maintenance.md), the
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
[portable processing guide](category-processing.md) owns commands, versions,
outputs and workflow details; the [lifecycle plan](../lifecycle/plan.md) records
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
| A product name states Blonde Chocolate or Blond Chocolate. | Extract `blonde` with the complete original name and capture pointer; retain its unreviewed state. |
| A product name states Milk Chocolate and Dark Chocolate Selection, or Milk & Dark Chocolate Selection. | Extract `mixed` from the coordinated selection, including lists with a shared chocolate suffix; retain original evidence and distinguish ambiguous component mentions. |
| Raw chocolate records are processed into silver. | Verify the raw snapshot, deduplicate exact seller listings and standardize them in one build; retain original captures/aliases, preserve separate sellers and roles, and emit candidate rows separately from reviewed eligible inputs. |
| A schema, mapping, pricing gate, or model interpretation changes. | Update the affected machine contracts, version references, specification, schema/silver guides, and lifecycle plan together; run the documentation drift check. |
| A study uses a category whose comparison basis is price per item. | Preserve its original quantities and prices during collection; derive its analytical profile without requiring cocoa percentage, edible weight, or GBP per 100 g. |
| Another category is added. | Reuse the minimal collection/evidence envelope, then derive its own analytical profile, dataset, and validated model domain from collected information. |
| Furniture or another non-food category is collected. | Track general or explicitly selected source sections, preserve arbitrary specifications and evidence, and do not require ingredients or nutrition. |
| A new category needs processing contracts. | Generate and validate all five local working contracts from its explicit versioned definition without copying a bundled profile; preserve existing folders and publish authoritative contracts separately with immutable dataset references. |
| A category uses non-GBP per-item prices or a different minor-unit scale. | Use its declared currency, observed item count, normalization base and minor-unit factor; apply one reviewed tax basis and retain missing-context exclusions. |
| Any category's raw archive needs a portable local text export. | Apply `rgc-text-evidence-1` locally: include original product records, text evidence, history, catalogues, collection reports, and coverage; omit image bytes, transfer caches, and runtime files while retaining metadata and explicit omission manifests. Reject raw upload requests. |
| A binary image is stored with a filename that suggests text. | Exclude its bytes from the local text export and record the reason; keep the original local evidence unchanged. |
| A local text export references an omitted image or cache file. | Preserve the historical reference and provide its omission entry; resolve complete source evidence in the full local archive. |
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

## 9. Decisions still to make

- The category boundaries and included product forms for the current UK chocolate
  study, and the category/market for subsequent studies.
- The first supported agent harnesses, adapter packaging, transport, capability
  mappings, and result/evidence delivery.
- Which sources are accessible and suitable, and what evidence can be retained
  under their access and usage conditions.
- The collection window and source/retailer coverage.
- Further chocolate schema extensions and extraction coverage, reviewed
  comparable groups, and confirmed quantity and the applicable consumer price
  basis before modeling.
- Coverage targets and the extraction review plan.

Resolve these decisions before the corresponding implementation or release
commitment. The [model specification](../model/spec.md#9-decisions-still-to-make)
owns numerical model release criteria and the
[current study price target](../model/spec.md#current-chocolate-study-price-target);
the [application specification](../app/spec.md) owns hosted preview verification
and access configuration.

## 10. Gold and the finalized training basis

This section owns Gold storage, data interfaces and family identity. The
[model specification](../model/spec.md#10-gold-and-the-finalized-training-basis)
owns the historical regular-price target and experimental OLS consumer. The
[current chocolate price target](../model/spec.md#current-chocolate-study-price-target)
and [training admission and inferred refit](../model/spec.md#gold-training-admission-and-inferred-lightgbm-refit)
define subsequent model preparation and training behavior.

The canonical chocolate architecture is Bronze (raw) → combined Silver → immutable Parquet Gold. Silver retains seller rows, evidence, reviews and source eligibility. Gold exports every candidate to one `training-data.parquet` population using `chocolate-gold-population-1` and `chocolate-gold-arrow-3`. Its analytical rows omit `model_eligible` and `exclusion_reasons`; it has no stored eligible subset. Typed empty tables, Zstandard compression, exact contracts/price/identity evidence, source manifests, logical digests and managed hashes support independent verification. Original source training views and complete migration parents are retained as provenance. Existing snapshots cannot be overwritten. The [Gold guide](chocolate-gold.md) defines build, migration, review provenance and trainer handoff.

The optional inferred export is a separate immutable bundle derived from an
explicit Silver snapshot and curated decision/provenance files. Typed profile
columns expose supplied accepted values alongside existing Silver values, while
`record_json` retains each complete Silver record. The bundle also contains a
Gold snapshot under `training/` and the decision/source audit under `inference/`.
Version 1 uses the explicit legacy builder and storage verifier to retain its
historical source eligibility and contract bytes. The public Gold loader then
exposes every candidate without selection fields for current model preparation.
The export preserves Silver source decisions. Its Hugging Face publication uses
the separate `gold-inferred/chocolate/uk/` prefix and pointer; the original
publication preserved normal Silver/Gold pointers and the default configuration.

`chocolate-source-mappings-2` adds reusable `chocolate-product-identity-1` family taxonomy. Evidence-backed Codex assignments populate product and candidate IDs; related range grouping prevents validation leakage while seller rows and prices stay separate. Unknown/conflicting relationships remain in grouped review packets. Family assignment alone does not confer eligibility. Exact physical pack identity, reviewed scope, price/tax/time/availability, edible quantity and predictors remain separate requirements. [The schema guide](chocolate-schema.md) and [registry guide](../../reviews/chocolate/README.md) own mapping details.


Every Gold candidate is included automatically. `verified_gold` verifies historical snapshots under their original storage rules and returns all candidates with selection fields removed. New builds and migrations write one population table; reports use `counts.training_rows` without eligibility or exclusion counts. Both legacy JSONL loader names alias the complete population. Administrative review remains optional manifest provenance. Models validate actual inputs and their selected study context; missing values produce concrete readiness blockers. Silver compatibility commands retain source eligibility. The current study derives its displayed-price target under `current-consumer-price-1` at training time. See [Gold population migration](chocolate-gold.md#make-every-gold-candidate-model-eligible).

## Original published Silver retirement

The user requested removal of `silver-6e246156b7292dd4bb49ebf0` from the current
Hugging Face dataset tree on 2026-10-03 and waived backward compatibility for
that snapshot. The current tree retains `silver-2f97cfe8b8c50ecfa79ebf46`, selected
by `silver/chocolate/uk/latest.json`. The verified deletion is published at
`2f96b70adab9ea0aec6e833d94f9ebd3e338a115`; the
[retirement receipt](analysis/chocolate-original-silver-retirement-2026-10-03.json)
records all 24 removed files and verification of retained content. This specific
retirement overrides prior snapshot retention for that directory; existing
historical release records keep their original revision references.
