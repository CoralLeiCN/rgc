# Standard Silver v2 implementation and published contract release

Recorded 4 October 2026. Status: implemented, validated and published after the
user approved the reviewed release. Publication follows the
[publication decision](../../decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit).
The [plan](../../lifecycle/plan.md#standard-silver-v2-implementation-4-october-2026)
records the chosen structures. The
[portable reference](../../../plugins/category-processing/skills/category-processing/references/standard-silver.md)
owns the executable interface.

Published commit:
[`337fb7f3984ac648e67edd2cb47802f056193efc`](https://huggingface.co/datasets/CoralLeiCN/rgc-collections/commit/337fb7f3984ac648e67edd2cb47802f056193efc),
parent `88b08aeada37e228fcd80334b5abddd768da6968`. All ten published files match
the reviewed bytes and hashes below. The commit adds those files only. Four new
Git manifests pin the separate Silver and Gold contracts; default builds use
these pins. Historical references and local pilot snapshots retain their identities.

Publication validation: all eight current/historical contract references loaded
from an empty cache; **649 tests passed, 7 skipped** after the loader updates.
Ruff and documentation checks passed. A build using the published pins produced
Silver `silver-4371b65f54cccd794a8a9888` and Gold
`gold-60876b0d1542f7fa9d55939a`, preserving the reviewed products, source IDs,
facts and profiling statistics. Fact storage order follows the published catalog;
all 5,358 rows agree as a multiset. The updated OLS run retains the same readiness
blockers. These validation outputs are local and do not replace published data.

## Alignment and behavior

The default chocolate builder and portable `process` now produce standard Silver
without requiring a model design. Gold owns comparison rules, target policy,
predictor selection, family relationships for the study and eligibility. The
historical APIs and `--legacy` retain their original contracts and price bases.

SQLite assigns persistent source subject IDs and aliases. Logical exports support
recovery. Source product/variant identity preserves established seller UIDs;
missing identity creates a review issue. Source-keyed child collections survive
reordering. No seller rows are merged across sellers.

Effective facts preserve scope, qualifier, measurement basis, evidence references
and extraction method. Human corrections have durable revisions, prior values,
reviewer/reason and applicability checks; stale writes are rejected. The local
review page displays original evidence and history. Saved decisions affect a
subsequent immutable rebuild. An agent's submitted inference cannot label itself
as a human review.

Each build manages JSON/Markdown schema reports and a dictionary. Reports include
every schema field, current and historical populations, source/context partitions,
method/state counts, categorical distinct values and complete frequencies,
member-wise list frequencies, and numeric min/max/quartiles/median. Missing
values remain in denominators; zero and false remain valid. The report identifies
the exact Bronze, schema, mappings, implementation and effective corrections.

Canonical Gold freezes candidate and selected-input Parquet tables and verifies
their derivation from copied Silver. OLS consumes the selected population,
retains the separate eligibility audit, copies the original Silver quality
report and records the study's price assumptions. Historical estimator adapters
retain their documented support; this change does not establish a migrated
interface for every experimental trainer.

## Contract changes

The portable chocolate catalog is the shared field source for the default
canonical and portable Silver paths. Its prior revision is
`d549ad91d63fb452af605df4a939c4e1f0a59bfa`. The current chocolate Gold study design
is derived separately from `d743cb8dbca37f5241cccd444a16165523304f6c`.

| Contract | Previous version | Prepared version |
| --- | --- | --- |
| Chocolate profile | `chocolate-processing-schema-1` | `chocolate-processing-schema-1.silver-2` |
| Chocolate mappings | `chocolate-source-mappings-1` | `chocolate-source-mappings-1.silver-2` |
| Chocolate validator | Same schema version as profile | Same prepared schema; `category-silver-record-2` |
| Chocolate recipe | `chocolate-processing-pipeline-2` | `chocolate-processing-pipeline-2.silver-2` |
| Selected chocolate Gold design | `chocolate-pricing-current-price-design-1` | `chocolate-pricing-current-price-design-1.silver-2` |
| Coffee profile | `coffee-schema-1` | `coffee-schema-1.silver-2` |
| Coffee mappings | `coffee-source-mappings-1` | `coffee-source-mappings-1.silver-2` |
| Coffee validator | Same schema version as profile | Same prepared schema; `category-silver-record-2` |
| Coffee recipe | `coffee-processing-pipeline-2` | `coffee-processing-pipeline-2.silver-2` |
| Selected coffee Gold design | `coffee-pricing-design-2` | `coffee-pricing-design-2.silver-2` |

The chocolate catalog retains 103 fields and coffee retains 12. No catalog fields,
declared value types, units, scopes or vocabularies are added or removed. Every
field receives a snake_case output column. Model roles/transforms leave the Silver
catalog. The 103 chocolate qualifier descriptions remain verbatim under
`qualifier_rule`; actual qualifiers are fact contexts. Nine nutrition fields with
`per_100g` in their names receive an explicit `per_100g` basis. The validator now
describes typed scalar/list values, null, tagged error/uncertainty states and the
source/method/context columns. Alias mappings retain their definitions.

Silver recipes retain source price extraction while dropping target policy,
legacy target aliases and automatic comparison-group derivation. The current
chocolate Gold design keeps the same predictor set and
`current-consumer-price-1`: displayed prices serve as the regular-price proxy,
without a separate regular-price, promotion or confirmed-tax gate. Promotion,
membership, tax and observation-date uncertainty remains explicit. Coffee keeps
`regular-consumer-price-1`, its original predictors and regular-unit-price target
names; its new design is a separate Gold contract. Neither contract fits a model.

## Evidence and pilot comparison

The convenience sample copies two sorted listings from each of 24 chocolate
source folders: 48 seller listings, 52 captures and 100 managed original JSON
files. It includes retailer sections and Shopify product/variant payloads.
All 100 managed files match the original local archive byte-for-byte. The 48
source subject IDs and raw-input manifest are unchanged across the comparison.

The baseline is the first local v2 build before the pack-mass fixes, not the
published corpus: `silver-2d51a2f97da5007db4c91f34`. The final build is
`silver-0544ad1af117ffb2685b7ec0`. Both preserve earlier captures; historical
coverage below includes those captures rather than only the current records.

| Measure | Baseline | Final |
| --- | ---: | ---: |
| Source listings / captures | 48 / 52 | 48 / 52 |
| Effective contextual facts | 5,358 | 5,358 |
| Current available field/context cells | 310 | 325 |
| Fields with a current available value | 20 / 103 | 21 / 103 |
| Historical available field/context cells | 322 | 337 |
| Conflict review issues | 19 | 17 |
| Rejected mass candidates retained for review | 0 | 17 |
| Missing external source identity issues | 4 | 4 |
| Total review issues | 23 | 38 |
| Unmapped source fields | 13 | 13 |
| Gold candidates / eligible inputs | 48 / 0 | 48 / 0 |
| Gold unresolved edible-mass predictor | 24 | 23 |
| Gold unresolved price or quantity | 35 | 34 |

The larger review queue exposes previously accepted bare gram statements. Moo
Free body HTML contains nutrition-table gram cells, which cannot establish edible
pack mass. The parser now requires explicit weight context and retains rejected
candidates and their evidence. Source names establish identical-unit arithmetic:

| Source text | Baseline pack mass | Final pack mass |
| --- | --- | ---: |
| Cadbury `Dairy Milk Jelly Popping Candy Bar 160g (Box of 19)` | 160 g | 3,040 g |
| Cadbury `Dairy Milk Advent Calendar 90g (Box of 12)` | 90 g | 1,080 g |
| Moo Free `Baking Dairy Free & Vegan Milk Chocolate Baking Drops (100g) — 2 X Bags` | Conflict | 200 g |
| Moo Free `Baking Dairy Free & Vegan Milk Chocolate Baking Drops (100g) — Case of 10 X Bags` | Conflict | 1,000 g |
| Nomo `Salted Popcorn Chocolate Bars — 32g / 24 Bars` | Missing | 768 g |
| Nomo `Salted Popcorn Chocolate Bars — 32g / 12 Bars` | Missing | 384 g |

Minimum cocoa declarations and differently scoped source statements remain
distinct. The Ocado Lindt 99% product also contains a 90% marketing statement;
the pipeline preserves the competing evidence instead of selecting a convenient
number. No component identity is guessed from prose. These counterexamples
remain part of the review evidence and limitations.

Final Gold is `gold-9b8faf252473d83482ce441a`. Its report records 48 unresolved
family assignments, 48 unresolved cocoa predictors under the default semantic
selector, 27 unresolved availability values and 22 unresolved source observation
times, alongside other field gaps. Current contextual Silver facts remain usable
even when a particular Gold selector cannot choose an unconditional value.

The real pilot OLS run `model-run-cfdd4544e568e74488fb16d5` returns unavailable
with `no_gold_observations_in_group` and
`fewer_than_two_reviewed_families_in_group`. It does not report an incomplete
Silver snapshot or produce fitted coefficients. A separate synthetic coffee
fixture produces one eligible Gold row at GBP 2.60 per 100 g under its retained
regular-price contract; this is fixture validation, not a coffee corpus study.

## Verification

Behavioral tests cover source alias/archive relocation stability, distinct
sellers, component reordering, errors, zero/false/null, method precedence,
same-context conflicts, correction replay, evidence changes, stale-write
rejection, index/history recovery, report calculations, immutable integrity,
model-free authoring, offline four-file contracts and isolated portable copies.
Gold tests verify target arithmetic, Parquet tamper rejection, study contract
reloads and OLS handoff with both eligible and excluded rows.

The standalone pandas report regenerated byte-for-byte. All 5,300 field/source/
context/population report partitions reconcile state, method and joint counts
to their denominators. The local browser review page was inspected with real
pilot evidence and empty correction history; correction persistence and
revision checks are exercised with synthetic tests, without recording a human
decision on the real pilot.

Validation uses the locked development environment, the complete pytest suite,
Ruff, the documentation checker, offline verification of all four pinned caches
and `git diff --check`. Final test results are recorded in the lifecycle plan.

The pilot does not establish full-corpus extraction accuracy. Most catalog
fields lack observed values in this sample. Image extraction, field evaluation,
full-corpus rebuild and migration of historical human decisions require further
work. Existing family registries require explicit mapping to the new Gold
relationship evidence contract. Published datasets, consumer pins and previous
training snapshots remain unchanged.

## Published release and exact files

Release: `standard-silver-2-2026-10-04` in dataset
`CoralLeiCN/rgc-collections`, target branch `main`, immutable revision
`337fb7f3984ac648e67edd2cb47802f056193efc`.
The release adds ten versioned contract files, replaces zero and removes zero.
Pilot datasets and original raw evidence are local verification artifacts and
were excluded from this upload. New v2 manifest references select the publication
while preserving the historical compatibility pins.

The prepared directory is `data/silver-alignment-pilot/release-final/`.
Its `release-index.json` SHA-256 is
`41bd0b11e08524261cf7f7bd9ae648e597a84e461f35b1a4d0b484888da73e9c`.
Paths below are relative to the dataset root and prepared directory.

| Published file | Bytes | SHA-256 |
| --- | ---: | --- |
| `contracts/category-processing/chocolate/silver-2/pipeline.json` | 3916 | `37bca2da45d20ef8409ee8fe4cfce252c7f2d529591c5c80103d35122088ae77` |
| `contracts/category-processing/chocolate/silver-2/product.schema.json` | 120612 | `3bd87aa6b14955253b96a1db4a37c6edc29f4491feb2b9e97e77da0b0fbd0f57` |
| `contracts/category-processing/chocolate/silver-2/profile.json` | 61850 | `8309432c5a5280547f9f897b235c731280af8d57dfa0825a124bf01876cea9b8` |
| `contracts/category-processing/chocolate/silver-2/source-mappings.json` | 17116 | `40ad336a6158c7828de958bea3c753268d8cdf7d6ead906b3e8afa0859045068` |
| `contracts/category-processing/coffee/gold-silver-2/model-design.json` | 3996 | `fd00c245e1cd488779fa94822ec20e5701b1cde7a629cb9573e2c0f877657eed` |
| `contracts/category-processing/coffee/silver-2/pipeline.json` | 1750 | `294b98f44536a6e45db00d950dd96584aeb3859609d52b1b93f03397b7cff48e` |
| `contracts/category-processing/coffee/silver-2/product.schema.json` | 13406 | `d16355f2dbc056f545db4f25a524ca7610d11075faa2e444216dc5c494e982ac` |
| `contracts/category-processing/coffee/silver-2/profile.json` | 5876 | `809d4d64be81c8b9c2bef080da7f73e36604e3c9741fde0824b3707f363b1fbd` |
| `contracts/category-processing/coffee/silver-2/source-mappings.json` | 1386 | `8aadfa54dfeef99e8048c37e8bbbbf072f069d8ba6e705bf481932696d7f5901` |
| `contracts/chocolate-current-price/silver-2/model-design.json` | 23157 | `29a452442ae00b807dd75303b60da1cc0a094215de7b4990c84ed5ef58fa1271` |

Local Silver manifest SHA-256:
`68d1943ff94789d2b3b5d5e77b0776ab3d303ca6b908382e589b9d02b3518f6b`.
Local Gold manifest SHA-256:
`222d5529b6240b31ae8b95dcff38dee1206e5e8db63f3d67812195e5ba66fe26`.
Schema profile SHA-256:
`d117a8f9dbbb9d9e71d8f95f4af1766d8b6f1b50308b279beeec7853a2decc4a`.
