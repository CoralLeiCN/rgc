# Project requirements and design

The [specification overview](../spec.md) links the three canonical feature
specifications. Each feature keeps its intent and spec together:

| Feature | Intent | Spec |
| --- | --- | --- |
| App | [Goals and scope](../app/intent.md) | [User workflows and application contracts](../app/spec.md) |
| Model | [Goals and scope](../model/intent.md) | [Studies, interpretation and validation](../model/spec.md) |
| Data | [Goals and scope](../data/intent.md) | [Collection, preparation and dataset contracts](../data/spec.md) |

Data preserves original evidence in Bronze and produces structured, standardized
Silver with persistent source IDs and profiling reports. Gold owns downstream
comparison groups, target policy, eligibility, features and model-input preparation.
Concrete Silver structures and report methods belong to the
[plan](plan.md#standard-silver-v2-implementation-4-october-2026) and source
investigation. Standard Silver v2 implements this boundary locally. The current
chocolate training interface uses immutable Parquet Gold. The
[stage descriptions](../data/chocolate-silver.md#stage-descriptions) define these
layer responsibilities.
Models validate actual inputs and their selected study before producing results.
The app presents observed evidence, user proposals and analytical outputs with
their support and limitations. The feature specifications own their acceptance
scenarios and link to detailed guides.

The [data preparation reassessment](../data/intent.md#current-focus-meaningful-data-for-analysis)
has an implemented runtime and a 48-listing pilot across 24 sources. Coverage
and unresolved evidence remain explicit. The approved contracts are published
with immutable references; historical studies retain their recorded status in the feature
specifications and [plan](plan.md).

The [documentation policy](../documentation-policy.md) defines ownership and
required updates. The [overall intention](../intention.md) owns shared goals;
[PROJECT.md](../../PROJECT.md) records capabilities and limitations.

The [UK cat litter collection](../data/cat-litter-raw.md) preserves original
Bronze captures and local evidence bundles. Its receipt records source coverage,
retrieval gaps and integrity separately from unverified market completeness.
