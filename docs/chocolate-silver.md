# UK chocolate raw and silver workflow

The canonical chocolate dataset has two layers: raw preserves original evidence,
and silver combines seller-specific deduplication with schema standardization,
price normalization, evidence review and model-input eligibility. These are
successive responsibilities inside one silver build, rather than separately
required deduplicated and standardized dataset layers.

The [schema guide](chocolate-schema.md) owns the 103-attribute chocolate contract,
standardization rules, review format and pricing-model handoff. The
[project specification](spec.md) owns cross-layer and release requirements.

## Layer responsibilities

| Responsibility | Raw: `data/collections/chocolate/uk` | Silver: `data/silver/chocolate/uk` |
| --- | --- | --- |
| Collect and preserve | Original source-driven product records, arbitrary fields, source/image artifacts and append-only capture histories. | Read preserved records; retain every accepted original capture in canonical seller groups without rewriting its values. |
| Identity | Preserve source identity and raw listing folder IDs as collected. | Deduplicate exact listings within one selling source and record raw-to-canonical aliases. Different shops remain unique. |
| Meaning and units | Retain original wording, values, units, claims and price representations, including unfamiliar information. | Apply versioned types, vocabularies, units, scopes and qualifiers; retain unknowns, conflicts, evidence and unmapped information. |
| Price context | Preserve reported prices, offers, availability and timestamps. | Separate observations, consolidate identical repeated evidence, normalize supported edible-mass prices and retain historical context. |
| Review | Preserve the evidence used to make future decisions. | Apply evidence-backed identity/scope/attribute/price decisions and report unresolved information. |
| Training boundary | Make no claim that collected records are model-ready. | Emit pricing candidates separately from reviewed eligible inputs, with explicit exclusion reasons and readiness limits. |
| Reproducibility | Keep indexed captures and immutable histories available for integrity checks. | Verify input snapshots and record content versions, contracts, implementation/review provenance and output hashes. |

Raw collection remains independent of a complete analytical taxonomy. Silver
implements the current chocolate taxonomy without limiting future raw collection
or discarding information that has no current feature mapping.

## Build silver

Run from the repository root with Python 3.9 or later:

```sh
python3 -B scripts/build_chocolate_silver.py \
  --archive-root data/collections \
  --output data/silver/chocolate/uk
```

`--archive-root` is the collections root containing
`chocolate/uk/products/<product_id>/product.json`. The output must not overlap
this root. Keep the raw collections root available to resolve original
artifact/history references. Use explicit paths for an archive elsewhere.

The build performs these operations in order:

1. Verify indexed raw captures against their immutable histories and form a
   content-addressed input snapshot; report unsupported or invalid archive records.
2. Group exact duplicate listings within each selling source and preserve every
   member capture, original raw product ID and raw-to-canonical alias.
3. Apply the versioned chocolate schema, controlled values and supported unit
   conversions, retaining provenance, missingness, conflicts and unfamiliar claims.
4. Form separate price observations and supported normalized values with the
   quantity and selling context belonging to that observation.
5. Apply evidence-backed reviews and initial model-design gates; emit candidates,
   eligible inputs, review items, seller-role partitions and reproducibility reports.

An unchanged raw input, implementation, contracts and reviews produce the same
content-based silver dataset version. Deduplication and standardization reuse
internal components; the caller does not have to generate or keep intermediate
`data/deduplicated/` or `data/standardized/` directories. A build does not collect
new sources, rewrite original evidence, fit a regression or publish a dataset.

## Seller-specific deduplication

A duplicate requires an exact match of `source_key`, hostname from `source_url`,
`source_product_id` and `source_variant_id`. A null variant ID may match another
null when the other identifiers are sufficient; missing source, hostname or
product identity prevents a merge. Product names, brands, GTINs, weights and
recipes do not cause a merge.

The canonical listing ID is the first member raw listing folder ID in sorted
order. `source_listing_ids` retains every member; `listing-aliases.jsonl` records
each raw listing's canonical ID. Captured `raw_record.product_id` values are
preserved rather than rewritten to that canonical ID.

A raw listing folder must retain the same exact seller-listing identity and
`source_key` across its captures. A change is an invalid archive record: exclude
that folder from the accepted snapshot and report a partial build, leaving its
raw evidence intact. This prevents historical captures from being attributed to
a different seller or product/variant; separate raw listings are required.

The same physical product sold by two retailers remains two silver listings.
Direct brand-store and retailer offers also remain separate. `source_role` is
`brand`, `retail` or `unknown`, describing the seller independently of the product
brand. Reviewed physical-product and family relationships can link designs for
validation; they never merge seller rows or prices.

New source keys without a supported seller-role mapping remain `unknown` until
source evidence supports an explicit mapping. Do not infer their role from the
product brand. Unknown-role listings and their captures remain in silver and its
unknown partition; the initial model gate excludes them.

## Output contract and evidence resolution

Read JSONL files as one JSON object per line.

| File | Meaning |
| --- | --- |
| `products.jsonl` | Schema-conforming canonical seller listings with all defined typed attributes, evidence states, review status and unmapped claims. |
| `source-listings.jsonl` | Canonical seller groups with source identity, all unchanged original capture objects, member raw listing IDs and latest capture ID. |
| `listing-aliases.jsonl` | Each accepted raw listing folder ID mapped to its canonical seller listing ID. |
| `assertions.jsonl` | Evidence-linked historical/current attribute assertions and review interpretations; `is_current` distinguishes latest/current support. |
| `prices.jsonl` | Seller price observations, original context, quantities, normalized values, review state and exclusion reasons. |
| `training-candidates.jsonl` | Proposed pricing targets/predictors and eligibility reasons, including incomplete or unreviewed records. |
| `model-inputs.jsonl` | Only reviewed observations passing the initial model-design gates; an empty file is valid. |
| `review-queue.jsonl` | Unknown, conflicting, unmapped, invalid or unreviewed information requiring attention. |
| `profile.json`, `source-mappings.json`, `product.schema.json`, `model-design.json` | Copies of all four exact versioned chocolate contracts used by the build. |
| `quality-report.json` | Raw/deduplication and standardization coverage, exclusions, extraction/review gaps and current readiness limits. |
| `manifest.json` | Silver layer/dataset version, raw snapshot provenance, contract and implementation/review provenance, and managed output hashes. |
| `brand/`, `retail/`, `unknown/` | Seller-role partitions, each containing `products.jsonl`, `prices.jsonl` and `source-listings.jsonl`, including empty files when applicable. |

Root product, price and source-listing tables combine all seller roles. Original
source/image bytes and immutable history files remain in raw. Resolve an
attribute or price `capture_id` through its listing in `source-listings.jsonl`,
then apply its JSON `pointer` to that retained capture object. Follow the
capture's history/artifact paths against the raw collections root when reviewing
original artifacts. Silver retains the route to the evidence without replacing
those bytes or requiring a persisted intermediate snapshot.

Raw index/history validation and retained artifact hashes do not constitute a
new rehash of every source/image payload. Use archive integrity tools when that
full verification is required. Listing counts describe seller records, rather
than verified distinct physical products or exhaustive UK market coverage.

The manifest uses `manifest_format_version: chocolate-silver-manifest-1`,
`layer_version: chocolate-silver-1` and a content-based `silver-<hash>` dataset
version. Raw snapshot provenance remains distinct from the silver dataset
version. Review/schema changes produce a new derived version without changing
original captures.
The report's `complete_snapshot` status describes accepted raw snapshot
consistency, not complete feature extraction or model readiness. The CLI exits
0 for a complete snapshot, 1 for a partial snapshot with reported input gaps,
and 2 if the build cannot complete. Inspect report coverage and readiness even
when the exit code is 0.

## Review, training and interpretation boundaries

Use `--reviews <reviews.json>` with the `chocolate-schema-reviews-1` format in
[the schema guide](chocolate-schema.md). Review map keys are `listing_id` for
products and `observation_id` for prices. Decisions need reviewer, reason and
resolvable capture/pointer evidence. Price and active feature reviews must
support the same price observation capture, rather than borrowing a later
recipe, claim or pack size.

Silver normalizes supported prices but does not establish training readiness
from parsing alone. The initial design requires reviewed identity/family, study
scope, comparable group, positive edible mass, regular GBP consumer price,
confirmed tax inclusion, timezone-aware observation and availability, and 11
reviewed predictors with supported scope/qualifiers. Unknown/conflicting values
are retained rather than coerced into an absent claim or reference category.
Profile/validator typed-value and unit/vocabulary/bounds drift fails before
publication under the supported validator template. A category-valid value
outside the selected model domain still belongs in silver, with
`model_predictor_outside_design_domain:<attribute>` excluding its candidate rather
than failing the whole build.

The proposed target is natural-log regular GBP per 100 g. Model preparation uses
family-grouped validation and training-only preprocessing; current helpers
provide validation, splitting, frozen encoding and contrast calculations without
fitting regression coefficients. A future fitted model must report references,
uncertainty, support, held-out performance and conditional interpretation under
the [specification](spec.md). Silver output does not establish causal effects,
isolated brand premiums or supported new-product predictions.

The current source-derived values remain unreviewed and price/tax basis is
unresolved, so eligible model inputs remain empty and `release_ready` is false.
Use the report and review queue to plan evidence review and extraction evaluation
before fitting.

## Mapping-maintenance workflow

The established chocolate CLI described in this guide emits versioned assertions,
unmapped claims and review items. The standalone
[category-processing plugin](category-processing.md) now packages the same
methodology with stable seller UIDs, a processing ledger, grouped triage batches
and a skill for the calling harness. Its portable chocolate schema has a distinct
version for that envelope. Those outputs do not change this CLI's contract;
select the portable workflow when they are needed. Neither workflow installs
automatic task dispatch, incremental processing caches or selective migrations.

1. Process a capture with a frozen schema/mapping/parser version. Keep unsupported
   values unknown and retain the raw statement and its evidence.
2. Group unresolved assertions by evidenced field, value, scope, unit/qualifier
   and reason. Include frequency and representative capture IDs/raw JSON pointers;
   keep seller/source context available so unrelated meanings are not combined.
   Report missingness separately rather than inventing a value or pointer for
   absent evidence. Distinguish repeated captures from listing/source coverage.
3. Triage a batch as a recognized alias, a genuinely new concept, a parser bug,
   missing data or conflicting evidence. Missing copy is not a new vocabulary
   value; a conflict is not an instruction to choose the most frequent claim.
4. Use Codex and human review to prepare a proposed mapping/parser/schema diff,
   evidence fixtures, tests and an impact comparison. An alias must preserve the
   original meaning; a new concept may need a typed field or scope change rather
   than another label. Do not change a live mapping during the normalization run.
5. After a version is accepted, reprocess affected existing captures and compare
   labels, missingness/conflicts, seller coverage and model eligibility. Preserve
   original captures and seller identities/aliases, and keep any training snapshot
   and fitted model bound to its original versions.

The work key combines input identity/content with a processing
fingerprint, rather than checking only for a new capture ID. Changes to parser,
mapping, schema or evidence reviews can require revisiting an unchanged capture.
The portable ledger records fingerprints and outcomes; its engine still rebuilds
the full accepted snapshot. Future selective caching needs explicit invalidation.

Batch frequency helps prioritize investigation, but does not prove an alias or
its factual correctness. Keep component versus whole-product cocoa, minimum
versus exact percentages, ingredient versus cross-contact statements, named
certifications versus generic wording, and mass/price bases distinct. Fix source
extraction defects before expanding the taxonomy to accommodate their output.
Assess each accepted mapping version's downstream eligibility and modeling
impact; taxonomy growth does not establish independent feature support.

This workflow does not configure messaging, dispatch or scheduling, or apply
unreviewed changes automatically. Package validation, data review and later model
release remain separate under the [specification](spec.md).

## Compatibility helpers and documentation maintenance

The standalone [deduplication helper](chocolate-deduplication.md),
`standardize_chocolate_data.py`, and earlier
[cleanup helper](chocolate-cleaning.md) remain available for compatibility or
component diagnostics. Their historical directories and formats are separate
helper outputs. The canonical workflow starts from raw and writes one silver
dataset; it does not depend on those prebuilt helper outputs.

When silver behavior, identity, schema, mappings, review gates or model design
changes, update the applicable contracts and versions, this guide,
[the schema guide](chocolate-schema.md), [specification](spec.md), affected
[intention](intention.md) and [lifecycle plan](lifecycle/plan.md) in the same
change. Follow the [documentation policy](documentation-policy.md) and run
`python3 -B scripts/check_documentation.py` with the relevant behavioral tests.
