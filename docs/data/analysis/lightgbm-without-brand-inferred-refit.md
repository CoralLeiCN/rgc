# LightGBM without brand refit from inferred Gold

Recorded: 3 October 2026. Status: actual experimental fit, published and verified.
Run `model-run-9f56df660a6d46e7cc720002` uses model ID `lightgbm_without_brand` and immutable
format `chocolate-lightgbm-inferred-run-1`. The [machine record](lightgbm-without-brand-inferred-refit.json)
contains hashes, counts, metrics and the absolute local artifact path.

The user requested the inferred-layer refit and then instructed that every
`gold_*` layer always be eligible. The common training adapter implements
`chocolate-gold-training-all-rows-1`: all 2,134 candidates enter training,
including all historically excluded rows. It preserves original flags and
reasons as source provenance. Required numerical values and model grouping
are assessed separately from admission. The original source training table
contains zero eligible inputs; this historical count is recorded without
restricting current training.

## Source and reproduction

The [published inferred Gold](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/812a03a5faaced471a2a20f4c389865ed5675826/gold-inferred/chocolate/uk/gold-inferred-5b539b9c4adbb011a40d7792)
contains 3,743 products, 103 attributes, 2,159 accepted inference decisions and
2,134 price-linked training candidates. The snapshot was copied from the
existing local verified publication cache and checked with the inferred-wrapper
and conventional Gold verifiers. The user's supplied Hugging Face `main` link
was checked after fitting: `main` still resolves to the same immutable revision,
its inferred latest pointer selects this snapshot, and the downloaded published
manifest matches the fitted local bytes. Its manifest SHA-256 is
`18b1d00b301b1ad7ce7190076614e9c76f84cbb99f3c43a5aa8273f9f4123bfe`.
The analytical target is the pinned `current-consumer-price-1` design at
revision `d743cb8dbca37f5241cccd444a16165523304f6c`. Displayed prices serve as
the regular-price proxy; promotion, membership and independently confirmed tax
status have no separate gate. Original price amounts and edible quantities
bind every fitted target to its copied source observation.

```sh
uv sync --locked
python3 -B scripts/fetch_contracts.py --all --offline
uv run python scripts/train_chocolate_model.py \
  --model-id lightgbm_without_brand \
  --gold-root data/gold-inferred/chocolate/uk/gold-inferred-5b539b9c4adbb011a40d7792
```

The default output is
`data/models/chocolate/uk/lightgbm_without_brand/inferred/model-run-9f56df660a6d46e7cc720002/`.
The standalone equivalent is `scripts/refit_chocolate_lightgbm_inferred.py`
with `--gold-inferred-root <snapshot>` and that output parent. Runtime pins
LightGBM 4.6.0, NumPy 2.2.6, SciPy 1.15.3 and PyArrow 21.0.0. Source and model
artifacts are ignored caches; Git retains this small result record and code.

## Experimental preparation and fit

The predeclared exploratory domain is Waitrose/Ocado bars with an established
family relationship, actual positive edible pack mass and positive GBP displayed
price. It yields 55 Waitrose observations in 15 families. Numerical or domain
filter counts overlap: 1,732 candidates lack a family relationship, 1,503 lack
usable mass, 1,334 fall outside bars and 1,137 fall outside Waitrose/Ocado.
No seller rows are merged and unresolved family IDs are not replaced by
seller IDs or invented groups.

Brand never enters preprocessing, fitting or tuning matrices. Core features
are log edible pack weight, native retailer and native chocolate type. The
enriched candidate adds nuts, vegan, Fairtrade and organic claims. Unknown or
conflict cells remain null and use native missing routes; unseen known holdout
categories route as missing and receive an explicit support flag. Cocoa
percentage is omitted because its comparable basis is absent. Recipe and
single-pack status remain unestablished. This is an independent local research
policy, `chocolate-lightgbm-inferred-exploration-1`; it does not claim alignment
with the proposed full shared supermarket feature contract.

Family order uses SHA-256 of seed 1729, LF and family ID. The first rounded
20% are final testing families; the rest fit. This freezes 40 fitting rows
in 12 families and 15 testing rows in three families. There is no calibration
partition. Three inner fitting-family folds use separate category maps and
family weights recomputed in each fold. Search compares core and enriched
features with the existing 15-leaf/depth-4/minimum-20-row configuration and
7-leaf/depth-3 configurations with minimum five or ten rows and L2 of two.
All use learning rate 0.03, squared log-price loss, at most 2,000 trees and
50-round early stopping. Family-weighted GBP/100 g MAE selects the candidate;
its median fold tree count is frozen before the final fit. Holdout outcomes
never select features, parameters or tree count.

The winner uses the three core features and 84 trees. Retailer is constant
in this sample and cannot establish a retailer comparison. Predictions are
geometric price benchmarks obtained by exponentiating raw log output without
mean correction.

## Final holdout results

| Metric | All 15 testing rows across three families |
| --- | ---: |
| Family-weighted unit MAE | GBP 0.542656 per 100 g |
| Family-weighted pack MAE | GBP 0.473168 |
| Weighted median absolute percentage error | 14.6872% |
| Signed unit bias | GBP +0.106084 per 100 g |
| Signed pack bias | GBP +0.156236 |
| Listing-weighted unit MAE | GBP 0.450769 per 100 g |
| Supported rows | 14 of 15 |
| Native TreeSHAP maximum reconstruction error | 1.11e-15 log units |

The primary metrics include every holdout row. The separate supported-only
unit MAE is GBP 0.644430 per 100 g; it cannot replace the primary score.
Native TreeSHAP explains raw log output with stored path counts and reconstructs
each prediction. Artifacts include selected rows and their original evidence,
family assignments, all six tuning candidates, fold preprocessing/weights,
source and target manifests, complete inferred inputs, booster, model,
preprocessing, report, evaluation and fitting/testing predictions. `load_run`
verifies managed file hashes, model/booster/preprocessing/experiment agreement,
identity and tree count before returning the native booster.

## Limits and verification

All Gold candidates are eligible, but many still lack numerical targets,
edible pack mass or established family relationships. Restricting to the
available families creates selection bias. This fit has no Ocado observations,
no established single-pack or recipe basis, no calibrated intervals, and only
three testing families. The result does not establish reliable market accuracy,
future prices, unseen-brand performance or a prediction champion. The web
serving reference continues to select its disclosed synthetic fixture.

Meaningful tests cover admission despite historical exclusion flags, immutable
source preservation, null preservation, deterministic family partitions,
outcome/brand independence, fitting-only category maps and ranges, missing and
unseen categories, native TreeSHAP, reload equivalence and tamper rejection.
The [lifecycle plan](../../lifecycle/plan.md) records final verification status.

## Verified model publication

The user requested publication after the local fit. The [published model](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/88b08aeada37e228fcd80334b5abddd768da6968/model/lightgbm_without_brand/model-run-9f56df660a6d46e7cc720002)
is stored under `model/lightgbm_without_brand/model-run-9f56df660a6d46e7cc720002/`
at immutable dataset commit `88b08aeada37e228fcd80334b5abddd768da6968`. The
[publication receipt](lightgbm-without-brand-inferred-model-publication.json)
records all 16 downloaded and verified file hashes, totaling 313,788 bytes.
All 186 prior dataset paths and objects were preserved.

The published inventory contains the frozen booster and model, preprocessing,
tuning, experiment, reports, fitting/testing predictions and signed attributions,
target/admission metadata, original run manifest, reproduction command and a
README with a checked native inference example. The publication manifest
inventories these model files; `source-run-manifest.json` preserves the complete
original local inventory. Original training inputs and selected-row evidence
remain available through their existing immutable source dataset reference.

The downloaded model passes the verified loader, reproduces all 15 saved
holdout predictions exactly, and runs the published inference example.
`real_data_fitted` is true, while `calibrated` and `release_ready` remain false.
Publication does not select a prediction champion or establish market accuracy.
