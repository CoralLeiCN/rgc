# Processing profile validation and release

## Supported contracts

The portable category-processing runtime requires Python 3.9 or later and five
aligned contracts. A generated working profile contains their full local bytes;
dataset references instead pin immutable published files and hashes.

All five files agree on the schema version. The profile and pipeline agree on
category and market; the validator uses the same constants and complete catalog.
Mappings and selected predictors reference declared attributes. Model quantity,
normalization base and recipe quantity agree. Define the initial schema, mapping,
pipeline and model-design version identifiers explicitly.

The generator supports `string`, `number`, `integer`, `boolean`, `enum` and
`string_list`. Attributes explicitly declare type, unit including null, scope
and standardization rule; enums need allowed values. Supported scopes are
product, ingredient, brand, packaging, packaging_component and observation.
Values also carry qualifier, evidence, method and review status.
Unknown, conflict and not-applicable values remain null; known values satisfy
their declared type, bounds and vocabulary. Review status is independent of
whether a value is known.

Raw directories use collection-normalized category/market slugs, with exact
safe-name fallback for compatible producers. Captured envelope values must still
match the profile exactly. Directory normalization preserves original captures
and seller UID inputs.

The loader checks its supported typed validator template, not arbitrary JSON
Schema. Descriptive rule names do not implement new parsing algorithms.
`init-profile` generates a structured adapter recipe. Structured fields require
capture-root JSON pointers and explicit units or conversions; it does not parse
arbitrary prose or perform OCR. Configuring an unobserved field cannot establish
its value. Source amount precision, currency and observed quantity must be
explicit. Missing counts remain unknown; shipping mass is not edible mass.

The portable model preparation contract currently requires
`regular-consumer-price-1` and reviewed regular, non-promotional,
consumer-tax-inclusive prices, with reject fallback. It does not convert taxes,
currencies or displayed prices into that target. The repository's separate
chocolate `current-consumer-price-1` study retains its explicit authorization and
implementation; it is not silently reinterpreted by this portable generator.
If a requested study needs another basis, retain its design and document the
unsupported runtime work. Do not alter the user's target to make generation pass.

## Validation

Use the initial schema catalog and its evidence as inputs to contract assembly.
Research and semantic checks belong to schema creation. This reference owns
executable contract validation, isolated processing checks and release preparation.
Interpret supported runtime types and target policies as generation constraints,
not a reason to replace the agreed schema or study design.

When implementation is in scope, locate the plugin runtime before running
commands. The complete plugin supplies `cli.py`; separately installed instructions
need that runtime in the user's project or installed plugin. If it is absent,
record contract generation and processing as pending.

`init-profile` validates all five contracts before creating the output and refuses
to overwrite any existing directory. Retain the exact input definition and
generated hashes. Exercise the definition example only as a software fixture;
its source mappings do not establish facts for another study.

When local processing validation is authorized:

```text
python3 -B <plugin-root>/cli.py process --archive-root <collections-root> --profile <working-profile> --output <isolated-silver>
python3 -B <plugin-root>/cli.py summarize --silver-root <isolated-silver> --output <review-packet>
```

Inspect quality, review, discovery and mapping artifacts and resolve original
evidence pointers. Test real distinctions: aliases with equivalent meanings,
unsupported units, missing evidence, minimum/component declarations, malformed
values and conflicting captures. A successful process does not establish full
extraction coverage, semantic correctness or model readiness.

For initial validation, inspect field coverage, values, scopes, qualifiers,
conflicts, seller/source counts and model exclusions. Preserve
seller UIDs, aliases, raw evidence and immutable earlier data/model snapshots.
Use meaningful focused tests for executable changes; finish the project's
required documentation and lint checks. Avoid tests that only repeat wording.

## Publication

For the RGC package, publish analytical payloads to the authoritative
`CoralLeiCN/rgc-collections` dataset and keep immutable revision/hash manifests in
Git. Never modify verified contract caches or copied snapshot contracts in place.
Existing profile meanings and historical price bases retain their versions.

Within authorized profile assembly, the calling agent can resolve supported
implementation decisions from the agreed schema and evidence and generate initial
contracts without individual field approval. For a new schema or its generated data, this package requires a detailed
release summary before a Hugging Face commit/upload and authorization of that
exact release. Finish initial contracts, generated data and checks first. The summary
includes initial contract versions and fields, original evidence and rationale,
mapping/unit/scope/price/predictor decisions, initial coverage and readiness,
checks and gaps, and exact repository/base/target revision, files and hashes.
Explain preservation of original captures and stable seller identities.
For another project, follow its established publication policy and current user
authorization. This skill provides guidance; it implements no uploader or gate.
