# Project requirements and design

The [specification overview](../spec.md) links the three canonical feature
specifications. Each feature keeps its intent and spec together:

| Feature | Intent | Spec |
| --- | --- | --- |
| App | [Goals and scope](../app/intent.md) | [User workflows and application contracts](../app/spec.md) |
| Model | [Goals and scope](../model/intent.md) | [Studies, interpretation and validation](../model/spec.md) |
| Data | [Goals and scope](../data/intent.md) | [Collection, preparation and dataset contracts](../data/spec.md) |

Data preserves original evidence in Bronze, produces reviewed Silver and
provides immutable Parquet Gold for downstream training. The
[stage descriptions](../data/chocolate-silver.md#stage-descriptions) define these
layer responsibilities.
Models validate actual inputs and their selected study before producing results.
The app presents observed evidence, user proposals and analytical outputs with
their support and limitations. The feature specifications own their acceptance
scenarios and link to detailed guides.

The [data preparation reassessment](../data/intent.md#current-focus-meaningful-data-for-analysis)
remains proposed work requiring a reviewed pilot. Current operational data
contracts, model studies and application behavior retain their recorded status
in the feature specifications and [plan](plan.md).

The [documentation policy](../documentation-policy.md) defines ownership and
required updates. The [overall intention](../intention.md) owns shared goals;
[PROJECT.md](../../PROJECT.md) records capabilities and limitations.

The [UK cat litter collection](../data/cat-litter-raw.md) preserves original
Bronze captures and local evidence bundles. Its receipt records source coverage,
retrieval gaps and integrity separately from unverified market completeness.
