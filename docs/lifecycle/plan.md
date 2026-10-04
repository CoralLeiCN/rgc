# Project implementation plan

## Schema workflow and Bronze source directories: main integration

The user requested committing this task and merging it into local `main`.
The task branch is `codex/bronze-schema-workflow`; its initial implementation
commit is `b625f2e7`. Main was refreshed from its configured upstream at
`89d76b38ee206278db1ad1d0606564c625ee1199`. Integration preserves main's blonde
and mixed chocolate extraction, inferred Gold publication records, model refit
and web changes. Two documentation conflicts were resolved by retaining those
extraction details alongside the dedicated initial-schema skill, Bronze-to-Silver
entry conditions and downstream model-preparation boundary.

The landing includes the initial-schema proposal/report, source-grouped collection
and readers, tests, rationale and the verified local raw migration record. Raw
data and ignored research execution files remain local. No analytical contract
or dataset publication is part of this Git operation.

Validation: locked Python dependencies and all four offline contract caches
verified. Ruff, the documentation guard and whitespace checks passed. The full
pytest suite passed 631 cases in 38.40 seconds, with seven web runtime cases
skipped because their fixtures were unavailable. The web files match refreshed
main exactly. These results validate the source tree for the single squash
commit on main.


## Main refresh to the inferred-Gold model release

Merged local main `137ed9e4d497f903041182fdbb435a2baceeaec0` into
`codex/matched-retailer` after fetching GitHub main
`364bafc70008b384250dc6d309592e22adad47a3`. Local main includes that remote
revision. The merge applied cleanly and preserves the matched estimator and
its task history. Incoming changes include the price-slice terrain interface,
Gold inferred preparation, and the separately published LightGBM without brand
model. This integration does not itself refit or publish a model.

Validation: locked Python dependencies and all four offline contract caches
verified; Ruff and the documentation guard passed. Node 24.20.0 typechecking,
price-slice invariants and the production build passed, including source-data,
asset, pinned model and all eight API trace checks. All 588 pytest cases passed
in 38.23 seconds without skips; final whitespace checks passed.

## Latest main integration for the matched retailer branch

Integrated local main `082c1857261b77244f07152345d6a75c8fced1ba` into
`codex/matched-retailer` after fetching GitHub main. The fetched remote head was
`c4a6de4bb9482a80275e3ae77628dd8c7aab5ea8`, an ancestor of local main. Resolved
the matched estimator and guide conflicts using the current Gold population
rules: every Gold candidate is considered automatically, model-facing rows
omit eligibility fields, and actual price, quantity, identity and context still
determine fit readiness. Retained the separate matched estimator, shared target
binding, immutable runs, numerical diagnostics, CLI dispatch and task history.
The incoming retailer baseline and Gold inferred web collection remain distinct
interfaces. No dataset rebuild or real model fit was performed for this merge.

Validation: `uv sync --locked` and all four offline contract caches passed.
The full pytest run passed 568 cases, with six web serving cases initially skipped
because their fixture was absent. After a locked Node 24.20.0 install and pinned
fixture preparation, all six passed in the focused suite. Ruff and the
documentation guard passed. Node 24 typechecking and the production build passed
snapshot, asset, model and all eight API trace checks. Whitespace checks passed.

The raw, combined Silver and immutable Parquet Gold architecture, chocolate
schema, model preparation, documentation maintenance and standalone processing
package have passed implementation checks. Experimental training code and
reviewed family assignments are available. The published Gold snapshot contains
2,134 candidates marked eligible under the user's instruction; current-price
preparation derives 630 unit-price targets. Missing inputs and model requirements
still block real fitting and supported price testing. Historical regular-price
attempts retain their recorded blockers. Native installation across harnesses is
unverified; scoring value for money awaits research.

The Vercel retailer workspace implements a layered trait terrain, typed cohorts,
product configuration, observed-price analysis and extraction adapters. Its
published snapshot and disclosed demo recipe have their own verification below.
Local Chromium verified family navigation and terrain hover/selection/orbit
interactions, including price slices. Browser checks also verified photo selection,
uploads and applying extraction results from local Codex. Other browsers and
hosted interactions remain unverified for the combined application.

Canonical requirements: [specification](../spec.md),
[silver responsibilities](../data/chocolate-silver.md),
[Gold responsibilities](../data/chocolate-gold.md),
[chocolate schema](../data/chocolate-schema.md),
[portable processing](../data/category-processing.md) and
[documentation policy](../documentation-policy.md).

## Current work and files

### Bronze directories grouped by source

The user requested one website parent directory for parsed Bronze product JSON.
Collection 0.3.0 writes new listings beneath
`products/<source_key>/<product_id>/`, using safe stable source keys. Missing,
null or empty keys retain their original records under `_unknown`.
Repeat captures append to the same product, including existing flat locations;
source changes and ambiguous duplicate indexes fail instead of combining sellers.
Chocolate and portable readers, snapshot checks, archive verification and local
evidence export support the grouped and legacy layouts. Processing 0.3.4 retains
stable seller UID semantics. Source grouping supports source-specific mappings
and a shared category analytical schema. Collection skill/import instructions
and affected processing guides document this boundary.

At the user's request, the [specification rationale](../spec.md#why-bronze-is-grouped-by-website)
now explains why website structures provide a useful boundary for source
sampling, parser development, missing-value review and maintenance. Intention,
the processing guide and the standalone collection import contract carry the
same reasoning. They require sampling variations within a website and retaining
shared category field meanings. This follow-up documents the design; it adds no
runtime behavior or migration. Documentation and whitespace checks passed.

The user subsequently requested moving the existing JSON and explicitly declined
redirects or backward-compatibility links. The physical relocation moves all
3,743 complete product folders into 24 website parents, with 4,347 captures.
Archive-managed paths are rewritten directly in indexes, histories and run
reports; raw source records, descriptions and artifact/image bytes retain their
content. No runtime alias, symlink or old-path lookup is created. Original
index/history hashes change with the storage metadata. Frozen research inventories
and earlier exports retain their pre-move meaning and need a fresh inventory for
use against the reorganized archive. No data or analytical contracts are published.

The local execution evidence is in
`data/investigation/2026-10-04-bronze-source-move/`. Baseline verification passed
all 4,347 histories and 19,462 referenced artifact files. The staged move checks
26,904 files and prepares 8,104 metadata updates, with recoverable originals kept
outside the active archive during execution. Three focused tests passed for
physical relocation, unchanged original evidence, concurrent-change rejection
and rollback after a simulated write failure. The move completed with 3,743
indexes under exactly 24 source directories, zero flat indexes, zero remaining
import locks and zero symlinks. Post-move verification passed all 4,347 histories
and 19,462 referenced files (10,759,101,910 bytes), with zero integrity failures.
All 18,798 moved source/image artifact files retained their original hashes.
A separate comparison confirmed every original raw record and information object
across all 4,347 captures remained equal. The active archive verification report
was replaced with the new successful result. Documentation checks, 27
documentation tests, repository Ruff and whitespace checks passed.
Validation: the locked environment was synchronized offline and all four pinned
contract caches verified with `python3 -B scripts/fetch_contracts.py --all --offline`.
The affected collection/processing/archive/export/Silver suite passed 229 tests.
`uv run pytest` passed 579 tests with seven existing web-runtime skips. A final
focused 21-test run also passed after ensuring duplicate indexes remain hashed
in the input snapshot. `uv run ruff check .`,
`python3 -B scripts/check_documentation.py` and `git diff --check` passed.


### Fresh chocolate schema from Bronze

The user requested running category-schema from scratch and comparing the result
with the old schema. The [report](../data/schema-proposals/chocolate-bronze-reconstruction-2026-10-04.md)
records 3,743 index/latest-capture bodies from 24 sources, 4,347 retained captures,
96 selected listing summaries, 24 source-format summaries, 10 targeted detailed
records (97 unique listings), and 13 reviewed semantic cases. It inventories raw
structure/prose candidates without importing the existing schema or extractors.
The 75-field catalog was semantically refined and frozen before the old profile
was opened; earlier conversation means this is not a cognitive blind evaluation.

The old profile at `d549ad91d63fb452af605df4a939c4e1f0a59bfa` was hash verified.
Its 103 fields have 44 counterparts/restructured concepts, 39 consolidations
requiring derived views, eight envelope/configuration moves, four evidence-only
moves and eight explicit catalog gaps. The report includes the full catalog and
crosswalk. The new count includes nine offers and three reviews, so counts are
not completeness measures. Post-design review of three additional originals
confirmed two genuine ruby-chocolate descriptions and a personalized-name
counterexample. Ruby is omitted by the frozen fresh vocabulary and must be
retained in a subsequent reviewed design.

Local working artifacts live in
`data/investigation/2026-10-04-schema-from-bronze/`; the frozen catalog SHA-256 is
`f915e32ba90319c8c3dd9d4c74ecaa8e8ec4320e18aa50d3e8958e2811f410be`.
All input index bytes were rehashed unchanged, 148 schema/case references resolve
to original capture/pointer values, and all 103 crosswalk entries resolve.
The old cocoa schema already supports the Chococo 47% minimum declaration;
its prior missing value remains an extraction/review gap. No working contract,
Silver/Gold data or publication was changed. Original artifact bodies, image
pixels/OCR and earlier capture bodies were not semantically investigated.
Final validation passed: 27 documentation pytest cases, repository Ruff and
explicit Ruff checks for all five ignored research scripts, documentation guard
and whitespace checks. The final provenance verifier rechecked all 3,743 input
hashes, the 148 draft/case references, three post-design source references, the
frozen schema hash and the complete 103-field crosswalk. No runtime semantic
suite was rerun because this task changed research artifacts and documentation.

### Bronze layer naming

The user defined the preserved raw-data layer as Bronze. The canonical
specification, intention, collection and processing guides, stage diagram,
project overview and schema skill now use Bronze → Silver → Gold. Collection
writes Bronze, schema creation researches it, and category-processing begins
with Bronze data and a generated schema before producing reviewed Silver.
Bronze is a formal layer name, replacing the earlier presentation-only wording.
Storage paths, raw format identifiers, original evidence and immutable snapshots
retain their existing contracts; this terminology change requires no migration.
Validation passed: three processing package tests, three collection packaging
tests, Ruff, documentation and whitespace checks. The schema and processing
skills passed quick validation. Collection packaging verifies its existing
`compatibility` frontmatter; the generic quick validator rejects that preexisting
supported field, so its result is not a collection validation pass. The installed
schema skill matches all maintained files by SHA-256 and its links resolve.

### Dedicated category schema skill

The user requested a dedicated skill for researching raw category data and
creating the initial schema. Processing package `0.3.3` includes
[category-schema](../../plugins/category-processing/skills/category-schema/SKILL.md)
with field meanings, types, units, scopes, qualifiers, original evidence,
coverage, rationale and semantic checks. It can propose or finalize the initial
catalog without a fixed file count, processing runtime or model target.
Initial draft refinement stays in creation; existing-schema refresh, review and
extension stay in processing maintenance.

The latest responsibility split moves the definition/example and executable
validation/release references into category-processing. Schema creation hands off
a catalog and evidence. Processing configures `source-mappings.json` and
`pipeline.json`, serializes the catalog into `profile.json` and derives the typed
`product.schema.json`. The model-handoff step owns `model-design.json` decisions.
Processing assembles the complete profile after those decisions are available.
The generator and loader still require all five contracts together. No runtime
logic, analytical contract, automated research engine or proposal registry changed.
Public guides and routing now describe this ownership, and the existing nonfood
fixture follows the definition example at its processing location.

The latest stage correction makes the processing skill check readable preserved
raw data and a generated schema before applying processing. Missing schemas route
to category-schema; missing raw data routes to collection. The skill now finishes
at reviewed Silver. Model design and preparation of training inputs, family
splits, encoders and matrices move to the downstream Silver-to-Gold reference;
the old model-handoff path forwards there for compatibility. Public workflow
commands no longer include `prepare-model` as a processing step.

Runtime migration remains pending: the portable loader/generator still requires
`model-design.json`, and Silver builds still emit legacy training views. The
existing downstream helper writes JSONL/encoder outputs and does not export
Parquet Gold. These limitations are explicit in skill and guides. No runtime,
analytical contract, source evidence or historical snapshot changed here.
Stage-scope checks passed: ten focused package/profile tests, both skill
validators, Ruff, offline verification of all four pinned contract caches, the
documentation guard and whitespace checks. The installed schema skill matches
all three maintained files by SHA-256 and its local references resolve.

The repository skill is the canonical maintained initial-creation source;
`/Users/coral/.codex/skills/category-schema` is its synchronized distribution.
The standalone skill includes only its raw-research reference and UI metadata.
Contract assembly needs the separately available processing runtime.

Earlier validation: locked offline environment, all four pinned contract caches
verified, 568 pytest cases passed and seven web integration cases skipped. Scope
and purpose refinements passed ten focused package/profile tests, skill validation,
Ruff, documentation and whitespace checks. The responsibility split also passed
ten focused package/profile tests, Ruff, skill validation, the documentation
guard and whitespace checks. All four pinned caches verified offline. The
installed skill now has three files, all matching the maintained source by
SHA-256; its references resolve locally and its frontmatter validates.
Execution across other harnesses remains unverified.

The retailer median branch integrated local main
`cd9e7df8eb7f50aee33d3fce5ca9f0509aff8deb`, retaining both experiment interfaces
and the independent baseline. It downloaded and verified the 24 manifest-pinned
Gold files at immutable revision `95c5fbd0ab5fa9a41fa5333648321d95f16927a7`.
Fresh run `retailer-median-cb2a4f9f896cd54f275d5031` binds the exact Gold publication
pin, accepts 2,134 eligible rows and derives 630 current targets. Zero complete
inputs remain because product identities and population/context values are
missing. All 29 managed artifacts and an identical replay verified; no real
model or upload resulted. The [integration/refit record](../data/analysis/retailer-median-training.md#refit-after-integrating-main-and-the-published-gold-snapshot)
contains the exact command and remaining blockers.


The current-price retailer median refit follows the user's superseding target
instruction. The published target pin is revision
`d743cb8dbca37f5241cccd444a16165523304f6c`, contract set
`contracts/chocolate-current-price/`, policy `current-consumer-price-1`.
The trainer applies its exact target to the baseline's selected features,
preserves Gold/source bytes and saves target contracts, explicit current fields,
documented aliases, actual model sample and per-row readiness. Its default scope
is the entire immutable snapshot; optional UTC bounds filter source capture times.
Promotion, tax and price review are retained as limitations, with no target veto.

Real run `retailer-median-385414893ddde39bcfb27060` accepted all 2,134 eligible
rows and derived 630 unit-price targets. Missing variant IDs and population
boundary values in every row, plus quantity/family/context gaps, leave zero
complete model inputs. Its 28 managed artifacts record concrete blockers. No
real fitted model or upload resulted. Synthetic current-price run
`retailer-median-6d261c66b3340160dc8efb92` fitted 100 observations in 50 families;
final MAE is GBP 0.40/100 g and GBP 0.32/pack with 100% support. These are software
validation metrics. The [current refit record](../data/analysis/retailer-median-training.md#refit-with-the-published-current-price-target)
owns the command, contract identity, full missingness and artifact inventory.

Current-price verification: the locked environment and all four contract caches
passed offline checks; all 422 pytest cases passed. Ruff, documentation and
whitespace checks passed. All 28 real-readiness and 34 fixture managed artifacts
matched their hashes/lengths, and both immutable runs passed identical replay.
The final real Gold manifest retained its supplied hash. Required data completion
is upstream variant/family and population/quantity/context values; fitting and
model upload remain blocked by those actual gaps.


The explicit eligibility snapshot `gold-8b897101474becaef946922b` has been copied
and verified against supplied manifest SHA-256
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Integrated Gold bulk-eligibility loading validates the complete embedded parent
and exact analytical preservation. The trainer binds authorization provenance
and reports missing values rather than treating old eligibility flags as blockers.
Refit `retailer-median-07a021020a85a1f4dfcc6b64` accepted all 2,134 eligible rows,
then stopped on 2,134 missing targets/variant IDs and 1,732 missing family IDs,
plus other required inputs and an undeclared window. It saved immutable readiness
artifacts; no real model fitted or uploaded. The
[latest refit report](../data/analysis/retailer-median-training.md#refit-using-explicitly-authorized-gold-eligibility)
records commands, full counts and integration checks.

Bulk-eligibility integration proof: `uv sync --locked`, all published contract
caches verified offline, all 409 pytest cases passed, Ruff, documentation guard
and whitespace checks passed. All 17 fresh run artifacts verified, with an
identical replay. Eight loader tests and 26 baseline tests cover promotion,
analytical/parent integrity, actual input failure reports and price-policy gates.

The independent [retailer median implementation](../data/analysis/retailer-median-training.md)
is implemented and fixture-validated. `scripts/train_chocolate_retailer_median.py`,
`scripts/chocolate_retailer_median.py`, `scripts/chocolate_experiment.py`, and
`scripts/prepare_chocolate_retailer_contract.py` implement the assigned baseline,
frozen family partitions, support/fallback rules, weighted metrics and immutable
readiness/model runs. Tests cover leakage, weighting, fallback, unsupported
inputs, target/context gates, artifact integrity and fixture labeling.

The published and explicit working-contract rebuilds both retain 3,743 seller
listings, 4,347 captures and 2,134 candidates, with zero eligible observations.
Working Gold `gold-56817976905f24210105f069` led to readiness run
`retailer-median-149182b8694b50266cdc217c`. Missing reviewed price/tax, population,
quantity and identity evidence, plus an explicit source-price window, block real
fitting. No fixture has been uploaded as a real model. Shared regression feature
evidence/identification, common-row comparison and comparator/release gates remain
pending. Contract publication requires the separate release review and portable
alignment where affected.

Verification: `uv sync --locked`, all three published caches verified offline,
399 pytest cases passed (24 baseline cases), Ruff, documentation guard and
`git diff --check`. Fixture run `retailer-median-642d5f0deb303a5a29f00316` supports
20 test rows in 10 synthetic families; unit/pack MAE is £0.40/100 g and £0.32.
Those metrics validate the implementation and do not establish market performance,
calibration or release readiness. Full identities and commands are in the report.

After the user confirmed Gold verification, a fresh local/remote inventory and
training retry accepted that confirmation and reloaded the actual files. Both
available real Gold snapshots passed integrity checks but still contained zero
eligible rows, zero regular-price targets and zero tax-inclusive price
observations. Hugging Face main remained `d549ad91d63fb452af605df4a939c4e1f0a59bfa`
with no Gold directory. The retry audit is saved in
`data/current-gold-verification-audit.json`; a different verified snapshot's
location is required for fitting/upload. Eligibility and missing values were
preserved. These current checks are separate from historical readiness reports.

### Integration of price slices with current main

Committed the price slices, family interaction and terrain tooltip fixes, then
merged main at `c4a6de4`. Resolved documentation and package script conflicts to
retain the terrain checks alongside the newer photo uploads, local extraction,
synthetic pricing demo and matched retailer training work. The existing price
slice preview predates those upstream features.

Included the generated frontend `AGENTS.md` and its `CLAUDE.md` reference in
version control at the user's request to commit every remaining changed file.

The combined application passed Node 24 type checks, terrain geometry checks and
the production build, including five assets, the immutable pricing model and
all eight API snapshot traces. Local Chromium verified price controls, both
retained sides, matching sections, the camera facing the cut, mobile controls
and restoration, with no browser errors or extra terrain requests. The locked
development environment and four cached contract sets verified; all 515 pytest
tests and Ruff passed. Documentation coverage against current main and whitespace
checks passed. Hosted interactions for the combined application remain unverified.

### Price sections through the cake

The user requested cuts at different price points. Implemented a GBP/100g slice
slider, a choice of retained side, a camera facing the exposed cut and a reset
to the whole cake. Closed layer faces and an SVG section come from clipping the original
surface triangles; unsupported regions remain gaps. Observed and draft points
are hidden on the removed side while their source coordinates and cohort
statistics remain intact. The SVG section also works in 2D mode. Slice changes
reuse cached geometry and preserve chart scales and camera orientation.

Node 24 TypeScript, production build, snapshot/asset checks and all seven API
traces passed. Numerical verification checks volume conservation, closed faces,
opposite sides, exact grid boundaries, support gaps, original geometry
preservation and point inclusion. Local Chromium with software WebGL verified
pointer and keyboard slider controls, both retained sides, fixed scales and
camera, visible geometry when facing the slice, matching SVG sections in 2D,
mobile controls and restoration of the original cake. Slicing made no extra
API requests and produced no browser errors. Hosted interaction checks and
other browsers remain unverified.

The [price slice preview](https://rgc-9blxl7c79-ptyyyy-s-projects.vercel.app),
deployment `dpl_EkGu3PAYpEMQTLiYp4MNoZ6MsEDm`, is READY. Its cloud build passed
TypeScript, data and vendor asset verification, and all seven API snapshot
traces. Vercel sign-in protection remains enabled. Documentation and whitespace
checks passed.

### Family card interaction

Removed the family coverage popovers at the user's request. Family cards are
buttons that open their member traits on click or keyboard activation, with
trait counts and coverage visible on the cards. Removed the unused breakdown
component and styles and updated the application guide and specification.
TypeScript, production build, snapshot/asset integrity, all seven API snapshot
traces, documentation and whitespace checks passed. Chromium verified that
family hover opens no popover and clicking still opens member traits.

### Terrain hover rendering and preview packaging

The user's screenshot showed blank SVG hover labels. A local Chromium check
reproduced the side label's pale text on a pale background; primary text was
visible in that browser. Replaced native chart labels with a React HTML tooltip
for product points, layers and gaps, using explicit colours and chart bounds.
Point names and numbers are rendered as text, with observed and proposed prices
identified separately. Chromium verified actual point hover content, tooltip
bounds, product selection, orbit dragging and clearing on pointer leave. The screenshot showed
readable primary and secondary text, with no browser errors. Other browsers
remain unverified.

The first preview build failed because `.vercelignore` excluded every README,
including the vendor README in the asset manifest. Anchored that rule to the
application root so the required vendor asset is uploaded. Node 24 TypeScript,
production build, data/asset integrity and all seven API traces passed locally.
The [replacement preview](https://rgc-4lwz80ftn-ptyyyy-s-projects.vercel.app),
deployment `dpl_8W6kwAW9KooyPDsByfFfqLL4srH4`, is READY. Its Node 24 cloud build
verified all three vendor assets, the snapshot and all seven API traces. Hosted
interaction checks have not been repeated; local browser checks used software
WebGL. Documentation and whitespace checks passed.

### Conflict resolution and remote integration

On 2026-10-03, resolved the interrupted rebase onto `a147e12`, preserving the
web application, model implementations, immutable contract references and
historical validation records. Reconciled current-price requirements, Gold
eligibility status and links to the data guides across the merged documents.
The six pending local commits replayed successfully.

Validation passed: `uv sync --locked`, verification of all four pinned contract
sets online and offline, Ruff, documentation checks including `--base origin/main`,
whitespace checks, web TypeScript checks and the production build. The build
verified 3,743 listings, 103 traits, 24 evidence shards, visualization assets
and snapshot inclusion in all seven API traces. `uv run pytest` stopped during
collection because the local LightGBM installation lacked `libomp.dylib`.
The user requested an immediate push while that dependency installation was in
progress; the complete Python suite had not passed at that initial push.

Follow-up verification installed the missing OpenMP runtime with
`brew install libomp`. The complete `uv run pytest` suite passed all 465 cases
in 43.32 seconds on macOS with CPython 3.13.13. All four pinned contract caches
verified offline. The [GitHub validation run](https://github.com/CoralLeiCN/rgc/actions/runs/37134596388)
also passed for merged commit `f72604a`, including locked dependencies, Ruff,
documentation maintenance and the Python suite on Linux. No code fixes were
required. The README now records the native macOS dependency for LightGBM and
test collection. Terrain/WebGL and live extraction limitations remain; later
sample photo checks are recorded below.

### Application and model status

The supplied front and back photos of Well&Truly Fudge & Brownie Oat M!lk
Chocolate, 30 g, are retained as original JPEGs under
`apps/web/public/examples/well-and-truly/`. The extraction panel offers
**Use example photos** alongside custom uploads of up to two PNG/JPEG/WebP
images. Browser preparation accepts readable originals up to 20 MiB and
40 megapixels each, then resizes and compresses temporary copies to at most
2,400 pixels on the longest edge and
1 MiB each. Selection loads photos; **Extract traits** calls the provider, then
explicit review/apply merges selected candidates while preserving proposed
price. The example has no prefilled traits or automatic score. These app assets
remain outside collection/training snapshots. Label instructions preserve the
component scope of the cocoa minimum and do not infer named Fairtrade
certification from “fairly traded.” This workflow is implemented and passed
local build, contract and browser checks recorded below. Direct local Codex
with ChatGPT sign-in is now configured; live proof is recorded below. This
revision has not been deployed;
the earlier protected preview retains its previous application version.

The current hackathon app is `apps/web`, with a Vercel frontend/backend, private
snapshot, leaf-colour terrain, typed filters, product configurator, gap finder and
brand analysis. Price is adjustable by slider; a read-only trait recipe supplies
the demo score. Image/text extraction supports server-side OpenAI or a local
Codex bridge or direct local Codex with ChatGPT OAuth sign-in. The direct mode
is selected in this checkout; hosted provider configuration remains pending.
After the earlier cleanup, the user authorized the published LightGBM synthetic fixture for product
price prediction and SHAP contributions. The current implementation is described
in the [fixture serving guide](../data/analysis/web-fixture-pricing.md).

The repository now keeps one current web app and the operational
[architecture](../vercel-architecture.md), [data guide](../collection-integration.md)
and [app setup](../../apps/web/README.md). The snapshot builder is
`scripts/build_web_snapshot.py` and outputs private server JSON only. Old static
studies, duplicated browser data, points API, fictional ID-seeded score mode,
retired UI modules and their asset-copy tooling are removed. Existing upstream
processing plugins and their verification suites are outside this cleanup.

Cleanup validation passes: TypeScript, production build, all seven API snapshot
traces, pinned Plotly integrity and documentation links. The simplified offline
snapshot builder reproduces all 26 JSON files byte-for-byte. The cleaned
[protected preview](https://rgc-mgr5btzho-ptyyyy-s-projects.vercel.app) is READY;
27 hosted route/asset checks and eight Next.js assets passed. Retired routes and
parameters are unavailable. Terrain/WebGL review remains pending. Earlier model
extraction was blocked by
workspace sandbox startup; the direct local mode and its current verification
are recorded below. No Funnel has been published. Provider setup remains in the
app README.

The app's immutable collection now pins Hugging Face revision
`812a03a5faaced471a2a20f4c389865ed5675826` and Gold inferred dataset
`gold-inferred-5b539b9c4adbb011a40d7792`. Its 3,743 listings, 103 traits,
2,159 accepted additions and zero eligible model rows describe that snapshot. Upstream analytical contracts
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
| Select supplied packaging photos or upload front/back images for candidate extraction. | `apps/web/public/examples/well-and-truly/`, product configurator, browser image preparation, extraction contract and providers | Implemented with up to two prepared images and legacy single-image input, explicit extraction/review/apply, original sample bytes preserved and asset hashes pinned. Local build, request/provider checks and browser selection/upload checks passed; live extraction and deployment of this revision remain pending. |
| Validate pinned snapshot contracts and derive private JSON plus an integrity manifest. | `scripts/build_web_snapshot.py`, `apps/web/snapshot/` | Implemented for the app's immutable revision; all 3,743 listings validate and evidence references are retained. |
| Package the Vercel application with pinned dependencies and snapshot/asset verification. | `apps/web/package.json`, lockfile, Next/Vercel configuration and verification scripts | Node 24 London functions use Vercel Authentication; cleanup verifies all seven API snapshot traces; hosted checks passed on the protected preview recorded below. |
| Demonstrate the built retail frontier workflow. | `PROJECT.md`, intention, lifecycle intent and `README` | Project description focuses on implemented collection, processing, evidence review and model preparation, with a brief description of the chocolate data, a runnable collection demo and explicit modelling limits. Event information, judging criteria and submission fields were removed from the project description. |
| Diagram the data processing workflow. | `docs/data/chocolate-silver.md`, `PROJECT.md` and `README` | Added a Mermaid diagram for source collection, raw preservation, silver processing, review, eligible model inputs and portable model preparation, with purpose, output and status descriptions for bronze/raw, Silver and immutable Parquet Gold inside the diagram and its companion table. Export and the experimental trainer are implemented; real fitting, validated pricing and explanations remain pending. Documentation tests, Ruff and documentation/whitespace checks passed; diagram stages were reviewed against the silver and portable guides. |
| Integrate data documentation with current main. | Data guides, diagram, `PROJECT.md`, Gold guide, analysis evidence, checker/tests and lifecycle documents | Reconciled newer pandas, Gold and trait contribution work; all 17 data artifacts are grouped under `docs/data/`. All 391 tests, offline pinned-cache verification, Ruff, documentation checks and a 262-link audit passed. Runtime and contract bytes match main apart from documentation checker paths. |
| Group data documentation under `docs/data/`. | Data guides, `docs/data/analysis/`, `docs/data/schema-proposals/`, repository links, documentation policy and checker/tests | Moved 11 guides and evidence/proposal artifacts; updated relative links and required documentation paths. Documentation tests, Ruff, documentation/whitespace checks and a repository link/content audit passed. |
| Record EAT_HACK participation in Retail Futures and the requested requirements. | `docs/eat-hack-track-two.md`, intention, lifecycle intent and `README` | Brief covers the Track 2 challenge, submission requirements and judging criteria; source review and documentation checks passed. |
| Define typed chocolate fields, vocabularies, units, evidence states and record shape. | Dataset `contracts/chocolate/`, pinned by `schemas/chocolate/dataset-contract.json` | Initial schema implemented; extraction review pending. |
| Define mappings and model training/interpretation contracts. | Pinned dataset contracts and `scripts/chocolate_model.py` | Contracts and preparation helpers implemented. |
| Combine raw verification, exact seller deduplication, standardization, price normalization and review/eligibility. | `scripts/build_chocolate_silver.py`, `scripts/chocolate_silver.py`, shared components, `scripts/tests/test_silver.py` | Silver implemented and verified; standalone cleanup/component CLIs serve compatibility and diagnostics. |
| Preserve broad original records, source/images and immutable captures; export verified local text evidence. | `plugins/category-research/`, `scripts/publish_collections.py` | Collection and local export implemented; raw upload interfaces reject publication under the user's storage instruction. |
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
| Preserve the regular consumer-price basis for historical studies and portable profiles. | Price-policy helpers, generated profiles, published original/portable contracts, specification and schema guides | Published and verified against immutable dataset pins; the original 375-case suite passed. The current chocolate study uses the separate current-price contract recorded below. |
| Map captured product names to reviewed families while preserving raw evidence. | `scripts/chocolate_standardization/identity.py`, `reviews/chocolate/family-mappings.json`, Silver CLI and contracts | 31 families and 1,285 family-only assignments verified. Exact physical identities remain unresolved. |
| Train experimental OLS from verified Gold with family holdout and bootstrap uncertainty. | `scripts/chocolate_regression.py`, `scripts/train_chocolate_model.py`, model design and tests | Implemented and fixture fits/failure gates verified. Current Gold has 2,134 eligible candidates and 630 current-price targets; identity and repeated-listing blockers prevent a real fitted model. Historical attempts retain their original input status. |
| Reconcile Gold/modeling work with main and prepare the dataset contract release before landing. | `docs/data/analysis/gold-modeling-contract-release.md`, integration code/tests and dataset references | Combined-main checks and corpus rebuild complete. User approved the refreshed exact release, published at `d549ad91d63fb452af605df4a939c4e1f0a59bfa` with all 16 remote files verified. Real-pin tests, offline caches, Ruff and documentation checks pass; landing uses one local main squash commit. |
| Use pandas for canonical chocolate grouping, partitions, counts and row envelopes. | `scripts/chocolate_tables.py`, shared components, silver CLI and tests | Implemented; integrated with main's family mappings, fixed-price target, Gold and locked pytest/Ruff development environment. Integration verification is recorded below. |
| Analyze every chocolate schema attribute and publish verified derived output. | `scripts/analyze_chocolate_schema.py`, reports and publication receipt | Verified original pandas snapshot and 103-field analysis published at immutable revisions. Current contracts retain the subsequent Gold/family/target release. |
| Recognize blonde chocolate and explicit mixed selections from names. | Canonical/portable adapters, adapter and Silver tests, schema guide and portable references | Implemented and verified against existing pinned vocabularies. The restored corpus rebuild has 24 blonde and 18 mixed listings; ambiguous component descriptions remain unknown. |
| Review all chocolate fields using five reviewers and cache evidence for batched inference. | Ignored investigation cache, source receipts, field reports and inference packets | Latest origin and public Hugging Face revision `bb1c9de580c64cc13aac62b352d58704fe2dd60e` synchronized. Five reviewers covered all 103 fields with exhaustive coverage counts and sampled semantic review. Five GPT-6 Luna workers completed Codex OAuth extraction in local batches of 500. The verified local review adds 2,159 values across 33 attributes; broader machine proposals remain unadopted pending semantic review. |
| Export and publish curated inference as a separate Gold layer. | Inferred Gold builder/CLI/tests, Gold/spec/schema/Silver guides, `README`, immutable dataset release receipt | Implemented and published `gold-inferred-5b539b9c4adbb011a40d7792` at Hugging Face revision `812a03a5faaced471a2a20f4c389865ed5675826`. All 47 release files passed downloaded-byte verification; existing Silver/Gold pointers and all 140 prior remote paths remain. Full product records, accepted decisions and ordinary Gold training tables are preserved. |

## Risks and controls

The user requested recognition of blonde chocolate and `mixed` for explicit milk
and dark selections. Both published chocolate schemas, mappings, validators and
selected models already allow these values. Canonical and portable adapters now
recognize blonde/blond names and coordinated selections, preserving name
evidence and review gates. Verification and full corpus impact are recorded
below; historical field reports retain their original counts.

Preserve raw evidence and seller identity independently of brand. Keep unsupported
fields unknown and distinguish source claims from independent verification.
Normalize prices using edible mass and promotion/currency/tax/time context from
the relevant observation; active predictor reviews must cite that observation's
capture. Preserve historical recipes and claims in their own context. Keep
candidates distinct from reviewed inputs, review source roles/extractor support,
retain unknown sellers outside the initial model and group related designs across
sellers in validation. Missing evidence cannot justify new taxonomy values.

## Proof

### Web application verification

#### Pricing label update

On 2026-10-03 the user requested removal of the “SYNTHETIC DEMO” text.
The price prediction panel no longer renders that badge, and its unused CSS
rule was removed. The generated-training-data disclosure remains visible.
The local browser confirmed the badge was absent. TypeScript, the documentation
guard and whitespace checks passed.

#### Custom photo upload repair

On 2026-10-03 the local browser exposed repeated extraction panels and duplicate
React keys after draft updates. Extraction and pricing shared the same numeric
session key. Their keys now include distinct panel prefixes, retaining selected
photos across ordinary draft edits and remounting both panels on copy/reset.
The browser rendered one upload panel after reload; uploading the two original
JPEGs through the file chooser produced two resized previews. Editing name and
pack price retained both photos and an enabled extraction button.

The live request then exposed a 403 because Next.js used an internal localhost
URL while the browser requested 127.0.0.1. Extraction now compares Origin with
the request protocol and Host header, using the URL host only when Host is
absent, as the price prediction route already does. The new route regression
test covers matching hosts, absent Origin/Host, foreign origins, different
ports and a misleading forwarded host; rejected requests never call a provider.

`uv sync --locked`, all 476 existing pytest cases, and the subsequent seven
extraction/pricing route tests passed. TypeScript, Ruff, production build,
snapshot/asset/model verification, all eight API traces and offline contract
verification passed. The repair is local; the hosted preview has not been
updated.

The corrected browser request returned HTTP 200 in 71 seconds with 33
reviewable candidates. One manufacture-country candidate contradicted the
response's own warning and was unchecked before Apply. Applying the remaining
32 candidates set edible weight to 30 g and retained the manually entered GBP
2.25 price. Both photo previews and one upload panel remained after applying.
This verifies the workflow, not the factual accuracy of generated candidates.
The documentation guard and whitespace check also passed.

#### Local Codex trait extraction

The 2026-10-03 local extraction update adds `codex-local` to the Next.js API.
It is the development default when no provider, bridge URL or OpenAI API key is
configured, and is explicitly selected in this checkout's ignored `.env.local`.
It uses the installed Codex CLI's existing ChatGPT OAuth sign-in, forces that
login method, removes API key environment variables and shares the bridge's
bounded input, disabled tools, schema output and temporary-file cleanup. Direct
local requests admit one job at a time and abort after 90 seconds. Vercel rejects
this mode and continues to require a hosted provider.

Live verification used Node 24.19.0 and the installed CLI, already signed in with
ChatGPT. The server bound to `127.0.0.1:3001`, with the browser at
`http://localhost:3001`. A synthetic text request returned HTTP 200 and 11
validated traits in 21.3 seconds. The browser resized both original Well&Truly
photos and submitted them together: HTTP 200 in 78 seconds, 34 candidates and
five limitation warnings. It omitted the component cocoa minimum and named
Fairtrade certification. Applying all 34 selected candidates set the draft's
name and edible mass (30 g), retained the manually entered GBP 2.25 price and
showed “34 reviewed traits applied. Pack price unchanged.” The extracted
candidates remain a user review workflow rather than verified product facts.

An overlapping request returned HTTP 429. Temporary checks verified forced
ChatGPT sign-in, removal of API key/bridge-token environment variables,
temporary-file cleanup and rejection of `codex-local` under Vercel. With Node 24,
TypeScript and the production build passed, including all five asset hashes and
all seven API snapshot traces. `uv sync --locked`, all four offline contract
caches, 26 documentation pytest checks, Ruff, documentation coverage and
whitespace checks passed. The managed shell sandbox cannot initialize the CLI's
app-server; the verified local server ran with host permissions. No hosted
bridge or tunnel was configured and this revision was not deployed.

Integration with local `main` at `bcd38cd` retains its synthetic pricing fixture
and resolves the documentation to describe both features. All 476 pytest cases,
Ruff, TypeScript, the Node 24 production build, five public asset hashes, pinned
model hashes, all eight API traces, four offline contract caches, documentation
coverage against `main` and whitespace checks passed for the combined tree.

#### Synthetic product prediction and SHAP

The user authorized the published `lightgbm_without_brand` fixture for a labelled
web demo. The form and `POST /api/predict-price` now use its immutable model,
five supported fields and explicit single bar pack scope. It displays synthetic
GBP/pack and GBP/100 g, raw field SHAP, the model reference, signed allocated
pounds/percentages, family totals and excluded schema fields. Its historical
`regular-consumer-price-1` basis and unavailable real-data interval are explicit.
The [serving guide](../data/analysis/web-fixture-pricing.md) records the interface.
No real training or remote publication was performed.

Validation on 3 October 2026:

- `uv sync --locked` installed the locked environment; four pinned contract sets
  passed `python3 -B scripts/fetch_contracts.py --all --offline`.
- All 476 cases passed with `uv run pytest`, including six serving tests. They
  compare raw price, reference and every field SHAP against native LightGBM 4.6.0
  over 324 supported combinations, and exercise allocation cancellation,
  negative values, zero/near-zero deviation, leakage/domain rejection, request
  validation and absent/corrupt model failures.
- `uv run ruff check .`, documentation and whitespace checks passed.
- TypeScript and the production build passed. All eight API traces retain the
  private snapshot, and prediction tracing includes both verified model files;
  the largest trace is 29.9 MiB before Vercel packaging.
- Clean `npm run prepare:model` downloaded and verified the pinned two-file
  model cache. Preparation supports clean Vercel builds; cached builds and
  `npm run verify:model` verify offline. Requests use no network or Python.
- Browser checks on the local production build showed a GBP 4.71 demo price
  for a 100 g dark plain bar, unknown nuts evidence and Waitrose. The reference
  was GBP 4.82; all five signed field allocations were visible. Changing proposed
  price retained the prediction, changing recipe hid it immediately, and 200 g
  returned the supported weight-range error. Screenshot proof is local.

Local web checks used Node 26.10.0; deployment configuration still selects Node
24. This feature has not been deployed to the existing protected preview.
Hosted extraction configuration and broad WebGL rendering retain their separate
verification limits. Fixture parity establishes implementation fidelity, not
market prediction accuracy or a validated real-product interval.

Integration with `main` at `f86f20b` retained the example photos and multiple
image uploads. All 476 tests, Ruff, TypeScript, the production build, five public
asset hashes, model hashes, all eight API traces, four offline contract caches,
documentation coverage against `main` and whitespace checks passed after
integration. The combined revision has not been deployed.

#### Example photos and multiple image uploads

On 2026-10-03 the sample photo revision passed `uv sync --locked`, fetching all
pinned contracts followed by
`python3 -B scripts/fetch_contracts.py --all --offline`, all 465 tests with
`uv run pytest`, and `uv run ruff check .`. With Node 24, `npm ci`,
`npm run typecheck` and `npm run build` passed. The final build verifies all five
public assets, including the two original JPEG hashes, and snapshot inclusion in
all seven API traces. Temporary checks covered image count/byte/body limits,
legacy single-image input, delivery of every image to both mocked providers and
cleanup of local Codex input files. `python3 -B scripts/check_documentation.py`
and `git diff --check` passed. These checks did not invoke a live model.

Browser checks against the rebuilt local production server verified example
selection with two complete 1,800 × 2,400 previews, custom upload of both original
JPEGs, removal of one photo, appending the other and rejection of a three-photo
selection while preserving the existing pair. Selecting the example preserved
a manually entered draft name and GBP 2.25 proposed price. **Extract traits**
submitted the selected pair and displayed the expected 503 provider-configuration
error. At that time, live extraction and its candidates remained unverified. No
deployment was performed for that revision; the hosted preview proof below
describes the earlier application. Terrain/WebGL interaction requires its own
browser review.

The photo revision was integrated with local `main` at `3c94377`, retaining the
local raw-evidence storage policy and both validation records. Locked dependency
verification, all four offline contract caches, all 470 Python tests, Ruff,
documentation coverage against `main` and whitespace checks passed. The web
application files match the previously verified photo revision byte for byte.

Integration with main preserves the app snapshot's verified contract independently
of newer training taxonomy and target-policy requirements. The updated adapter
validated all 3,743 listings offline and reproduced all 26 private JSON files
byte-for-byte. Targeted Ruff, TypeScript, production build, data/asset integrity,
all seven API snapshot traces, documentation and whitespace checks passed after
the merge. Upstream training requirements remain enforced by their own pipeline.

The earlier cleaned web preview, deployment `dpl_2JRVCEdm45vGfxtkPJYiSHDoMy5T`, passed
its Vercel build and all seven API snapshot traces (largest traced dependency
set 28.5 MiB). Hosted verification checked all active APIs, three vendor assets
against their hashes, the homepage and eight Next.js assets. The retired
`/api/points` and study URL return 404; `scoreMode=demo` returns 400. Unsupported
methods return 405, and the private snapshot remains inaccessible over HTTP.

Observed analysis retains 892 priced listings, with 811 in the core range;
the terrain retains 289 complete core-range and 338 full-range products. Exact
prices, raw numeric heights, trait-recipe scores and category shares reconcile
against the pinned snapshot. Parent-family dimension requests return 400.
The extraction endpoint returns 400 for invalid input and 503 for missing
configuration; no live provider was called. Default Vercel Authentication remains
enabled, unauthenticated API access redirects to sign-in, and temporary verification
credentials were revoked with their local files deleted. Previous previews and
production were not changed. Browser rendering and live extraction remain unverified.

### Pipeline and model preparation verification

The verification below was recorded on 2026-10-03. Each run establishes the stated
implementation scope. Dataset manifests and quality reports own build counts and
readiness; `complete_snapshot` establishes accepted input consistency.

| Verification | Recorded result and evidence |
| --- | --- |
| Blonde and mixed chocolate extraction | `uv sync --locked` installed the locked environment; all three pinned caches passed `python3 -B scripts/fetch_contracts.py --all --offline`. `uv --cache-dir /private/tmp/rgc-uv-cache run --locked pytest` passed all 429 cases in 18.31 seconds. Checks cover both adapters, blonde/blond names, coordinated/shared type wording, repeated types, component/chip ambiguity, canonical and portable Silver evidence, preserved source records and unreviewed eligibility gates. Ruff, documentation and whitespace checks passed. No analytical contract bytes or immutable references changed because both schema/validator/model vocabularies and aliases already support the labels. The subsequent corpus rebuild is recorded below. |
| Restored corpus and five field reviewers | All 152 public dataset files (3,539,612,644 bytes) were downloaded at revision `bb1c9de580c64cc13aac62b352d58704fe2dd60e` and verified against remote hashes; all 22,372 raw archive members were verified. Local `silver-5a662182f9d2fdcb35355453` retains 3,743 listings and 4,347 captures with no archive/extraction errors. Chocolate type has 1,467 known cells, including 24 blonde and 18 mixed; 12 ambiguous former labels became unknown. Existing family decisions restore 1,285 family IDs. Eligible model inputs remain zero under the pinned regular-price contract. Five reviewer reports cover all 103 fields; the completed local inference adoption is recorded below. |
| Curated Luna inference and corrected Silver | Five OAuth workers processed all 3,743 listings using model-authored source extraction rules in batches of 500, generating 25,179 proposals. Independent review and parent validation accepted 2,159 values across 33 attributes and 1,764 listings: 1,618 explicit SKUs, eight pack counts, 494 nutrition values and 39 other source declarations. Exhaustive accepted nutrition column checks corrected two adult reference-intake values to 2,413 kJ and 582 kcal per 100 g. Final local `silver-f865cac2a7324d5204b797f4` preserves all seller rows, 4,347 exact capture objects and 2,134 price observations; all 24 managed hashes pass. Exactly the accepted attribute cells change. There are 53 attributes with known values, 50 with none and 1,460 conflicting cells. Eligible inputs remain zero under `regular-consumer-price-1`. Inputs, proposals, reviews, corrections, superseded output and hash-verified checkpoint archives are cached under ignored `data/investigation/2026-10-03-field-review/`; publication of the inferred wrapper is recorded in the following row. |
| Gold inferred export and publication | [Publication receipt](../data/analysis/chocolate-gold-inferred-publication-2026-10-03.json) records parent `06680d7248ccc4487726b9a97e59aa8f586fb54e`, immutable release `812a03a5faaced471a2a20f4c389865ed5675826` and all 47 file hashes. Latest source comparison verified 23 unchanged published Silver files. All 3,743 decoded product records and 385,529 typed attribute cells match reviewed Silver; accepted-decision bytes, prices and 2,134 training rows are preserved. The original on-disk Gold child retains zero source-eligible inputs under `regular-consumer-price-1`; current loaders expose all 2,134 candidates for model preparation. Eight new tests cover evidence matching, typed/null/conflict preservation, eligible-source preservation, symlinks, replay and tamper rejection. The full locked suite passed 437 tests in 9.20 seconds; Ruff, documentation and whitespace checks passed. Dataset configurations select inferred products or training separately from the existing default. |
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

Many chocolate source values still need review and price/tax basis is unresolved:
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


The local main/current-price integration passed all 467 pytest cases, the locked
environment sync, all four offline contract sets, Ruff, documentation guard and
whitespace checks. The published-Gold refit verified its 29 managed artifacts
and immutable replay. No source values or model eligibility flags were rewritten.

### Original published Silver retirement

On 2026-10-03, the user requested removal of the original published Silver
snapshot and waived its backward compatibility. Published a guarded deletion
at dataset revision `2f96b70adab9ea0aec6e833d94f9ebd3e338a115`, removing
24 files (1,415,482,135 bytes) under
`silver/chocolate/uk/silver-6e246156b7292dd4bb49ebf0/`, its six LFS rules, and
correcting the dataset card. Verified the expected inventory, unchanged content
identifiers for all 141 retained files outside updated metadata, SHA-256 of both
metadata downloads, and the unchanged latest pointer selecting the pandas
snapshot. Current-tree bytes fell from 3,547,659,430 to 2,132,176,764. The
[retirement receipt](../data/analysis/chocolate-original-silver-retirement-2026-10-03.json)
records exact paths and checks. Historical publication records retain the
inventory at their original revisions. Historical Hub commits and local
worktree copies remain; historical storage reclamation is not established.

`uv sync --locked`, offline verification of all four pinned contract caches,
Ruff, documentation guard, 26 documentation pytest cases and whitespace checks
passed. No processing code or analytical contract changed.


### Keep raw source evidence local

On 2026-10-03, the user requested local raw evidence and clarified removal of
raw files only. Verified the existing primary local text export: 22,372 bundle
members, 3,608,764,602 included bytes, 3,743 index rows, exact archive hash and
all bundle inventory hashes. The complete collection remains under
`/Users/coral/repos/rgc/data/collections/` and the verified export under
`/Users/coral/repos/rgc/data/huggingface-export/`. Prepared removal of the remote
raw archive, root product index and export manifest; Silver source-listings are
retained. Published the deletion at `06680d7248ccc4487726b9a97e59aa8f586fb54e`.
The [local storage receipt](../data/analysis/chocolate-local-raw-storage-2026-10-03.json)
records removal of three files (671,923,490 bytes), matching local hashes before
and after publication, unchanged content identifiers for all 138 other retained
files, verified SHA-256 of both updated metadata downloads, and the unchanged
Silver latest pointer. All four Silver source-listings files remain published.
Current-tree bytes fell from 2,132,176,764 to 1,460,252,307. The dataset card now
defaults to the existing Gold training table; its published checksum and Parquet
metadata verify 2,134 rows. The raw exporter rejects its old CLI and callable
upload interfaces before local export or remote actions, and reports
`export_bytes` with no Hub dependency.

The locked development environment and all four pinned contract caches were
verified. Ruff, documentation guard, 34 publication/documentation pytest cases,
Gold loader table checks and whitespace checks passed. These tests cover retired
upload rejection before export, the disabled callable API, complete local export
verification, deterministic preservation and documentation coverage. Historical
Hub commits retain old raw files; historical storage reclamation is not claimed.

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


### Local raw storage integration with main

The user requested committing all storage changes and merging them into local
`main`. The task branch `codex/local-raw-storage` includes both verified Hugging
Face receipts and the local-only exporter. Integration with refreshed main
`f72604a` preserved its web application, pinned display snapshot and independent
hedonic estimator. Five documentation conflicts were resolved by retaining
both sessions' requirements and correcting the new application intention's
raw-storage statement to refer to the local archive. The lifecycle intent now
records the same source locations and retained published Silver scope.

`uv sync --locked --offline`, all four offline contract caches, Ruff, the
documentation guard and the complete 470-case pytest suite passed after
integration. Whitespace checks passed. The requested landing uses one squash
commit; source/target tree equality and clean-worktree checks follow the commit.

## Gold inferred app adoption

The requested app data migration is implemented by `scripts/web_gold_inferred.py`
and `scripts/build_web_snapshot.py`. The committed app reference pins dataset
revision `812a03a5faaced471a2a20f4c389865ed5675826`, source manifest SHA-256
`18b1d00b301b1ad7ce7190076614e9c76f84cbb99f3c43a5aa8273f9f4123bfe` and
`gold-inferred-5b539b9c4adbb011a40d7792`. The downloader verifies every managed
file. Nested Gold verification authenticates contracts, prices, training rows
and source Silver provenance; authoritative Parquet product records receive a
logical hash check and full product validation. The app build rejects stale
collection references. Original evidence links and curated inference counts are
available in the workspace.

The regenerated private JSON contains 3,743 listings, 103 traits, 24 evidence
shards and 33,845 known cells. All 2,159 accepted additions across 33 attributes
retain evidence and review states. Default terrain retains 289 core or 338 full
rows, and observed analysis retains 892 usable prices. The export preserves its
historical `regular-consumer-price-1` contract, 2,134 candidates and zero eligible
inputs. Current-price study contracts and the synthetic pricing fixture retain
their independent provenance.

Validation passed: `uv sync --locked`, all four contract caches verified offline,
all 482 pytest cases, `uv run ruff check .`, documentation contracts and
`git diff --check`. Node 24.20.0 TypeScript and production builds passed data,
asset/model verification and all eight API traces (31.5 MiB largest dependency
set before Vercel packaging). Production localhost checks served the new dataset
through schema, products, single-listing evidence, comparison, analysis and
terrain APIs; private collection assets returned 404. Every accepted decision
matched the app's exported value. The offline rebuild reproduced all 26 JSON
files byte for byte. This change has not been deployed to the hosted app.

## Independent matched retailer session, 3 October 2026

Implemented exactly `matched_retailer` on `codex/matched-retailer` through
`scripts/chocolate_matched_retailer.py` and the trainer's explicit model selector.
The [diagnostic guide](../data/chocolate-matched-retailer.md) owns exact matching
evidence, working-contract preparation, frozen family partitions, weights, graph
components/bridges, leave-one-family-out stability, bootstrap disconnections,
residual metrics and immutable run interfaces. Existing experimental OLS remains
a separate path. No comparator or full-sample refit was trained here.

Verified the three published contract caches offline at revision
`d549ad91d63fb452af605df4a939c4e1f0a59bfa`. The preserved raw input at the saved
project checkout produced `raw-snapshot-70239771976a75a48c5d99db`, Silver
`silver-f651a7faea94ed5a7f003e64` and Gold `gold-4939405fcf8724686f9ee32c`. All
3,743 listings and 4,347 captures were retained. Gold managed file and logical
row hashes and copied contracts verified: 2,134 candidates, zero eligible rows.
The Gold manifest SHA-256 is
`cfc10a09c8685e501e6085c523b7726d9cc75ee60b0ab6a0f970a10db5553d4a`.
The real attempt exits 2 with readiness blockers, persisted in
`data/models/chocolate/uk/matched_retailer/matched-run-7441cfa4a781a697b80b7271/`.
All candidates lack required scope/identity/quantity/price-tax review; 1,157 also
lack verified time/availability. Matching reviews and a genuine window are absent.
No real model fitted, calibrated or released.

A separate synthetic fit at
`data/models/chocolate/uk/matched_retailer/matched-run-b5cf6a9673773b0e32604da9/`
uses 40 rows/20 families split 12/4/4, fitting 24 rows from 12 families. It recovers
the injected 0.2 log contrast (22.1403%) with 200 successful family replicates and
zero disconnections. Family-weighted fitting residual MAE is approximately
`8.96e-10` GBP/100 g and `7.17e-10` GBP/pack. Those are fixture diagnostics, not
measured retailer results. Held-out families receive unavailable predictions.
23 native pytest tests verify outcome-independent splitting, weights, exact
variant conflicts, source/time/context gates, leakage prevention, graph/weak
bridge uncertainty, price policy, corruption and immutable artifact behavior.

The local `chocolate-matched-retailer-design-1` contract is prepared in ignored
`data/working-contracts/matched_retailer/`. Original/portable production contract
coordination and the required release review remain pending; no analytical
contracts were published or pins changed. Actual trained model uploads are now
authorized under `model/matched_retailer/<run-id>/`, but zero eligible data means
there is no actual trained model to upload. Synthetic models were not published.
Common experiment identity must be compared with other sessions before shared
results or champion decisions.

Verification: `uv sync --locked` passed; `python3 -B
scripts/fetch_contracts.py --all --offline` verified all three caches. `uv run
pytest` passed all 398 cases in 9.23 seconds, including the 23 new diagnostic
cases. `uv run ruff check .`, `python3 -B scripts/check_documentation.py` and
`git diff --check` passed. Gold emitted sandbox CPU-probe warnings but completed
and all Parquet integrity tests passed. CI has not run in this session.

The real experiment SHA-256 is
`1c3d4a468519b9c38e2d92af89dba76507ef8eae67f177e9453d84cb6f4a7b96`;
its working-contract SHA-256 is
`7915ff8d4a26f9ff977ab0063c8f66ec15e2cfd28a15f4499b2b2e800673183a`.
Both the fixture and real attempts use common-policy SHA-256
`87f82023f06d820965c498825646f64f64e9f759a6acb0425cfa47bdffe4bf83`.
The fixture experiment has a different synthetic Gold/window/review identity
and is never pooled with the real attempt.

## Direct training after the user's Gold verification

On 3 October 2026 the user confirmed that all existing Gold data are verified
and requested training without rebuilding Gold or adding a data layer. Added
`--verified-gold-candidates` to the matched-retailer trainer. This task-authorized
path considers existing candidates, selects required matched-model fields,
records `gold_verification_basis: explicit_task_authorized_candidates`, and
preserves stored eligibility flags, source values and all Gold bytes. Optional
regression-feature missingness is not a prerequisite for this estimator. Source
content cannot authorize the flag. Default stored-eligibility behavior remains
available for callers without the instruction.

Fresh inspection found only `gold-4939405fcf8724686f9ee32c` across this worktree,
the parent checkout and saved project. The direct attempt considered all 2,134
candidates as verified and reached concrete missing-value checks: zero regular
prices, zero regular unit-price targets and zero exact-variant IDs. Of 2,134
rows, 1,732 lack family IDs, 1,503 lack candidate edible weight, 997 lack brand
and 1,289 lack type; all stored tax bases are `unknown`. Displayed prices exist
on 2,133 observations but do not supply the specified regular-price target.
Exact formulation/flavor/pack and comparable context fields are also absent
from copied price observations. These are current value counts, not a repeated
review requirement. The Gold manifest still hashes to
`cfc10a09c8685e501e6085c523b7726d9cc75ee60b0ab6a0f970a10db5553d4a`.

Direct model run
`data/models/chocolate/uk/matched_retailer/matched-run-02561db39aefddea2f22b87f/`
saves all candidate domain membership and concrete missing-value counts. Its
experiment SHA-256 is
`011fd82149ebe5820ad1444a6651b7d3d4426d8819051868ec443d97a3ed54fe`.
All 21 managed artifacts verify against the model manifest. The CLI command
appends `--verified-gold-candidates` to the documented real command. It exits 2
for missing model inputs and produces no fitted model. Neither Gold nor Silver
was rebuilt. No model was uploaded.

Four new tests establish fitting of task-verified candidates despite historical
false flags and optional-feature nulls, preservation of source flags/bytes,
missing-target/identity failures, direct use of existing context, and rejection
of inconsistent regular targets. `uv sync --locked` and offline verification
of all pinned contract caches passed. `uv run pytest` passed all 402 tests in
8.72 seconds; Ruff and whitespace checks passed. Documentation and semantic
coverage were checked with the updated guides. Production contract publication
and real fitted model upload remain pending actual inputs and their applicable
release requirements.

## Refresh from the newly promoted Gold snapshot

On 3 October 2026 the user authorized all Gold entities as eligible and requested
a fresh assigned-model attempt against the newly supplied snapshot. Integrated
`scripts/chocolate_gold_eligibility.py`, its CLI and its tests from the supplying
worktree. The Gold reader now dispatches to `verified_eligible_gold` for
`chocolate-gold-bulk-eligibility-1`, verifying the complete embedded parent, all
managed and logical hashes, original analytical values and the exact permitted
flag/exclusion changes. Model-specific training remains separate.

The supplied absolute snapshot at
`/Users/coral/.codex/worktrees/bb33/rgc/data/gold/chocolate/uk/gold-8b897101474becaef946922b`
was verified against the provided manifest SHA-256
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
It retains parent `gold-56817976905f24210105f069`, source Silver
`silver-485af2f8e7fae127cd73578b`, and the established raw snapshot. Both
Parquet tables contain 2,134 rows with true eligibility and empty exclusions.
This session used the shared immutable snapshot directly; neither Gold nor
Silver was rebuilt.

The copied storage contract is a locally prepared
`chocolate-retailer-median-design-1`, differing from published default bytes.
Prepared an explicit local `verified_gold_snapshot` input configuration bound
to the exact supplied Gold manifest and all four copied contract hashes. It
retains the finalized regular-price target. This is an input/storage binding;
the assigned estimator remains `matched_retailer` with its own working model
design. Published original/portable contract pins remain unchanged.

Fresh run
`data/models/chocolate/uk/matched_retailer/matched-run-f7f9bf7d031040a8599b3721/`
records the exact Gold manifest, eligibility provenance, parent identity, input
storage-design identity, required-value counts and all candidate domain
membership. It reports 2,134 eligible source rows and zero complete matched
model inputs. Every row still lacks regular price, regular unit-price target
and exact-variant ID; all tax values remain `unknown`. Missing family, candidate
edible weight, brand and type counts are 1,732, 1,503, 997 and 1,289 respectively.
The attempt exits 2 on those current value failures, with no historical Silver
eligibility blocker. No fit, measured retailer contrast, calibration, release or
model upload occurred. All 21 saved managed artifacts and the unchanged input
manifest were verified.

The [matched refresh guide](../data/chocolate-matched-retailer.md#refresh-from-promoted-gold)
records exact preparation and training commands. Added a meaningful fixture test
that verifies promoted rows and provenance through the new loader, binds differing
copied storage contracts, preserves the assigned estimator, and rejects a wrong
input-manifest binding. The imported eligibility tests cover parent preservation,
reviewed/empty inputs, replay, authorization, analytical tampering and false
reports. Locked environment setup, offline pinned-contract verification, Ruff
and whitespace checks passed. Final `uv run pytest` passed all 411 tests in 9.40 seconds, including the
count-label refinement. Ruff, the full documentation guard and whitespace checks
also passed. CI has not run in this session.

The refreshed experiment SHA-256 is
`335bcca404580ceed424eae7c40c61184c25c06ad29b0ed97c10b165e50de194`;
the explicit snapshot-bound working-contract SHA-256 is
`1da798a1caf0aaef6512cef8fa6bc2c40aaec2f96f953e2d74ca6cc477b24489`.
The model manifest includes the exact user eligibility provenance.

## Interim current-price target instruction

The user superseded separately evidenced regular prices, non-promotional status
and verified tax inclusion as study prerequisites. Added explicit current study
working design `chocolate-matched-retailer-design-2` with
`current-consumer-price-1`, selected by `--current-price-proxy` during configuration
preparation. Source Gold remains intact. The trainer derives a separate
`model_target` from actual positive displayed GBP prices and existing edible
weights, records quantity source and promotion/tax metadata, and persists every
considered row in `prepared-current-inputs.jsonl`. No regular price or tax
resolution check blocks this mode. Historical regular-price runs retain their
original contract identities and validation behavior.

Current-target fixture validation recovers the injected matched retailer
contrast with promotional observations, unknown tax and absent regular prices.
Additional cases verify target/source preservation, positive actual quantity,
missing current price and currency failures, and missing exact identity.
The quantitative diagnostic now consumes the explicit model target and retains
its log/unit/pack units. The interim quantity selection uses positive candidate
edible weight, otherwise an existing positive corresponding price-observation
edible weight, with conflicting known weights excluded. Common comparison must
verify alignment with the coordinating task's shared current-price adapter
before comparing differing normalized domains.

Fresh current-mode run
`data/models/chocolate/uk/matched_retailer/matched-run-e23c42e088b0da7acf4edb73/`
uses the exact already verified `gold-8b897101474becaef946922b` manifest, with all
2,134 rows eligible. It records 2,133 positive current pack prices and 1,210
normalized targets, with one missing current price and 923 missing usable weights.
Every exact-variant ID is still absent, so no matched fit is possible. Missing
family/type/brand counts remain 1,732/1,289/997. Regular-price, promotion and tax
requirements are absent from the current blockers. No new Gold/Silver build,
source rewrite, fabricated identity, fitted real model or upload occurred.
All 22 managed artifacts and the unchanged shared Gold manifest verify.

The shared current-price input contract announced by the coordinating task has
not yet been delivered at this interim attempt. This local run explicitly
records its policy and domain; it does not claim fitting on a future shared
snapshot or publishing an analytical contract. The [current-price guide](../data/chocolate-matched-retailer.md#current-price-study-policy)
owns the updated preparation and target interfaces.

Current-mode checks: all 417 pytest cases passed in 8.77 seconds, including
34 matched-model cases. Ruff, documentation and whitespace checks passed.
The current experiment SHA-256 is
`fe73e7abad6b617c828f6bd6a4c99d3390fb3637979f5b8079bf0b8496ab3bae`.
The locked environment and offline published caches were verified in this
continuous refresh session. No analytical contract or model was published.

## Published shared current-price alignment

Consumed the supplied published current-price contract at immutable dataset
commit `d743cb8dbca37f5241cccd444a16165523304f6c`. Its separate Git manifest pins
all four payload hashes and sizes; existing established and portable references
retain their revision. Added an offline resolver, `fetch_contracts.py
--current-price` and inclusion in `--all`. Copied and verified the supplied cache
against the immutable reference. Shared preparation
`chocolate-current-price-target-1` now owns the actual price/quantity arithmetic.
Matched working design `chocolate-matched-retailer-design-3` binds published
`chocolate-pricing-current-price-design-1`, preserves its full target definition
and records the reference and payloads in each model run. The estimator still
fits exact variant and retailer effects.

The adapter requires positive candidate edible weight matching the price
observation; price-only quantity fallback is removed. It retains all considered
rows, with null unavailable targets and explicit failure counts. Current fields
and equal `regular_*` compatibility aliases occur only in derived model inputs;
the aliases represent the current proxy. Original Gold/Silver inputs remain
copied intact. New tests cover shared arithmetic, promotions/unknown tax,
quantity/provenance failures and target tampering; matched tests exercise the
published target binding and persisted input contract.

Fresh assigned-model run
`data/models/chocolate/uk/matched_retailer/matched-run-1525e48d0fb469cbba36d8a9/`
uses supplied `gold-8b897101474becaef946922b` directly, with all 2,134 candidates
eligible and verified under the task instruction. It finds 2,133 positive pack
prices and 630 current unit-price targets. One current price and 1,503 candidate
weights are missing or invalid. All 2,134 rows lack exact variant IDs, so no
matched fit is possible. Family/type/brand missing counts remain
1,732/1,289/997. Eligibility, regular-price verification, promotion and tax
metadata do not block this attempt. No Gold rebuild, real fit or model upload
occurred. The 28 managed artifacts and implementation hashes verify, and the
Gold manifest remains
`e3a7a1dc3c4a4c4b454b241b3f2738d196eb47897e3169c9c6531e9fdf315d90`.
Experiment file SHA-256:
`df4c6aff20f2fead9e19b782f4adf2d009dcdb89f9a9d3b6e03636068d28d4f8`.

Validation: `uv sync --locked` passed; all four caches verified with
`python3 -B scripts/fetch_contracts.py --all --offline`; all 425 pytest cases
passed in 9.94 seconds; Ruff, documentation and whitespace checks passed.

## Latest published Gold pull and assigned-model attempt

The user requested a fresh remote Gold pull and fitting with feature selection
confined to model preparation. Hugging Face dataset head resolved to
`bb1c9de580c64cc13aac62b352d58704fe2dd60e`; its latest pointer still selects
`gold-8b897101474becaef946922b`. Downloaded the manifest and all 23 managed files
(24,540,810 bytes) into this worktree, verifying every SHA-256 and length against
the immutable pointer/manifest. The receipt and original pointer are saved in
ignored `data/model-input-receipts/matched_retailer/`. No Gold transformation,
schema change or rebuild occurred.

Prepared a separate current-price working configuration and reran only
`matched_retailer` from the downloaded local Gold. The output is
`data/models/chocolate/uk/hf-bb1c9de580c64cc13aac62b352d58704fe2dd60e/matched_retailer/matched-run-1525e48d0fb469cbba36d8a9/`.
All 2,134 rows remain eligible; 630 have current unit-price targets; every exact
variant ID is null and the attempted fit has zero matching inputs. Raw Parquet
inspection independently confirms the missing identities. Feature selection
cannot recover product matching in the assigned estimator. No fitted model or
upload occurred. Verified all 28 model artifacts and reverified the complete
Gold loader and downloaded bytes after the attempt. The locked environment and
all four contract caches verified; documentation and whitespace checks passed.
No implementation changed, so the previous numerical test results remain
applicable.

During this latest pull, publication revision
`95c5fbd0ab5fa9a41fa5333648321d95f16927a7` was announced. Downloaded its 25 Gold
files at that exact revision and compared every byte with the initial download.
Its latest pointer, manifest and all 23 managed files are identical. The Gold
pin read from local main `cd9e7df` matches the manifest/inventory; shared
current-price preparation and target reference also match that main revision.
Reran the assigned fit under `data/models/chocolate/uk/hf-95c5fbd0ab5fa9a41fa5333648321d95f16927a7/matched_retailer/`,
with the same run ID, 630 targets and zero exact matches. The new receipt owns
the publication revision and all 28 artifacts verify. Gold bytes remain intact.

## Matched retailer integration into main, 3 October 2026

The user requested committing the model training code to local `main`. Integrated
main `f2e056c` into `codex/matched-retailer`, retaining the current-price OLS,
LightGBM and hedonic commands and main's data guides under `docs/data/`. The
matched selector shares the integrated parser, preserves its own working
contract/review interface and rejects options belonging to the other estimators.
New CLI tests cover both selector spellings, persisted matched readiness,
unchanged Gold bytes and rejected incompatible options. The current-price cache
is selected once by `--all`; `--current-price` remains available independently.

`uv sync --locked` passed. All four immutable contract caches verified with
`python3 -B scripts/fetch_contracts.py --all --offline`. The combined branch's
`uv run pytest` passed 508 tests with seven web tests skipped because this
worktree lacks the web TypeScript runtime and pinned web model cache. Both LightGBM suites, hedonic and
matched numerical/artifact suites passed. Ruff, documentation checks against
main and whitespace checks passed. Web implementation matches main; the prior
web validation remains recorded above. No real matched fit or model publication
is established: published Gold has 630 current targets and no exact variant IDs.


Retailer median landing validation integrated the refreshed main branch while
preserving other estimators and application changes. The locked environment,
all four offline contract sets, Ruff, documentation checks against main and
whitespace checks passed. The complete Python run passed 549 tests; seven
optional web extraction/serving tests skipped because this model worktree lacks
npm dependencies and the prepared web model cache. All model training tests
passed. Generated inspection and model artifacts remain outside Git.

## Gold inferred app landing integration

The app adoption branch incorporated main's matched retailer and retailer median
training changes before landing. Four documentation conflicts retained both the
app collection contract and the independent training handoffs. The app's
historical Gold inferred price basis and zero eligible rows remain distinct from
the training study's current-price Gold inputs. Combined-tree validation passed:
`uv sync --locked --offline`, four verified offline contract sets, all 561 pytest
cases, Ruff, the documentation guard against main and whitespace checks.
Node 24.20.0 TypeScript and production builds passed source-data, asset/model
verification and all eight API traces. Main's configured upstream was refreshed
successfully. The requested landing adds one local squash commit to main.



## Gold population without eligibility fields

On 2026-10-03 the user refined the Gold instruction: treat every row as eligible
and remove `model_eligible` and relevant fields entirely. Implemented
`chocolate-gold-population-1` / `chocolate-gold-arrow-3` with one
`training-data.parquet` table, no eligibility/exclusion columns or stored subset,
and `counts.training_rows`. Builds verify source Silver and retain its exact
training JSONL as provenance. Migrations and administrative reviews retain a
complete verified Gold parent and compare ordered analytical values.

The public loader verifies historical storage then exposes every candidate
without selection fields. Both legacy logical input names alias that population.
All four experimental trainers consume it without row or source-price eligibility
flags. Actual input checks and declared study cohorts remain; current-price OLS
records the displayed-price proxy and historical studies keep their target basis.
Source analytical contracts and portable profiles keep their exact versions.

Downloaded and hash-verified all 24 files in the pinned source Gold snapshot.
The local migration `gold-ae712cc107e875e18816280c` contains all 2,134 rows in one
Parquet table without either selection column. Its manifest SHA-256 is
`a3add352cf4974bd447b736f80314dd96eca182e2ca1bea36c52e253468f83c6`.
Current-price readiness run `model-run-9182ff8464720d2698b6b26b` considered all
2,134 rows, derived 630 unit-price targets and selected all 800 bar observations.
Missing canonical variant IDs and repeated listing observations block fitting;
no real model was fitted. The retained parent verifies independently.

The new snapshot is local. The published reference continues to identify its
immutable historical bytes; no Hugging Face publication was performed.


Validation passed: `uv sync --locked`, pinned contract fetching and
`python3 -B scripts/fetch_contracts.py --all --offline`, `uv run pytest`
(483 passed, 7 optional web tests skipped), `uv run ruff check .`,
`python3 -B scripts/check_documentation.py` and `git diff --check`.
Tests cover every supported historical migration, preserved parents and source
bytes, omitted/reordered/altered rows despite recomputed hashes, typed empty
populations, source-price flags absent, formerly excluded valid fixture fitting,
and explicit actual-price/family readiness failures. The actual corpus migration
and current-price readiness run were verified locally; remote publication and
real model fitting remain unperformed.

## Integrate Gold population with the current main branch

The local main branch added matched-retailer, retailer-median and Gold inferred
web consumers after this task started. Their merged implementations consume
the complete Gold population automatically. Matched-retailer checks actual
required values and records `gold_verification_basis: all_gold_rows`; the median
records `population_selection: all_gold_rows`. Both report `training_rows`,
omit modeling eligibility fields and retain exact source inputs. The web adapter
verifies complete population counts separately from historical Silver quality
counts and exposes `training_rows` in metadata. Historical run identities and
source analytical contracts remain preserved.

Integration validation passed: `uv sync --locked`, all four contract caches
verified offline, `uv run pytest` (567 passed, 7 optional web tests skipped),
`uv run ruff check .`, `python3 -B scripts/check_documentation.py --base main`
and `git diff --check`. Focused retailer and web integration coverage passed
all 83 cases. Real model fitting remains blocked by missing actual inputs.

## Inferred Gold LightGBM refit and all-row admission

On 3 October 2026 the user requested the without-brand model refitted with
the inferred layer, then directed every `gold_*` layer always training
eligible. Implemented `chocolate-gold-training-all-rows-1` in the shared
Gold training adapter and applied it to OLS, hedonic without brand and both
historical LightGBM entry points. Source integrity verification retains exact
historical bytes and counts; original exclusions and flags remain provenance
in admitted rows and price records. The complete inferred-wrapper verifier,
builder, CLI and eight tests were imported from its existing implementation.

The [refit record](../data/analysis/lightgbm-without-brand-inferred-refit.md)
and [machine results](../data/analysis/lightgbm-without-brand-inferred-refit.json)
record actual run `model-run-9f56df660a6d46e7cc720002` from inferred Gold
`gold-inferred-5b539b9c4adbb011a40d7792`. All 2,134 candidates are eligible;
55 Waitrose bars in 15 established families have usable target/mass/grouping
for the experiment. The 80/20 family holdout has 40 fitting and 15 testing
rows, spanning 12 and three families. Three inner family folds select 84 trees
and the core size/retailer/type features. Brand is excluded from every fitted
matrix. Current displayed prices use the pinned current-price study target.
All holdout rows yield unit MAE GBP 0.542656/100 g, pack MAE GBP 0.473168 and
weighted median percentage error 14.6872%. Native TreeSHAP reconstructs within
1.11e-15 log units. One test row has a domain support flag. No intervals,
Ocado result, market release or champion claim are established.

Final verification passed: `uv sync --locked` with a writable temporary uv
cache, all four contract sets verified by
`python3 -B scripts/fetch_contracts.py --all --offline`, 483 pytest cases,
Ruff, `python3 -B scripts/check_documentation.py` and `git diff --check`.
Seven existing web tests skipped because this checkout has no prepared web
model cache or npm dependencies; web serving was not changed. The affected
83-test selection also passed. The final model loader reproduced all 15 saved
test predictions exactly and verified brand exclusion. Live Hugging Face
`main` resolved to `812a03a5faaced471a2a20f4c389865ed5675826`; its inferred
latest pointer and downloaded manifest match the actual fitting snapshot. At completion of the initial fit the local model was unpublished and used
its own verified loader. The subsequent publication is recorded below.

## Publish the inferred LightGBM refit

On 3 October 2026 the user explicitly requested publication of the completed
model. Published `model-run-9f56df660a6d46e7cc720002` under
`model/lightgbm_without_brand/` at dataset revision
`88b08aeada37e228fcd80334b5abddd768da6968`, guarded against parent
`812a03a5faaced471a2a20f4c389865ed5675826`. All 16 published files were
downloaded and verified against staging, totaling 313,788 bytes. The
[receipt](../data/analysis/lightgbm-without-brand-inferred-model-publication.json)
records hashes, paths and separate fit/calibration/release status. All 186
existing remote paths and object identities were preserved.

The model publication includes booster, model, preprocessing, tuning,
evaluation, predictions and signed TreeSHAP results, experiment and target
metadata, original run manifest, reproduction command and README. Source
training data remain at their existing immutable dataset location. The
published manifest inventories the model payload; the original complete local
inventory remains in `source-run-manifest.json`. The downloaded model passed
its loader, reproduced all 15 held-out predictions exactly and ran the README's
native inference example. It remains experimental, uncalibrated and not
release ready. No serving reference or champion selection was changed.

Verification passed: `uv sync --locked`, all four contract caches checked
with `python3 -B scripts/fetch_contracts.py --all --offline`, Ruff, all 39
publication/model-integrity/documentation pytest cases,
`python3 -B scripts/check_documentation.py` and `git diff --check`.
The earlier full refit suite remains recorded above; no training code changed
in this publication follow-up.

## Integrate the inferred refit into main

On 3 October 2026 the user requested committing and merging the published
inferred refit into main. When local and remote main diverged, the user
explicitly authorized merging origin/main into local main while preserving
both histories. Main reconciliation created commit `4fb4e841`. The refit
then integrated the canonical Gold population implementation and the other
current model and web work from main.

The inferred version 1 wrapper uses the legacy storage verifier for historical
hashes and counters. Runtime refit rows remove selection fields, admit all
candidates and retain prior decisions only as provenance. The integration
adapter policy is `chocolate-gold-training-all-rows-2`. Current canonical
Gold remains `chocolate-gold-population-1`. The already published model and
its source manifests retain their immutable identities and original policy.
Future fits bind the updated implementation, including the population module,
to a new run identity.

Integration verification passed: the locked environment synchronized, all four
pinned contract caches verified offline, and the complete pytest suite passed
580 cases. Seven web tests skipped because npm dependencies and the pinned
web model cache are absent. The additional canonical-population admission
case and all six inferred-refit tests passed in the final focused check.
Ruff, the documentation guard against main and whitespace checks passed.

A fresh local integration fit admitted all 2,134 candidates and selected the
same 55 usable observations. It reproduced all 15 published holdout
predictions, all evaluation metrics and the 84-tree selection exactly.
Both the original complete run and the published subset payload passed the
verified loader. This local verification fit has a new implementation-bound
identity; the published immutable model remains the completed publication.


## Inferred export integration with current main

The inferred exporter and its publication record are integrated with the data
guide relocation, current-price study and Gold population contract. Version 1
builds and verifies its nested child through the explicit legacy storage APIs,
preserving the published source flags and historical regular-price basis.
Current loaders and the inferred model adapter expose every candidate and use
the selected study target. The immutable publication receipt is relocated to
`docs/data/analysis/` with its original bytes. Cached review and inference
artifacts remain under `data/investigation/2026-10-03-field-review/`.

Integration with main `96415842` passed locked dependency installation, all four
offline contract caches, Ruff, the documentation guard and whitespace checks.
The full Python suite passed 611 cases; eight documentation cases initially
failed on links affected by the guide relocation. After correcting those links,
all 27 documentation cases passed. The final focused run after main's validation
update passed all 65 documentation and matched-retailer cases. Seven web cases
were skipped because this worktree lacks Node dependencies and the web model
fixture. The published inferred snapshot also passed verification with the
merged loaders: 3,743 products, 2,134 stored candidates and zero stored eligible
rows; the current training loader exposes all 2,134 candidates. Earlier
publication and test results above describe their recorded revisions.
