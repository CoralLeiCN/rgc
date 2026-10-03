# Project implementation plan

The raw/silver architecture, chocolate schema, model preparation, documentation
maintenance and standalone processing package have passed implementation checks.
Current chocolate evidence still needs review and extraction evaluation before
model fitting, validation and supported price testing. Native installation across
harnesses is unverified; scoring value for money awaits research.

Canonical requirements: [specification](../spec.md),
[silver responsibilities](../chocolate-silver.md),
[chocolate schema](../chocolate-schema.md),
[portable processing](../category-processing.md) and
[documentation policy](../documentation-policy.md).

## Current work and files

| Work | Files | Status |
| --- | --- | --- |
| Define typed chocolate fields, vocabularies, units, evidence states and record shape. | Dataset `contracts/chocolate/`, pinned by `schemas/chocolate/dataset-contract.json` | Initial schema implemented; extraction review pending. |
| Define mappings and model training/interpretation contracts. | Pinned dataset contracts and `scripts/chocolate_model.py` | Contracts and preparation helpers implemented. |
| Combine raw verification, exact seller deduplication, standardization, price normalization and review/eligibility. | `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, shared components, `scripts/tests/test_silver.py` | Silver implemented and verified; standalone cleanup/component CLIs serve compatibility and diagnostics. |
| Preserve broad original records, source/images and immutable captures; export public text evidence. | `plugins/category-research/`, `scripts/publish_collections.py` | Collection and export implemented. |
| Document responsibilities, schema, training, commands and compatibility helpers. | Canonical guides, `README`, lifecycle views | Contracts and documentation checks verified. |
| Maintain documents with implementation changes and apply the agent writing rules. | `AGENTS.md`, `docs/documentation-policy.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml`, tests | Ownership, drift checks and writing rules recorded. |
| Package processing with chocolate/coffee profiles, stable seller identity and a harness skill. | `plugins/category-processing/`, `docs/category-processing.md` | Bundled tests, skill validation, isolated execution after copying the package and independent workflow checks passed. |
| Record capture/rules fingerprints, grouped mapping gaps and maintenance decisions. | Ledger, batch/summary helpers, skill references | Implemented; processing rebuilds all accepted captures. |
| Prepare generic model inputs grouped by family and encoders learned from training rows. | Portable model helpers, `prepare-model` CLI | Reviewed preparation and exclusion/failure gates verified. |
| Reject typed contract drift and retain valid category values outside selected model domains. | Profile loader, both standardization pipelines, regression tests | Verified. Runtime uses an explicit validator template. |
| Specify supermarket pricing, retailer comparisons and LightGBM/SHAP/AI explanations. | `docs/chocolate-modeling-design.md`, `docs/analysis/lightgbm-shap-explanation-design.md` | Proposed research design; active preparation contracts await migration and model fitting remains pending. |
| Move analytical contract bodies to the dataset with immutable references and verified ignored caches. | Three `dataset-contract.json` manifests, resolver/fetch/publication helpers, `docs/dataset-contracts.md` | Published and verified against original bytes; offline caches and both processing pipelines verified. |
| Consolidate repeated documentation and apply plain wording while preserving contracts and evidence. | Repository instructions, canonical/lifecycle guides, root and package READMEs, package skills/references | Completed; original cleanup and integration with the contract migration verified below. |

## Risks and controls

Preserve raw evidence and seller identity independently of brand. Keep unsupported
fields unknown and distinguish source claims from independent verification.
Normalize prices using edible mass and promotion/currency/tax/time context from
the relevant observation; active predictor reviews must cite that observation's
capture. Preserve historical recipes and claims in their own context. Keep
candidates distinct from reviewed inputs, review source roles/extractor support,
retain unknown sellers outside the initial model and group related designs across
sellers in validation. Missing evidence cannot justify new taxonomy values.

## Proof

The verification below was recorded on 2026-10-03. Each run establishes the stated
implementation scope. Dataset manifests and quality reports own build counts and
readiness; `complete_snapshot` establishes accepted input consistency.

| Verification | Recorded result and evidence |
| --- | --- |
| Initial chocolate silver | 140 script tests and 13 collection tests passed (153 total), covering combined processing, preservation, integrity/identity drift, review gates, historical evidence, model preparation, path safeguards and documentation drift. The real build completed with `complete_snapshot`, no archive/extraction errors and all rows valid. Original captures matched immutable history; all 22 output hashes, implementation hashes and exact bytes of four contracts were verified. A repeat reproduced dataset version, manifest and all hashes. Documentation guard and `git diff --check` passed. |
| Initial portable package | 143 script, 13 collection and 50 processing tests passed (206 total). `quick_validate.py` passed in an existing Python environment. An isolated copy verified raw preservation, seller identity, grouped evidence, review examples and mapping/review fingerprint changes without sibling imports. Reviewed coffee preparation yielded four observations in two families, split into two training and two validation rows; families stayed together and regression/release flags stayed false. |
| Initial portable chocolate build | `silver-39e4c5cc1df5299d00ef2898` completed with `complete_snapshot` and no archive/extraction errors. All 26 output hashes, exact bytes of five copied contracts and retained captures against immutable history were verified. A repeat reproduced report/manifest/hashes and classified all captures unchanged. Raw archives were preserved. This corpus check used temporary output; the documented build command writes a persistent snapshot when requested. |
| Contract consistency and model domain fixes before landing | 147 script, 64 processing and 13 collection tests passed (224 total). Checks covered nullable/known types, units, vocabularies, bounds, unsupported value constraints, portable category/market and model compatibility, and category values retained with candidate exclusions for model domains in both pipelines. |
| Current portable chocolate build | `silver-622d46124487f0ab7683c49e` completed with `complete_snapshot` and no archive/extraction errors. Retained captures matched immutable history, all 26 managed hashes passed and a repeat reproduced the manifest. Earlier datasets were preserved. Mapping gaps/evidence batches and zero eligible reviewed inputs were recorded in generated reports. |
| Analytical contract publication | Published on 2026-10-03 at Hugging Face commit `d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`. All 14 original payloads, the new index and updated dataset card were downloaded and verified against original bytes. Comparison with `1ff72d7d1d0611ac134adfe08e82b77d99e6117a` verified object identifiers, sizes and LFS metadata for all 29 existing files apart from the updated card, preserving raw exports and silver files. The 14 payloads were removed from the working tree after verification. Three manifests preserve existing semantic versions, hashes and exact snapshot contracts/provenance; `fetch_contracts.py --all --offline` verified all three caches. |
| Contract migration verification | 168 script, 75 processing and 13 collection tests passed (256 total). Checks cover missing/corrupt caches, custom contracts, snapshot copies/provenance and isolated offline package use. Full/structural documentation guards, all 30 documentation tests and scoped whitespace checks passed. Documentation tests use small temporary fixtures and cover clean clone checks without caches, malformed pins/hashes, documented versions, optional partial caches, cache markers and complete cache catalog/version alignment. Silver rebuilding and model fitting were outside these checks. |
| Proposed model design integration | Documentation guard and 30 documentation tests passed. Specification, schema/silver guides and design preserve active preparation contracts and identify proposed extensions. |
| Agent writing guidelines | Documentation guard, documentation checker tests and `git diff --check` passed. Rules are in `AGENTS.md`, referenced from intention and policy. |
| Documentation cleanup | 147 script, 64 processing and 13 collection tests passed (224 total), alongside the documentation guard and local file/heading link checks. Independent semantic review and comparison with the saved originals retained requirements, source URLs, identifiers, command arguments, examples/formulas, acceptance scenarios and historical proof. Repeated detail now links to owning guides; package references remain complete for independent use. Removed the empty root `README.md`. |
| Cleanup integration with main | 168 script, 75 processing and 13 collection tests passed (256 total). All three pinned contract caches verified offline; documentation guard, 157 local file/heading links and whitespace checks passed. Independent review preserved both parents' requirements, source URLs, CLI arguments, examples/formulas, acceptance scenarios, migration evidence and active/proposed model boundaries. Runtime files and immutable contract manifests match main. |

Current chocolate source values are unreviewed and price/tax basis is unresolved:
`model-inputs.jsonl` is empty and `release_ready` is false. Unsupported mappings
and evidence batches remain available in quality/review/batch artifacts. Package
correctness and reproducibility need separate evidence for extraction completeness,
statistical support, fitted coefficients, uncertainty and pricing insights.

Run from the repository root:

```sh
python3 -B scripts/build_chocolate_silver.py \
  --archive-root data/collections \
  --output data/silver/chocolate/uk
python3 -B scripts/fetch_contracts.py --all
python3 -B scripts/fetch_contracts.py --all --offline
python3 -B scripts/check_documentation.py
python3 -B -m unittest discover -s scripts/tests -v
python3 -B -m unittest discover -s plugins/category-research/tests -v
python3 -B -m unittest discover -s plugins/category-processing/tests -v
```

The [silver guide](../chocolate-silver.md) and [acceptance scenarios](../spec.md#8-acceptance-scenarios-for-stages-1-and-2)
define preservation, exact seller deduplication, aliases/captures, typed records,
normalization, deterministic versions/outputs, unresolved eligibility and seller
partitions. Evidence must resolve directly to raw without temporary stages.
Verify stable seller UIDs across alias/capture changes, profile/ledger invalidation,
grouped evidence, review gates and successful/failing model preparation in an
isolated copy. Check documentation, standardization semantics and drift alongside
behavior. Native client installation needs separate verification.

## Remaining work

1. Extend extraction using mappings supported by source evidence. Review physical
   and family identities, study scope, comparison groups, quantity and price basis.
2. Evaluate classification on reviewed samples and resolve coverage/release
   thresholds. Fit and validate a pricing model after these gates pass, then
   deliver supported insights and testing for proposed products.
3. Verify native installation and execution across agent harnesses.
4. Develop incremental caches, automatic harness dispatch/scheduling and selective
   migrations as future work. Current maintenance uses grouped evidence, triage,
   versioned diffs, tests and impact review within the task; accepted changes
   rebuild history with stable seller identities and immutable data/model snapshots.
5. Research methods for value for money before implementing scoring.
