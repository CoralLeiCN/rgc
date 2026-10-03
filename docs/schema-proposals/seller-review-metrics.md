# Proposal: seller review metrics

Status: proposed; pending agent evidence and contract assessment. User review or
approval is not required under the
[standing maintenance decision](../decisions/agent-led-schema-maintenance.md).
No attributes, mappings,
model predictors or existing datasets are changed by this document.

## Why investigate

The preserved archive contains a product's seller-reported review rating and
count outside the configured extraction sections. These describe a dated seller
observation and could be useful across categories. They are not product quality
measurements or independently verified customer feedback.

The existing chocolate adapter was run against the capture below. It returned
identity, composition and price candidates, but no rating or review-count
candidate. Neither metric appears in the current chocolate attribute catalog.

## Original evidence

Source listing: `chocolate-shop-14974681809269-55180038668661`.
Capture: `20261003T081437558349Z-efc34e4da7-000245`.
Source URL: <https://chocolate-shop.co.uk/products/vietnamese-dark-milk-chocolate>.

The discovery pass retains the complete parent array at
`/raw_record/information/page_structured_data_json_ld`, with stable candidate ID
`source-field-fe0ef164bfe65910b62b47c9` in `category-unmapped-fields-1`.
This structural candidate contains the metrics below; its identity does not
establish a canonical review concept. The proposal reviews the immutable raw
capture, not a migrated or accepted silver schema.

The local preserved record is
`/Users/coral/repos/rgc/data/collections/chocolate/uk/products/chocolate-shop-14974681809269-55180038668661/product.json`.
The following pointers are relative to the capture; prefix `/captures/0` when
resolving them against that product file.

| Capture-relative pointer | Exact raw value |
| --- | --- |
| `/raw_record/information/page_structured_data_json_ld/2/name` | `"Vietnamese 48% Cacao Milk Chocolate"` |
| `/raw_record/information/page_structured_data_json_ld/2/aggregateRating/ratingValue` | `"5.0"` |
| `/raw_record/information/page_structured_data_json_ld/2/aggregateRating/reviewCount` | `"1"` |
| `/raw_record/information/page_structured_data_json_ld/2/aggregateRating/worstRating` | `"1.0"` |
| `/raw_record/information/page_structured_data_json_ld/2/aggregateRating/bestRating` | `"5.0"` |

These are source JSON strings. Numeric normalization would be a new derived
interpretation and must retain each string and pointer as evidence. The same
rating object also appears in the preserved embedded JSON-LD representation;
duplicate representations do not represent additional reviews.

## Proposed interpretation

| Proposed attribute | Type | Unit | Scope |
| --- | --- | --- | --- |
| `reviews.rating_value` | number | source rating scale | observation |
| `reviews.rating_scale_min` | number | source rating scale | observation |
| `reviews.rating_scale_max` | number | source rating scale | observation |
| `reviews.review_count` | integer, minimum 0 | count | observation |

Use `observation` scope with the qualifier identifying the seller, matched source
product and capture. A product-level aggregate must not be silently assigned to
an individual variant or combined with another seller's aggregate. Preserve the
scale, rather than assuming every source uses five stars. A missing scale remains
unknown. Verify that the JSON-LD product name, identifier or URL refers to the
listing being processed; unrelated recommendations and organization ratings
must not supply product metrics.

Record conflicting visible-text and structured-data values for review. Reject
nonfinite ratings, fractional or negative counts, reversed bounds and ratings
outside declared bounds. A count of one must remain one. Collection time does
not establish the date of the reviews or a last-updated date for the aggregate.

The default model role should be `context`, outside the selected predictors. Any
later predictor selection needs separate justification, including seller coverage,
scale compatibility, low-count uncertainty and temporal leakage checks.

## Change and validation required before adoption

Update the selected profile's five contracts together: define attributes in
`profile.json`; record numeric normalization in `source-mappings.json`; add typed
value validation in `product.schema.json`; add product-matched extraction and
raw pointers in `pipeline.json` or its reviewed adapter; keep these fields
explicitly excluded in `model-design.json`. Version the affected meanings and
update canonical documentation and lifecycle status. Do not modify prior
training snapshots.

Tests should cover exact numeric strings, declared non-five-star scales, zero
review count, malformed/fractional counts, missing bounds, unrelated products,
multiple variants, duplicate representations and conflicting aggregates. Compare
the resulting review queue and coverage with the unchanged build before accepting
the extension.
