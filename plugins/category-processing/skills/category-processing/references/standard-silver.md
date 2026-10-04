# Standard Silver v2

`process` builds `category-silver-manifest-2` snapshots. `--legacy` explicitly
selects the historical five-contract engine. Standard Silver requires
`profile.json`, `source-mappings.json`, `product.schema.json` and `pipeline.json`.
It does not read a model design or produce target, eligibility or training tables.
Packaged `profiles/<category>/silver-dataset-contract.json` references pin the four
published field contracts at `337fb7f3984ac648e67edd2cb47802f056193efc`. Explicit
historical inputs support deterministic migration. Input hashes and the four
effective contract copies are retained. The historical `dataset-contract.json`
still serves `--legacy`; coffee's separate Gold design has
`profiles/coffee/gold-dataset-contract.json`.
New contract publication requires the release review described in
[mapping maintenance](mapping-maintenance.md).

## Build and inspect

```text
python3 <plugin-root>/cli.py process --archive-root <collections> --category chocolate --offline --output <silver> --state-db <state>/sources.sqlite
python3 <plugin-root>/cli.py review --silver-root <silver> --state-db <state>/sources.sqlite --archive-root <collections>
python3 <plugin-root>/cli.py restore-state --silver-root <snapshot> --state-db <recovered>/sources.sqlite
python3 <plugin-root>/cli.py export-silver-contracts --profile <existing-profile> --output <new-release-folder>
```

The result returns its immutable `output` directory. `<silver>/latest.json`
points to that directory. Repeated identical inputs produce the same snapshot;
changed inputs create a new one. State must live outside Bronze, contracts and
snapshot directories. Preserve its SQLite database; `source-index.json` and
`corrections.jsonl` allow recovery from a verified generated snapshot. No source
capture is edited. The review server binds only to `127.0.0.1`, defaults to port
8765, and requires a session token for writes.

`source_index.py` assigns seller IDs from category, market, source key, host,
source product ID and nullable variant ID. Existing portable `seller_uid` values
are preserved. Legacy listing IDs are aliases. Missing external identity uses
the archive record ID and produces a review issue; names cannot establish a
match. An archive relocation preserving relative records retains IDs. A renamed
unresolved record needs an explicit alias assignment in the index. Distinct
sellers and variants remain distinct. Children use parent ID and declared source
keys. Capture and source-price identities remain separate from listing identity.

## Field and evidence contract

`products.jsonl` contains current subjects. A listing also has a `children` array
of current component objects. Each subject has a stable `subject_id`, parent
`listing_id`, `subject_kind`, source and capture identity. Catalog keys map to
snake_case columns, by replacing dots with underscores or an explicit `column`.
For example, `quantity.total_edible_weight_g` maps to
`quantity_total_edible_weight_g`. Canonical units remain in the catalog.

Every field has a typed value, `<column>.source`, `<column>.method` and
`<column>.contexts`. Missing values are plain null; nonmissing states are objects
with exactly one key, for example `{"state":"parse_error"}`. States are
`parse_error`, `inference_error`, `unresolved`, `conflict`, `not_applicable`.
Methods are `parsed`, `inferred`, `reviewed`, or null when no result was produced.
No per-value conversion formula is stored. Field and mapping contracts own rules.

A source array retains each supporting reference:

```json
[{"bronze_path":"chocolate/uk/products/shop/item/history/capture.json",
  "capture_id":"capture", "capture_sha256":"canonical-capture-digest",
  "pointer":"/raw_record/information/net_weight"}]
```

The digest is SHA-256 of the capture serialized with the package's canonical
`json_bytes`, not the file's original whitespace. `raw-inputs.json` additionally
pins original file byte hashes. Pointers locate original values; absent fields
have no fabricated pointer. Assertions retain original candidate values,
evidence content and parser diagnostics.

`facts.jsonl` stores effective results by subject, capture, field and semantic
`context` (`scope`, `qualifier`, `basis`). `is_current` distinguishes the latest
observation from history. Minimum and exact declarations stay separate. Multiple
contexts yield an `unresolved` flat projection; each context remains usable
through its own fact. Incompatible available results at the same priority and
context produce `conflict`. Applicable human decisions supersede parsing,
which supersedes inference. Failed attempts remain diagnostics and cannot
suppress a usable lower-priority result. `--inferences` accepts an assertion
array with subject ID, capture ID, attribute, value, pointer and optional scope,
qualifier/basis; supplied method labels cannot grant human review status.

Recipes may declare `collections` with `name`, capture-root `pointer`, relative
`id_pointer` and relative field pointers. Duplicate or missing child keys create
issues; array positions never identify children. `string_list` defaults to set
semantics. `list_semantics: ordered` preserves order and repeated members.
Automatic chocolate component discovery from arbitrary prose is not provided.

## Corrections

The local interface shows current facts, candidates, raw evidence and correction
history. Confirm or edit a JSON value, provide supporting references, reviewer
and reason, then save. Missing values can be confirmed as null. Supporting
references for a previously missing value must come from this subject's current
evidence. Save errors remain visible without erasing edits. Saving records a
human decision; rebuilding applies it to a new snapshot and regenerates reports.

`save-correction --silver-root <snapshot> --state-db <db> --input <decision.json>`
provides the same operation for explicit human decisions. The input contains
`subject_id`, `field`, `context`, `result`, `reviewer`, `reason` and
`expected_previous` (null initially, then the previous correction ID). Optional
`source` selects supporting references. The service records prior automated and
accepted results, source evidence, field-meaning/evidence hashes, time and
superseded revision. Concurrent stale writes fail. Definition/evidence changes
retain the decision and raise `stale_correction`; parser-only changes preserve
applicable decisions. Child evidence uses relative field pointers for applicability,
so array reordering preserves corrections. The exported history provides reusable
regression examples; no automatic model training or remote dispatch occurs.

## Profiles and quality

Every build manages `schema-profile.json`, `schema-profile.md`,
`data-dictionary.json`, `quality-report.json`, `review-queue.jsonl`,
`discovered-fields.jsonl`, all assertions, source aliases and raw input hashes.
The standard library implements portable aggregation. The canonical chocolate
command uses pandas quantiles with the same linear interpolation semantics.

Reports include every catalog field, current subjects and observation history,
source and semantic-context partitions, and schema groups. Each partition states
its denominator. Available count plus missing/error/state counts equals N;
not_applicable remains in N. Empty denominators produce null coverage. Methods
and method/state cross counts are separate. Categorical lists count each member
once per subject, retain complete frequencies and list unused vocabulary values.
Exact text repetition is reported separately. Numeric summaries preserve finite
zero values and report minimum, maximum, quartiles and median, with source-linked
extreme values. Group coverage counts subject-field-context cells. Capture
recorded-time coverage describes archive capture time; source price observation
time remains in `prices.jsonl`. Reports do not establish market popularity or
semantic correctness. Inspect successful extraction as well as reported failures.

Chocolate v2 distinguishes explicit identical-unit packs from unit mass. It uses
labeled body weights and does not interpret bare nutrition-table gram cells as
pack weights. Unclassified candidates remain in the review queue with evidence.

## Author a field profile

`init-silver-profile --input <definition.json> --output <profile>` accepts:

```json
{
  "definition_format_version":"category-silver-definition-2",
  "category":"example", "market":"uk",
  "versions":{"schema":"example-1","mapping":"example-mappings-1","pipeline":"example-parser-1"},
  "attributes":{"identity.name":{"type":"string","unit":null,"scope":"product"}},
  "mappings":{"aliases":{}},
  "pipeline":{"adapter":"structured","fields":[{"attribute":"identity.name","pointer":"/raw_record/identity/name"}]}
}
```

Supported field types are string, enum, boolean, integer, number and string_list.
Declare units, vocabularies, bounds, semantic context and evidence-based meaning.
Numeric source values with explicit units use declared conversion factors. Price
and quantity extraction are optional. Targets and predictors belong to the
separate [Gold procedure](silver-to-gold.md).
