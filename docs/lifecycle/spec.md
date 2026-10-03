# Project requirements and design

Status: maintained navigation view. [docs/spec.md](../spec.md) owns the project
contracts and acceptance requirements. [The silver guide](../chocolate-silver.md)
owns the canonical raw/silver workflow; [the schema guide](../chocolate-schema.md)
owns typed field meanings, review and pricing handoff with machine contracts.
The [portable processing guide](../category-processing.md) owns the standalone
plugin's category profiles, stable seller envelope, ledger/batches, maintenance
workflow and generic model-preparation entry points.

## Requirements

Preserve broad raw source evidence; combine exact within-seller deduplication
and versioned chocolate standardization inside one silver build without merging
different shops; retain explicit missingness, conflict, review, and provenance;
separate product
attributes from price observations; and keep candidate records distinct from
reviewed eligible model inputs. Track brand identity independently of seller
role, and emit brand, retail, and unknown partitions.

Training must use reviewed price/quantity/scope and identity decisions, a
declared comparison group and feature design, grouped held-out validation,
training-only preprocessing, support checks, and a documented missing-value
policy. Insights must state target units, references, conditional contrasts,
uncertainty, support, and limitations. No fitted model is implied by a dataset
build.

## Design and evidence boundaries

```text
raw collection -> silver (deduplication + standardization + reviews/gates)
                      -> reviewed eligible inputs -> later validated model
```

Silver verifies raw index/history consistency, retains canonical source groups
with unchanged captures and aliases, and applies the versioned profile,
source-mapping, product-schema and model-design files pinned by
`schemas/chocolate/dataset-contract.json`. The JSON bodies are authoritative in
the Hugging Face dataset and downloaded into ignored verified caches; Git keeps
only immutable revision/hash/version references and human documentation.
It preserves original source references and unknown claims for future extensions.
Separately persisted deduplicated and standardized datasets are not required.
The earlier cleanup and standalone component CLIs remain compatibility/diagnostic
helpers, described in their guides rather than additional canonical layers.

The portable package keeps raw/silver responsibilities while supplying all of its
runtime and five-contract dataset references without sibling imports. Processing records
capture and rules fingerprints and groups evidenced mapping gaps. The calling
harness proposes changes within the current task; profiles remain fixed per run,
and accepted changes create a new snapshot. Current execution rebuilds fully;
incremental caching, automatic dispatch and selective migrations remain future.
Native plugin installation across harnesses remains unverified. Chocolate's
portable seller envelope and generic targets use distinct versions from the
established chocolate CLI; no existing dataset or model is silently migrated.

The [canonical specification](../spec.md) defines release constraints and open
decisions. [Documentation policy](../documentation-policy.md) identifies the
documents that must be synchronized when any contract changes.

Next document: [Implementation plan](plan.md).
