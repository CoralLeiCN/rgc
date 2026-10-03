# Proposal: source selling-plan terms

Status: proposed; pending agent evidence and contract assessment. User review or
approval is not required under the
[standing maintenance decision](../decisions/agent-led-schema-maintenance.md).
No schema extension or
subscription price normalization has been implemented by this document.

## Why investigate

Some preserved product variants include selling-plan requirements and allocations
outside configured extraction sections. Keeping these terms separately would
help distinguish ordinary purchases from conditional prices across categories.
It would also prevent a lower conditional price from silently replacing an
ordinary purchase price.

The current chocolate adapter was run against the example below. It emitted no
selling-plan feature or price from this variant representation. Its integer
prices have no configured major/minor currency basis, so they must remain raw
until a reviewed source rule establishes that basis.

## Original evidence

Source listing: `firetree-6690202583110-41129638625350`.
Capture: `20261003T102806952639Z-f16e455975-000016`.
Source URL:
<https://firetreechocolate.co.uk/products/hispaniola-dominican-republic-72-cocoa?variant=41129638625350>.

For this capture, the discovery pass retains the complete parent object at
`/raw_record/information`, with stable candidate ID
`source-field-6781cbcb04fbde809ba88480` in `category-unmapped-fields-1`.
The selling-plan evidence below remains intact within that broader structural
candidate. The proposal reviews the immutable raw capture, not a migrated or
accepted silver schema.

The local preserved record is
`/Users/coral/repos/rgc/data/collections/chocolate/uk/products/firetree-6690202583110-41129638625350/product.json`.
The following pointers are relative to the capture; prefix `/captures/0` when
resolving them against that product file.

| Capture-relative pointer | Exact raw value |
| --- | --- |
| `/raw_record/identity/source_variant_id` | `"41129638625350"` |
| `/raw_record/information/original_source_page_variants/0/id` | `41129638625350` |
| `/raw_record/information/original_source_page_variants/0/requires_selling_plan` | `false` |
| `/raw_record/information/original_source_page_variants/0/selling_plan_allocations/0/selling_plan_id` | `829292614` |
| `/raw_record/information/original_source_page_variants/0/selling_plan_allocations/0/price` | `379` |
| `/raw_record/information/original_source_page_variants/0/selling_plan_allocations/0/compare_at_price` | `395` |
| `/raw_record/information/original_source_page_variants/0/selling_plan_allocations/0/per_delivery_price` | `379` |

The source represents other allocation IDs as `829358150` and `893878342` at
allocation indices 1 and 2 respectively. Their presence does not establish the
delivery interval, renewal terms or cancellation policy.

## Proposed interpretation

| Proposed attribute | Type | Unit | Scope |
| --- | --- | --- | --- |
| `commerce.requires_selling_plan` | boolean | none | observation |
| `commerce.source_selling_plan_ids` | string_list | none | observation |

Retain the seller, selected source variant and capture in the qualifier. Match
the variant ID explicitly; index zero is specific to this evidence example and
must not become a general extraction rule. Normalize identifiers to strings
without claiming their meanings. An explicit `false` requirement does not mean
that selling plans are absent. Missing allocations do not prove absence of a
subscription option. Do not infer subscription cadence from a plan identifier.

Keep the model role `context`, outside the selected predictors. If conditional
price observations are later supported, each observation needs its source plan ID,
purchase condition, currency/unit basis and source timing. Price target
eligibility must explicitly decide whether those conditions are comparable.

## Related rejected shortcut

The same capture records
`/raw_record/information/original_source_page_variants/0/weight` as `86`, while
`/raw_record/information/source_information_sections/1/derived_text` is exactly
`"70g Dark Chocolate Bar"`. The logistics-like weight cannot establish edible
mass. The existing adapter deliberately excludes Shopify grams from edible-mass
normalization. Discovery should preserve such values for basis review; it must
not treat every unseen numeric field as an acceptable quantity mapping.

## Change and validation required before adoption

Update the selected profile's five contracts together: add the two typed
attributes to `profile.json` and `product.schema.json`; define identifier and
boolean handling in `source-mappings.json`; specify matched-variant extraction
and evidence pointers in `pipeline.json` or its reviewed adapter; preserve
exclusion in `model-design.json`. A recipe capable of matching list entries by
variant ID is required; fixed list indices are insufficient. Conditional price
support would additionally require an explicit price-observation contract and
eligibility change, and is a separate proposal.

Tests should cover reordered variants, false versus missing requirements,
matching allocation IDs, malformed identifiers, multiple plan allocations,
unconfirmed integer currency units and an ordinary price coexisting with plan
prices. Verify that shipping weights remain excluded from edible quantity and
that reviewed model inputs retain their existing price basis. Version accepted
rules, update canonical documentation and lifecycle status, compare outputs and
preserve immutable prior training snapshots.
