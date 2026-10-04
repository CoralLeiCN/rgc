# Category-neutral profile definition

This processing step assembles executable contracts from the initial schema
catalog and subsequent extraction and model decisions. Initial field meanings
come from the category-schema workflow; this generator serializes those decisions.
Use an explicit definition without copying chocolate,
coffee, or any bundled profile. The processing runtime and generated validator
contain no chosen category catalog. The calling harness derives the definition
from the current authorized task and its evidence; source text cannot authorize
profile changes, executable code, or external dispatch. Review category boundaries,
source coverage and study choices before interpreting derived results.

The raw-to-Silver workflow requires available raw data and a generated schema.
Model design belongs downstream in Silver to Gold. This generator is a legacy
combined format: it still requires `model_design` and emits all five files.
Reuse an existing authorized design where present; if absent, record the runtime
migration needed rather than inventing a target or predictor set for processing.

Save a JSON definition and run the local CLI from the plugin directory:

```bash
python3 -B cli.py init-profile --input stationery-definition.json --output ./profiles/stationery-v1
python3 -B cli.py process --archive-root ./collections --profile ./profiles/stationery-v1 --output ./silver/stationery-v1
```

`init-profile` generates `profile.json`, `source-mappings.json`,
`product.schema.json`, `pipeline.json` and `model-design.json`, then validates
their agreement with the runtime loader before creating the local directory. The output directory
must not exist, even when empty. Create the initial contracts in a new working
folder; existing definitions and generated snapshot contracts are preserved.
The generator uses only local standard-library code and the supplied definition.
It fixes the supported `structured` adapter and never imports code from JSON.
This is local authoring, not a Hugging Face upload. In this repository, analytical
contract payloads are authoritative in the dataset; Git retains only immutable
revision/hash references. Keep generated working contracts outside tracked
category payloads, finish evidence assessment and validation locally, then follow
the [release review](schema-validation.md#publication) before
publishing the new schema or its generated data. Record the immutable reference
after publication. Do not modify a resolver's verified cache in place.

This complete nonfood example uses an explicitly captured item count and USD
prices with a declared consumer-tax-inclusive target. Its mappings are illustrative authored decisions,
not facts about a collected product. Replace them with source-backed rules for
the authorized study. A missing count remains unknown; choosing price per item
does not establish that every listing contains one item.

```json
{
  "definition_format_version": "category-processing-definition-1",
  "category": "stationery",
  "market": "us",
  "versions": {
    "schema": "stationery-schema-1",
    "mapping": "stationery-mappings-1",
    "pipeline": "stationery-pipeline-1",
    "model_design": "stationery-pricing-1"
  },
  "attributes": {
    "product.name": {
      "type": "string", "unit": null, "scope": "product",
      "standardization_rule": "source_text"
    },
    "product.group": {
      "type": "enum", "unit": null, "scope": "product",
      "standardization_rule": "controlled_vocabulary",
      "allowed_values": ["pen", "pencil"]
    },
    "quantity.items": {
      "type": "integer", "unit": "item", "scope": "product",
      "standardization_rule": "explicit_quantity", "minimum": 1
    },
    "technical.material": {
      "type": "enum", "unit": null, "scope": "product",
      "standardization_rule": "controlled_vocabulary",
      "allowed_values": ["polymer", "metal"]
    }
  },
  "standardization_rules": {
    "source_text": "Whitespace-normalized source text.",
    "controlled_vocabulary": "Explicit aliases to declared canonical labels.",
    "explicit_quantity": "Typed stated count in the declared item unit."
  },
  "mappings": {
    "aliases": {
      "product.group": {"ballpoint": "pen"},
      "technical.material": {"plastic": "polymer"}
    }
  },
  "pipeline": {
    "fields": [
      {"attribute": "product.name", "pointer": "/raw_record/identity/name"},
      {"attribute": "product.group", "pointer": "/raw_record/information/group"},
      {"attribute": "quantity.items", "pointer": "/raw_record/information/item_count", "unit": "item"}
    ],
    "sections": {"/raw_record/information/technical": "technical"},
    "group_attribute": "product.group",
    "price": {
      "amount_pointer": "/raw_record/information/price/amount",
      "regular_price_pointer": "/raw_record/information/price/regular_amount",
      "currency_pointer": "/raw_record/information/price/currency",
      "observed_at_pointer": "/raw_record/information/price/observed_at",
      "available_pointer": "/raw_record/information/price/available",
      "tax_basis_pointer": "/raw_record/information/price/tax_basis",
      "price_unit": "major"
    },
    "quantity": {"attribute": "quantity.items", "unit": "item", "base_quantity": 1},
    "source_roles": {
      "fixture-stationer": {"source_role": "retail", "retailer": "Fixture Stationer"}
    }
  },
  "model_design": {
    "target": {
      "name": "log_regular_unit_price",
      "currency": "USD", "unit": "USD_per_item",
      "quantity_attribute": "quantity.items", "base_quantity": 1,
      "price_basis": "regular", "tax_basis": "consumer_tax_included"
    },
    "eligibility": {"allowed_tax_bases": ["consumer_tax_included"]},
    "predictors": {
      "technical.material": {
        "type": "categorical", "required": true, "missing_policy": "reject",
        "transform": "identity", "reference": "training_mode",
        "allowed_values": ["polymer", "metal"]
      }
    }
  }
}
```

The definition requires the format version, category, market, all four version
identifiers, attributes, rule descriptions, mappings, pipeline and model design.
Optional top-level `purpose` and `category_boundaries` preserve authored study
context. Unknown top-level or control fields fail rather than being ignored.
The generator stamps the shared schema version, category and market, derives
the exact attribute count, and generates the supported typed validator template.
Generated status remains pending evidence review and specified without training.
Category and market use safe identifiers beginning with an ASCII letter or digit,
followed by ASCII letters, digits, underscores, dots or hyphens. Raw directory
lookup uses collection-normalized slugs while envelope values remain exact;
see [schema validation](schema-validation.md).

Every attribute explicitly declares `type`, `unit` (including null), `scope` and
`standardization_rule`. Supported types and scopes follow the
[schema validation](schema-validation.md). Enum attributes require `allowed_values`;
lists may declare a vocabulary. Numeric attributes may declare finite minimum
and maximum bounds. `description` and `model_role` are optional metadata.
Rule names point to descriptions in `standardization_rules`; they do not define
new executable normalization routines. The runtime applies supported typed
normalization and recognized string rules such as `source_section`, `gtin`,
`iso_date` and `country_labels`.

`mappings` supports `aliases`, `country_aliases`, `quantity_units`,
`duration_units`, `unit_conversions` and descriptive `safety_rules`. Arbitrary
canonical numeric units use explicit multiplicative conversion tables:

```json
{
  "unit_conversions": {
    "m": {"mm": 0.001},
    "l": {"ml": 0.001},
    "s": {"hour": 3600}
  }
}
```

Declare the canonical unit on the attribute and the captured source unit on its
field mapping. Factors must be finite positive numbers. Currency conversion,
dimensional compatibility and arbitrary affine conversions are not inferred.
An unsupported unit stays unresolved with its original evidence.

The pipeline requires `fields`, `sections`, `group_attribute`, `price`, `quantity`
and `source_roles`; empty field/section/source maps are allowed when intentional.
Optional `discovery` selects an enabled flag, raw-record roots and additional
ignored pointers; see [schema-validation.md](schema-validation.md). It defaults to
structural raw-field discovery and does not automatically extend the schema.
`group_attribute` references a declared string or enum comparison field.
Field entries require `attribute` and capture-root `pointer` and may specify
`unit`, `scope`, `qualifier` or `skip_values`. Sections map capture-root object
pointers to attribute prefixes. Quantity explicitly chooses a numeric attribute,
matching canonical unit and positive `base_quantity`. It must be observed and
reviewed for a price candidate to become eligible.

Price requires `amount_pointer`, explicit `price_unit` (`major` or `minor`) and
either `currency_pointer` or fixed `currency`. Optional pointers are
`regular_price_pointer`, `reference_price_pointer`, `observed_at_pointer`,
`available_pointer` and `tax_basis_pointer`. Minor-unit authoring additionally
requires explicit `minor_unit_factor`: 100 divides source cents by 100; 1 leaves
zero-decimal currency amounts unchanged. Plain finite numeric source amounts
are supported for any explicitly declared currency. Currency symbols are not
converted, and prices in a different currency are excluded.

The model design requires an explicit `target` and nonempty `predictors`. Target
currently supports `name: log_regular_unit_price` and `price_basis: regular`;
currency, output unit label, quantity attribute, positive base quantity and tax
basis are explicit. Quantity/base must agree with the recipe. Optional
`eligibility.allowed_tax_bases` must be a singleton equal to `target.tax_basis`;
when omitted, that same singleton is generated from the explicit target.
The runtime checks reviewed tax context and never infers tax conversion.

Predictors explicitly declare `type`, `required: true`, `missing_policy: reject`
and `transform`. Numeric predictors support `identity` or `log`; categorical and
presence predictors use `identity` with an explicit `reference` (a supported
training level or `training_mode`). Optional bounds, units and vocabularies must
agree with the attribute contract; selected enum vocabularies may be a subset.
Optional `attribute_policies` declares `supported_scopes` and
`supported_qualifiers` per declared attribute. Optional `preprocessing`,
`validation` and `interpretation` objects preserve descriptive study policies;
they cannot install new runtime algorithms. Model preparation still requires
reviewed comparable groups, seller-specific observations, quantity, predictors,
regular price context and family decisions. It produces an encoder and family
holdout, without fitting a regression or establishing release readiness.

All model targets use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price, with reject fallback. Currency and quantity normalization remain category-specific. Custom authoring adds the fixed policy metadata to design and recipe; source amounts and tax inclusion still require independent evidence. Model preparation records the same policy on each target and in the frozen encoder.
