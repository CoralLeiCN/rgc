# Web snapshot integration

The Vercel app consumes a verified Hugging Face Gold inferred snapshot through
`scripts/build_web_snapshot.py`. It exports private JSON for the current app;
there is no standalone HTML explorer or browser data export.
See the [architecture](vercel-architecture.md) and
[app setup](../apps/web/README.md) for API and deployment details.

## Pinned data

Repository: [CoralLeiCN/rgc-collections](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Revision: `812a03a5faaced471a2a20f4c389865ed5675826`.
Gold inferred dataset: `gold-inferred-5b539b9c4adbb011a40d7792`.
Source Silver: `silver-f865cac2a7324d5204b797f4`.
The [app collection reference](../apps/web/collection-dataset.json) pins the
immutable revision, dataset path and source manifest SHA-256.

| Published measure | Count |
| --- | ---: |
| Source listings | 3,743 |
| Price observations | 2,134 |
| Tracked traits | 103 |
| Retail / brand / unknown seller role | 1,173 / 671 / 1,899 |
| Training candidates | 2,134 |
| Eligible model inputs | 0 |
| Accepted inferred trait additions | 2,159 |
| Traits with accepted additions | 33 |
| Listings with accepted additions | 1,764 |
| Known / unknown / conflicting attribute cells | 33,845 / 350,224 / 1,460 |

The published `release_ready` flag is false. Accepted additions retain curated
source evidence and per-field review states.
The export preserves its historical `regular-consumer-price-1` training policy
and zero eligible inputs; a successful snapshot build does not establish model
readiness. The separate current-price study retains its own price basis.
The upstream processing code and immutable published dataset retain their own
versions. Updating code does not automatically migrate the dataset.

## Data contract

The default downloader reads the app's immutable collection reference and verifies
its manifest hash before fetching every managed file. Byte sizes and SHA-256
are checked for the complete Gold inferred export. The loader decodes authoritative
`record_json` from `products.parquet`, verifies the source logical record hash,
and loads the nested `training/` snapshot through `verified_gold`. Source Silver
and training identities, contracts, report counts and inference provenance must
agree. The app validates all 103 attributes for every complete product against
the copied profile, mappings and product schema before writing any web assets.
Accepted values, full evidence, methods and review states are preserved in the
source shards. The pinned inference provenance also supplies an immutable link
to original source captures in the evidence inspector.

The historical Silver adapter remains available with `--layer silver` or an
existing Silver `--snapshot`. It validates that snapshot's own contracts. The
app build requires Gold inferred JSON matching the committed collection reference.
Current training identity and price-policy gates belong to their selected training
pipeline.
Rows join by listing ID; observation IDs remain separate.

Original downloaded bytes remain in ignored `data/hf-gold-inferred/`; historical
Silver uses `data/hf-snapshot/`. Raw archives,
assertions and review queues are not bundled into the app. The export contains
`index.json`, `evidence/<source>.json` and a derived `manifest.json`, under
`apps/web/snapshot/`. These are server assets, never public files. The browser
receives bounded API responses and requests source evidence only for a selected
listing. No draft or extracted candidate writes to this snapshot.

Price selection uses the latest dated observation by timezone-aware instant.
Undated or ambiguous timestamps rank last. Same-time conflicts on price,
currency or quantity exclude that listing from price analysis. Unit price must
be positive finite GBP/100g with positive known edible mass from the same
observation. No older price is substituted when the selected one is unusable.

Known, unknown, conflicting and not-applicable traits remain distinct. Missing
claims are not false and missing numeric values are not zero. The matrix index
shortens long text; selected evidence retains full values, methods, review state,
capture IDs and source pointers. Family coverage measures completeness.

## Refresh

From the repository root:

```sh
# Download the pinned Gold inferred export and rebuild private JSON.
uv run python -B scripts/build_web_snapshot.py

# Rebuild without network access from the verified cache.
uv run python -B scripts/build_web_snapshot.py --snapshot data/hf-gold-inferred/812a03a5faaced471a2a20f4c389865ed5675826/gold-inferred-5b539b9c4adbb011a40d7792

# Compare a historical Silver export in a separate directory.
uv run python -B scripts/build_web_snapshot.py --layer silver --output /tmp/rgc-silver-review
```

Keep the exported JSON and manifest together. Vercel builds verify hashes and
trace the complete snapshot into every API function. Preparation never changes
raw evidence, review gates or model eligibility. Preparation uses the locked
PyArrow environment. Download requires network
access; offline rebuilds use the verified cached files. To refresh the deployed
collection, update the immutable app reference and rebuild its JSON together.

## Current display

Terrain X uses observed GBP/100g, Y uses the disclosed shared trait-derived demo
recipe and Z uses a single raw numeric leaf. Colour uses one enum/numeric/boolean/
list leaf, never a parent family. Numeric colours use five fixed full-snapshot
bands. Complete coordinates determine terrain inclusion; missing values remain
in the matrix. The current default has 289 core-range products and 338 in Full.
Observed-price analysis has 892 usable prices regardless of terrain completeness.

The score recipe and smooth coloured layers are illustrative. They do not supply
a fitted pricing benchmark or causal trait effects. Extraction candidates require
explicit review/apply, and the local configured product stays separate from all
observed statistics. Provider setup and current verification are recorded in the
[app README](../apps/web/README.md) and [lifecycle plan](lifecycle/plan.md).

The extraction panel also offers the supplied Well&Truly Fudge & Brownie 30 g
front and back photos as a selectable example. Original JPEG bytes live in
`apps/web/public/examples/well-and-truly/front.jpg` and `back.jpg`; they are
repository demo inputs served as public app assets. They are outside the pinned
collection export, training corpus and local raw text-evidence export. Users can
select these photos or upload up to two of their own PNG/JPEG/WebP images. The
browser prepares temporary copies within the extraction request limits. Selecting
the example loads the photos, and **Extract traits** requests candidates from the
configured provider. Local Next.js development defaults to direct Codex with
ChatGPT OAuth sign-in when no explicit provider, bridge URL or API key is set;
`TRAIT_EXTRACTOR_PROVIDER=codex-local` selects it explicitly. Hosted access uses
a configured OpenAI provider or HTTPS Codex bridge. The example provides no
prefilled traits. Review/apply preserves
the proposed price and keeps the draft outside observed statistics.

## Product prediction demo

The product configurator now separately uses the published synthetic
`lightgbm_without_brand` fixture to predict supported single bar packs and
explain field contributions. Its immutable revision differs from this Gold inferred
web snapshot. Prepare it with `python3 -B scripts/fetch_web_pricing_model.py`;
Git retains only [the pinned reference](../apps/web/pricing-model.json), while
the original model and manifest stay in ignored `apps/web/model-cache/`.
Predictions and exact stored-path SHAP run inside `POST /api/predict-price`
without Python or a network hop. They do not alter observed statistics, review
states, source evidence or eligibility. The fixture retains its historical
regular-price basis and explicit synthetic status. The
[serving guide](data/analysis/web-fixture-pricing.md) owns inputs, attribution
units, verification and limitations. The hosted preview predates this feature.
