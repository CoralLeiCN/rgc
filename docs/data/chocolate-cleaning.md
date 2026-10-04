# UK chocolate cleanup compatibility helper

The earlier cleanup helper reads preserved UK chocolate listings directly from
raw and writes typed product, feature and price records for [spec.md](../spec.md),
sections 3.2–4. Its `uk-chocolate-clean-1` profile provides draft mappings with
partial taxonomy coverage for the collected sources.

The canonical workflow is [raw plus silver](chocolate-silver.md). This helper
supports compatibility and diagnostics through its distinct
`uk-chocolate-clean-1`/`chocolate-reviews-1` contracts.

## Build a derived dataset

Run from the repository root with Python 3.9 or later:

```sh
python3 -B scripts/clean_chocolate_data.py \
  --archive-root data/collections \
  --output data/derived/chocolate/uk
```

`--archive-root` is the collections root containing
`chocolate/uk/products/<source_key>/<product_id>/product.json`. Legacy
`products/<product_id>/product.json` indexes are also supported. Source directory
names must match the captures; duplicate product IDs across directories are
reported as archive errors. Use an explicit path when the
archive lives elsewhere. Evidence paths in the generated records are relative
to this root. Keep it available when reviewing the output.

The output directory must not overlap the archive root. Derived files belong in
their own directory, and the raw importer continues to own raw captures. An
unchanged input archive and unchanged reviews produce the same dataset version derived from
content. The profile version records the cleanup rules separately from
the dataset version.

Add reviewed decisions with `--reviews chocolate-reviews.json`. Source
retrieval, regression fitting and publication are separate operations.

## Output contract

| File | Meaning |
| --- | --- |
| `products.jsonl` | Combined source listing records after exact deduplication within a source, with source identity and role, proposed variant/family identity and comparable group, typed quantities, evidence, and review state. |
| `features.jsonl` | Separate feature assertions linked to evidence with types, units, mapping version, extraction method, review state, and `is_current` to distinguish assertions supported by the latest capture from history. |
| `prices.jsonl` | Source price observations and their original context, parsed amounts, normalization where possible, review state, and eligibility reasons. Identical observations repeated by an import retain a combined evidence list. |
| `review-queue.jsonl` | Missing, ambiguous, unsupported, conflicting, or unreviewed information that needs evidence review. |
| `quality-report.json` | Listing and observation counts, missingness, coverage, exclusions, and readiness limitations. |
| `manifest.json` | Dataset version and reproducibility metadata for the input and generated files. |
| `profile.json` | The versioned chocolate mapping, quantity, comparison, and eligibility rules. |
| `study.json` | The UK study context and source scope used for this derived dataset. |
| `model-inputs.jsonl` | Only observations that pass the reviewed eligibility rules for regular prices; these rows do not imply that a model is ready to fit or release. |
| `capture-evidence.jsonl` | Capture IDs, retained history paths, source listing identities, and the associated artifact IDs. |
| `artifacts.jsonl` | Unique artifact metadata, including recorded paths, URLs, hashes, retrieval states, and local availability. |
| `brand/products.jsonl`, `brand/prices.jsonl` | Product and price rows for direct brand store sources. |
| `retail/products.jsonl`, `retail/prices.jsonl` | Product and price rows for retailer sources. |
| `unknown/products.jsonl`, `unknown/prices.jsonl` | Product and price rows whose source role is unresolved. |

Read JSONL files one JSON object per line. Empty `model-inputs.jsonl` is a valid
result when the archive has useful candidates but the required review decisions
are missing. Use `products.jsonl`, `features.jsonl`, and `prices.jsonl` to inspect
those candidates, and `quality-report.json` to understand their limitations.

The combined root product and price files contain all source roles. Every role
partition is emitted even when empty. `source_role` is `brand`, `retail`, or
`unknown`; it describes the selling source, independently of the product's
`brand`. Product brand and seller/retailer identity remain separate fields.

Deduplication applies only within one source, using the exact combination of
`source_key`, the hostname in `source_url`, `source_product_id`, and
`source_variant_id`. The hostname prevents unrelated websites using the same
source label from merging. A match of product names or brand names alone does
not establish a duplicate. The report records decisions about deduplication
within a source, preserving their source evidence.

The same physical product sold by different shops always remains separate
analytical product and price records. A reviewed `variant_id` may link the same
design, and `family_id` may link related variants for grouped validation; those
relationships never merge rows across sources. Source listing counts therefore
describe unique source records after deduplication within a source. Counts of
distinct physical products require separate verification. Review identity relationships and
comparison groups before using them for eligibility or grouped validation.

## Evidence and missing values

The shared adapter recognizes "Blonde Chocolate" and "Blond Chocolate" as
`blonde`, and explicitly coordinated chocolate selections as `mixed`, including
"Milk Chocolate and Dark Chocolate Selection". Original names and evidence
pointers accompany these unreviewed assertions. The
[schema guide](chocolate-schema.md#chocolate-type-from-product-names) defines
the supported wording and scope limits used by canonical Silver too.

Derived assertions refer to capture IDs and JSON pointers into retained source
records. Resolve a capture through `capture-evidence.jsonl` and its artifact IDs
through `artifacts.jsonl`; these shared tables avoid repeating complete artifact
metadata in every assertion. Source URLs, recorded paths, and available hashes
retain the route back to the preserved evidence. Cleanup never replaces
original source wording, reported prices, arbitrary source fields, or image
bytes.

The build checks that indexed captures match their immutable history records
and that those inputs do not change during cleanup. Artifact hashes are retained
as provenance metadata; the cleaner does not rehash every original source or
image payload. Use the archive integrity tools when full artifact verification
is required.

Within a raw listing folder, the exact identity of the seller listing and
`source_key` must remain consistent across captures. A changed identity is reported as an
invalid archive record and excluded from the accepted inputs, while its raw
evidence remains intact. Separate seller/product/variant identities require
separate raw listings so historical prices are not reassigned.

`present`, `absent`, and `unknown` are distinct. Missing retailer text does not
establish absence of a claim, and an unavailable image does not establish an
empty package. A seller's certification claim is an observed claim rather than
independent verification. General ethical wording does not establish a named
certification.

Nut ingredients and cross contact warnings are separate assertions. "May
contain nuts" does not establish nuts as an ingredient. Cocoa percentages
retain qualifiers and scope: a minimum percentage in the chocolate component
of a filled product or a product containing nuts must not silently become the percentage
of the whole product. A manufacturer's address does not establish country
of manufacture; [quantity rules](#quantity-and-price-rules) require edible weight.

Unmapped information remains available in the raw records. Review the queue and
extend the profile with mappings supported by evidence as unfamiliar fields and
product forms are discovered. Classification coverage for ingredients, packaging
claims and promotional themes remains partial.

The plugin archive format is `category-research-raw-1`. Unsupported or legacy
records are reported for review. The initial `draft-1` example with five products
is an illustrative derived sample; legacy `draft-raw-1` prior extractions must not
be presented as original historical page or image captures.

## Quantity and price rules

For comparison by mass, the chocolate profile uses:

```text
price_per_100g = pack_price_gbp / total_edible_weight_g * 100
```

Mass must be positive and must describe the edible contents of the selling
unit. For example, three 50 g bars total 150 g; a count of three bars without
their mass is insufficient. Shipping weight does not supply edible mass.
Ambiguous or conflicting quantities remain review items.

Price conversion depends on the source format. A source amount expressed in
pennies must be divided by 100, while an amount expressed in pounds must not.
The original amount and its evidence remain available. Zero, invalid, unknown,
or conflicting amounts cannot provide a positive normalized price.

Displayed prices, reference prices, and promotions retain separate meanings.
A Shopify `compare_at_price` is a reported reference price and does not alone
prove the ordinary selling price. A listing with only a promotional price
cannot supply an invented regular price. Offer dates, membership conditions, multibuy mechanics,
availability, and shipping remain part of the source context where available.

Capture and archive timestamps record collection activity; price observation
time and validity require their own evidence. Initial model inputs require a
regular GBP consumer pack price, positive edible mass, scope and comparable
group, all reviewed under [review decisions](#review-decisions). Source
availability must be explicitly true; unavailable and unknown listings remain
in the derived dataset with exclusion reasons. The UK market label alone does
not establish tax treatment.

## Review decisions

The optional review file uses the following envelope. Its `products` map is
keyed by listing ID from `products.jsonl`; its `prices` map is keyed by price ID
from `prices.jsonl`. Use the generated IDs and read supporting evidence before
adding decisions:

```json
{
  "review_format_version": "chocolate-reviews-1",
  "products": {},
  "prices": {}
}
```

Every decision must identify `reviewed_by`, a substantive `reason`, and
supporting `evidence`. Evidence entries contain a `capture_id` and a JSON
`pointer` rooted at that retained capture. For example,
`/raw_record/information/selected_variant/price` addresses a preserved price in
that source format. The command validates capture IDs and pointer locations.
Referencing a real location establishes provenance; reviewers must still check
that its contents support the decision.

| Product review field | Meaning |
| --- | --- |
| `variant_id` | Reviewed identity of the physical variant, preserving differences in flavor, recipe, mass, and pack configuration. A shared value links a design without merging listings from different shops. |
| `family_id` | Related variants that should remain together during grouped validation. |
| `in_scope` | Boolean decision on whether the listing belongs to the intended chocolate study. |
| `comparable_group` | Reviewed pricing comparison group. |
| `total_edible_weight_g` | Optional confirmation of positive edible mass for the entire selling unit. |
| `pack_count` | Optional confirmation of the number of edible units in the selling unit. |

Supported group labels are `bar`, `assorted_box`, `chocolate_pieces`,
`baking_chocolate`, `hot_chocolate`, and `other`. A label's presence in the
profile does not make its products in scope or establish comparability with
another group; those remain explicit study and review decisions.

| Price review field | Meaning |
| --- | --- |
| `regular_price` | Positive observed ordinary price of the selling unit supported by source evidence. |
| `currency` | Confirmed currency; the initial input basis for regular prices requires GBP. |
| `tax_basis` | The supported initial basis is `consumer_tax_included`. |
| `observed_at` | Confirmed price observation timestamp including timezone. |

Omit unconfirmed values. Without the relevant review, automatically proposed
identities, quantities, prices, and groups remain unreviewed. To enter the
initial eligible set of model inputs, a price decision must explicitly confirm
all four fields: `regular_price`, `currency`, `tax_basis`, and `observed_at`.
Partial price decisions remain excluded with `price_basis_review_incomplete`. A
quantity review must explicitly support the capture associated with its price
observation; missing or conflicting historical weights require evidence from
that observation. Rebuild after changing reviews so the decisions and dataset
version stay together.

## Readiness and validation

`quality-report.json` reports candidate records separately from reviewed
eligible observations. `release_ready` remains false until the required
classification evaluation and modeling validation actually exist. Reviewing a
price and quantity is only one part of dataset readiness.

Before modeling, evaluate classification against a reviewed sample, resolve
identity ambiguities, define the policy for missing values, inspect source and
feature coverage, and select comparable groups. Keep related families together
in validation. Follow [spec.md](../spec.md), sections 4–5, for model support,
uncertainty, evaluation on data held out of training, and release requirements.
Establish readiness through classification and model validation; eligible row
counts and automatically extracted confidence scores alone are insufficient.

Run compatibility cleanup checks in the locked development environment:

```sh
uv sync --locked
python3 -B scripts/fetch_contracts.py --all
uv run pytest scripts/tests/test_cleaning.py
uv run ruff check .
python3 -B scripts/check_documentation.py
```

Current canonical processing leads from raw through combined Silver to immutable Parquet [Gold](chocolate-gold.md). Compatibility cleanup uses `uk-chocolate-clean-2` and the finalized `regular-consumer-price-1` target: reject unsupported regular or tax-inclusive basis without substituting displayed offers. The [schema guide](chocolate-schema.md) owns reusable family mappings; these preserve seller listings and require independent evidence review.

## Table backend provenance

The compatibility CLI uses the standard-library table backend. Shared helpers
also accept an explicit pandas backend for the combined silver build; grouping
and partitions retain seller identity and original captures. Backend runtime and
the shared table helper enter the deduplication fingerprint. Cleanup fingerprints
include the shared helper and fixed-target model helper. The
[silver guide](chocolate-silver.md#deduplication-within-each-seller) owns the
canonical pandas workflow.
