# Category Processing Agent Plugin

This self-contained package targets the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-processing/SKILL.md](skills/category-processing/SKILL.md), in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation/discovery depend on the
client's format support; native execution in multiple harnesses is unverified.

The standard-library Python 3.9+ core accepts preserved raw category/market
archives and a versioned profile. It combines exact seller deduplication, stable
seller identity, typed schema/unit/vocabulary standardization, price/review
eligibility, a processing ledger and grouped mapping-review artifacts in one
silver dataset. The calling harness uses the skill and evidence batches to
prepare mapping changes; there is no external dispatcher or scheduler.

The package includes its engine, model-preparation helpers and chocolate/coffee
profiles. It does not import repository sibling modules, require another plugin
installation or fit a regression. Copy the whole package when moving it; run its
CLI directly when native plugin installation is unavailable.

```text
python3 <plugin-root>/cli.py process --archive-root <collections-root> --profile <plugin-root>/profiles/chocolate --output <silver-root>
python3 <plugin-root>/cli.py summarize --silver-root <silver-root> --output <summary-output>
python3 <plugin-root>/cli.py prepare-model --silver-root <silver-root> --output <model-preparation-root> --validation-fraction 0.2
```

Read the skill's references for the
[processing/archive contract](skills/category-processing/references/processing-contract.md),
[profile configuration](skills/category-processing/references/profile-contract.md),
[mapping maintenance](skills/category-processing/references/mapping-maintenance.md), and
[model handoff](skills/category-processing/references/model-handoff.md).
Chocolate has a broad 103-attribute profile and conservative source parsing;
coffee is a small structured-source starter demonstrating category independence,
rather than complete coffee extraction or a fitted coffee model.

Profile loading checks typed attributes, units, enum/list vocabularies and bounds
against the validator's supported nullable/known-value template, plus category/
market constants and selected predictor compatibility. Unsupported value
constraints fail explicitly; this runtime does not execute arbitrary JSON Schema.
Values valid for the category but outside a selected model domain remain in
silver, with candidate exclusion reasons rather than a failed build.

Raw discovery, original source/image retrieval and import remain collection
responsibilities. The category-research collection package can produce the
common raw archive consumed here; any compatible producer works. There is no
runtime dependency on that package. Review examples and stable seller review
keys are in the profile reference.

Run the bundled tests from the package root:

```text
python3 -B -m unittest discover -s tests -v
```

All 64 bundled tests pass, including typed-contract drift and selected-model
domain exclusion checks. A copied package ran with isolated Python without
repository sibling modules; independent coffee processing/review/model-preparation
and real chocolate preservation/hash/repeated-build checks passed. Skill structure
validation passed. These checks establish package behavior; native installation
in multiple harnesses remains unverified.

Dataset eligibility is separate from package correctness: unreviewed evidence and
unresolved price basis remain excluded. Current real chocolate has mapping gaps
and no eligible reviewed model inputs. Inspect generated reports rather than
treating successful processing as model readiness. No regression is fitted.
