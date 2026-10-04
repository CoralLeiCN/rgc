# Synthetic LightGBM price demo

Recorded: 3 October 2026. The user authorized using the published synthetic
fixture in the product configurator after its training status was verified.
This interface demonstrates price prediction and field attribution; it does
not establish accuracy on UK product prices.

## Immutable model and preparation

The [web model reference](../../../apps/web/pricing-model.json) pins dataset
`CoralLeiCN/rgc-collections`, revision
`06680d7248ccc4487726b9a97e59aa8f586fb54e`, and run
`model-run-643f7148c9f44c42e5f42212` under
`model/lightgbm_without_brand/fixtures/`. It records SHA-256 and byte lengths for
the complete model and run manifest. The original
[publication receipt](lightgbm-without-brand-model-publication.json) retains the
larger training/replay inventory.

Run `python3 -B scripts/fetch_web_pricing_model.py` from the repository root
before development or deployment. `--offline` verifies existing cached bytes.
The downloader writes only ignored `apps/web/model-cache/`; generated boosters
and training artifacts remain dataset owned. `npm run prepare:model` provides
Node preparation for clean Vercel builds, downloading absent files with bounded
responses and verifying both hashes before writing. Prebuild invokes it;
cached builds verify existing bytes offline and corrupt files fail. Both
artifacts enter the prediction trace. Requests never download models, train
or invoke Python.

Runtime verifies source hashes, manifest/run identity, the embedded booster
digest, synthetic status, target basis, exact feature order, booster format and
tree count. The reader admits only this five-field regression fixture. A new
model needs its own verified reference and serving compatibility review; a
moving `main` URL cannot select a replacement implicitly.

## Inputs and output

`POST /api/predict-price` accepts JSON with these keys:

| Key | Supported value |
| --- | --- |
| `scope` | User-confirmed `single_pack_chocolate_bar` |
| `quantity.total_edible_weight_g` | Finite number between 50 and 150 g, inclusive |
| `composition.chocolate_type` | `dark`, `milk`, `white` |
| `composition.recipe_class` | `plain`, `inclusion`, `filled` |
| `composition.nuts_presence` | `present`, `explicitly_absent`, `unknown` |
| `identity.retailer` | `Waitrose`, `Ocado` |

The fixture's frozen preprocessing owns ranges, category codes and admitted
retailer/type/recipe combinations. Edible weight uses its natural logarithm.
Proposed price, brand, names and other schema traits are rejected by this API.
The form shares edible weight, type and retailer with the draft. Recipe and nuts
evidence selections remain local scenario inputs. Legacy schema `absent` is not
silently converted into model `explicitly_absent`; the user reviews it. Changing
source nuts evidence clears a previous model selection. Listing copy/reset clears
scope confirmation, recipe and nuts selections and stale results.

Extraction still requires a configured provider, and reviewed extracted values
may supply compatible draft fields. Recipe class remains an explicit model
selection because it is absent from the historical extraction schema. The
single bar pack confirmation declares scenario scope; it does not verify product
facts or eligibility. Model inputs are never saved into Silver or Gold.

Responses report fixture/run/revision identity, the historical
`regular-consumer-price-1` target basis, geometric GBP/100 g, converted GBP/pack,
model reference, raw field SHAP, signed price allocations, family totals,
reconstruction errors and reached-leaf support. Intervals are `null`: fixture
calibration does not establish uncertainty for real products. The UI describes
the generated training data and illustrative estimates, and lists all excluded
schema fields as not modeled. The separate “SYNTHETIC DEMO” badge was removed
at the user's request.
The model excludes cocoa percentage, certifications and brand.

Requests are bounded to 4 KiB; malformed input returns 400, excess bytes 413,
foreign origins 403, unsupported products 422 and missing/corrupt model files
503. Responses use `Cache-Control: no-store`; no input persistence occurs.
Changed model inputs hide old results immediately and cancel pending requests;
proposed-price edits do not enter prediction or invalidate it.

## Attribution convention and verification

Node evaluates the original LightGBM v4 booster directly. Exact subset
enumeration over 32 coalitions computes the five-feature stored-path SHAP game.
At unspecified splits, branch probability uses stored observation counts, with
repeated splits on a feature receiving the same coalition membership. Native
categorical bitsets and frozen numeric thresholds retain original routing.
Stored leaf values already contain shrinkage; it is not applied again.
The implementation is verified against LightGBM 4.6.0
`Booster.predict(pred_contrib=True)`. It uses no approximation or supplied
background; it does not invoke the native Python runtime on web requests.

Raw contributions sum in log GBP/100 g. The displayed pounds and final-price
percentages follow [specification section 5.2.1](../../model/spec.md#521-trait-and-trait-family-percentages-of-predicted-price):
with raw prediction `L`, reference `b`, and deviation `d=L-b`, use
`k=-expm1(-d)/d` (or 1 at zero), field share `100*k*phi`, and reference share
`100*exp(-d)`. Pounds equal the share multiplied by predicted pack price.
Reference plus signed field/family shares reconciles to 100% before rounding;
reference pounds plus field pounds reconstructs the pack estimate. Negative
values and a reference exceeding 100% remain valid. The UI displays both raw
SHAP and the allocation convention. Allocations are not ingredient costs,
causal effects or SHAP computed directly on currency output.

Quantity belongs to the quantity display family; type, recipe and nuts belong
to composition; retailer belongs to selling context. These presentation groups
do not modify the authoritative training contracts or product identity families.

`uv run pytest scripts/tests/test_web_pricing.py` compares raw predictions,
reference and every individual SHAP value across 324 supported combinations,
including categorical levels, numeric boundaries and interior weights. It also
checks pack conversion, signed/family reconciliation, cancellation, near-zero
deviation, out-of-domain inputs, price leakage, body/origin validation and
missing/corrupt artifact failures. Tests use the downloaded published fixture
and native LightGBM, with no new training run. Prepare the cache and npm
dependencies before these checks; absent prerequisites cause explicit skips.

The existing protected hosted preview predates this feature. Local build and
browser proof are recorded in the [lifecycle plan](../../lifecycle/plan.md).
