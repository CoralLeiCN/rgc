# Model handoff

Use a complete silver snapshot and eligible reviewed `model-inputs.jsonl`:

```text
python3 <plugin-root>/cli.py prepare-model --silver-root <silver-root> --output <preparation-root> --validation-fraction 0.2
```

Generic targets are `regular_unit_price` and `log_regular_unit_price`;
`target_definition` saves category, market, currency, quantity attribute, unit and
base quantity. Chocolate and the coffee starter use regular GBP/100 g; another
category must deliberately define its comparable price basis. Chocolate may
also expose compatible GBP/100 g aliases.

The command verifies hashes, complete-snapshot status and candidate contracts.
Eligibility requires reviewed scope, physical/family identity, price/quantity
basis and selected predictors with observation-consistent capture evidence.
Unknown/conflicting/unreviewed active fields are rejected. The tracking catalog
is broader than the selected predictors.

Families stay together across sellers. Deterministic splitting needs at least
two eligible families. Only training rows define vocabularies, reference levels,
numeric domains and constant-term removal. Bundled designs use training-mode
references with deterministic ties, reject missingness, and do not impute, scale
or center. Frozen validation rejects unseen levels/out-of-range values rather
than refitting or extending support. Investigate those failures explicitly.

| Output | Meaning |
| --- | --- |
| `train.jsonl`, `validation.jsonl` | Reviewed observations partitioned by family. |
| `encoder.json` | `category-processing-encoder-1`, frozen columns/references/domains, support, training IDs and target/version context. |
| `design-matrix.jsonl` | Partition, observation ID, encoded X and log-price y. |
| `model-design.json` | Exact source design. |
| `preparation-report.json` | `category-model-preparation-1`, source versions, split, columns, dropped terms, hashes and limitations. |

No regression is fitted. Reports retain `regression_fitted: false` and
`release_ready: false`; zero eligible rows fails instead of fabricating an
encoder or prediction. Helpers validate, split, encode and compute conditional
contrast arithmetic. They do not establish sufficient samples, identifiable
brand/seller effects, coefficients or uncertainty.

For a later reviewed log-price model, `coefficient_percent(beta, delta)` computes
`100 * (exp(beta * delta) - 1)`. Prediction contrasts exponentiate fitted log
predictions into conditional median prices on the saved target basis; they do
not automatically estimate conditional means. Report units, feature/reference
changes, held-fixed context, support, fitted uncertainty and limitations.
Interpret conditional associations without causal premium claims. New-product
price testing and value-for-money scoring require later validation/release
decisions. Mapping changes never rewrite an old model's training snapshot.
