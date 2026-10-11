# Tree model trainer interface

The implementation is `scripts/train_chocolate_lightgbm.py`, with experiment and
input preparation in the associated modules. It consumes verified immutable Gold
and the selected study design. Use the trainer's `--help` for supported options.

```sh
uv run python scripts/train_chocolate_lightgbm.py --help
```

Validate actual input identities, target policy and support before fitting. Keep
preprocessing, feature selection and tuning restricted to fitting partitions;
retain independent evaluation and calibration inputs. Record transformed feature
order, selected settings, model bytes, predictions and input provenance.

The implementation supports tree-based attribution; reconstruction checks do not
establish causal explanations. Report unsupported inputs and model limitations.
Dataset-owned contracts determine feature vocabulary and study assumptions.
Private research documents own chosen populations, metrics and comparisons.
See [model interfaces](../model/spec.md) and [maintenance](../model-maintenance.md).
