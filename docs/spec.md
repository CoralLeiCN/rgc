# Feature specifications

| Feature | Intention | Interface |
| --- | --- | --- |
| Data | [Goals](data/intent.md) | [Collection and preparation](data/spec.md) |
| Model | [Goals](model/intent.md) | [Inputs, validation and release](model/spec.md) |
| App | [Goals](app/intent.md) | [Evidence, drafts and prediction](app/spec.md) |

Bronze preserves original evidence, Silver standardizes facts with persistent
source identity, and Gold prepares a selected downstream use case. Models verify
actual inputs and a fixed design; the app consumes immutable artifacts and keeps
drafts separate from observations.

The [documentation policy](documentation-policy.md) defines public implementation
guidance and private research storage. The [plan](lifecycle/plan.md) records
software status without disclosing researched inventories. Dataset manifests
own exact contract versions and file hashes.
