# Project requirements and design

[Canonical specification](../spec.md) owns contracts and acceptance requirements.
The essential sequence is:

```text
raw collection -> silver (deduplication + standardization + reviews/gates)
                      -> reviewed eligible inputs -> later validated model
```

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
| [Silver](../chocolate-silver.md) | Raw/index/history verification, captures/aliases, outputs and compatibility helpers. |
| [Chocolate schema](../chocolate-schema.md) | Dataset contracts pinned by `schemas/chocolate/dataset-contract.json`, review decisions and pricing handoff. |
| [Portable processing](../category-processing.md) | Standalone runtime, five contract references, stable seller envelope, fingerprints/batches and harness maintenance. |

Contract bodies are authoritative in Hugging Face and downloaded into verified
ignored caches. Git retains human documentation and immutable revision/hash/version
manifests. The [dataset contract guide](../dataset-contracts.md) owns storage and
offline behavior.

Profiles are fixed per run; accepted changes rebuild a new complete snapshot
while retaining prior data and model versions. The portable chocolate envelope
uses distinct versions from the established CLI. See the
[plan](plan.md) for validation, native installation and future work, and the
[documentation policy](../documentation-policy.md) for required updates.

The [Gold contract](../chocolate-gold.md) defines Parquet pass-through, provenance, optional user-directed bulk review and verified training input. The [schema guide](../chocolate-schema.md) defines reusable family mappings and experimental OLS. All models retain `regular-consumer-price-1`; no displayed/promotional/reference or unknown-tax fallback is supported. The prepared contracts require an approved verified dataset release before updating immutable references.
