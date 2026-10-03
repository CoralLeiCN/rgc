# Chocolate schema, reviews and pricing handoff in silver

The [authorized Gold eligibility override](chocolate-gold.md) changes Gold's
training flags in a new immutable snapshot with retained parent/provenance.
The baseline trainer accepts those flags and records actual missing inputs.
The user's current-price study supersedes the regular target requirement for
this baseline: `current-consumer-price-1` uses collected displayed GBP prices
and actual matching edible pack weight. The latest refit has 2,134 eligible rows
and 630 current GBP/100 g targets; missing variant IDs and population boundary
values prevent fitting. Original observations and historical target meanings
are preserved.

The initial schema, `chocolate-schema-1`, tracks broad chocolate information
within the combined silver layer. This guide owns field meanings,
standardization, reviews supported by evidence and the pricing model handoff.
The [silver guide](chocolate-silver.md) owns raw/silver responsibilities, the
build command, dataset outputs, evidence resolution and current build status.

## Machine contracts

The [current-price dataset pin](../../schemas/chocolate/current-price/dataset-contract.json)
references `contracts/chocolate-current-price/` at immutable revision
`d743cb8dbca37f5241cccd444a16165523304f6c`. This set retains `chocolate-schema-1`,
103 attributes and `chocolate-source-mappings-2`, and supplies
`chocolate-pricing-current-price-design-1`. The retailer median applies its exact
target definition to `chocolate-retailer-median-design-1-current-price-1`.
Derived modeling rows carry `current_price_per_100g_gbp` and
`log_current_price_per_100g_gbp`. Equal `regular_*` compatibility aliases in those
rows mean current-price proxies. The original Gold Parquet columns and input
bytes retain their historical meanings. No regular/reference fallback or weight
imputation is permitted. The published target, pin, working design and derived
rows are saved and hashed in each current-price run.


The independent [retailer median trainer](analysis/retailer-median-training.md)
uses an explicitly prepared unpublished working model design. It requires
reviewed single-pack/boundary context alongside retailer, type, brand, source
role, group, weight and family identities. Published contracts and OLS snapshots
retain their meanings. The current target is published; the effective baseline
working design remains unpublished. Actual input gaps block the real fit; common
comparison feature evidence and baseline design publication remain pending.


| Contract | Version | Responsibility |
| --- | --- | --- |
| `profile.json` | `chocolate-schema-1` | Attribute types, units, vocabularies, scope, qualifiers, model roles, standardization rules, and missingness. |
| `source-mappings.json` | `chocolate-source-mappings-2` | Recognized source aliases, conversion bases, and rules for source scope. |
| `product.schema.json` | `chocolate-schema-1` | Required standardized product envelope and typed attribute objects. |
| `model-design.json` | `chocolate-pricing-design-3` | Selected predictors, target, eligibility, preprocessing, validation, and insight requirements. |

These four files are authoritative under `contracts/chocolate/` in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
The [dataset manifest](../../schemas/chocolate/dataset-contract.json) in Git pins
the immutable dataset commit, file paths, SHA-256 hashes and version metadata.
Runtime loading verifies downloaded and cached bytes, including byte lengths,
under ignored `data/contract-cache/`. Git stores the manifest instead of the
analytical JSON bodies. The documentation guard checks manifest pins and
documented versions offline; it verifies cached contracts when present without
downloading them. See [dataset contracts](dataset-contracts.md) for cache,
publication and verification rules.

Machine contracts define the complete field list and allowed values; this guide
explains their intent and use. The [project specification](../spec.md) owns
requirements across layers and for release.

Loading rejects drift between each profile attribute and the product validator's
type, unit, enum/list vocabulary and numeric bounds in both nullable value
branches and value branches with a known status. Validation uses the explicit
typed template;
unsupported keywords constraining values fail loading. General JSON Schema
execution remains unimplemented.

## What the schema tracks

The proposed pricing explanation groups modeled traits by the attribute families
below, with seller observation inputs in a selling-context family. Each predicted
price will report individual trait contributions and one signed percentage per
trait family, plus a model reference percentage, under
[specification section 5.2.1](../spec.md#521-trait-and-trait-family-percentages-of-predicted-price).
Trait groups differ from product identity families. This output awaits a versioned
model mapping, implementation and validation; existing contracts and helpers do
not produce it.

The initial profile contains 103 attributes, organized as follows. Every
product tracks each field once, even when its evidence state is unknown.

| Family | Information retained |
| --- | --- |
| Identity and scope | Source product/variant IDs, name, SKU, GTIN, brand, manufacturer, retailer and seller role, variant/flavour name, product group, study boundary, and reviewed physical/family relationships. |
| Composition | Chocolate type; percentages of cocoa, cocoa butter and milk solids; original ingredients/allergen sections; ingredient labels; nuts and nut types; cross contact warnings; fruit, palm oil, alcohol, salt, sweeteners, flavour, filling and inclusions. |
| Dietary claims | Vegan and vegetarian claims; claims of being free from gluten, dairy, nuts, soy, palm oil, sugar or genetically modified organisms; claims of no added sugar. |
| Certification claims | Specifically named schemes and scoped Fairtrade, generic fair trade, organic, Rainforest Alliance, kosher, halal, FSC packaging, and B Corp claims. |
| Nutrition | Original nutrition section and basis, energy, fat, saturates, carbohydrate, sugars, fibre, protein, salt and serving mass. |
| Origin | Cocoa countries, regions, estates and varieties; manufacture country; claims of a single origin or estate. |
| Packaging | Type, components and materials; claims of being recyclable, compostable, reusable, plastic free or packaged as a gift. |
| Processing | Production from beans to bars, handmade claims, roasting, conching, claims that the product is raw and source description. |
| Storage | Instructions, declared temperature range, shelf life and best before date. |
| Marketing | Original claims, tasting notes, awards, ethical and sustainability statements, seasonal/occasion themes and claims of premium positioning. |
| Quantity | Total edible mass and edible mass for each unit, pack count and piece count. |

Seller/price context is a separate observation contract: preserve displayed,
regular, promotional and reference prices; currency and original representation;
availability, observation time, tax basis, offer mechanics and source evidence.
Price observations retain their historical context.

The schema is implemented. Current extractors support a subset of its vocabulary
and source formats; a tracked field requires evidence, review and model support
before use as an independent predictor. Complete extraction coverage, reviewed
classification and a fitted/validated pricing model remain outstanding.

Automatic extraction currently reuses supported source adapters for basic
identity, proposed product groups, explicit edible quantities, prices, a subset
of chocolate/ingredient/dietary/certification assertions, and retained ingredient,
allergen, nutrition and promotional text. Selected variant fields and recognized
structured composition, nutrition, dietary, certification, origin, packaging,
processing, storage and marketing fields can also be standardized. Broad OCR,
comprehensive ingredient parsing, nutrition table extraction and automatic
production/packaging review are unsupported. Source product types, tags and
unfamiliar keys in supported structured sections remain unmapped information.
Other information specific to a source remains in the input captures even when
no current extractor creates an assertion or review item for it.

## How standardization works

Each attribute has `value`, `status`, `unit`, `qualifier`, `scope`, `evidence`,
`method`, and `review_status`. Evidence contains a `capture_id` and JSON
`pointer` into the retained capture. Follow the
[silver evidence resolver](chocolate-silver.md#output-contract-and-evidence-resolution)
for original capture objects, raw artifact/history paths and verification limits.

Selected product attributes describe the latest capture, supplemented by explicit
review decisions. Compatible latest assertions retain their combined evidence;
incompatible values, scopes or qualifiers produce a conflict. The separate
assertions table retains historical source assertions, with `is_current` marking
support from the latest capture and current review assertions. Price observations
retain their own capture context, including the quantity supported by that
observation.

| State | Meaning |
| --- | --- |
| `known` | A valid typed value has supporting evidence; review status separately states whether the interpretation was reviewed. |
| `unknown` | Available evidence does not establish a value; `value` is null. |
| `not_applicable` | Determination supported by evidence that the field does not apply; `value` is null. |
| `conflict` | Supported statements disagree or their bases cannot be reconciled; no selected value is silently chosen. |

A presence field has `present` or `absent` only when the evidence establishes
that claim. Missing copy is an unknown state. Automatic extraction remains
unreviewed until a decision supported by evidence confirms it.

Standardization checks the declared type and range, converts supported units to
canonical units, maps recognized aliases to controlled values, retains source
scope and qualifiers, and rejects unfamiliar or conflicting values for review.
Original text and evidence remain available; interpreted token normalization
never rewrites source bytes. Representative rules include:

- Edible mass uses grams, with explicit supported unit conversions and pack
 basis. Shipping weight and nutrition quantities do not establish pack mass.
- Percentage values retain exact/minimum/approximate meaning and scope for the
 whole product or its chocolate component. Do not average incompatible percentages.
- Product nut ingredients and “may contain” allergen statements are different
 fields. An incomplete ingredient section cannot establish ingredient absence.
- A named Fairtrade claim stays separate from generic fair trade or direct trade
 wording. A source certification claim remains a claim, rather than an
 independent verification of certification status.
- Origin roles stay separate: cocoa origin, manufacture country, and the UK sales
 market do not substitute for each other. A manufacturer's address alone does
 not establish manufacture origin.
- Nutrition requires a declared comparable basis; values for each serving or
 prepared values do not silently become per 100 g as sold. Salt and sodium remain distinct.
- Packaging and production statements need evidence about the product. Global
 navigation, footer claims and general advice cannot establish product features.
- Price conversion follows the source's currency representation. Pence and
 pounds use different conversion factors; a comparison/reference price cannot
 silently become a regular price.

The typed conversion API also validates supported GTIN lengths/check digits
without removing leading zeroes, maps only declared country aliases, and accepts
unambiguous valid `YYYY-MM-DD` dates. Supported declared quantity units convert
to grams; declared day/week durations convert to days; declared Fahrenheit
temperatures convert to Celsius. The unit/basis must be supplied explicitly to
the converter. Missing units, ambiguous dates and unspecified month lengths
remain unresolved. Extraction coverage depends on source fields and adapter support.

Unmapped claims remain attached to records and review outputs. Add a mapping
only when the source meaning and scope support the canonical value. Extending
a vocabulary does not make an old unknown value known until the dataset is
rebuilt with the new versioned rule.

## Build silver with this schema

Use the [silver build command](chocolate-silver.md#build-silver) and
[output contract](chocolate-silver.md#output-contract-and-evidence-resolution)
for the combined raw snapshot verification, exact seller deduplication,
standardization, price normalization and reviewed eligibility.

The standalone `scripts/standardize_chocolate_data.py --deduplicated-root ...`
helper supports compatibility or diagnostics with an explicit persisted
deduplicated snapshot. Its historical `data/standardized/chocolate/uk` output
is an optional helper snapshot in the canonical raw/silver workflow.

## Inspect field coverage and value frequencies


The historical [published pandas report](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/blob/db32e43635793a0edd1308df4bd0dee112ddbe44/analysis/chocolate/uk/silver-2f97cfe8b8c50ecfa79ebf46/schema-popularity.json) covers all 103 attributes from the
verified silver snapshot at revision `c1725ff8bbeef8f78c7182fd67af5bde75ef65ef`.
At that publication revision, both chocolate profiles have matching attribute definitions; frequencies use
3,743 silver seller listings. Twenty-four attributes have known selected values
and 79 have zero coverage. The [publication receipt](analysis/chocolate-pandas-publication-2026-10-03.json)
records the immutable report revision and checksums.

Use the pandas analysis helper with an explicitly supplied local silver snapshot:

```sh
uv run --script scripts/analyze_chocolate_schema.py \
  --silver-root /path/to/downloaded/silver \
  --dataset-revision <immutable-40-character-dataset-commit> \
  --analysis-date <YYYY-MM-DD> \
  --output data/analysis/chocolate-schema-popularity.json
```

Both scripts pin pandas 2.2.3 through PEP 723 metadata. The helper also supports
direct Python execution when pandas is installed. It performs no download and
checks product, profile and model-design SHA-256 hashes against the local
manifest before analysis. The caller must establish which immutable dataset
commit supplied those inputs; `--dataset-revision` records that commit rather
than proving a remote association. `--analysis-date` accepts an ISO date and
defaults to the interpreter's current local date when omitted. Supply it
explicitly for a reproducible report.

Replace the example input path, commit token and date token with the downloaded
snapshot directory, its verified 40-character Hugging Face commit and an ISO
analysis date. `--output` must be outside the supplied silver directory and
separate from any supplied profile or manifest. The helper writes the result
atomically after its input checks and analysis complete.

The JSON report describes all attributes in the snapshot's profile:

- Field coverage uses every seller/variant listing as its denominator and keeps
  `known`, `unknown`, `conflict` and `not_applicable` counts separate. Review
  counts, field families, source coverage and active model predictors remain
  explicit, including fields with zero known values.
- Value frequencies count exact selected values only when status is `known`,
  with percentages of all listings and of known listings. Controlled categories
  include allowed values with zero counts; labels and numeric values retain
  their full exact distributions. String lists are counted as exact lists.
- Numeric summaries report count, minimum, quartiles, median and maximum using
  linear-interpolated quantiles, both pooled and separated by scope and
  qualifier. Component-specific percentages and minimum claims retain those
  different meanings.
- Other text and identifier fields show their ten most repeated exact strings,
  with original-prefix excerpts of up to 240 characters, character counts and
  exact-value hashes. Repeated text is not a semantic ingredient or claim count.
- Provenance records input hashes, dataset/silver versions, analysis date,
  Python/pandas versions and the analysis script hash.

Optional `--portable-profile /path/to/profile.json` verifies a portable chocolate
profile against `--portable-manifest`, which defaults to the checked-in portable
chocolate dataset reference. It compares attribute definitions with the baseline
profile; all frequency counts still use the supplied baseline silver products.

Known values remain subject to extraction and review limitations. Missing claims
do not mean absence; source imbalance, repeated variants, unresolved aliases,
pack-basis ambiguities and parser defects can affect counts. The report describes
collected seller listings, without estimating sales, preferences or UK market
share. It writes a separate analysis artifact and does not modify evidence,
classification decisions, contracts or model readiness.

## Reviews supported by evidence

Use a review file with a separate format from the earlier cleanup reviews:

```json
{
 "review_format_version": "chocolate-schema-reviews-1",
 "products": {},
 "prices": {}
}
```

Pass it with `--reviews <reviews.json>`. Use `listing_id` from `products.jsonl`
and `observation_id` from `prices.jsonl` as the keys in the review maps.
Every decision needs a named `reviewed_by`, substantive `reason`, and evidence
entries containing valid `capture_id`/`pointer` locations from this listing's
retained captures. A resolvable pointer is necessary; the reviewer must also
check that its contents substantiate the decision.

| Review location | Decisions |
| --- | --- |
| `products[listing_id]` | `variant_id`, `family_id`, and `in_scope`; accompanying reviewer/reason/evidence must support the relationships and scope. |
| `products[listing_id].attributes[attribute_name]` | Canonical `value`, `status`, optional `qualifier` and `scope`, plus reviewer/reason/evidence; use the dotted field name and declared type/vocabulary. |
| `prices[observation_id]` | `regular_price`, `currency`, `tax_basis`, `observed_at` and `available`, plus reviewer/reason/evidence. |

Confirm the comparable group through `identity.product_group`, edible pack mass
through `quantity.total_edible_weight_g`, and selected feature meanings through
their attribute reviews. The initial price gate requires positive ordinary GBP
consumer pack price, `consumer_tax_included`, an observation time with a timezone,
and confirmed availability. Capture/import time does not automatically establish
price observation time. Reviewed mass and every active predictor must have
supporting evidence in the price observation's capture. A later pack weight,
recipe or claim cannot silently classify an earlier observation. Decisions for
scope, physical variant and family at the top level also populate the
corresponding schema attributes; contradictory attribute decisions are rejected.

Partial decisions remain visible with exclusion reasons. Do not populate absent
or negative values merely to make a candidate eligible. Rebuild after reviews
change so the decision file and resulting dataset version remain reproducible.
A row's `review_status: reviewed` records that a review decision exists; it
does not establish that every attribute or price context requirement was
confirmed. Inspect attribute review states and `model_eligible` with its
`exclusion_reasons` for the actual training boundary.

## Pricing model handoff and insights

This section documents the executable `chocolate-pricing-design-3` preparation
contract. The [consolidated pricing research design](chocolate-modeling-design.md)
proposes a subsequent model comparison, optional feature policy and calibration
workflow. Its variants with and without brand, missing value handling and calibration
require aligned versioned contracts and implementation, with regenerated reviewed
inputs. Existing contracts and snapshots retain their own preparation rules.

The independent [LightGBM without brand implementation](analysis/lightgbm-without-brand-implementation.md)
now has an explicit local working configuration and synthetic validation. It
requires selected cohort, pack-count, recipe and cocoa-basis fields absent from
the published 11-predictor design, plus the proposed optional evidence states.
It records these as readiness blockers. Local configuration does not add source
evidence or change published schema/portable rules. Dataset/portable alignment,
reviewed regeneration and the separate contract release review remain pending.

The initial target is the natural logarithm of regular consumer GBP per 100 g:

```text
regular_price_per_100g_gbp = regular_pack_price_gbp / edible_pack_mass_g * 100
log_target = log(regular_price_per_100g_gbp)
```

The model design selects a supported subset of the tracked attributes and
seller/brand context. It excludes prices, computed unit prices, price bands and
any derived price score from predictors. This prevents encoding the target as
its own explanation. Pack mass is independently evidenced and may remain a
size predictor after normalization of unit price.

The initial design has 11 required predictors: product group, seller role,
product brand, seller identity, chocolate type, cocoa percentage, nut ingredient
presence, vegan claim, Fairtrade claim, organic claim, and total edible mass.
Cocoa percentage must be an exact value for the whole product: minimums,
approximate values and percentages of chocolate components remain tracked but
are excluded from this numeric predictor. Edible mass receives a log transform. The initial
encoder performs no imputation, scaling or centering; categorical references
use the most frequent training value, with lexical ties, and are saved with the
encoder. The experimental OLS trainer implements this design; real-data support still needs review
and validation before fitting.

Current required predictors must be known and reviewed; unknown, conditional,
conflicting or unsupported interpretations remain excluded. Each must have
product scope and an unconditional meaning: qualifiers for other attributes may
be null, `exact` or `unconditional`, while cocoa requires `exact`. Record
missingness explicitly, and use a versioned model design if an optional category
for missing values or imputation policy is later introduced. Do not map an unknown label to a known
reference category.

The selected model domain can be narrower than the schema's category vocabulary.
A known value valid for the category but outside the selected model domain
remains in products and assertions; the candidate records
`model_predictor_outside_design_domain:<attribute>` and is excluded. Such a value
does not abort the silver build or become an unknown/reference value. Keep this
declared check of the study domain distinct from support learned later by the
encoder.

[scripts/chocolate_model.py](../../scripts/chocolate_model.py) provides helpers to
validate eligible rows, split by reviewed `family_id`, learn a frozen encoder
from training rows, and transform rows held out of training with that encoder.
Related physical/family designs stay in one split while seller rows remain unique;
this follows the grouped validation principle illustrated by
[GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html).
Learning preprocessing from training data and applying the same fitted transform
to data held out of training follows the
[scikit-learn guidance on leakage](https://scikit-learn.org/stable/common_pitfalls.html).

The encoder records selected columns, reference levels, observed level/family
support, numeric ranges, and dropped constant terms. Under the initial policy
for supported domains, rows held out of training with unseen levels or values
outside training ranges are rejected. The helper consumes observed eligible rows with
targets. The experimental trainer fits OLS with family holdout and family-cluster
bootstrap coefficient intervals; an interface for predicting new designs remains
subsequent work. Numerical classification/model release thresholds and
statistical sufficiency remain explicit study decisions.

For a future supported indicator coefficient on log price, the conditional
percentage contrast is `100 * (exp(beta) - 1)` relative to its stated reference.
For a continuous predictor, state the unit and change; for interactions, compute
the contrast in the actual product context. Interpretation helpers also convert
two supplied log predictions into conditional median price and percentage
contrasts. They do not estimate coefficients or supply uncertainty by themselves.
The existing helper returns `estimate_type: conditional_median_price`; the caller
must justify that interpretation for the supplied log predictions.

The proposed research design labels `exp(fitted_log_price)` as a geometric price
benchmark. Exponentiation alone establishes neither an arithmetic mean nor a
conditional median. An arithmetic mean requires a separate correction learned
from training data and validation on the original price scale; it is outside the
proposal's initial output.

Every released insight must identify target units and price basis, both compared
profiles, categorical reference, conditioning terms, observation/family support,
uncertainty, validation, and domain limits. Distinguish coefficient intervals
from prediction intervals for new products and median retransformation from mean
price estimation. An adjusted association or unexplained residual does not
establish a causal feature effect, isolated brand premium, product quality, or
consumer willingness to pay.

Use the [silver build status](chocolate-silver.md#review-training-and-interpretation-boundaries)
for current review and price/tax gaps. Silver remains a standardized candidate
dataset until evidence review, extraction evaluation, support checks and the
[specification's release gates](../spec.md) pass.

## Extending the schema and keeping documentation current

1. Inspect an original capture and retain the unfamiliar statement/evidence.
2. Add or amend typed definitions, allowed values, source aliases, scope and unit
  rules in a local working copy of the dataset contracts; bump affected version
  identifiers when semantics change.
3. Implement extraction/validation scoped to the evidence and test the actual
  ambiguity or conversion, including unknown/conflict behavior where relevant.
4. Rebuild silver and inspect coverage, exclusions and review changes.
5. For schema changes, present the completed release summary and wait for user
  review before its Hugging Face commit under the
  [maintenance decision](../decisions/agent-led-schema-maintenance.md). Supported
  local changes require no user approval.
6. Publish reviewed contracts to a new immutable dataset revision, verify bytes
  and update manifest pins/hashes under
  [dataset contract maintenance](dataset-contracts.md#maintenance-and-verification).
7. Update this guide and the applicable documents under the
  [documentation policy](../documentation-policy.md); run
  `python3 -B scripts/check_documentation.py`.

New tracked fields can remain unknown or excluded from the model until evidence,
review and support justify their use.

Use the locked development environment for schema and model contract checks:

```sh
uv sync --locked
python3 -B scripts/fetch_contracts.py --all
uv run pytest scripts/tests/test_standardization.py scripts/tests/test_standardized_values.py scripts/tests/test_contract_consistency.py scripts/tests/test_model_contract.py
uv run ruff check .
python3 -B scripts/check_documentation.py
```

## Family and physical-product mapping

The raw-to-Silver build accepts `--family-mappings <family-mappings.json>` for
reusable accepted identity relationships, with an empty decision set when the
default `reviews/chocolate/family-mappings.json` registry is absent. With no
explicit option, the build loads that checked-in registry when present. Keep
global identity separate from each seller's source product/variant IDs and the
broad product-group taxonomy. An exact
physical-product ID links the same variant across sellers; a family ID groups
related variants for validation without merging their listing records or prices.
A supported named manufacturer range may form a conservative validation family
across flavours, sizes and gift configurations; this does not establish exact
physical equivalence between those variants.

`chocolate-source-mappings-2` declares the
`chocolate-product-identity-1` taxonomy and `chocolate-family-mappings-1`
decision format. A decision file has this envelope:

```json
{
 "mapping_format_version": "chocolate-family-mappings-1",
 "taxonomy_version": "chocolate-product-identity-1",
 "families": {},
 "physical_products": {},
 "assignments": []
}
```

Each family definition has a `label` and `definition`. Each exact physical
product has a `label` and its `family_id`. An assignment identifies a stable
`mapping_id`, a family ID and an optional exact `variant_id`, plus
`reviewed_by`, `reason` and valid `capture_id`/`pointer` evidence. Its selector
uses `source_key`, `source_product_id`, `source_variant_id` and an exact `name`
guard; a `listing_id` plus exact `name` guard is available when reliable seller
product identifiers are unavailable. A null source variant is explicit. Listing
selectors resolve preserved raw-to-canonical aliases. The name guard prevents
silently applying an old decision to a renamed product. Do not treat a seller's
local identifiers as global product relationships.

Selectors do not detect consumer-pack changes that retain the same source IDs
and name. The initial registry contains family-only decisions; any future exact
physical assignment requires Codex to check changed pack evidence on later
captures before reusing that relationship.

Accepted mappings populate the existing typed `identity.product_family_id`
attribute, and an accepted exact variant also populates
`identity.physical_product_id`. Both use the `reviewed_identity_mapping` rule,
supporting evidence and identity review provenance. Candidate `family_id` and
`variant_id` values come from these resolved identities. No extra product
attribute is added to the 103-field schema. Silver preserves the parsed decision
file at `family-mappings.json` and fingerprints it in the manifest.

Silver emits unresolved grouped cases in `family-review-packets.jsonl`. Codex
reads each packet and its original captures in the current authorized task,
checks the variant-defining evidence, and records supported decisions for the
next frozen mapping build. Names, brands and category labels alone cannot justify
exact cross-seller matching. Preserve unresolved cases when evidence conflicts
or is insufficient; assigning one arbitrary family per seller listing would
conceal validation leakage. Processing does not dispatch or schedule another
agent automatically.

A family/physical identity mapping confirms only that relationship. It does not
review scope, active predictors, edible quantity or regular tax-inclusive price.
Existing `chocolate-schema-reviews-1` product identity decisions remain supported;
contradictions between an accepted registry assignment and a product review are
rejected rather than silently overridden. Older Silver and Gold snapshots keep
their original identities and contracts; rebuild into a new snapshot to apply
later mappings. Conflicting registry assignments preserve a `conflict` state
and require another evidence-backed decision; frequency does not pick a winner.

## Prepared Gold and regression contract release

The published contract release retains `chocolate-schema-1` and its 103 typed fields, changes source mappings to `chocolate-source-mappings-2`, and selects `chocolate-pricing-design-3`. Model helpers use `chocolate-encoder-2` and `chocolate-regression-2`. The historical `regular-consumer-price-1` target requires regular, non-promotional, consumer-tax-inclusive price with reject fallback; chocolate remains log GBP per 100g. The 11 selected predictors are unchanged. Seller role supplies reviewed context; seller identity supplies fitted seller terms. Training validates target amounts against the copied price observations.

The experimental trainer implements family-held-out OLS, rank/conditioning and confounding gates, and family-cluster bootstrap coefficient intervals. No real-data regression has fitted and no prediction intervals or released domain are established. [Gold](chocolate-gold.md) preserves candidates separately from eligible inputs and carries accepted identity decisions. The [published release](analysis/gold-modeling-contract-release.md) records exact files, hashes, impact and publication status; authoritative manifests now pin verified Hugging Face commit `d549ad91d63fb452af605df4a939c4e1f0a59bfa`.


## User eligibility in Gold

The explicit Gold bulk eligibility operation sets every candidate model eligible
for training selection. Silver's evidence eligibility is retained in a complete
parent snapshot; logical predictor/target fields, nulls, identifiers and copied
analytical contracts retain their original values and versions. This operation
changes Gold selection under `chocolate-gold-bulk-eligibility-1` without changing
the analytical product schema or price policy. Trainers must validate actual
required values and retain the override provenance in their run artifacts. See
[Gold eligibility](chocolate-gold.md#make-every-gold-candidate-model-eligible).


## Current-price training target contract

The current chocolate modeling study selects `chocolate-pricing-current-price-design-1`
under `current-consumer-price-1`, using unchanged `chocolate-schema-1` and
`chocolate-source-mappings-2`. The 103 typed product attributes, validator,
source mappings, prices and source contracts retain their existing versions.
A separately pinned contract set `chocolate-current-price` copies the original
profile/mapping/validator bytes and supplies the current target design. This
changes training interpretation without manufacturing a regular-price observation.
Explicit current target fields exist in prepared model inputs; legacy `regular_*`
fields are equal compatibility aliases under this recorded contract. Source Gold
still retains its original target schema. The [modeling guide](chocolate-modeling-design.md#1-population-and-price-target)
owns normalization and limitations.

The [current-price pin](../../schemas/chocolate/current-price/dataset-contract.json)
selects immutable dataset revision `d743cb8dbca37f5241cccd444a16165523304f6c`.
Its model-design SHA-256 is
`c7b7f55d0424f8bdbef2fbc76e7b75475753eaad8021f7e1acd266de284ac8de`.
All four files and available caches verify against the pin.

## LightGBM with brand handoff

The [independent LightGBM trainer](chocolate-lightgbm-with-brand.md) uses an explicit working experiment alongside copied Gold contracts. The current published `chocolate-pricing-design-3` remains the experimental OLS contract. Its eligible view lacks the shared single-pack population, recipe/inclusion, cocoa basis and optional missingness handoff required by the new experiment. Missing fields block training; the new trainer cannot manufacture evidence or promote candidates. An aligned original and portable contract release and regenerated reviewed inputs are still required.

The all-eligible Gold data is now published at immutable dataset revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7`. Its
[small Gold reference](../../schemas/chocolate/gold-dataset.json) records the
source manifest and managed file hashes. This publication packages the existing
source interpretation and user eligibility; it changes no typed product fields.


The independent [retailer median refit](analysis/retailer-median-training.md#refit-after-integrating-main-and-the-published-gold-snapshot)
uses all 2,134 eligible rows from the exact published Gold revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7`. The current displayed-price target
produces 630 GBP/100 g values. Missing variant IDs and population boundary values
in every row, plus other family/quantity/context gaps, prevent fitting. Its
trainer preserves the original Gold/evidence bytes, applies the published
current target to its selected retailer/type predictors, and records the exact
Gold publication pin, target contracts and per-row readiness. Historical regular
mode remains available; no real baseline fit or upload is claimed.

## Local hedonic handoff

The independent `hedonic_without_brand` trainer consumes verified Gold under `chocolate-supermarket-hedonic-working-1`, prepared explicitly in an ignored local file. Its [implementation record](analysis/hedonic-without-brand-implementation.md) specifies family weighting, prediction support, cocoa imputation, claim states and retailer calibration. Published original and portable schema/design pins retain their current versions. Required recipe class, explicit supermarket cohort and exported single-pack count are absent from the published eleven-predictor handoff; cocoa basis also needs an optional export contract. This is a readiness blocker. The working policy does not implement those source mappings or review evidence. Contract publication requires coordinated original/portable contracts and the established release review.

## Gold inferred web collection

The web workspace now consumes the published
`gold-inferred-5b539b9c4adbb011a40d7792` export at immutable dataset revision
`812a03a5faaced471a2a20f4c389865ed5675826`. Its 3,743 complete product records
retain all 103 attributes and 2,159 accepted additions supported by source evidence across
33 attributes. Parquet `record_json` owns complete values and evidence; the
web adapter validates them with the export's copied contracts and preserves
per-field review states. Nested training Gold retains 2,134 candidates, zero
eligible inputs and the historical `regular-consumer-price-1` basis. The separate
current-price study keeps its own policy. Silver continues to own source
processing, interpretation, review and eligibility. The app reference pins the
manifest and revision; [collection integration](../collection-integration.md)
defines preparation and offline rebuild commands.

## Matched retailer working contract

The [matched retailer diagnostic](chocolate-matched-retailer.md) implements exact
physical-variant and retailer effects through an explicit local
historical `chocolate-matched-retailer-design-1` working contract. It verifies the historical
Gold contract copies and preserves `regular-consumer-price-1`; matching requires
reviewed formulation, flavor, edible weight, pack and genuine observation/context
evidence. Existing published schema, mappings and eligibility remain authoritative.
Family-only assignments cannot establish exact variants. The local diagnostic
does not implement the proposed regression optional-feature migration. Common
feature identification and a coordinated original/portable dataset release remain
pending before production adoption. The initial real rebuilt input had zero eligible rows.

For task-authorized Gold verification, the matched trainer selects its required
fields from existing candidates and records the caller's explicit instruction.
Historical review flags and optional regression features do not block that path.
It preserves source values, including nulls, and performs target arithmetic and
identity checks. The [direct Gold path](chocolate-matched-retailer.md#task-authorized-gold-verification)
records missing current numeric/identity values separately from review status.

The bulk eligibility loader verifies `chocolate-gold-bulk-eligibility-1` by
comparing promoted tables to the embedded complete parent. It accepts the user's
eligibility decision while retaining exact analytical values and nulls.
An explicit snapshot-bound working input configuration can preserve copied
storage contracts that differ from current published pins; the matched estimator
is still identified independently. The [matched refresh](chocolate-matched-retailer.md#refresh-from-promoted-gold)
records the new snapshot and missing current targets/identities. Published
original/portable references remain unchanged.

Current-study matched design `chocolate-matched-retailer-design-3` selects an
explicit `current-consumer-price-1` proxy target following the user's updated
instruction. Model artifacts keep derived current targets separate from original
Gold fields and retain promotion/tax limitations. Historical regular-price
contracts remain distinct; no published original/portable pins are changed by
this local model configuration. A separate immutable current-price overlay at
`d743cb8dbca37f5241cccd444a16165523304f6c` supplies the published target.
Shared preparation requires candidate edible weight to match the price quantity;
it does not infer missing weights. See [current-price preparation](chocolate-matched-retailer.md#current-price-study-policy).
