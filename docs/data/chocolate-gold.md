# UK chocolate gold training data

Gold is the canonical Parquet training interface downstream of the combined
[silver dataset](chocolate-silver.md). Its initial pipeline passes silver's
existing training views through without semantic changes. It packages verified,
typed training data; it does not establish that every candidate is eligible for
the current model or that a statistically supported model can be fitted.
An optional bulk review operation records a user instruction as a separate Gold
workflow status in a new snapshot. A separate bulk eligibility operation makes
every candidate model eligible under an explicit user instruction and preserves
the complete parent snapshot, including Silver eligibility, for provenance.

The [schema guide](chocolate-schema.md) continues to own logical field meanings,
evidence reviews and eligibility. The [specification](../spec.md) owns cross-layer
and release requirements. The portable category-processing plugin keeps its
separate prepare-only interface and profile versions.

## Build an immutable gold snapshot

Run from the repository root:

```sh
uv run --script scripts/build_chocolate_gold.py \
  --silver-root data/silver/chocolate/uk \
  --output data/gold/chocolate/uk
```

These are the default input and output paths. The script pins `pyarrow==21.0.0`.
It writes a content-addressed snapshot under
`data/gold/chocolate/uk/<gold-version>/` rather than replacing an existing
snapshot. Unchanged inputs, contracts and implementation reproduce the same
version. An identical verified replay is accepted; an existing snapshot with
different or damaged contents is refused. Input and output paths must remain
separate.

The builder verifies silver's manifest, managed output hashes and copied
contracts before exporting. Parquet uses an explicit Arrow schema and ZSTD
compression, including the empty eligible table. The build checks that reading
each Parquet file returns the original logical JSON values in the original row
order. Logical row digests and file hashes record both value preservation and
stored-file integrity.

## Initial output contract

| Output | Meaning |
| --- | --- |
| `training-data.parquet` | Every row from silver's `training-candidates.jsonl`, unchanged, including excluded or unreviewed candidates. |
| `model-inputs.parquet` | Every row from silver's `model-inputs.jsonl`, unchanged; an empty typed table is valid. |
| `inputs/profile.json`, `inputs/source-mappings.json`, `inputs/product.schema.json`, `inputs/model-design.json` | Exact copies of the four original chocolate contracts used by silver. |
| `inputs/prices.jsonl` | Unchanged auxiliary price observations and evidence context for the trainer's input checks. |
| `inputs/quality-report.json` | Unchanged silver quality and readiness report. |
| `inputs/family-mappings.json` | Exact accepted family/physical identity decisions when supplied by Silver; historical snapshots without this artifact remain supported. |
| `inputs/silver-manifest.json` | Exact source silver manifest, retaining raw/source versions and processing provenance. |
| `manifest.json` | Gold format/version, source identity, Parquet schema version, row digests, row counts, implementation provenance and managed file hashes. |
| `report.json` | Export and round-trip verification, source versions, candidate/eligible counts and separate storage/statistical readiness. |

Accepted identity mappings travel through the candidate IDs and their copied
decision artifact. The loader checks the artifact against the exact source
Silver manifest, and bulk review preserves it. Gold does not resolve new
identity cases; the raw-to-Silver pipeline supplies those decisions.

The initial versions are `chocolate-gold-1`,
`chocolate-gold-pass-through-1`, `chocolate-gold-arrow-1`,
`chocolate-gold-manifest-1` and `chocolate-gold-report-1`. The gold snapshot has
its own `gold-<24-hex-digest>` identifier. Each training row retains its original
silver `dataset_version` and source versions rather than being relabeled with
the gold storage version.

Gold's primary training data is Parquet; it does not duplicate the candidate
and eligible source JSONL files. The auxiliary JSON files preserve provenance,
contracts and the existing validation context. Original source artifacts and
images remain in raw, and silver remains the full evidence and interpretation
dataset.

The pass-through retains predictor and target values, explicit nulls,
eligibility flags, exclusion reasons, identifiers and version fields, with
evidence routing preserved through the copied source context. It does not
filter candidates, deduplicate again, infer missing
facts, change reviews, impute features, add predictors, normalize prices again,
or choose training/validation splits. The current logical schema, mappings and
model design therefore keep their existing versions.

## Mark Gold rows reviewed at the user's request

The user can explicitly mark every candidate reviewed without revisiting each
source interpretation. Run this separate operation against an existing Gold
snapshot:

```sh
uv run --script scripts/review_chocolate_gold.py \
  --gold-root 'data/gold/chocolate/uk/<gold-version>' \
  --output data/gold/chocolate/uk \
  --reviewed-by task-user \
  --reason 'Bulk marked reviewed at the user request on 2026-10-03'
```

The operation writes a new immutable snapshot using
`chocolate-gold-bulk-review-1` and `chocolate-gold-arrow-2`. It sets top-level
`review_status` to `reviewed` and adds `review_basis: user_instruction` to each
candidate in `training-data.parquet` and each existing eligible row in
`model-inputs.parquet`. The manifest and report record the reviewer, reason, parent Gold
snapshot and `reviewed_counts`. Their `review_provenance` records
`review_status`, `review_basis`, `reviewed_by`, `reason` and
`evidence_validation_performed: false`. The original Silver manifest and
contracts remain copied exactly, and `inputs/parent-gold-manifest.json` retains
the exact parent Gold manifest. Its hash is bound into the new snapshot identity.
Earlier pass-through snapshots using `chocolate-gold-arrow-1` remain loadable.

This status records the user's bulk instruction. It does not claim that each
attribute or price was individually checked against evidence, and it does not
replace Silver's evidence-backed review contract. Predictor and target values,
missingness, listing/variant/family IDs, source versions, row ordering,
`model_eligible` and `exclusion_reasons` remain unchanged. The eligible table
contains the same rows, annotated with the same workflow status; excluded
candidates are not promoted into it. Silver, raw evidence and earlier Gold
snapshots remain unchanged. Copied auxiliary files, including
`inputs/prices.jsonl`, retain their original Silver review states and source
context; the bulk annotation applies to the two primary Parquet training views.

An identical operation with the same input, reviewer, reason and implementation
reuses its verified content-addressed snapshot. The existing model design and
logical product schema keep their versions because their values and
evidence/eligibility meanings are unchanged. The new Arrow version describes
the added Gold workflow annotation only.

## Make every Gold candidate model eligible

The user requested every Gold entity model eligible on 2026-10-03. Apply that
instruction to an exact existing snapshot:

```sh
uv run python -B scripts/make_chocolate_gold_eligible.py \
  --gold-root 'data/gold/chocolate/uk/<parent-gold-version>' \
  --output data/gold/chocolate/uk \
  --authorized-by task-user \
  --reason 'User requested every Gold entity model eligible on 2026-10-03'
```

`chocolate-gold-bulk-eligibility-1` sets `model_eligible: true` and
`exclusion_reasons: []` for every candidate in both `training-data.parquet` and
`model-inputs.parquet`. Both tables contain every candidate in original order.
The operation supports an original pass-through or bulk-reviewed parent and
writes a new immutable sibling snapshot. An identical replay verifies and reuses
that snapshot. Apply bulk review before eligibility if both operations are needed.
An eligibility snapshot cannot be used as another eligibility operation's parent.

The Arrow row contract remains `chocolate-gold-arrow-1`. No predictor, target,
identity, source version or missing value is changed. The analytical contracts
retain their exact source bytes and versions. `inputs/parent-gold/` retains the
complete exact parent snapshot, including its manifest, Parquet tables and
original eligibility/exclusion metadata. The new manifest binds the parent's
SHA-256 and `eligibility_provenance`: authorizing identity, explicit reason,
`eligibility_basis: user_instruction`, `model_eligible: true` and
`evidence_validation_performed: false`. It does not infer evidence review.

The report records new `counts`, original `source_counts`,
`eligibility_preserved: false`, `row_values_preserved: false`,
`analytical_values_preserved: true`, `source_snapshot_preserved: true` and
`release_ready: false`. Copied Silver quality/counts describe the original
Silver decisions; Gold's report describes the promoted views.

`verified_gold` verifies the retained parent, copied auxiliary bytes and both
promoted tables. Even after table hashes are recomputed, changing an analytical
value, omitting a candidate or reordering rows fails comparison with the parent.
The loader returns promoted flags and all candidates in both logical input
views. It keeps the original Silver manifest and exact contracts for source
provenance. Training artifacts must retain the new Gold manifest and its
eligibility provenance. User eligibility authorizes selection; actual target,
identity and numerical validation still apply, including
the selected price-target contract. Source regular-price targets remain missing; current-price training derives its separate target from copied displayed prices.

## Training and readiness

Use the exact snapshot path returned by the builder:

```sh
uv run --script scripts/train_chocolate_model.py \
  --gold-root 'data/gold/chocolate/uk/<gold-version>' \
  --output data/models/chocolate/uk \
  --group bar
```

The trainer pins `numpy==2.2.6` and `pyarrow==21.0.0`. It verifies gold's
manifest, managed bytes and logical Parquet row digests, original silver
provenance and contracts before using the eligible view. The original
`--silver-root` command remains available for compatibility. Supply exactly one
source interface per run.

Historical regular-price models retain the `regular-consumer-price-1` basis:
regular, non-promotional, tax-inclusive consumer selling price, with no fallback
to displayed, promotional, member, multibuy or reference/compare-at amounts or
unconfirmed tax. The current `chocolate-pricing-design-3` represents that price
as regular GBP per 100 g and its natural logarithm. The trainer checks eligible
targets against the matching reviewed regular-price observation and quantity
normalization, and records the price basis in its immutable run artifacts.
Gold preserves those targets exactly; export and bulk review cannot establish
missing price or tax evidence. A separately supported regular price alongside
a promotional offer remains usable, while the promotional amount itself cannot
become the target. Earlier immutable Gold snapshots retain their original
contracts and provenance; a new checked-in model design applies on a rebuild.
Model-run artifacts retain the exact Gold manifest. When the source has the
bulk workflow annotation, the run report also records `gold_review_provenance`
and a successful fitted model retains the same provenance. Its user-instruction
basis remains visible after the loader restores the original analytical input
view.

A verified initial pass-through snapshot reports `gold_ready_for_loading: true`,
`row_values_preserved: true` and `eligibility_preserved: true` even when some or
all candidates fail the current statistical gates. Candidate and eligible counts
and exclusion reasons are preserved; `release_ready` remains false.
`training-data.parquet` retains those candidates so their exclusions and future processing remain
inspectable; the current trainer consumes only `model-inputs.parquet`. It does
not promote candidates into eligible rows. An empty eligible view produces an
immutable readiness report, no fitted coefficients and exit status 2, just as
the silver interface does. Storage integrity, reviewed eligibility, successful
fitting and model release are separate states.
The bulk review status is also separate from eligibility: reviewed Gold rows
with missing targets or required identities still fail the current fitting
contract. Its preservation report distinguishes original analytical values from
the deliberately changed workflow review annotation. For the bulk review
snapshot, `row_values_preserved: true` and
`source_row_values_preserved: true` describe the ordered source analytical
fields after excluding `review_status` and `review_basis`; those two fields are
the intentional metadata changes. The loader verifies the parent manifest and
restores the original logical input view before handing rows to the current
trainer, so a Gold bulk review cannot bypass its eligibility checks.

Family holdout, training-only preprocessing and model diagnostics belong to the
trainer and its immutable run artifacts. Gold creation does not select a split
or claim predictive validity. See the [schema guide](chocolate-schema.md) for
the current experimental fitting contract and outstanding release requirements.

## Independent LightGBM without brand

The [without-brand trainer](analysis/lightgbm-without-brand-implementation.md)
verifies immutable Gold and an explicit local working contract, then freezes
family partitions and fitting-only transforms. Its original regular-price
Gold attempt had zero eligible inputs; synthetic fixture fitting is published
separately. New shared current-price data requires explicit trainer migration
and required feature evidence. Gold eligibility alone cannot establish fitting
or market validity.

## Add processing later

The initial silver-to-gold stage only changes storage. Bulk review changes
workflow metadata and bulk eligibility changes selection under their respective
rule versions. Any further filtering, missing-value
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
user-eligible candidates remain considered, including rows lacking quantities.
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

Use the [independent LightGBM with brand command](chocolate-lightgbm-with-brand.md#run-from-verified-gold) for the proposed supermarket experiment. It verifies immutable Gold, managed bytes, logical row digests, copied contracts and reviewed price observations, then saves model-specific immutable artifacts or a readiness report. It requires an explicit unpublished working contract and source-price window. The rebuilt `gold-4939405fcf8724686f9ee32c` retains 2,134 candidates and zero eligible inputs, so no real LightGBM model can fit. Existing OLS snapshots and Gold bulk review cannot supply missing population, identity or price evidence. Fixture runs retain a synthetic status through artifacts and loaded predictions.

## Published all-eligible training snapshot

The user-authorized all-eligible snapshot `gold-8b897101474becaef946922b` is
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
selects the all-eligible Gold table; eligibility records the user's bulk
selection and does not establish complete model targets or individual evidence
review. Immutable Gold files and the existing Gold publication pin are retained.
Follow [local raw storage](dataset-contracts.md#local-raw-evidence-storage) for
source locations and remote deletion provenance.

## Independent hedonic training handoff

The assigned estimator is runnable with `--model-id hedonic_without_brand --gold-root <immutable-snapshot> --working-contract <local-policy> --group bar`. Prepare the policy with `--prepare-working-contract <local-policy>`. Its default run root is `data/models/chocolate/uk/hedonic_without_brand/`; the [implementation record](analysis/hedonic-without-brand-implementation.md) defines commands, frozen experiments, fitting/calibration/test partitions and verified model artifacts. Gold verification retains managed hashes, logical row digests and original price/contract provenance. This loader does not promote excluded candidates. The historical regular-price Gold inspected in this session has zero eligible rows and lacks three required handoff declarations, so the actual attempt writes an immutable readiness report and returns status 2. Fixture fitting and calibration validate numerical behavior; no real fit or released interval exists.

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

The task-authorized `--verified-gold-candidates` option accepts the user's
confirmed Gold verification and uses `training-data.parquet` directly. It does
not modify or rebuild Gold, or silently rewrite its stored eligibility flags.
Required price, weight and exact-identity values are checked in memory; optional
regression features can be omitted. Model artifacts record the authorization
basis, original flags, missing-value counts and candidate domain membership.
The historical regular-price inspection found zero regular prices/targets and zero exact-variant
IDs in the existing 2,134-row snapshot. The [matched guide](chocolate-matched-retailer.md#task-authorized-gold-verification)
describes the command and concrete current failure.

## Explicit bulk eligibility snapshot loading

`chocolate-gold-bulk-eligibility-1` records the user's instruction that every
Gold entity is model eligible. `scripts/chocolate_gold_eligibility.py` and
`scripts/make_chocolate_gold_eligible.py` preserve the complete source under
`inputs/parent-gold/` and promote candidates into both Parquet views. The rule
changes only `model_eligible` and `exclusion_reasons`; analytical values, nulls
and original parent bytes remain intact. `eligibility_provenance` records the
authorizing user and reason, with evidence validation separately declared.

`verified_gold` dispatches to `verified_eligible_gold`, verifies the embedded
original/reviewed parent, every managed hash, table logical digest, exact
promotion, auxiliary copies and report consistency, then returns promoted rows.
It preserves source Silver provenance while accepting the Gold-specific table
counts. Source content cannot authorize a bulk eligibility action.

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
