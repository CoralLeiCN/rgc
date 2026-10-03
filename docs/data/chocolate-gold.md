# UK chocolate gold training data

Gold is the canonical Parquet training interface downstream of the combined
[silver dataset](chocolate-silver.md). Its initial pipeline passes silver's
existing training views through without semantic changes. It packages verified,
typed training data; it does not establish that every candidate is eligible for
the current model or that a statistically supported model can be fitted.
An optional bulk review operation records a user instruction as a separate Gold
workflow status in a new snapshot. It preserves Silver's source values and
eligibility decisions.

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

Every pricing model retains the finalized `regular-consumer-price-1` basis:
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

## Add processing later

The initial silver-to-gold stage only changes storage. The optional bulk review
operation changes workflow metadata under its own version. Any future filtering, missing-value
handling, feature preparation or eligibility change must be explicitly designed
and versioned, documented with its evidence and tested. Preserve the original
silver input and earlier gold snapshots; write a new immutable gold snapshot
with its own processing provenance. Changing storage cannot silently relax the
reviewed-input contract or manufacture facts from missing evidence.

## Integration with dataset-owned contracts

The locked pytest environment includes NumPy 2.2.6 and PyArrow 21.0.0 for the numerical and Parquet checks. Silver resolves immutable dataset pins or explicit custom working-contract roots before producing its snapshot. Gold copies the exact resolved contracts and their hashes, rather than resolving newer contracts at load time. A prepared schema/design release cannot change an existing Gold snapshot. The [published release](analysis/gold-modeling-contract-release.md) records the verified immutable contract revision for the updated Silver defaults; verified existing Gold remains self-contained.

## LightGBM with brand trainer

Use the [independent LightGBM with brand command](chocolate-lightgbm-with-brand.md#run-from-verified-gold) for the proposed supermarket experiment. It verifies immutable Gold, managed bytes, logical row digests, copied contracts and reviewed price observations, then saves model-specific immutable artifacts or a readiness report. It requires an explicit unpublished working contract and source-price window. The rebuilt `gold-4939405fcf8724686f9ee32c` retains 2,134 candidates and zero eligible inputs, so no real LightGBM model can fit. Existing OLS snapshots and Gold bulk review cannot supply missing population, identity or price evidence. Fixture runs retain a synthetic status through artifacts and loaded predictions.
