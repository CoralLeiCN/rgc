# Silver to Gold and model-input preparation

## Standard Silver input

`prepare-gold` consumes a verified Silver v2 snapshot and a separate study design:

```text
python3 <plugin-root>/cli.py prepare-gold --silver-root <silver> --model-design <design.json> --relationships <relationships.json> --output <gold-preparation>
```

The design names the Silver schema version, selected predictors and explicit
current or regular consumer-price target, currency, quantity attribute and base
quantity. `silver_contexts` selects scope/qualifier/basis per field. Unspecified
fields require product scope and an unconditional qualifier. Multiple compatible
contexts remain unresolved until a selection is declared. `comparison_rule:
chocolate_name_group-1` enables the chocolate name rule downstream in Gold.
`accepted_silver_methods` selects usable methods and defaults to parsed, inferred
and reviewed. This study rule affects Gold inputs and leaves Silver facts intact.
Source time and availability are required by default. Regular-price studies keep
their confirmed tax basis; current-price studies add no regular-price, promotion
or confirmed-tax gate. No currency conversion or missing-value imputation occurs.

`category-gold-relationships-1` contains an `assignments` array. Each assignment
supplies `subject_id`, stable `family_id`/`variant_id`, `name_guard`, `source`,
`reviewed_by` and `reason`. References must match the subject's Silver evidence.
Missing relationships become eligibility reasons without merging seller rows.

The immutable preparation stores candidates, selected model inputs, price targets,
a separate eligibility audit, design, relationships, exact Silver copies and a
manifest. It fits no model. The repository chocolate builder consumes this
preparation and writes immutable Parquet candidate and selected-input tables;
the portable package itself uses the standard library and writes JSONL.

See [standard Silver](standard-silver.md) for the upstream contract. The remainder
of this reference describes the historical `prepare-model` helper and its fixed
regular-price study. Those requirements apply to v1 snapshots only.

## Historical helper

This procedure is downstream of category-processing. Its input is a verified,
reviewed Silver snapshot. It owns the study's model design and preparation of
training inputs for the Gold/modeling handoff. Do not invoke it to satisfy the
raw-to-Silver skill's entry conditions. Silver retains source evidence reviews
and existing eligibility decisions; this stage consumes that evidence.

The package currently provides a legacy `prepare-model` helper that writes
JSONL splits, an encoder and a design matrix. It does not create an immutable
Parquet Gold dataset. Canonical chocolate Gold uses the repository's separate
builder; other categories need their own implemented Gold export contract.
Do not report those exports as implemented by this helper.

## Define the study model

This step owns `model-design.json`. Consume the category's schema catalog and
study purpose; choose the target, comparable groups, selected predictors,
quantity/price basis, eligibility and preparation rules. The tracking catalog may
remain broader than the selected predictors. Do not invent model decisions to
complete schema creation. Honor the authorized study and report unsupported
runtime targets explicitly.

The legacy [processing definition](profile-definition.md) and loader still
require model decisions before a Silver run. That is an existing implementation
dependency, not the intended layer responsibility. An existing versioned profile
can supply its legacy design; do not create model choices merely to begin
raw-to-Silver work. Removing this dependency requires a runtime migration.

## Prepare reviewed inputs

Use a complete silver snapshot and eligible reviewed `model-inputs.jsonl`:

```text
python3 <plugin-root>/cli.py prepare-model --silver-root <silver-root> --output <preparation-root> --validation-fraction 0.2
```

Generic targets are `regular_unit_price` and `log_regular_unit_price`;
`target_definition` saves category, market, currency, quantity attribute, unit and
base quantity. Chocolate and the coffee starter use regular GBP/100 g; another
category must deliberately define its comparable price basis. Chocolate may
also expose compatible GBP/100 g aliases.

New definitions explicitly choose their currency, numeric observed quantity,
unit and base; a per-item design still requires source-supported count evidence.
`eligibility.allowed_tax_bases` selects one reviewed basis matching the target;
older designs default to `consumer_tax_included`. Do not mix included/excluded
prices without a separately implemented, reviewed normalization. Source monetary
minor units use the recipe's explicit factor. No tax or currency conversion is
performed by model preparation.

The command verifies hashes, `complete_snapshot` status and candidate contracts.
Eligibility requires reviewed scope, physical/family identity, price/quantity
basis and selected predictors with evidence from the relevant observation capture.
Unknown/conflicting/unreviewed active fields are rejected. The tracking catalog
is broader than the selected predictors.

Families stay together across sellers. Deterministic splitting needs at least
two eligible families. Only training rows define vocabularies, reference levels,
numeric domains and removal of constant terms. Bundled designs use the mode of
training values for reference levels, with deterministic ties; they reject
missingness and do not impute, scale or center. Validation uses the frozen encoder
and rejects unseen levels and values outside the training range. Investigate
those failures explicitly.

| Output | Meaning |
| --- | --- |
| `train.jsonl`, `validation.jsonl` | Reviewed observations partitioned by family. |
| `encoder.json` | `category-processing-encoder-1`, frozen columns/references/domains, support, training IDs and target/version context. |
| `design-matrix.jsonl` | Partition, observation ID, encoded X and log price y. |
| `model-design.json` | Exact source design. |
| `preparation-report.json` | `category-model-preparation-1`, source versions, split, columns, dropped terms, hashes and limitations. |

No regression is fitted. Reports retain `regression_fitted: false` and
`release_ready: false`; zero eligible rows fails instead of fabricating an
encoder or prediction. Helpers validate, split, encode and compute conditional
contrast arithmetic. They do not establish sufficient samples, identifiable
brand/seller effects, coefficients or uncertainty.

For a later reviewed model of log price, `coefficient_percent(beta, delta)` computes
`100 * (exp(beta * delta) - 1)`. Prediction contrasts exponentiate fitted log
predictions into conditional median prices on the saved target basis; they do
not automatically estimate conditional means. Report units, feature/reference
changes, context held fixed, support, fitted uncertainty and limitations.
Interpret conditional associations without causal premium claims. Testing prices
for new products and scoring value for money require later validation/release
decisions. Mapping changes never rewrite an old model's training snapshot.

All model targets use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price, with reject fallback. Currency and quantity normalization remain category-specific. Custom authoring adds the fixed policy metadata to design and recipe; source amounts and tax inclusion still require independent evidence. Model preparation records the same policy on each target and in the frozen encoder.
