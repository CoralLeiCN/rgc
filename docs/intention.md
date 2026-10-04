# RGC project intention

Build a tool for classifying product features and analyzing how those features
relate to product pricing within a category.

The tool and both plugins must support arbitrary product categories through
category-specific configuration. Chocolate is an example. New categories must
not require copying food assumptions into the collection or processing core.

The team is entering EAT_HACK on 3 October 2026 in Track 2, Retail Futures.
The [hackathon brief](eat-hack-track-two.md) covers the Track 2 challenge,
submission requirements and judging criteria. The entry should support a concrete
brand or retail decision and disclose substantial work completed before the event.

The hackathon project is named **retail frontier**. Its
[project description](../PROJECT.md) demonstrates built capabilities and a
runnable collection workflow, distinguishing implemented features from proposed
modelling. Keep event requirements and judging criteria in the hackathon brief.
The team confirms that no substantial project work existed before EAT_HACK.

Retail category managers, buyers and pricing teams are the primary application
users. They need to explain a SKU's proposed price against comparable market
evidence and its position in an assortment. Brand product developers are a
related audience. Retailer examples such as Tesco identify the intended users;
internal retailer data or a customer relationship is not assumed.

The retail frontier entry includes the **Piece of Cake Pricing** web workspace.
Current application work covers evidence exploration, a declared prototype trait
score, product configuration and candidate extraction. Users can cut vertically
through the cake at selected price points to inspect its layer composition.
The user subsequently authorized the published LightGBM without brand fixture
for a clearly labelled synthetic prediction demo. The form should calculate a
price from supported inputs and show signed SHAP field contributions relative
to the model reference. Real market benchmarks retain their separate review
and validation requirements.

The user requested that the app consume the published Gold inferred collection.
Use its accepted derived attributes with preserved source evidence, review states,
missingness and immutable provenance. Dataset adoption does not establish model
readiness.

## 1. Category research and a pricing model

The user requested six independent model implementation/training sessions. This
independent without-brand session owns `lightgbm_without_brand` and must complete an implementation,
meaningful fixture validation and attempted real-data workflow independently of
other fitted artifacts. Model artifact publication is authorized under
`model/<model-id>/<run-id>/` in the existing Hugging Face dataset when an actual
real-data fit exists. Fixture fits cannot serve as real trained models; analytical
contract publication retains its separate release review. The user later requested
model storage under `model/*`; the saved synthetic run is published under
`model/lightgbm_without_brand/fixtures/<run-id>/`, with its synthetic status
retained. See the
[implementation record](data/analysis/lightgbm-without-brand-implementation.md).

For a chosen product category and market, collect enough product data to fit a
regression model. Chocolate sold in the United Kingdom is one example study.

Find as many types and varieties of products in the selected category as possible,
and collect:

- Prices.
- Basic product information, brands, specifications, and relevant source
  statements. Collect complete ingredient lists when applicable to the category.
- Product features.
- All identifiable points emphasized on packaging and in promotional material.

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
content while changing the archive's storage metadata.

Collection of product information must be available as
an agent plugin that can connect to multiple agent harnesses and be integrated
with other plugins. Follow the Agent Plugins specification at
https://agent-plugins.org/specification.

Use the collected data to estimate the contribution of individual product
features to the final price. Examples include fair trade, brand, and nuts.

### Evidence layers and the chocolate schema

For the current chocolate training task, the user explicitly requested every
Gold entity be model eligible. Apply that instruction in a new immutable Gold
snapshot, record authorization provenance and retain the complete parent.
Training honors the promoted flags and preserves actual analytical values.
The user subsequently superseded the regular-price requirement for this study:
use the collected current displayed price as the target, normalize by actual
edible weight, and retain promotion and tax metadata as limitations. Independently
verified regular prices, non-promotional classification and confirmed tax
inclusion must not block this study. Missing quantities or identities still
require a concrete failure report. The [Gold guide](data/chocolate-gold.md) owns this operation.

Keep the original raw archive and one combined silver dataset. Silver performs
deduplication within each seller followed by schema, unit and vocabulary
standardization, price normalization, evidence review and training eligibility.
The [silver guide](data/chocolate-silver.md) defines these responsibilities in one build.
Use pandas for the combined chocolate silver table operations and schema coverage
and exact value-frequency analysis, preserving evidence and explicit states.
Publish verified chocolate snapshots and analysis to the dataset with immutable
revisions and per-file hashes.

Combine repeated listings only within one selling source. Keep records from
direct brand stores and retailers separate, and retain the same physical product
sold by different shops as unique seller listings. Preserve every original
capture and the route back to its source evidence.

Use a defined, versioned chocolate schema within silver. Track as much useful
information supported by sources as practicable across identity, composition,
quantities, nutrition, dietary information, origins, certifications and other
claims, production, packaging, promotional emphasis and seller/price context.
The schema may cover more than the current extractors can establish: unsupported
fields remain explicitly unknown, with unfamiliar information retained for later
mapping.

Use typed fields, controlled vocabularies, declared units, explicit unknown and
conflict states, versioned source mappings, and evidence references to standardize
the information consistently. Extend the schema as evidence reveals additional
useful information without rewriting original source material.

Keep analytical schemas, mappings, validators, model designs and processing
recipes in the authoritative
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Git retains human documentation and small manifests pinning an immutable
commit and each contract's SHA-256. Downloaded contracts are ignored caches;
moving storage must preserve contract versions and original evidence.

Package the method after collection as a standalone processing plugin with its
core, category profiles, evidence reports, maintenance skill and model helpers.
Define collection sections, fields, source mappings, comparable groups, units,
currency and price basis for each study. Generate five aligned local working
contracts from an explicit definition, then publish the authoritative contracts
and pin their verified immutable dataset revision after release review.
Give initial schema creation a dedicated reusable
[category-schema skill](../plugins/category-processing/skills/category-schema/SKILL.md)
covering raw research, field meanings and semantic validation of the initial
catalog. Its output includes original evidence, rationale, coverage and unresolved
decisions. It can propose or finalize the catalog within the requested task.
Run initial schema creation as a fresh research exercise on the existing chocolate
Bronze data, assuming no usable analytical schema, then compare the frozen result
with the current schema. Record inspected evidence, coverage, semantic gaps and
all field relationships; distinguish the proposal from an adopted executable
contract. The [reconstruction report](data/schema-proposals/chocolate-bronze-reconstruction-2026-10-04.md)
records this exercise and comparison.
Define Bronze as the raw-data layer containing original records, source artifacts
and immutable capture history. Collection produces Bronze; schema creation reads
Bronze; processing turns Bronze into reviewed Silver; Gold serves the training
handoff. Use Bronze → Silver → Gold consistently in workflow descriptions.
Existing raw archive paths and format identifiers remain Bronze storage contracts.
Category-processing starts when preserved raw data and a generated schema are
available for the same study. If the schema is missing, generate it with the
schema skill first. Processing owns mapping/extraction configuration, schema
serialization, evidence review and reviewed Silver. Model design and model-input
preparation belong to the subsequent Silver-to-Gold layer. Existing Silver
eligibility decisions remain source evidence for that handoff. Later steps can
continue within the same task when requested. Schema creation needs no processing runtime, fixed file count or
invented pricing model. The current runtime still requires five aligned files
for a runnable profile and emits legacy training views; removing that coupling
needs a runtime migration. Keep the schema instructions usable independently.
Existing-schema refresh, review and extension remain in processing maintenance.
Chocolate and coffee references are optional examples; products beyond food and
mass quantities must exercise the common core. The
[portable processing guide](data/category-processing.md) owns commands and boundaries.

Normalize captures with a frozen mapping, then summarize unsupported values and
unfamiliar vocabulary with evidence. Under the
[maintenance decision](decisions/agent-led-schema-maintenance.md), the agent
assesses and applies supported local schema, mapping and parser changes without
user approval. Distinguish new concepts from missing data and conflicts; leave
insufficient evidence unresolved with a reason. When the schema changes, finish
implementation and validation, present a detailed release summary and wait for
user review before committing the changed schema or rebuilt data to Hugging Face.

Discover retained source fields beyond configured extraction with exact typed
values and capture pointers. Keep hypotheses, justification, counterexamples and
accept/reject/defer decisions in durable proposals linked to immutable evidence.
After an accepted version change, rebuild affected history with stable seller
identities and immutable training snapshots. Track content and rules fingerprints
in the portable ledger and grouped summaries. Selective caches, automatic task
dispatch and silent migrations remain future work; package correctness needs
separate evidence for reviewed data and fitted models.

Use this schema as the shared contract for preparing pricing model inputs,
training an interpretable model, and explaining the resulting associations as
insights. Record reviewed eligibility, feature support, references, uncertainty,
validation and limitations before treating extracted data as ready for training.
Interpret associations with listing prices within the sampled market context;
do not claim causal effects from regression coefficients.

Explain each supported predicted price through individual trait contributions
and one signed percentage per trait family of the final predicted price. Include
a separate model reference percentage so the allocation reconciles to the price.
Trait families group related attributes; product families continue to define
identity and validation groups. This explanation output requires implementation
and validation before use.

Maintain canonical documents and implementation status with behavior changes,
using the repository's rules and runnable check in
[documentation-policy.md](documentation-policy.md).

## 2. Price review for a retailer or a newly designed product

The intended validated workflow lets a retailer review an existing SKU, proposed
listing or price change against a supported model and comparable range. A brand
can also test a newly designed product. Declare category, market, comparison
group and selling context, then report the estimate, prediction interval and
supported comparisons. Unsupported designs require an explanation of missing
support.

The current application provides observed evidence and proposed-price placement.
Connecting the pricing model is excluded from the current work at the user's
request. A prototype trait score does not fulfill the validated workflow.

## 3. Category value for money and brand premium

Develop a score within each category for value for money and assess the brand
premium a product carries.

Implementation of this feature is deferred. Research suitable scientific methods
first. A price residual alone cannot establish brand premium, quality or consumer
value. Descriptive brand median rankings in the application measure observed
price positioning only.

## Gold, final price basis and family maintenance

Prepare immutable Parquet Gold from Silver as the training interface. Include
every candidate and remove `model_eligible` and related exclusion fields from
Gold analytical rows. Preserve analytical values, missingness and source evidence.
Implement experimental training from verified Gold; validate actual model inputs
and distinguish population membership from a fitted and validated model.

The current chocolate study uses collected displayed prices as its regular-price
proxy under `current-consumer-price-1`, without a separate regular-price,
promotion or confirmed-tax gate. Keep GBP per 100 g normalization, log scale,
actual edible weight requirements and original source metadata. Record promotion,
membership, tax and capture-date uncertainty in `PROJECT.md` and run artifacts.
Historical `regular-consumer-price-1` studies and other category contracts retain
their original price basis.

Include reusable product-family taxonomy mappings during raw-to-Silver
processing. Codex decides supported new family relationships within the
authorized study and persists decisions supported by evidence for later builds.
Preserve separate seller listings, original evidence and prior immutable
snapshots. Keep exact physical pack identity distinct from broad related product
ranges, and defer insufficient or conflicting cases.

## 4. Hackathon application: Piece of Cake Pricing

The workspace is **Piece of Cake Pricing**, with subtitle **FMCG Pricing made
easy.** It serves a two-person hackathon team presenting to retail pricing
teams. The requested delivery platform is Vercel for both frontend and backend.
The [application architecture](vercel-architecture.md) defines a Next.js app,
server APIs and a pinned, verified collection snapshot. Frontend, backend and
platform implementation are delegated to subagents after architecture design.

The current application is an evidence explorer and product-configuration
prototype. Its pinned UK chocolate snapshot contains 3,743 source listings,
2,134 price observations and 103 traits. These are seller listings, not reviewed
independent products. Zero rows pass the published model-input gate. No fitted
pricing model, supported benchmark, prediction interval or recommended selling
price is connected. [Integration notes](collection-integration.md) distinguish
implemented behavior from remaining validation and deployment work.

### Terrain and trait exploration

The primary visualization is a layered 3D terrain. X is observed GBP per 100 g;
Y is a reproducible prototype score calculated from known traits; Z is one
selected numeric leaf trait in its original units. Exact product points retain
all three coordinates. The terrain smooths nearby numeric values with positive
local weights and leaves unsupported areas open. Colored layers divide height
above a declared baseline; their thickness is a visual composition, not a price
contribution, cost share, model coefficient or quality measure. A 2D projection
provides an accessible alternative when 3D is unavailable.

The user rejected aggregating an entire parent family into a color bar or height
index. The published schema has flat families containing individual fields, not
a migrated nested family hierarchy. Families organize navigation, definitions,
filters and matrix comparison. Color is selected from one leaf field: number,
integer, enum, boolean or string list. Numeric colors use five equal-width bands
calibrated to the immutable full snapshot; filtering does not redefine a band's
meaning. A multi-valued list splits its visual share equally between its distinct
values. Unknown, conflicting, not-applicable and truncated evidence stay explicit.
Z accepts a single numeric leaf; family means and normalized family indices are
excluded.

Retailers can build a cohort with source, role, product-type, search and typed
trait conditions, then inspect the same evidence in a dynamic matrix and an
up-to-four-product comparison. Several trait families can expand at once;
pinning and per-family limits preserve manageable detail without changing
coverage denominators. The family browser exposes Filter, Colour and Height
actions for eligible leaf traits. Legend highlighting and surface smoothing
change presentation, not the cohort or original product coordinates.

The gap finder and brand analysis continue to use observed prices from the full
filtered listing collection, independently of matrix pagination and terrain
coordinate completeness. Gaps identify empty interior price bands at the chosen
resolution. Brands stand out by higher median observed price positioning within
the cohort; sales, profit, causal brand premium and demand are not inferred.
Core/full price ranges disclose excluded tails, while brand statistics retain
the full priced cohort.

### Configure a proposed product

The right column lets a retailer specify a proposed product with schema-typed
traits, pack price and edible weight. A price slider and precise numeric input
move its proposed GBP/100 g position. Score is read-only and recalculated from
traits using the shared, declared six-input prototype recipe. Prices and names
do not affect the score. No recognized scoring inputs means no score; unknown
claims are not treated as absent. A visible demo/prototype disclosure and an
inspectable rule breakdown distinguish this recipe from the separate pricing
research.

A valid configured product appears at its exact proposed price, calculated
score and selected raw numeric trait. Invalid or missing coordinates suppress
the marker instead of inventing values. A price beyond the observed range can
extend the display axes while preserving the observed cohort and range. The
draft never becomes a source listing or enters gap or brand statistics.

An explicit action can copy known, untruncated values from a selected listing;
ordinary source selection preserves edits. Product descriptions and packaging
images can also be submitted for model-assisted trait extraction. Results are
candidates with evidence and warnings. The retailer reviews and selects them,
then explicitly applies them to the draft. Applying candidates can replace
matching name, weight or trait inputs, but never changes proposed pack price.
Original source evidence remains available in a collapsed disclosure.

Keep the supplied front and back photos of Well&Truly Fudge & Brownie Oat M!lk
Chocolate, 30 g, as repository demo data and offer them as a selectable example
in the extraction panel. Users can also upload their own photos, including both
sides of a pack. Selecting an example loads its images for the same explicit
extraction and review workflow; it does not supply prefilled traits. Preserve
original photos and prepare temporary browser copies that fit request limits.
Retain label qualifiers: component cocoa minimums and “fairly traded” wording
must not imply an exact whole-product cocoa percentage or a named certification.
Demo photos and local drafts stay outside the training corpus.

Enable local image/text trait extraction through the installed Codex CLI using
its ChatGPT OAuth sign-in. The local Next.js server should invoke it directly,
with candidates still requiring explicit review and Apply. Hosted extraction
supports a configured OpenAI API provider or authenticated Codex bridge,
including the requested laptop connection through Tailscale. The extraction
model has a separate purpose from the synthetic pricing fixture and its field
SHAP explanation.
Missing provider configuration produces an explicit error. Record successful
live extraction separately from hosted bridge and network availability.

### Presentation, assets and remaining work

Use a restrained professional palette, explicit units, legible comparisons and
inspectable assumptions. Explanatory prose belongs in accessible question-mark
help beside headings, available on hover, focus and tap. Actual values, field
labels, errors and demo-score disclosure remain visible. The four top summary
cards have been removed. Avoid factory metaphors and unsupported claims of
market-wide coverage.

Maintain one current application and its operational documentation. Retired
visual studies, generated static explorers, intermediate design notes and tests
added for the hackathon are removed at the user's request. No compatibility
support is retained for those prototypes. The active terrain, product
configuration, extraction workflow and declared trait-derived demo score remain.

The teammate's pricing research and upstream experimental training remain
separate from this application. The user subsequently authorized the published
synthetic fixture for the local price prediction and field SHAP demo. The hosted
preview still predates that feature; a real market benchmark remains unvalidated.
The full local raw text-evidence archive remains available for separate modeling
work, with image bytes deliberately omitted from the export. Application
requests use their pinned snapshot and do not automatically adopt a new Gold
release or model artifact.

Upstream research retains experimental training from verified Gold and reviewed
family mappings. Remaining readiness work includes unresolved identities,
missing quantities, other feature reviews, and evaluation against a baseline.
Historical regular-price studies retain their separate price and tax evidence
requirements. Supported price testing requires validated benchmarks and
uncertainty, including held-out or out-of-fold results for training products.
If validation remains inadequate, the demo must remain an evidence explorer and
explicit prototype score, without claiming optimal pricing, value for money or
causal brand premium. The [specification](spec.md) remains authoritative for
model readiness and interpretation.

## Repository language and writing style

Author repository content in English, including when prompts are in Chinese.
Preserve original source evidence verbatim in its original language. Follow the
writing rules in [AGENTS.md](../AGENTS.md).

## Independent training sessions

On 2026-10-03 the user requested every Gold entity model eligible and instructed
all three chocolate training chats to pull the refreshed data and refit. The user refined this instruction to remove Gold eligibility requirements and
related fields entirely. Gold now includes every candidate automatically,
retaining original parents and evidence. Training uses actual stored values and the current
displayed consumer price target; eligibility does not fill missing facts or establish a
successful fit.

Implement and validate `lightgbm_with_brand` independently in this session, preserving the fixed regular consumer target and immutable Gold. Persist real-data readiness failures and distinguish synthetic acceptance fits from real trained models. Model artifact upload is authorized under `model/lightgbm_with_brand/<run-id>/` for completed actual real-data fits; analytical contract publication retains its separate release review requirement.

On 2026-10-03, the user requested removal of the original published chocolate
Silver snapshot `silver-6e246156b7292dd4bb49ebf0` from the current Hugging Face
dataset tree and waived backward compatibility for that snapshot. Retain the
pandas snapshot `silver-2f97cfe8b8c50ecfa79ebf46` selected by `latest.json`.
This instruction overrides earlier retention requirements for that specific
published snapshot. Record the deletion and verify the retained inventory.


On 2026-10-03, the user requested keeping raw source files locally instead of
publishing them to Hugging Face, then clarified removal of raw files only. Keep
the complete local collection, archive bundle, raw product index and export
manifest. Remove the public raw bundle, root raw index and export manifest,
retain published Silver source-listings, and prevent raw exporter uploads.
Derived Silver, Gold, analysis, model artifacts and analytical contracts remain
published. This storage choice supersedes the earlier raw publication policy.

## Independent chocolate estimator session

Implement and attempt real-data training for `hedonic_without_brand` independently of other model sessions, preserving regular-consumer-price-1 and family partitions. Save concrete readiness blockers when eligible evidence is absent. Trained real artifacts may be uploaded under `model/hedonic_without_brand/<run-id>/`; fixture fits cannot stand in for real training. Analytical contract releases retain their separate review requirement. The [implementation record](data/analysis/hedonic-without-brand-implementation.md) distinguishes local policy, numerical validation and evidence readiness.

Include reusable product-family taxonomy mappings during raw-to-Silver processing. Codex decides supported new family relationships within the authorized study and persists evidence-backed decisions for later builds. Preserve separate seller listings, original evidence and prior immutable snapshots. Keep exact physical pack identity distinct from broad related product ranges, and defer insufficient or conflicting cases.

The independent matched-retailer session implements and attempts real fitting
of exactly `matched_retailer`, using reviewed exact physical variants and
contemporaneous comparable regular-price evidence. Preserve separate seller rows
and report concrete readiness blockers when evidence is insufficient. Model
artifact publication is authorized for actual trained models under
`model/matched_retailer/<run-id>/` in the existing dataset; synthetic fixture fits
are not real trained models. Analytical contract publication retains the separate
release review requirement. See [the diagnostic guide](data/chocolate-matched-retailer.md).

The user confirmed all Gold-layer data as verified and requested direct training
without rebuilding Gold or adding another data layer. The matched-retailer
trainer records this task instruction, considers existing candidates, selects
required model fields and preserves source bytes and flags. Actual missing
values must still be reported without fabrication.

The user superseded the regular-price target: collected current/displayed prices
serve as the modeling target under an explicit proxy assumption. Separately
evidenced regular prices, non-promotional status and confirmed tax inclusion
are no longer prerequisites for this study. Preserve source metadata and record
those limitations. Positive edible weight and assigned-model identity/statistical
requirements still apply.

## Gold training eligibility and inferred refit

On 3 October 2026 the user requested a refit of `lightgbm_without_brand` using
the inferred Gold layer and then directed that every `gold_*` layer always be
training eligible. Gold training admits all candidate rows regardless of saved
Silver eligibility flags. Original eligibility and exclusion reasons remain
provenance. Missing numerical targets, pack mass and relationship fields still
limit which observations a declared model can use. The current study uses
`current-consumer-price-1`; market validation and champion selection require
separate evidence.
