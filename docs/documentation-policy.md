# Documentation maintenance policy

Update documentation with the behavior it describes. Record user intention,
implemented contracts and validation status distinctly. The
[repository instructions](../AGENTS.md) apply this policy and own the writing
rules, including preservation of original source evidence, and test selection
rules.

## Canonical documents and ownership

Data workflow guides, model designs, review evidence and schema proposals live
under `docs/data/`. Update their links and documentation checker paths when
changing this structure.

| Document | Owns | Update condition |
| --- | --- | --- |
| [Intention](intention.md) | User goals, requested scope, and constraints. | User goals, requested deliverables, scope, or constraints change. |
| [Specification](spec.md) | Contracts across layers, supported behavior, readiness, training, interpretation and release requirements. | Behavior, interface, eligibility, model basis or acceptance requirements change. |
| [Silver guide](data/chocolate-silver.md) | Raw/silver responsibilities, combined pipeline, preservation of source listings and aliases, outputs, evidence resolution, manifest and CLI. | Silver behavior, identity, output, provenance, CLI, schema/review application or eligibility changes. |
| [Portable processing guide](data/category-processing.md) | Standalone processing package, profile versions, stable seller envelope, generic targets, ledger/batches, harness maintenance and model preparation commands. | Portable engine, package, profile, ledger/batch, review/eligibility, model handoff or public CLI changes. |
| [Processing package README](../plugins/category-processing/README.md), [skill](../plugins/category-processing/skills/category-processing/SKILL.md) and its references | Standalone use, decisions, archive/profile contracts, evidence triage and model handoff. | Package behavior or workflow changes; preserve complete use after copying the package without repository siblings. |
| [Deduplication guide](data/chocolate-deduplication.md) | Standalone deduplication helper identity, snapshot outputs and CLI. | Shared deduplication identity, helper partitions/provenance or CLI changes; update the silver contract too. |
| [Cleanup guide](data/chocolate-cleaning.md) | Earlier compatibility cleanup directly from raw and its distinct review contract. | Helper implementation, profile, review format or CLI changes; keep its relationship to silver accurate. |
| [Chocolate schema guide](data/chocolate-schema.md) | Typed fields, standardization rules, evidence reviews, training handoff and insight interpretation within silver. | Chocolate schema, vocabulary, source mappings, review/eligibility, model design or related behavior changes. |
| [Chocolate dataset manifest](../schemas/chocolate/dataset-contract.json) | Immutable dataset revision, paths, hashes and versions for executable contracts. | Typed attributes, vocabulary, units, mapping behavior, record shape, feature selection or model design changes. Publish affected contracts and synchronize manifest, versions and documentation. |
| [Dataset contract guide](data/dataset-contracts.md) | Dataset ownership, immutable pins, caches, offline use and publication. | Manifest format, resolver, cache behavior or publication workflow changes. |
| [README](../README) | Entry points, usable commands, and implementation overview. | A public entry point, layer, usable command, or implementation status changes. |
| [Lifecycle intent](lifecycle/intent.md) and [lifecycle specification](lifecycle/spec.md) | Short navigation views of canonical intention and specification. | Their summarized scope or status would become inaccurate. Keep detail in canonical documents. |
| [Lifecycle plan](lifecycle/plan.md) | Implementation work, current status, risks, proof, and remaining work. | Every behavioral, schema, pipeline, or modeling change; update affected progress and proof in the same change. |

The authoritative contracts are in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
`contracts/chocolate/` contains `profile.json`, `source-mappings.json`,
`product.schema.json` and `model-design.json`;
`contracts/category-processing/<category>/` adds `pipeline.json` for each
portable profile. Git retains `schemas/chocolate/dataset-contract.json` and
`plugins/category-processing/profiles/<category>/dataset-contract.json`, with
immutable commit pins, per-file SHA-256 hashes and version metadata. Runtime
caches are ignored; generated snapshots retain exact contract copies/provenance.

Publish changed contracts to a new immutable revision before updating manifests.
For schema changes, complete local implementation and validation and follow the
[release review decision](decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
before the Hugging Face commit. Supported local maintenance needs no user approval.
Verify hashes and profile alignment, synchronize affected semantic versions and
documentation, then rebuild. Moving storage alone preserves bytes and versions.
All five portable contracts must agree on schema/catalog and declare mapping,
model design and recipe versions. Synchronize the portable guide's version table.
Portable chocolate's stable seller envelope uses distinct schema/design versions.
Preserve established snapshots and rebuild from authoritative contracts.

## Mechanically required change coverage

The guard requires these accompanying documents when the listed implementation
paths change. This is a minimum; use the ownership table to update additional
documents when their meaning or public entry points are affected.

| Changed paths | Required document updates |
| --- | --- |
| `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, `schemas/chocolate/**`, `scripts/chocolate_standardization/**`, `scripts/standardize_chocolate_data.py`, `scripts/chocolate_model.py`, `scripts/dataset_contracts.py`, `scripts/fetch_contracts.py` | `docs/spec.md`, `docs/data/chocolate-schema.md`, `docs/data/chocolate-silver.md`, `docs/lifecycle/plan.md` |
| `scripts/dataset_contracts.py`, `scripts/fetch_contracts.py` | Also `docs/data/dataset-contracts.md` and `README`. |
| `scripts/publish_contracts.py` | `docs/spec.md`, `docs/data/dataset-contracts.md`, `README`, `docs/lifecycle/plan.md` |
| `scripts/chocolate_cleanup/**`, `scripts/clean_chocolate_data.py`, `scripts/deduplicate_chocolate_data.py` | `docs/spec.md`, `docs/data/chocolate-cleaning.md`, `docs/data/chocolate-deduplication.md`, `docs/data/chocolate-silver.md`, `docs/lifecycle/plan.md` |
| `plugins/category-research/**`, excluding its tests | `docs/spec.md`, `plugins/category-research/README.md`, `docs/lifecycle/plan.md` |
| `plugins/category-processing/**`, excluding its tests | `docs/spec.md`, `docs/data/category-processing.md`, `plugins/category-processing/README.md`, `docs/lifecycle/plan.md` |
| `scripts/publish_collections.py`, `scripts/archive_product_sources.py`, `scripts/verify_product_archive.py` | `docs/spec.md`, `README`, `docs/lifecycle/plan.md` |
| `AGENTS.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml` | `docs/documentation-policy.md`, `docs/lifecycle/plan.md` |

## Requirements for each change

1. Identify the affected contracts and update their canonical documents with
   the implementation. Update intention only when intent has changed.
2. Keep schema/profile, source mapping, record format and model design version
   references aligned. Change the relevant version when its meaning changes;
   retain old dataset manifests as the record of older builds.
3. Update lifecycle plan status and proof. Distinguish implemented code, reviewed
   data, evaluated extraction, and fitted/validated models. None implies the next.
4. Update commands and links when files or entry points move. Do not leave an
   alternate contract in a lifecycle summary or README.
5. Use the locked development environment, run Ruff and the structural guard,
   then run tests appropriate to the change with pytest before finishing.
   Follow the test selection rules in `AGENTS.md`: create tests when they are
   meaningful and necessary, and broaden or repeat testing after required checks
   pass only when new changes, failures or unresolved concerns justify it.
   Choose the relevant commands below for the affected behavior:

   ```sh
   uv sync --locked
   python3 -B scripts/fetch_contracts.py --all
   uv run ruff check .
   python3 -B scripts/check_documentation.py
   uv run pytest scripts/tests
   ```

   Run the collection plugin's tests when collection behavior changes:

   ```sh
   uv run pytest plugins/category-research/tests
   ```

   Run the processing package's tests when its core, profiles or workflow change:

   ```sh
   uv run pytest plugins/category-processing/tests
   ```

   Select a test module when it covers the affected behavior, for example:

   ```sh
   uv run pytest scripts/tests/test_documentation.py
   ```

   Run the complete affected suites when reviewing coverage across modules or
   changing shared fixtures. Consolidate duplicate coverage and setup while
   preserving distinct observable behavior and failure cases.

The guard checks required documents, local references, lifecycle placeholders,
contract/version alignment and documentation coverage for tracked or untracked
changes. It checks both portable profiles' five contract references, documented
versions and required skill/reference links. Structural checks work offline in a
clean clone without cached contracts. Available cached files receive hash/version
checks, with schema/catalog alignment checked for complete caches. Review the
prose, changed contracts and
generated quality report for semantic accuracy and evidence review. Verify
execution after copying a package and native client installation independently.

pytest is the repository test framework and Ruff checks Python source and tests.
Their development versions and dependencies are pinned in `uv.lock`, including
pandas 2.2.3 for canonical chocolate silver and schema analysis. The script-local
metadata also supports `uv run --script`; the guard remains usable offline
without pandas or contract caches. A full
verification uses `uv run pytest`; focused commands above select the affected
suite. Runtime plugins continue to use the standard library. Verify populated
contract caches with `python3 -B scripts/fetch_contracts.py --all --offline`.

The [validation workflow](../.github/workflows/validation.yml) runs Ruff, pytest
and the guard for pull requests and pushes. Its explicit `--base <git-ref>`
compares against the pull request base or previous push revision; local checks
include current tracked and untracked changes.

## Completion record

Record runnable verification commands and material limitations in the lifecycle
plan. Dataset manifests and quality reports own counts for each build; reference
them from specifications. Use a regenerated report's actual status.

Use existing task authorization for documentation maintenance. Publication,
deployment and communication require authorization within their own task scope.

## Gold and fixed target maintenance

Changes to Gold build/review/load interfaces require `docs/spec.md`, `docs/data/chocolate-schema.md`, `docs/data/chocolate-silver.md`, `docs/data/chocolate-gold.md`, `README` and `docs/lifecycle/plan.md`. Experimental regression/training and family mapping changes require the schema/spec/Silver guides and lifecycle status; trainer handoff also updates Gold. Canonical contract bodies stay dataset-owned; prepare local versioned releases and update immutable references after approved verified publication. Maintain the finalized regular, non-promotional, tax-inclusive target with reject fallback across bundled and generated profiles.

Locked development dependencies include NumPy 2.2.6 and PyArrow 21.0.0 so pytest exercises numerical and Parquet behavior instead of skipping it. Preserve administrative Gold review provenance separately from evidence-backed Silver eligibility. The schema-release review policy in [agent-led maintenance](decisions/agent-led-schema-maintenance.md) remains authoritative before any Hugging Face commit.
