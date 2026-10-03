# Category Research Agent Plugin

This package targets the [Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification).
Its discoverable component is
[skills/category-research/SKILL.md](skills/category-research/SKILL.md), in the
[Agent Skills format](https://agentskills.io/specification). The manifest uses
the official versioned schema. Client installation and discovery depend on the
client's support for this format; native compatibility with particular harnesses
has not been demonstrated.

The core uses Python 3.9+ and its standard library to preserve supplied product
records and original source/image bytes independently of an analytical taxonomy.
The skill, CLI and Python API are bundled under this plugin root. Other plugins
can read the skill, call the CLI or import `category_research.import_document`
directly. Execution needs no server, package installation or global installation.

```text
python3 <plugin-root>/cli.py import --input <collection.json> --output <archive-root> --download-images --workers 4
```

Read the [import contract](skills/category-research/references/import-contract.md)
for input fields, local source/catalog preservation, API usage, transfer options,
and archive/report semantics. Products can be supplemented by subsequent imports:
raw artifacts and capture history remain immutable while `product.json` retains
every capture in its current index. Network transfer failures and missing
ingredient fields remain visible.

Collection preserves raw archives for later processing. The separate
category-processing package provides its own CLI and skill and consumes the
[archive format](skills/category-research/references/import-contract.md)
to build silver data with distinct seller rows, apply category profiles, summarize
mapping gaps and prepare reviewed model inputs. It runs independently of this
collection package's installation. Regression fitting belongs to later modeling.

Run the behavioral tests from the package root:

```text
python3 -B -m unittest discover -s tests -v
```

From the repository root, use `plugins/category-research/tests` for `-s`.
