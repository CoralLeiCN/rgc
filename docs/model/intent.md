# Model intention

The model feature uses supported product facts and selling context to explain
observed prices and provide validated price benchmarks within a declared
category and market. Chocolate sold in the United Kingdom is the example study.
Product features, including brand, nuts and fair trade claims where supported,
can explain conditional associations with listing prices. These associations do
not establish causal effects, consumer value or an optimal selling price.

This is one of the three core features in the [project intention](../intention.md).
The [data intention](../data/intent.md) owns meaningful analytical data and its evidence;
the [app intention](../app/intent.md) owns the workspace through which users explore it
and consume supported model outputs. The 4 October 2026 data reassessment does
not plan model selection, training or evaluation. That scope applies to the data
reassessment and preserves the existing model feature described here.

This document organizes existing intentions and authorizations. It introduces no
new modeling plan or claim of validation. The [model specification](spec.md),
[model design](../data/chocolate-modeling-design.md), implementation records and
[lifecycle plan](../lifecycle/plan.md) distinguish designs, experimental fits,
synthetic validation and supported releases.

## Supported price explanations

Use the shared analytical schema and verified study inputs to estimate supported
feature contributions to price. Record the model's domain, feature support,
references, uncertainty, validation and limitations. Interpret results within
the sampled market and selling context.

Explain each supported prediction with individual trait contributions and one
signed percentage per trait family of the final predicted price. Include a
separate model reference percentage so the allocation reconciles to the price.
Trait families group related attributes; product families define identity and
validation groups. These percentages allocate a model prediction and do not
measure ingredient costs or causal premiums. The
[explanation design](../data/analysis/lightgbm-shap-explanation-design.md) and
[specification](spec.md#521-trait-and-trait-family-percentages-of-predicted-price)
own the numerical interpretation. Family percentage explanations require their
own implementation and validation before use.

The authorized application demo uses the published synthetic
`lightgbm_without_brand` fixture to calculate a price from supported inputs and
show signed SHAP field contributions relative to its model reference. Preserve
its synthetic status, single chocolate bar pack scope and historical
`regular-consumer-price-1` basis, as recorded in the
[fixture serving guide](../data/analysis/web-fixture-pricing.md). Fixture
validation does not establish a market benchmark. The
[app intention](../app/intent.md) owns its presentation and adoption boundary.

## Price review workflow

The intended validated workflow lets a retailer review an existing SKU, proposed
listing or price change against a supported model and comparable range. A brand
can also test a newly designed product. Declare the category, market, comparison
group and selling context, then report the estimate, prediction interval and
supported comparisons. Explain missing support for unsupported designs.

Supported price testing requires validated benchmarks and uncertainty. Products
used in training need held-out or out-of-fold results for their benchmark.
Remaining readiness work includes unresolved identities, missing quantities,
feature reviews and evaluation against a baseline. Market validation and
champion selection require their own evidence. A successful experimental fit,
new dataset publication or application prototype does not establish readiness
for this workflow.

The application supports evidence exploration and a declared prototype trait
score, with a later authorization for the synthetic prediction and field SHAP
demo. These capabilities retain their stated limits until supported price review
is validated. Application requests use pinned artifacts and do not automatically
adopt a new Gold release or model run.

## Chocolate input and target policy

The [data intention](../data/intent.md) owns the raw archive, combined Silver processing,
shared schema, stable seller identities, reusable product-family mappings and
immutable Parquet Gold interface. Use those verified inputs and preserve actual
analytical values, missingness and evidence when preparing a model's study.
Family relationships link separate seller observations without merging them.

Initial schema creation belongs to category-schema. Category-processing applies
that schema to preserved Bronze data and finishes at reviewed Silver. Model
design, predictor selection and training input preparation belong to the
subsequent Silver-to-Gold stage. Data retains source interpretation, evidence
review and the canonical Parquet Gold export interface.

The current Gold population includes every candidate automatically. Its
analytical rows omit `model_eligible` and related exclusion fields; original
source flags and exclusion reasons remain provenance. This policy supersedes
the earlier instruction to promote every entity's eligibility flag. Every
`gold_*` layer, including inferred Gold, admits all candidates for model
preparation. Models still validate required quantities, targets, identities,
relationships and features against the declared study. Population membership
cannot fill missing facts or establish a successful fit. The
[Gold guide](../data/chocolate-gold.md) owns storage, migration and historical
snapshot verification.

The current chocolate study uses `current-consumer-price-1`: the collected
current displayed selling price serves as the regular-price proxy. Normalize
GBP per 100 g using actual edible weight and retain the log price target. A
separately verified regular price, non-promotional classification and confirmed
tax inclusion do not gate this study. Preserve source price metadata and record
promotion, membership, tax and capture-date uncertainty in run artifacts and
[project limitations](../../PROJECT.md#limitations). Missing quantities and
identities still need concrete failure reports.

Historical `regular-consumer-price-1` snapshots and runs, and other study
contracts, retain their original price basis. The current-price instruction
supersedes the original regular-price assignment for current chocolate training;
it does not change a frozen historical experiment. Each new run records its
selected input, effective target contract, assumptions and limitations.

## Existing independent assignments and authorizations

The user requested six independent implementation and training sessions. Each
assigned estimator must establish its own implementation, meaningful fixture
validation and attempted real-data workflow independently of other fitted
artifacts. The following assignments were recorded in the original project
intention; they identify those sessions rather than assigning a role to whoever
reads this document.

| Original assignment | Preserved scope and reference |
| --- | --- |
| `lightgbm_without_brand` | Implement and validate the estimator independently, attempt real training, then refit from inferred Gold under the later current-price and complete-population instructions. See the [implementation record](../data/analysis/lightgbm-without-brand-implementation.md) and [inferred refit record](../data/analysis/lightgbm-without-brand-inferred-refit.md). |
| `lightgbm_with_brand` | Implement and validate the estimator independently, preserve immutable inputs, and record concrete real-data readiness failures. Its original assignment used the fixed regular consumer target; current chocolate training follows the later target policy above. See the [trainer guide](../data/chocolate-lightgbm-with-brand.md). |
| `hedonic_without_brand` | Independently implement and attempt real training with product-family partitions. Preserve the original regular-price experiment and concrete blockers; later current chocolate attempts declare the current-price contract. See the [implementation record](../data/analysis/hedonic-without-brand-implementation.md). |
| `matched_retailer` | Implement and attempt fitting only the assigned matched-retailer estimator using exact physical variants and comparable observations. Preserve separate seller rows and record identity, time, numerical and statistical blockers. Its original assignment required contemporaneous regular-price evidence; the later current-price instruction removes the separate regular-price, promotion and tax gates for the current study. See the [diagnostic guide](../data/chocolate-matched-retailer.md). |

On 3 October 2026, the user instructed the three active chocolate training chats
to pull refreshed Gold and refit, then refined the policy to remove Gold
eligibility requirements and related fields. A later request specifically
required a `lightgbm_without_brand` refit from inferred Gold and admitted every
`gold_*` candidate regardless of saved Silver flags. These instructions preserve
original parents and evidence and require training on actual stored values.

For the matched-retailer task, the user confirmed Gold data as verified and
requested direct training without rebuilding Gold or adding another data layer.
The trainer records that task authorization, considers existing candidates,
selects required model fields and preserves source bytes and flags. Actual
missing values remain explicit; the authorization does not supply missing
variant identities or statistical support.

Publication of completed real-data model artifacts is authorized under
`model/<model-id>/<run-id>/` in the existing
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections),
including each named assignment above. Fixture fits cannot stand in for real
trained models. The published synthetic run uses
`model/lightgbm_without_brand/fixtures/<run-id>/` and retains its synthetic status.
The [model maintenance guide](../model-maintenance.md) owns immutable run storage,
verification and receipts. Analytical contract publication retains its separate
release review requirement, described in the [data intention](../data/intent.md).

## Value for money and brand premium research

Develop category-specific approaches to assessing value for money and brand
premium. Implementation remains deferred pending research into suitable
scientific methods. A price residual alone cannot establish brand premium,
quality or consumer value. Descriptive brand median rankings in the application
measure observed price positioning only.
