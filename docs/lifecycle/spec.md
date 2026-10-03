# Project requirements and design

[Canonical specification](../spec.md) owns contracts and acceptance requirements.
The essential sequence is:

The retailer-facing [collection explorer](../collection-integration.md) consumes
an immutable published silver snapshot, exposes known/unknown/conflicting trait
states, and plots available observations without changing upstream review gates.
It keeps price observations tied to their quantities and evidence. The trait-derived demo score does not establish a trained benchmark. The intended validated workflow supports retail
SKU price review as well as a brand's new-product test.

The [Vercel architecture](../vercel-architecture.md) defines a single Next.js
frontend/backend application under `apps/web`, an expandable family matrix,
a layered price/trait-score/numeric-leaf terrain, observed gap finder and brand
price-position analysis, with private bundled snapshot/evidence assets. Parent
families organize navigation; only leaf fields supply colour and only one numeric
leaf supplies raw Z. Draft scores are trait-derived and read-only; a proposed-price
slider moves the draft without changing observed analysis. Image/text extraction
returns reviewable candidates through OpenAI or a token-protected local Codex bridge.
The server returns bounded pages, terrain coordinates, aggregate analysis; the browser does not load the full collection
index. Schema validation, typed filter bounds and original review semantics
apply at the interface. The delivery stack is decided; hosted verification and
implementation status are recorded in the plan.

```text
bronze/raw -> silver (deduplication + standardization + reviews/gates)
           -> immutable Parquet Gold -> experimental trainer -> later validated model
```

The [stage descriptions](../data/chocolate-silver.md#stage-descriptions) label raw
as bronze and describe Silver processing and immutable Parquet Gold export.
Gold preserves candidate and eligible views; zero eligible chocolate inputs
produce a readiness report from the implemented experimental trainer. Validated
price testing and explanations remain planned.

Preserve broad original evidence, exact seller identities and provenance.
Retain explicit unknown/conflict states, separate attributes from observations,
and distinguish candidates from reviewed model inputs. Brand identity and seller
role remain distinct, with brand, retail and unknown partitions.

Collection sections and processing fields, units, quantity and pricing basis
belong to each study. `init-profile` validates five aligned local working
contracts without copying a packaged profile. Structural discovery preserves
unconfigured raw fields and creates schema-extension worksheets; interpretation,
predictor selection and durable proposal decisions require evidence assessment.
The agent may apply supported local changes without user approval. A changed
schema requires a detailed release summary and user review before its Hugging
Face commit under the [standing decision](../decisions/agent-led-schema-maintenance.md).

Training requires reviewed scope, identities, price/quantity basis and features,
comparison groups, validation grouped by family, preprocessing learned from
training rows, support checks and a defined policy for missing values. Insights
state units, references, context, uncertainty and limits.

| Guide | Design detail |
| --- | --- |
| [Silver](../data/chocolate-silver.md) | Raw/index/history verification, captures/aliases, outputs and compatibility helpers. |
| [Chocolate schema](../data/chocolate-schema.md) | Dataset contracts pinned by `schemas/chocolate/dataset-contract.json`, review decisions and pricing handoff. |
| [Portable processing](../data/category-processing.md) | Standalone runtime, five contract references, stable seller envelope, fingerprints/batches and harness maintenance. |

Contract bodies are authoritative in Hugging Face and downloaded into verified
ignored caches. Git retains human documentation and immutable revision/hash/version
manifests. The [dataset contract guide](../data/dataset-contracts.md) owns storage and
offline behavior.

Profiles are fixed per run; accepted changes rebuild a new complete snapshot
while retaining prior data and model versions. The portable chocolate envelope
uses distinct versions from the established CLI. See the
[plan](plan.md) for validation, native installation and future work, and the
[documentation policy](../documentation-policy.md) for required updates.

The [Gold contract](../data/chocolate-gold.md) defines Parquet pass-through, provenance, optional user-directed bulk review and verified training input. The [schema guide](../data/chocolate-schema.md) defines reusable family mappings and experimental OLS. The current chocolate study uses `current-consumer-price-1`: displayed prices normalized to GBP per 100 g, with no separate regular-price or confirmed-tax requirement. Historical regular-price contracts retain `regular-consumer-price-1`. The prepared contracts require an approved verified dataset release before updating immutable references.

## Independent LightGBM without brand

The [without-brand implementation](../data/analysis/lightgbm-without-brand-implementation.md)
provides its own regular-price working experiment, seeded family partitions,
family balancing, fitting-only grouped tuning, retailer calibration and native
raw-log TreeSHAP reconstruction. It saves immutable runs and supports verified
run loading. Synthetic validation is published separately from real fitting.
The web product form now serves the published historical synthetic fixture
through a bounded Node prediction API, with native-equivalent field SHAP values
and reconciled price allocations. Current-price migration, real market
comparisons and released real-data scenario interfaces remain pending. [Model maintenance](../model-maintenance.md)
owns artifact storage in Hugging Face and immutable receipts in Git.

The independent [hedonic trainer](../data/analysis/hedonic-without-brand-implementation.md) implements family-weighted fitting, calibration and support under a local working policy. The published Gold handoff and reviewed real data are insufficient: no real model or release is established, and aligned producer/portable contract migration remains pending.
