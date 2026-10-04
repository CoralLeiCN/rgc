# UK chocolate gold training data

Gold is the canonical Parquet training interface downstream of the combined
[Silver dataset](chocolate-silver.md). Every Gold row belongs to the training
population. Gold has no `model_eligible` or `exclusion_reasons` columns and no
separate eligible subset. Models validate the actual targets, quantities,
identities and predictors needed by their selected study.

The [schema guide](chocolate-schema.md) owns Silver evidence interpretation and
reviews. The [data specification](spec.md) owns dataset interfaces; the
[model specification](../model/spec.md) owns readiness and release requirements.
The portable processing profiles retain their selected contracts. Source evidence,
contracts, missing values and immutable historical snapshots retain their original
meaning.

## Processing handoff

The layer sequence is Bronze (raw) → Silver → Gold. Category-processing checks
that preserved Bronze data and a generated schema are
available, then finishes at reviewed Silver. If the initial schema is absent,
category-schema creates it from the raw evidence before processing. Model-input
preparation belongs to the subsequent Silver-to-Gold/modeling handoff. Silver
retains evidence interpretation, reviews and existing eligibility decisions;
Gold and model consumers use that provenance under their selected study.

The portable package's downstream
[procedure](../../plugins/category-processing/skills/category-processing/references/silver-to-gold.md)
includes its legacy JSONL/encoder helper. That helper does not create canonical
chocolate Parquet Gold. Its existing model-contract dependency and training views
remain compatibility behavior; this instruction change does not alter immutable
Silver or Gold snapshots or their price bases.

## Build an immutable gold snapshot

Run from the repository root:

```sh
uv run --script scripts/build_chocolate_gold.py \
  --silver-root data/silver/chocolate/uk \
  --output data/gold/chocolate/uk
```

The builder verifies every managed Silver file, its exact contract hashes and
its source training tables before exporting every candidate in original order.
It removes only the two selection fields from the analytical rows. It uses
`pyarrow==21.0.0`, an explicit typed Arrow schema and ZSTD compression, and checks
that the Parquet round trip preserves all analytical values, including nulls.
An empty population remains a typed, loadable table.

The output is a content-addressed `data/gold/chocolate/uk/<gold-version>/`
snapshot. Identical verified replay reuses it; changed or damaged existing bytes
cannot be overwritten. Source and output directories must be separate. Migration
may write a sibling snapshot in the source Gold snapshot's containing directory.

## Output contract

| Output | Meaning |
| --- | --- |
| `training-data.parquet` | Every Silver candidate, with `model_eligible` and `exclusion_reasons` removed. |
| `inputs/profile.json`, `inputs/source-mappings.json`, `inputs/product.schema.json`, `inputs/model-design.json` | Exact source analytical contracts. |
| `inputs/prices.jsonl`, `inputs/quality-report.json` | Exact source observations and Silver report, including original evidence and review metadata. |
| `inputs/family-mappings.json` | Exact accepted identity decisions when present. |
| `inputs/silver-manifest.json` | Exact source Silver manifest and contract/source identities. |
| `inputs/source-training-candidates.jsonl`, `inputs/source-model-inputs.jsonl` | Original source training views retained solely for provenance and projection verification. |
| `inputs/parent-gold/` | Complete verified parent snapshot when migrating or annotating an existing Gold snapshot. |
| `manifest.json` | Gold identity, Arrow version, source hashes, logical row digest and managed file hashes. |
| `report.json` | `counts.training_rows`, analytical preservation, storage readiness and model readiness limitations. |

`chocolate-gold-population-1` and `chocolate-gold-arrow-3` define this format.
Layer, manifest and report versions remain `chocolate-gold-1`,
`chocolate-gold-manifest-1` and `chocolate-gold-report-1`. Source product, mapping
and model contracts retain their exact dataset-owned bytes and versions. Gold's
row version fields retain their Silver values; the snapshot has its own
`gold-<24-hex-digest>` identity.

There is one primary training table. Gold reports contain no eligibility counts,
exclusion counts, eligibility-preservation flag or eligibility override provenance.
Copied source reports and observations can retain those historical fields as
source evidence. They do not determine Gold population membership.

## Build a separate inferred export

The version 1 inferred export packages curated attribute decisions beside a
Gold training snapshot using its historical storage format. The exporter
accepts an explicit Silver snapshot, accepted decisions and their provenance:

```sh
uv run --script scripts/build_chocolate_gold_inferred.py \
  --silver-root data/silver/chocolate/uk/<silver-version> \
  --decisions data/investigation/<review>/adoption/accepted-decisions.jsonl \
  --provenance data/investigation/<review>/adoption/provenance.json \
  --output data/gold-inferred/chocolate/uk
```

It writes an immutable `gold-inferred-<hash>` bundle. `products.parquet`
contains every Silver product with typed columns for the 103 profile attributes.
The exporter verifies that each accepted decision matches its reviewed Silver
cell and source evidence. `record_json` retains the complete Silver record,
including evidence, statuses and review context. The `inference/` directory
preserves accepted-decision JSONL and provenance bytes, including model records
and source review evidence.

Version 1 explicitly uses `build_legacy_gold_dataset` and
`verified_gold_storage` for its `training/` child. This preserves historical
candidate and eligible tables, source flags, copied contracts and price bytes
through wrapper verification. The public `verified_gold` loader independently
exposes all candidates without selection fields when consuming that child.
Supply `--gold-root <bundle>/training` to a conventional Gold trainer, with the
current-price target selected for the current study. The inferred LightGBM
route below accepts the whole bundle and joins the reviewed product attributes.

The exporter packages existing Silver values and supplied review artifacts;
its manifest binds their exact bytes and source identity. Publish it under the
separate `gold-inferred/chocolate/uk/` dataset prefix with its own `latest.json`.
The original publication preserved normal Silver/Gold pointers and the default
training configuration.

The [2026-10-03 publication receipt](analysis/chocolate-gold-inferred-publication-2026-10-03.json)
records `gold-inferred-5b539b9c4adbb011a40d7792`: 3,743 products, 103 attribute
columns, 2,159 curated additions and 2,134 training candidates. The immutable
on-disk child retains zero source-eligible inputs under its pinned historical
`regular-consumer-price-1` contract. That counter does not restrict the current
loader's population. All 47 published files were downloaded and verified.

## Mark Gold rows reviewed at the user's request

An optional administrative review records its author and reason in a new
population manifest and report:

```sh
uv run --script scripts/review_chocolate_gold.py \
  --gold-root 'data/gold/chocolate/uk/<gold-version>' \
  --output data/gold/chocolate/uk \
  --reviewed-by task-user \
  --reason 'Bulk marked reviewed at the user request on 2026-10-03'
```

The complete parent remains under `inputs/parent-gold/`. `review_provenance`
records `review_status`, `review_basis`, `reviewed_by`, `reason` and
`evidence_validation_performed: false`. The operation writes the same analytical
population without row review or eligibility columns. It records an administrative
instruction and does not assert that source facts were individually verified.

## Make every Gold candidate model eligible

The user's refined instruction on 2026-10-03 removes the eligibility requirement
from Gold entirely. Every candidate is included automatically when building or
loading Gold. A separate bulk eligibility instruction is unnecessary.

Migrate an exact historical snapshot to the new storage contract:

```sh
uv run --script scripts/build_chocolate_gold.py \
  --gold-root 'data/gold/chocolate/uk/<parent-gold-version>' \
  --output data/gold/chocolate/uk
```

The migration verifies and retains the complete parent, removes the two selection
fields and writes every candidate to `training-data.parquet`. It accepts original,
bulk-reviewed, historical bulk-eligibility and population snapshots. It compares
ordered analytical values with the verified parent; rehashing a changed value,
omitted row or reordered table cannot bypass this comparison. The source snapshot
remains immutable.

`scripts/make_chocolate_gold_eligible.py` remains a compatibility entry point for
this migration. It requires only the source and output paths. Historical
`--authorized-by` and `--reason` arguments are accepted for command compatibility;
Gold membership needs no authorization annotation.

Historical `chocolate-gold-pass-through-1`, `chocolate-gold-bulk-review-1` and
`chocolate-gold-bulk-eligibility-1` storage is still verified against its original
contract. `verified_gold` then exposes every candidate without either selection
field. Its `training-candidates.jsonl` and `model-inputs.jsonl` return values are
identical in-memory aliases for the population, rather than stored subsets.
Original source flags remain inspectable in retained provenance.

## Training and readiness

For the current chocolate study:

```sh
uv run --script scripts/train_chocolate_model.py \
  --gold-root 'data/gold/chocolate/uk/<gold-version>' \
  --current-price-target \
  --output data/models/chocolate/uk \
  --group bar
```

Trainers verify the Gold manifest, managed bytes, schema, ordered source projection
and logical digests before selecting their declared group or cohort. Gold row and
source-price eligibility flags are not prerequisites. The OLS run records
`population_selection: all_gold_rows`, `counts.training_rows` and actual selected
counts. Its selected inputs have no eligibility or exclusion fields.

Every row remains part of the population even if a target or predictor is missing.
Actual input failures produce readiness blockers and no fitted model. Family
holdout, preprocessing, numerical identification, study context and model release
checks still belong to the selected trainer. Current-price preparation uses
`current-consumer-price-1`: collected displayed prices serve as the regular-price
proxy without a separate regular-price, promotion or confirmed-tax gate. Positive
GBP prices and actual edible quantities are needed to compute GBP per 100 g.

Historical `regular-consumer-price-1` studies retain their original target basis
and reviewed source context. Source price flags do not gate Gold membership;
their price, quantity, time and tax checks still validate the selected historical
study. Silver compatibility commands continue to apply Silver's source selection.
Gold population membership alone does not establish a successful or validated fit.

## Independent LightGBM without brand

The [without-brand trainer](analysis/lightgbm-without-brand-implementation.md)
verifies immutable Gold and an explicit local working contract, then freezes
family partitions and fitting-only transforms. Its original regular-price
Gold attempt had zero eligible inputs; synthetic fixture fitting is published
separately. New shared current-price data requires explicit trainer migration
and required feature evidence. Gold eligibility alone cannot establish fitting
or market validity.

## Add processing later

The Silver-to-Gold stage projects every candidate into the training population.
Bulk review records manifest metadata; historical bulk eligibility is supported
for immutable storage verification. Any further filtering, missing-value
handling, feature preparation or eligibility change must be explicitly designed
and versioned, documented with its evidence and tested. Preserve the original
silver input and earlier gold snapshots; write a new immutable gold snapshot
with its own processing provenance. Changing storage cannot silently relax the
reviewed-input contract or manufacture facts from missing evidence.

## Integration with dataset-owned contracts

The locked pytest environment includes NumPy 2.2.6 and PyArrow 21.0.0 for the numerical and Parquet checks. Silver resolves immutable dataset pins or explicit custom working-contract roots before producing its snapshot. Gold copies the exact resolved contracts and their hashes, rather than resolving newer contracts at load time. A prepared schema/design release cannot change an existing Gold snapshot. The [published release](analysis/gold-modeling-contract-release.md) records the verified immutable contract revision for the updated Silver defaults; verified existing Gold remains self-contained.


## Prepare the current-price training target

Append `--current-price-target` to the experimental OLS training command. The
trainer resolves the dataset-owned `chocolate-pricing-current-price-design-1`
contract, reads unchanged Gold prices, and derives current GBP per 100 g targets.
A separate regular price, price review annotation, promotion classification or
confirmed tax basis is not required. The Gold source remains immutable and all
Gold candidates remain considered, including rows lacking quantities.
The run saves current preparation counts, explicit current targets in selected
inputs, the effective model design and exact target contract. Original source
contracts and source price bytes remain copied as provenance. Missing required
values produce a saved unavailable run with concrete blockers.

For a prepared local release, `--target-contract-root` supplies its verified
working contract directory. The three model chats use the shared
`current_price_targets` and `current_price_design` helpers with their selected
model designs. Their run artifacts must record `current-consumer-price-1` and
its limitations. See [the modeling specification](chocolate-modeling-design.md#1-population-and-price-target)
and [PROJECT.md limitations](../../PROJECT.md#limitations).

## LightGBM with brand trainer

Use the [independent LightGBM with brand command](chocolate-lightgbm-with-brand.md#run-from-verified-gold) for the proposed supermarket experiment. It verifies immutable Gold, managed bytes, logical row digests, copied contracts and reviewed price observations, then saves model-specific immutable artifacts or a readiness report. It requires an explicit unpublished working contract and source-price window. The historical `gold-4939405fcf8724686f9ee32c` stores 2,134 candidates and zero source-eligible inputs. Its original attempt did not fit; the current population loader exposes every candidate and validates numerical usability separately. Existing OLS snapshots and Gold bulk review cannot supply missing population, identity or price evidence. Fixture runs retain a synthetic status through artifacts and loaded predictions.

## Local population migration

The verified local migration `gold-ae712cc107e875e18816280c` contains all 2,134
rows in one `training-data.parquet` without selection fields. Its source is the
published snapshot below, retained completely inside the new snapshot. Its
manifest SHA-256 is
`a3add352cf4974bd447b736f80314dd96eca182e2ca1bea36c52e253468f83c6`.
Current-price preparation considered all rows and produced 630 unit-price targets.
The local readiness run selected 800 bar observations and recorded missing
variant identities and repeated listing observations as blockers. No model fitted.
This migration has not been published to Hugging Face.

## Published all-eligible training snapshot

The historical user-authorized all-eligible snapshot `gold-8b897101474becaef946922b` is
published in `CoralLeiCN/rgc-collections` at immutable revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7`, under
`gold/chocolate/uk/gold-8b897101474becaef946922b/`. Both primary Parquet views
contain 2,134 eligible candidates. The 25 uploaded files include the complete
original parent and `gold/chocolate/uk/latest.json`. Every remote byte was
downloaded and verified, and the downloaded snapshot passed `verified_gold`.

The [Gold dataset reference](../../schemas/chocolate/gold-dataset.json) pins the
revision, source manifest checksum and every managed file checksum. Its source
manifest SHA-256 is
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
The latest pointer also records the current-price target contract; training
applies that explicitly recorded interpretation to the preserved source prices.
Download the exact snapshot directory, including `inputs/parent-gold/`, then
supply it with `--gold-root` and `--current-price-target`. The current-price
contract is independently pinned at revision
`d743cb8dbca37f5241cccd444a16165523304f6c`. A published eligible dataset does not
establish a successful fit or model release readiness.


The independent [retailer median refit](analysis/retailer-median-training.md#refit-after-integrating-main-and-the-published-gold-snapshot)
uses all 2,134 eligible rows from the exact published Gold revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7`. The current displayed-price target
produces 630 GBP/100 g values. Missing variant IDs and population boundary values
in every row, plus other family/quantity/context gaps, prevent fitting. Its
trainer preserves the original Gold/evidence bytes, applies the published
current target to its selected retailer/type predictors, and records the exact
Gold publication pin, target contracts and per-row readiness. Historical regular
mode remains available; no real baseline fit or upload is claimed.

## Public dataset default loader

Following the user's request to keep raw files locally, the verified dataset
card at `06680d7248ccc4487726b9a97e59aa8f586fb54e` replaces the root raw index with
`gold/chocolate/uk/gold-8b897101474becaef946922b/training-data.parquet` for its
default `train` split. The metadata was downloaded and verified; the table's
SHA-256 and 2,134-row Parquet metadata match the existing Gold reference. This
selects the complete Gold population; the historical snapshot records the user's bulk
selection and does not establish complete model targets or individual evidence
review. Immutable Gold files and the existing Gold publication pin are retained.
Follow [local raw storage](dataset-contracts.md#local-raw-evidence-storage) for
source locations and remote deletion provenance.

## Independent hedonic training handoff

The assigned estimator is runnable with `--model-id hedonic_without_brand --gold-root <immutable-snapshot> --working-contract <local-policy> --group bar`. Prepare the policy with `--prepare-working-contract <local-policy>`. Its default run root is `data/models/chocolate/uk/hedonic_without_brand/`; the [implementation record](analysis/hedonic-without-brand-implementation.md) defines commands, frozen experiments, fitting/calibration/test partitions and verified model artifacts. Gold verification retains managed hashes, logical row digests and original price/contract provenance. The current loader considers every candidate without eligibility columns. The historical regular-price Gold inspected in this session has zero eligible rows and lacks three required handoff declarations, so the actual attempt writes an immutable readiness report and returns status 2. Fixture fitting and calibration validate numerical behavior; no real fit or released interval exists.


## Gold inferred web collection

The web workspace now consumes the published
`gold-inferred-5b539b9c4adbb011a40d7792` export at immutable dataset revision
`812a03a5faaced471a2a20f4c389865ed5675826`. Its 3,743 complete product records
retain all 103 attributes and 2,159 accepted additions supported by source evidence across
33 attributes. Parquet `record_json` owns complete values and evidence; the
web adapter validates them with the export's copied contracts and preserves
per-field review states. The immutable nested training files retain 2,134 candidates, zero
source-eligible inputs and the historical `regular-consumer-price-1` basis. The
current Gold loader exposes all 2,134 candidates without selection fields; the
current-price study applies its own target policy. Silver continues to own source
processing, interpretation, review and eligibility. The app reference pins the
manifest and revision; [collection integration](../collection-integration.md)
defines preparation and offline rebuild commands.

## Matched retailer trainer handoff

`train_chocolate_model.py --model-id matched_retailer --gold-root <snapshot>
--working-contract <local-model-design.json> --group bar` verifies Gold before
preparing an independent diagnostic. Add `--match-review <bundle.json>` for
reviewed formulation/flavor/weight/pack and genuine date/context evidence.
The [matched retailer guide](chocolate-matched-retailer.md) owns the bundle
interface, immutable run artifacts, matching and uncertainty. Administrative
Gold review does not establish any of that evidence.

The initial matched session rebuilt and verified `gold-4939405fcf8724686f9ee32c` from Silver
`silver-f651a7faea94ed5a7f003e64`, preserving all 2,134 candidates and zero eligible
rows. Real training saves readiness artifacts under
`data/models/chocolate/uk/matched_retailer/`; it has no fitted parameters or
calibration. Fitting partitions and held-out domain membership travel with the
run; exact effects do not predict held-out families.

The matched trainer considers every Gold candidate automatically. The historical
`--verified-gold-candidates` option is accepted for compatibility. Actual price,
weight and exact-identity values are checked in memory; optional regression
features can be omitted. Model artifacts record `gold_verification_basis:
all_gold_rows`, missing-value counts and candidate domain membership, with no
row eligibility fields.

The historical regular-price inspection found zero regular prices/targets and zero exact-variant
IDs in the existing 2,134-row snapshot. The [matched guide](chocolate-matched-retailer.md#task-authorized-gold-verification)
describes the command and concrete current failure.

## Explicit bulk eligibility snapshot loading

Historical `chocolate-gold-bulk-eligibility-1` snapshots record the earlier user
instruction and retain the complete source under `inputs/parent-gold/`. Their
stored promotion flags and provenance are verified against their original rule.
The public `verified_gold` loader then exposes every candidate without selection
fields. New builds and the compatibility migration command write
`chocolate-gold-population-1` with a single training table and no eligibility
provenance. Exact historical bytes and source Silver decisions remain preserved.

This matched-retailer session uses the already created promoted snapshot
`gold-8b897101474becaef946922b` at its supplied shared absolute path. Its manifest
hash is `e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`;
parent `gold-56817976905f24210105f069` and Silver
`silver-485af2f8e7fae127cd73578b` are independently verified through the retained
parent. All 2,134 candidates are now in both eligible and candidate views.
The [matched refresh](chocolate-matched-retailer.md#refresh-from-promoted-gold)
records actual remaining numeric/identity failures and its exact input contract
binding. No rebuild was performed in this session.

For the user's current-price proxy study, the matched trainer reads existing
Gold current/displayed prices and positive edible weights directly. It persists
derived `model_target` values in model artifacts while retaining original Gold
rows and price context. No Gold rebuild is required. The [current-price mode](chocolate-matched-retailer.md#current-price-study-policy)
records the explicit `current-consumer-price-1` assumption and binds the published
shared target overlay at `d743cb8dbca37f5241cccd444a16165523304f6c`.
Preparation requires candidate edible weight matching the price observation:
630 targets are available, with every exact variant ID missing. Promotions and
unresolved tax are limitations. All 2,134 Gold rows retain their user-authorized
eligibility and copied original values.

## Current training policy: every Gold candidate is eligible

The canonical Gold loader exposes every candidate without selection fields.
The inferred refit adapter follows this population policy under
`chocolate-gold-training-all-rows-2`. It verifies the version 1 inferred wrapper
and its historical child with `verified_gold_storage` before removing
`model_eligible` and `exclusion_reasons` from runtime rows. Original decisions
remain optional `source_model_eligible` and `source_exclusion_reasons`
provenance. Original price bytes remain in `source-prices.jsonl`. Runs save
`gold-training-policy.json` with the training population count and any
historical source counter. Historical counters never restrict admission.
New canonical Gold snapshots use `training-data.parquet`; the inferred version
1 wrapper retains its exact historical storage format and integrity checks.

The inferred layer from dataset revision
`812a03a5faaced471a2a20f4c389865ed5675826` is
`gold-inferred-5b539b9c4adbb011a40d7792`: 3,743 products, 103 typed attributes,
2,159 accepted decisions and 2,134 training candidates.
`scripts/chocolate_gold_inferred.py` verifies its wrapper, full product records,
accepted decisions, null states and conventional Gold child. Its builder and
CLI use the explicit legacy storage APIs to preserve this version 1 contract.

Refit with the pinned current displayed-price target:

```sh
uv run python scripts/train_chocolate_model.py \
  --model-id lightgbm_without_brand \
  --gold-root data/gold-inferred/chocolate/uk/gold-inferred-5b539b9c4adbb011a40d7792
```

This route uses `scripts/refit_chocolate_lightgbm_inferred.py` and its explicit
local research policy. The [refit record](analysis/lightgbm-without-brand-inferred-refit.md)
reports the actual model, family holdout, tuning and native TreeSHAP proof. All
2,134 candidates are eligible; 55 Waitrose bar observations across 15
established families have usable targets and pack weights for this experiment.
No Ocado performance, reliable market accuracy or calibrated intervals are
established. Models still require numerical inputs and declared grouping;
Gold eligibility supplies no missing values.

The completed inferred LightGBM refit is [published](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/88b08aeada37e228fcd80334b5abddd768da6968/model/lightgbm_without_brand/model-run-9f56df660a6d46e7cc720002)
at immutable dataset revision `88b08aeada37e228fcd80334b5abddd768da6968`. Its
[publication receipt](analysis/lightgbm-without-brand-inferred-model-publication.json)
records 16 verified model and metadata files. The source inferred Gold snapshot
retains its original immutable publication reference; model publication does
not rewrite source inputs or establish calibrated market predictions.
