# Hedonic Price Benchmark Without Brand implementation

Gold now supplies every candidate without `model_eligible` or `exclusion_reasons`
under the [population contract](../chocolate-gold.md#output-contract). The trainer uses
`counts.training_rows` and applies its declared cohort and actual input checks.
Source price eligibility flags are not required. Historical experiment counts
below describe their original immutable runs; the selected regular-price study
retains its price, quantity, time and review context. Invalid actual inputs produce
readiness blockers rather than a population eligibility exclusion.

Recorded: 3 October 2026. Model ID: `hedonic_without_brand`. Status: implemented
under an explicit local working policy and validated with synthetic inputs;
this historical regular-price experiment has no real-data fit. Its original
training attempt lacked targets and the required analytical handoff.

The assigned session implements one estimator. It preserves the published
`chocolate-pricing-design-3` equal-listing OLS interface as a historical
experimental implementation. The [six-model design](../chocolate-modeling-design.md)
continues to own comparison, champion selection and release requirements.

## Run the assigned estimator

Use the locked development environment and an explicit immutable Gold directory:

```sh
uv sync --locked
python3 -B scripts/fetch_contracts.py --all --offline
uv run python scripts/train_chocolate_model.py \
  --prepare-working-contract data/working-contracts/hedonic_without_brand.json
uv run python scripts/train_chocolate_model.py \
  --model-id hedonic_without_brand \
  --gold-root data/gold/chocolate/uk/gold-4939405fcf8724686f9ee32c \
  --working-contract data/working-contracts/hedonic_without_brand.json \
  --group bar
```

The final command returns status 2 for the inspected real snapshot. Its readiness
run preserves the exact verified Gold and Silver manifests, copied analytical
contracts and price observations. No model is fitted when eligibility is empty.
The default output root is `data/models/chocolate/uk/hedonic_without_brand/`.
An explicit `--output` chooses a different model-specific root.
`--experiment-manifest <run>/experiment.json` requires an identical frozen
experiment, including its data, contracts, assignments and policies.

`--prepare-working-contract` materializes
`chocolate-supermarket-hedonic-working-1` in an ignored local file. The trainer
requires that exact supported version; adding a predictor or changing a policy
requires an explicit implementation/version change. It does not alter dataset
pins or publish contracts. The implementation uses NumPy 2.2.6 and PyArrow 21.0.0.

## Analytical handoff and pending producer migration

The working policy requires an eligible Silver row with reviewed family, exact
variant and stable seller listing identities. Exact variants must have consistent
brand, mass, type, recipe and nut-ingredient values across sellers. The input
cohort must explicitly be `uk-supermarket-single-pack-bars-1`, pack count must be
one, retailer must be Ocado or Waitrose, and type must be dark, milk or white.
Product group `bar` alone cannot establish that population. Tesco and other
seller populations require separate evidence and validation.

Required features are log edible grams, type, `composition.recipe_class`
(`plain`, `inclusion`, `filled`), reviewed nut ingredients (`present`, `absent`,
`unknown`), and retailer. Allergen warnings cannot fill the nut feature. Required
context includes reviewed brand identity, `study.cohort`, and
`quantity.pack_count`; none of these context fields enters the fitted formula.
Names, IDs, observed prices and price-derived fields cannot enter predictors.
The exact regular, non-promotional, tax-inclusive `regular-consumer-price-1`
amount is checked against the copied reviewed price observation and verified
edible mass. There is no fallback or target/quantity imputation.

The published eleven-predictor Gold contract lacks recipe class, exported pack
count and explicit cohort. Optional `composition.cocoa_basis` also requires an
export contract. Pack count already exists in the product catalog; the Gold
predictor handoff does not currently export it. Recipe/cohort/basis declarations
in the working policy describe the required future analytical handoff, not
completed evidence extraction. A supported producer migration must coordinate
the dataset-owned schema/catalog, mappings, validator, selected model design,
Gold export and portable five-contract profile. Existing original and portable
pins remain at `d549ad91d63fb452af605df4a939c4e1f0a59bfa`. The portable package keeps
its independently usable preparation interface; this repository trainer is not
added to that package. The [release review requirement](../../decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
still applies before any analytical contract publication. No contract publication
has occurred in this session.

Optional enrichment uses cocoa percentage with a reviewed whole-product or
chocolate-portion basis, and separate vegan, Fairtrade and organic claim terms.
Claims distinguish `present`, `explicitly_absent` and `unknown`; missing input is
not silently converted to unknown or absence. Cocoa uses an explicit null,
fitting-only median by type/basis with a global fitting median fallback and a
missing indicator. No numerical cocoa value is admitted with an unknown basis.

## Estimation, selection and uncertainty

Every partition and fold recomputes row weights `1 / n_f`. Whole families are
assigned by sorting SHA-256 of UTF-8 `1729:<family_id>`, breaking hash ties by the
family ID. Round `0.2 * number_of_families` half up; the first block is calibration,
the second is final testing, and the remainder is fitting. Persist all assignments.
There are no within-brand quotas. Equal rows and this exact configuration produce
identical assignments; other sessions must compare experiment hashes before
claiming a common sample or split.

Three folds inside fitting use the same ordered families with index modulo three.
Every fold learns its own category vocabularies, family-weighted modal references,
imputation and support. Ocado is the retailer reference when supported. The
core and enriched formulas, with no interactions, retailer by type, retailer by
log mass, or both, are evaluated on complete common supported validation rows.
Candidates without complete validation support are refused. Optional enrichment
is refused when its augmented brand design fails identification; the admissible
policy is saved for later comparison with other sessions. This probe checks rank
and conditioning without fitting another model ID. Required-term aliasing blocks
that configuration.

The estimator minimizes weighted squared log-price error using a square-root
weight transformation and `numpy.linalg.lstsq`. It requires more rows than columns,
full rank and condition number at most `1e12`; it never removes an aliased required
term or substitutes a penalized solution. Constant categorical references remain
recorded without an unidentifiable dummy. The log-size term remains required.
Interactions need at least 5% improvement over the best main-effects candidate
and stable coefficients under 30 family bootstrap draws: at least 80% successful
comparable draws and standard deviation at most one log unit. These are frozen
engineering checks, not established scientific thresholds.

Fit only on the fitting partition after selection. Persist coefficient uncertainty
from 200 whole-family bootstrap draws, refitting preprocessing with the fixed
selected formula and named references. Missing formula levels and rank failures
count as failed draws. Each repeated family draw receives a distinct copy ID and
total weight one. Intervals require at least 20 and 80% successful draws. Bootstrap
coefficient and paired complete-scenario intervals exclude formula-selection
uncertainty and are conditional associations. They are separate from a new-product
prediction interval; marginal endpoints are never subtracted to represent
uncertainty in a retailer price difference.

Fitting-only diagnostics retain the selected estimator's no-retailer ablation and
whole-family brand-held-out results. They do not fit a comparator model ID or
supply unseen-brand calibration. Geometric GBP/100 g predictions use `exp(f(x))`;
pack conversion multiplies by verified edible grams divided by 100. No conditional
median or arithmetic mean claim is attached automatically.

## Calibration, support and evaluation

Within each retailer and calibration family, sort observation IDs and make one
uniform choice with Python `random.Random`, seeded by the integer SHA-256 of the
canonical JSON `[1729, retailer, family_id]`. Select before examining outcomes or
filtering support; apply the same rule to testing. Support is frozen from fitting.

For each retailer, use unweighted absolute log residuals and the
`ceil((n + 1) * 0.90)` order statistic. When it exceeds `n`, record a null quantile
and unavailable/unbounded interval. Save selected IDs and residual records. A
finite quantile alone does not establish release readiness.

Reject unseen retailers/types/categories, unobserved fitted categorical
combinations, inconsistent missingness, invalid quantities and numeric values
outside that retailer's fitting range. Supported but sparse profiles return an
experimental point estimate without an interval when their joint cell has fewer
than nine fitting families. A supplied unseen brand gets an experimental point
with no interval. Calibrated claims concern representative families within the
supported retailer and snapshot population; unseen-brand, unseen-retailer and
future-price claims remain unvalidated.

Evaluation saves every final-test observation with domain membership. Report
family-weighted MAE for GBP/100 g and GBP/pack, weighted median absolute percentage
error, signed bias and listing-weighted sensitivity. Recompute weights inside
retailer and other reported strata. Breakdowns cover retailer, type, recipe, size,
brand, cocoa missingness, and shared versus unique retailer assortments.
Representative-family interval results include coverage, one-sided 95% Wilson
lower bound and median relative width. Unsupported rows remain in denominators.
Baseline-relative gates and champion selection remain pending because this
session does not fit or require comparator models. Final testing cannot change
selection.

## Artifacts and validation

Each immutable `model-run-<digest>/` binds model ID, Gold/logical table/contract
identities, experiment and split hashes, working policy, implementation hashes,
runtime versions and parameters. Fitted runs additionally retain `model.json`,
`selection.json`, `predictions.jsonl`, `evaluation.json`, `calibration.json`,
`support-rules.json`, `uncertainty.json` and `fitting-diagnostics.json`. The model
contains bootstrap refits usable by `scenario_contrast`. `reproduce.txt` records
the exact command. The loader verifies managed hashes and run/experiment/model
identity; identical reruns verify existing artifacts and changed bytes are refused.

Fixture data is explicitly labeled in its Silver quality report and source
manifest. A fixture flag is inherited even if the caller omits `--fixture`.
Fixture fits cannot report `real_data_fitted: true`. Generate numerical evidence
in its own directory:

```sh
PYTHONPATH=scripts uv run python scripts/tests/hedonic_fixture.py \
  --output data/fixtures/hedonic_without_brand --families 600
uv run python scripts/train_chocolate_model.py \
  --model-id hedonic_without_brand --fixture --group bar \
  --gold-root 'data/fixtures/hedonic_without_brand/gold/<returned-gold-version>' \
  --working-contract data/working-contracts/hedonic_without_brand.json
uv run pytest scripts/tests/test_hedonic_without_brand.py
```

The real rebuild read `/Users/coral/repos/rgc/data/collections` and wrote only in
this session's worktree. It preserved 3,743 seller listings and 4,347 captures,
applied 1,285 accepted family assignments without conflicts, and retained 2,134
candidates. All candidates lack reviewed regular-price context, consumer tax
basis, edible quantity, model-predictor reviews, and complete exact variant/family
identity. The eligible view is empty. Silver is
`silver-f651a7faea94ed5a7f003e64`; verified Gold is
`gold-4939405fcf8724686f9ee32c`. No real model, real calibrated interval, release or
Hugging Face model upload is claimed. Authorization to upload trained artifacts
does not supply missing evidence or permit a fixture to be published as a real
trained model.

## Final verification record

The current-value audit was repeated after the user confirmed that all Gold data
was verified and instructed training to proceed. The local model sessions' real
Gold inventories contained the inspected snapshot plus one additional
2,134-candidate snapshot with zero eligible rows. The remote dataset inventory at
immutable revision `d549ad91d63fb452af605df4a939c4e1f0a59bfa` contained no Gold files.
The actual verified Parquet candidates in the selected snapshot have zero positive
regular unit-price targets, zero finite log targets, zero exact variant IDs,
402 resolved family IDs and 631 positive edible-weight values. All 2,134 copied
price observations have unknown tax basis and none has a positive regular pack
amount. The current failure is therefore present in the values as well as the
eligibility flags. The user's verification statement is preserved in
`data/readiness/hedonic_without_brand/gold-availability-20261003.json`; no values
or eligibility decisions were rewritten.

The final real-data attempt is
`data/models/chocolate/uk/hedonic_without_brand/model-run-b8d9ff2c6e93b65b693a3fa0/`.
Its experiment SHA-256 is
`9c4151dc633e986943e3f4a441c586496f67bc7b7769f98ddf793865881596b7`;
Gold manifest SHA-256 is
`cfc10a09c8685e501e6085c523b7726d9cc75ee60b0ab6a0f970a10db5553d4a`;
working policy SHA-256 is
`ccc4c9914cea2263475c58c964c6a9d80fe1c1c6877b2b82f3d4080dd9747e4d`.
All four real copied contract hashes match the current dataset pin. Status is
`readiness_blocked`, with no fitted model and no real calibration or release.

The final numerical fixture run is
`data/models/chocolate/uk/hedonic_without_brand/model-run-89faf11be25b98e1a7761e6a/`,
using synthetic Gold `gold-5a88d8d17c96c113314e6229` and fixture experiment hash
`8844e4498ba64ddfcd880e90769ab25481a6d84b6c1b3b0cdfe7c52225a518bc`.
It retains 1,200 rows in 600 families, split into 360 fitting, 120 calibration and
120 testing families. Fitting-only selection chose enrichment with no retailer
interactions; the matrix has rank 10 of 10 and all 200 bootstrap fits succeeded.
Reloaded immutable parameters reproduce supported predictions and paired scenario
uncertainty after JSON serialization; a regression test covers canonical category
ordering in the joint-support hashes.

| Fixture final-test result | Measured value |
| --- | --- |
| Supported point predictions | 240 / 240 rows, 120 families |
| Family-weighted MAE, GBP/100 g | 0.136074 |
| Family-weighted MAE, GBP/pack | 0.173709 |
| Weighted median absolute percentage error | 3.9724% |
| Signed unit-price bias, GBP/100 g | +0.024077 |
| Signed pack-price bias, GBP/pack | +0.028996 |
| Supported calibration representatives | 93 families per retailer |
| Finite final-test intervals | 99 / 120 representatives per retailer |
| Ocado interval coverage | 88.889%; one-sided Wilson lower bound 82.625% |
| Waitrose interval coverage | 90.909%; one-sided Wilson lower bound 85.007% |
| Median relative interval width | 21.065% Ocado; 21.172% Waitrose |

These are synthetic validation results. They do not establish market accuracy,
release gates, a prediction champion or permission to publish a real fitted
model. In particular, the fixture Ocado coverage lower bound is below the proposed
85% release threshold. Comparator-relative gates remain pending.

`uv sync --locked`, offline verification of all three pinned contract caches,
`uv run pytest` (398 passing cases, including 23 new hedonic cases),
`uv run ruff check .`, `python3 -B scripts/check_documentation.py` and
`git diff --check` passed. This sandbox used
`UV_CACHE_DIR=/private/tmp/rgc-hedonic-uv-cache` for the locked environment because
the default user cache is outside its writable roots. Arrow's CPU-cache probing
reported sandbox permission messages; typed Parquet round trips and all tests
passed. The initial implementation phase performed no merge, push, dataset contract publication or model upload.

## Authorized fixture model publication

After the fixture status was explained, the user explicitly requested publishing
the trained fixture model and committing/merging the implementation into local
`main`. Hugging Face commit
`419150708bbbca16a738ff36a3c0b9373e8cda8e` adds
`model/hedonic_without_brand/model-run-89faf11be25b98e1a7761e6a/`.
All 15 model and metadata files were downloaded and verified against expected
bytes. The [publication receipt](hedonic-without-brand-model-publication.json)
records each SHA-256 and byte length. The [published model directory](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/419150708bbbca16a738ff36a3c0b9373e8cda8e/model/hedonic_without_brand/model-run-89faf11be25b98e1a7761e6a)
labels the fit synthetic, experimental and not release ready.

Publication includes fitted parameters/bootstrap models, preprocessing/support
rules, experiment/splits, selection, predictions, calibration, evaluation and
uncertainty. It excludes source code, environment files, raw/copied analytical
inputs and fixture Gold tables. The original immutable run manifest is retained
as `original-run-manifest.json`; the inference manifest retains the original
run identity and hashes the files present in the published bundle. This narrower
publication followed automatic review rejection of the broader source/runtime/Gold
payload. Existing dataset contents and authoritative analytical contracts were
preserved through a guarded parent commit. No real-data model is claimed.

## Integration with the current-price study

Local main advanced after the original audit and now pins eligible Gold
`gold-8b897101474becaef946922b` and a separate
`current-consumer-price-1` study. The readiness records above refer to their exact
historical regular-price snapshot and audit date. They do not describe all newer
Gold snapshots. The published fixture retains `regular-consumer-price-1` and its
original source identities. The integrated entry point preserves both the new
LightGBM/current-price commands and this explicit historical working policy.
Selecting a different price basis requires its own versioned experiment; this
commit does not claim a new real hedonic fit.

Integration verification: the complete merged suite passed 461 tests. The
subsequent four CLI regression cases cover dispatch to both independent model
IDs using separated and equals-style arguments; all 27 hedonic cases passed.
All four pinned contract caches, Ruff, documentation and whitespace checks
passed. Downloaded published parameters reproduced all 240 supported fixture
predictions through the integrated model loader. The original uploaded run and
its recorded implementation hashes remain immutable historical artifacts.
