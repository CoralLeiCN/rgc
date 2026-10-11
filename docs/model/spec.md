# Model specification

## Inputs and study contract

Train from immutable, verified Gold inputs. The selected dataset-owned design
specifies the target, units, population, features, support rules, transformations
and evaluation protocol. Preserve that exact design and its reference with every
run. A historical admission flag remains provenance and cannot establish current
model readiness on its own.

Targets require supported price and quantity relationships. An explicitly chosen
displayed-price proxy must remain identified as such in the contract and run
limitations. Never silently substitute a different price policy or infer missing
identities to enable fitting.

## Training and evaluation

Split at the identity level required by the design, preserve independent test
inputs, and learn preprocessing only from fitting data. Record support failures,
omitted features and transformations. Compare estimators only with reconciled
populations and compatible targets.

The available implementations include linear, tree-based, hedonic, matched
retailer and median baselines. Their command interfaces are documented in the
[Gold guide](../data/chocolate-gold.md),
[tree trainer guide](../data/chocolate-lightgbm-with-brand.md), and
[matched diagnostic guide](../data/chocolate-matched-retailer.md).
Executable options and selected designs determine supported behavior; an available
trainer does not imply that a research fit or release has been completed.

## Output and release

Retain input hashes, contract bytes, preprocessing, fitted artifacts, predictions,
metrics and relevant support diagnostics. Verify files before loading or serving.
Source claims are not independently verified facts. Feature attribution describes
the fitted model and does not establish causality or willingness to pay.

Keep study-specific coefficients, metrics, comparisons, population counts and
release receipts in ignored research documents or dataset artifacts. Publish
only after the applicable review and authorization; use an immutable reference
for deployed artifacts. See [model maintenance](../model-maintenance.md).
