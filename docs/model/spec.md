# Model specification

Standard Silver v2 supplies reusable source facts. `chocolate-gold-standard-2`
now owns study context selection, comparison groups, displayed-price targets,
eligibility and selected model inputs. Its OLS loader verifies the prepared
population before training. The local schema migration pilot is not model-ready;
missing relationships and predictors remain reported. Existing experiment
adapters and historical snapshots retain their selected contracts. See the
[Gold interface](../data/chocolate-gold.md#standard-silver-handoff).

This document defines the model feature's study readiness, pricing methods,
explanations, validation and research requirements for the [model intention](intent.md).
The [project specification](../spec.md) connects the three core features. The
[data specification](../data/spec.md) owns collection, analytical facts and
immutable input contracts; the [app specification](../app/spec.md) owns user
workflows and presentation. The [lifecycle plan](../lifecycle/plan.md) records
implementation and verification evidence.

Model comparison groups, eligibility, target/price policy, predictor selection
and training-input preparation belong to the downstream Gold/model workflow.
Silver supplies standardized source facts, persistent source identities and
profiling reports under the [data requirements](../data/spec.md#21-research-a-category).
The existing Silver model dependency remains legacy behavior pending migration.

The numbered sections retain their original identifiers so existing requirements
remain traceable. Historical experiment records keep their original assumptions
and outcomes. The [current chocolate target](#current-chocolate-study-price-target)
and [Gold training admission](#gold-training-admission-and-inferred-lightgbm-refit)
sections govern current study preparation. The 4 October 2026 data reassessment
adds no model planning; this document preserves the existing model requirements.

The historical [Gold eligibility override](../data/chocolate-gold.md) can apply an explicit user
instruction to both training views in a new immutable snapshot. The complete
parent, original analytical values and authorization provenance are verified.
The retailer median trainer records the promoted row counts/provenance and saves
readiness artifacts for missing-input failures. Original auxiliary Silver
eligibility flags do not veto the override. The current retailer median study
uses `current-consumer-price-1` under the user's superseding target instruction;
actual quantities, identities and model domain requirements continue to apply.

The independent [retailer median implementation](../data/analysis/retailer-median-training.md)
implements only `retailer_median`: fitting-only family-weighted retailer/type
medians, flagged retailer-wide fallback, frozen whole-family splits and support
rules, weighted evaluation, and immutable artifacts. Its unpublished working
contract applies the published current-price target to its selected retailer/type
predictors and requires stored single-pack supermarket population context.
Synthetic validation passed; the recorded real Gold attempt had 2,134 eligible
rows and 630 normalized targets, but no complete model inputs or fitted model. Common comparison evidence,
cross-model metrics, calibration/release decisions and baseline design publication
remain pending. Existing `chocolate-pricing-design-3` experimental OLS is separate.

The snapshot promotion above records an earlier operation. Current Gold exposes
every candidate without selection fields, as defined in the
[data interface](../data/spec.md#10-gold-and-the-finalized-training-basis) and the
[training admission policy](#gold-training-admission-and-inferred-lightgbm-refit).
Historical eligibility counts do not describe a new gate for current training.

## 2. Core workflows

### 2.2 Fit and inspect a pricing model

1. Select the eligible observations and comparable product group.
2. Build model inputs from the reviewed feature schema.
3. Fit an interpretable regression and evaluate it on held out data.
4. Present feature estimates, reference levels, uncertainty, support counts,
   validation results, and limitations.

The output must distinguish an estimated conditional price association from a
causal effect. A coefficient cannot by itself establish that adding a claim or
ingredient causes the corresponding price change.

Use the [data price and comparability contract](../data/spec.md#33-prices-and-comparability)
when preparing those observations. The [app price review workflow](../app/spec.md#23-review-a-retailer-price-or-test-a-newly-designed-product)
and [input/output contract](../app/spec.md#6-retailer-price-review-and-new-product-price-test)
define how supported estimates reach users.

## 4. Dataset readiness

Before fitting, report:

- Unique variants, related product families, brands, retailers, dates, and
  comparable groups.
- Coverage across feature values for the category, applicable sizes/quantities,
  and price ranges.
- Missingness, unknown labels, disputed matches, and extraction review results.
- Exclusions and their reasons, including inconsistent price or quantity data.
- Rare features, correlated features, and combinations absent from the sample.

Readiness requires enough independent products and variation for the intended
comparisons, with acceptable validation and uncertainty. A row count alone is
insufficient. A feature seen only in one brand may be inseparable from that brand's
effect even with repeated retailer listings. Mark such estimates unsupported,
combine levels transparently or collect more varied products.

Sampling and retailer coverage determine what population the model describes.
Without sales data, the model describes sampled listings; estimating a market
average weighted by sales requires sales data.

## 5. Pricing regression

The [UK chocolate model design](../data/chocolate-modeling-design.md) consolidates the
initial cohort, baseline, hedonic and LightGBM architecture, feature handling,
validation, uncertainty and prediction contract. The
[LightGBM and explanation design](../data/analysis/lightgbm-shap-explanation-design.md)
specifies TreeSHAP and grounded AI interpretation. The complete comparison remains a design. At the original proposal stage, no
pricing model had been fitted. The later independent experimental implementations
and [inferred refit](#gold-training-admission-and-inferred-lightgbm-refit) below
record subsequent progress and its limits.

### 5.1 Initial model proposal

Start with a hedonic regression relating observed prices to measured product
characteristics. Select target, normalization and terms using the category
profile and comparable groups, then validate for that study. The original proposed UK
chocolate target was the log of regular GBP price per 100 g. The
[current study policy](#current-chocolate-study-price-target) supersedes that
requirement for current chocolate training while retaining historical contracts:

```text
log(price_per_100g_i) = intercept
    + product_feature_terms_i
    + brand_term_i
    + size_and_pack_terms_i
    + retailer_term_i
    + collection_period_term_i
    + error_i
```

Use available variation to choose terms; a constant collection period does not
need a fitted time effect. For chocolate, include pack size terms because unit
normalization does not remove quantity discounts. Use the applicable
quantity/size terms for each category. Add interactions only when there is
adequate support and an explicit reason. Compare against a simple category/group
baseline and keep the formula interpretable.

Treat retailer as an explicit pricing context. Compare the same reviewed variant
across retailers on consistent date, channel, tax, membership and promotion bases
to distinguish retailer differences from assortment differences. Use retailer
fixed effects and supported interactions when differences vary by product
profile. The UK chocolate design includes a retailer diagnostic using matched
variants, plus validation and prediction intervals for each retailer. Report
conditional retailer price associations; hypotheses about different target
audiences require additional shopper or choice evidence. An unseen retailer has
no supported coefficient until collection, fitting and validation establish its
domain.

Specify reference levels for categorical features. Review rank deficiency,
correlation, sparse levels, influential observations, residual behavior, and
stability across sources and reasonable model choices. Account for dependence
between observations of the same product when estimating uncertainty.

For an established statistical use of this method, see the
[BLS explanation of hedonic quality adjustment](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm).
Applying it to UK chocolate is this specification's proposal and requires its own
validation.

The historical executable preparation contract, `chocolate-pricing-design-3`, is
in dataset `contracts/chocolate/model-design.json`, pinned by the
[dataset manifest](../../schemas/chocolate/dataset-contract.json). It selects
features and preprocessing from the typed schema. Retain useful tracking evidence
even when a field is sparse, redundant, unsupported or descriptive and excluded
from the model. Save the fitted design under section 5.3; standardization alone
cannot establish coefficients or a price premium. The consolidated research
design proposes a subsequent version for separate models with and without brand,
handling of optional features and calibration. Existing preparation commands
retain the published OLS preparation rules. The independent
[`lightgbm_without_brand` implementation](../data/analysis/lightgbm-without-brand-implementation.md)
adds local experimental training, calibration and native TreeSHAP with an explicit
working configuration. It has fixture validation; its historical regular-price
Gold attempt had zero eligible rows and lacked four selected shared fields.
That historical trainer required explicit migration for refreshed current-price
Gold. The later [inferred refit](#gold-training-admission-and-inferred-lightgbm-refit)
provides a separate current-price exploration path. Full comparison, aligned
contract migration and market validation remain pending.

The proposed comparison includes LightGBM candidates with and without brand,
using the same target of log price, reviewed features, retailer contexts, family
weights and grouped splits as their hedonic comparators. Select settings and the
prediction champion through validation within the fitting partition, then freeze
each model before separate calibration and final testing. Retain hedonic models
for coefficient comparisons. Nonlinear predictions do not resolve confounded
attributes or unsupported retailers.

### 5.2 Feature contributions

For an indicator coefficient `beta` in a model of log price, report the estimated
percentage difference from its reference as `100 * (exp(beta) - 1)`, holding other
terms fixed. Report continuous features with their unit or an explicit input
change. With interactions, calculate the contrast for the actual product context.

For another target scale, use the corresponding model interpretation and
prediction contrasts in its declared units. Record that interpretation in the
model metadata.

Each result must identify its reference, sample support, uncertainty, and
conditioning variables. Contributions on the log scale are additive in log space;
percentage effects are multiplicative. Do not present percentages or currency
contrasts as additive shares of the final selling price. Use the explicit
allocation below for percentages of the final predicted price.

For a supported product profile, also express a feature contrast as the
difference between two predicted prices with the feature changed and all other
inputs held fixed. State both profiles and the selling unit basis of that currency
difference.

If two attributes cannot be distinguished in the data, say so. A Fairtrade term
may capture correlated brand, origin, quality, or retail positioning that the
dataset does not adequately measure.

For LightGBM, use exact TreeSHAP verified for the pinned versions to explain the
model's raw output on the log price scale. For the same frozen model and tree
count, its base value plus signed contributions must numerically reconstruct the
raw prediction. Contributions allocate
that prediction relative to the model explanation reference; they are neither
additive GBP amounts, causal premiums nor uncertainty intervals. Keep scenario
contrasts using complete predictions distinct from attribution.

An AI narrative may interpret a validated packet of predictions, SHAP values,
feature evidence and support limits. Deterministic code owns arithmetic. Require
traceable claims and validate references, numbers, directions and meaning; use a
fixed template if validation fails. Retain limitations from correlated
retailer/brand/claims and missing evidence. SHAP cannot establish shopper
segments, quality, demand or optimal price.

#### 5.2.1 Trait and trait-family percentages of predicted price

For each supported product prediction, report individual trait contributions
and one signed percentage per trait family of the final predicted price.
A trait family groups related product attributes, such as composition, dietary
claims, certification claims or quantity. It is distinct from the product
`family_id` used for identity, validation splits and training weights.

Use a versioned, exhaustive mapping from fitted inputs to traits and from traits
to families. Combine a trait's categorical encodings, transformations and
missing indicators before reporting its contribution. Include modeled brand
and selling context in named families so every fitted term is accounted for.
Fields excluded from the fitted model have status `not_modeled`, rather than
an estimated zero contribution. A modeled family with a computed zero retains
its zero percentage. Preserve signed cancellation within a family.

Start from a validated additive log-price explanation: `L = b + sum_j phi_j`,
where `L` is the frozen model's log prediction, `b` is its explanation reference
and `phi_j` is a trait's signed log contribution. LightGBM uses its TreeSHAP
reference and values. An additive hedonic model uses an explicit supported
reference profile, with term contributions equal to the fitted term differences
from that profile. Split a hedonic interaction term equally among its distinct
participating traits, recording that allocation convention before grouping.

Define a proportional allocation along the exponential price transformation:

```text
P = exp(L)
P_reference = exp(b)
d = L - b
k = -expm1(-d) / d       if d != 0; otherwise k = 1
trait_contribution_percent_j = 100 * k * phi_j
family_contribution_percent_g = sum_j_in_family_g trait_contribution_percent_j
reference_contribution_percent = 100 * exp(-d)
reference_contribution_percent + sum_g family_contribution_percent_g = 100
```

Here `expm1(t)` means `exp(t) - 1`, evaluated stably near zero. This convention
allocates the price difference `P - P_reference` in proportion to signed log
contributions and retains their cancellation when `d = 0`. The denominator is
the final predicted price `P`. These are allocated shares of a model prediction;
they are not price-scale SHAP values, causal effects, ingredient costs, observed
price shares or the percentile pricing score. Keep coefficient contrasts and
`100 * (exp(phi_j) - 1)` distinct from this allocation.

Present each trait family as its label and percentage, alongside a separately
labeled model reference percentage. A positive family percentage adds to the
reference price and a negative one subtracts from it. The reference can exceed
100% when the final prediction is below the reference; do not clip, take absolute
values or renormalize families alone to 100%. Unit-price and pack-price shares
are identical when both prediction and reference use the same product's quantity
conversion; the conversion does not add a second quantity contribution.

Retain unrounded values, model/explainer identity, reference profile or base,
trait/family mapping version and allocation method in the explanation packet.
Check both log reconstruction and the reference-plus-family total before display;
use a numerical tolerance and disclose display rounding. Failed, nonfinite or
unsupported explanations return unavailable contributions. Global mean absolute
importance is a separate measure and must not populate local price percentages.
This remains a proposed shared-model output requirement; implementation and
validation under the subsequent model contract release remain pending. The
separately authorized [synthetic app demo](../app/spec.md#synthetic-product-price-demo)
has its own fixture allocation and verification contract.

### 5.3 Validation and model release

Keep product families together in the split, including repeated retailer listings,
duplicate observations and closely related variants. Learn preprocessing from
training data only, then use the same fitted policy in validation and prediction.
Document unknown levels, imputation and rejection of missing required inputs.
Validate on a later collection period for claims about future prediction, and
hold brands out when evaluating support for unseen brands.

Save each model's category/profile, study and data versions, target price basis,
eligibility rules, actual fitted feature schema/list, missing value policy,
formula, fitted parameters, categorical reference levels, numeric scaling,
training/validation membership, supported ranges/domain, default prediction
context, target interpretation and evaluation. This metadata binds preparation,
prediction and insights to the released model.

Measure price error on the original scale and in the study's currency and target
units, for example MAE in GBP per 100 g for the UK chocolate study, and
relative error, alongside prediction interval coverage. Compare with the simple
baseline and report errors by supported group, size, brand, and retailer where
the sample permits. A high training R-squared is not a release criterion.

Exponentiating a log prediction does not automatically produce an expected
arithmetic price. Label the default exponentiated prediction as a geometric price
benchmark. A median
claim requires supporting assumptions; a mean requires a justified
retransformation adjustment and validation on the original scale.
Use prediction intervals for a new product, not only coefficient confidence
intervals.

Numeric release thresholds for coverage, extraction quality and prediction error
remain open decisions. Define them for the study before judging a model ready.
If the data or validation is inadequate, retain the dataset report and mark the
model experimental or unavailable for supported price testing.

## 7. Deferred research on value for money and brand premium

Stage 3 begins with research into adjusted price comparisons. Consumer utility,
sensory quality and causal brand value require evidence beyond the planned
product/price dataset. Value for money and price differences associated with
brand are related, distinct quantities.

### 7.1 Methods to investigate

| Method | What it can estimate | Data required | Main limitation |
| --- | --- | --- | --- |
| Hedonic price regression | Conditional price differences associated with attributes and brands. | The planned product/price data, with comparable size, retailer, time, and selling conditions. | Omitted quality and correlated features affect estimates; a brand term is an association. [BLS](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm) provides a statistical application of hedonic regression. |
| Comparison of matched products | Price differences between products with similar measured attributes. | Products with overlapping features for the category and selling context; composition, claims, format, and size are chocolate examples. | Check balance and reject comparisons without overlap; unmeasured quality remains a possible explanation. This is a proposed product application of [Rosenbaum and Rubin's method for matched sampling](https://dash.harvard.edu/entities/publication/73120378-8487-6bd4-e053-0100007fdf3b). |
| Conjoint using choices / discrete choice experiment | Consumer willingness to pay for features and brand identities. | A separately collected consumer study with varied prices and attributes. | Sampling, experimental design, a meaningful option to make no purchase, and bias from hypothetical choices affect interpretation. See [Ben-Akiva, McFadden, and Train](https://eml.berkeley.edu/~train/papers/foundations.pdf). |
| Randomized experiment with brand information | The effect of disclosed brand information on preference or willingness to pay in the tested setting. | A new experiment holding the physical product constant while randomly varying brand information, with a monetary outcome if monetary premium is the target. | A blind taste ranking alone does not yield a monetary premium. Related evidence from a food category is [Bronnenberg, Dube, and Sanders' blind taste experiment with private labels](https://www.nber.org/papers/w25214). |

The last two options require new consumer or experimental data before use.

### 7.2 Candidate measures

In a model of log price with additive brand terms, the conditional price
difference associated with brand relative to an explicit reference brand is:

```text
brand_difference_percent = 100 * (exp(alpha_brand - alpha_reference) - 1)
```

This comparison needs adequate feature overlap and the same selling context.
With interactions, calculate the contrast at specified product attributes.
It is not proof of the price effect of renaming the same physical product.

A candidate indicator of adjusted price is:

```text
adjusted_price_indicator = log(benchmark_price / observed_price)
```

Define the benchmark using the same attributes and selling context, with an
explicit reference brand or stated brand distribution supported by the data.
Larger values mean a lower observed price relative to that benchmark. Use
predictions from models fitted without the evaluated rows, either with a held out
sample or across validation folds, so their own prices do not directly determine
their benchmark.

A percentile within a defined comparable cohort could map the indicator onto a
0-100 score. This is a proposed scoring convention, not a universal scientific
definition of value for money. The cohort, benchmark, price basis, and uncertainty
must be visible, and scores would be relative to that cohort.

Do not label `observed_price - predicted_price` as brand premium. That residual
also includes omitted attributes, selling conditions, and prediction error.
Refitting without brand does not create a price with brand value removed:
correlated attributes can retain differences associated with brand.

For a simple choice model with linear price utility, an attribute's marginal
willingness to pay can be estimated as:

```text
WTP_attribute = -beta_attribute / beta_price
```

This uses consumer choices rather than listed prices. The ratio requires an
identified price effect, uncertainty estimates, and an appropriate utility
specification; a price coefficient near zero makes it unstable. See the
[Goett, Hudson, and Train choice study](https://eml.berkeley.edu/~train/papers/RetailEnergy.pdf).

### 7.3 Research recommendation

Investigate prices adjusted for attributes and conditional brand comparisons
using the planned category dataset, matched product checks and uncertainty.
Assess price position with these methods. Design separate studies for consumer
value or causal effects of brand information, and keep scoring deferred until
its definition and evidence are agreed.

## 8. Acceptance scenarios for stages 1 and 2

The scenarios for chocolate illustrate one category profile. The
[data acceptance scenarios](../data/spec.md#8-acceptance-scenarios-for-stages-1-and-2)
cover input evidence and processing; the
[app acceptance scenarios](../app/spec.md#8-acceptance-scenarios-for-stages-1-and-2)
cover supported price review and presentation.

| Scenario | Expected behavior |
| --- | --- |
| A certification appears only in one brand. | Flag identification/support limits; do not claim a separately established causal certification premium. |
| A dataset contains repeated offers and related sizes. | Keep product families together during validation on held out data. |
| The design has an unseen brand or unsupported feature combination. | Use a validated, labeled fallback where available or report insufficient support. |
| No reliable model passes the study's release criteria. | Show data/validation limitations and do not claim a supported price estimate. |

## 9. Decisions still to make

- Numerical model release criteria for the study.
- Whether stage 3 will define value for money as a comparison of adjusted prices or
  include separately collected consumer utility/quality evidence.

The [data decisions](../data/spec.md#9-decisions-still-to-make) cover study
boundaries, evidence coverage, extraction review and schema requirements that
inform model readiness. Resolve these decisions before the corresponding
implementation or release commitment.

## 10. Gold and the finalized training basis

The [data specification](../data/spec.md#10-gold-and-the-finalized-training-basis)
owns Gold architecture, immutable snapshots, inferred exports, family mappings
and population loader behavior. This section retains the historical target and
experimental trainer requirements. The [current study target](#current-chocolate-study-price-target)
below supersedes the regular-price requirement for current chocolate training.

Model design, predictor selection, training input preparation, family splits,
encoders and design matrices belong to the downstream
[Silver-to-Gold procedure](../../plugins/category-processing/skills/category-processing/references/silver-to-gold.md)
after category-processing produces standardized Silver with quality metadata.
Parsed and inferred values remain usable under the Silver contract. The data
specification owns source interpretation, review decisions and canonical Parquet
Gold export.

The portable `prepare-model` compatibility helper writes JSONL inputs, splits,
encoders and matrices; it does not create canonical Parquet Gold. The historical
loader requires `model-design.json` and emits legacy training views. Standard
Silver v2 loads four field contracts; `prepare-gold` accepts its study design
separately. Historical portable profiles retain their selected price contracts,
separately from current chocolate model preparation below.

Historical regular-price models and the portable processing profiles use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive selling price, with `fallback_policy: reject`. Retain displayed/promotional/reference amounts as evidence; none substitutes for the target, and no tax guess or reverse discount is permitted. A separately evidenced regular amount alongside a promotional offer is supported. Chocolate normalizes GBP per 100g and logs it; other categories retain their declared currency and quantity basis. This fixed monetary basis supersedes earlier examples allowing excluded-tax model targets, without changing the preserved observations. Generated custom profiles retain this basis.

The experimental `chocolate-pricing-design-3` trainer reads verified Gold, with Silver compatibility, and saves immutable runs. It implements log-price OLS, family holdout, training-only encoders, support/rank/confounding gates and family-cluster bootstrap coefficient intervals. It validates actual targets against the copied observations under the selected price basis. Empty populations and invalid required inputs yield a readiness report and no fitted artifact. This implemented experimental baseline does not establish release readiness or supersede the proposed LightGBM/SHAP research design. [The published contract release](../data/analysis/gold-modeling-contract-release.md) documents the verified publication and exact changes.

## Current chocolate study price target

The user's 2026-10-03 instruction supersedes the regular-price requirement for
current chocolate training. Use `current-consumer-price-1`: collected current
displayed GBP price normalized by actual positive edible weight to GBP per 100 g,
with log scale for regression. Separate regular price, promotion classification,
review flags on the monetary observation and confirmed tax inclusion do not gate
target preparation. Original metadata stays preserved. The effective target is
recorded in model artifacts; no silent substitution into a historical study is
allowed. See the [modeling specification](../data/chocolate-modeling-design.md#1-population-and-price-target)
and [project limitations](../../PROJECT.md#limitations).

## Independent LightGBM with brand implementation

The [LightGBM with brand guide](../data/chocolate-lightgbm-with-brand.md) owns the independent experimental trainer, explicit unpublished working experiment, grouped fitting selection, retailer calibration, native TreeSHAP and artifact integrity. The assigned estimator is implemented; fixture validation and real-data readiness are recorded in the lifecycle plan. Its historical rebuilt Gold has 2,134 candidates and zero eligible rows. The historical promoted Gold snapshot marked every candidate eligible; this trainer requires migration to the current-price policy and shared handoff fields. Real fitting, authoritative handoff migration, comparator gates and supported release remain pending.

The user requested committing the task and publishing changed data. That historical Gold
publication contains 2,134 eligible candidates in both Parquet views, with its
full original parent. Immutable dataset revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7` and per-file checksums are recorded
in the [Gold reference](../../schemas/chocolate/gold-dataset.json). All 25 files
were downloaded and byte/loader verified. Publication and fitting are separate;
current-price preparation remains the explicitly versioned training operation.

## Independent LightGBM without brand

The [without-brand implementation](../data/analysis/lightgbm-without-brand-implementation.md)
provides its own regular-price working experiment, seeded family partitions,
family balancing, fitting-only grouped tuning, retailer calibration and native
raw-log TreeSHAP reconstruction. It saves immutable runs and supports verified
run loading. Synthetic validation is published separately from real fitting.
For that historical experiment, current-price migration, full comparisons and
released product scenario interfaces remain pending. The later
[inferred refit](#gold-training-admission-and-inferred-lightgbm-refit) is a separate
current-price exploration path. [Model maintenance](../model-maintenance.md)
owns artifact storage in Hugging Face and immutable receipts in Git.

## 11. Independent family-weighted hedonic trainer

`--model-id hedonic_without_brand` selects an independent family-weighted log-linear estimator with an explicit local working contract and verified immutable Gold. It supports fitting-only grouped formula selection, known-brand rank probing without fitting another estimator, refitted family-bootstrap uncertainty, retailer-specific split conformal calibration, support rejection and final-test metrics. The existing equal-listing OLS command retains its contract. The [implementation record](../data/analysis/hedonic-without-brand-implementation.md) defines the exact cohort, missingness, split, support, artifact and validation rules. The inspected historical regular-price Gold has 2,134 candidates and zero eligible rows; its contract also lacks three required cohort/core fields. No real fit or release is established. A coordinated dataset/portable producer migration and evidence reviews remain necessary before this working handoff can be supplied by the canonical pipeline.

## 12. Independent matched retailer implementation

`--model-id matched_retailer` now dispatches a separate weighted exact-variant
and retailer fixed-effect estimator from verified immutable Gold. Its explicit
unpublished working contract, field-level matching evidence, 48-hour rule, frozen
family splits, overlap/bridge diagnostics and family uncertainty are documented
in [the matched retailer guide](../data/chocolate-matched-retailer.md). The original
`chocolate-pricing-design-3` OLS path remains separately identified. This diagnostic
does not supply new-product or regression conformal intervals. The independent
initial real rebuild had 2,134 candidates and zero eligible rows; readiness reports record
blockers and no fitted model. Fixture validation establishes implementation
behavior only. Common comparison/champion gates and coordinated dataset/portable
contract adoption remain pending.

The user's confirmed Gold verification is accepted through
`--verified-gold-candidates` for `matched_retailer`. This explicit task option
considers Gold candidates without editing stored flags or rebuilding layers.
The run records its authorization basis and checks concrete target/identity
values. Missing prices or exact variant IDs remain missing inputs. See the
[direct Gold path](../data/chocolate-matched-retailer.md#task-authorized-gold-verification).

Promoted Gold snapshots use `chocolate-gold-bulk-eligibility-1` and persist
explicit user eligibility provenance with the complete original parent. The
loader verifies exact flag/exclusion changes and unchanged analytical fields
before returning the promoted tables. Matched training records the new Gold
manifest/provenance and can bind an explicit local input contract to copied
snapshot contracts. The [Gold guide](../data/chocolate-gold.md#explicit-bulk-eligibility-snapshot-loading)
and [matched refresh](../data/chocolate-matched-retailer.md#refresh-from-promoted-gold)
own these interfaces. Eligibility does not supply missing price or identity
values; the recorded 2,134-row promoted snapshot has no regular targets or exact
variant IDs and the fresh assigned-model attempt cannot fit.

The user has superseded the regular-price requirement for the current study.
Matched working design `chocolate-matched-retailer-design-3` uses actual
collected current/displayed GBP prices under `current-consumer-price-1`. It
records promotions and tax uncertainty as limitations and normalizes using
positive candidate edible weight matching the price observation. Source regular
fields remain preserved. Its target binds published design
`chocolate-pricing-current-price-design-1` at immutable dataset commit
`d743cb8dbca37f5241cccd444a16165523304f6c`; shared preparation
`chocolate-current-price-target-1` yields 630 targets from the 2,134-row promoted
Gold snapshot. Every row lacks an exact variant ID, so the assigned matched model
has no fitting rows.
The [current-price diagnostic policy](../data/chocolate-matched-retailer.md#current-price-study-policy)
owns the explicit target, quantity selection, source preservation and verified
shared-contract binding; exact matching is still required.

## Gold training admission and inferred LightGBM refit

The user instruction of 3 October 2026 establishes
`chocolate-gold-training-all-rows-2` at the training boundary.
`scripts/chocolate_gold_training.py` verifies immutable source Gold before
exposing every candidate without `model_eligible` or `exclusion_reasons`.
The adapter accepts conventional Gold and the inferred wrapper. It preserves
prior flags and exclusion reasons as source provenance and retains original
price bytes beside the trainer price view. Training reports distinguish saved
source counts from admitted counts. Source snapshot verification continues to
check the exact historical file hashes, row digests and reports.

OLS, hedonic without brand and both historical LightGBM trainers consume the
canonical `verified_gold` population loader. The inferred refit uses this
wrapper adapter to retain its historical child provenance. Silver compatibility inputs retain their selected contract.
All-row Gold eligibility supplies no missing numbers, identity relationships or
model cohort fields. Historical fixed-price experiments retain their targets
and can record numerical or context readiness failures.

`--model-id lightgbm_without_brand --gold-root <inferred-bundle>` without a
historical working contract routes to the inferred exploration adapter. It
consumes authoritative product cells and source prices under the pinned
`current-consumer-price-1` contract. Its bar/Waitrose/Ocado research domain uses
established family IDs and actual positive pack mass and GBP displayed prices.
Unknown and conflict attributes remain null and use native missing routes.
Brand is excluded from all fitted matrices; no known-brand rank gate restricts
this independent exploratory estimator. Recipe and single-pack status remain
unestablished; cocoa percentage is omitted because its comparable basis is
absent.

The local experimental policy uses 80% fitting and 20% testing families,
ordered by SHA-256 of seed 1729, LF and family ID. Three inner family folds
select core versus enriched features and bounded tree settings using unit MAE,
with fold-specific category maps and recomputed family weights. The median
selected fold iteration count is frozen before final fitting. No calibration
partition or prediction intervals are claimed. All holdout rows contribute to
the primary metric; support-restricted metrics are additional diagnostics.
Artifacts bind source manifests, pinned target bytes, implementation hashes,
selected rows, tuning, preprocessing, booster and native TreeSHAP results. The
[refit record](../data/analysis/lightgbm-without-brand-inferred-refit.md) owns the
actual fit and its small-sample limitations. It remains an experimental research run
with no champion or serving-reference replacement. The completed model was
subsequently published at immutable dataset revision `88b08aeada37e228fcd80334b5abddd768da6968`.
The [receipt](../data/analysis/lightgbm-without-brand-inferred-model-publication.json)
records all 16 remotely verified model/metadata files and exact preservation
of the previous dataset inventory.
