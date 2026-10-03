# Profile contract

Choose a supplied profile or copy a starter into a separately versioned profile
directory. The five JSON files own separate decisions:

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

Loading checks category/market constants and each attribute's declared type,
unit, enum/list vocabulary and numeric bounds against both the nullable value
branch and the known-status value condition in `product.schema.json`. Drift
fails before publishing a snapshot. The runtime supports the explicit typed
template used by the bundled validators; it rejects unsupported value-constraint
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
claims cannot become exact whole-product facts.

The recipe uses `pipeline_format_version: category-processing-profile-1` and
adapter `structured` or `chocolate`. It is configuration, not arbitrary Python
imports. Structured extraction uses capture-root JSON pointers:

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
`price` declares amount, optional regular price, currency, observation time,
availability and tax pointers, optional fixed currency and explicit major/minor
money units. Quantity uses a numeric declared attribute/unit and positive base.

Conversions require declared units or supported source structure: g/kg/mg mass,
recognized duration/temperature units, currency major/minor units, validated
GTINs, ISO dates and supported country aliases. Ambiguous freeform values,
shipping weights and unfamiliar sections are retained rather than silently
coerced. Keep unsupported values, product types/tags and structured fields as
unmapped claims with evidence. Chocolate uses conservative source-specific
parsing; coffee demonstrates structured extraction, not broad coffee coverage.
Gap detection reaches configured pointers/sections and supported parser cases;
fields outside that coverage remain raw and may not create a review batch.
Audit section coverage and sample original evidence before claiming complete
classification for a new category or source.

Reviews use the recipe's format, normally `category-processing-reviews-1`;
chocolate also accepts its documented legacy format. Use actual listing/price
keys, reviewer, reason and valid capture/pointer evidence. Prefer stable
`seller_uid` for product keys; canonical listing IDs and retained raw aliases are
accepted for compatibility. Conflicting decisions for aliases of one seller are
rejected. Attribute reviews
provide typed value/status and scope/qualifier; identity reviews establish
in-scope, variant and family; prices establish regular price, currency, aware
time, availability and tax basis. Inspect output records and design before
reviewing. Reviews cannot borrow another seller's capture or bypass feature,
quantity and price observation gates.

An illustrative partial coffee review is below. Replace seller/observation/
capture IDs with actual output IDs and each value/pointer with evidence-backed
decisions; these examples are not reusable facts about collected products.

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
supported product scope/qualifiers. Whole-product cocoa requires an exact
percentage in the chocolate design. A pointer resolving successfully is
necessary, but the reviewer must also verify that it supports the stated decision.
