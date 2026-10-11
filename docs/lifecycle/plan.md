# Implementation status

## Documentation storage, 11 October 2026

Research-specific documentation is preserved in ignored `docs/private/` storage.
Historical originals have a local preservation manifest with their checksums.
Dedicated research reports and proposal documents are removed from tracked
paths. Maintained public guides describe software behavior and interfaces rather
than collected populations, category inventories, measurements or study results.

Schema bodies and analytical definitions belong in the authoritative dataset.
Git retains immutable resolution manifests and checksums. Dataset caches and
local draft proposals remain ignored. This documentation migration does not
publish a schema release or rewrite repository history.

## Implemented workflow

The collection plugin preserves original records and immutable captures.
The processing plugin resolves dataset-owned contracts and supports Silver,
source identity, corrections and profiling. Gold prepares immutable model inputs.
Model tools validate selected contracts and actual inputs; the web application
loads verified artifacts and keeps drafts separate from observed data.

Standalone compatibility commands retain their documented interfaces. Source
retrieval, preprocessing, model fitting and publication are separate operations.
Passing integrity checks does not establish semantic correctness, exhaustive
coverage or model readiness.

## Verification

Run the locked environment and relevant pytest suites, Ruff, documentation checks
and whitespace checks. Verify contract caches offline when available. Check a
clean tracked-file export so ignored research documents cannot satisfy required
links accidentally. The local migration receipt records preservation checks,
exact changed files and test results without exposing research subjects in Git.
