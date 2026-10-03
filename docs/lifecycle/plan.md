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
| Explain retail frontier using the hackathon submission and judging structure. | `PROJECT.md`, intention, lifecycle intent and `README` | Description, capability status, collection demo and submission fields added and reviewed; documentation checks and the offline demo passed. Team names, video, brand votes and public access verification remain pending. |
| Record EAT_HACK participation in Retail Futures and the requested requirements. | `docs/eat-hack-track-two.md`, intention, lifecycle intent and `README` | Brief covers the Track 2 challenge, submission requirements and judging criteria; source review and documentation checks passed. |
| Define typed chocolate fields, vocabularies, units, evidence states and record shape. | Dataset `contracts/chocolate/`, pinned by `schemas/chocolate/dataset-contract.json` | Initial schema implemented; extraction review pending. |
| Define mappings and model training/interpretation contracts. | Pinned dataset contracts and `scripts/chocolate_model.py` | Contracts and preparation helpers implemented. |
| Combine raw verification, exact seller deduplication, standardization, price normalization and review/eligibility. | `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, shared components, `scripts/tests/test_silver.py` | Silver implemented and verified; standalone cleanup/component CLIs serve compatibility and diagnostics. |
| Preserve broad original records, source/images and immutable captures; export public text evidence. | `plugins/category-research/`, `scripts/publish_collections.py` | Collection and export implemented. |
| Document responsibilities, schema, training, commands and compatibility helpers. | Canonical guides, `README`, lifecycle views | Contracts and documentation checks verified. |
| Maintain documents with implementation changes and apply the agent writing and testing rules. | `AGENTS.md`, `docs/documentation-policy.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml`, tests | Ownership, drift checks, writing rules and test selection rules recorded. |
| Review existing tests for useful coverage and repeated execution. | `scripts/tests/`, both plugin test suites, `docs/documentation-policy.md` | Reviewed 256 cases; consolidated seven duplicate cases and removed five redundant cases. Retained distinct preservation, integrity, identity, review, model and isolated package execution checks. |
| Package processing with chocolate/coffee profiles, stable seller identity and a harness skill. | `plugins/category-processing/`, `docs/category-processing.md` | Bundled tests, skill validation, isolated execution after copying the package and independent workflow checks passed. |
| Record capture/rules fingerprints, grouped mapping gaps and maintenance decisions. | Ledger, batch/summary helpers, skill references | Implemented; processing rebuilds all accepted captures. |
| Prepare generic model inputs grouped by family and encoders learned from training rows. | Portable model helpers, `prepare-model` CLI | Reviewed preparation and exclusion/failure gates verified. |
| Reject typed contract drift and retain valid category values outside selected model domains. | Profile loader, both standardization pipelines, regression tests | Verified. Runtime uses an explicit validator template. |
| Specify supermarket pricing, retailer comparisons and LightGBM/SHAP/AI explanations. | `docs/chocolate-modeling-design.md`, `docs/analysis/lightgbm-shap-explanation-design.md` | Proposed research design; active preparation contracts await migration and model fitting remains pending. |
| Move analytical contract bodies to the dataset with immutable references and verified ignored caches. | Three `dataset-contract.json` manifests, resolver/fetch/publication helpers, `docs/dataset-contracts.md` | Published and verified against original bytes; offline caches and both processing pipelines verified. |
| Consolidate repeated documentation and apply plain wording while preserving contracts and evidence. | Repository instructions, canonical/lifecycle guides, root and package READMEs, package skills/references | Completed; original cleanup and integration with the contract migration verified below. |
| Configure collection sections and generate processing profiles for new categories. | Collection `collection_sections`, processing `profile_builder.py`, `init-profile`, definition reference and generic engine/archive tests | Implemented: Unicode section reports, five-contract authoring, non-food quantities/currencies/tax bases and normalized study paths. |
| Discover unconfigured structured source fields and document proposals. | Processing `discovery.py`, `schema_suggestions.py`, pipeline/summary outputs, tests/reference, `docs/schema-proposals/` | Implemented structural discovery and worksheets; seller review metrics and selling plan terms await agent assessment. Prose investigation, a decision registry and snapshot comparisons remain future work. |
| Maintain schemas autonomously and review completed schema releases before Hugging Face commits. | `docs/decisions/agent-led-schema-maintenance.md`, canonical guides, processing skill/references and generated guidance | Standing user decision: agents apply supported local changes without approval, with evidence, versioning, tests and impact checks. Present the detailed completed release for user review before its remote commit. The harness owns this step; no popup UI or upload gate is implemented. |
| Use pytest for tests and Ruff for Python linting. | `pyproject.toml`, `uv.lock`, native pytest tests, plugin `pytest.ini` files, `.github/workflows/validation.yml`, development documentation | Implemented with locked development dependencies and CI commands. All 304 tests and Ruff checks passed after test consolidation; prior isolated package verification is recorded below. |

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
| retail frontier project description | `python3 -B scripts/check_documentation.py`, whitespace and local link checks passed. The description contains 169 words and preserves judging weights and required submission fields. Independent source review verified capability boundaries; the embedded collection demo preserved five original records and sample metadata across repeated imports with network blocked. It established capture preservation and valid reports, with completeness still `not_verified`; silver processing and model fitting were outside this demo. |
| EAT_HACK Retail Futures brief | `python3 -B scripts/check_documentation.py` and whitespace checks passed. Reviewed the summary against the supplied participant brief and independently checked the requested scope: Track 2 challenge, submission requirements and judging criteria. |
| Initial chocolate silver | 140 script tests and 13 collection tests passed (153 total), covering combined processing, preservation, integrity/identity drift, review gates, historical evidence, model preparation, path safeguards and documentation drift. The real build completed with `complete_snapshot`, no archive/extraction errors and all rows valid. Original captures matched immutable history; all 22 output hashes, implementation hashes and exact bytes of four contracts were verified. A repeat reproduced dataset version, manifest and all hashes. Documentation guard and `git diff --check` passed. |
| Initial portable package | 143 script, 13 collection and 50 processing tests passed (206 total). `quick_validate.py` passed in an existing Python environment. An isolated copy verified raw preservation, seller identity, grouped evidence, review examples and mapping/review fingerprint changes without sibling imports. Reviewed coffee preparation yielded four observations in two families, split into two training and two validation rows; families stayed together and regression/release flags stayed false. |
| Initial portable chocolate build | `silver-39e4c5cc1df5299d00ef2898` completed with `complete_snapshot` and no archive/extraction errors. All 26 output hashes, exact bytes of five copied contracts and retained captures against immutable history were verified. A repeat reproduced report/manifest/hashes and classified all captures unchanged. Raw archives were preserved. This corpus check used temporary output; the documented build command writes a persistent snapshot when requested. |
| Contract consistency and model domain fixes before landing | 147 script, 64 processing and 13 collection tests passed (224 total). Checks covered nullable/known types, units, vocabularies, bounds, unsupported value constraints, portable category/market and model compatibility, and category values retained with candidate exclusions for model domains in both pipelines. |
| Current portable chocolate build | `silver-622d46124487f0ab7683c49e` completed with `complete_snapshot` and no archive/extraction errors. Retained captures matched immutable history, all 26 managed hashes passed and a repeat reproduced the manifest. Earlier datasets were preserved. Mapping gaps/evidence batches and zero eligible reviewed inputs were recorded in generated reports. |
| Analytical contract publication | Published on 2026-10-03 at Hugging Face commit `d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`. All 14 original payloads, the new index and updated dataset card were downloaded and verified against original bytes. Comparison with `1ff72d7d1d0611ac134adfe08e82b77d99e6117a` verified object identifiers, sizes and LFS metadata for all 29 existing files apart from the updated card, preserving raw exports and silver files. The 14 payloads were removed from the working tree after verification. Three manifests preserve existing semantic versions, hashes and exact snapshot contracts/provenance; `fetch_contracts.py --all --offline` verified all three caches. |
| Contract migration verification | 168 script, 75 processing and 13 collection tests passed (256 total). Checks cover missing/corrupt caches, custom contracts, snapshot copies/provenance and isolated offline package use. Full/structural documentation guards, all 30 documentation tests and scoped whitespace checks passed. Documentation tests use small temporary fixtures and cover clean clone checks without caches, malformed pins/hashes, documented versions, optional partial caches, cache markers and complete cache catalog/version alignment. Silver rebuilding and model fitting were outside these checks. |
| Proposed model design integration | Documentation guard and 30 documentation tests passed. Specification, schema/silver guides and design preserve active preparation contracts and identify proposed extensions. |
| Agent writing guidelines | Documentation guard, documentation checker tests and `git diff --check` passed. Rules are in `AGENTS.md`, referenced from intention and policy. |
| Agent testing guidelines | `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Test selection and stopping rules are recorded in `AGENTS.md` and referenced by the documentation policy. |
| Existing test review | All 256 original cases passed after fetching pinned contracts. Reviewed each suite against observable behavior and retained failure gates. Consolidated seven duplicate cases, removed five redundant cases, five pipeline builds, three collection imports and one repeated publication inventory build; removed helper validator self-checks and fixed prose assertions. Final discovery passed 161 script, 13 collection and 70 processing cases (244 total, no skips), using unittest discovery with a temporary timing runner. Sum of reported suite execution times was 5.84 seconds before and 5.13 seconds after; these single local runs used verified caches and provide an indicative comparison. Independent review confirmed coverage retained by the documentation consolidation and publication fixture extraction. All three caches verified with `fetch_contracts.py --all --offline`; documentation guard and `git diff --check` passed. |
| Documentation cleanup | 147 script, 64 processing and 13 collection tests passed (224 total), alongside the documentation guard and local file/heading link checks. Independent semantic review and comparison with the saved originals retained requirements, source URLs, identifiers, command arguments, examples/formulas, acceptance scenarios and historical proof. Repeated detail now links to owning guides; package references remain complete for independent use. Removed the empty root `README.md`. |
| Cleanup integration with main | 168 script, 75 processing and 13 collection tests passed (256 total). All three pinned contract caches verified offline; documentation guard, 157 local file/heading links and whitespace checks passed. Independent review preserved both parents' requirements, source URLs, CLI arguments, examples/formulas, acceptance scenarios, migration evidence and active/proposed model boundaries. Runtime files and immutable contract manifests match main. |
| Prior main integration with pending generic/discovery work | On 2026-10-03, local main `9cafecb` was integrated while retaining pending collection/profile authoring, discovery and maintenance policy changes. 168 script, 129 processing and 19 collection tests passed (316 total), with documentation and whitespace checks. All 14 contract payloads matched immutable manifest hashes/lengths and all three caches verified offline. An isolated package processed the two proposal captures with 31 discovered occurrences, full typed evidence, 28 verified managed files and reproducible repeated outputs/review packets. |
| Pytest and Ruff migration after the latest main sync | On 2026-10-03, fetched origin and integrated local main `f932668` while preserving pending work. All 316 tests passed as native pytest tests with pytest 9.1.1; Ruff 0.16.10, documentation and whitespace checks passed. Locked development dependencies and equivalent CI commands are configured; the updated GitHub workflow has not run here. Isolated copied plugins passed all 129 processing and 19 collection tests using their own pytest configuration. Existing immutable contract references are unchanged. |
| Test cleanup integration with main | Integrated main `9f81be3` into the committed test review `38c2998`, translating the same cleanup into native pytest assertions and retaining generic category/discovery coverage. `uv sync --locked` installed Python 3.13.3 with pytest 9.1.1 and Ruff 0.16.10. `uv run --locked pytest` passed all 304 cases (161 script, 19 collection and 124 processing) in 5.54 seconds; `uv run --locked ruff check .`, `python3 -B scripts/fetch_contracts.py --all --offline`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Independent review verified the conflict resolutions, retained assertions and combined documentation policy. |

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
uv sync --locked
python3 -B scripts/fetch_contracts.py --all
python3 -B scripts/fetch_contracts.py --all --offline
uv run pytest
uv run ruff check .
python3 -B scripts/check_documentation.py
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
