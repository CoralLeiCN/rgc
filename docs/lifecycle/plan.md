# Project implementation plan

The raw, combined Silver and immutable Parquet Gold architecture, chocolate
schema, model preparation, documentation maintenance and standalone processing
package have passed implementation checks. Experimental training code and
reviewed family assignments are available. Real Gold still has zero eligible
observations; model fitting, validation and supported price testing await evidence
review. Native installation across harnesses is unverified; scoring value for
money awaits research.

The Vercel retailer workspace implements a layered trait terrain, typed cohorts,
product configuration, observed-price analysis and extraction adapters. Its
published snapshot and disclosed demo recipe have their own verification below.
Live browser/WebGL and configured model extraction remain unverified.

Canonical requirements: [specification](../spec.md),
[silver responsibilities](../data/chocolate-silver.md),
[Gold responsibilities](../data/chocolate-gold.md),
[chocolate schema](../data/chocolate-schema.md),
[portable processing](../data/category-processing.md) and
[documentation policy](../documentation-policy.md).

## Current work and files

The current hackathon app is `apps/web`, with a Vercel frontend/backend, private
snapshot, leaf-colour terrain, typed filters, product configurator, gap finder and
brand analysis. Price is adjustable by slider; a read-only trait recipe supplies
the demo score. Image/text extraction supports server-side OpenAI or a local
Codex bridge; live provider configuration remains pending. The user cancelled
the new pricing-model integration and requested removal of added tests, retired
prototypes and intermediate demo documents.

The repository now keeps one current web app and the operational
[architecture](../vercel-architecture.md), [data guide](../collection-integration.md)
and [app setup](../../apps/web/README.md). The snapshot builder is
`scripts/build_web_snapshot.py` and outputs private server JSON only. Old static
studies, duplicated browser data, points API, fictional ID-seeded score mode,
retired UI modules and their asset-copy tooling are removed. Existing upstream
processing plugins and their verification suites are outside this cleanup.

Cleanup validation passes: TypeScript, production build, all seven API snapshot
traces, pinned Plotly integrity and documentation links. The simplified offline
snapshot builder reproduces all 26 JSON files byte-for-byte. A cleaned preview
is deploying; hosted checks are pending. The last protected preview is
[available here](https://rgc-hqvkpvxpj-ptyyyy-s-projects.vercel.app); it predates
this cleanup. Live browser/WebGL and actual model extraction remain unverified.
Codex startup is blocked by this workspace before a model request; no Funnel
has been published. Provider setup remains in the app README.

The app's immutable snapshot pins Hugging Face revision
`d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`. Its 3,743 listings, 103 traits and
zero eligible model rows describe that snapshot. Upstream analytical contracts
now pin `d549ad91d63fb452af605df4a939c4e1f0a59bfa`; their Gold, family-review and
training progress is recorded in the work table and pipeline proof below.
The app continues to use its disclosed `trait-demo-1` recipe. Upstream
experimental training and evidence review retain their own status.

Model maintenance and without-brand integration checks passed against main
`cd9e7df8eb7f50aee33d3fce5ca9f0509aff8deb`: `uv sync --locked`, all four
pinned contract sets verified offline, all 438 pytest cases, Ruff, documentation
checks including `--base main`, whitespace checks, local documentation links
and the without-brand command route. Existing with-brand modules, dependencies,
current-price policy and published Gold reference were preserved. The
without-brand estimator has separate module names and uses the shared SciPy
1.15.3 lock; its published fixture retains its exact earlier source and lock.
No new model fit or remote publication is claimed by this integration.

[Model maintenance](../model-maintenance.md) now owns model artifact storage,
immutable publication receipts, verification and retraining requirements.
Generated model/data artifacts stay in ignored local directories and Hugging
Face; Git retains code, dependencies, tests, documentation and small receipts.
The current publication is a synthetic fixture. General remote model fetching
and automatic maintenance are not implemented by this documentation change.

The independent `lightgbm_without_brand` session implements a native categorical
LightGBM estimator, family balancing and deterministic seeded fitting/calibration/
testing, fitting-only grouped tuning, retailer conformal calibration and exact
raw-output TreeSHAP with reconstruction/fallback. Its
[implementation record](../data/analysis/lightgbm-without-brand-implementation.md)
owns commands, local working policy and remaining interfaces. Integration
uses independent without-brand module names and the shared SciPy 1.15.3 lock;
the published fixture retains its original source and SciPy 1.16.2 lock.
Current-price migration is pending for this trainer. The session's pinned regular-price data blocks
real fitting; fixture fits and actual fitted/release status are distinct.

The session rebuilt Silver `silver-f651a7faea94ed5a7f003e64` from the saved checkout
with 3,743 listings, 4,347 captures, 2,134 candidates and zero eligible rows, and
created verified Gold `gold-4939405fcf8724686f9ee32c`. Existing snapshots and raw
evidence were preserved. The real-data readiness report records four missing
selected shared fields, unresolved source-price window and no fitting families.
No real-data fitted model exists in this session; aligned analytical/portable contract
migration, release review, reviewed inputs and comparison gates remain pending.

Original pre-integration verification for this session: `uv sync --locked`, all three pinned caches
verified with `python3 -B scripts/fetch_contracts.py --all --offline`, `uv run pytest`
(387 passed, including 12 new estimator cases), `uv run ruff check .`,
`python3 -B scripts/check_documentation.py` and `git diff --check` passed.
Synthetic run `model-run-643f7148c9f44c42e5f42212` fitted 722 trees on 648 rows/
108 families, with 216 rows/36 families in each held-out partition. Test MAE was
GBP 0.09775/100 g and GBP 0.09030/pack; weighted median percentage error was
1.96862%. All 216 native TreeSHAP decompositions reconstructed within
`5.33e-15` log units. Retailer representative coverage was 33/36 for Ocado and
36/36 for Waitrose. Wilson lower bounds were 0.8089/0.9301; Ocado falls below
the proposed 0.85 gate. Listing sensitivity is unchanged because every synthetic
family has the same row count; the weighting test also covers unequal counts.
These are synthetic measurements, with no market-performance or release claim.
The [fixture proof](../data/analysis/lightgbm-without-brand-fixture-validation.json)
records full metrics and hashes. The user requested storage under `model/*`;
the [synthetic model bundle](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/bb1c9de580c64cc13aac62b352d58704fe2dd60e/model/lightgbm_without_brand/fixtures/model-run-643f7148c9f44c42e5f42212) was published at
`bb1c9de580c64cc13aac62b352d58704fe2dd60e`. All 53 published files matched their prepared
bytes, all 99 existing dataset files were preserved, and a portable replay
reproduced the run and 23 managed artifacts apart from the historical local
command. The [publication receipt](../data/analysis/lightgbm-without-brand-model-publication.json)
records per-file hashes. Real readiness inputs remain local after automatic
approval review rejected their inclusion in the initial payload. This fixture
publication establishes no real-data model or release claim. Its parent
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7` includes refreshed Gold from another session;
the earlier regular-price audit below does not evaluate that newer snapshot.

After the human confirmed all Gold data are verified and requested training,
the session reloaded current Gold and searched the designated/saved worktrees
and the remote dataset. The [current audit](../data/analysis/lightgbm-without-brand-current-gold-audit.json)
records successful integrity verification, 2,134 null regular unit/log targets,
2,134 unknown tax bases and zero eligible rows at the exact current manifest
hash. The [remote root inventory](../data/analysis/lightgbm-without-brand-remote-availability.json)
at `d549ad91d63fb452af605df4a939c4e1f0a59bfa` contains no Gold directory.
Readiness run `model-run-ffff17f6eca01c6dd1d782dc` therefore records a current input
failure, while preserving the human verification status and requesting the
location of any different verified snapshot. It does not rely solely on older
documentation or rewrite eligibility/targets.

| Work | Files | Status |
| --- | --- | --- |
| Deploy the retailer workspace with typed cohorts, family matrix, comparison and layered terrain with gap/brand analysis. | `apps/web/app/`, `apps/web/components/`, `apps/web/lib/client/` | Implemented; cleanup build, types and integrity verification are recorded above. Live browser/WebGL review remains. |
| Serve bounded schema, product, terrain, evidence, comparison and analysis data, plus trait extraction adapters. | `apps/web/app/api/`, `apps/web/lib/server/`, `apps/web/lib/contracts.ts` | Implemented with typed queries and a 4 MB response cap; live extraction awaits provider configuration. |
| Validate pinned snapshot contracts and derive private JSON plus an integrity manifest. | `scripts/build_web_snapshot.py`, `apps/web/snapshot/` | Implemented for the app's immutable revision; all 3,743 listings validate and evidence references are retained. |
| Package the Vercel application with pinned dependencies and snapshot/asset verification. | `apps/web/package.json`, lockfile, Next/Vercel configuration and verification scripts | Node 24 London functions use Vercel Authentication; cleanup verifies all seven API snapshot traces, with hosted cleanup verification pending. |
| Explain retail frontier using the hackathon submission and judging structure. | `PROJECT.md`, intention, lifecycle intent and `README` | Description, capability status, collection demo and submission fields added and reviewed; documentation checks and the offline demo passed. Team names, video, brand votes and public access verification remain pending. |
| Demonstrate the built retail frontier workflow. | `PROJECT.md`, intention, lifecycle intent and `README` | Project description focuses on implemented collection, processing, evidence review and model preparation, with a brief description of the chocolate data, a runnable collection demo and explicit modelling limits. Event information, judging criteria and submission fields were removed from the project description. |
| Diagram the data processing workflow. | `docs/data/chocolate-silver.md`, `PROJECT.md` and `README` | Added a Mermaid diagram for source collection, raw preservation, silver processing, review, eligible model inputs and portable model preparation, with purpose, output and status descriptions for bronze/raw, Silver and immutable Parquet Gold inside the diagram and its companion table. Export and the experimental trainer are implemented; real fitting, validated pricing and explanations remain pending. Documentation tests, Ruff and documentation/whitespace checks passed; diagram stages were reviewed against the silver and portable guides. |
| Integrate data documentation with current main. | Data guides, diagram, `PROJECT.md`, Gold guide, analysis evidence, checker/tests and lifecycle documents | Reconciled newer pandas, Gold and trait contribution work; all 17 data artifacts are grouped under `docs/data/`. All 391 tests, offline pinned-cache verification, Ruff, documentation checks and a 262-link audit passed. Runtime and contract bytes match main apart from documentation checker paths. |
| Group data documentation under `docs/data/`. | Data guides, `docs/data/analysis/`, `docs/data/schema-proposals/`, repository links, documentation policy and checker/tests | Moved 11 guides and evidence/proposal artifacts; updated relative links and required documentation paths. Documentation tests, Ruff, documentation/whitespace checks and a repository link/content audit passed. |
| Record EAT_HACK participation in Retail Futures and the requested requirements. | `docs/eat-hack-track-two.md`, intention, lifecycle intent and `README` | Brief covers the Track 2 challenge, submission requirements and judging criteria; source review and documentation checks passed. |
| Define typed chocolate fields, vocabularies, units, evidence states and record shape. | Dataset `contracts/chocolate/`, pinned by `schemas/chocolate/dataset-contract.json` | Initial schema implemented; extraction review pending. |
| Define mappings and model training/interpretation contracts. | Pinned dataset contracts and `scripts/chocolate_model.py` | Contracts and preparation helpers implemented. |
| Combine raw verification, exact seller deduplication, standardization, price normalization and review/eligibility. | `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, shared components, `scripts/tests/test_silver.py` | Silver implemented and verified; standalone cleanup/component CLIs serve compatibility and diagnostics. |
| Preserve broad original records, source/images and immutable captures; export public text evidence. | `plugins/category-research/`, `scripts/publish_collections.py` | Collection and export implemented. |
| Document responsibilities, schema, training, commands and compatibility helpers. | Canonical guides, `README`, lifecycle views | Contracts and documentation checks verified. |
| Maintain documents with implementation changes and apply the agent writing and testing rules. | `AGENTS.md`, `docs/documentation-policy.md`, `scripts/check_documentation.py`, `.github/workflows/validation.yml`, tests | Ownership, drift checks, writing rules and test selection rules recorded. |
| Review existing tests for useful coverage and repeated execution. | `scripts/tests/`, both plugin test suites, `docs/documentation-policy.md` | Reviewed 256 cases; consolidated seven duplicate cases and removed five redundant cases. Retained distinct preservation, integrity, identity, review, model and isolated package execution checks. |
| Package processing with chocolate/coffee profiles, stable seller identity and a harness skill. | `plugins/category-processing/`, `docs/data/category-processing.md` | Bundled tests, skill validation, isolated execution after copying the package and independent workflow checks passed. |
| Record capture/rules fingerprints, grouped mapping gaps and maintenance decisions. | Ledger, batch/summary helpers, skill references | Implemented; processing rebuilds all accepted captures. |
| Prepare generic model inputs grouped by family and encoders learned from training rows. | Portable model helpers, `prepare-model` CLI | Reviewed preparation and exclusion/failure gates verified. |
| Reject typed contract drift and retain valid category values outside selected model domains. | Profile loader, both standardization pipelines, regression tests | Verified. Runtime uses an explicit validator template. |
| Specify supermarket pricing, retailer comparisons and LightGBM/SHAP/AI explanations. | `docs/data/chocolate-modeling-design.md`, `docs/data/analysis/lightgbm-shap-explanation-design.md` | Proposed research design; active preparation contracts await migration and model fitting remains pending. |
| Explain predicted price through individual traits and one percentage per trait family. | `docs/spec.md` section 5.2.1, intention, schema/modeling and SHAP guides | Specified signed percentages of final predicted price with a separate reference share, exhaustive versioned grouping and reconciliation checks. Proposed output; contract migration, implementation and validation remain pending. |
| Move analytical contract bodies to the dataset with immutable references and verified ignored caches. | Three `dataset-contract.json` manifests, resolver/fetch/publication helpers, `docs/data/dataset-contracts.md` | Published and verified against original bytes; offline caches and both processing pipelines verified. |
| Consolidate repeated documentation and apply plain wording while preserving contracts and evidence. | Repository instructions, canonical/lifecycle guides, root and package READMEs, package skills/references | Completed; original cleanup and integration with the contract migration verified below. |
| Configure collection sections and generate processing profiles for new categories. | Collection `collection_sections`, processing `profile_builder.py`, `init-profile`, definition reference and generic engine/archive tests | Implemented: Unicode section reports, five-contract authoring, non-food quantities/currencies/tax bases and normalized study paths. |
| Discover unconfigured structured source fields and document proposals. | Processing `discovery.py`, `schema_suggestions.py`, pipeline/summary outputs, tests/reference, `docs/data/schema-proposals/` | Implemented structural discovery and worksheets; seller review metrics and selling plan terms await agent assessment. Prose investigation, a decision registry and snapshot comparisons remain future work. |
| Maintain schemas autonomously and review completed schema releases before Hugging Face commits. | `docs/decisions/agent-led-schema-maintenance.md`, canonical guides, processing skill/references and generated guidance | Standing user decision: agents apply supported local changes without approval, with evidence, versioning, tests and impact checks. Present the detailed completed release for user review before its remote commit. The harness owns this step; no popup UI or upload gate is implemented. |
| Use pytest for tests and Ruff for Python linting. | `pyproject.toml`, `uv.lock`, native pytest tests, plugin `pytest.ini` files, `.github/workflows/validation.yml`, development documentation | Implemented with locked development dependencies and CI commands. All 304 tests and Ruff checks passed after test consolidation; prior isolated package verification is recorded below. |

| Export immutable Parquet Gold and annotate all rows on the user instruction without changing eligibility. | `scripts/chocolate_gold.py`, Gold CLIs, `docs/data/chocolate-gold.md` | Implemented and locally verified, including integrity checks, pass-through values, immutable snapshots and user-review provenance. |
| Use regular, non-promotional, tax-inclusive consumer prices in every model. | Price-policy helpers, generated profiles, published original/portable contracts, specification and schema guides | Implemented, published with user authorization, and verified against immutable dataset pins; the complete 375-case suite passes. |
| Map captured product names to reviewed families while preserving raw evidence. | `scripts/chocolate_standardization/identity.py`, `reviews/chocolate/family-mappings.json`, Silver CLI and contracts | 31 families and 1,285 family-only assignments verified. Exact physical identities remain unresolved. |
| Train experimental OLS from verified Gold with family holdout and bootstrap uncertainty. | `scripts/chocolate_regression.py`, `scripts/train_chocolate_model.py`, model design and tests | Implemented and fixture fits/failure gates verified. Real Gold has zero eligible observations; no model fitted or released. |
| Reconcile Gold/modeling work with main and prepare the dataset contract release before landing. | `docs/data/analysis/gold-modeling-contract-release.md`, integration code/tests and dataset references | Combined-main checks and corpus rebuild complete. User approved the refreshed exact release, published at `d549ad91d63fb452af605df4a939c4e1f0a59bfa` with all 16 remote files verified. Real-pin tests, offline caches, Ruff and documentation checks pass; landing uses one local main squash commit. |

| Use pandas for canonical chocolate grouping, partitions, counts and row envelopes. | `scripts/chocolate_tables.py`, shared components, silver CLI and tests | Implemented; integrated with main's family mappings, fixed-price target, Gold and locked pytest/Ruff development environment. Integration verification is recorded below. |
| Analyze every chocolate schema attribute and publish verified derived output. | `scripts/analyze_chocolate_schema.py`, reports and publication receipt | Verified original pandas snapshot and 103-field analysis published at immutable revisions. Current contracts retain the subsequent Gold/family/target release. |

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

### Pipeline and model preparation verification

The verification below was recorded on 2026-10-03. Each run establishes the stated
implementation scope. Dataset manifests and quality reports own build counts and
readiness; `complete_snapshot` establishes accepted input consistency.

| Verification | Recorded result and evidence |
| --- | --- |
| Trait contribution and family percentage specification | On 2026-10-03, `uv sync --locked`, `uv run pytest scripts/tests/test_documentation.py` (26 cases), `uv run ruff check .`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Direct arithmetic checks verified reference-plus-trait reconciliation for positive, negative, cancelling, zero and near-zero log contributions, and identical unit/pack shares. Semantic review kept trait families distinct from product identity families and the allocation distinct from price effects and global importance. This validates the documentation and formula only; model contracts, runtime explanations and fitted-data results remain pending. |
| Data documentation integration with main | `uv sync --locked`, `python3 -B scripts/fetch_contracts.py --all`, `uv run --no-sync pytest` (391 passed), `uv run --no-sync ruff check .`, `python3 -B scripts/fetch_contracts.py --all --offline`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Audited 262 local links and all five relocated JSON evidence files against main. Verified 94 runtime/test/contract/identity/dependency files against main; only documentation checker paths and their existing tests differ. Updated the diagram and project description to distinguish implemented Parquet Gold/export/training helpers from zero eligible real chocolate inputs and pending validated pricing/explanations. |
| Data flow diagram | `uv sync --locked`, `uv run pytest scripts/tests/test_documentation.py` (26 passed), `uv run ruff check .`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Reviewed the Mermaid stages against the documented collection import boundary, combined silver build, seller preservation, review gates and portable model preparation. Bronze labels the existing raw archive; after main integration, Gold describes the implemented immutable Parquet training interface and experimental trainer. Stage purposes, retained data and implementation status appear directly in the Mermaid nodes; current chocolate eligibility and planned model fitting are explicit. |
| Data documentation relocation | `uv sync --locked`, `uv run pytest scripts/tests/test_documentation.py` (26 passed), `uv run ruff check .`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Audited 213 local links across repository and plugin documentation. Compared all 10 moved Markdown guides/proposals with their previous content after resolving link destinations, and verified the JSON review evidence retained its SHA-256. No stale former paths remain. |
| retail frontier project description | Product focus revision: `uv sync --locked`, `uv run pytest scripts/tests/test_documentation.py` (26 passed), `uv run ruff check .`, `python3 -B scripts/check_documentation.py` and `git diff --check` passed. Reviewed capability and data descriptions against the implementation overview, raw/silver guide and illustrative sample. Removed event details and judging/submission tables; the demo output path is `data/product-demo`. Earlier verification of the embedded collection demo preserved five original records and sample metadata across repeated imports with network blocked, with completeness still `not_verified`. The demo was not rerun for this prose and output-path revision; silver processing and model fitting remain outside its scope. |
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

| Gold/modeling integration with main | Main `bb6b73d` was reconciled on the task branch, retaining generic profiles/discovery, immutable dataset references, pytest and Ruff. `uv sync --locked` passed. All 375 pytest cases passed in a disposable checkout using verified prepared contracts and test-only references; source pins remain on the actual published revision. Ruff, documentation and whitespace checks passed. Explicit draft-contract Silver `silver-2e61c59362d10096186ef5b1` retained 3,743 listings and 4,347 exact original capture objects, matching raw snapshot `raw-snapshot-70239771976a75a48c5d99db`. All 1,285 assignments applied without conflict/inactive records; 402 of 2,134 candidates have families. Gold `gold-1342c4177a1b08c325f69f52` and user-reviewed `gold-d9478bc242bc93a7ac0cb986` preserve candidates/eligibility. Readiness run `model-run-aae002fdc9b5247b60d53902` recorded zero eligible inputs and did not fit. This pre-publication check used local contracts; the subsequent publication and real-pin validation are recorded below. |

| Gold/modeling contract publication and final checks | On 2026-10-03 the user approved the refreshed publication parent/card. Guarded Hugging Face commit `d549ad91d63fb452af605df4a939c4e1f0a59bfa` has parent `db32e43635793a0edd1308df4bd0dee112ddbe44`. All 16 uploaded files matched their approved bytes, preserving newer Silver/analysis sections and remote snapshots. Three Git manifests pin the verified revision, all caches verify offline, and `uv sync --locked` remains valid. The actual repository suite passed all 375 cases against these published pins in 8.04 seconds. Ruff, full documentation/change-coverage checks and whitespace checks passed. CI has not run here; corpus data/model snapshots remain local and no real model has fitted. |

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

The [silver guide](../data/chocolate-silver.md) and [acceptance scenarios](../spec.md#8-acceptance-scenarios-for-stages-1-and-2)
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
   deliver supported insights and testing for proposed products. Implement the
   specified trait contributions and family percentages with a versioned mapping,
   reference share, numerical reconciliation and unavailable-explanation checks.
3. Verify native installation and execution across agent harnesses.
4. Develop incremental caches, automatic harness dispatch/scheduling and selective
   migrations as future work. Current maintenance uses grouped evidence, triage,
   versioned diffs, tests and impact review within the task; accepted changes
   rebuild history with stable seller identities and immutable data/model snapshots.
5. Research methods for value for money before implementing scoring.

6. Verify live browser/WebGL interaction and complete provider/tunnel setup for
   image/text extraction in the web app. Pricing-model integration into the app
   remains cancelled.

### Original pandas verification and publication

This proof predates main's later family taxonomy and fixed-target contract
release. It describes the preserved immutable outputs and the original runtime,
rather than the merged implementation or current dataset contracts.


The original pandas build selected pandas for seller grouping, role partitions,
coverage/exclusion aggregation and top-level derived envelopes.
Component builders retain a standard-library default; the portable processing
package remains self-contained. `processing_runtime` records backend, Python
implementation/full version and pandas/NumPy versions in report, manifest and
derived fingerprints. Original captures and versioned analytical contracts
retain their existing meanings. Both canonical and analysis scripts pin pandas
2.2.3 in PEP 723 metadata; direct Python callers must install that dependency.

The analysis helper uses an explicitly supplied local silver snapshot, verifies
product/profile/model-design hashes and reports every profile field with
separate evidence/review states, exact selected-value frequencies, source
coverage and numeric quantiles by scope and qualifier. It records caller-supplied
immutable dataset provenance rather than fetching evidence. Attribute, group,
source and value counts for all 103 fields in the inspected snapshot match the
preceding report exactly.

Verification completed on 2026-10-03 using CPython 3.12.14, pandas 2.2.3 and
NumPy 2.3.5. All 184 repository script tests, 13 collection-plugin tests and 75
portable processing-plugin tests passed (272 total). The full corpus build
completed with `complete_snapshot`, no archive/extraction errors and
`release_ready=false`. The previous implementation produced
`silver-eef578e917ea00f9bd59f7a8`; the pandas implementation produced
`silver-2f97cfe8b8c50ecfa79ebf46`. Both used the same raw snapshot,
`raw-snapshot-70239771976a75a48c5d99db`.

Strict canonical-JSON record multiset comparisons matched across all 17 JSONL
tables after removing only the top-level `dataset_version` and
`source_dataset_version` fields. Every nested original capture remained
identical. Quality-report statistics and limitations matched after removing
runtime/version metadata. All 22 managed output hashes and byte lengths were
verified, and all four copied contracts matched byte for byte. A repeat build
reproduced the same pandas dataset version, byte-identical manifest and all
managed file hashes and lengths. The
[verification record](../data/analysis/chocolate-pandas-processing-verification-2026-10-03.json)
records these results. On 2026-10-03, the verified pandas output was published
as an [immutable silver snapshot](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/c1725ff8bbeef8f78c7182fd67af5bde75ef65ef/silver/chocolate/uk/silver-2f97cfe8b8c50ecfa79ebf46) at dataset revision
`c1725ff8bbeef8f78c7182fd67af5bde75ef65ef`. The latest pointer selects this snapshot.
The [schema analysis](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/blob/db32e43635793a0edd1308df4bd0dee112ddbe44/analysis/chocolate/uk/silver-2f97cfe8b8c50ecfa79ebf46/schema-popularity.json) and pandas verification report were published
at revision `db32e43635793a0edd1308df4bd0dee112ddbe44`; the analysis records the snapshot
revision and exact input hashes. Its 103-field statistics match the previous
analysis, with 24 attributes populated and 79 having zero known-value coverage.

All 23 snapshot files and both analysis reports passed remote size/content-hash
checks; analysis reports and selected metadata were also downloaded and checked
with SHA-256. Raw exports, previous snapshots and contract bytes were preserved.
Hugging Face appended six LFS storage rules for new snapshot paths while retaining
all existing rules. The [publication receipt](../data/analysis/chocolate-pandas-publication-2026-10-03.json)
records both immutable revisions and per-file hashes. Contract semantic versions
and existing immutable manifest pins remain unchanged. The snapshot remains
`release_ready=false`; publication does not resolve extraction or review gaps.


### Pandas integration with current main

The pandas source commit was merged with main's Gold, reviewed family mappings,
regular consumer-price policy, pytest and Ruff changes. The merged build retains
`family_mappings` alongside the pandas backend, identity-mapping fingerprints,
managed family registries/review packets and current immutable contract pins.
The original 272-test report remains historical; the integration uses the locked
CPython 3.13 development environment with pandas 2.2.3, NumPy 2.2.6 and PyArrow
21.0.0. All 391 pytest cases passed, including exact pandas/standard-library
record parity, evidence preservation, family identity and Silver/Gold/training
gates. Ruff, the documentation guard, whitespace checks and all three verified
contract caches passed. Both parents' existing capabilities and contract pins
are retained for the local squash landing.


## Gold eligibility for every entity and training refresh

On 2026-10-03 the user requested every Gold entity model eligible and authorized
messages to all three chocolate training chats asking them to refresh and refit.
Implemented `scripts/make_chocolate_gold_eligible.py` and
`chocolate-gold-bulk-eligibility-1`. Both training tables contain every candidate
with true eligibility and empty current exclusions. The exact parent snapshot
retains original flags, exclusions, evidence provenance and workflow annotations.
The loader compares promoted rows to parent analytical values before returning
all rows. Contracts retain their original bytes and versions. The override is
Gold workflow selection; missing regular prices and model identities still need
actual values for a fit. No fitted model is implied by eligibility.

Eight new cases cover original/reviewed parents, mixed eligibility, unchanged
missing values, original snapshot preservation, replay and damaged destinations,
empty views, missing authorization, recomputed-hash target/flag/order corruption,
false readiness reports and parent corruption. Focused Gold tests passed: 35.
Offline pinned contract verification and the locked development installation
passed. Full suite, documentation checks and shared snapshot/refit handoff are
recorded below after completion.

The real operation used the newest available training snapshot,
`gold-56817976905f24210105f069`, from
`silver-485af2f8e7fae127cd73578b`. Its new immutable sibling is
`gold-8b897101474becaef946922b`; manifest SHA-256:
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Both Parquet views and the verified loader contain 2,134 eligible candidates,
compared with zero eligible rows in the parent. All regular unit-price targets
and exact variant IDs remain null; family IDs are present on 402 rows. Source
contracts and price policy retain their original bytes and versions. This
change publishes a local immutable snapshot; no remote dataset files changed.

`uv run pytest` passed all 399 tests in 9.91 seconds. Ruff, the documentation
guard and whitespace checks passed. Messages delivered to all three existing
training chats with the exact snapshot path, hash, loader support and instruction
to pull/copy it and refit: Train retailer median chocolate model; Train hedonic
chocolate model with brand; Train matched retailer chocolate comparison. All
three acknowledged and began their refresh/refit. Training completion is recorded
in their individual model runs; Gold eligibility alone does not establish it.


## Current-price target at the user's request

On 2026-10-03 the user replaced the chocolate study's regular-price requirement
with collected current displayed prices and requested this assumption in
`PROJECT.md` limitations. Implemented a versioned current target contract and
shared preparation from unchanged verified Gold observations. Current training
requires positive GBP displayed price and actual edible pack weight, with no
separate regular-price, promotion/review or confirmed-tax gate. Explicit current
fields and equal legacy aliases are recorded under `current-consumer-price-1`;
source regular prices, source evidence and historical studies are preserved.
The three training chats received the new user instruction and will use the
shared helpers and contract for fresh refits. `PROJECT.md` documents promotions,
membership conditions, unverified tax inclusion and different capture dates.

The real preparation considered all 2,134 eligible candidates and produced 630
current unit-price targets. There are 1,503 missing edible weights and one
missing current price. The OLS attempt saved concrete identity and repeated
listing blockers instead of a missing regular-price gate. Contract publication
and final validation are recorded below after completion.

The current-price contract set was published to the authoritative dataset at
`d743cb8dbca37f5241cccd444a16165523304f6c`, adding four files under
`contracts/chocolate-current-price/` and updating the contract-set index. All
five uploaded files were downloaded and verified byte for byte. The product
schema (`chocolate-schema-1`, 103 attributes), source mappings
(`chocolate-source-mappings-2`), original evidence and historical source/portable
contract pins retain their original bytes and versions. The new model design is
`chocolate-pricing-current-price-design-1`, SHA-256
`c7b7f55d0424f8bdbef2fbc76e7b75475753eaad8021f7e1acd266de284ac8de`.
A new small Git reference pins this immutable set; the resolver, all-contract
fetcher and offline documentation guard verify it through the existing cache
protocol. No typed product schema change was made.

All three existing training chats received the exact target pin, verified local
contract directory, shared helpers, actual target counts and instruction to
refit under the current-price policy. The real OLS attempt considers all 2,134
eligible candidates and selects 800 bar observations. It produces 630 current
unit-price targets across the candidate table and saves explicit identity and
repeated-listing blockers, with no missing-regular-price gate. Independent model
outcomes belong to their individual chats and run artifacts.

Ten new tests validate current-price arithmetic, missing weights/prices, invalid
amounts/currencies, no regular-price fallback, quantity/provenance conflicts,
source preservation, current target metadata, a synthetic regression and an
end-to-end fitted model run with regular prices absent and tax/review unresolved.
`uv run pytest` passed all 409 tests in 9.38 seconds. Ruff, documentation checks,
whitespace checks and offline verification of all four contract sets passed.
`PROJECT.md` limitations and the modeling specification record temporary/member
prices, unverified tax inclusion and different source capture dates. These
assumptions do not establish causal effects or model release readiness.

## Independent LightGBM with brand session

Implemented `scripts/chocolate_experiment.py`, `scripts/chocolate_lightgbm.py`, `scripts/train_chocolate_lightgbm.py` and a synthetic fixture builder. The [model guide](../data/chocolate-lightgbm-with-brand.md) records the explicit working contract, common seed 1729, family partitions, fold-specific weights and preprocessing, known-brand identification/support gates, bounded LightGBM tuning, frozen tree count, retailer conformal calibration, native TreeSHAP reconstruction and immutable artifact verification.

Pinned original and both portable contract caches verify offline at dataset revision `d549ad91d63fb452af605df4a939c4e1f0a59bfa`. The available raw archive rebuilt Silver `silver-f651a7faea94ed5a7f003e64` and Gold `gold-4939405fcf8724686f9ee32c` in this worktree: 3,743 seller listings, 4,347 captures, 2,134 candidates and zero eligible inputs. A real training attempt saved a readiness report with exact exclusion counts and missing shared field blockers. No real model or real-data interval is fitted, calibrated, release-ready or uploaded. The existing OLS and portable preparation contracts retain their published pins; a coherent handoff migration and evidence review remain prerequisites.

Final checks passed: `uv sync --locked`, all three pinned caches verified with `python3 -B scripts/fetch_contracts.py --all --offline`, all 392 pytest cases (17 new native estimator checks, no skips), Ruff, documentation guard and whitespace checks. The synthetic run `lightgbm-run-ef4f9838ceafa12e44488f38` fitted 1,030 trees on 1,440 observations in 240 families, split into 144 fitting, 48 calibration and 48 final-test families. Its 288 supported test listings yielded unit MAE £0.02443/100 g, pack MAE £0.01940, median APE 0.6435% and unit signed bias −£0.00220/100 g. Each retailer has 48 calibration representatives; synthetic test coverage is 95.83% for Ocado and 91.67% for Waitrose. These are fixture acceptance results, with release/champion decisions pending.

After the user's confirmation that Gold is verified, the session re-scanned available snapshots and the remote dataset. Remote revision `d549ad91d63fb452af605df4a939c4e1f0a59bfa` has no Gold files. Another available snapshot, `gold-56817976905f24210105f069`, passed current loading/integrity checks and was run through the trainer. It has 2,134 candidates, 402 family assignments, zero exact variants, zero regular/log targets and zero eligible inputs. Current attempt `lightgbm-run-746f4a1a0b8e82fdf753b987` saved those actual failures with experiment `05b3990e86a348008aeb6a6e6e2163bf47e7bba92a695e861172c73af20e46af`. The session's own rebuilt-input attempt is `lightgbm-run-64e34a9a917e83313f2d5a9c`, experiment `f4105c926fe13e33654044104459da2fce70138384f1854cd91b1266b8793c0b`. The [readiness record](../data/analysis/lightgbm-with-brand-readiness-2026-10-03.json) retains exact hashes, source identities, counts, metrics and status. A verified populated snapshot is still needed for actual training and the authorized model upload; source values and eligibility were preserved.

### LightGBM with brand integration with main

Integrated local main `f1ec072` into the committed training branch, preserving
pandas Silver/schema analysis and the data guides under `docs/data/`. The new
LightGBM guide and readiness record follow that structure, with canonical and
lifecycle links updated. The combined lock retains pandas 2.2.3, NumPy 2.2.6 and
PyArrow 21.0.0 alongside LightGBM 4.6.0 and SciPy 1.15.3. `uv sync --locked` and
all 408 pytest cases passed, including the 17 native LightGBM acceptance checks.
All three pinned contract caches verify offline; Ruff, documentation and
whitespace checks pass. Historical immutable fixture/readiness artifacts retain
their original data, package and implementation identities. Real-data fitting,
contract migration, comparator release decisions and model upload remain pending.

## Commit, Gold publication and main integration

The user requested committing this task, merging to local main and publishing
changed data to Hugging Face. Source changes were committed on
`codex/gold-current-price`. Main's reorganized `docs/data` layout and updated
PROJECT overview were integrated while preserving the current-price limitations.
A later independent LightGBM commit on main was also incorporated; its historical
readiness artifacts and implementation remain preserved.

Published `gold-8b897101474becaef946922b` and its latest pointer at immutable
Hugging Face revision `95c5fbd0ab5fa9a41fa5333648321d95f16927a7`. All 25
remote files (24,549,078 bytes) were downloaded, compared to the local snapshot
and loaded successfully with `verified_gold`. Both primary tables contain all
2,134 eligible rows. Git records a small reference pinning the revision,
manifest SHA-256 and managed file hashes; dataset bytes stay in Hugging Face.
The previously published current-price model contract retains revision
`d743cb8dbca37f5241cccd444a16165523304f6c`. No fitted real-data model is
implied by publication. Updated handoffs were sent to the active LightGBM
without-brand chat; the with-brand chat had been archived when dispatch was
attempted. Its landed historical trainer remains available on main.

Final integrated validation passed: `uv sync --locked`, all 426 pytest cases
(including the native LightGBM checks), Ruff, documentation and whitespace
checks, and offline verification of all four contract sets. The landing procedure
refreshes main from its upstream and guards the target revision before creating
one squash commit. The source and target file trees must match and both
worktrees must be clean after landing. Real-data model fitting remains subject
to each training chat's preparation and identification gates.

## Independent hedonic_without_brand session

Implemented the assigned family-weighted log-linear estimator in `scripts/chocolate_hedonic.py`, exposed through the existing trainer under an explicit unpublished working policy. Fitting-only grouped selection, common brand-identification probing, optional cocoa preprocessing, retailer interactions, family bootstrap, split conformal calibration, support/domain outputs and immutable run verification are covered by native pytest fixtures. The [implementation record](../data/analysis/hedonic-without-brand-implementation.md) owns exact policies and reproducible commands. Real raw-to-Silver-to-Gold rebuilding preserved 3,743 listings and 4,347 captures; Gold `gold-4939405fcf8724686f9ee32c` retains 2,134 candidates and zero eligible rows. Missing reviewed regular-price/tax/quantity/identity evidence and recipe/cohort/pack-count handoff declarations block real fitting. Comparator gates, champion selection, aligned producer/portable contract migration and release review remain pending. Trained artifact upload is authorized, but no real fitted artifact is available for publication.

Verification for this session: all 398 pytest cases passed, including 23 assigned
hedonic cases; Ruff, documentation/change coverage, whitespace checks and all
three offline pinned caches passed. The immutable real attempt is
`model-run-b8d9ff2c6e93b65b693a3fa0` and the explicitly synthetic validated run is
`model-run-89faf11be25b98e1a7761e6a`. The latter supports 240 testing rows in 120
families, with fixture MAE 0.136074 GBP/100 g and 0.173709 GBP/pack, and 200
successful family bootstrap draws. These figures describe synthetic evidence.
After the user's Gold verification update, current local and remote inventories
were checked and training rerun. Actual current Gold values still have zero
positive regular targets and zero exact variant IDs; all 2,134 price observations
have unknown tax basis. The current-value audit is saved with the readiness
report. No real fitted artifact exists to upload; producer migration and evidence
completion remain concrete prerequisites, without requiring another confirmation
of the user's Gold verification.

The user subsequently authorized publication of the explicitly synthetic trained
fixture. Its 15 model/metadata files were uploaded under
`model/hedonic_without_brand/model-run-89faf11be25b98e1a7761e6a/` in Hugging Face
commit `419150708bbbca16a738ff36a3c0b9373e8cda8e`, preserving other dataset contents.
Every uploaded file was downloaded and verified; the
[publication receipt](../data/analysis/hedonic-without-brand-model-publication.json)
records hashes. It is experimental fixture evidence, with no real-data fit or
release claim. Source/runtime files and Gold inputs were excluded from upload.

Integration with local main preserved its data-guide relocation, current-price
contracts, eligible Gold reference and LightGBM dispatch. The historical hedonic
working policy explicitly rejects a different price basis. The uploaded inference
bundle was downloaded at commit `419150708bbbca16a738ff36a3c0b9373e8cda8e`: all 15
file hashes passed and the integrated loader reproduced all 240 supported frozen
fixture predictions. The merged locked environment and all four contract caches
were verified. The complete integrated suite passed 461 tests; four additional
CLI routing regressions cover both model IDs and both argument spellings. The
focused hedonic suite now contains 27 passing cases. Ruff, documentation and
whitespace checks passed before the requested local squash into main.
