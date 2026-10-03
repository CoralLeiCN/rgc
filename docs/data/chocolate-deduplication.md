# UK chocolate deduplication compatibility helper

The standalone deduplication helper groups repeated listings from the same
selling source into a separate dataset, preserving original product information
and capture history. Prices, quantities, claims, source fields and original
source text remain as collected.

The canonical [silver build](chocolate-silver.md) applies this same deduplication
operation and retains seller groups in `source-listings.jsonl`. This standalone
CLI supports compatibility and diagnostics; inspect its
`data/deduplicated/chocolate/uk` snapshot or supply it to the standalone
standardization helper. The earlier [cleanup](chocolate-cleaning.md) has its own
compatibility contract. Feature classification and model eligibility require
subsequent review.

## Build the deduplicated dataset

Run from the repository root with Python 3.9 or later:

```sh
python3 -B scripts/deduplicate_chocolate_data.py \
  --archive-root data/collections \
  --output data/deduplicated/chocolate/uk
```

`--archive-root` is the collections root containing
`chocolate/uk/products/<product_id>/product.json`. The output must be separate
from this root. Use explicit paths when the archive or output lives elsewhere.
Keep the supplied collections root available to resolve preserved history and
artifact references.

An unchanged raw archive and implementation produce the same dataset version,
derived from content. Rebuild the snapshot after importing additional
captures. The command validates indexed captures against their immutable
history records and checks that the input files do not change during the build.

The exact identity of the seller listing and `source_key` must remain consistent
across captures within each raw folder. A change makes the folder an invalid
archive record; exclude it from the accepted snapshot and report the reason and
partial status. Preserve its raw evidence, and use separate raw listings for
different sellers/products/variants so historical captures retain their identity.

## Deduplication rule

Listings are duplicates only when all of these source identifiers match:

- `source_key`
- Hostname from `source_url`
- `source_product_id`
- `source_variant_id`

The variant identifier may be null for a source listing without separate
variant IDs, such as a supermarket SKU. Two null variant IDs can match when
the other three identifiers agree; missing source, hostname, or product IDs
prevent a merge.

The rule applies within one selling source. The hostname prevents unrelated
websites that use the same source label from merging. Listings without enough
source identity remain separate. Merge only on the source identifiers,
regardless of name, product brand, GTIN, weight or recipe. The canonical listing
ID is the first raw listing folder name in sorted order; `source_listing_ids` retains all member
folder IDs.

The same product sold by two retailers remains two unique listings. A product
sold directly by its brand and by a retailer also remains two unique listings.
`source_role` describes the selling source as `brand`, `retail`, or `unknown`;
the product's `brand` is a separate field. Unresolved source roles remain
`unknown`.

## Output contract

| File | Meaning |
| --- | --- |
| `products.jsonl` | All canonical seller listings, their source identifiers and role, original captures, and latest capture ID. |
| `brand/products.jsonl` | Listings sold by direct brand store sources. |
| `retail/products.jsonl` | Listings sold by retailer sources. |
| `unknown/products.jsonl` | Listings with an unresolved role of the selling source. |
| `listing-aliases.jsonl` | Each accepted raw listing folder ID mapped to its canonical listing ID. |
| `quality-report.json` | Input and canonical listing counts, coverage of source roles, duplicate groups, and unsupported or invalid archive records and imports in progress. |
| `manifest.json` | Dataset format/version, implementation and input hashes, and generated file hashes. |

Read JSONL files one JSON object per line. The combined product file includes
all source roles, and every role partition is emitted even when empty.

Each product row contains `listing_id`, `source_listing_ids`, `source_role`,
`brand`, `retailer`, source identifiers, `captures`, and `latest_capture_id`.
`captures` contains the original capture objects from all member listings.
Captured `raw_record.product_id` values retain their original raw listing IDs;
they are not rewritten to the canonical listing ID. All timestamps, source
values, arbitrary source sections, and history/artifact references remain
available in those capture objects.

This layer does not extract, normalize, or deduplicate price observations.
Repeated imports remain represented by their original capture histories. The
later analytical cleanup may consolidate identical price observations while
retaining their evidence. Both operations keep seller listings separate across
shops.

After deduplication, the shared source adapter used by Silver and compatibility
cleanup applies the [chocolate type rules](chocolate-schema.md#chocolate-type-from-product-names)
for blonde names and explicit mixed selections to each preserved capture.

## Evidence and coverage

Source artifacts, images, and immutable history files remain in the raw archive;
the snapshot retains references to them instead of copying or replacing their
bytes. Manifest input hashes cover the product indexes and referenced history
records. Full verification of source/image artifacts requires the archive
integrity tools.

Unsupported formats, imports in progress, and invalid archive records are
reported for review and excluded from valid products. The quality report distinguishes accepted raw listing folders from canonical seller
listings and records the exact duplicate groups. Those counts describe source
listings. Distinct physical products and exhaustive market coverage require
separate verification.

The CLI exits with 0 for a complete snapshot, 1 for a partial snapshot with
reported gaps, and 2 when the build cannot complete.

Run deduplication checks in the locked development environment:

```sh
uv sync --locked
uv run pytest scripts/tests/test_deduplication.py
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
