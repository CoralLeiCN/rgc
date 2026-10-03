# Category Processing Agent Plugin

This package targets the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-processing/SKILL.md](skills/category-processing/SKILL.md), in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation/discovery depend on the
client's format support.

The core uses Python 3.9+ and its standard library to process preserved
category/market archives with a versioned profile. It combines exact seller deduplication, stable
seller identity, typed schema/unit/vocabulary standardization, price/review
eligibility, a processing ledger and grouped artifacts for mapping review in one
silver dataset. The calling harness uses the skill and evidence batches to
prepare mapping changes; there is no external dispatcher or scheduler.

The package includes its engine, helpers for model preparation and pinned references
to chocolate/coffee contracts in the
[Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Category JSON payloads live in the dataset. The plugin verifies files against an
immutable commit revision, SHA-256 hashes and byte lengths. It runs independently
of repository sibling modules and other plugin installations. Copy the whole
package when moving it; run its CLI directly when native installation is unavailable.

```text
python3 <plugin-root>/cli.py process --archive-root <collections-root> --category chocolate --output <silver-root>
python3 <plugin-root>/cli.py process --archive-root <collections-root> --profile <custom-profile-folder> --output <silver-root>
python3 <plugin-root>/cli.py summarize --silver-root <silver-root> --output <summary-output>
python3 <plugin-root>/cli.py prepare-model --silver-root <silver-root> --output <model-preparation-root> --validation-fraction 0.2
```

Choose exactly one of `--category` and `--profile`. `--category chocolate` and
`--category coffee` resolve the corresponding
`profiles/<category>/dataset-contract.json` reference. `--profile` also accepts a
reference directory or a custom local directory containing the five contracts.
Cache misses download the pinned bytes. Each resolution verifies the cache,
including its reference marker; corrupt or inconsistent content fails explicitly.
Processing reads local archives.

The default cache is `<plugin-root>/.contract-cache`, excluded from Git. Select a
writable location with `--contracts-cache <cache-root>` when the installed plugin
permits no writes. Add `--offline` to require a verified populated cache and prohibit
downloads. A full custom profile without a dataset reference needs no network.
Silver outputs preserve the five exact contract files and record their hashes,
repository, immutable revision and reference fingerprint.

Read the skill's references for the
[processing/archive contract](skills/category-processing/references/processing-contract.md),
[profile configuration](skills/category-processing/references/profile-contract.md),
[mapping maintenance](skills/category-processing/references/mapping-maintenance.md), and
[model handoff](skills/category-processing/references/model-handoff.md).
Chocolate has a broad profile with 103 attributes and conservative source parsing;
coffee is a small starter for structured sources that demonstrates category
independence, with extraction limited to configured inputs.

Profile loading checks typed attributes, units, enum/list vocabularies and bounds
against the validator's supported template for nullable and known values, plus
category/market constants and selected predictor compatibility. Unsupported value
constraints fail explicitly; this runtime does not execute arbitrary JSON Schema.
Values valid for the category but outside a selected model domain remain in
silver, with candidate exclusion reasons rather than a failed build.

Raw discovery, original source/image retrieval and import remain collection
responsibilities. The category-research collection package can produce the
common raw archive consumed here; any compatible producer works. Review examples
and stable seller review keys are in the profile reference.

Run the bundled tests from the package root:

```text
python3 -B -m unittest discover -s tests -v
```

The bundled tests cover drift in typed contracts, exclusions from selected model
domains, reference/cache routing and execution of a copied plugin with isolated
Python. Prior verification passed coffee processing, review and model preparation,
real chocolate preservation/hash/repeated build checks and skill structure checks.
Category integration tests require a populated default cache or access to the
public dataset on their first run. Resolver unit tests use mocked downloads and
synthetic references without category payload fixtures. Native installation in
multiple harnesses remains unverified.

Dataset eligibility is separate from package correctness: unreviewed evidence and
unresolved price basis remain excluded. Current real chocolate has mapping gaps
and no eligible reviewed model inputs. Inspect generated reports rather than
treating successful processing as model readiness. No regression is fitted.
