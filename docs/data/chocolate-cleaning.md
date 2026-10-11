# Cleanup compatibility interface

`scripts/clean_chocolate_data.py` is a compatibility and diagnostic entry point.
The canonical workflow is combined [Silver](chocolate-silver.md), followed by
immutable [Gold](chocolate-gold.md) for a selected downstream study.

```sh
python3 -B scripts/clean_chocolate_data.py --archive-root /path/to/collections --output /path/to/derived
```

Use the command's `--help` for review inputs and other supported options. Keep
input and output directories separate. Retain raw captures, source identities,
original artifact references and historical observations.

The helper emits derived product, feature and price rows, review queues, quality
reports and reproducibility metadata. Missing or unresolved evidence remains
explicit; valid output does not establish readiness for fitting or release.
Historical compatibility policies remain distinct from a newly selected study.

Actual attribute vocabulary and analytical rules belong to dataset-owned contracts.
Keep source examples, review cases and coverage measurements in ignored local
documents. See [contract ownership](dataset-contracts.md),
[model interfaces](../model/spec.md) and [deduplication](chocolate-deduplication.md).
