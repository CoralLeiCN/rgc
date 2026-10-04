# RGC project intention

Build **retail frontier** to help people research product categories, understand
product features and inspect price positioning through three core features:
**app, model and data**. Each feature has its own intention, scope and constraints.

## Core features

| Feature | Intent | Spec | Responsibility |
| --- | --- | --- | --- |
| App | [App intent](app/intent.md) | [App spec](app/spec.md) | Help retail users explore evidence, compare products, configure proposals and inspect supported analytical results. |
| Model | [Model intent](model/intent.md) | [Model spec](model/spec.md) | Establish and explain supported relationships between product features and observed prices, with explicit assumptions and validation. |
| Data | [Data intent](data/intent.md) | [Data spec](data/spec.md) | Collect, preserve and prepare meaningful product data that can be filtered, joined, compared and summarized for multiple analytical uses. |

The data preparation reassessment recorded on 4 October 2026 belongs to the data
feature. Its exclusion of model planning applies to that reassessment. App and
model goals are documented in their respective feature intentions.

Data supplies evidence and analytical facts for the app, models and other
analyses. Models consume declared data inputs and return results with their
assumptions, support and limitations. The app presents observed evidence,
user proposals and analytical results with their status visible. Data quality,
model validity and application readiness each require their own verification.

## Shared scope

Support arbitrary product categories through category configuration. Chocolate
sold in the United Kingdom is the initial study. Collection and processing
plugins must support additional categories without placing food assumptions in
their common cores.

Retail category managers, buyers and pricing teams are the primary application
users; brand product developers are a related audience. Retailer examples identify
intended users without implying access to internal retailer data or a customer
relationship.

Preserve original source evidence, explicit uncertainty, stable seller identities
and immutable published references across feature boundaries. Author repository
content in English while retaining original source wording in its own language.
Follow [AGENTS.md](../AGENTS.md) for repository language and writing rules.

## Project context and documentation

The retail frontier entry for EAT_HACK on 3 October 2026 belongs to Track 2,
Retail Futures. Its application is **Piece of Cake Pricing**. The two-person
team confirms that no substantial project work existed before EAT_HACK. The
[hackathon brief](eat-hack-track-two.md) owns the challenge, submission and judging
requirements. [PROJECT.md](../PROJECT.md) describes implemented capabilities,
the collection workflow and limitations.

Each feature directory contains `intent.md` for goals and requested scope and
`spec.md` for contracts and supported behavior. The
[specification overview](spec.md) links these specifications and affected guides;
the [lifecycle plan](lifecycle/plan.md) records implementation, verification and
remaining work. The [lifecycle intent](lifecycle/intent.md) provides short
navigation. Maintain these boundaries under the
[documentation policy](documentation-policy.md), and distinguish proposed work
from implemented or validated capabilities.
