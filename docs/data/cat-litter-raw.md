# UK cat litter Bronze collection

The 4 October 2026 study uses the chocolate collection method to preserve UK
cat litter source information in the existing `category-research-raw-1` archive.
The [collection receipt](analysis/cat-litter-raw-2026-10-04.json) records counts,
local locations, source coverage, checksums and verification results. Product
information completeness and exhaustive UK market coverage remain unverified.

## Scope and records

Collect litter substrate, including clumping and non-clumping products, pack
sizes, multipacks and source-labelled unavailable products. Prefilled litter
products such as Catsan Smart Pack are included. Accessory-only trays, scoops,
mats, empty liners, disposal cartridges, deodorisers and delivery services are
excluded from the primary product index; their original catalogue evidence and
selection decisions remain in discovery files.

Three source offers have unresolved litter contents or inconsistent source
identity. Their raw captures remain included as explicit candidates in the
coverage report; they do not establish confirmed litter-only offers.

A record is a seller listing, a source variant or a manufacturer product page.
Sources that expose native variant IDs retain each variant separately. Otherwise,
the original product page and its source options remain together. A source SKU
can be shared by variants; native variant IDs identify those records where
available. Different selling sources remain separate, and record counts do not
establish the number of distinct physical products. Unavailable listings retain
the source status, without treating it as evidence of current stock.

The collection retains original product and variant JSON, descriptions,
source-stated composition, sizes and units, prices and conditions, availability,
usage and disposal instructions, claims, source IDs and image URL references
where supplied. Original source wording and language remain intact. No complete
field catalogue is required for Bronze. `collection_sections: {}` disables
field-presence heuristics for this study; no analytical schema or derived feature
values are produced.

## Local files

The raw archive is `data/collections/cat-litter/uk/`. This capture used the
collection implementation before the source directory convention was integrated
into this task. It retains the supported flat product layout and original source
keys, including source labels containing dots. Current readers and verification
accept the saved layout. New imports use the current source-key rules in the
[import contract](../../plugins/category-research/skills/category-research/references/import-contract.md).
The original input remains the exact historical sender document.

Its saved paths are:

- `products/<product_id>/product.json` contains every preserved capture.
- `products/<product_id>/history/` contains immutable capture records.
- `products/<product_id>/sources/` contains original source artifacts.
- `catalogs/` contains shared catalogues linked to relevant product captures.
- `discovery/` retains source responses, retrieval metadata, supplemental evidence,
  attempted sources, exclusions and collection audit reports.
- `runs/` retains the exact import document and importer report.
- `coverage.json`, `archive-verification.json` and `README.md` describe this study.

The preparation directory is `data/cat-litter-uk/`. Its collector inputs, source
responses and reports remain local. The verified text export is
`data/exports/cat-litter-uk-2026-10-04/`; `products.jsonl` indexes the records and
`evidence/cat-litter/uk.tar.gz` contains the filtered text evidence. The complete
local bundle is `evidence/cat-litter/uk-complete-raw.tar.gz`. Extract that complete
bundle to a common collections root to resolve archive-relative references.
The text exporter excludes original `.response.gz` paths; matching source copies
remain in discovery, and the complete bundle preserves every original path.
Both bundles have verified byte inventories. Git keeps
the small receipt and this guide; the ignored local evidence is not included in
a repository clone. Raw evidence follows the existing local storage policy.

## Evidence and limitations

Direct retrieval retains original HTTP response bytes, usually in gzip form,
with URLs, timestamps, HTTP status and SHA-256 hashes. Failed responses and
interruption shells remain failed or limited evidence. Text returned by a web
retrieval provider is labelled with its method and any returned crawl date; it
cannot establish that the underlying page or price was live on the collection
date. Search snippets serve discovery. Full structured catalogues can supply
product information when a detail page fails, with the failure retained.

Catalogue pagination reports describe the traversed source pages and observed
stopping conditions. Manufacturer ranges without enough UK sale evidence remain
supplemental discovery. Dynamic content, source inconsistency, store-specific
availability, shipping geography and promotions require later investigation.
Amazon, eBay and other marketplaces have finite observed coverage. Independent
stores, regional shops, offline-only products and new listings can remain absent.
Image URLs are retained; image payloads and packaging OCR were not collected.

Storage verification checks saved bytes, raw records and immutable history. It
does not validate manufacturer claims, establish product completeness or measure
UK market recall. No Silver dataset, analytical profile or pricing model is
created for cat litter by this collection.

## Verification and reuse

Use the existing collection importer for additional evidence and preserve its
history. The [import contract](../../plugins/category-research/skills/category-research/references/import-contract.md)
owns the envelope and capture semantics. Verify the completed local archive with:

```sh
python3 -B scripts/verify_product_archive.py \
  --archive-root data/collections --category cat-litter --market uk \
  --input data/cat-litter-uk/inputs/combined.json \
  --report data/collections/cat-litter/uk/archive-verification.json
```

The [raw storage specification](spec.md#311-public-dataset-publication-policy)
owns local export rules. The receipt records the export directory and its
manifest and bundle hashes. Reuse the full raw records and attributed source
artifacts for later research; collection counts alone do not define an analytical
schema or reviewed model inputs.
