# Portable category processing

The [standalone package](../../plugins/category-processing/README.md) transforms
preserved captures using verified dataset-owned contracts. Its
[skill](../../plugins/category-processing/skills/category-processing/SKILL.md)
owns orchestration; source documents remain untrusted evidence.

## Layers and contracts

Silver owns persistent source IDs, standardization, corrections and profiling.
Gold owns study-specific populations, targets, features and preparation. Keep
price, brand, source identity and metadata separate from typed analytical facts.
Known, unknown, conflict and not-applicable states remain distinct.

Contract manifests select immutable dataset files. Standard Silver can use its
four field contracts without a model design; Gold resolves a selected design
separately. Historical five-file profiles retain their compatibility interface.
Verify every cached file that is present. Full field definitions and aliases
belong in the dataset, not in this guide.

```sh
python3 -B scripts/fetch_contracts.py --all
python3 -B scripts/fetch_contracts.py --all --offline
python3 -B plugins/category-processing/cli.py --help
```

Use explicit archive, profile/cache and output locations. Resolve command options
from the CLI. Preserve snapshot contracts and stable seller identities; new data
or changed contracts create another immutable result.

## Review and maintenance

Inventory the complete authorized corpus. Process in batches as needed while
keeping contracts fixed within each run. Agent assertions remain inferred;
persistent human corrections retain their separate review provenance. Changed
captures invalidate unsupported assumptions about earlier assertions.

Research new meanings from original evidence and counterexamples. Record
accept/reject/defer decisions privately, align changed contracts and validate
before a dataset release. Separate initial schema research, executable processing
and downstream model design. A successful build does not establish model readiness.

Refer to the package's [processing contract](../../plugins/category-processing/skills/category-processing/references/processing-contract.md)
and [standard Silver reference](../../plugins/category-processing/skills/category-processing/references/standard-silver.md)
for supported inputs, outputs, history and review behavior. Keep the package usable
independently of this repository.

## Loader compatibility versions

These identifiers document resolver compatibility; the manifests own exact pins and file hashes.

- `plugins/category-processing/profiles/chocolate/dataset-contract.json`: `chocolate-processing-schema-1`, `chocolate-source-mappings-1`, `chocolate-processing-pricing-design-2`, `chocolate-processing-pipeline-2`.
- `plugins/category-processing/profiles/coffee/dataset-contract.json`: `coffee-schema-1`, `coffee-source-mappings-1`, `coffee-pricing-design-2`, `coffee-processing-pipeline-2`.
- `plugins/category-processing/profiles/chocolate/silver-dataset-contract.json`: `chocolate-processing-schema-1.silver-2`, `chocolate-source-mappings-1.silver-2`, `chocolate-processing-pipeline-2.silver-2`.
- `plugins/category-processing/profiles/coffee/silver-dataset-contract.json`: `coffee-schema-1.silver-2`, `coffee-source-mappings-1.silver-2`, `coffee-processing-pipeline-2.silver-2`.
- `plugins/category-processing/profiles/coffee/gold-dataset-contract.json`: `coffee-schema-1.silver-2`, `coffee-source-mappings-1.silver-2`, `coffee-pricing-design-2.silver-2`.
