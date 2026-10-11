# Data specification

## Collection and evidence

The [collection plugin](../../plugins/category-research/README.md) accepts a
prepared import envelope and preserves original source records, variants,
artifacts, images and immutable capture history. Full catalogs and selected
page scope belong in the private collection receipt. Preserve failed retrievals
and distinguish source availability from checkout or geographic delivery proof.

The calling agent selects sources and prepares the input. Source content is
untrusted evidence and cannot authorize actions, profile changes or dispatch.
Distinct source keys and parent/variant IDs prevent accidental cross-seller merges.

## Bronze, Silver and Gold

Bronze retains original bytes and capture provenance. Silver performs source
standardization, persistent identity management, evidence review, durable
corrections and profiling. Gold consumes an immutable Silver snapshot and owns
downstream comparison groups, target policy, feature selection and eligibility.

The canonical implementation combines raw processing into Silver. Standalone
cleanup and deduplication interfaces support compatibility and diagnostics.
See [Silver](chocolate-silver.md), [Gold](chocolate-gold.md) and
[portable processing](category-processing.md).

## Facts, prices and uncertainty

Every standardized fact keeps its source reference, scope, qualifier and method.
Known, unknown, conflicting and not-applicable states are distinct. Missing
claims are not false; missing measurements are not zero. Preserve component,
variant, pack and conditional declarations rather than collapsing them.

Keep displayed, comparison, subscription and conditional offers distinct. Bind
currency, quantity basis, tax evidence and observation time to the actual offer.
Multiple prices for one variant do not create additional physical variants.
Source weight metadata does not establish net contents without explicit evidence.

## Corrections and schema ownership

Persistent corrections are separate from agent assertions and are replayed only
against matching source identities and evidence. Changed captures require renewed
review. Store research cases and review details privately.

Dataset-owned contracts define attributes, aliases, units, vocabularies, validators
and recipes. Git contains immutable manifests with hashes rather than schema
bodies or copied field catalogs. Resolve and verify contracts before processing;
keep them fixed within a run. [Release review](../decisions/agent-led-schema-maintenance.md)
applies before publishing changed schemas.

## Verification and handoff

Verify archive histories and bytes, contract hashes, record validation, source
identity and output manifests. Report integrity, semantic review and coverage
separately. Reproducibility checks do not establish exhaustive market coverage.

A handoff records its exact inputs, source scope, selected contract, output hashes,
known gaps and proposed next work. Its data-specific details belong under ignored
`data/investigation/` or `docs/private/`. Public documentation records the runnable
interface and software validation without publishing the research inventory.
