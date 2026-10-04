# Processing contract

The [standard Silver v2 reference](standard-silver.md) owns default `process`,
four-contract authoring, durable human corrections and generated reports. This
reference preserves the historical v1 interface and applicable research guidance;
use `process --legacy` for v1 outputs. Gold owns model policy in the v2 workflow.

Use the entire plugin directory with Python 3.9+. The core uses the standard
library and local archives. Packaged contracts resolve pinned Hugging Face
references, downloading missing bytes and verifying SHA-256 hashes and byte
lengths. A populated verified cache or full custom profile supports offline
execution. The package runs independently of repository sibling modules and
client installation. `<plugin-root>` contains `plugin.json` and `cli.py`.

The skill checks readable preserved raw data and a generated schema for the same
category/market before applying processing. A missing schema routes to
category-schema; missing raw data routes to collection. Processing finishes at
reviewed Silver. The [Silver-to-Gold procedure](silver-to-gold.md) owns model-input
preparation. The existing runtime still requires a legacy model contract and
writes training views listed below; this workflow revision does not remove those
compatibility outputs or implement model-independent processing.

```text
python3 <plugin-root>/cli.py process --archive-root <collections-root> --profile <profile-folder> --output <silver-root> [--reviews <reviews.json>]
python3 <plugin-root>/cli.py process --archive-root <collections-root> --category chocolate --contracts-cache <cache-root> --output <silver-root> [--offline]
```

Another Python caller can place the plugin root on its import path and use
`category_processing.pipeline.build_silver_dataset(archive_root, output,
profile_root, reviews=None)`. Reviews may be a JSON-file path or a decision object.
They record evidence-backed agent assessments; they do not require user approval.
If schema changes, review of the detailed summary before a Hugging Face commit
or publication of the changed schema or its rebuilt data is the only required
user-facing review; see [mapping maintenance](mapping-maintenance.md#hugging-face-release-review).
The calling harness waits for authorization of that exact release after local
contracts, rebuilds and checks are ready. These local commands do not upload.
This function returns the quality report and writes the snapshot. CLI execution
additionally compares a prior output ledger and reports counts of processing changes.
Use `category_processing.profiles.resolve_profile(category="chocolate",
cache_root=<cache-root>, offline=True)` to materialize a verified pinned directory
before an API call. Existing full custom profile directories remain supported;
profile directories containing a dataset reference resolve its pinned bytes.
The CLI requires exactly one of `--category` and `--profile`. Its default cache
is `<plugin-root>/.contract-cache`; supply a writable cache when the installation
permits no writes. Offline mode fails when pinned bytes are unavailable or corrupt.

The archive root contains
`<category-slug>/<market-slug>/products/<source_key>/<product_id>/product.json`.
Legacy `products/<product_id>/product.json` indexes are also accepted, including
mixed archives. Source-directory names must equal the raw capture source key; `_unknown`
represents missing, null or empty keys without assigning a seller identity.
Product IDs remain unique across the study; ambiguous duplicate directories are
reported as errors. Read the stored history/artifact references rather than
reconstructing paths. Grouping by website supports source mappings under a
shared category schema; it does not change seller UIDs.
Slugs case-fold category/market values, replace runs outside ASCII letters/digits
with hyphens and trim edge hyphens, matching collection directory names. Exact
safe-name paths are accepted as a fallback for other compatible producers.
Original envelope category/market must still equal the profile values exactly;
path normalization does not change seller identity or source evidence.
Each index follows `category-research-raw-1`, identifies category, market and
product, and contains captures plus `latest_capture_id`. Capture history paths
are relative to the archive root. Index and immutable history must agree;
capture IDs are unique, identities match their folders, and each folder's source
key and exact seller identity remain stable across captures. Invalid folders are
reported; identity changes fail folder integrity. Original captures
and source/image artifacts remain unchanged in raw.

Exact seller identity uses source key, URL host, source product ID and optional
source variant ID. Only identical tuples merge. Similar names, brands, images or
GTINs do not merge different sellers. Unresolved identities stay separate.
`seller_uid` hashes category, market and this identity independently of canonical
display `listing_id`; selecting another alias cannot change the seller UID.
Product brand is distinct from seller identity and `brand`, `retail` or `unknown`
role. Unsupported source keys remain in the unknown partition.
Missing/empty/malformed source keys become unknown derived selling context and
nontext brand values become null; preserve their original raw values.

Silver combines verification, deduplication, typed standardization, normalized
observations, reviews supported by evidence and model eligibility. Inspect the actual
manifest and quality report before using results.
The layer is `category-processing-silver-1`; manifest/report formats are
`category-processing-silver-manifest-1` and `category-processing-silver-report-1`.
Archive verification compares indexes and history and checks the input snapshot;
this build does not rehash every preserved source/image artifact's payload.

| Output | Meaning |
| --- | --- |
| `source-listings.jsonl`, `listing-aliases.jsonl` | Unchanged captures grouped by seller and relationships between raw folders and canonical listings. |
| `products.jsonl`, `assertions.jsonl` | Complete typed attribute envelopes and assertions supported by sources. |
| `prices.jsonl` | Observations linked to evidence on the profile's currency/quantity basis. |
| `training-candidates.jsonl`, `model-inputs.jsonl` | Proposed inputs with exclusions and eligible reviewed rows respectively. |
| `review-queue.jsonl` | Unsupported/conflicting evidence and unresolved eligibility decisions. |
| `processing-ledger.jsonl` | Capture fingerprints and processing outcomes. |
| `mapping-review-batches.jsonl`, `mapping-review-summary.md` | Grouped evidence gaps for the calling harness. |
| `discovered-fields.jsonl`, `schema-extension-review.md` | Full typed unhandled raw fields (`category-unmapped-fields-1`) and bounded evidence-backed proposal worksheets; meaning/scope/unit remain unresolved. |
| `profile.json`, `source-mappings.json`, `product.schema.json`, `model-design.json`, `pipeline.json` | Exact copies of all five contracts. |
| `quality-report.json`, `manifest.json` | Coverage, exclusions/readiness, versions, fingerprints, hashes, contract source/revision and raw artifact roots. |
| `brand/`, `retail/`, `unknown/` | Products, prices and source listings partitioned by seller role. |

Resolve capture IDs and JSON pointers rooted in captures through `source-listings.jsonl`;
original bytes remain under the manifest's raw artifact roots. Reviews require
the relevant observation's evidence, reviewer and reason. Do not borrow a later
recipe to classify an older price. Read the profile's review format and model
design for identity, family, scope, feature and price requirements.

The command rebuilds the complete snapshot. Comparison against the previous ledger reports
`new`, `unchanged`, `capture_changed`, `rules_changed` and `retry`; it does not skip
unchanged captures. Use a new output path to retain an immutable training
snapshot. Output stays separate from raw. Summary/model consumers verify managed
hashes. Exit codes are 0 for success, 1 for partial processing and 2 for fatal
errors. `complete_snapshot` proves accepted input consistency, not complete
extraction or model readiness.

Default structural discovery scans `/raw_record` beyond handled fields and
exact archive/core context. Optional recipe `discovery` defines raw roots,
additional exclusions or explicit disabling; the quality report saves effective
coverage and counts. Highest unhandled meaningful subtrees retain their complete
typed values and source pointers, including zero/false and nested nulls. Handled
subtrees are skipped; partially handled ones yield unhandled siblings. Original
raw data and typed product facts stay unchanged by discovery. The mechanism
does not parse unseen concepts from already-used text or open source artifacts.
Read [schema-discovery.md](schema-discovery.md) before writing proposals. Keep
agent narratives outside managed snapshot artifacts. The `summarize` command
regenerates discovery evidence/worksheets from covered, verified snapshot files;
old snapshots without discovery remain supported.
For an older snapshot, reusing an output directory removes obsolete generated
`discovered-fields.jsonl` and `schema-extension-review.md` files and leaves other
files intact. Unsafe write/removal paths are rejected before packet changes.
Mapping summaries quote and escape source-derived labels and values as bounded
JSON code spans; full evidence remains in their JSONL batches.

All model targets use `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price, with reject fallback. Currency and quantity normalization remain category-specific. Custom authoring adds the fixed policy metadata to design and recipe; source amounts and tax inclusion still require independent evidence. Model preparation records the same policy on each target and in the frozen encoder.
