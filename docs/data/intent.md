# Data intention

Prepare meaningful, reusable product data that people can filter, join, compare
and summarize within a category. Product classification, assortment analysis,
ingredient and claim analysis, seller comparisons and pricing are downstream
uses of that shared evidence.

This document owns data collection, preparation, evidence and publication goals.
The [data specification](spec.md) owns current contracts and supported behavior.
The [overall intention](../intention.md) provides shared project context;
[application intention](../app/intent.md) and [model intention](../model/intent.md) own their delivery
scopes. The exclusion of model planning below applies to this data preparation
reassessment. Earlier modeling intentions remain in the model document.

## Current focus: meaningful data for analysis

On 4 October 2026, the user requested a fresh assessment of how extracted
chocolate website data should become meaningful structured data that is easy to
analyze. Assess the approach from the preserved source evidence and ordinary
analytical questions, independently of the existing implementation. The user
clarified that modeling is one downstream use; planning model selection,
training or evaluation is outside this data preparation reassessment.

The user clarified the layer boundary: **Silver is the structured, standardized
layer; Gold further enriches Silver for a downstream use case.** Bronze preserves
the original evidence. Silver applies the category schema, consistent types,
units and vocabularies, with source identities, provenance and explicit
uncertainty. Its definition does not depend on a model or another downstream
consumer. Gold owns additional interpretations, derived features, aggregations
and selection rules required by a particular analysis, application or model,
including comparison groups, price targets, model eligibility and model-input
preparation.

The intended result is a reusable analytical dataset with understandable fields,
consistent units and categories, explicit uncertainty and a route from each
interpreted value to its evidence. Mixed text, numbers, dates and categories are
expected. Retain useful text and structure its supported facts alongside it.
Converting a string to a number establishes its type; its meaning also depends
on the quantity, component, offer or observation it describes.

This section records the current intention and approach. The earlier
delivery scope below and the [overall intention](../intention.md) provide
context. Standard Silver v2 implements this approach locally. The
[plan](../lifecycle/plan.md#standard-silver-v2-implementation-4-october-2026)
records the source pilot, validation and remaining release work.

### Meanings and relationships to preserve

Define each field's meaning, type, unit, scope, qualifiers, allowed values and
rules for missing information in a data dictionary. For example, distinguish an
individual item's mass from total edible pack mass, a minimum cocoa declaration
from an exact value, ingredient origin from manufacturing country, and an
allergen cross-contact warning from ingredient presence.

Retain these logical distinctions when assessing the schema and analytical
views; concrete structures are decided in the implementation plan or while
inspecting the actual Bronze data, then validated against that evidence:

| Concept | Meaning |
| --- | --- |
| Product variant | Product identity, composition, flavor and form supported by evidence. |
| Pack | The selling quantity, item count, individual mass and total edible mass where established. |
| Seller listing | A seller's listing of a particular product and pack, with stable source identity. |
| Observation | What a source displayed at a recorded time and context, including price and availability. |
| Evidence | Original source text, images and capture references supporting a fact or interpretation. |

Keep listings from different sellers distinct and retain capture history.
Reuse the same ID whenever the same raw source listing/variant is parsed again.
Maintain a durable source-to-ID index, which can use SQL, so processing changes,
new duplicate aliases or moved archive paths preserve established identities.
Different source records retain separate IDs; captures and repeated subjects
keep their own context under the stable source identity.
Product relationships should support joins and distinct counts without merging
seller observations. Preserve multiple ingredients, origins and claims, with
their component or product scope, instead of forcing them into one ambiguous
value. Retain competing source statements and record the basis for any preferred
interpretation. Source wording remains verbatim, including its language.

Use the standardized column name for its result, including the canonical
unit where applicable, such as `net_weight_g`. Name its source reference by
appending `.source` to that complete name: `net_weight_g.source`. The reference
locates the raw value in a specific Bronze capture, where its original type and
wording are preserved. This distinguishes the standardized value, source
reference and original raw value. Define canonical units, conversion formulas
and parsing rules in the versioned schema
documentation. Keep the applicable schema version at dataset level; conversion
instructions do not belong in individual Silver data fields.

### Proposed preparation workflow

1. Locate relevant source sections, offer context and the selected variant in
   the preserved evidence.
2. Interpret what each candidate value describes, recording its source and any
   ambiguity. Language models may assist with interpretations supported by
   evidence; their output must allow unresolved values.
3. Standardize established facts with repeatable number parsing, unit conversion
   and documented vocabulary mappings. Document the rules in the schema and
   record the applicable version for the dataset.
4. Validate field meanings and relationships, including pack arithmetic, matching
   price and variant, measurement bases, identity and conflicting source values.
5. Review consequential ambiguities, recover evidence where possible and audit
   a diverse sample that includes apparently successful extraction.
6. Produce typed, standardized Silver tables, accompanied by their
   data dictionary, stable identifiers, provenance and quality report.

Distinguish information absent from the source, extraction failure, conflicting
evidence and information that does not apply. Reserve plain `null` for missing
information; represent parsing errors and other unresolved states explicitly.
Keep these states separate from how a result was obtained: processing by rules
is `parsed`, LLM/model processing is `inferred`, and human confirmation or
correction is `reviewed`. All three are usable, with priority
`reviewed > parsed > inferred` for the same fact and context. Conversion rules
remain in documentation. Preserve partially useful records: a missing
weight can prevent a price calculation per unit while still allowing ingredient
analysis. Report field coverage and quality in Silver. Define further enrichment
and views for a particular analytical use in Gold.

### Intended deliverable and evidence of usefulness

The first proposed deliverable is a small standardized chocolate dataset, its
data dictionary and a quality report distinguishing parsed, inferred and human
reviewed results. Human review can improve accepted data over time; it is not a
requirement for using every parsed or inferred result. Select examples across sellers,
product forms, pack structures and ambiguous source presentations. Use the pilot
to establish field correctness, consistency, completeness, traceability and
unresolved issues by field and source, then refine the approach before scaling.

Generate schema popularity reports measuring field coverage, distinct values and
frequencies for categorical fields, and numeric ranges in their declared units
and context. Include fields with no available values, separate missing/error
states from values, and show the counting population and denominators. These
reports describe the collected data and help identify gaps and inconsistencies;
the plan owns the exact calculations and report design.

Evaluate usefulness through ordinary analytical questions: count distinct
products and seller listings; compare pack sizes; summarize ingredients and
stated claims; identify sellers offering the same pack; and inspect changes
between recorded observations. Users should be able to answer supported
questions without repeatedly interpreting free text or guessing units, row
meaning or the meaning of missing values. Quality reports must disclose coverage
and the evidence behind unresolved results. Typed exports alone do not establish
that these meanings or answers are correct.

### Persistent user review and improvement

Provide an interface for users to inspect standardized values, their raw sources
and their method, then confirm or revise a result. A downstream error report
should lead back to the relevant Silver field and evidence. Save human decisions
durably and apply them on future reruns, including full reprocessing of the same
Bronze data. Regenerating Silver must preserve an applicable correction.

Tie corrections to stable listing/component/observation identities, the field and
its evidence context. Keep earlier decisions and their reasons available when a
user revises a correction. Changed source facts or field meanings require an
applicability check; retain the saved decision and surface cases needing another
review. Repeated components in JSON need stable IDs so array reordering cannot
move a correction to a different subject.

Use saved corrections as evidence for improving extraction models, parsing rules
and regression tests. Track and validate those improvements through their own
versions. Data quality improves through continued use and feedback. The
[app intention](../app/intent.md#persistent-review-of-standardized-data) owns the
review interface; the data specification owns correction storage and replay.
The local `review` interface and durable correction replay implement this workflow.
The hosted application retains its separate draft workflow.

## Earlier delivery scope and operational context

The following intentions preserve the earlier collection and processing scope.
They describe the established delivery context for the fresh assessment above;
they do not establish that the existing implementation is the best preparation
approach. The proposed reassessment does not change published contracts,
immutable snapshots or implemented behavior. Validate a revised approach and
follow the applicable contract and documentation maintenance process before
changing those interfaces.

### Collection across product categories

The tool and both plugins must support arbitrary product categories through
category configuration. Chocolate sold in the United Kingdom is one example
study. New categories must not require copying food assumptions into the
collection or processing core.

For a chosen category and market, collect many product types and varieties,
including enough evidence to support the separately defined pricing study.
Collect prices; basic product information, brands, specifications and source
statements; product features; and identifiable points emphasized on packaging
and in promotional material. Collect complete ingredient lists when applicable
to the category.

Preserve each product's original information and product images. Each product
has its own folder under a parent for its website/storefront, with a JSON file
covering as much relevant product information as possible. Group Bronze by source
so schema research can inspect similar raw structures together and processing can
apply mappings for each source. Websites often reuse page templates or catalogue
formats, making the source a useful boundary for sampling, parser development,
missing-value investigation and maintenance when the website changes. Sample
different representations within each source and compare concepts across sources
to create the category's shared analytical schema. Collect many products first,
then derive a complete schema from the collected information. The
[Bronze grouping rationale](spec.md#why-bronze-is-grouped-by-website) explains the
design and its limits. The user also requested physically moving the existing
product folders into this structure and updating archive paths directly, with
no redirects, symlinks or backward-compatibility lookup. Preserve original source
content while changing the archive's storage metadata. Source wording remains
verbatim, including its language.

Make collection available as an agent plugin that can connect to multiple agent
harnesses and integrate with other plugins, following the
[Agent Plugins specification](https://agent-plugins.org/specification).

### Initial schema research and workflow ownership

Give initial schema creation a dedicated reusable
[category-schema skill](../../plugins/category-processing/skills/category-schema/SKILL.md)
covering raw research, field meanings and semantic validation of the initial
catalog. Its output includes original evidence, rationale, coverage and unresolved
decisions. It can propose or finalize the catalog within the requested task.
Run initial schema creation as a fresh research exercise on the existing chocolate
Bronze data, assuming no usable analytical schema, then compare the frozen result
with the current schema. Record inspected evidence, coverage, semantic gaps and
all field relationships; distinguish the proposal from an adopted executable
contract. The
[reconstruction report](schema-proposals/chocolate-bronze-reconstruction-2026-10-04.md)
records this exercise and comparison.

Define Bronze as the raw-data layer containing original records, source artifacts
and immutable capture history. Collection produces Bronze; schema creation reads
Bronze; processing turns Bronze into structured, standardized Silver; Gold
enriches Silver for a downstream use case. Training is one such use.
Use Bronze → Silver → Gold consistently in workflow descriptions.
Existing raw archive paths and format identifiers remain Bronze storage contracts.

Category-processing starts when preserved raw data and a generated schema are
available for the same study. If the schema is missing, generate it with the
schema skill first. Processing owns mapping/extraction configuration, schema
serialization, evidence review and standardized Silver. Enrichment for downstream
uses, including model design and model-input preparation, belongs to Gold.
Existing Silver eligibility decisions remain recorded legacy outputs. Later steps
can continue within the same task when requested. Schema creation needs no
processing runtime, fixed file count or invented pricing model. The current runtime still
requires five aligned files for a runnable profile and emits legacy training
views; removing that coupling needs a runtime migration. Keep the schema
instructions usable independently. Existing-schema refresh, review and extension
remain in processing maintenance.

### Combined Silver, evidence and identity

Keep the original Bronze archive and one combined Silver dataset. Silver performs
deduplication within each seller followed by schema, unit and vocabulary
standardization, supported price normalization and source evidence review.
The existing builds also emit model eligibility decisions as legacy behavior;
those outputs do not define the intended Silver layer.
The [Silver guide](../data/chocolate-silver.md) defines these responsibilities in
one build. Use pandas for the combined chocolate Silver table operations,
schema coverage and exact value frequency analysis, preserving evidence and
explicit states. Publish verified derived snapshots and analysis with immutable
revisions and per-file hashes under the storage policy below.

Combine repeated listings only within one selling source. Keep direct brand
stores and retailers separate, and retain the same physical product sold by
different shops as distinct seller listings. Preserve every original capture
and the route back to its source evidence.

Use a defined, versioned chocolate schema within Silver. Track useful information
supported by sources across identity, composition, quantities, nutrition, dietary
information, origins, certifications and other claims, production, packaging,
promotional emphasis and seller and price context. The schema may cover more
than current extractors can establish: unsupported fields remain explicitly
unknown, with unfamiliar information retained for later mapping.

Use typed fields, controlled vocabularies, declared units, explicit unknown and
conflict states, versioned source mappings and evidence references. Extend the
schema as evidence reveals additional useful information without rewriting
original source material. Record reviewed eligibility, feature support,
references, uncertainty, validation and limitations at the data interface;
population membership does not establish fitness for a particular analytical use.

Include reusable product family taxonomy mappings during Bronze to Silver
processing. Codex decides supported new family relationships within the
authorized study and persists decisions with source evidence and stable reusable
IDs for later builds. Keep exact physical pack identity distinct from broader
related product ranges. Preserve separate seller listings, original evidence
and prior immutable snapshots; defer insufficient or conflicting cases.

### Portable processing and maintenance

Package the method after collection as a standalone processing plugin with its
core, category profiles, evidence reports, maintenance skill and model helpers.
Keep its skill and references usable independently of this repository. Define
collection sections, fields, source mappings, comparable groups, units, currency
and price basis for each study. Generate five aligned local working contracts
from an explicit definition, then publish the authoritative contracts and pin
their verified immutable dataset revision after release review. Keep the
portable profile's schema, mappings, validator, recipe and selected model design
aligned. Chocolate and coffee references are optional examples; products beyond
food and mass quantities must exercise the common core. The
[portable processing guide](../data/category-processing.md) owns commands and
boundaries.

Normalize captures with a frozen mapping, then summarize unsupported values and
unfamiliar vocabulary with evidence. Under the
[maintenance decision](../decisions/agent-led-schema-maintenance.md), the agent
assesses and applies supported local schema, mapping and parser changes without
user approval. Distinguish new concepts from missing data and conflicts; leave
insufficient evidence unresolved with a reason. When the schema changes, finish
implementation and validation, present a detailed release summary and wait for
user review before committing the changed schema or rebuilt data to Hugging Face.

Discover retained source fields beyond configured extraction with exact typed
values and capture pointers. Keep hypotheses, justification, counterexamples and
accept, reject or defer decisions in durable proposals linked to immutable
evidence. After an accepted version change, rebuild affected history with stable
seller identities and immutable training snapshots. Track content and rules
fingerprints in the portable ledger and grouped summaries. Selective caches,
automatic task dispatch and silent migrations remain future work. Package
correctness, reviewed data and fitted models require separate evidence.

### Contract storage and publication

Keep analytical schemas, mappings, validators, model designs and processing
recipes in the authoritative
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Git retains human documentation and small manifests pinning an immutable
commit and each contract's SHA-256. Downloaded contracts are ignored caches;
moving storage must preserve contract versions and original evidence. The
[dataset contract guide](../data/dataset-contracts.md) owns storage and verification.

On 3 October 2026, the user requested keeping raw source files locally and
clarified removal of raw files only from the public dataset. Keep the complete
local collection, archive bundle, raw product index and export manifest. Remove
the public raw bundle, root raw index and export manifest, retain published
Silver source listings, and prevent raw exporter uploads. Derived Silver, Gold,
analysis, model artifacts and analytical contracts remain published. This is the
current raw storage policy.

Keep the complete verified local raw text evidence export available for analysis
and modeling work under the
[local storage policy](../data/dataset-contracts.md#local-raw-evidence-storage).
Image bytes are deliberately omitted from that export; image URLs do not imply
that the bytes are included. Original product images remain part of the
preserved collection evidence.

The user also requested retirement of the original published chocolate Silver
snapshot `silver-6e246156b7292dd4bb49ebf0` from the current Hugging Face dataset
tree and waived backward compatibility for that snapshot. Retain the pandas
snapshot `silver-2f97cfe8b8c50ecfa79ebf46` selected by `latest.json` in that
retirement operation. Record the deletion and verify the retained inventory;
this exception applies to the named snapshot.

### Immutable Gold data interface

The current chocolate training use case prepares immutable Parquet Gold from
Silver. Gold's broader responsibility is enrichment for the selected downstream
use case. The following records the existing training interface. Include
every candidate and remove `model_eligible` and related exclusion fields from
Gold analytical rows. Retain original parent snapshots, analytical values,
missingness and source evidence. Every `gold_*` layer admits all candidate rows
regardless of saved Silver eligibility flags; original eligibility and exclusion
reasons remain provenance. Missing numerical targets, edible pack mass and
relationship fields still limit which observations a declared model can use and
must be reported without fabrication. The
[Gold guide](../data/chocolate-gold.md) owns this interface.

The current chocolate study uses collected displayed prices as its regular-price
proxy under `current-consumer-price-1`. Normalize to GBP per 100 g using actual
edible weight and preserve original source metadata. A separate regular-price,
promotion or confirmed-tax gate is not required for this study. Record promotion,
membership, tax and capture-date uncertainty in
[PROJECT.md](../../PROJECT.md) and run artifacts. Historical
`regular-consumer-price-1` studies and other category contracts retain their
original price basis. The [model intention](../model/intent.md) owns training, statistical
requirements and interpretation.

The application consumes its pinned published collection, including accepted
derived attributes with source evidence, review states, missingness and immutable
provenance. The [application intention](../app/intent.md) owns adoption of the published
Gold inferred collection and its user experience. Dataset adoption does not
establish model readiness or automatically update a pinned consumer.

Maintain canonical documents and implementation status when behavior changes,
following the [documentation policy](../documentation-policy.md). The plan records
the standard Silver implementation and its pilot evidence separately from these
historical operational results.

## UK cat litter collection

On 4 October 2026 the user requested the broadest feasible collection of product
information for cat litter sold in the UK, using the chocolate case as the
collection example. Deliver the Bronze/raw layer with original evidence,
source listings and available pack variants. Use English for authored output
and preserve original source evidence verbatim. Source ownership is divided
between agents so a webpage has at most one agent collecting it at a time.
Keep the data locally under the established raw storage policy. The
[cat litter guide](cat-litter-raw.md) records the archive, scope and gaps.
Exhaustive market coverage is a research goal, not an established result.
