---
name: category-research
description: Collect and archive broad product information, prices, original source evidence, and images for category research before designing a feature taxonomy. Use when building or supplementing a product collection, including collection invoked by another plugin.
compatibility: Requires Python 3.9 or later; network access only when source or image fetching is requested.
---

# Category Research

Start with the requested category, market, source coverage, and product boundary.
Collect many products and retain source-specific information before proposing a
complete analytical schema. Discovery uses the calling agent's available source
retrieval tools; the bundled core imports records and preserves their evidence.

Read [the import contract](references/import-contract.md) when preparing a
collection payload. Preserve complete source records, source product/variant
identifiers, sale/availability evidence, unfamiliar fields, and collection notes.
Do not reduce the payload to attributes already used by a pricing model.

Archive records with the bundled standard-library importer:

```text
python3 <skill-root>/scripts/import_products.py import --input <collection.json> --output <archive-root> --download-images --workers 4
```

Use `--fetch-pages` for URL-only source artifacts. Inline content and `local_path`
artifacts are retained without refetching. Network access is optional; image
limits and downloading are caller choices. Other plugins can invoke this CLI or
use the Python API described in the contract.

Keep original source/image bytes, source timestamps, hashes, provenance, and
immutable capture history. `product.json` is the current index containing all
captures; adding information must retain earlier records and evidence.
Missing ingredients, inaccessible pages, unverified certification, and unreadable
packaging remain unknown or explicitly failed. Source-field presence is not
proof of complete product information. Inspect the persisted run report and
report actual coverage and gaps. Regression, price testing, and scoring use a
later derived schema and are outside this collection plugin.
