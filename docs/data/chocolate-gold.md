# Immutable Gold preparation

Gold consumes verified Silver and prepares a downstream study under its selected
dataset-owned design. Silver owns source processing, corrections, persistent
identity and profiling. Gold owns comparison groups, targets, features,
eligibility and model-input preparation. Historical eligibility decisions remain
provenance rather than silently becoming current admissions.

```sh
uv run python scripts/build_chocolate_gold.py --silver-root /path/to/silver --output /path/to/gold --offline
```

Use `--help` for historical inputs, inferred exports and explicit review options.
The default standard interface resolves its selected Gold design separately from
Silver's four field contracts. Legacy snapshots retain their exact copied
contracts and original target policy.

## Output and verification

Gold writes immutable Parquet records, training preparation and a manifest with
managed file hashes and provenance. Consumers verify physical bytes and logical
record digests, copied contract agreement and input identities before using data.
Do not edit a historical snapshot to change eligibility or target meaning.

A source displayed price can serve as a proxy only under an explicit selected
policy. Preserve this assumption in the dataset-owned design and run limitations.
Historical policies retain their original meaning. Source quantity and context
requirements still apply.

## Training and publication

Training evaluates the actual target, identity, support and feature requirements.
An eligible row or successful export does not establish model readiness. Retain
input snapshots, contract hashes and explicit exclusions with each run.

The [model specification](../model/spec.md) and
[model maintenance guide](../model-maintenance.md) define the handoff. Publication
uses immutable references and remote-byte verification. Research populations,
source details, fit results and publication receipts remain in private documents
or dataset artifacts. Git holds interfaces and minimal immutable references.

## Loader compatibility versions

The manifest owns exact pins and hashes; definitions remain dataset assets.

- `schemas/chocolate/standard-gold/dataset-contract.json`: `chocolate-processing-schema-1.silver-2`, `chocolate-source-mappings-1.silver-2`, `chocolate-pricing-current-price-design-1.silver-2`.
