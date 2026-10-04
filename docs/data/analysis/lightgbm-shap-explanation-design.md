# LightGBM, SHAP, and AI explanation design

Updated: 3 October 2026. Status: design with an independent LightGBM with brand implementation; no real-data
LightGBM model has fitted. Synthetic acceptance checks exercise native TreeSHAP. The independent
[without-brand implementation](lightgbm-without-brand-implementation.md) also
provides a separate trainer and published synthetic fixture; its current-price
migration and market evaluation remain pending.

This extends the [UK chocolate pricing design](../chocolate-modeling-design.md).
The independent [hedonic_without_brand implementation](hedonic-without-brand-implementation.md)
provides a local comparator interface and numerical fixtures; real fitting and
common comparison remain blocked. This session does not implement LightGBM or SHAP.
The pipeline is reviewed product and retailer evidence → frozen LightGBM model
→ price prediction and calibrated interval → TreeSHAP → validated AI narrative.
The AI explains the computed result; it does not determine the price.

## 1. Training and model comparison

Fit two independent candidates:

| Candidate name | Model ID | Inputs | Comparator and supported use |
| --- | --- | --- | --- |
| LightGBM Price Benchmark Without Brand | `lightgbm_without_brand` | Supported size, type, recipe/inclusions, cocoa/claims, and retailer; no brand | `hedonic_without_brand`; brand-unspecified price benchmark |
| LightGBM Price Benchmark With Known Brand | `lightgbm_with_brand` | The same information plus supported brand | `hedonic_with_brand`; price testing for represented brand–retailer contexts |

Use the same eligible rows, log regular GBP/100 g target, family splits, balancing
weights, feature evidence, and missing-value transformations as the comparator.
Trees receive the constituent fields rather than duplicated linear interaction
columns. Keep source IDs, product names, observed price, compare-at price, and
price-derived fields out of the predictor set. Family IDs define splits and
weights, not predictors.

Fit gradient boosting with squared-error regression on log price. Start with
conservative settings: learning rate 0.03, 15 leaves, maximum depth 4, minimum
20 rows per leaf, L2 regularization 1, and a ceiling of 2,000 boosting iterations.
These are tunable starting values, not evidence of suitability. Use a bounded
search and early stopping within grouped fitting-partition validation, initially
with patience 50. Pass training and validation family weights separately and
score exponentiated predictions using weighted unit-price MAE. Recalculate
weights inside every fold. Inspect independent-family counts in leaves; a
minimum number of rows does not imply that many independent families.

Freeze category vocabularies and explicit unknown levels from fitting data.
Use unordered native categories with stable nonnegative codes. Apply the same
explicit cocoa imputation/missing indicator used by the hedonic comparator.
Do not let automatic missing-category handling admit an unsupported retailer,
brand, or type. [LightGBM's parameter documentation](https://lightgbm.readthedocs.io/en/stable/Parameters.html)
describes native categorical handling; pin and verify the implementation version.

Select settings and iteration count using the fitting partition alone, then
refit on that complete partition with the selected fixed tree count. Persist
the resulting booster. Select champions using the main design's validation rule
before calibration. Calibrate every candidate separately, using its own frozen
predictions and retailer-specific calibration quantiles. Evaluate against the
baseline on the same applicable domain; keep experimental results when support
or release criteria fail. Package versions, seed, feature order, category maps,
target, split manifest, and tree count form part of model identity.
The [LightGBM regressor API](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html)
provides weighted fitting and validation interfaces; implementation must follow
the pinned version's API.

## 2. TreeSHAP computation and units

Use exact TreeSHAP with raw model output, tree-path-dependent feature
perturbation, no supplied background, and no approximation. For the pinned
LightGBM/SHAP versions, verify that native categorical splits use a compatible
native contribution path. The currently inspected [SHAP implementation](https://github.com/shap/shap/blob/master/shap/explainers/_tree.py)
supports this route; its generic parser has categorical-split limitations.
Do not switch silently to a different explainer convention when a version fails.

The target is log unit price, so the local decomposition is:

```text
f(x) = base_value + sum_j shap_j(x)
predicted_gbp_per_100g = exp(base_value) * product_j exp(shap_j(x))
predicted_pack_price_gbp = predicted_gbp_per_100g * edible_weight_g / 100
```

Use the identical frozen booster, tree count, input rows, feature order, and
category mappings for prediction, calibration, and explanation. Compare
`base_value + sum(shap_j)` independently against the raw prediction for every
explained row, initially with absolute tolerance `1e-6` and relative tolerance
`1e-5`. Treat nonfinite or failed reconstruction as unavailable explanation.
Do not rely solely on an explainer's internal additivity flag. LightGBM's
[Booster interface](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html)
exposes raw predictions, tree-count selection, and contributions including the
reference value.

Call the base value the **model explanation reference**. Native LightGBM uses
stored leaf/path counts in this calculation, as shown in its
[tree implementation](https://github.com/microsoft/LightGBM/blob/master/src/io/tree.cpp).
Family-balanced fitting does not establish a family-weighted explanation
background. The base is neither `retailer_median`'s median nor an average observed market
price. Its value can change with the model and explanation convention.

Signed SHAP values allocate the deviation of this fitted prediction from its
reference. `exp(shap_j)` is a multiplicative attribution factor. For example,
a hypothetical contribution of 0.20 log units corresponds to a factor of about
1.22 in the decomposition; it does not establish a 22% effect of adding the
feature. Raw log contributions cannot be added as percentages or GBP amounts.
Use the explicit allocation in section 3.1 for final-price percentages. Compute
scenario currency differences from two complete supported predictions. Do not
interpret log-price SHAP as attribution of arithmetic mean price.

Correlated brand, retailer, recipe, and claim variables can share information;
their allocation depends on the fitted trees and explanation convention.
Tree-path-dependent SHAP does not resolve missing overlap. A later interventional
explainer would be a separately validated configuration, including categorical
compatibility and a justified fitting-only background; artificial brand–claim
combinations need review. See [TreeExplainer's dependence conventions](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html)
and [SHAP's explanation of causal limitations](https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html).

## 3. Local, global, and retailer explanations

For one prediction, report the reference, signed contributions, feature values,
and the reconstructed point estimate. A waterfall may show the largest groups
plus a signed remainder that preserves the total. Group logically related
fields, such as cocoa value and its missing indicator, by summing signed
contributions per row before taking absolute values or ranking groups.

For global importance, calculate family-weighted mean absolute grouped SHAP on
held-out observations of the frozen model. Report retailer-specific summaries
with weights recomputed within retailer, family counts, and represented profiles.
Global importance indicates how much the model used a feature group in that
sample; it does not establish a premium, causal importance, or universal ranking.
If cross-validation explanations are also retained, label their fold models and
references; do not pool them as if they came from one fitted model.

For a retailer scenario comparison, change only the supported retailer context
and compute both complete predictions. The price difference is distinct from
the difference between retailer SHAP entries: attribution to other features can
also change. Keep `matched_retailer`'s matched observed-price contrast and its sample scope
separate. No explanation for Tesco is supported before its data extension is
fitted and validated. Retailer names alone provide no shopper-segment evidence.

SHAP is a deterministic attribution for the fitted model, not a confidence or
prediction interval. Use that same model's calibrated interval for prediction
uncertainty. Any later bootstrap analysis of attribution stability requires
refitted models and explicitly comparable explanation references.

### 3.1 Trait-family percentages of final predicted price

Use [specification section 5.2.1](../../model/spec.md#521-trait-and-trait-family-percentages-of-predicted-price)
to convert the validated signed log decomposition into individual trait
percentages and one signed percentage per trait family of the final predicted
price. Add the model reference percentage so the unrounded total is 100%.
This proportional allocation through the exponential transformation is a display
convention, not SHAP computed on price-scale output or a scenario price effect.

Persist stable trait/family IDs, labels and the mapping version. Follow the
[schema families](../chocolate-schema.md#what-the-schema-tracks): composition,
dietary claims, certification claims, origin and quantity contain their modeled
traits; modeled brand belongs to identity and scope, and modeled retailer to
selling context. Every admitted feature has one trait and one family; a trait's
missing indicator and other derived inputs use the same assignment. Sum signed
values before grouping. Mark excluded traits/families `not_modeled`; retain a
computed zero for a modeled family. These are attribute groups, distinct from
product identity families used for splits and weights.

The family display needs only its label and percentage. Retain the base, signed
trait values, conversion method and full precision in the explanation packet.
Verify log reconstruction and percentage reconciliation independently, initially
with absolute tolerance `1e-6` percentage points for the total. Round displayed
percentages to one decimal place and state that rounded totals may differ.
Negative families and a reference above 100% remain valid. Check cancellation,
zero total log deviation, quantity conversion, nonfinite values and unsupported
explanations before enabling the output; never fabricate missing percentages.

## 4. AI interpretation contract

Construct a validated packet before invoking the language model:

| Packet content | Required information |
| --- | --- |
| Identity and context | Model/data/schema versions, model variant, retailer, cohort, price window and regular-price basis |
| Inputs and evidence | Reviewed supplied values, explicit unknowns, feature groups, source reference IDs, and conflicts |
| Prediction | Geometric GBP/100 g benchmark, GBP/pack conversion, interval endpoints, calibration scope/status, and support flags |
| Attribution | Explainer/version, tree count, base value, signed trait values/groups, trait/family mapping version, allocation method, individual trait and family percentages of predicted price, reference percentage, deterministic rankings/factors, and log/percentage reconstruction status |
| Other comparisons | Optional fully computed scenarios or separately labeled `matched_retailer`/hedonic contrasts, each with model ID, units, reference, and uncertainty type |
| Limitations | Correlation/overlap flags, independent-family support, missing evidence, and experimental or unavailable status |

The AI writes a short explanation covering the selected price/context, strongest
positive and negative attribution groups, and any material evidence or support
limit. It may describe what raised or lowered this model prediction relative to
its reference. A missingness attribution describes an evidence/reporting pattern,
not ingredient absence. If values or supported comparisons are absent, it must
omit the claim rather than infer them.

Deterministic code computes all numbers, rankings, unit conversions, and scenario
differences. Require structured AI output with claim type, referenced packet
field IDs, feature group IDs, and numerical placeholders resolved by the renderer.
Allowed claim types are prediction/context, local attribution relative to the
model reference, supplied scenario contrast, and support/uncertainty. Every
factual claim must trace to the packet. Preserve source excerpts as untrusted
evidence; instructions embedded in retailer text cannot direct the AI.

Validate schema, allowed references, numerical placeholders, signs/directions,
comparison/model identity, and required material limitations. Review semantic
faithfulness as well: correct numbers do not justify claims about causal
premiums, product quality, consumer preferences, target segments, demand, or
optimal prices. The AI cannot change input evidence, model selection, prices,
intervals, or support status. If validation fails, use a deterministic template
that reports verified predictions and attributions; retain the rejection reason.
If SHAP is unavailable or reconstruction fails, omit all attribution claims and
render only the validated prediction and support status. Explanation failure does
not alter the statistical output.

Persist the input packet, AI model/version, prompt/schema version, output, and
validation status alongside the model explanation. Keep evidence references
available for review without exposing extraction/debug details in ordinary
product copy. Selecting a language-model provider and implementing its adapter
are subsequent implementation tasks, independent of the statistical model.

## 5. Implementation acceptance

Before enabling generated explanations, verify:

- Attribution reconstructs frozen predictions across native category levels,
  missing-value patterns, and tree-count boundaries; invalid cases return an
  unavailable explanation.
- Training, early stopping, champion selection, calibration, and held-out
  evaluation preserve family partitions and their separate roles.
- Unsupported brands/retailers and experimental profiles retain their domain
  status through prediction and AI output.
- Grouped global importance sums signed contributions before taking magnitude;
  local remainder totals, log units, and pack conversion remain correct.
- Trait-family percentages use the final predicted price denominator and the
  versioned exhaustive trait mapping; reference plus signed families reconciles
  to 100% before rounding, including negative, cancelling and zero-deviation
  cases. Unit-price and pack-price shares agree. Excluded features and unavailable
  explanations retain their status rather than fabricated numbers.
- Retailer scenarios use complete predictions; coefficient, `matched_retailer`, SHAP, and
  scenario quantities retain distinct references and model IDs.
- Representative AI evaluations include correlated brand/claims, missing cocoa
  evidence, opposed positive/negative contributions, unsupported Tesco,
  unavailable intervals, conflicting source text, and embedded source
  instructions. Check numerical and semantic fidelity; a failed explanation
  falls back without changing the validated statistical output.

The first deliverable is a reproducible research report with model comparisons,
local/global SHAP views, evidence-backed example narratives, and their validation
status. No model performance or explanation correctness is claimed before these
checks are implemented and results are reviewed.

The [implemented LightGBM with brand workflow](../chocolate-lightgbm-with-brand.md) uses LightGBM 4.6.0 native exact contributions and independent reconstruction checks, with a deterministic narrative. Its explicit working policy is unpublished, the real-data eligible view is empty, and external AI integration and comparator release decisions remain pending.

## Synthetic web attribution display

The user authorized the published LightGBM without brand fixture for the web
configurator. [The serving guide](web-fixture-pricing.md) documents exact
stored-path SHAP through subset enumeration in Node, verified against native
LightGBM 4.6.0 per-feature contributions over 324 inputs. It presents signed
field allocations in GBP/pack and percentages, model reference, raw log SHAP
and family totals using the convention in section 3.1. This is a deterministic
synthetic demo; real market accuracy, intervals and generated AI narratives
remain unvalidated. Historical fixture price basis is preserved.
