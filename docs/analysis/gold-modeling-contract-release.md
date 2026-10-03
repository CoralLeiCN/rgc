# Published Gold/modeling contract release

Status: user-approved and published on 2026-10-03 at Hugging Face commit `d549ad91d63fb452af605df4a939c4e1f0a59bfa`. All 16 remote files were verified byte for byte, and all three Git references now pin that immutable revision.

Repository: `CoralLeiCN/rgc-collections`, branch `main`. Previous Git reference revision: `d4ebef3df5ac17145e8dbd2f8a7ae2b10c0afe70`. Revised publication parent: `db32e43635793a0edd1308df4bd0dee112ddbe44`. The exact parent and all upload payload hashes were guarded before publication. Published revision: `d549ad91d63fb452af605df4a939c4e1f0a59bfa`.

Prepared bundle manifest digest: `cf1091abf07e33660b4e03ca9b2bc4dbbdb04280ff82398846d251b12ac6b03d`. The complete 16-file payload is preserved locally in `data/contract-release/bundle` and the machine receipt is `data/contract-release/prepared-release.json`.

## Contract and behavior changes

- Chocolate schema stays `chocolate-schema-1`, 103 attributes. No fields, types, units, scopes or vocabulary labels are added or removed. The existing family/physical fields acquire the reviewed identity-mapping rule and metadata.
- Chocolate mapping advances `chocolate-source-mappings-1` → `chocolate-source-mappings-2`, declaring `chocolate-product-identity-1` and `chocolate-family-mappings-1`. Names/GTIN/seller-parent hints alone never establish exact consumer-pack equality.
- Chocolate design advances `chocolate-pricing-design-1` → `chocolate-pricing-design-3`: the fixed regular consumer target, implemented experimental OLS with family holdout and cluster bootstrap, 11 unchanged selected predictors, seller-role diagnostic context, and reviewed price-observation checks.
- Portable chocolate schema/mapping stay `chocolate-processing-schema-1` / `chocolate-source-mappings-1`. Design and recipe advance to `chocolate-processing-pricing-design-2` / `chocolate-processing-pipeline-2`.
- Coffee schema/mapping stay `coffee-schema-1` / `coffee-source-mappings-1`. Design and recipe advance to `coffee-pricing-design-2` / `coffee-processing-pipeline-2`.
- Every model target requires `regular-consumer-price-1`: regular, non-promotional, consumer-tax-inclusive price and reject fallback. Chocolate remains log GBP per 100g; other categories retain explicit currency/quantity normalization. Displayed offers, reference amounts, missing tax and guessed discount reversal cannot supply a target. Generated custom profiles retain this basis.

## Evidence and impact

Codex reviewed 31 named ranges and persisted 1,285 family-only assignments. Every assignment resolved to its preserved captured name; known counterexamples (Mackie's Dairy Milk and non-Cadbury mini eggs), ambiguous mixed ranges and Oreo-only names remain deferred. Reused unit GTINs appear on single bars, bulk packs and personalized gifts, so the seed asserts no exact physical identities.

The real rebuild retained 3,743 seller listings and 4,347 captures; the raw snapshot version and all retained original capture objects were unchanged. Family coverage changed from zero to 1,285 products and 402 of 2,134 pricing candidates (26 ranges among candidates); 2,458 product families remain unresolved. There were zero applied mapping conflicts or inactive assignments and 3,394 grouped family/physical review packets. All 2,134 candidate rows remain, with zero eligible model inputs: exact physical IDs, regular/tax evidence and other reviews are incomplete. No model fitted. Earlier immutable Silver/Gold/model snapshots remain unchanged.

The verified new reviewed Gold is `gold-a0da78d668e5e3a04172d3c2`, from Silver `silver-3434c1cb7c08d10f44330862`; readiness run `model-run-4ddc55390c3393b8f3dbea8a` did not fit. Original checks passed 306 cases before main integration. After reconciling main, all 375 pytest cases passed against verified local draft-contract fixtures in a disposable checkout; the checkout used test-only reference revisions, with the source references left on the actual published revision. Ruff, the documentation checker and whitespace checks passed. The updated CI workflow has not run here.

The combined-main rebuild with explicit prepared contracts completed as `silver-2e61c59362d10096186ef5b1`, preserving raw snapshot `raw-snapshot-70239771976a75a48c5d99db` and all 4,347 capture objects (aggregate SHA-256 `72c94755fa2b4b5bf555d93771fd813fd526cb72e2aa4d80308575df5af4b413`). Counts and family coverage match the previous rebuild. Pass-through Gold `gold-1342c4177a1b08c325f69f52` and user-reviewed Gold `gold-d9478bc242bc93a7ac0cb986` contain all 2,134 candidates and zero eligible inputs. Readiness run `model-run-aae002fdc9b5247b60d53902` recorded the expected lack of eligible observations and did not fit. These remain local data/model snapshots; only the analytical contracts and card were uploaded.

## Exact managed publication files

Published the exact 16 files below: 14 contract JSON files, `contracts/manifest.json` and the prepared `README.md`. The card updates only its analytical-contract section and preserves all other text. Remove no remote files. Raw indexes, evidence bundles, Silver exports and fitted-model releases are outside this contract-only upload. The revised card was generated from immutable parent `db32e43635793a0edd1308df4bd0dee112ddbe44`. Before publication, verify the parent and generated card still match this reviewed payload; verify the returned immutable commit byte for byte afterward.

| Managed file | SHA-256 | Bytes |
| --- | --- | --- |
| `contracts/chocolate/profile.json` | `881da5b79167bde7c8ac54dce76d39a3962cb5f73540e0e062c34dfde81e6458` | 65092 |
| `contracts/chocolate/source-mappings.json` | `5084dde12e3b2309f11b33e4a98226005bc6cb877531eb58510d17715f6f0128` | 18698 |
| `contracts/chocolate/product.schema.json` | `e61c8d202774a95250d40673f292f68fa743dbec3a6d0948beedcc58e8fec84c` | 327514 |
| `contracts/chocolate/model-design.json` | `5ab4317e10f0c7fd5598a99cf46c887c6c047db193b9a3d7d7cae016ab37092b` | 22850 |
| `contracts/category-processing/chocolate/profile.json` | `5c6a5cb67a8c598a87d50dc3094d7fe0c7337f952c7e175d7bf8285210305b3e` | 64785 |
| `contracts/category-processing/chocolate/source-mappings.json` | `a00d79f8227c44a703786c94eadb456d334e421b82b3ba4642ed788ddf609293` | 17051 |
| `contracts/category-processing/chocolate/product.schema.json` | `69d1aafa431add79029ced1e7908ea5f45a2396c4d8a90a35ff8155a0b314294` | 327390 |
| `contracts/category-processing/chocolate/model-design.json` | `31036183bf3b51f2292dee46efd44fcfa70289ce711d1fff4a533c7b818ed558` | 21030 |
| `contracts/category-processing/chocolate/pipeline.json` | `216876b1ba7857e19c8992e8de3b98279bdf277742236526a0b8ad9d6f07183a` | 4237 |
| `contracts/category-processing/coffee/profile.json` | `0c17fda56943b62973f44188223418a8828e6a7f43ca8d4fe0ffb1678251f4d3` | 5035 |
| `contracts/category-processing/coffee/source-mappings.json` | `ce174895499816635bc325b166216b19c50c3de123566c04c5040ab945613d89` | 1368 |
| `contracts/category-processing/coffee/product.schema.json` | `68f82ab86f8d18207c6b5757872a6beb88603aa44edc0d69f557577f0364d1b1` | 43486 |
| `contracts/category-processing/coffee/model-design.json` | `72732366ce62120f40f0ec3a5584dd5166657a53c90e20603fe3b50854c68ec7` | 3612 |
| `contracts/category-processing/coffee/pipeline.json` | `829b4cfb642d0bf7ce3798a8131c13f9229e28b1ad3aea3c8c7e926bbed66818` | 1959 |
| `contracts/manifest.json` | `926b8281fed9586188163c6d814c9bfc3fef60fba266d54abf13d1446b0d3043` | 4684 |
| `README.md` | `454e3608c88c4d7512c49b2217a2890ee666fdc51debf164985dc8040c0b4e9b` | 5205 |

Publication verified every uploaded byte and updated the three Git reference manifests with the returned immutable revision and exact hashes. All three caches were materialized for final offline verification and behavioral checks before the Git squash commit.

The approval requirement comes from the [accepted maintenance decision](../decisions/agent-led-schema-maintenance.md): present the completed release and wait for authorization of the specific Hugging Face commit. Local evidence decisions and implementation are already authorized.

## Publication parent refresh on 2026-10-03

Before uploading, the strict parent guard found two intervening remote commits: `c1725ff8bbeef8f78c7182fd67af5bde75ef65ef` published a pandas Silver snapshot, and `db32e43635793a0edd1308df4bd0dee112ddbe44` published schema coverage and verification reports. All 15 analytical contract/index files match the originally reviewed parent. The revised card is identical to the new parent card and preserves its new Chocolate silver and Chocolate schema analysis sections (1,995 additional bytes). All 14 prepared contract bodies and their index remain exactly as originally reviewed. The proposed 16-file upload has no removals and preserves all intervening Silver and analysis files.

Automatic approval review initially rejected the refreshed-parent upload because its exact card payload and parent differed from the earlier review. The user explicitly approved the updated release, after which the guarded upload succeeded. All uploaded bytes were verified and Git references updated. The remote commit preserves the intervening Silver snapshot and analysis reports.

## Final published-reference verification

All three caches passed offline verification. The actual repository pytest suite passed all 375 cases against the published immutable references in 8.04 seconds. Ruff, full documentation/change-coverage checks and whitespace checks passed. The GitHub workflow has not run here. Local main is landed as one squash commit with the same file tree as the task branch; no Git push is part of this request.
