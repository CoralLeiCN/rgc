# Project specification overview

The specification is organized by core feature. Each feature directory contains
its intention and its specification; the [overall intention](intention.md) owns
shared project goals and boundaries.

| Feature | Intention | Specification | Contract ownership |
| --- | --- | --- | --- |
| App | [App intent](app/intent.md) | [App spec](app/spec.md) | User workflows, application interfaces, evidence presentation, product drafts and synthetic demo serving. |
| Model | [Model intent](model/intent.md) | [Model spec](model/spec.md) | Study inputs, targets, estimators, explanations, validation, uncertainty and release requirements. |
| Data | [Data intent](data/intent.md) | [Data spec](data/spec.md) | Collection, source preservation, identity, structured facts, processing, quality, storage and dataset interfaces. |

Detailed requirements and acceptance scenarios live in the owning feature
specification. Existing section numbers are retained there to keep moved
requirements recognizable. Supporting guides and immutable dataset contracts
continue to own the details linked from those specifications.

## Interfaces between features

Data preserves source evidence and produces versioned analytical records and
immutable dataset interfaces. The model feature validates its actual inputs and
study assumptions before fitting or releasing results. The app consumes pinned
data and model artifacts, presents their status and keeps user proposals distinct
from collected observations.

The requested review interface connects downstream error reports to Silver
fields and their Bronze evidence. The app owns user review and revision; data
owns durable corrections and replay on subsequent processing runs. Corrections
also supply evidence for improving rules, models and regression tests. This
interface is implemented locally through the portable review server and SQLite
store described in the
[app](app/spec.md#persistent-review-of-standardized-data) and
[data](data/spec.md#persistent-corrections-and-replay) specifications.

The intended layers are Bronze for preserved source evidence, Silver for
structured and standardized data, and Gold for further enrichment serving a
downstream use case. Silver preserves source IDs across reprocessing and reports
schema coverage, categorical values and numeric ranges. Gold owns comparison
groups, target/price policy, eligibility and model-input preparation. Concrete
Silver structures and the SQLite source index are recorded with Bronze evidence
in the [plan](lifecycle/plan.md#standard-silver-v2-implementation-4-october-2026).
The current chocolate implementation uses Bronze (raw) →
combined Silver → immutable Parquet Gold for its training use case. Its Silver
builder owns source processing and persistent corrections. Standard Gold records
every candidate and a separately selected input population under its study
contract; historical Gold population behavior remains available. These
interfaces are specified in [data](data/spec.md#10-gold-and-the-finalized-training-basis)
and [model](model/spec.md#gold-training-admission-and-inferred-lightgbm-refit).

The [data preparation reassessment](data/intent.md#current-focus-meaningful-data-for-analysis)
is implemented in standard Silver v2 with a local pilot. Model planning remains
owned by the model specification. The application's historical synthetic price fixture retains its own
scope and target, as defined in the [app specification](app/spec.md#synthetic-product-price-demo).

## Status and maintenance

The [lifecycle plan](lifecycle/plan.md) records implementation, verification and
remaining work. [PROJECT.md](../PROJECT.md) describes capabilities and limitations;
the [hackathon brief](eat-hack-track-two.md) owns event requirements.
Follow the [documentation policy](documentation-policy.md) to update the owning
feature specification and affected guides when behavior changes. Shared contract
changes require updates to each affected feature. Author repository content
under [AGENTS.md](../AGENTS.md), preserving original source evidence verbatim.

The [UK cat litter collection](data/cat-litter-raw.md) uses the existing Bronze
archive contract. Its [data specification](data/spec.md#31-bronze-the-raw-data-layer)
and collection receipt record scope, storage and verification limits.
