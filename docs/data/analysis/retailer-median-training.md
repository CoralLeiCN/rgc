# Retailer Median Price Baseline implementation and readiness

Recorded: 3 October 2026. Model ID: `retailer_median`. Implementation and
synthetic validation are complete. The original real-data attempt reached verified Gold
and saved immutable readiness artifacts with zero eligible observations. No real
model has fitted, no interval has calibrated, and no model has been uploaded.

Every Gold row belongs to the training population. The loader removes
`model_eligible` and `exclusion_reasons` from model inputs and ignores source
price eligibility flags. Reports and experiments record
`population_selection: all_gold_rows`; reports use `counts.training_rows`.
Actual target, quantity, identity and declared cohort requirements determine
readiness. The run records below describe their historical implementations.

## Estimator and frozen experiment

`scripts/train_chocolate_retailer_median.py` runs independently.
`scripts/chocolate_retailer_median.py` learns the lower family-weighted median
regular GBP/100 g by retailer and reviewed chocolate type. Each fitting family
has total weight one; retain each row's `1 / n_f` weight inside median groups.
An exact half-mass tie selects the lower observed value. Preserve separate seller
rows. Edible weight converts unit price to pack price; no size effect is fitted.
Brand, recipe, cocoa and claims do not condition this baseline.

Learn a retailer-wide median for fallback where a retailer/type cell is absent
but that type exists elsewhere in fitting. Flag every fallback. Reject unseen
retailers or globally unseen types, invalid weights, weights outside the
retailer's fitting range, unresolved population context and non-single packs.
Brand is context only. New/omitted brands receive an experimental benchmark with
no calibrated new-brand claim. Sparse strata remain experimental; median
differences may reflect assortment.

`scripts/chocolate_experiment.py` ranks families by SHA-256 of
`json_bytes([1729, family_id])`, then family ID. Serialization is finite UTF-8
JSON with sorted keys, two-space indentation and a trailing LF. For `N >= 3`,
fitting gets `clamp(floor(0.6*N + 0.5), 1, N-2)` families, calibration gets
`clamp(floor(0.2*N + 0.5), 1, N-fitting-1)`, and final testing gets the remainder.
The algorithm ID is `sha256_json_seed_family_rank_round_60_20_remainder_v1`.
Persist exact assignments and observations. There are no brand quotas or outcome
choices. Equal families/configuration reproduce equal splits across row order.

There is no tuning or learned feature preprocessing. Score calibration and final
testing separately; neither selects parameters. The four-regression conformal
contract does not require baseline intervals. Reports recompute family weights
within supported partitions and retailer/type/size/brand strata. They include
unit/pack MAE, weighted median absolute percentage error, signed unit/pack bias,
listing-weighted sensitivity, support denominators and fallback counts. Size
bins are at most 50 g, over 50 through 100 g, and over 100 g. Required fields are
complete by eligibility; optional evidence missingness is explicitly unavailable
in this input contract.

The hashed common feature policy records the proposed regression core, optional
features, missingness, excluded identifiers/names/prices, and fitting-only
known-brand identification. Shared regression feature evidence/identification,
the common applicable-row comparison, comparator results, baseline-relative
gates and champion selection remain explicit comparison readiness blockers.
Check complete experiment identities before comparison with another session;
different domains or algorithms require disclosure.

## Working contract and commands

Published `chocolate-pricing-design-3` at
`d549ad91d63fb452af605df4a939c4e1f0a59bfa` authorizes experimental OLS. The new
trainer rejects attempts to relabel it. Prepare an unpublished working design:

```sh
uv run python scripts/prepare_chocolate_retailer_contract.py \
  --output data/working-contracts/chocolate/retailer-median-1
uv run python scripts/build_chocolate_silver.py \
  --archive-root /Users/coral/repos/rgc/data/collections \
  --output data/silver/chocolate/uk/retailer-median-working-rebuild \
  --schema-root data/working-contracts/chocolate/retailer-median-1 --offline
uv run python scripts/build_chocolate_gold.py \
  --silver-root data/silver/chocolate/uk/retailer-median-working-rebuild \
  --output data/gold/chocolate/uk
uv run python scripts/train_chocolate_retailer_median.py \
  --gold-root data/gold/chocolate/uk/gold-56817976905f24210105f069
```

The preparer preserves profile, mappings and validator bytes, creates
`chocolate-retailer-median-design-1`, and records source/working hashes. It retains
`regular-consumer-price-1`. Required reviewed context adds
`identity.boundary_status: in_scope` and `quantity.pack_count: 1` alongside brand,
seller role, group, retailer, type, mass, and family/physical IDs. Scope review
under this design must establish standard single-pack eating bars and exclude
gifts, novelty, assortments, non-chocolate foods and other excluded forms. Only
Waitrose and Ocado are accepted. Old OLS scope review cannot authorize this cohort.

The real command returned 2 and saved readiness artifacts. Once evidence is
reviewed, supply explicit inclusive timezone-aware `--window-start` and
`--window-end` price-observation bounds. Ingestion timestamps cannot supply the
window. The default output is `data/models/chocolate/uk/retailer_median/<run-id>/`.
Integrity errors return 1; successful fitting returns 0 with experimental status.
`--fixture` labels synthetic validation. Detected fixture provenance cannot be
reported as real training when the flag is omitted.

The loader verifies Gold managed bytes, logical row digests, copied contracts,
Silver provenance and the complete Gold population. The trainer checks targets against reviewed
regular-price observations and edible weights, and rechecks input/implementation
before writing. Immutable runs bind model/data/contract/experiment identities,
environment/implementation hashes, seeds, parameters, assignments, copied inputs,
medians, support rules, uncertainty, evaluation, prediction domain membership and
CLI arguments. Identical replays verify bytes; altered runs are refused.

The portable package retains its published prepare-only schema, mappings,
validator, recipe and selected model design, independently usable. This repository
extension has not changed those interfaces. A later common comparison release
must align affected contracts/guides and undergo the separate
[release review](../../decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
before immutable contract publication and pin updates. No contracts were
published here. The authorized model upload requires an actual real fit; fixture
fits remain local.

## Inputs, results and proof

The parent checkout had no data directory. The saved checkout had raw data and
published caches but no Gold. All outputs were written in this session's worktree.

| Input/artifact | Identity/status |
| --- | --- |
| Raw | `raw-snapshot-70239771976a75a48c5d99db`; 3,743 seller listings, 4,347 captures |
| Published-contract Silver | `silver-f651a7faea94ed5a7f003e64`; 2,134 candidates, zero eligible |
| Published-contract Gold | `gold-4939405fcf8724686f9ee32c`; old OLS design rejected by baseline trainer |
| Working-contract Silver | `silver-485af2f8e7fae127cd73578b`; 2,134 candidates, zero eligible |
| Working-contract Gold | `gold-56817976905f24210105f069`; loadable, eligibility preserved |
| Gold manifest SHA-256 | `362a3273f61b5c73de96d27562f232052340c32e33cb984e406c62eda367e277` |
| Working design SHA-256 | `ed403304c28b88655f77e0f48f3d4fe745bb22618b965e7ba71de987d7fe325c` |
| Policy SHA-256 | `735bd3c36f3654a22bce581bd71148330c5ff72f553d9d749aaa958fe8c4853d` |
| Feature policy SHA-256 | `0bd653f9b67e55806277cea718c49955aaf35c9b52a593a21c69dfbc78db2fc6` |
| Readiness experiment SHA-256 | `603fb8dfc0d6e4de87b96e33e9a3c86b5ee1d17b014009e011ef81c93e502c43` |
| Real readiness run | `retailer-median-149182b8694b50266cdc217c`; not fitted/calibrated/release-ready |
| Synthetic Gold | `gold-0d50a3c556b4905c4e6fdfa0`; 100 rows, 50 synthetic families |
| Fixture run | `retailer-median-642d5f0deb303a5a29f00316`; 30 fitting / 10 calibration / 10 final-test families |

Both rebuilds completed without archive/extraction errors. All 2,134 candidates
have unresolved regular price/tax, quantity review, population/predictor review,
and family/physical identity review. Another 1,157 lack verified time/availability.
Thirty-nine observed pack counts fall outside the single-pack domain. Exclusion
counts overlap and are retained in readiness artifacts. No candidate was
promoted, no target manufactured, and original evidence/earlier snapshots remain
preserved. Gold bulk review cannot bypass eligibility.

The real run has no selected rows, usable split or metrics. Blockers: zero
reviewed eligible observations, an undeclared reviewed price window, and fewer
than three reviewed families in that window.

The fixture final test supports all 20 rows in 10 synthetic families, with 10
rows/families per retailer. Family-weighted unit MAE is £0.40/100 g; pack MAE
£0.32; median absolute percentage error 20%; unit bias −£0.16/100 g; pack bias
−£0.14. Listing-weighted results coincide because seller counts per family are
equal. Calibration-partition unit/pack MAE is £0.44/100 g and £0.35, with median
absolute percentage error 29.63%. These validate artifact/metric behavior, not
market performance or release. Fallback has a separate fixture test. No intervals
were calibrated.

Checks: `uv sync --locked`, offline verification of all three published caches,
`uv run pytest` (399 passed, including 24 baseline cases), `uv run ruff check .`,
`python3 -B scripts/check_documentation.py`, and `git diff --check`. A writable
`UV_CACHE_DIR` was needed in the sandbox. CI and remote publication have not run.

## Training retry after the user's Gold verification

The user subsequently confirmed that all Gold data were verified and requested
training. That verification was accepted. A new inventory checked the saved and
parent checkouts, the available Gold directories across local model worktrees,
and the current Hugging Face dataset. Remote main still resolved to immutable
commit `d549ad91d63fb452af605df4a939c4e1f0a59bfa`; its complete 92-entry recursive
tree contained Silver and contracts, with no Gold directory or Parquet file.

Both real local snapshots were loaded again through `verified_gold`, and the
trainer was rerun against each. Managed bytes, logical digests and provenance
passed. Current decoded contents of each snapshot have 2,134 candidates, all
`model_eligible: false`, zero eligible Parquet rows, zero non-null regular unit
targets, zero auxiliary regular prices and zero tax-inclusive price observations.
There are 402 non-null family IDs. These are current file observations, separate
from the user's confirmed verification status.

Working snapshot `gold-56817976905f24210105f069` again returned the immutable
readiness run `retailer-median-149182b8694b50266cdc217c`. The actual failed
requirements were an empty eligible view, no declared price window, and fewer
than three selected families. The published-design snapshot also failed the
working baseline contract check. No eligibility flags or missing values were
rewritten. No fitted model or new market metrics resulted.

`data/current-gold-verification-audit.json` records the confirmation, check time,
complete remote inventory, current table counts/digests, manifest/contract hashes,
and the new training attempts. The available files do not contain trainable
regular-price targets. The location of any different verified Gold snapshot is
required to continue fitting and the authorized upload.

## Refit using explicitly authorized Gold eligibility

The user supplied `gold-8b897101474becaef946922b` from the `bb33` worktree and
authorized all entities as model eligible. The exact snapshot was copied into
this worktree, without rebuilding from Silver. Its manifest SHA-256 is
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Parent Gold is `gold-56817976905f24210105f069`; source Silver is
`silver-485af2f8e7fae127cd73578b`. Rule: `chocolate-gold-bulk-eligibility-1`.
`eligibility_provenance` records the user instruction and
`evidence_validation_performed: false`. The complete parent remains embedded
under `inputs/parent-gold/`.

The historical `chocolate_gold_eligibility.py` loader verified parent integrity,
unchanged analytical fields, exact promoted flags, complete managed inventory,
logical row digests and provenance. Both Parquet views now have all 2,134 rows
with `model_eligible: true` and `exclusion_reasons: []`. The trainer accepts that
eligibility. Under the verified override, original auxiliary Silver price
eligibility flags do not veto the Gold decision; target, tax, quantity and price
evidence checks remain enforced. Source auxiliary files are preserved exactly.

The trainer writes missing-value counts and readiness artifacts for actual
input failures, including the exact Gold manifest and original inputs.
Historical artifacts retain their recorded eligibility provenance; current
modeling inputs omit selection fields and reports identify the full population. A missing-input failure no longer exits
before saving that report. Run:

```sh
uv run python scripts/train_chocolate_retailer_median.py \
  --gold-root data/gold/chocolate/uk/gold-8b897101474becaef946922b
```

Fresh attempt `retailer-median-07a021020a85a1f4dfcc6b64` returned status 2 with
2,134 eligible rows and zero fitted rows. Its report is under
`data/models/chocolate/uk/retailer_median/retailer-median-07a021020a85a1f4dfcc6b64/`.
Old Silver eligibility and exclusion reasons are not blockers.

| Stored required input | Null rows out of 2,134 |
| --- | --- |
| Regular GBP/100 g target and log target | 2,134 each |
| Variant ID | 2,134 |
| Family ID | 1,732 |
| Population boundary | 2,134 |
| Edible weight | 1,503 |
| Pack count | 2,093 |
| Chocolate type | 1,289 |
| Brand | 997 |
| Product group | 415 |

Listing/observation IDs, retailer and seller role are non-null. The blockers are
`required_model_inputs_missing`, an undeclared explicit price window, and fewer
than three usable families in that window. A weighted price median cannot be
fitted without observed target values. Missing targets and identities were
preserved. No real fit, metrics, calibrated intervals or model upload resulted.

Loader tests verify full-parent preservation and reject altered analytical
values, flags, order and reports even after table rehashing. Trainer tests verify
that promoted rows count as eligible, missing inputs save a report, provenance is
bound, and ignoring auxiliary eligibility cannot admit unknown tax. The locked
environment and published caches passed verification. All 409 pytest cases
passed, including 8 loader and 26 baseline cases. Ruff, documentation and
whitespace checks passed. All 17 fresh run artifacts matched their hashes and
byte lengths, and an identical replay verified the immutable run.


## Refit with the published current-price target

The user superseded the regular-price requirement and requested a refit using
collected current displayed prices. The published target contract set
`contracts/chocolate-current-price/` is pinned at immutable Hugging Face dataset
revision `d743cb8dbca37f5241cccd444a16165523304f6c`. The Git reference is
`schemas/chocolate/current-price/dataset-contract.json`; published design
`chocolate-pricing-current-price-design-1` has SHA-256
`c7b7f55d0424f8bdbef2fbc76e7b75475753eaad8021f7e1acd266de284ac8de`.
All four contract bytes and their pin are verified and retained in run artifacts.

The trainer applies the exact published target to its own selected predictors in
`chocolate-retailer-median-design-1-current-price-1`. Policy:
`current-consumer-price-1`, `price_basis: current_displayed`,
`promotion_basis: as_displayed`, `tax_basis: as_displayed`, reject fallback.
The shared `chocolate_current_price.py` preparation requires positive displayed
GBP pack price and matching positive edible weights in the predictor and price
observation. Its local import adapter uses the baseline target registry; its
preparation and provenance arithmetic match the supplied shared helper.

Separately verified regular amounts, promotion classification, confirmed tax,
price review status and availability do not veto the proxy. Original inputs,
Parquet files, evidence, eligibility and parent snapshots are preserved. Derived
modeling rows have explicit `current_price_per_100g_gbp` and
`log_current_price_per_100g_gbp` fields. Equal `regular_*` compatibility aliases
mean current-price proxies in that derived view. They make no independently
verified regular-price claim. No regular/reference fallback or mass imputation
is permitted.

The default current-price sample covers every observation in the immutable
snapshot. Optional `--window-start` and `--window-end` UTC bounds filter recorded
source observation times. Every Gold row receives an input readiness audit;
complete rows can form a model sample even when other rows are missing
inputs. Variant/family consistency, population, one observation per seller
listing, the family split, weights and support rules still apply. Price, tax,
promotion and review context remain recorded as limitations. Original snapshot
bytes remain preserved; the modeling view has no eligibility columns.

Run the exact refit with:

```sh
uv run python scripts/train_chocolate_retailer_median.py \
  --gold-root data/gold/chocolate/uk/gold-8b897101474becaef946922b \
  --current-price-proxy
```

Real attempt `retailer-median-385414893ddde39bcfb27060` produced 28 immutable
managed artifacts under
`data/models/chocolate/uk/retailer_median/retailer-median-385414893ddde39bcfb27060/`.
Gold manifest SHA-256 remains
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
It accepted all 2,134 eligible rows and found 630 normalized current targets.
Preparation reports 1,503 missing edible weights and one missing current price;
these account for 1,504 null unit/log targets. The actual missing context is:

| Required input | Null rows out of 2,134 |
| --- | --- |
| Variant ID | 2,134 |
| Population boundary | 2,134 |
| Family ID | 1,732 |
| Edible weight | 1,503 |
| Pack count | 2,093 |
| Chocolate type | 1,289 |
| Brand | 997 |
| Product group | 415 |

Listing ID, observation ID, retailer and seller role are non-null. No row has
all required inputs. The only readiness blockers are
`no_complete_current_price_model_inputs` and
`fewer_than_three_usable_families_in_selected_sample`. Missing regular prices,
promotion/tax review, and absence of explicit window bounds are not blockers.
No real model, market error metrics, calibrated intervals or upload resulted.

Current artifacts include the exact original inputs and Gold manifest,
all four published target contracts and pin, working model design, target
policy, target preparation, the complete derived Gold population and selected
rows, per-row readiness, missing-value counts, source price context, unavailable
experiment, exact command and report. Their hashes and byte lengths are bound
by the immutable run manifest. Historical regular-price mode remains available
for reproducing its earlier contracts.

Synthetic current-price fit `retailer-median-6d261c66b3340160dc8efb92` has 100
observations in 50 families, split into 30 fitting, 10 calibration and 10 final
families. It deliberately uses unreviewed promotional observations with unknown
tax, absent regular price, false auxiliary Silver price eligibility and unknown
availability. Final testing covers 20 observations with 100% support; family
weighted MAE is GBP 0.40/100 g and GBP 0.32/pack, MdAPE 20%, signed biases
GBP -0.16/100 g and GBP -0.14/pack. Calibration MAE is GBP 0.44/100 g and
GBP 0.35/pack, MdAPE 29.63%. These validate software behavior only. All 34
managed artifacts are retained; the fixture is not published as a real model.

Verification covers current-versus-regular amount selection, preserved source
bytes and eligibility, missing/mismatched quantities, currency, provenance and
target tampering, partial usable samples, exact published contract binding,
immutable replay and explicit fixture labeling. The documentation guard checks
the new pin offline and validates any cache present. The historical contracts,
portable prepare-only profiles and prior snapshots retain their versions.

Final verification: `uv sync --locked`,
`python3 -B scripts/fetch_contracts.py --all --offline`, `uv run pytest`,
`uv run ruff check .`, `python3 -B scripts/check_documentation.py` and
`git diff --check` passed. All 422 pytest cases passed, including 12 current-price
cases and the added offline cache integrity case. All 28 real-readiness and 34
fixture managed artifacts matched their hashes and byte lengths; identical
replays verified both immutable runs. The real Gold manifest retained its exact
supplied hash. No fixture or blocked readiness artifact was uploaded as a fitted
market model.


## Refit after integrating main and the published Gold snapshot

Local main commit `cd9e7df8eb7f50aee33d3fce5ca9f0509aff8deb` was integrated into
the task branch while retaining the independent baseline, tests and earlier run
records. Canonical data guides now live under `docs/data/`. The merge retains
main's shared current-price helper and experiment interface, alongside the
baseline's existing `freeze_partitions` interface. Their historical split
algorithms remain explicitly distinct; shared comparison assignments are still
pending and no cross-model score is claimed.

The refit downloaded every manifest-pinned training file at immutable dataset
revision `95c5fbd0ab5fa9a41fa5333648321d95f16927a7`, directory
`gold/chocolate/uk/gold-8b897101474becaef946922b/`. The 24 downloaded files comprise
the manifest and its 23 managed files. Every hash/length matched
`schemas/chocolate/gold-dataset.json`; `verified_gold` validated the complete
embedded parent and both Parquet views. The Gold manifest retains SHA-256
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Source bytes match the previously supplied local snapshot.

The trainer now binds the exact Gold publication reference and immutable
revision in artifacts and rejects a matching snapshot identity whose manifest
or inventory differs from that pin. The current-price target remains pinned at
`d743cb8dbca37f5241cccd444a16165523304f6c` with policy
`current-consumer-price-1`. Recorded refit command:

```sh
uv run python scripts/train_chocolate_retailer_median.py \
  --gold-root data/downloaded-gold/95c5fbd0ab5fa9a41fa5333648321d95f16927a7/gold-8b897101474becaef946922b \
  --current-price-proxy
```

Run `retailer-median-cb2a4f9f896cd54f275d5031` accepted 2,134 eligible rows,
derived 630 current unit-price targets and found zero complete model inputs.
Its concrete missingness and two readiness blockers match the previous attempt.
All rows lack variant IDs and population boundary values; the remaining family,
pack, weight, brand and chocolate-type gaps are listed above. Regular-price,
promotion, tax, price-review and availability metadata are not target gates.
The run has 29 managed artifacts under
`data/models/chocolate/uk/retailer_median/retailer-median-cb2a4f9f896cd54f275d5031/`.
All hashes and byte lengths passed, and an identical replay verified the immutable
run. No real fitted model, market metrics or upload resulted.

Integration verification passed: `uv sync --locked`, all four contract caches
verified offline, all 467 pytest cases, Ruff, documentation guard and whitespace
checks. Publication tests cover retained exact reference bytes and rejecting a
changed pin before model artifacts are written. Merge resolution retains both
`validate_price_targets(..., design=...)` and the historical baseline's explicit
auxiliary-eligibility override argument. Canonical shared current-price helper
bytes now match main, including its imports from the shared model policy.


## Latest Gold sufficiency inspection

A fresh download from dataset head `06680d7248ccc4487726b9a97e59aa8f586fb54e`
verified the same immutable Gold snapshot and managed hashes. It still has
2,134 eligible rows and 630 current unit-price targets. A separate core-input
audit finds 119 Ocado/Waitrose retail rows with supported chocolate type and
normalized price, and 52 rows with family IDs across 14 families. All 52 family
rows are Waitrose: 10 dark, 38 milk and 4 white. These values can support limited
exploratory calculations, but do not establish the declared single-pack study,
exact physical variant identity or an Ocado comparison. The existing trainer
protocol still has zero complete rows. The full local read-only audit is under
`data/huggingface-latest-gold-readiness.json`; downloaded snapshots and generated
inspection outputs remain outside Git.
