# Project intent

Status: maintained project view. The canonical scope is
[docs/intention.md](../intention.md).

## Problem and outcome

Collected product evidence is too inconsistent for dependable pricing analysis
without source preservation, seller-specific deduplication, standardization,
and review. Build reusable category research and feature classification, then
support an interpretable pricing model and a brand's new-product price test.
Chocolate sold in the UK is the first study.

The requested chocolate workflow has raw and one combined silver layer. Raw
preserves original evidence. Silver performs seller-specific deduplication,
versioned schema/unit/vocabulary standardization, price normalization, evidence
review and model-input eligibility in one build. It tracks broad source-supported
product information and supplies a consistent contract for pricing inputs and
interpreted insights; persistent intermediate layers are not required.

Package the whole post-collection method in a self-contained
[category-processing plugin](../category-processing.md), with category profiles,
stable seller identity, typed processing, a capture/rules ledger, grouped mapping
gaps, a calling-harness maintenance skill and model-input preparation. Normalize
under frozen versions first, propose evidence-backed improvements, then rebuild
affected history while preserving raw evidence and immutable training snapshots.

## Constraints

- Preserve original captures and evidence. Author repository content in English;
 retain original source wording in its original language.
- Deduplicate only within a selling source. Keep products sold by different
 shops unique, and expose direct brand-store and retail data separately.
- Keep source claims, derived interpretations, reviewed facts, and model inputs
 distinguishable. Unknown evidence cannot establish absence.
- Validate model support and uncertainty before supported price testing;
 regression associations do not establish causal effects.
- Keep value-for-money scoring deferred pending the research in the canonical
 [specification](../spec.md). Maintain documentation in the same change as
 behavior under the [documentation policy](../documentation-policy.md).

## Remaining decisions

Source coverage, reviewed study boundaries, extraction evaluation thresholds,
and numerical model release thresholds remain to be resolved before release.
The schema and combined silver dataset can be built now while these data and
validation decisions remain visible. The [silver guide](../chocolate-silver.md)
documents each layer's responsibilities.

Next document: [Requirements and design](spec.md).
