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

The chocolate architecture remains Bronze (raw) → combined Silver → immutable Parquet
Gold. Silver owns source processing, review and eligibility decisions. Current
Gold admits every candidate while preserving source provenance; actual model
inputs and the selected target still determine numerical usability. These
interfaces are specified in [data](data/spec.md#10-gold-and-the-finalized-training-basis)
and [model](model/spec.md#gold-training-admission-and-inferred-lightgbm-refit).

The [data preparation reassessment](data/intent.md#current-focus-meaningful-data-for-analysis)
is proposed work. Its exclusion of model planning applies to that reassessment;
it does not replace the model specification or establish a new implemented data
contract. The application's historical synthetic price fixture retains its own
scope and target, as defined in the [app specification](app/spec.md#synthetic-product-price-demo).

## Status and maintenance

The [lifecycle plan](lifecycle/plan.md) records implementation, verification and
remaining work. [PROJECT.md](../PROJECT.md) describes capabilities and limitations;
the [hackathon brief](eat-hack-track-two.md) owns event requirements.
Follow the [documentation policy](documentation-policy.md) to update the owning
feature specification and affected guides when behavior changes. Shared contract
changes require updates to each affected feature. Author repository content
under [AGENTS.md](../AGENTS.md), preserving original source evidence verbatim.
