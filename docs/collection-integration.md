# Web snapshot integration

`scripts/build_web_snapshot.py` prepares server JSON from the immutable source
selected by `apps/web/collection-dataset.json`. It verifies source manifests,
managed bytes, logical records, contracts and identities before emitting assets.
Use its `--help` for supported layers and explicit offline snapshot paths.

```sh
uv run python -B scripts/build_web_snapshot.py
```

Keep generated index, evidence shards and manifest together. Application builds
validate snapshot hashes and function traces. Updating code does not automatically
migrate data. Refresh the immutable reference and derived assets together under
their applicable release procedure.

The browser receives bounded API responses and requests evidence for selected
listings. Source listing and price observation IDs remain distinct. Preserve
known, unknown, conflicting and not-applicable states, and keep draft product
inputs out of observed analyses.

Choose a price using its source observation time and compatible quantity basis;
ambiguous or conflicting evidence must not be silently substituted. Display
coverage and uncertainty from the loaded artifact rather than copying research
counts into this guide. Private documents own actual source inventories and
research results.

See [application setup](../apps/web/README.md),
[architecture](vercel-architecture.md) and [data interfaces](data/spec.md).
