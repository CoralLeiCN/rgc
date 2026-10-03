# Independent LightGBM without brand

Gold now supplies every candidate without `model_eligible` or `exclusion_reasons`
under the [population contract](../chocolate-gold.md#output-contract). The trainer uses
`counts.training_rows` and applies its declared cohort and actual input checks.
Source price eligibility flags are not required. Historical experiment counts
below describe their original immutable runs; the selected regular-price study
retains its price, quantity, time and review context. Invalid actual inputs produce
readiness blockers rather than a population eligibility exclusion.

Recorded: 3 October 2026. Model ID: `lightgbm_without_brand`. Implemented and
validated with synthetic fixtures. Its historical regular-price fitting is blocked; release status
is experimental. This session fits only the assigned estimator. The published
`chocolate-pricing-design-3` OLS implementation retains its estimator and contract.

## Entry point and explicit working configuration

The [trainer](../../../scripts/train_chocolate_lightgbm_without_brand.py) accepts verified immutable
Parquet Gold and an explicit local working model configuration. The existing
[entry point](../../../scripts/train_chocolate_model.py) routes
`--model-id lightgbm_without_brand` to it. It requires no comparator artifacts.

```sh
uv sync --locked
python3 -B scripts/fetch_contracts.py --all --offline
uv run python scripts/train_chocolate_model.py \
  --model-id lightgbm_without_brand \
  --gold-root data/gold/chocolate/uk/gold-4939405fcf8724686f9ee32c \
  --working-contract data/working-contracts/lightgbm_without_brand.json \
  --prepare-working-contract
uv run python scripts/train_chocolate_model.py \
  --model-id lightgbm_without_brand \
  --gold-root data/gold/chocolate/uk/gold-4939405fcf8724686f9ee32c \
  --working-contract data/working-contracts/lightgbm_without_brand.json
```

Preparation refuses to replace an existing working configuration. Declare the
evidence-supported aware `price_window.start` and `price_window.end` before a fit.
The default deliberately leaves this window unresolved. Actual reviewed input
rows must fall inside it; a declared window cannot create price evidence.
`--experiment <path>` optionally verifies an exact existing frozen experiment.
`--fixture` explicitly labels synthetic inputs and all fitted artifacts.
The Python API provides batch prediction and verified run loading; a product
scenario CLI or external AI provider is not implemented.

The locked numerical dependencies are NumPy 2.2.6, SciPy 1.16.2, PyArrow 21.0.0
and LightGBM 4.6.0 for the original published fixture. The integrated trainer
uses SciPy 1.15.3 with the shared lock; the other pinned versions are unchanged.
The published bundle retains the original source and lock for exact replay.
Runtime verifies the selected versions. On macOS LightGBM also
requires OpenMP; this session installed Homebrew `libomp` 23.1.2. See the
[versioned installation guide](https://lightgbm.readthedocs.io/en/v4.6.0/Installation-Guide.html).
Native TreeSHAP uses the pinned LightGBM implementation directly, with no separate
SHAP Python package or substituted explanation convention.

## Evidence and shared input boundary

Raw → combined Silver → immutable Parquet Gold remains the training architecture.
Gold verifies all managed hashes, logical row digests, copied contracts, source
provenance, quality counts and eligible table equality before training. The
trainer binds every eligible target to reviewed price observations, including
verified edible weight and `regular-consumer-price-1`. A displayed/member/offer
or reference price and an unknown tax basis cannot replace the regular target.

The local `chocolate-common-input-1-local` policy declares the supermarket single
pack chocolate bar cohort, Waitrose and Ocado, reviewed type and recipe, nut
ingredients, edible weight and explicit optional evidence states. It requires
reviewed brand/family/variant identities for diagnostics, splitting and weighting.
Brand is excluded from the LightGBM feature matrix. Required shared fields absent
from contracts or rows cause readiness failures; seller names do not establish
cohort, pack count or recipe evidence.

Four required fields are absent from the published selected-predictor contract:
`identity.study_cohort`, `quantity.pack_count`, `composition.recipe_class` and
`composition.cocoa_percentage_basis`. Its old required/reject policy and
present/absent encoding also differ from the proposed optional evidence policy.
This implementation does not convert absent to explicitly absent or interpret a
missing field as unknown. Prepared configuration is local and unpublished;
aligned analytical and portable schema/mapping/validator/recipe/design changes
and reviewed regeneration remain prerequisites. Authoritative dataset pins and
portable contracts retain their published versions. Contract publication requires
the separate repository release review.

## Frozen experiment and fitting

The experiment hashes the verified Gold/Silver identities, contract hashes,
selected logical rows, local feature policy, declared cohort/window and exact
family assignments. Sort families by SHA-256 of `seed + LF + family_id`, with
family ID as the tie breaker. Allocate the first rounded 20% to calibration,
the next rounded 20% to final testing, and the remainder to fitting. Rounding
uses `int(n * 0.2 + 0.5)`. Default seed is 1729. Assignment uses no outcomes or
within-brand quotas. Equal identities, rows and configuration reproduce the same
experiment; different snapshots/policies cannot claim a common experiment.

Three fitting-only folds sort families by the hash of `[seed, "fold", family_id]`
and assign successive families modulo three. Every family has total weight one
in each partition, fold and evaluation stratum, with row weight `1/n_f` recomputed
there. Seller rows remain separate. At least ten fitting families are a technical
gate, not evidence of statistical readiness.

Each fold fits its own unordered native category codes, support ranges and
optional cocoa medians by type/basis, with a fitting-wide fallback and missing
indicator. Missing cocoa never implies a recipe. Required weight and price are
never imputed. Known-brand linear rank checks inspect identifiability without
fitting a comparator. Aliased optional fields are omitted; required core aliasing
blocks fitting. Core and enriched candidates must cover every validation row,
so dropping unsupported rows cannot improve the selection score. Categories,
ranges and retailer/type/recipe combinations absent from fitting are rejected.

Bounded search compares the specified start (learning rate 0.03, 15 leaves,
depth 4, minimum 20 rows per leaf, L2 1) with 7 leaves/depth 3/L2 2. Both use
squared log-price error, at most 2,000 iterations and early-stopping patience 50.
Selection uses family-weighted GBP/100 g MAE after exponentiation, aggregated
over inner validation families. The final tree count is the median selected
fold iteration count; refitting uses that fixed count without calibration or
testing feedback. Actual final tree count and per-leaf independent-family
counts are frozen. Sparse leaves retain experimental points and unavailable
intervals. The configurable minimum defaults to five families per leaf.

## Calibration, evaluation and attribution

For each retailer/family, sort observation identities and select uniformly with
a per-group random generator seeded by the hash of `[calibration_seed, retailer,
family_id]`. Default seed is 1729. Selection precedes domain filtering and uses
no prices or residuals. Unsupported selected rows are excluded without replacement.
Apply the same rule to final testing. Retailer 90% conformal quantiles use
unweighted absolute log residuals and rank `ceil((n+1)*0.9)`; an excessive rank
retains an unavailable/unbounded interval. Supported intervals convert to pack
price using verified edible weight. Unrepresented brands receive experimental
points without a new-brand interval. Unseen retailers, including Tesco, are
rejected. Future-price calibration is unvalidated.

Evaluation saves family-weighted unit/pack MAE, weighted median absolute
percentage error, signed unit/pack bias and listing-weighted sensitivity.
Breakdowns cover retailer, type, fixed size bands, brand and cocoa evidence
missingness, with domain/support counts and sparse-stratum flags. Interval metrics
use equal representative-family weights and report coverage, a one-sided 95%
Wilson lower bound and median relative width by retailer. Baseline-relative gates
and champion selection remain pending comparator results. No test outcome changes
parameters or selects a champion.

Native exact TreeSHAP uses the frozen booster/tree count, raw log output,
tree-path dependence and no supplied background. Independently check reference
plus contributions against raw predictions at absolute tolerance `1e-6` and
relative tolerance `1e-5`. Persist signed feature/group values and factors in log
GBP/100 g, the stored-path explanation reference, method/version and reconstruction
status. Sum cocoa/basis/missing contributions before taking magnitudes. Held-out
global and retailer summaries use recomputed family weights. Reconstruction or
explanation failure preserves the point result and returns a deterministic
prediction/support template. AI provider integration remains separate.
The [LightGBM Booster documentation](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.Booster.html)
defines the native contribution interface.

## Runs, proof and remaining work

Runs are immutable under
`data/models/chocolate/uk/lightgbm_without_brand/<run-id>/`. Identity binds model,
Gold/Silver/source/contract/experiment hashes, implementation hashes, exact Python
and package versions, platform, seed, parameters, preprocessing, tree count and
artifact hashes. Runs include copied inputs, local contract, experiment, readiness
report and reproducible JSON CLI arguments. Fitted runs also retain booster,
model, preprocessing, leaf support, tuning/fold weights, calibration, evaluation
and predictions with domain membership. Verified loading checks every managed
file and consistency among model, booster, preprocessing, calibration and identity.
An identical rerun verifies existing bytes; a changed run cannot overwrite them.

The session rebuilt Silver `silver-f651a7faea94ed5a7f003e64` from the saved
checkout, preserving 3,743 listings and 4,347 captures, with no archive/extraction
errors. Source identity is recorded in its manifest. Verified Gold
`gold-4939405fcf8724686f9ee32c` contains 2,134 candidates and zero eligible rows.
The real-data attempt exits 2 with readiness blockers: no eligible observations,
four absent shared contract fields, unresolved source-price window and zero
fitting families. No real fitted booster, calibration, performance result or
release claim exists. Bulk Gold review cannot clear these blockers.

After the user confirmed Gold verification and instructed training, a
[fresh current reload](lightgbm-without-brand-current-gold-audit.json) passed all
integrity checks and found 2,134 null regular unit/log targets, 2,134 unknown tax
bases and zero eligible rows in that exact snapshot. The
[remote inventory](lightgbm-without-brand-remote-availability.json) at immutable
revision `d549ad91d63fb452af605df4a939c4e1f0a59bfa` has no Gold directory. This is a
current input failure, with the human's verification status retained. The session
requested the location of any different verified snapshot, without requesting
confirmation of verification or changing targets/eligibility.

Readiness run `model-run-ffff17f6eca01c6dd1d782dc` binds Gold manifest SHA-256
`cfc10a09c8685e501e6085c523b7726d9cc75ee60b0ab6a0f970a10db5553d4a`
and experiment SHA-256
`d937eb7d9716a85eca0f89aa394686196c15f6c889f4edf490181dbb621b4ddd`.
Synthetic run `model-run-643f7148c9f44c42e5f42212` has 722 trees and 216 final-test
rows in 36 families. Unit/pack MAE is GBP 0.09775/GBP 0.09030, weighted median
percentage error 1.96862%, and all 216 TreeSHAP sums reconstruct within
`5.33e-15` log units. See [full fixture proof](lightgbm-without-brand-fixture-validation.json)
for interval results, bias, listing sensitivity, support and exact hashes.
These results validate synthetic implementation behavior; they do not establish
market accuracy or release readiness.

Meaningful synthetic checks exercise leakage, weight recomputation, native
categories, cocoa missingness, rejected predictors/retailers/ranges, exact TreeSHAP
and fallback, calibration rank boundaries, immutable replay, integrity failures
and excluded-row readiness. Synthetic fits are labeled fixtures and are never
published as real models. The complete check and fixture measurement record is
maintained in [the lifecycle plan](../../lifecycle/plan.md).

Brand-disjoint validation/calibration, no-retailer ablation, feature-rich subset
sensitivity, shared-versus-unique-assortment metrics, complete comparison/champion
selection and product scenario interfaces remain pending. A local working policy
cannot establish that other sessions used matching domains or feature choices.
Actual model artifact upload is authorized under
`model/lightgbm_without_brand/<run-id>/` in `CoralLeiCN/rgc-collections`, with guarded
commits and verified immutable hashes. The current evidence produces no actual
real-data fitted model to upload. Analytical contract publication retains its
separate review requirement.

## Model publication

The user requested model storage under `model/*` in the existing dataset.
The [synthetic fixture bundle](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/bb1c9de580c64cc13aac62b352d58704fe2dd60e/model/lightgbm_without_brand/fixtures/model-run-643f7148c9f44c42e5f42212) is committed at
`bb1c9de580c64cc13aac62b352d58704fe2dd60e`, preserving all 99 existing dataset files, including
the refreshed Gold added by another session. Its 53 published files include
the model directory README and 52 immutable bundle files: the frozen run,
generated fixture Gold, exact source, locked dependencies, portable replay
command and SHA-256 inventory. The [publication receipt](lightgbm-without-brand-model-publication.json)
records every remotely verified file. All remote bytes match staging.

The portable replay reproduced the same run identity and all 23 managed
artifacts apart from the historical local reproduction command. This is
synthetic implementation evidence; `real_data_fitted` and `release_ready`
remain false. Copies of contracts in the bundle retain their original status.
Automatic approval review rejected the initial combined payload because it
included real Gold readiness inputs without specific payload authorization.
The successful publication contains only the synthetic fixture bundle;
real readiness inputs remain local.

The publication parent `95c5fbd0ab5fa9a41fa5333648321d95f16927a7` includes newer Gold
from another session. Earlier readiness audits describe this session's pinned
regular-price snapshot. They do not assess that newer snapshot or establish
that a current-price model has been fitted by this trainer.

## Web scenario demo

The user subsequently authorized using this published synthetic fixture in the
web product form. [The serving guide](web-fixture-pricing.md) defines the
immutable reference and restricted single bar pack interface. Node evaluates
the original booster and computes exact stored-path SHAP, verified against
native LightGBM 4.6.0 for every field across 324 supported input combinations.
It labels estimates as synthetic, retains `regular-consumer-price-1`, and shows
signed price allocations and excluded traits. No real training, current-price
migration or market-release claim follows from this UI integration.

## Current inferred Gold refit

The initial inferred refit implemented the user's all-row instruction through
`chocolate-gold-training-all-rows-1`. Historical audits above retain their exact
source snapshot status. The published refit records original eligibility flags
and reasons as provenance. Main integration follows the population policy below.

An inferred bundle supplied to the normal without-brand command without a
historical working contract routes to the current displayed-price refit. The
[refit record](lightgbm-without-brand-inferred-refit.md) owns its actual fit,
reproduction command, restricted observed domain, 80/20 family split, missing
feature policy and small-sample limitations. It has a distinct immutable run
format and verified loader. It does not establish common-experiment comparator
results or replace the published web fixture.

The inferred refit was subsequently [published](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/88b08aeada37e228fcd80334b5abddd768da6968/model/lightgbm_without_brand/model-run-9f56df660a6d46e7cc720002)
at immutable commit `88b08aeada37e228fcd80334b5abddd768da6968` after the user's explicit
request. The [receipt](lightgbm-without-brand-inferred-model-publication.json)
records 16 verified model/metadata files and preserved existing dataset objects.
Downloaded predictions match all 15 saved holdout results. The actual fit
remains experimental, uncalibrated and not release ready.

## Main integration and population policy

The published inferred refit retains its original policy and immutable artifact
identity. Integration with main updates the inferred adapter to
`chocolate-gold-training-all-rows-2`: runtime rows omit selection fields and
carry historical source decisions only as provenance. Conventional trainers
use main`s canonical `verified_gold` population loader. The inferred version
1 wrapper verifies its original child with `verified_gold_storage`. The
published model remains readable by its verified loader; future fits record
the updated implementation hashes and a new run identity.
