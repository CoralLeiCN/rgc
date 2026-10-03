# Project implementation plan

Status: raw and combined silver architecture, chocolate schema, model-preparation
components, documentation maintenance and the self-contained portable processing
package implemented and verified. Evidence
review, extraction evaluation and model fitting/validation remain outstanding.

Canonical requirements: [specification](../spec.md),
[silver responsibilities](../chocolate-silver.md),
[chocolate schema](../chocolate-schema.md),
[portable category processing](../category-processing.md), and
[documentation policy](../documentation-policy.md).

## Implemented foundation

The category-research plugin preserves broad raw records, original source/image
artifacts, and append-only captures. Exact seller-listing deduplication and
schema standardization are shared processing components now combined in silver.
The earlier cleanup and standalone component CLIs remain compatibility and
diagnostic helpers. Public text-evidence export is implemented separately.
Native portability across multiple agent harnesses, complete feature
evaluation, and a validated pricing model remain outstanding.

## Current work and files

| Work | Files | Status |
| --- | --- | --- |
| Define typed chocolate attributes, vocabularies, units, evidence states, and record shape. | `schemas/chocolate/profile.json`, `schemas/chocolate/product.schema.json` | Implemented initial schema; extraction review remains. |
| Define source-mapping and model-training/interpretation contracts. | `schemas/chocolate/source-mappings.json`, `schemas/chocolate/model-design.json`, `scripts/chocolate_model.py` | Implemented contracts and preparation helpers; no regression fitted. |
| Combine raw verification, exact seller deduplication, standardization, price normalization and review/eligibility in silver. | `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, shared processing components, `scripts/tests/test_silver.py` | Implemented; real build, preservation, contracts, hashes and complete test verification passed. |
| Document raw/silver responsibilities, schema and training boundaries, canonical commands and compatibility helpers. | `docs/intention.md`, `docs/spec.md`, `docs/chocolate-silver.md`, `docs/chocolate-schema.md`, compatibility guides, `README`, lifecycle views | Implemented; canonical commands, contract ownership and documentation checks verified. |
| Enforce same-change documentation maintenance including silver behavior. | `AGENTS.md`, `docs/documentation-policy.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml`, and tests | Implemented; silver guide included in required ownership and drift checks. |
| Package the whole processing methodology with chocolate/coffee profiles, stable seller identity and caller-harness skill. | `plugins/category-processing/`, `docs/category-processing.md` | Implemented; bundled tests, skill validation, isolated copied-package and independent workflow checks passed. |
| Record capture/rules fingerprints, grouped mapping gaps and explicit mapping-maintenance decisions. | Processing ledger, batch/summary helpers, skill references | Implemented full-rebuild ledger/batches and current-task guidance; no dispatcher, incremental cache or automatic migration. |
| Prepare generic family-held-out model inputs and frozen training-only encoders. | Portable model helpers and `prepare-model` CLI | Implemented; positive reviewed preparation and exclusion/failure gates verified, no regression fitted. |
| Reject typed profile/validator drift and retain category-valid values outside selected model domains. | Portable profile loader, both standardization pipelines and regression tests | Implemented and verified by final prelanding suite/corpus checks. Supported validator template is explicit, not arbitrary JSON Schema execution. |

## Risks and controls

Seller identity must remain distinct from brand identity. Schema expansion must
preserve raw evidence and must not make unsupported fields appear known. Source
claims do not independently verify certification, origins, or quality. Price
normalization requires edible mass from the same observation, with explicit
promotion, currency, tax, and time context. Active predictor reviews must also
cite that observation's capture rather than borrowing later recipes or claims.
Keep candidate records separate from reviewed eligible training rows. New
source-role mappings and extractor support need evidence review; unknown sellers
remain retained and excluded from the initial model. Group related designs
across seller records in validation to avoid repeated-product leakage.

## Proof

Portable package verification uses its own tests, copied-package checks, a
structured second-category fixture, evidence-preservation checks and the
documentation guard. Prior chocolate-specific verification below does not imply
native plugin compatibility or portable package verification.

```sh
python3 -B -m unittest discover -s plugins/category-processing/tests -v
python3 -B scripts/check_documentation.py
```

Test the copied processing directory with isolated Python execution and no
repository sibling imports. Verify stable seller UIDs across alias/capture
changes, exact deduplication without shop merging, ledger invalidation after
profile changes, grouped evidence batches, review gates and positive/failing
model preparation. Native installation in multiple harnesses remains unverified.

Portable verification completed on 2026-10-03: all 143 repository script tests,
13 collection-plugin tests and 50 processing-plugin tests passed (206 total).
The skill passed `quick_validate.py` using an existing Python environment.
Independent testing of a copied package with isolated Python verified raw
preservation, seller identity, grouped evidence, review examples and mapping/review
fingerprint changes. Reviewed coffee preparation produced four eligible
observations in two families, with two training and two validation rows; families
stayed together and regression/release flags stayed false.

The initial portable chocolate build, `silver-39e4c5cc1df5299d00ef2898`, completed
with `complete_snapshot` and no
archive/extraction errors. All 26 managed output hashes and exact bytes of all
five copied contracts were verified. Every retained capture matched its original
immutable history. A second full build reproduced the same report/manifest and
output hashes and classified all captures unchanged. Source archives were not
written. The corpus verification used a temporary output; the documented command
builds a persistent snapshot when requested.

The real data still has unsupported field mappings and evidence batches, and no
eligible reviewed model inputs. Those gaps are retained in quality/review/batch
artifacts; successful integrity/reproducibility verification does not establish
extraction completeness or pricing insights. Native installation across harnesses,
incremental caching and fitted-model validation remain outstanding. Documentation
structure/change-coverage checks and `git diff --check` passed.

Prelanding verification on 2026-10-03 followed the typed-contract consistency and
model-domain fixes. All 147 repository script tests, 64 processing-plugin tests
and 13 collection-plugin tests passed (224 total). Checks cover nullable/known
type/unit/vocabulary/bounds drift, unsupported value constraints, portable
category/market and model compatibility, and retaining category-valid values with
model-domain candidate exclusions in both pipelines.

The current portable chocolate build, `silver-622d46124487f0ab7683c49e`, completed
with `complete_snapshot` and no archive/extraction errors. Every retained capture
again matched its original immutable history; all 26 managed hashes were
verified, and a repeat build reproduced the identical manifest. Unsupported
field mappings and evidence batches remain visible in generated reports, with no
eligible reviewed model inputs. This updates implementation proof without
migrating the earlier dataset or establishing fitted-model readiness.

Run from the repository root:

```sh
python3 -B scripts/build_chocolate_silver.py \
  --archive-root data/collections \
  --output data/silver/chocolate/uk
python3 -B scripts/check_documentation.py
python3 -B -m unittest discover -s scripts/tests -v
python3 -B -m unittest discover -s plugins/category-research/tests -v
```

The build must verify raw index/history consistency, preserve original raw
bytes and unchanged capture objects, deduplicate exact seller listings without
merging shops, validate schema records, retain aliases and source listings,
normalize supported observations, emit deterministic versioned outputs, report
unresolved fields/eligibility and preserve brand/retail/unknown partitions.
The silver manifest must remain resolvable without temporary processing stages.
The documentation check must pass with canonical contracts and lifecycle views
synchronized. Relevant behavioral tests
must cover preservation, standardization semantics, eligibility, and drift.

Build-specific counts and readiness are owned by the generated manifest and
quality report. Current raw-derived facts are unreviewed and tax basis is not
established; a schema build does not establish model readiness or supported
pricing estimates.

Chocolate-specific verification completed on 2026-10-03: the real silver build finished with
`complete_snapshot`, no archive/extraction errors, and all product rows passing
the runtime validator. Every retained original capture matched its immutable
history. All 22 managed output hashes, current implementation hashes and exact
original bytes of all four copied contracts were verified. All 140 script tests
and 13 collection-plugin tests passed (153 total), covering combined processing, preservation,
integrity/identity drift, review gates, historical evidence, model preparation,
path safeguards and documentation drift. The documentation guard and
`git diff --check` passed.
A repeated real build reproduced the identical silver dataset version, manifest
and all managed output hashes.

Initial `model-inputs.jsonl` remains empty and `release_ready` remains false.
`complete_snapshot` establishes accepted input consistency rather than complete
extraction or model readiness. Dataset counts and versions remain owned by the
silver quality report and manifest.

## Remaining work after this delivery

The [portable capture-to-mapping loop](../category-processing.md) now supplies
input-plus-processing fingerprints, grouped evidenced gaps and skill-guided
triage/diffs/tests/impact review, with package verification passed. Current
execution rebuilds all accepted captures after version changes;
incremental caches, automatic harness dispatch/scheduling and selective migrations
remain future. Preserve seller identities and immutable model/data snapshots.
Unknown/missing evidence is not a reason to add taxonomy values.

Extend extraction only with source-supported mappings, review identity/family,
study scope, comparison groups, quantity and price basis, evaluate classification
on a reviewed sample, and resolve coverage/release thresholds. Fit and validate
a pricing model only after those gates pass; then deliver supported insights and
new-product price testing. Value-for-money scoring remains deferred.
