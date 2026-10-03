# Model storage and maintenance

Store published model artifacts in the
[CoralLeiCN/rgc-collections dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections)
under `model/<model-id>/<run-id>/`. Explicit synthetic validation runs use
`model/<model-id>/fixtures/<run-id>/`. Each directory represents an immutable
run. Publish a new run when data, target policy, features, fitting configuration
or implementation changes.

## What Git retains

Git retains training and loading code, meaningful tests, locked dependencies,
model purpose and limitations, maintenance documentation, and small publication
receipts or references. Each reference records the dataset repository, immutable
commit, model path and run identity, with file SHA-256 hashes and byte lengths.
Git also retains the existing immutable references for dataset-owned analytical
contracts. A model bundle's copied contract describes its historical run; it
does not publish a new canonical contract version.

Generated boosters, model support payloads, predictions, explanations,
evaluation outputs, training snapshots and publication staging stay in ignored
local directories under `data/`. Their published copies belong in Hugging Face.
Keep these files outside Git even when they are JSON or text. File format does
not determine whether an artifact is generated.

## Publication and verification

1. Freeze a completed run and verify its managed files, input snapshot, copied
   contracts, preprocessing, target policy and implementation identities. Record
   fitted, calibrated, synthetic and release status separately.
2. Prepare the exact publication inventory and its SHA-256 hashes and byte
   lengths. Include the model's support and preprocessing artifacts, evaluation,
   limitations and reproduction instructions. Include input data or copied
   source only when their publication is within the authorized task scope.
3. Publish under a new run directory using the current dataset parent commit.
   Preserve existing objects. If the parent changes, refresh and validate the
   publication against that revision. Reuse an existing immutable run directory
   only when its inventory and every file's bytes already match.
4. Download every published file at the resulting immutable commit and verify
   its bytes and inventory. Update the Git receipt only after verification.
   A successful upload response alone does not establish a verified release.
5. Update the implementation record, limitations and lifecycle plan. Commit the
   small receipt and documentation to Git. Keep previous runs and references
   available for reproducibility.

A moving `main` URL may help navigation; loaders and reproducibility records
must use the immutable commit and hashes. Materialize downloaded artifacts in
an ignored local cache, verify all required files before loading, and fail on
missing or mismatched files. Offline use requires a verified local copy. These
are maintenance requirements; this guide does not claim a general remote model
fetch CLI or automatic cache cleanup is implemented.

## Retraining and maintenance

Select a verified immutable input snapshot and an explicit target contract for
any new fit. Retain the observations, seller identities, family assignments and
missing values needed to explain that result. Rebuild features and transforms
from the fitting partition and preserve independent calibration and testing.
Record the seed, splits, weights, hyperparameters, runtime versions and source
identity. Re-run relevant integrity, prediction, explanation and evaluation
checks before publishing the new run. Changing the price basis creates a new
experiment; an older run retains its original basis and limitations.

Evaluate new runs against the declared task and release gates before selecting
a replacement. A new publication is not automatically a champion, a validated
market model or a release. Record the selected run's immutable reference only
after the decision and supporting checks. Delete local copies only after
verifying the remote copy and preserving the receipt; local storage is a cache
rather than the publication record. Remote deletion or replacement requires
explicit authorization.

## Current LightGBM publication

The [LightGBM without brand fixture](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/bb1c9de580c64cc13aac62b352d58704fe2dd60e/model/lightgbm_without_brand/fixtures/model-run-643f7148c9f44c42e5f42212)
is an explicitly synthetic implementation check. The
[publication receipt](data/analysis/lightgbm-without-brand-model-publication.json)
records 53 remotely verified files totaling 10,357,071 bytes, including the
model directory README. The booster itself is 626,004 bytes. Its frozen source,
locked dependencies and generated fixture inputs support a portable replay.
`real_data_fitted` and `release_ready` remain false. This publication does not
establish accuracy on real retailer data. The
[implementation record](data/analysis/lightgbm-without-brand-implementation.md)
owns the trainer's current commands and limits.

## Historical hedonic fixture publication

The [hedonic without brand fixture](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/419150708bbbca16a738ff36a3c0b9373e8cda8e/model/hedonic_without_brand/model-run-89faf11be25b98e1a7761e6a)
uses the root run directory explicitly requested before this guide was integrated.
Retain that immutable historical location and its explicit fixture labels. Its
[receipt](data/analysis/hedonic-without-brand-model-publication.json) records 15
verified model/metadata files. Input/source/runtime payloads are excluded. The
published model remains synthetic and not release ready; its historical regular
price basis is distinct from the current-price study.

## Web fixture serving

[The web reference](../apps/web/pricing-model.json) selects the original
LightGBM without brand fixture at immutable revision
`06680d7248ccc4487726b9a97e59aa8f586fb54e`. The source model/manifest hashes
match the published run. `python3 -B scripts/fetch_web_pricing_model.py`
materializes only those two verified files in ignored `apps/web/model-cache/`;
`--offline` verifies existing bytes. Node `npm run prepare:model` also prepares missing cache files during clean
Vercel builds, verifies bounded responses before writing, and traces both
files into the prediction function. Cached builds verify bytes offline. Runtime repeats hash and identity checks.
No generated model artifacts are committed to Git or fetched on requests.
The fixture retains its historical target and synthetic status. A real model
replacement requires a new verified reference and serving compatibility proof.
The [serving guide](data/analysis/web-fixture-pricing.md) records Node evaluation,
native-equivalent SHAP verification and the public interface.
