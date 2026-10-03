# Matched retailer diagnostic

`matched_retailer` fits family-weighted exact physical variant fixed effects plus
retailer fixed effects on log GBP per 100 g under an explicit price policy.
The current study uses collected current/displayed prices; historical regular
price contracts remain separate. It describes retailer
contrasts within the matched assortment. The implementation is
[`scripts/chocolate_matched_retailer.py`](../../scripts/chocolate_matched_retailer.py),
dispatched through [`scripts/train_chocolate_model.py`](../../scripts/train_chocolate_model.py).
The existing `chocolate-pricing-design-3` experimental OLS path retains its
separate identifier and contract. Only the assigned estimator runs here.

## Inputs and local contract

Use raw → combined Silver → immutable Parquet [Gold](chocolate-gold.md).
The loader verifies all Gold managed hashes, Parquet logical digests, copied
contracts, source manifest provenance, eligible/candidate equality and reviewed
regular-price observations. Copied contract hashes and lengths must match the
immutable base reference in the working contract. The default path retains the legacy snapshot's eligibility predictor
requirements. The explicit task-authorized path below selects this diagnostic's
required fields while preserving source eligibility metadata.

The integrated CLI selects this estimator with `--model-id matched_retailer`.
Its target and experiment settings come from the matched working contract and
`--match-review`; the OLS `--current-price-target`/`--target-contract-root` and
hedonic `--experiment-manifest`/`--fixture` options are rejected for this selector.
Prepare matched contracts with the command below. The integrated trainer's
`--prepare-working-contract` option prepares the separate hedonic policy.

Prepare an explicit unpublished working contract:

```sh
uv run python scripts/chocolate_matched_retailer.py \
  --prepare-working-contract data/working-contracts/matched_retailer/model-design.json
```

This produces `chocolate-matched-retailer-design-1` from verified cached dataset
contracts. Contract bodies stay in ignored `data/`, and exact bytes travel with
each run. The contract specifies Waitrose/Ocado, the standard single-pack
supermarket chocolate-bar cohort, `regular-consumer-price-1`, seeds, matching,
weights and support requirements. Set its `price_window.start` and `.end` to
genuine aware observation dates before fitting. The initial null window is a
readiness blocker. Tesco requires a separate evidence and validation extension.

The contract records `chocolate-comparison-policy-1`: regression core size,
type, recipe/inclusion and retailer features; optional cocoa/basis and claims;
fitting-only transformations and known-brand identification; exclusions of names,
identifiers and observed/derived prices. This estimator uses only exact-variant
and retailer effects; variant identity is necessary to its diagnostic. It fits
no regression encoder, imputer, interactions or feature selection. Common
regression feature identification and alignment with other sessions remain
pending. Missing shared fields cannot be invented to enable a comparison.

## Exact matching evidence

`--match-review` names a JSON bundle with `format` equal to
`chocolate-exact-match-reviews-1`, an explicit boolean `synthetic_fixture`,
`gold_manifest_sha256`, `managed_files`, and `reviews` keyed by observation ID.
Every managed evidence file has its SHA-256 and byte length. Paths must stay
inside the bundle directory and cannot use symlinks. The run copies all referenced
original JSON evidence verbatim. Each review has `status: reviewed`, an identified
`reviewed_by`, and `fields`. Each field has `value` and a nonempty `evidence` list
of `{source_file, pointer}` objects. JSON pointers must resolve to exactly the
reviewed value, including its JSON type. Upstream reviewers remain responsible
for source meaning; pointer equality does not establish independent truth.

Required fields are:

| Field | Rule |
| --- | --- |
| `cohort` | `standard_single_pack_supermarket_chocolate_bar` |
| `formulation`, `flavor` | Reviewed identical physical recipe and flavor within a variant ID |
| `edible_weight_g`, `pack_count` | Positive verified edible weight matching Gold; integer pack count one |
| `brand`, `chocolate_type` | Reviewed values matching Gold |
| `observed_at`, `observed_at_basis` | Aware source price observation date matching Gold; basis `source_price_observation` |
| `channel`, `location_scope`, `membership` | `online`, resolved common price scope, `public_non_member` |

Family equality never establishes variant equality. Conflicting formulation,
flavor, weight, pack, brand, type or family within a variant fails. Unknown scope
or invocation-time evidence cannot establish contemporaneous matching.
Each variant must have one observation at each of at least two retailers,
identical context, and a full observation window no longer than 48 hours.
Unmatched variants, conflicting contexts and wider windows receive explicit
domain exclusions. Repeated seller observations require upstream occasion
selection. Seller rows and stable listing IDs stay separate.

## Experiment and uncertainty

Freeze splits on all upstream eligible rows before narrowing the matched domain.
Order whole families by the lexicographic SHA-256 digest of UTF-8
`str(1729) + ":" + family_id`, breaking ties by family ID. Assign the first
`floor(0.6N)` families to fitting, the next `floor(0.2N)` to calibration, and the
remainder to final testing. Persist the algorithm, full family order and exact
assignments; brands and prices never affect assignment. Equal input identities
and configuration reproduce equal splits. Cross-session split identity must be
verified before any common experiment comparison.

Fit only contemporaneous matches in the fitting partition. Reference code
retailer effects within each connected component, with one intercept per exact
variant and no separate global intercept. Solve weighted least squares using
NumPy 2.2.6, refusing deficient rank or a condition number above `1e12`.
Recompute `1/n_f` within each fitted component and diagnostic subset.

The retailer–variant graph records direct links, independent-family and variant
counts, connected components and families whose removal disconnects retailers.
Contrasts exist only inside a component, with direct/indirect linkage labeled.
Leave each family out and record changed contrasts or disconnection. Resample
whole families 200 times with seed 1729. Repeated sampled families receive
distinct cluster and variant aliases, giving every sampled family total weight
one. Persist all successful bootstrap draws and disconnection counts.

Report 95% percentile intervals only with at least two independent families,
all family deletions connected for that pair, at least 20 successful replicates,
and at least 80% bootstrap success. Otherwise report the point contrast with
weak-support status and unavailable uncertainty. These minimums are configurable
engineering checks, not a market representativeness or release claim.

Whole-family holdouts have no fitted exact-variant intercept, so calibration and
final testing receive unavailable predictions and explicit domain membership.
No new-product or regression conformal prediction interval applies. Fitting
residual diagnostics report family-weighted unit/pack MAE, percentage error,
signed bias and listing-weighted sensitivity, with retailer/type/size/brand/
missingness breakdowns. They are descriptive fit diagnostics. Comparator gates,
champion selection and release readiness remain pending. No full-sample refit
is performed by this entry point.

## Run and verified status

```sh
uv run python scripts/train_chocolate_model.py --model-id matched_retailer \
  --gold-root data/gold/chocolate/uk/gold-4939405fcf8724686f9ee32c \
  --working-contract data/working-contracts/matched_retailer/model-design.json \
  --group bar
```

Add `--match-review <bundle.json>` when reviewed exact matching evidence is
available. Immutable runs are stored under
`data/models/chocolate/uk/matched_retailer/<run-id>/`. Each run includes copied
inputs/evidence, manifest, experiment, splits, predictions/domain membership,
support rules, evaluation, uncertainty, a reproducible argument vector, and fitted
parameters when available. Run identity binds model ID, Gold/Silver/contract/
experiment/review hashes, implementation bytes, versions and seeds. Identical
reruns verify bytes; differing artifacts cannot overwrite an existing run.

On 3 October 2026, this session rebuilt Silver
`silver-f651a7faea94ed5a7f003e64` from the saved project's preserved raw archive:
3,743 listings, 4,347 captures, 2,134 candidates, zero eligible rows. Gold
`gold-4939405fcf8724686f9ee32c` preserves those values and eligibility. Contracts
pin dataset revision `d549ad91d63fb452af605df4a939c4e1f0a59bfa`.
Actual readiness artifacts record exclusions: all 2,134 candidates lack resolved
scope, physical identity, reviewed edible quantity and regular-price/tax context;
1,157 also lack verified observation time/availability. Exact matching reviews
and a genuine price window are absent. No real model fitted, calibrated or
released. Synthetic fixture fits are explicitly labeled and do not establish
real evidence support. Model upload authorization does not permit publishing
these fixture fits as real trained models.

The working contract is a local proposal. A production contract migration still
needs a coordinated original/portable release, reviewed eligible rebuild and
the [required Hugging Face release review](decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit).
Existing dataset pins, portable contracts and historical snapshots retain their
published identities.

## Task-authorized Gold verification

The user confirmed that all Gold data are verified and requested training directly
from the existing layer. `--verified-gold-candidates` records that instruction in
the model run and considers the existing candidate Parquet table. It preserves
the Gold manifest, Parquet bytes, source eligibility flags and exclusion reasons.
It requires no Silver or Gold rebuild. Source metadata cannot enable this option;
the calling task supplies it under the user's explicit instruction.

This path selects the fields required by exact matching, so historical optional
regression-feature review requirements do not block it. It validates actual
regular prices, edible weight, target arithmetic, price provenance and variant/
family identity. Existing matching/context values can be read directly from
copied Gold price observations, using the required field names in the table
above; missing values remain missing. A supplied match bundle is also supported.
Splits use existing family identities; rows without family identity have an
unavailable partition. Predictions/domain membership retain every considered
candidate, including rows with missing required values.

The direct command appends `--verified-gold-candidates` to the earlier command.
A fresh attempt inspected `gold-4939405fcf8724686f9ee32c`, the only snapshot
available in this worktree or the two referenced checkouts. It considered all
2,134 candidates as task-verified. Actual stored values include zero regular
prices, zero regular unit-price targets, zero exact-variant IDs, 402 family IDs,
631 candidate edible weights and 2,133 displayed prices. All tax bases remain
`unknown` values. No fitted matched-retailer model can be obtained from these
missing numeric targets and exact identities. This attempt uses current values
and bypasses historical review flags; it does not require a repeated review of
the user's verification decision.

The new run records `gold_verification_basis: explicit_task_authorized_candidates`
and concrete missing-value counts. Displayed prices cannot substitute for this
model's specified regular-price target. The missing formulation, flavor, pack
and comparable channel/location/membership fields remain additional matching
requirements when numeric and identity inputs become available.

## Refresh from promoted Gold

The loader supports `chocolate-gold-bulk-eligibility-1`. It verifies the complete
embedded parent, source/copy hashes, decoded analytical values and user
eligibility provenance. Both modeling tables contain the promoted candidate
rows; flags and exclusions are the only permitted changes from the parent.
The model run persists `eligibility_provenance`, the parent Gold ID, exact input
manifest and copied storage-design identity.

For a provided Gold snapshot with locally prepared copied contracts, prepare a
working configuration bound to that exact input:

```sh
uv run python scripts/chocolate_matched_retailer.py \
  --prepare-working-contract data/working-contracts/matched_retailer/gold-8b897101474becaef946922b/model-design.json \
  --gold-root /Users/coral/.codex/worktrees/bb33/rgc/data/gold/chocolate/uk/gold-8b897101474becaef946922b
uv run python scripts/train_chocolate_model.py --model-id matched_retailer \
  --gold-root /Users/coral/.codex/worktrees/bb33/rgc/data/gold/chocolate/uk/gold-8b897101474becaef946922b \
  --working-contract data/working-contracts/matched_retailer/gold-8b897101474becaef946922b/model-design.json \
  --group bar --verified-gold-candidates
```

`input_contract_basis: verified_gold_snapshot` binds the immutable Gold manifest
and every copied contract's SHA-256. The copied storage design in this snapshot
is `chocolate-retailer-median-design-1`; this records the source table contract.
The fitted estimator remains explicitly `matched_retailer`, and its local model
design remains `chocolate-matched-retailer-design-1`. The snapshot binding does
not label local input contracts as published or change repository dataset pins.

A fresh attempt used `gold-8b897101474becaef946922b`, manifest SHA-256
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`, from
parent `gold-56817976905f24210105f069` and Silver
`silver-485af2f8e7fae127cd73578b`. Both input tables verify with 2,134 eligible
rows and empty exclusions. Actual values still include no regular price, no
regular-unit-price target and no exact-variant ID on any row. The attempt saves
current missing-value counts and the new provenance; no fit or upload occurred.
No Gold or Silver was rebuilt for this refresh.

## Current-price study policy

The user superseded the separately evidenced regular-price requirement and
selected collected current/displayed prices as the modeling target.
`chocolate-matched-retailer-design-3` uses `current-consumer-price-1` under that
explicit assumption, with log current GBP per 100 g as the target. Promotions
and unknown tax metadata are retained limitations and do not exclude rows.
Historical regular-price working contracts and snapshots keep their identities.

Prepare the current-price configuration by adding `--current-price-proxy` to
the snapshot-bound preparation command and selecting a fresh output path.
The training command continues to use `--verified-gold-candidates`. The trainer
reads actual positive `displayed_price` and GBP currency from the copied price
observation. Shared preparation `chocolate-current-price-target-1` requires
positive candidate `quantity.total_edible_weight_g` and a matching positive
quantity on the price observation. Missing quantities remain missing. The target
is taken from published `chocolate-pricing-current-price-design-1`, pinned at
dataset commit `d743cb8dbca37f5241cccd444a16165523304f6c` through the
[current-price manifest](../schemas/chocolate/current-price/dataset-contract.json).
The working configuration and run bind that exact reference and copy all four
verified contract payloads. Fetch them with `scripts/fetch_contracts.py
--current-price` before preparing the configuration offline.

Derived current targets are stored in a separate `model_target` object in model
artifacts. Original rows, regular-price fields, review flags, promotion and tax
evidence remain in the copied inputs. `prepared-current-inputs.jsonl` records
all considered rows, current targets, quantity sources and source price context.
The shared adapter also supplies equal `regular_*` compatibility aliases in
these derived rows; they represent the declared current proxy and do not certify
regular prices. `current-price-preparation.json` records common target counts,
failure reasons and limitations.
The fixed-effect estimator and diagnostic metrics consume that explicit target.
No regular-price value, non-promotional classification or verified tax inclusion
is required in this study mode. Missing current price, actual edible weight, GBP
currency, exact identity and comparable context remain model requirements.

The shared-contract attempt against promoted `gold-8b897101474becaef946922b`
uses all 2,134 eligible rows and finds 2,133 positive current pack prices and 630
normalized targets. One price and 1,503 candidate edible weights are missing or
invalid. All 2,134 rows lack exact-variant IDs; 1,732 lack family IDs, 1,289 lack
type and 997 lack brand. No matched fit or upload occurred. This supersedes the
interim design-2 domain of 1,210 targets, which allowed price-only quantities.
Gold manifest SHA-256 remains
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Current-price support is fixture-validated with promotional/unknown-tax
observations and no regular-price values. Gold and its original rows are intact.

## Pull from published latest Gold

On 3 October 2026, the dataset API resolved its head to
`bb1c9de580c64cc13aac62b352d58704fe2dd60e`. At that immutable revision,
`gold/chocolate/uk/latest.json` selects `gold-8b897101474becaef946922b` with the
same manifest SHA-256 above and the published current-price target reference.
Downloaded all 23 managed files (24,540,810 bytes) plus the manifest into
`data/gold/chocolate/uk/gold-8b897101474becaef946922b/`, verifying lengths and
hashes before exposing the local snapshot. The download receipt and original
latest pointer are under `data/model-input-receipts/matched_retailer/`.

Prepared a separate model configuration from this local copy and attempted the
assigned estimator:

```sh
uv run python scripts/chocolate_matched_retailer.py \
  --prepare-working-contract data/working-contracts/matched_retailer/hf-bb1c9de580c64cc13aac62b352d58704fe2dd60e/model-design.json \
  --gold-root data/gold/chocolate/uk/gold-8b897101474becaef946922b \
  --current-price-proxy
uv run python scripts/train_chocolate_model.py --model-id matched_retailer \
  --gold-root data/gold/chocolate/uk/gold-8b897101474becaef946922b \
  --working-contract data/working-contracts/matched_retailer/hf-bb1c9de580c64cc13aac62b352d58704fe2dd60e/model-design.json \
  --group bar --verified-gold-candidates \
  --output data/models/chocolate/uk/hf-bb1c9de580c64cc13aac62b352d58704fe2dd60e
```

The immutable result is `matched-run-1525e48d0fb469cbba36d8a9` under that
output's `matched_retailer/` directory. It reproduces the 630 targets and zero
exact variant IDs, with no fitting rows. Selecting fewer regression features
cannot supply the exact product matches required by this estimator. Its report
records the unsuccessful fit attempt; no fitted model or upload is claimed.
All Gold bytes still match the downloaded manifest after training.

A subsequent published revision, `95c5fbd0ab5fa9a41fa5333648321d95f16927a7`,
was announced during this pull. Downloaded all 25 remote Gold files at that exact
revision, including latest pointer and manifest; every byte matches the first
download. The published Gold pin read from local main `cd9e7df` also matches
all managed hashes and the manifest. Shared current-price code and target
reference are identical to that main revision. A separate fit attempt under
`data/models/chocolate/uk/hf-95c5fbd0ab5fa9a41fa5333648321d95f16927a7/matched_retailer/`
produces the same run ID and missing-input counts. The receipt records the new
publication revision, and all 28 model artifacts verify. Gold remains unchanged.
