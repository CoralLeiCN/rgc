# Category Research Agent Plugin

This package targets the [Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-research/SKILL.md](skills/category-research/SKILL.md), in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation and discovery depend on the
client's support for this format; native compatibility with particular harnesses
has not been demonstrated.

The standard-library Python core preserves supplied product records and original
source/image bytes. It can be invoked by another plugin through the CLI or
`category_research.import_document`. It has no dependency on a particular category
taxonomy and does not fit a model. Python 3.9 or later is required; no package or
global installation is needed.

```text
python3 <plugin-root>/cli.py import --input <collection.json> --output <archive-root> --download-images --workers 4
```

Read the [import contract](skills/category-research/references/import-contract.md)
for input fields, local source/catalog preservation, API usage, transfer options,
and archive/report semantics. Products can be supplemented by subsequent imports:
raw artifacts and capture history remain immutable while `product.json` retains
every capture in its current index. Network transfer failures and missing
ingredient fields remain visible.

The skill, CLI, and Python API are bundled under this plugin root. Other plugins
can read its skill, call its script, or import the core directly without a server.

Collection and post-collection processing are separate responsibilities. The
standalone category-processing package consumes this preserved archive format to
build seller-specific silver data, apply category profiles, summarize mapping
gaps and prepare reviewed model inputs. It does not need this collection package
installed, and collection does not require a complete analytical taxonomy.
Within this repository, see [portable processing](../../docs/category-processing.md)
for composition and the processing package's self-contained CLI/skill.

Run the behavioral tests from the repository root:

```text
python3 -B -m unittest discover -s plugins/category-research/tests -v
```
