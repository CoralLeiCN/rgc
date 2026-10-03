# Pricing model handoff for the retailer workspace

Status: proposed integration boundary for the teammate building the pricing and
scoring model. No model, prediction service or score is connected to the app yet.
The application owns data exploration, deployment and presentation; the teammate
owns feature/model decisions, training, scoring definitions and evaluation.

## Shared data reference

Rechecked the public dataset on 2026-10-03. Its current revision is still
`d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`, which is the application's pinned input.

| Artifact | Purpose |
| --- | --- |
| [Raw product index](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/blob/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70/products.jsonl) | Source-specific product/variant records. Identity and latest information are JSON strings, preserving arbitrary source fields. The loader's `train` split is not a reviewed modeling split. |
| [Raw text evidence archive](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/blob/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70/evidence/chocolate/uk.tar.gz) | Original product JSON, capture histories, text/HTML/JSON evidence, catalogues and collection reports. |
| [Raw export manifest](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/blob/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70/export-manifest.json) | Archive size, SHA-256, included-file counts and deliberate omissions. |
| [Silver snapshot](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70/silver/chocolate/uk/silver-6e246156b7292dd4bb49ebf0) | Typed products, separate price observations, listing aliases, reviews/eligibility and the exact contracts used for this build. |
| [Application interfaces](../apps/web/lib/contracts.ts) | Current schema, product, observation, evidence and point-cloud response shapes. |

The archive is **513,744,886 compressed bytes**, contains 22,372 files and
3,608,764,602 included bytes. Its SHA-256 is
`b95dfe3e0963bd59ffb82f07febd2c004827351d4e9c11c264de115362f4cbaa`.
The export preserves raw text evidence but deliberately omits images and HTTP
transfer caches. The archive was inspected through its published manifest; it
was not downloaded or bundled into the web deployment in this session.

Keep raw data and model training outside page requests. The current web backend
uses the smaller verified silver projection and selected-listing evidence.
The [collection integration guide](collection-integration.md) owns preparation
commands and the exact app snapshot. If the model uses a newer snapshot, update
the web snapshot and prediction artifact together.

## Joins that must stay explicit

- The app's `Product.id` is the established silver **listing ID**, not a globally
  deduplicated physical SKU. Different sellers retain separate records.
- `Product.sourceListingIds` preserves raw aliases. Use the snapshot's
  `listing-aliases.jsonl` if the model starts from the raw index.
- A price-sensitive result identifies the **observation ID**, not just a listing.
  Each listing may contain several observations with different dates or weights.
- Carry the Hugging Face revision, silver dataset version, schema version and
  model version with every artifact. A mismatch needs an explicit migration.
- The portable category-processing profiles use a distinct stable seller
  envelope. Do not equate their UIDs with the established listing IDs by string
  similarity; supply an explicit mapping if the model uses that profile.
- Missing traits retain their known/unknown/conflict/not-applicable states.
  Never encode an unknown certification as false or an unknown number as zero.

## Proposed model output

The user confirmed that the teammate will provide a **hosted prediction API**.
The browser will call a same-origin Vercel backend adapter, which will call that
service with server-held configuration and credentials. This keeps the web
release independent of the model's runtime and training dependencies. The
provider URL, request/response examples or OpenAPI document, and authentication
method have been requested and are still pending. The field names below are a
proposed semantic boundary to map to that service, not an assertion about its
existing wire format. No prediction endpoint or analytical machine-contract
change is implemented by this document.

The [hosted adapter design](hosted-model-api.md) describes the request flow,
server-side configuration, validation and failure states. Endpoint wiring remains
pending the teammate's actual service contract.

| Field | Expected meaning |
| --- | --- |
| `model_version`, `generated_at` | Reproducible model identity and output time. |
| `dataset_revision`, `dataset_version`, `schema_version` | Exact input data and schema provenance. |
| `validation_status` | Explicitly `experimental` or `validated`, backed by the model's evaluation report. |
| `target` | Currency, unit, regular/displayed/promotion basis, tax context, category, cohort and output transform. Report whether a price is a mean, median or another statistic. |
| `results[].listing_id`, `observation_id` | Exact join to the app listing and price observation. |
| `results[].status`, `support_reasons` | Supported, unsupported or unavailable, with an explanation when no result is usable. |
| `results[].predicted_price` | Finite positive prediction on the declared price basis, or null. Optional for a score-only model. |
| `results[].prediction_interval` | Lower/upper bounds and declared coverage level, or null when unavailable. Distinguish prediction intervals from confidence intervals. |
| `results[].score` | Value plus name, definition, range, direction and reference cohort, or null. Do not assume a universal 0–100 value-for-money scale. |
| `results[].explanation` | Optional baseline and signed per-trait contributions, their units/space and reference values. Include unexplained or rounding remainder explicitly. |
| `results[].comparison_basis_compatible` | Whether the selected observed price and model prediction can be compared on quantity, promotion, tax and timing context; include reasons when they cannot. |

The current design's regression target is log regular GBP per 100 g. The web
cloud currently uses displayed observed GBP per 100 g. These bases are not
automatically comparable. A model predicting another basis must identify it;
any change to the established analytical design follows the repository's
versioned-contract workflow. The teammate's experimental outputs do not silently
turn existing unreviewed records into reviewed, release-ready inputs.

## How results will become visual

Join results to the selected listing and observation. Show observed and predicted
prices, interval and support status together. A price gap is shown only when the
comparison basis matches. An observed-minus-predicted gap is not labelled a
causal brand premium.

For the layered 3D study, contributions must reconcile to the model output in a
declared space. GBP contributions can form signed currency layers; log-space
contributions must not be labelled as GBP thicknesses. If the model supplies only
a score, show a clearly labelled score color scale without manufacturing a
predicted price or feature decomposition. Keep the existing fictional study
separate until real outputs and their interpretation are validated.

When the service contract is ready, add a server-side adapter, reject version
and observation mismatches, validate finite values and units, and add a linked
model layer to the dashboard. Until then, the deployed workspace remains an
observed-data explorer with no generated model scores.
