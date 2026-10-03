# Processing contract

Use the entire plugin directory with Python 3.9+. The core uses the standard
library and local files. No repository sibling module, network service or
particular client installation is required. `<plugin-root>` contains
`plugin.json` and `cli.py`.

```text
python3 <plugin-root>/cli.py process --archive-root <collections-root> --profile <profile-folder> --output <silver-root> [--reviews <reviews.json>]
```

Another Python caller can place the plugin root on its import path and use
`category_processing.pipeline.build_silver_dataset(archive_root, output,
profile_root, reviews=None)`. Reviews may be a JSON-file path or a decision object.
This function returns the quality report and writes the snapshot. CLI execution
additionally compares a prior output ledger and reports processing-change counts.

The archive root contains `<category>/<market>/products/<product_id>/product.json`.
Each index follows `category-research-raw-1`, identifies category, market and
product, and contains captures plus `latest_capture_id`. Capture history paths
are relative to the archive root. Index and immutable history must agree;
capture IDs are unique, identities match their folders, and each folder's source
key and exact seller identity remain stable across captures. Invalid folders
are reported rather than reinterpreted under a different shop. Original captures
and source/image artifacts remain unchanged in raw.

Exact seller identity uses source key, URL host, source product ID and optional
source variant ID. Only identical tuples merge. Similar names, brands, images or
GTINs do not merge different sellers. Unresolved identities stay separate.
`seller_uid` hashes category, market and this identity independently of canonical
display `listing_id`; selecting another alias cannot change the seller UID.
Product brand is distinct from seller identity and `brand`, `retail` or `unknown`
role. Unsupported source keys remain in the unknown partition.
Missing/empty/malformed source keys become unknown derived selling context and
non-text brand values become null; preserve their original raw values. A changed
source identity across captures still fails folder integrity rather than merging
that history under the latest source.

Silver combines verification, deduplication, typed standardization, normalized
observations, evidence-backed reviews and model eligibility. Inspect the actual
manifest and quality report before using results.
The layer is `category-processing-silver-1`; manifest/report formats are
`category-processing-silver-manifest-1` and `category-processing-silver-report-1`.
Archive verification compares indexes and history and checks the input snapshot;
this build does not rehash every preserved source/image artifact's payload.

| Output | Meaning |
| --- | --- |
| `source-listings.jsonl`, `listing-aliases.jsonl` | Unchanged captures grouped by seller and raw-folder-to-canonical relationships. |
| `products.jsonl`, `assertions.jsonl` | Complete typed attribute envelopes and source-supported assertions. |
| `prices.jsonl` | Evidence-linked observations on the profile's currency/quantity basis. |
| `training-candidates.jsonl`, `model-inputs.jsonl` | Proposed inputs with exclusions and eligible reviewed rows respectively. |
| `review-queue.jsonl` | Unsupported/conflicting evidence and unresolved eligibility decisions. |
| `processing-ledger.jsonl` | Capture fingerprints and processing outcomes. |
| `mapping-review-batches.jsonl`, `mapping-review-summary.md` | Grouped evidence gaps for the calling harness. |
| `profile.json`, `source-mappings.json`, `product.schema.json`, `model-design.json`, `pipeline.json` | Exact copies of all five contracts. |
| `quality-report.json`, `manifest.json` | Coverage, exclusions/readiness, versions, fingerprints, hashes and raw artifact roots. |
| `brand/`, `retail/`, `unknown/` | Products, prices and source listings partitioned by seller role. |

Resolve capture IDs and capture-root JSON pointers through `source-listings.jsonl`;
original bytes remain under the manifest's raw artifact roots. Reviews require
the relevant observation's evidence, reviewer and reason. Do not borrow a later
recipe to classify an older price. Read the profile's review format and model
design for identity, family, scope, feature and price requirements.

The command rebuilds the complete snapshot. Previous-ledger comparison reports
`new`, `unchanged`, `capture_changed`, `rules_changed` and `retry`; it does not skip
unchanged captures. Use a new output path to retain an immutable training
snapshot. Output stays separate from raw. Summary/model consumers verify managed
hashes. Exit codes are 0 for success, 1 for partial processing and 2 for fatal
errors. `complete_snapshot` proves accepted input consistency, not complete
extraction or model readiness.
