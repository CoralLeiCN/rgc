# Documentation maintenance policy

The repository records user intention, implemented contracts, and current
validation separately. Documentation must change with the behavior it describes.
The [repository instructions](../AGENTS.md) apply this policy to future work.

## Canonical documents and ownership

| Document | Owns | Update condition |
| --- | --- | --- |
| [Intention](intention.md) | User goals, requested scope, and constraints. | User goals, requested deliverables, scope, or constraints change. |
| [Specification](spec.md) | Cross-layer contracts, supported behavior, readiness, training, interpretation, and release requirements. | Any behavior, interface, eligibility gate, model basis, or acceptance requirement changes. |
| [Silver guide](chocolate-silver.md) | Canonical raw/silver responsibilities, combined pipeline, source-listing/alias preservation, outputs, evidence resolution, manifest and CLI. | Silver behavior, identity, output, provenance, CLI, schema/review application or eligibility changes. |
| [Portable processing guide](category-processing.md) | Self-contained processing plugin, profile versions, stable seller envelope, generic targets, ledger/batches, calling-harness maintenance and model-preparation commands. | Portable engine, package, profile, ledger/batch, review/eligibility, model handoff or public CLI changes. |
| [Processing package README](../plugins/category-processing/README.md), [skill](../plugins/category-processing/skills/category-processing/SKILL.md) and its references | Standalone use, decisions, archive/profile contracts, evidence triage and model handoff without repository siblings. | Package behavior or usable workflow changes; keep progressive references accurate and copied-package use self-contained. |
| [Deduplication guide](chocolate-deduplication.md) | Standalone deduplication helper identity, snapshot outputs and CLI. | Shared deduplication identity, helper partitions/provenance or CLI changes; update the silver contract too. |
| [Cleanup guide](chocolate-cleaning.md) | Earlier direct-from-raw compatibility cleanup and its distinct review contract. | That helper implementation, profile, review format or CLI changes; keep its compatibility relationship to silver accurate. |
| [Chocolate schema guide](chocolate-schema.md) | Typed fields, standardization rules, evidence reviews, training handoff and insight interpretation within silver. | Chocolate schema, vocabulary, source mappings, review/eligibility, model design or related behavior changes. |
| [Chocolate machine contracts](../schemas/chocolate/profile.json) | Executable field definitions and versioned rules. | Typed attributes, vocabulary, units, mapping behavior, record shape, feature selection, or model design changes. Update the affected contract files and versions together. |
| [README](../README) | Entry points, usable commands, and implementation overview. | A public entry point, layer, usable command, or implementation status changes. |
| [Lifecycle intent](lifecycle/intent.md) and [lifecycle specification](lifecycle/spec.md) | Short navigation views of canonical intention and specification. | Their summarized scope or status would become inaccurate. Keep detail in canonical documents. |
| [Lifecycle plan](lifecycle/plan.md) | Implementation work, current status, risks, proof, and remaining work. | Every behavioral, schema, pipeline, or modeling change; update affected progress and proof in the same change. |

The schema contract consists of `profile.json`, `source-mappings.json`,
`product.schema.json`, and `model-design.json` under `schemas/chocolate/`.
Generated output copies describe the exact build that produced them; edit the
checked-in contracts and rebuild rather than editing generated copies.
Portable profiles under `plugins/category-processing/profiles/<category>/` also
include `pipeline.json`; their five contracts must agree on schema/catalog and
have explicit mapping, model-design and recipe versions. Keep the portable guide's
version table synchronized. Portable chocolate's stable seller envelope uses its
own schema/design versions; do not rewrite established chocolate snapshots.

## Mechanically required change coverage

The guard requires these accompanying documents when the listed implementation
paths change. This is a minimum; use the ownership table to update additional
documents when their meaning or public entry points are affected.

| Changed paths | Required document updates |
| --- | --- |
| `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, `schemas/chocolate/**`, `scripts/chocolate_standardization/**`, `scripts/standardize_chocolate_data.py`, `scripts/chocolate_model.py` | `docs/spec.md`, `docs/chocolate-schema.md`, `docs/chocolate-silver.md`, `docs/lifecycle/plan.md` |
| `scripts/chocolate_cleanup/**`, `scripts/clean_chocolate_data.py`, `scripts/deduplicate_chocolate_data.py` | `docs/spec.md`, `docs/chocolate-cleaning.md`, `docs/chocolate-deduplication.md`, `docs/chocolate-silver.md`, `docs/lifecycle/plan.md` |
| `plugins/category-research/**`, excluding its tests | `docs/spec.md`, `plugins/category-research/README.md`, `docs/lifecycle/plan.md` |
| `plugins/category-processing/**`, excluding its tests | `docs/spec.md`, `docs/category-processing.md`, `plugins/category-processing/README.md`, `docs/lifecycle/plan.md` |
| `scripts/publish_collections.py`, `scripts/archive_product_sources.py`, `scripts/verify_product_archive.py` | `docs/spec.md`, `README`, `docs/lifecycle/plan.md` |
| `AGENTS.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml` | `docs/documentation-policy.md`, `docs/lifecycle/plan.md` |

## Same-change requirements

1. Identify the affected contracts and update their canonical documents with
   the implementation. Update intention only when intent has changed.
2. Keep schema/profile, source-mapping, record-format, and model-design version
   references aligned. Change the relevant version when its meaning changes;
   retain old dataset manifests as the record of older builds.
3. Update lifecycle plan status and proof. Distinguish implemented code, reviewed
   data, evaluated extraction, and fitted/validated models. None implies the next.
4. Update commands and links when files or entry points move. Do not leave an
   alternate contract in a lifecycle summary or README.
5. Run the structural guard and relevant behavioral tests before finishing:

   ```sh
   python3 -B scripts/check_documentation.py
   python3 -B -m unittest discover -s scripts/tests -v
   ```

   Run the collection plugin's tests when collection behavior changes:

   ```sh
   python3 -B -m unittest discover -s plugins/category-research/tests -v
   ```

   Run the processing package's tests when its core, profiles or workflow change:

   ```sh
   python3 -B -m unittest discover -s plugins/category-processing/tests -v
   ```

The guard checks required documents, local references, lifecycle placeholders,
contract/version alignment, and whether tracked or untracked behavioral changes
have corresponding documentation updates. It cannot prove that prose is correct
or that a source assertion was reviewed. Review the changed contracts and
generated quality report for those questions.
It also checks that both bundled portable profiles have aligned five-file
schema/catalog contracts and documented schema/mapping/model-design/recipe
versions, plus required package skill/reference links. Copied-package behavior
and native client installation require their own verification.

The [validation workflow](../.github/workflows/validation.yml) runs the guard and
behavioral tests for pull requests and pushes. Its explicit `--base <git-ref>`
compares against the pull-request base or previous push revision; local checks
include current tracked and untracked changes. Change coverage checks that the
applicable documents changed, rather than proving that those changes describe
the implementation correctly. Review their substance as part of the same work.

## Completion record

Record runnable verification commands and material limitations in the lifecycle
plan. Do not store volatile counts in several specifications: dataset manifests
and quality reports own build-specific counts. If a report is regenerated, use
its actual status rather than assuming previous results still apply.

This policy requires documentation maintenance within authorized work. It does
not add a user approval gate, require a separate planning conversation, or
authorize unrelated publication, deployment, or communication.
