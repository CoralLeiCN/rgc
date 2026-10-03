# Intention

Build a tool for classifying product features and analyzing how those features
relate to product pricing within a category.

The tool will support many product categories. Chocolate is an example.

## 1. Category research and a pricing model

For a chosen product category and market, collect enough product data to fit a
regression model. Chocolate sold in the United Kingdom is one example study.

Find as many types and varieties of products in the selected category as possible,
and collect:

- Prices.
- Basic product information, including complete ingredient lists, brands, and
  other relevant source statements.
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
The [silver guide](chocolate-silver.md) defines these responsibilities in one build.

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

Package the whole method after collection as a standalone processing agent
plugin, separate from the raw collection plugin. Include the processing
core, category profiles, evidence reports, a skill for maintaining mappings and
helpers for model preparation. Another harness or plugin must be able to use it
independently of repository siblings. Include chocolate and a starter for a
second category to demonstrate reuse through profiles. See
[category-processing.md](category-processing.md).

Normalize captures under a frozen, versioned mapping, then summarize unsupported
values and unfamiliar vocabulary with evidence. Use Codex and human review in
the current task to propose and accept mapping/parser/schema improvements.
Distinguish new concepts from missing data and conflicts. Reprocess affected
history after acceptance while preserving seller identities and immutable
training snapshots. Track input content and processing fingerprints together in
the portable ledger and grouped summaries. The
[portable processing guide](category-processing.md) defines the workflow;
selective caches, automatic dispatch and silent migrations are outside delivery.

Use this schema as the shared contract for preparing pricing model inputs,
training an interpretable model, and explaining the resulting associations as
insights. Record reviewed eligibility, feature support, references, uncertainty,
validation and limitations before treating extracted data as ready for training.
Interpret associations with listing prices within the sampled market context;
do not claim causal effects from regression coefficients.

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
