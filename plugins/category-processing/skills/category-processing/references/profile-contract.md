# Profile contract

The [standard Silver v2 reference](standard-silver.md) owns default `process`,
four-contract authoring, durable human corrections and generated reports. This
reference preserves the historical v1 interface and applicable research guidance;
use `process --legacy` for v1 outputs. Gold owns model policy in the v2 workflow.

Use the [category-schema skill](../../category-schema/SKILL.md) to create a new
analytical schema. Existing-schema changes follow
[mapping maintenance](mapping-maintenance.md). This reference owns runtime loading and consumption
of existing profiles. Choose a supplied profile for the requested category/market
or resolve a packaged category with
`category_processing.profiles.resolve_profile(category="coffee")`. Packaged
references live in `profiles/<category>/dataset-contract.json`; their five JSON
payloads live under `contracts/category-processing/<category>/` in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Each reference pins a full immutable commit revision, source paths, SHA-256 hashes
and byte lengths. The portable resolver checks every file and rechecks any cache
on use. It rejects mutable revision references and corrupt cache content.
`--contracts-cache` selects the cache, and `--offline` requires verified cached
bytes without downloading.

Processing owns working-copy contract assembly and generation from an explicit
[definition](profile-definition.md), using the initial schema catalog and the
subsequent extraction and model decisions. A custom directory without `dataset-contract.json` supports local
loading. Verified caches and immutable snapshots retain their exact contracts.
Published analytical payloads are authoritative in the Hugging Face dataset;
Git retains immutable revision/hash references. The five files own these runtime
decisions:

| File | Owns |
| --- | --- |
| `profile.json` | Category/market, schema version, types, units, vocabularies, scopes, qualifiers and standardization rules. |
| `source-mappings.json` | Mapping version, aliases to declared canonical values and normalization policies. |
| `product.schema.json` | Product envelope and exact complete attribute catalog. |
| `model-design.json` | Design version, target basis, selected predictors, eligibility and preprocessing/interpretation policies. |
| `pipeline.json` | Recipe version, raw pointers, adapter, source roles and price/quantity extraction. |

All five agree on schema version; profile and recipe agree on category/market.
Declared enum/list vocabularies require unique nonempty labels.
Counts, validator properties/required fields, aliases and predictors refer to the
same declared catalog. Version the contract whose meaning changes and rebuild.
Never edit a generated output's copied contracts to change its meaning.

The bundled chocolate selected model/recipe are
`chocolate-processing-pricing-design-2` / `chocolate-processing-pipeline-2`;
coffee uses `coffee-pricing-design-2` / `coffee-processing-pipeline-2`.
Their existing schema and mapping versions are retained because the tracked
attribute meanings and aliases are unchanged.

Loading checks category/market constants and each attribute's declared type,
unit, enum/list vocabulary and numeric bounds against both the nullable value
branch and the condition for known values in `product.schema.json`. Drift
fails before publishing a snapshot. The runtime supports the explicit typed
template used by the pinned validators; it rejects unsupported value constraint
keywords rather than acting as a general JSON Schema executor.

Selected numeric/categorical/presence predictors must use compatible profile
types and units; declared predictor vocabularies may be a subset of the profile's
allowed values. Keep this narrower study domain deliberate. A valid category
value outside the selected model domain stays in silver and its candidate is
excluded with `model_predictor_outside_design_domain:<attribute>`; it does not
abort processing or require adding a misleading taxonomy value. This declared
model domain is separate from support learned later from training rows.

Attribute types are string, number, integer, boolean, enum and string_list.
Values preserve unit, scope, qualifier, evidence, method, review status and
`known`, `unknown`, `not_applicable` or `conflict` status. Unknown/conflict values
are null. Presence/absence needs evidence. Scopes are product, ingredient, brand,
packaging, packaging_component and observation. Minimum, conditional and component
claims cannot become exact facts about the whole product.

The recipe uses `pipeline_format_version: category-processing-profile-1` and
adapter `structured` or `chocolate`. It is configuration, not arbitrary Python
imports. Structured extraction uses JSON pointers rooted in captures:

```json
{
  "fields": [
    {"attribute": "quantity.net_weight_g", "pointer": "/raw_record/information/net_weight_g", "unit": "g"}
  ],
  "sections": {"/raw_record/information/coffee": "coffee"},
  "quantity": {"attribute": "quantity.net_weight_g", "unit": "g", "base_quantity": 100}
}
```

This is a fragment of a complete recipe. Field entries may specify scope and
qualifier; sections map structured objects to attribute families. `source_roles`
maps exact source keys to role/retailer; brand does not establish retailer role.
`group_attribute` identifies the declared comparable-group field. New category
definitions require it explicitly; older recipes default to
`identity.product_group`. `price` declares amount, optional regular price, currency, observation time,
availability and tax pointers, optional fixed currency and explicit major/minor
money units. For structured minor-unit money, `minor_unit_factor` is the positive
divisor converting to major units; omitted legacy values use 100. Major prices
are unchanged. Quantity uses a numeric declared attribute/unit and positive base.
It may describe items, packs, mass, volume, length or time. No default count is
inferred. `unit_conversions` maps a canonical unit to source-unit multipliers;
choose conversions supported by the category and source evidence.
Structured money accepts positive plain decimal amounts in the explicit currency.
Locale punctuation or symbols are not parsed; legacy £/GBP prefixes require an
explicit GBP observation. Invalid derived money stays null with its raw evidence
preserved.

Model `eligibility.allowed_tax_bases` selects exactly one resolved reviewed basis;
the default for older designs is `consumer_tax_included`. `target.tax_basis`, when
present, must match. A separate study may select `consumer_tax_included` or
another evidenced basis. The engine does not normalize taxes or exchange rates
or pool incompatible price bases.

Every `model-design.json` target and `pipeline.json` `price.target_policy` must
declare the shared final monetary basis:

```json
{
  "price_basis_contract_version": "regular-consumer-price-1",
  "price_basis": "regular",
  "tax_basis": "consumer_tax_included",
  "promotion_basis": "non_promotional",
  "fallback_policy": "reject"
}
```

Profile loading rejects missing or alternative bases. Category targets additionally
declare `name: log_regular_unit_price`, currency, unit, quantity attribute and
positive base quantity; quantity attribute/base must match the recipe. A source's
displayed/reference price cannot become a regular target by default. Reviewers
may establish that a displayed amount is also the regular non-promotional
tax-inclusive amount only when the cited source independently supports that
decision. A separately supported regular amount remains usable during a displayed
promotion. Do not reconstruct a regular amount from discount arithmetic or assume
tax inclusion from a taxable flag.

Conversions require declared units or supported source structure: g/kg/mg mass,
recognized duration/temperature units, currency major/minor units, validated
GTINs, ISO dates and supported country aliases. Ambiguous freeform values,
shipping weights and unfamiliar sections are retained rather than silently
coerced. Keep unsupported values, product types/tags and structured fields as
unmapped claims with evidence. Chocolate uses conservative source-specific
parsing; coffee demonstrates structured extraction, not broad coffee coverage.

For chocolate names, "Blonde Chocolate" and "Blond Chocolate" yield `blonde`.
Coordinated distinct types in selections, assortments, collections, mixes,
bundles, sets or gift bags/boxes yield `mixed`; supported examples include "Milk
Chocolate and Dark Chocolate Selection", "Milk & Dark Chocolate Selection"
and "Milk, Dark & White Chocolate Selection". Repeated mentions of one type
retain that type. Ambiguous component/chip mentions and selections without
explicit types remain unresolved. Assertions retain the original name and
capture pointer and remain unreviewed. The existing profile, aliases, validator
and model design already permit `blonde` and `mixed`; rebuilt processing
fingerprints record the changed adapter implementation.

Known-field gap detection reaches configured pointers/sections and supported
parser cases. Structural discovery also records meaningful source subtrees
outside that coverage, preserving their full typed values and evidence pointers.
Audit section coverage and sample original evidence before claiming complete
classification for a new category or source; concepts hidden inside already-used
prose still need separate investigation.

Optional `pipeline.json` `discovery` settings contain `enabled` (default `true`),
`roots` (a nonempty list, default `["/raw_record"]`) and `ignore_pointers` (extra
exact source paths excluded alongside known identity/provenance metadata).
All roots and exclusions must be JSON pointers within `/raw_record`. Explicit
field mappings and selected sections remain extraction coverage. Version the
recipe when changing these discovery boundaries; the quality report records the
effective policy. See [schema discovery](schema-discovery.md) for review outputs,
unresolved semantic scope and durable proposal guidance.

Reviews use the recipe's format, normally `category-processing-reviews-1`;
chocolate also accepts its documented legacy format. Use actual listing/price
keys, reviewer, reason and valid capture/pointer evidence. Prefer stable
`seller_uid` for product keys; canonical listing IDs and retained raw aliases are
accepted for compatibility. Conflicting decisions for aliases of one seller are
rejected. Attribute reviews
provide typed value/status and scope/qualifier; identity reviews establish
study scope, variant and family; prices establish regular price, currency, aware
time, availability and tax basis. Inspect output records and design before
reviewing. Reviews cannot borrow another seller's capture or bypass feature,
quantity and price observation gates.

Review is an evidence assessment by the calling agent within the authorized
study, not a required user approval. User review or confirmation is not required
for local authorized schema, mapping or parser maintenance. Before a Hugging Face
commit or publication carrying a changed schema or its rebuilt data, complete
the local contracts and checks, present the detailed release summary, and wait
for user authorization of that release; see
[mapping maintenance](mapping-maintenance.md#hugging-face-release-review).
The `reviewed_by` value identifies the agent or other actual reviewer; valid
source support and all eligibility checks still apply.

An illustrative partial coffee review is below. Replace seller/observation/
capture IDs with actual output IDs and each value/pointer with decisions supported
by evidence; the examples illustrate the format and must be replaced with facts
from collected products.

```json
{
  "review_format_version": "category-processing-reviews-1",
  "products": {
    "seller-<actual-uid>": {
      "variant_id": "<reviewed-physical-variant>",
      "family_id": "<reviewed-family>",
      "in_scope": true,
      "reviewed_by": "<reviewer>",
      "reason": "The captured identity establishes the reviewed study boundary and relationships.",
      "evidence": [{"capture_id": "<actual-capture>", "pointer": "/raw_record/identity"}],
      "attributes": {
        "quantity.net_weight_g": {
          "value": 250,
          "status": "known",
          "unit": "g",
          "scope": "product",
          "qualifier": "exact",
          "reviewed_by": "<reviewer>",
          "reason": "The stated net product weight applies to this observation.",
          "evidence": [{"capture_id": "<actual-capture>", "pointer": "/raw_record/information/net_weight_g"}]
        }
      }
    }
  },
  "prices": {
    "observation-<actual-id>": {
      "regular_price": 6.5,
      "currency": "GBP",
      "tax_basis": "consumer_tax_included",
      "observed_at": "2026-10-03T07:00:00Z",
      "available": true,
      "reviewed_by": "<reviewer>",
      "reason": "The capture establishes the regular consumer price, time and availability.",
      "evidence": [{"capture_id": "<actual-capture>", "pointer": "/raw_record/information/price"}]
    }
  }
}
```

Partial reviews are allowed and improve reviewed coverage without making a row
eligible. Eligibility additionally needs every selected predictor, quantity,
comparable category group and identity/scope decision, plus full price context.
Selected features and quantity must cite the price observation's capture with
supported product scope/qualifiers. The chocolate design requires an exact cocoa
percentage for the whole product. A pointer resolving successfully is
necessary, but the reviewer must also verify that it supports the stated decision.

All model targets use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price, with reject fallback. Currency and quantity normalization remain category-specific. Custom authoring adds the fixed policy metadata to design and recipe; source amounts and tax inclusion still require independent evidence. Model preparation records the same policy on each target and in the frozen encoder.
