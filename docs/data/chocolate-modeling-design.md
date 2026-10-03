# UK chocolate pricing model design

The Gold training population includes every candidate automatically. New Gold
rows have no `model_eligible` or `exclusion_reasons`; all model implementations
validate their actual required inputs and declared study cohort. Readiness
blockers remain explicit for missing quantities, targets, identity or features.
The [Gold contract](chocolate-gold.md#output-contract) owns storage, migration and
historical loader behavior.

Updated: 3 October 2026. Status: consolidated design; an experimental inferred Gold model without brand is fitted; market validation remains pending.

The independent [without-brand trainer](analysis/lightgbm-without-brand-implementation.md)
implements a separate historical regular-price experiment with published
synthetic validation. Current-price migration and market validation remain pending.

Build a median-price baseline, interpretable hedonic models, and LightGBM
prediction candidates with and without brand. Keep hedonic regression for
coefficient comparisons; select the prediction model through grouped validation.
Explain LightGBM predictions with TreeSHAP and a grounded AI narrative. The first
supported domain is standard chocolate bars sold by UK supermarkets. The outputs are conditional price
associations and retailer-specific market price benchmarks. Add a matched-product
retailer diagnostic to distinguish retailer pricing from assortment differences.

This design specifies the modeling direction in [the specification](../spec.md),
sections 3–7. The [data review](analysis/chocolate-data-review-2026-10-03.json)
records the inspected 1,844 source records and 2,445 captures. Numerical usability and
identity resolution determine the actual analytical sample.
The [LightGBM, SHAP, and AI explanation design](analysis/lightgbm-shap-explanation-design.md)
defines training, attribution units, and the narrative contract in detail.

The source [silver workflow](chocolate-silver.md) and
[schema guide](chocolate-schema.md) retain `chocolate-pricing-design-3` for their
original evidence contract. Current-price model preparation selects
`chocolate-pricing-current-price-design-1` downstream of verified Gold. The
complete model comparison remains a separate design and validation task.
Its 11 required predictors, rejection of missing selected values, and current
training/validation helpers differ from the brand/no-brand variants,
optional-feature policy, and calibration design below. Implementing this proposal
requires a new aligned version of the affected machine contracts and helpers,
with regenerated reviewed inputs; existing snapshots retain their own contracts.

## 1. Population and price target

Include single-pack eating-chocolate bars: plain, with inclusions, or filled.
Record milk-style, dark, and white chocolate separately, and retain explicit
dairy-free claims. Exclude multipacks, assortments, gift sets, advent calendars,
personalized products, novelty shapes, hot chocolate, subscriptions, and
chocolate-coated non-chocolate foods from this first domain.

The primary study starts with Waitrose and Ocado observations, with retailer as
an explicit input. Tesco is a planned extension: the reviewed snapshot has no
Tesco corpus. Its predictions require new eligible evidence, fitting, and
retailer-specific validation/calibration. Direct-brand and specialist-shop prices
use separate subsequent study configurations; their selling mechanisms and
brand/channel overlap differ.
Never pool them silently into the supermarket model.

The current study uses `current-consumer-price-1`: the positive collected current
(displayed) GBP selling-pack price is the modeling target and serves as the
study's regular-price proxy. A separately evidenced regular price is not needed.
Promotion classification and confirmed tax inclusion do not gate this target.
Keep the original promotion, membership and tax metadata as limitations. Use
recorded source captures across available dates; no date arguments are required
for the hedonic study. A capture is not a live quote.

The regression target and pack conversion are:

```text
unit_price = current_displayed_pack_price_gbp / total_edible_weight_g * 100
y = log(unit_price)
predicted_pack_price = predicted_unit_price * total_edible_weight_g / 100
```

Actual positive edible weight is required for unit normalization. Missing current
prices, weights and identities remain missing. Promotions, membership conditions,
unverified tax inclusion and variation across capture dates can influence fitted
product, brand and retailer associations. The [project limitations](../../PROJECT.md#limitations)
record these interpretation limits.

`chocolate-pricing-current-price-design-1` is the dataset-owned current target
contract. `scripts/chocolate_current_price.py` derives training inputs from the
verified Gold candidate and auxiliary price views. `current_price_targets`
retains every Gold candidate, produces explicit `current_price_per_100g_gbp`
and `log_current_price_per_100g_gbp` targets, and records missing-value counts.
Existing experimental trainers may read the corresponding `regular_*` aliases;
under the recorded current-price contract those aliases carry the same current
price proxy and assert no separate regular price. Source Gold, Silver prices,
review states and earlier snapshots retain their original bytes.

The experimental OLS command uses `--current-price-target`; three independent
training chats apply the same policy to their selected model designs. Run
artifacts retain the exact source Gold manifest, original price observations,
current target contract, effective design, preparation counts and limitations.
Historical regular-price studies retain `regular-consumer-price-1` and their own
contract metadata.

Retain a fitted size term because unit normalization does not remove quantity
discounts. With the same rows and freely estimated log-weight term, unpenalized
log pack-price and log unit-price fits are algebraic reparameterizations, not
independent model benchmarks.

## 2. Analytical records and weighting

Keep three versioned tables, derived without rewriting the raw archive:

| Table | Contents |
| --- | --- |
| Product variants | Canonical variant and family IDs, source IDs, reviewed brand, form/type, labeled edible weight, pack configuration, and identity evidence |
| Feature evidence | Normalized value, raw evidence location, capture/source ID, extraction method, review status, and unknown/conflict reason |
| Price observations | Variant, retailer ID, online/in-store channel, available store/location context, source-price window, currency, pack price, regular/promotion and membership basis, tax basis, stock evidence, freshness, quantity, and computed unit price |

Retain silver's unique seller listing records and stable seller UIDs. Reviewed
physical-variant and family relationships link listings across sellers without
merging their source rows. One analytical row represents one reviewed
variant–retailer observation in the declared snapshot. Duplicate imports and enrichment captures of the same price
occasion produce one row. Different retailer observations remain separate.
Related sizes and flavors share a family ID; identity matching requires
formulation and pack evidence, not name equality alone.

Traverse all captures: the audit found earlier browser listing data missing from
latest Ocado captures and repeated identical Waitrose catalogue contexts. Derive
edible weight from labeled quantities and pack count. Catalogue `grams` is
unreviewed source/shipping metadata; it cannot substitute for net edible weight.
Preserve price and recipe conflicts instead of resolving them through inference.

Give every product family total weight one within each training/evaluation
partition. If family `f` has `n_f` eligible rows, each row has weight `1 / n_f`.
This prevents many sizes or retailer copies from dominating. These are balancing
weights, not sales shares or inverse measurement variances.

## 3. Features and missing values

Required inputs are cohort, retailer, verified positive edible weight, and reviewed
chocolate type. Training also requires resolved variant/family/brand identity and
eligible price evidence. Brand is optional at prediction time for the market
benchmark.

| Feature block | Encoding |
| --- | --- |
| Size | `log(total_edible_weight_g)` |
| Type and recipe | Reference-coded type; plain/inclusion/filled recipe; reviewed broad inclusion classes, including nut ingredients |
| Cocoa | Percentage plus its evidence basis; percentage of the chocolate portion is distinct from percentage of the whole product |
| Claims | Separate named certification, organic, vegan/dairy-free, and origin claims when identifiable; `present`, `explicitly_absent`, and `unknown` remain distinct |
| Selling context | Retailer fixed effects in hedonic models; native retailer categories in LightGBM; channel/location/membership context defines comparable observations |
| Brand | Reference-coded fixed effects in `hedonic_with_brand`; native brand categories in `lightgbm_with_brand`; omitted from `hedonic_without_brand`/`lightgbm_without_brand` |

Allergen warnings such as "may contain nuts" are not nut-ingredient features.
Nutrition, visual packaging, unrestricted marketing text, and embeddings are
outside the first model. Preserve their evidence for later schema extensions.

Use an explicit unknown category for optional categorical attributes. For an
optional numeric cocoa value, fit a training-only median within supported
type/basis groups plus a missing indicator; use a training-wide median if a
group has no usable values. This is an input transformation, not an inferred
recipe. Never impute price or edible weight. Every fitted imputation value and
category mapping travels with the model.

Create a core feature fit using size, type, broad recipe/inclusion terms, and
retailer. Add cocoa and claim terms only when evidence quality, within-brand/source
overlap, and training validation support them. Compare core and enriched fits on
the same eligible rows; also report how an evidence-rich subset changes the
represented brands and prices. Select the feature set using training data only.

Require full-rank encoded inputs for the hedonic models and check rare levels,
correlations, and coefficient stability. Preserve a poorly supported feature in the analytical
table but omit its standalone estimate. If brand and retailer effects are aliased,
fit separate retailer models. Certification exclusive to one brand cannot produce
a separately identified certification estimate.
Finalize a common admissible feature set after checking `hedonic_with_brand`
identification; omit aliased optional terms from both fits. If required core
terms remain aliased, `hedonic_with_brand` is unavailable for that configuration
rather than reporting arbitrary effects.
LightGBM does not require a full-rank linear design, but correlated inputs still
prevent separate causal interpretations. Use the common admissible feature set
for the first model comparison; nonlinear fitting cannot create missing overlap.

## 4. Model architecture

Use the descriptive names below in reports and the stable model IDs in stored
results, explanation packets, and model bundles. The name states the method and
brand input; it does not assert market representativeness or causal brand value.

| Model name | Model ID | Definition | Use |
| --- | --- | --- | --- |
| Retailer Median Price Baseline | `retailer_median` | Family-weighted median unit price by chocolate type and retailer, with retailer-wide fallback learned from training data | Benchmark for prediction error; fallback context is recorded |
| Hedonic Price Benchmark Without Brand | `hedonic_without_brand` | Weighted log-linear hedonic regression using the supported feature set, retailer fixed effects, and validated retailer interactions, with no brand term | Brand-unspecified benchmark for the selected retailer |
| Hedonic Price Benchmark With Known Brand | `hedonic_with_brand` | The hedonic feature/context design plus supported brand fixed effects | Price testing and conditional brand/feature comparisons for represented brands |
| LightGBM Price Benchmark Without Brand | `lightgbm_without_brand` | Family-weighted gradient-boosted trees on log unit price, using the same supported input information as the hedonic model without brand | Nonlinear prediction candidate against the corresponding hedonic model; local/global TreeSHAP explanations |
| LightGBM Price Benchmark With Known Brand | `lightgbm_with_brand` | Separately fitted boosted trees using the same supported input information as the hedonic model with brand | Nonlinear prediction candidate within the supported brand–retailer domain |
| Matched Retailer Price Comparison | `matched_retailer` | Exact product-variant fixed effects plus retailer fixed effects on contemporaneous matched listings | Same-product retailer price contrasts for the matched assortment; no new-product prediction |

The Retailer Median Price Baseline conditions only on retailer and chocolate
type. Edible weight converts pack price into GBP/100 g, but the baseline does
not fit a size effect or adjust for brand, recipe, cocoa, or claims. Its
retailer-wide fallback also drops type conditioning and must be flagged.
Median differences can therefore reflect both pricing and assortment; they are
not adjusted retailer premiums. The four price regressions use the features in
section 3, with brand included only in the known-brand versions. Adjusted
retailer contrasts still require overlap, especially when brands are exclusive
to one retailer. Use matched exact variants for the dedicated retailer comparison.

Fit both hedonic models separately by minimizing family-weighted squared log
residuals:

```text
hedonic_without_brand: y = intercept + size + type + recipe/inclusions
      + supported_cocoa_and_claim_terms + retailer_fixed_effect
      + supported_retailer_interactions + error
hedonic_with_brand: y = hedonic_without_brand_terms + brand + error
objective = sum_i weight_i * (y_i - prediction_i)^2
```

The [BLS hedonic-method application](https://www.bls.gov/cpi/white-papers/hedonic-quality-adjustments-statistical-agency-perspective.pdf)
supports price modeling using characteristics and selling context. This
chocolate application remains subject to its own evidence and validation.
Implementation can use [statsmodels weighted least squares](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.WLS.html)
for the fitted objective; use family-based uncertainty rather than default
inverse-variance standard errors for the balancing weights.

Use `hedonic_with_brand` when the supplied brand and brand–retailer context are
supported. `hedonic_without_brand` is a separately fitted benchmark when brand
is omitted. It does not represent a price
with brand value removed: correlated features can retain brand-associated
differences. `hedonic_with_brand` rejects unseen brands. Predictions for an actually new brand
remain experimental until a separate brand-held-out evaluation and calibration
supports that use.

Ridge regression, multilevel effects, splines, and image/text embeddings remain
deferred. LightGBM is included in the first comparison. There is no time term in
this effective collection snapshot.

### 4.1 LightGBM prediction candidates

Fit `lightgbm_without_brand` and `lightgbm_with_brand` separately with the same
target, eligible observations, family weights, feature evidence, retailer
contexts, and partitions as their respective
hedonic comparators. Use squared log-price loss. Native categorical features
allow trees to learn supported nonlinearities and interactions without manually
duplicating the hedonic interaction columns. Use the same explicit missing-value
policy initially, and persist category mappings and unsupported-level rules.

Use small trees and regularization, with bounded hyperparameter selection and
early stopping inside grouped fitting-partition validation. Apply fold-specific
family weights to training and validation; choose settings using original-scale
unit-price MAE. Inspect independent-family support in leaves as well as row
counts. Freeze the final booster and tree count before calibration and testing.
The [LightGBM regressor API](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html)
supports sample weights, categorical inputs, and validation configuration.

Select a prediction champion separately for the brand-unspecified and known-brand
domains using fitting-partition validation. Retain the hedonic candidate when
LightGBM does not meet the predeclared improvement rule. Save all candidates'
final evaluation, and label every prediction and explanation with its own model
ID. Calibration and SHAP must use that exact frozen model and tree count.
LightGBM's routing of missing or unseen categories does not override domain
rejections, including unsupported Tesco or new-brand predictions.

### 4.2 Retailer effects and audience positioning

Retailers can price the same bar differently and can stock different kinds of
bars. Model these as separate sources of observed variation. The retailer fixed
effect captures a conditional price-level difference relative to a named
reference. Limited retailer-by-chocolate-type and retailer-by-log-weight
interactions allow that difference to vary by product profile. Other explicit
hedonic claim or brand interactions are deferred until overlap and independent-family support
justify them. Retain interactions only if training grouped validation improves
prediction and estimates remain stable.
LightGBM receives retailer as a native category and can learn interactions from
the same supported inputs. The complete-prediction retailer contrasts below
apply to either prediction model; learned interactions still require support.

Use Ocado as the initial reference retailer where it is supported; the reference
is recorded with each fit. For two supported retailers A and B and the same
product profile `x`, report:

```text
retailer_difference_percent(x) = 100 * (exp(f(x, A) - f(x, B)) - 1)
retailer_difference_gbp(x) = predicted_pack_price(x, A) - predicted_pack_price(x, B)
```

Compute the contrast from complete predictions, including retailer interactions.
Do not apply a universal markup to every product. Retailer terms in `hedonic_without_brand` can still
absorb unmeasured brand/quality mix; `hedonic_with_brand` conditions on supported brand terms too.
Report these feature-adjusted contrasts separately from `matched_retailer`.

`matched_retailer` uses only reviewed exact variants sold at multiple retailers: the same
formulation, flavor, edible weight, and pack configuration. Its model is:

```text
log(unit_price_variant_retailer) = variant_fixed_effect
    + retailer_fixed_effect + error
```

The variant intercept absorbs product attributes, including brand. Family IDs
group uncertainty and weights; they do not replace exact-variant matching.
The [ECB's barcode-based price comparisons](https://www.ecb.europa.eu/press/research-publications/resbull/2023/html/ecb.rb230420~fecc3b10ca.en.html)
illustrate comparing identical products to limit composition differences; `matched_retailer`
is this study's proposed diagnostic.

Pair genuine price observations within 48 hours by default, with consistent
channel, location coverage, tax, membership, and regular-price basis. Missing
location remains unknown; include it only where the documented price scope
establishes comparability. Exclude unresolved contexts. Cached-page invocation
times do not establish observation dates. If later studies add period terms,
retailers must also overlap in periods; a time term cannot resolve complete
retailer/time confounding.

Build a retailer–variant overlap graph. Report matched variants and independent
families per retailer link, direct versus indirect comparisons, and families
bridging retailer groups. Estimate contrasts only within connected components;
check leave-one-family-out stability and bootstrap disconnections. Weak bridges
can make a comparison unsupported despite algebraic identification. `matched_retailer` describes
the matched assortment and is not a blanket adjustment for unmatched products.
Use fitting-partition evidence for `matched_retailer` whenever it informs feature or model
choices. Any later full-sample descriptive refit is labeled separately and does
not feed back into the frozen validation results.

Different target audiences are a plausible explanation for retailer pricing,
alongside service, competition, and costs. Listed prices alone do not identify
that mechanism. Do not assign guessed premium/budget segment labels from names
or fit redundant segment dummies that duplicate retailer identity. A distinct
audience-effect study needs shopper, basket, demographic, or choice evidence.

For the Tesco extension, collect a labeled assortment sample and exact variants
shared with Ocado/Waitrose, refreshing all matched prices in the same window.
Matched products identify retailer comparisons; the broader sample establishes
which Tesco product profiles the prediction model can support.

## 5. Explanations and uncertainty

The coefficient interpretation below applies to both hedonic models. It does
not decompose a LightGBM prediction. Matched retailer comparisons, hedonic
coefficient contrasts, complete-model scenario differences, and SHAP
attributions are distinct outputs.

Name reference levels and report supporting independent families for every
estimate. For a binary term `beta`, the fitted conditional percentage contrast
is `100 * (exp(beta) - 1)`. Report continuous contrasts in explicit units, such
as a ten-percentage-point cocoa change within the same stated basis.

Also compare predicted prices for two stated, supported profiles with all other
inputs held fixed. Brand contrasts use `hedonic_with_brand` and an explicit reference brand.
Percentages are multiplicative; they are not additive shares of the final price.
Contrasts describe associations. Missing overlap and unmeasured quality prevent
causal interpretations of adding a claim or changing the brand name.
Retailer contrasts also remain conditional associations; an observed difference
does not establish the causal effect of changing the retailer's audience.

Estimate coefficient/contrast uncertainty by resampling whole training families
and refitting the preprocessing and fixed model formula. Report instability and
rank failures in bootstrap fits; do not hide them behind narrow intervals. These
intervals condition on the chosen formula and exclude model-selection uncertainty.
They are distinct from the prediction interval for a new product.
Each resampled family copy retains total weight one, so repeated draws preserve
bootstrap multiplicity rather than collapsing back to the original family.

The default point output is `exp(fitted_log_price)`, labeled a geometric-price
benchmark. It is not automatically an arithmetic mean or conditional median.
An arithmetic-mean output requires a separate training-only retransformation
correction and original-scale validation; it is outside the initial output.

### 5.1 TreeSHAP and AI interpretation

For both LightGBM models, compute exact TreeSHAP attributions in raw model-output
units: log GBP per 100 g. The base value plus signed feature contributions reconstructs
the frozen model's log-price prediction. Exponentiating a contribution gives
a factor in that decomposition, not the effect of adding an ingredient or an
additive GBP amount. A SHAP value is not a prediction interval or an estimate
of causal brand, claim, or retailer value.

Use a version-verified tree-path-dependent explainer without an external
background for the native-categorical LightGBM model. Its base is a model
explanation reference, not `retailer_median`'s median or a family-weighted market average.
Enforce an independent numerical reconstruction check against the identical
prediction. Report local signed contributions and family-weighted held-out mean
absolute contributions, grouping related fields before calculating magnitude.
See [TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html)
and the [implementation contract](analysis/lightgbm-shap-explanation-design.md).

Report individual trait contributions and one signed percentage per trait family
of each final predicted price using [the specification's allocation](../spec.md#521-trait-and-trait-family-percentages-of-predicted-price).
Map traits to the schema's attribute families, with modeled brand in identity
and scope and retailer in a selling-context family. Derived encodings and missing
indicators stay with their underlying trait. These groups differ from product
families used for splits. Include the model reference percentage in the total;
families alone need not sum to 100%. This deterministic allocation is a proposed
display convention, distinct from raw log SHAP, coefficient contrasts and global
importance. Persist its mapping and method with the explanation bundle.

The AI receives a validated explanation packet containing prediction, units,
context, interval status, supplied features and evidence, SHAP values, and
support limits. It writes a short plain-language account of what moved this
model prediction above or below its reference. Deterministic code owns
arithmetic and rankings. Validate claims, references, directions, and numbers;
use a fixed explanation template when validation fails. If SHAP is unavailable
or reconstruction fails, the template omits attribution and reports only the
validated prediction and support status. Correlated brand,
retailer, and claims require explicit caution; missing evidence cannot be
described as ingredient absence. Do not invent consumer segments, quality,
demand, or optimal-price conclusions from SHAP.

## 6. Splits and prediction intervals

Split complete families into approximately 60% fitting, 20% calibration, and
20% final testing, with a persisted seed and split manifest. Keep duplicate
retailer listings and related variants together. Select features using grouped
cross-validation inside the fitting partition; fit preprocessing there too.
Select features, LightGBM settings/tree count, and the prediction champion inside
this partition. Freeze each model before calibration and leave the final test
untouched.
[Grouped validation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)
prevents a family from appearing in both fitting and validation.

Use random whole-family splits without forcing within-brand quotas. Determine
the supported brands and combinations for `hedonic_with_brand` and
`lightgbm_with_brand` from fitting data, then apply that frozen support filter
consistently to calibration and testing. Unseen or insufficiently
supported brands stay outside their domains. If independent families cannot support
fitting, calibration, and useful evaluation, retain experimental fits and do not
release supported price testing.

Calibrate each of the four price regressions separately for each supported
retailer. Within that retailer, select one observation per calibration family
uniformly using a saved seed and
a sorted identity list. Fix this outcome-independent selection rule before
examining prices or residuals, and apply it to final-test families. This defines
the representative-family population for the interval assessment.

For a 90% split-conformal interval on the log unit-price scale:

```text
r_i = abs(log(observed_unit_price_i) - fitted_log_price_i)
k = ceil((n_calibration_families + 1) * 0.90)
q = k-th smallest calibration residual
unit_price_interval = [exp(fitted_log_price - q), exp(fitted_log_price + q)]
pack_price_interval = unit_price_interval * edible_weight_g / 100
```

Calibration scores are unweighted; the training weights do not transfer to this
ordinary conformal construction. If `k` exceeds the calibration count, the
interval is unbounded/unavailable, rather than clipping the rank. Nine families
are the mathematical minimum for a finite 90% interval, not a readiness target.

[Conformal prediction](https://arxiv.org/html/2107.07511v6) provides marginal
coverage under exchangeability. Here that assumption concerns representative
families within the declared retailer/snapshot population. It does not guarantee
coverage for every brand, every arbitrary design, or future prices. Repeated
observations need special care, as [hierarchical-data research](https://arxiv.org/html/2306.06342v4)
explains. Report empirical coverage and width for the specified task.

A family-based interval does not validate unseen-brand coverage. Run a separate
brand-held-out diagnostic for `hedonic_without_brand` and
`lightgbm_without_brand`; actual unseen-brand support needs a brand-disjoint
fitting/calibration/test design with appropriate independent
calibration units. Until that is viable, do not advertise a calibrated
new-brand interval. A later-date holdout is required for future-price claims.

## 7. Evaluation and initial release rules

Compare `retailer_median`, `hedonic_without_brand`, and `lightgbm_without_brand`
on their common applicable observations. Compare `retailer_median`,
`hedonic_with_brand`, and `lightgbm_with_brand` on the common known-brand domain,
reporting any smaller supported domain explicitly.
Report family-weighted MAE in
GBP/100 g and GBP/pack, weighted median absolute percentage error, signed bias,
and listing-weighted sensitivity results. Evaluate interval coverage and width
on the representative-family test population defined above, with independent
family counts and sampling uncertainty.
For retailer-specific point metrics, recompute `1 / n_f` using each family's rows
within that retailer. For interval metrics, each selected representative has equal
weight; report unweighted coverage and median relative width separately by retailer.

Break results down by retailer, type, size, brand, and evidence missingness. Flag
poorly supported strata instead of assigning them precise quality claims. Do not
use training R-squared as a readiness criterion.
Report errors separately for products shared across retailers and products
unique to one assortment. Compare the retailer-aware fits with a no-retailer
ablation inside training validation. Retailer-held-out checks are diagnostic;
neither fixed effects nor categorical tree routing establish a validated
prediction for an unseen retailer.

Use the following configurable engineering defaults, frozen before final-test
evaluation. They are design targets, not results established by the current data:

- At least 10% lower family-weighted unit-price MAE than `retailer_median` on the applicable
  domain, and weighted median absolute percentage error no greater than 20%.
- For each retailer's nominal 90% interval, a one-sided 95% Wilson lower confidence
  bound on test coverage of at least 85%. Median relative interval width,
  `(upper - lower) / point_estimate`, is no greater than 80% on that retailer's
  representative-family population. Coverage and width gates are separate.
- Reviewed eligible prices/quantities, traceable features, full rank for hedonic
  models, and explicit rejection of unsupported categorical levels or combinations.

For champion selection, initially require LightGBM to reduce grouped-validation
family-weighted unit-price MAE by at least 5% against its hedonic comparator.
Freeze this engineering threshold before selection; final-test release gates
still apply to the selected model. Do not switch champions after inspecting
calibration or test outcomes.

These gates evaluate the sampled snapshot domain; passing them does not prove
conditional coverage or forecasting accuracy. If a gate fails, save the model
and findings as experimental and return the readiness/validation report.

## 8. Prediction contract and deliverables

Require retailer, cohort, type, edible weight, and values or explicit unknowns for
the fitted optional features. Use the frozen known-brand champion,
`hedonic_with_brand` or `lightgbm_with_brand`, only for a supported supplied brand.
When brand is omitted, use the frozen `hedonic_without_brand` or
`lightgbm_without_brand` champion as a labeled benchmark. A supplied unseen brand
receives only an experimental brand-unspecified benchmark without a supported
new-brand interval. Reject invalid quantities, unseen retailer/type levels,
weights outside the supported range, and unsupported feature combinations.
Poorly supported but valid profiles receive an experimental result
with no supported interval claim.

Return model/data/schema versions, selected context, geometric unit-price and
pack-price benchmarks, interval and its scope, feature/brand contrasts with
references and uncertainty, and support flags. For a LightGBM prediction, also
return the SHAP method/reference, signed contributions and groups, numerical
reconstruction status, and validated AI explanation or template fallback.
For models with a validated additive explanation, include individual trait
percentages, one percentage per trait family and the model reference percentage
of the final predicted price, or an explicit unavailable status.
Hedonic comparisons remain separately labeled. When a proposed pack price is
given, return `proposed - predicted` and
`100 * (proposed / predicted - 1)` on the same selling basis.
For a supported retailer comparison, return separate estimates and marginal
prediction intervals for each retailer plus the predicted price difference.
Use a paired family bootstrap for uncertainty on the fitted difference; do not
subtract two marginal interval endpoints and call that a calibrated interval
for the price difference. An unseen retailer, including Tesco before its
extension passes validation, receives no supported retailer prediction.

Implementation proceeds through analytical tables and a readiness report, then
building the median baseline and fitting the four price regressions, matched
retailer comparisons, grouped validation, champion selection and calibration,
and a reproducible scenario/explanation
report. Persist preprocessing, coefficients, boosters and tree counts, package
versions, feature references, family weights, explanation packets/settings,
AI prompt/schema versions and validation status, split assignments,
calibration residuals/quantiles, evaluation, and model-domain
rules. The first deliverable is a batch research report; the application consumes
that validated model bundle later.

Value-for-money scores, consumer willingness to pay, causal brand value, demand,
and profit-maximizing price remain outside this model design. A later adjusted-
price indicator must use out-of-fold benchmarks and be labeled price position.

The [independent LightGBM with brand implementation](chocolate-lightgbm-with-brand.md) implements the assigned estimator under a separate unpublished working experiment. Native fitting, calibration and attribution are exercised with synthetic fixtures; its recorded historical real-data attempt had zero eligible inputs and absent shared handoff fields. The current published Gold makes all candidates eligible, while migration of this frozen trainer to the current-price policy and shared fields remains pending. Other estimators and the common comparison are outside this session.


The independent [retailer median refit](analysis/retailer-median-training.md#refit-after-integrating-main-and-the-published-gold-snapshot)
uses all 2,134 eligible rows from the exact published Gold revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7`. The current displayed-price target
produces 630 GBP/100 g values. Missing variant IDs and population boundary values
in every row, plus other family/quantity/context gaps, prevent fitting. Its
trainer preserves the original Gold/evidence bytes, applies the published
current target to its selected retailer/type predictors, and records the exact
Gold publication pin, target contracts and per-row readiness. Historical regular
mode remains available; no real baseline fit or upload is claimed.

## Independent regular-price hedonic implementation

The [hedonic_without_brand implementation](analysis/hedonic-without-brand-implementation.md)
provides a separately fitted family-weighted historical regular-price experiment,
validated on synthetic fixtures and published with its fixture status. It preserves
its original target, data and working-policy identities. The current-price study
on main is a distinct experiment; this merge does not relabel the published fit
or relax its cohort/recipe/pack-count requirements.

## Matched retailer implementation status

The independent [matched retailer diagnostic](chocolate-matched-retailer.md) now
implements exact-variant/retailer effects with family weights, a persisted random
60/20/20 family split (seed 1729), matching evidence gates, graph components and
weak bridges, leave-one-family-out stability and family bootstrap disconnections.
It fits fitting-partition evidence only, reports descriptive residual diagnostics
and records unavailable holdout predictions. It fits no comparator or full-sample
refit. The required local working contract is unpublished. The initial preserved-raw
rebuild had zero eligible rows. The published Gold now has 2,134 eligible candidates
and 630 current-price targets, but missing exact variant IDs still block fitting.
The six-model common feature policy, coordinated portable/dataset migration,
comparison and release decisions remain pending; this implementation does not
establish those outcomes.

## Inferred Gold LightGBM exploration

The [inferred refit](analysis/lightgbm-without-brand-inferred-refit.md) fits
an experimental current displayed-price model without brand. Gold supplies
all candidates; the declared cohort and available numerical inputs determine
the 55-row fitting and testing population. The published run uses an 80/20
family holdout and fitting-only three-fold selection. It has no calibration
partition, prediction intervals, champion selection or established market
validation. Its [publication receipt](analysis/lightgbm-without-brand-inferred-model-publication.json)
pins the immutable model payload and source snapshot.
