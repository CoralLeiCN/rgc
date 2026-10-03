# Collection integration, pricing terrain and extraction

Implemented 3 October 2026.

- [Real collection explorer](visuals/collection-explorer.html)
- [500-product fictional point cloud](visuals/layered-price-landscape.html)
- [Vercel frontend/backend architecture](vercel-architecture.md)
- [Hosted preview](https://rgc-hqvkpvxpj-ptyyyy-s-projects.vercel.app) — Vercel sign-in required
- [Teammate model handoff](model-handoff.md)

## What is usable now

The standalone HTML explorer reads an actual, checksum-verified Hugging Face snapshot. It has
product/source search, seller-role and price-availability filters, a paginated
matrix spanning all 103 tracked traits, selectable 3D axes, and a selected-listing
panel with exact evidence references and price history. Full evidence loads by
source when needed; it is not all parsed on initial page load.

The schema integration exposes typed definitions, units, enum vocabularies,
numeric bounds, review states and the 11 selected model inputs. Numeric range,
enum/boolean and evidence-state conditions build a filtered cohort. Trait columns
can be pinned, and up to four listings can be compared. Definitions distinguish
schema coverage from reviewed evidence and from selection in the model design.
Every listing is validated against the copied snapshot contracts before export.

The Vercel application in `apps/web` consumes the same validated projection as
server-side JSON. Bounded read-only GET routes supply product pages, point and
terrain coordinates, price analysis, schema definitions, comparison and
single-listing evidence; full source shards stay server-side. The new
`POST /api/extract-traits` route submits explicit image/text inputs to a model
provider and returns candidates, without writing the collection. The standalone
HTML remains a separate way to open the snapshot locally.

### Current dashboard behavior

Piece of Cake Pricing now uses a layered 3D terrain. X is observed GBP/100g,
Y is the shared trait-derived prototype score, and Z is one selected numeric
leaf trait in its original units. The score is disclosed as **TRAIT SCORE · DEMO**.
`apps/web/lib/trait-demo.ts` supplies the same recipe for observed listings and
the configured product: base 20 with at least one known scoring input, cocoa
percentage × 0.30, and 10 each for explicit organic, Fairtrade, bean-to-bar,
single-origin and gift-pack claims. Explicit absence adds zero; missing,
conflicting, invalid and truncated inputs are omitted. With no recognized inputs,
the score is unknown. Price and name never affect it; no manual score control or
fitted pricing model is connected.

Only individual leaf fields provide color: numeric/integer, enum, boolean or
string-list traits. Families organize browsing, definitions, filters and matrix
comparison; they do not become aggregate color bars or normalized height indices.
Numeric color uses five equal-width bands calibrated to the full immutable
snapshot, with stable boundaries under filtering. A list field divides its
visual share equally between distinct values. Unknown, conflict, N/A, truncated
and explicitly empty-list states remain visible. The schema still contains flat
families; no deeper family hierarchy has been migrated.

The client builds a 24 × 24 surface using positive local weights in price/score
space. The surface averages nearby Z values and leaves unsupported cells open.
Its layers divide height above an explicit baseline by local category shares;
these are illustrative visual shares, not causal price effects or model
contributions. Exact dots stay at their original price, calculated score and raw
Z. Smoothing and legend highlighting leave point coordinates unchanged. Up to
eight named/state layers plus Other categories are ordered by weighted median Z.
A 2D projection offers the exact coordinates when 3D is unavailable.

`/api/terrain` applies the common cohort and Core/Full price range, with bounded
deterministic sampling and explicit missing-coordinate/tail counts. Missing
score or Z removes a row from the terrain, not from the matrix or observed-price
analysis. Family actions help select eligible leaf filters/color/height fields.
Matrix and shortlist families expand independently, share pinned traits and
per-family limits, and retain full-schema evidence denominators.

The right column configures a local product. Proposed pack price and edible
weight determine GBP/100g; an exact price input and price slider change only the
price coordinate. The score is read-only with a rule breakdown. A valid selected
raw Z value is also required for its terrain marker. Missing/invalid coordinates
are not invented. The display can extend to an out-of-range proposed price
without adding it to the observed cohort or changing its range. Explicit listing
import copies known, untruncated traits and same-observation usable price/weight;
ordinary listing selection preserves edits. Source evidence stays in a collapsed
disclosure. Drafts never enter the dataset, gap/brand statistics or model inputs.

### Image and text candidate extraction

A description of up to 12,000 characters and/or a PNG, JPEG or WebP image up to
2 MiB can be submitted to `/api/extract-traits`. The server validates input limits,
image contents and schema output, returning provider/model metadata, trait
candidates, evidence and warnings. The retailer checks candidates before pressing
Apply. Applying replaces only selected matching draft inputs, maps name/weight
to their controls and preserves proposed pack price and unrelated edits. A
candidate is not an independently reviewed source fact. Its applied traits
recalculate only the declared prototype score.

The client aborts stale work when extraction inputs change. Reset or explicit
listing import also clears the extraction session and previews. Async arrival
never overwrites edits; apply always merges into the latest draft. Image preview
URLs are released, and the app does not persist uploads, candidates or drafts.

The route supports server-side OpenAI configuration or an authenticated HTTPS
bridge to a local Codex CLI session, including the requested Tailscale laptop
connection. No provider keys are entered in the frontend. Unconfigured providers
return a useful 503 setup error. The local bridge implementation and controller
checks do not establish a live model call: Codex startup is blocked in the current
sandbox, so that path and its network configuration remain unverified. Provider
setup and runnable commands belong to the
[application README](../apps/web/README.md). This extraction provider is separate
from the teammate's unconnected pricing model.

Observed gaps and brand price positioning still come from `/api/analysis`, across
the full filtered cohort independently of terrain completeness or matrix pages.
Core/Full ranges disclose tail exclusions, and brand metrics retain the full
priced cohort. Gap highlights show collected empty intervals, not inferred
demand. Brands are ranked by median observed price with minimum sample support,
not sales, profit or causal premium. The [architecture](vercel-architecture.md)
owns the statistical rules.

### Earlier deployment and visual studies

The previously recorded application release passed production build, TypeScript
and 70 API/display/controller tests on Node 24. Its six backend function traces
contained the private snapshot with a 4 MB response ceiling. That protected
preview passed 14 representative hosted HTTP cases and eight Next.js asset
checks. These are historical proof for the earlier 2D dashboard, not proof that
the latest terrain/extraction changes are hosted. Current checks and deployment
status are recorded in the [lifecycle plan](lifecycle/plan.md). Default Vercel
sign-in protection remains enabled. Live browser/GPU verification remains
unavailable in this sandbox.

The previous 2D fictional stacked-score chart, family score drilldown and manual
configured-product score are retired from the current Dashboard. Legacy
components and the optional analysis demo-score payload remain separate fixtures.
The older 3D points API/controller and static HTML explorer retain their
observed-price behavior; their default weight/cocoa/price axes have 338 complete
listings. The current terrain uses a different score/Z completeness gate, while
observed gap and brand analysis require only usable price context.

## Downloaded snapshot

Repository: [CoralLeiCN/rgc-collections](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Pinned revision: `d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`, updated
`2026-10-03T12:26:06Z`. Silver dataset: `silver-6e246156b7292dd4bb49ebf0`.

| Published measure | Count |
| --- | ---: |
| Source listings | 3,743 |
| Price observations | 2,134 |
| Tracked attributes | 103 |
| Retail / brand / unknown seller role | 1,173 / 671 / 1,899 |
| Training candidates | 2,134 |
| Eligible model inputs | **0** |

The published `release_ready` flag is false and `model-inputs.jsonl` is empty.
Every training candidate is excluded. Product scope, physical identity, predictor
review, edible quantity, tax basis and regular-price context still need review.
The source manifest names cleanup, standardization and model-design modules.
Those backend files and the self-contained category-processing plugin are now
available locally after pulling `3e9c833`. The explorer still reads the pinned
published snapshot and its own copied contracts; pulling code does not rebuild
or migrate that dataset. The original chocolate CLI and portable category plugin
use distinct contracts, documented in the [processing guide](category-processing.md).

The downloader resolves the repository revision once, pins subsequent requests
to it, and checks the latest-pointer/manifest relationship. The builder verifies
byte sizes and SHA-256 hashes for all ten downloaded managed inputs. Rows join
by listing ID; price observation IDs remain distinct.

Downloaded: normalized products, prices, training candidates, model inputs,
quality report, product schema, profile, model design, source mappings, and
listing aliases, plus metadata, latest pointer, manifest and README. Large raw
evidence/source-listing/assertion/review-queue files are not downloaded for this
UI. Original downloaded bytes remain under ignored `data/hf-snapshot/`.
Browser projections and on-demand evidence are under `docs/visuals/data/`.

## Price and trait rules

- One plotted point represents a source listing, not a proven unique physical product.
- Select the latest dated observation by timezone-aware instant. Undated or
  timezone-ambiguous observations rank last. Do not fall back to an older price
  merely because the latest one lacks a usable unit price.
- Same-time disagreement on price, currency or quantity excludes a listing from
  price axes. There are 34 such listings in this snapshot.
- Unit-price axes require a positive finite published GBP value and positive,
  known edible quantity. The values retain their unreviewed status.
- The standalone explorer's default weight axis uses that same price observation's quantity, rather
  than a potentially different quantity from another capture.
- The Vercel API also excludes the observation-weight coordinate when the latest
  price observations conflict, avoiding an arbitrarily selected weight from a tie.
- Known, unknown, conflicting and not-applicable traits stay distinct. Unknown
  organic/vegan/nuts claims do not become false; missing numbers do not become zero.
- Matrix columns rank by known-value coverage. All 103 can be viewed, searched
  and filtered by family. Coverage is not confidence.
- Long matrix text is shortened in the index; the panel loads its full value,
  extraction method, review status, capture ID and JSON pointer on demand.

## Earlier point-cloud rotation investigation

In the earlier point-cloud study, the subagent found no camera-event feedback loop. The previous default scene had
17 traces, translucent markers and a default 2× resolution in both dimensions.
Those increase orbit rendering work; an end-of-drag click could also select a
product and trigger a full update.

That patch uses five batches, opaque markers and 1× WebGL resolution. All 500
products and 7,674 layer samples remain. Camera presets update only the camera;
orbit events do not rebuild data. Drag-ending clicks are ignored, rapid updates
coalesce and scene updates wait until the pointer drag ends. The real-data
explorer follows these principles with two traces. This is a structural
performance fix, not a measured frame-rate claim.

## Run and refresh

Open either HTML file directly with its sibling assets intact. No server or
frontend package installation is required. Evidence uses local script loading
so it also works with a local file URL.

```sh
# Download the latest published silver snapshot and rebuild.
python3 -B scripts/build_collection_explorer.py

# Rebuild this downloaded snapshot without network access.
python3 -B scripts/build_collection_explorer.py --snapshot data/hf-snapshot/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70

# Also prepare the self-contained Vercel application's private data bundle.
python3 -B scripts/build_collection_explorer.py --snapshot data/hf-snapshot/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70 --server-output apps/web/snapshot

# Integrity and browser-controller checks.
python3 -B -m unittest discover -s scripts/tests -p 'test_collection_explorer.py' -v
node docs/visuals/check-collection-explorer.cjs
node docs/visuals/check-layered-price-interactions.cjs
```

This session downloaded via curl and ran the builder offline. The Python HTTPS
download path is provided for environments with network access.
The server export includes `index.json`, `evidence/<source>.json` and a derived
SHA-256/byte-length manifest. Its 28,020,670 JSON data bytes are bundled privately
with the backend, not sent to each browser. The largest listing evidence document
in this snapshot is 61,028 bytes. Preparation keeps raw files unchanged and does
not fit a model or alter review gates. See the
[application README](../apps/web/README.md) for install/build/deploy commands.
The initial `git pull --rebase --autostash` attempt in the agent session failed
because Git could not resolve GitHub. A subsequent pull reached `3e9c833` and
restoring the autostash conflicted in three documentation files. These were
reconciled to preserve upstream processing/schema contracts and the retailer/UI
work. The working branch matches `origin/main`; the autostash remains as a backup.

Checks passed for integrity, count reconciliation, timestamp ordering, same-time
conflicts, original evidence preservation, missing values, currency/quantity
exclusions, filtering, all 103 columns, selection and on-demand evidence loading.
Controller checks confirm camera events do not replot and dragging does not
select a product. Live WebGL/GPU behavior remains unverified because browser
startup is blocked in this workspace.

## Next useful implementation

Use the newly pulled cleanup/model-design backend and its documented review
workflow. Select a narrow retailer-facing cohort, review price
and trait evidence, and rebuild silver until rows pass the eligibility gate.
Then fit and evaluate a baseline with an appropriate held-out product grouping,
and add model explanations that reconcile to predictions on a compatible basis.
Keep those signed contributions and uncertainty distinct from the terrain's
raw-trait heights and illustrative layers. Do not silently bypass review gates
to train on currently excluded rows.
