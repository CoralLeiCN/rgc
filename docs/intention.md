# Intention

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

## 1. Category research and a pricing model

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
may have its own folder, with a JSON file covering as much relevant product
information as possible. Collect many products first, then derive a complete
schema from the collected information.

Collection of product information must be available as
an agent plugin that can connect to multiple agent harnesses and be integrated
with other plugins. Follow the Agent Plugins specification at
https://agent-plugins.org/specification.

Use the collected data to estimate the contribution of individual product
features to the final price. Examples include fair trade, brand, and nuts.

### Evidence layers and the chocolate schema

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

## 2. Price testing for a newly designed product

A brand, as a user of the application, can use the model to test the price of a
newly designed product.

## 3. Category value for money and brand premium

Develop a score within each category for value for money and assess the brand
premium a product carries.

Implementation of this feature is deferred. Research suitable scientific methods
first.

## Repository language and writing style

Author repository content in English, including when prompts are in Chinese.
Preserve original source evidence verbatim in its original language. Follow the
writing rules in [AGENTS.md](../AGENTS.md).

## Gold, final price basis and family maintenance

Prepare immutable Parquet Gold from Silver as the ready-to-load training interface, initially preserving its candidates, missing values and reviewed eligibility without new processing. Implement experimental training from verified Gold; distinguish loadable candidates, actual eligible observations and a validated fitted model.

Use regular, non-promotional, tax-inclusive consumer price as the final target basis for every pricing model. Keep each category's declared currency/quantity normalization; chocolate uses log GBP per 100g. Missing regular or tax evidence is not a fallback to displayed offers.

Include reusable product-family taxonomy mappings during raw-to-Silver processing. Codex decides supported new family relationships within the authorized study and persists evidence-backed decisions for later builds. Preserve separate seller listings, original evidence and prior immutable snapshots. Keep exact physical pack identity distinct from broad related product ranges, and defer insufficient or conflicting cases.
