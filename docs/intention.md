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

The product-information collection part of category research must be available as
an agent plugin that can connect to multiple agent harnesses and be integrated
with other plugins. Follow the Agent Plugins specification at
https://agent-plugins.org/specification.

Use the collected data to estimate the contribution of individual product
features to the final price. Examples include fair trade, brand, and nuts.

### Evidence layers and the chocolate schema

Keep the original raw archive and one combined silver dataset. Silver performs
seller-specific deduplication followed by schema, unit and vocabulary
standardization, price normalization, evidence review and training eligibility.
These are responsibilities within one layer, without requiring separately
persisted deduplicated and standardized datasets.

Combine repeated listings only within one selling source. Keep direct
brand-store and retail records separate, and retain the same physical product
sold by different shops as unique seller listings. Preserve every original
capture and the route back to its source evidence.

Use a defined, versioned chocolate schema within silver. Track as much useful
source-supported information as practicable across identity, composition,
quantities, nutrition, dietary information, origins, certifications and other
claims, production, packaging, promotional emphasis and seller/price context.
The schema may cover more than the current extractors can establish: unsupported
fields remain explicitly unknown, with unfamiliar information retained for later
mapping. Document the raw and silver responsibilities in the
[silver guide](chocolate-silver.md).

Use typed fields, controlled vocabularies, declared units, explicit unknown and
conflict states, versioned source mappings, and evidence references to standardize
the information consistently. Extend the schema as evidence reveals additional
useful information without rewriting original source material.

Keep analytical schemas, mappings, validators, model designs and processing
recipes in the authoritative
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Git retains human documentation and small manifests pinning an immutable
dataset commit and each contract's SHA-256. Downloaded contracts are ignored
local caches; moving storage must preserve existing contract versions and
original evidence.

Package the whole post-collection methodology as a standalone category-processing
agent plugin, separate from the raw collection plugin. Include the processing
core, category profiles, evidence reports, mapping-maintenance skill and
model-preparation helpers so another harness or plugin can use it without
repository sibling dependencies. A chocolate profile and a second-category
starter must demonstrate that the method is category-driven. See
[category-processing.md](category-processing.md).

The intended maintenance loop is to normalize new captures with the
existing versioned mapping, summarize evidence-backed unsupported or
out-of-vocabulary cases, and use Codex plus human review to propose and accept
mapping/parser/schema improvements. Distinguish missing data and conflicts from
new concepts. Freeze the mapping for each run, reprocess affected existing
captures after an accepted version change, and preserve seller identities and
immutable model-training snapshots. Track input content and processing
fingerprints together, rather than treating a new capture ID as the only trigger.
The portable plugin records its ledger and grouped summaries; the calling Codex
harness guides proposed changes in the current task. Selective processing caches,
automatic task dispatch and silent migrations are outside the current delivery.
The [portable processing guide](category-processing.md) records the workflow and
pitfalls; package correctness does not imply reviewed data or a fitted model.

Use this schema as the shared contract for preparing pricing-model inputs,
training an interpretable model, and explaining the resulting associations as
insights. Record reviewed eligibility, feature support, references, uncertainty,
validation, and limitations. A defined schema or an automatic extraction is not
proof that the current dataset is ready for training. Interpret listing-price
associations within the sampled market context; do not claim causal effects from
regression coefficients.

Keep intention, specification, schema, and implementation status synchronized
when behavior changes. The repository must have maintained rules and a runnable
documentation check for this obligation; see
[documentation-policy.md](documentation-policy.md).

## 2. Price testing for a newly designed product

A brand, as a user of the application, can use the model to test the price of a
newly designed product.

## 3. Category value for money and brand premium

Develop a category-based value-for-money score to assess how much brand premium
a product carries.

Implementation of this feature is deferred. Research suitable scientific methods
first.

## Repository language

All repository content must be in English, even when prompts are written in
Chinese.
