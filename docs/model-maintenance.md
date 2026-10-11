# Model artifact maintenance

Model artifacts belong in dataset storage. Git retains a minimal immutable
reference with the repository, revision, paths and hashes required by a loader.
Research inventories, selected populations, fit results and publication receipts
remain in ignored documents or dataset artifacts.

## Publication and consumption

Prepare a run with exact verified inputs, selected contract, preprocessing,
feature order, fitted files and validation diagnostics. Obtain applicable release
authorization, publish an immutable artifact set, verify remote bytes and only
then update consumer references. Preserve unrelated remote files and earlier runs.

Loaders validate hashes, model format, feature order and domain support before
prediction. A successful load does not establish current suitability or statistical
validity. Clearly label fixtures and prototypes and keep them distinct from a
validated research result.

## Retraining

New evidence, selected contracts or implementation changes produce a new run.
Keep the previous input snapshot and record the new run's exact provenance.
Compare results only after reconciling populations, targets and support. The
[model specification](model/spec.md), [Gold interface](data/chocolate-gold.md) and
[dataset guide](data/dataset-contracts.md) own the corresponding boundaries.
