# Analytical contract resolution

Attribute definitions, types, units, vocabularies, aliases, validators and model
designs are owned by the dataset. Do not copy their field catalog or actual
research examples into Git documentation. Git retains small immutable references:

- [Established interface](../../schemas/chocolate/dataset-contract.json)
- [Target-policy overlay](../../schemas/chocolate/current-price/dataset-contract.json)

The historical filenames identify implementation compatibility paths. Use
[contract resolution](dataset-contracts.md) to materialize verified bodies in
ignored caches. Keep those bodies fixed during a processing run, and copy exact
contracts and provenance into each immutable output snapshot.

## Use and maintenance

The [Silver builder](chocolate-silver.md) applies source mappings and preserves
known, unknown, conflict and not-applicable states with evidence. Review schema
meaning against original source examples and counterexamples. Keep the actual
case record and proposal in ignored local documents.

An initial proposal does not establish a tested parser or executable contract.
Accepted changes require aligned schema, mappings, validator, recipe and selected
model-design versions, followed by validation and the
[dataset release review](../decisions/agent-led-schema-maintenance.md).

Use `scripts/analyze_chocolate_schema.py --help` to inspect the profiling interface.
Generated frequency tables, field coverage and source examples are private
research artifacts. A profile report does not establish complete extraction.

## Loader compatibility versions

These identifiers document resolver compatibility; the manifests own exact pins and file hashes.

- `schemas/chocolate/dataset-contract.json`: `chocolate-schema-1`, `chocolate-source-mappings-2`, `chocolate-pricing-design-3`.
- `schemas/chocolate/current-price/dataset-contract.json`: `chocolate-schema-1`, `chocolate-source-mappings-2`, `chocolate-pricing-current-price-design-1`.
