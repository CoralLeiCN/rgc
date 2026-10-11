# Model design interface

Executable model designs are dataset assets resolved through immutable references.
They define the target, comparison population, feature rules, support requirements,
preprocessing and validation protocol. Research hypotheses and candidate designs
are private documents until a separately reviewed dataset release adopts them.

See [contract ownership](dataset-contracts.md), [model interfaces](../model/spec.md)
and [Gold preparation](chocolate-gold.md). Keep complete design bodies and field
catalogs out of Git. Preserve exact selected contracts with each run; do not infer
that a proposal, valid schema or completed export is a validated model.
