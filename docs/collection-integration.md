# Web snapshot integration

The Vercel app consumes a checksum-verified Hugging Face silver snapshot through
`scripts/build_web_snapshot.py`. It exports private JSON for the current app;
there is no standalone HTML explorer or browser data export.
See the [architecture](vercel-architecture.md) and
[app setup](../apps/web/README.md) for API and deployment details.

## Pinned data

Repository: [CoralLeiCN/rgc-collections](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Revision: `d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`.
Silver dataset: `silver-6e246156b7292dd4bb49ebf0`.

| Published measure | Count |
| --- | ---: |
| Source listings | 3,743 |
| Price observations | 2,134 |
| Tracked traits | 103 |
| Retail / brand / unknown seller role | 1,173 / 671 / 1,899 |
| Training candidates | 2,134 |
| Eligible model inputs | 0 |

The published `release_ready` flag is false. Source claims and prices remain
unreviewed; a successful snapshot build does not establish model readiness.
The upstream processing code and immutable published dataset retain their own
versions. Updating code does not automatically migrate the dataset.

## Data contract

The downloader resolves the repository revision once, pins every download to it,
and verifies the latest-pointer/manifest relationship. Ten managed inputs are
checked by byte size and SHA-256: products, prices, training candidates, model
inputs, quality report, product schema, profile, model design, source mappings
and listing aliases. The snapshot reader checks schema versions, the attribute
catalog, field constraints, mapping/predictor references and standardization
rules against these verified files, then validates every product. Historical
display snapshots retain their own contract; current training identity and
price-policy requirements are enforced by the training pipeline.
Rows join by listing ID; observation IDs remain separate.

Original downloaded bytes remain in ignored `data/hf-snapshot/`. Raw archives,
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
# Resolve and download the latest published snapshot, then export private JSON.
python3 -B scripts/build_web_snapshot.py

# Rebuild the pinned download without network access.
python3 -B scripts/build_web_snapshot.py --snapshot data/hf-snapshot/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70

# Write to a separate directory for comparison or review.
python3 -B scripts/build_web_snapshot.py --snapshot data/hf-snapshot/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70 --output /tmp/rgc-snapshot-review
```

Keep the exported JSON and manifest together. Vercel builds verify hashes and
trace the complete snapshot into every API function. Preparation never changes
raw evidence, review gates or model eligibility. Python download requires network
access; the offline rebuild uses only previously downloaded files.

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
Silver export, training corpus and local raw text-evidence export. Users can
select these photos or upload up to two of their own PNG/JPEG/WebP images. The
browser prepares temporary copies within the extraction request limits. Selecting
the example loads the photos, and **Extract traits** requests candidates from the
configured provider. It provides no prefilled traits. Review/apply preserves
the proposed price and keeps the draft outside observed statistics.
