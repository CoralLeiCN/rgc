# Research raw data and propose a schema

## Establish the evidence universe

Locate the user's Bronze raw records, artifact references and available source
metadata. For a category archive, inspect `product.json` envelopes, capture
history, source keys, product/variant identities and source URLs. Other supplied
raw formats can inform a proposal without being converted into this archive.
Use source manifests/hashes when available to identify the inspected snapshot.
Keep evidence read-only and write analysis outside source and snapshot directories.

Inventory the full supplied corpus when practical; stream large JSONL files and
aggregate counts rather than loading every artifact into a prompt. For a limited
sample, state its selection and scope. Record source/listing/capture counts,
source formats, field paths, observed value types, explicit units, representative
values, nulls and structural omissions. Report parse failures and inaccessible
artifacts. Keep latest captures and historical captures distinct, and count
seller listings, products and repeated captures with explicit denominators.

Raw key frequency can prioritize work but does not establish semantics. Inspect
source-specific variants of the same key and adjacent context. Distinguish raw
presence from an interpretable value and explicit null from a missing path.
Repeated seller variants or duplicate captures must not inflate apparent support.

## Investigate meaning

Select examples spanning different sellers, product forms, variants and source
formats, including counterexamples and malformed/contradictory cases. Inspect
complete parent objects, headings and relevant product text. Resolve capture IDs
and JSON pointers to the originals; link available images/artifacts when needed
for evidence. Preserve quotations and their original language verbatim.

Investigate concepts embedded in descriptions, ingredient statements, technical
specifications, tables and packaging copy as well as structured keys. A structural
discovery report can miss concepts inside prose already consumed by an extractor.
Example profiles and processed missingness reports are context, not a
complete inventory of what the raw sources establish. Report the actual research
method: mechanical inventory, extraction rules, sampled semantic inspection or
image inspection. A rule written by a model is not individual model review of
every listing.

For each concept, consider alternatives and scope: product, ingredient/component,
brand, packaging or seller observation. Keep physical product relationships
distinct from analytical trait groups. Assess meaningful aliases and unit
conversions; retain minimum, exact, approximate and conditional qualifiers.
Product-specific claims need product-specific context. Navigation, brand-wide
copy, shipping weights and related products cannot silently supply product facts.

Consolidate concepts with equivalent meanings in the new proposed catalog.
If interpretations disagree, retain conflict or defer. Lack of
wording cannot establish a negative claim. Source occurrence counts do not prove
certification truth, completeness or suitability as a model predictor.

## Produce a reviewable proposal

Use the existing project's document/artifact layout. A proposal can be prose,
tables and an optional machine-readable catalog; the accepted catalog becomes
the schema input to later processing contract assembly.
Include these substantive outputs without requiring a particular file count:

- Study scope and intended comparisons, inspected snapshot/provenance, source
  inventory and sampling/coverage limitations.
- Findings about available information, source differences, ambiguities,
  missingness and extraction gaps.
- Proposed field families and a catalog with each field's meaning, type, unit,
  vocabulary/bounds, scope, qualifier rules and normalization policy.
- Field rationale, original evidence references and excerpts, representative
  examples/counterexamples, source coverage and evidence strength. Requested
  fields lacking observed support remain explicitly identified as such.
- Candidate source mappings or extraction rules, with proposed versus implemented
  coverage stated separately. Do not report candidate matches as validated cells.
- Schema identity/version when needed by the project. Preserve original source
  fields independently of the proposed derived catalog.
- Unresolved questions, alternatives, recommended decisions and the next work
  needed for contracts, extraction and processing. Model selection remains a
  separate study decision; unspecified targets/predictors can stay unspecified.

Attach occurrence statistics to their actual denominators and method. A claim
that a proposed field is supported across sources requires investigated evidence
from those sources. A broad tracking catalog may exceed observed evidence;
explain the study reason and coverage gap for those fields.

Exercise representative evidence against the proposed definitions, including
ambiguous scope, mixed units and missing/conflicting cases. Report semantic
checks separately from runtime validation. For research/proposal requests, deliver
this design for review or finalize it within the authorized task. Hand its catalog
and evidence to processing, then to Silver-to-Gold steps when those are requested;
use the existing task authorization without adding a new approval gate.
