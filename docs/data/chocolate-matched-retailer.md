# Matched comparison interface

The matched diagnostic is implemented in `scripts/chocolate_matched_retailer.py`
and exposed by `scripts/train_chocolate_model.py` through the `matched_retailer`
selector. Use both commands' `--help` for supported preparation and fitting options.

A matched comparison requires evidence for exact physical variant identity,
compatible price context and actual target quantities. A broad family identity
does not prove an exact match. Keep separate seller observations and retain
unsupported, ambiguous or contradictory cases as explicit exclusions.

Review bundles preserve original evidence, pointers and checksums. The run verifies
those files, binds them to the selected immutable Gold snapshot and retains its
exact working contract. Local prepared designs remain unpublished until an
approved dataset release adopts them.

Study-specific matching windows, seller selections, population decisions and
results belong in dataset contracts and ignored research documents. See
[Gold preparation](chocolate-gold.md), [model interfaces](../model/spec.md) and
[contract release review](../decisions/agent-led-schema-maintenance.md).
