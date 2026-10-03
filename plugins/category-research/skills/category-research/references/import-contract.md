# Raw collection import contract

The envelope below is sufficient to begin collection. `information` and any
additional product fields accept free JSON independently of a feature taxonomy.
`contract_version` is a required nonempty label preserved from the sender.

```json
{
  "contract_version": "1",
  "study": {
    "study_id": "category-study",
    "category": "furniture",
    "market": "uk",
    "currency": "GBP",
    "scope": "Products listed by the selected UK sources."
  },
  "collection_sections": {
    "description": ["description", "bodyhtml"],
    "prices": ["price"],
    "materials": ["material"],
    "dimensions": ["dimension", "height", "width", "depth"]
  },
  "products": [
    {
      "product_id": "source-product-variant",
      "source_url": "https://example.com/products/product",
      "source_key": "example-shop",
      "identity": {
        "name": "Source product name",
        "brand": "Source brand",
        "source_product_id": "source-id",
        "source_variant_id": "variant-id",
        "gtin": null
      },
      "information": {
        "original_source_product": {},
        "original_source_variant": {},
        "additional_source_fields": "Retain source wording, units, offers and availability.",
        "materials": ["Source-stated solid wood"],
        "dimensions": "Source-stated 90 x 45 x 75 cm"
      },
      "source_artifacts": [
        {
          "url": "https://example.com/products/product",
          "kind": "page",
          "local_path": "sources/product.html.gz",
          "content_encoding": "gzip",
          "retrieved_at": "2026-10-03T10:00:00Z",
          "http_status": 200
        }
      ],
      "images": [
        {
          "url": "https://example.com/product.png",
          "source_page_url": "https://example.com/products/product",
          "alt": "Original source label",
          "role": "source product gallery"
        }
      ],
      "collection_notes": []
    }
  ]
}
```

An artifact can provide `local_path` or `content` instead of requesting a fetch.
Local bytes are copied unchanged. String `content` is preserved as UTF-8;
JSON content other than strings is serialized and labeled accordingly. If both are
supplied, local bytes are the archived artifact and the entire descriptor still
remains in the record. Artifact kind labels are extensible. Recognized examples
are `page`, `json`, `text`, `derived_text`, and `fetch_error`. Derived text is
explicitly labeled; failed HTTP responses are not treated as product information.
Unfamiliar kinds and fields remain preserved. Compression, source retrieval times/statuses,
original URLs, and arbitrary descriptor metadata are retained.

`source_catalogs` may be supplied at the document root. A product's
`source_catalog` may be an artifact object, a string containing a local path, or an array of
these. Exact catalog bytes are copied once per run into shared artifacts, with
links from each product capture. Relative local paths resolve from `--input-base`
or the import JSON's directory. Images may also supply `local_path` for existing
original image files.

The CLI requires `--input` and `--output`. `--download-images` fetches all supplied
image URLs by default; `--image-limit N` limits fetched references per product.
`--fetch-pages` retrieves artifacts supplied only as URLs, or the product's `source_url` when
no artifact list is provided. `--workers`, `--timeout`, and `--max-bytes` configure
parallel imports and transfers. Progress for each product goes to stderr; use
`--quiet-progress` to suppress it. Stdout contains a concise summary and the path
of the full run report.

Another Python plugin can add this plugin's root to its module search path and
call:

```python
from category_research import get_raw, import_document

report = import_document(
    document, archive_root, input_base=source_directory,
    download_images=True, image_limit=None, fetch_pages=False, workers=4,
)
metadata, original_bytes = get_raw(public_source_url, timeout=20, max_bytes=20971520)
```

The archive is rooted at
`<output>/<category-slug>/<market-slug>/products/<product_id>/`. Each capture has
immutable source/image files and a history JSON. `product.json` updates atomically
and retains the full raw record, information, notes, and evidence for all
captures. Duplicate product IDs in one import append separate captures safely.
Transfers are cached by URL per run; original bytes are copied into each product
folder. Shared catalogs, original import JSON values, and full run reports are
retained alongside the product folders.

The category label is unrestricted by a bundled category list; records retain
arbitrary fields for food, electronics, apparel, furniture and other product
types. The importer does not discover or extract those fields automatically.
The calling agent supplies source-specific records and obtains evidence through
its authorized retrieval tools.

Optional `collection_sections` maps nonempty section names to nonempty arrays of
field-key markers. Markers are matched as substrings of source keys after Unicode
NFKC normalization, case-folding and retaining letters and numbers; for example, `battery capacity`
matches `battery_capacity_wh`. Only `information` is inspected. Each observation
records matching paths and `source_field_present` or `unknown`, with
`completeness: not_verified`. Nonempty fields include numeric zero and Boolean
false. These heuristic observations cannot establish substantive content,
category applicability or source completeness. No observation is an import
requirement. Omit the configuration to observe description (`description`,
`bodyhtml`), prices (`price`) and availability (`availability`, `available`,
`stock`); supply `{}` to disable all observations. Supplied configuration replaces
the defaults and is retained in captures and reports, alongside
`section_presence_contract_version: category-research-sections-2`.
Source keys in other languages are supported: an English section label such as
`materials` may use an original source marker such as `材料`. Normalization applies
only to matching; configured markers, matching source paths and all raw evidence
retain their original wording and language.

An explicitly configured section named `ingredients` retains the conservative
legacy ingredient heuristic. Ingredient presence requires
substantive source text, lists, or candidate data; metadata, status fields, and
unknown placeholders do not count. An ingredient field can be
`source_field_present` or `unknown`; neither means its text or composition is
complete or independently verified. New product run outcomes use
`section_field_statuses`, and CLI summaries use the `section_fields_unknown` map.
The legacy `ingredient_field_status` and `ingredient_fields_unknown` compatibility
fields are emitted only when `ingredients` is explicitly selected. Calling the
Python `section_presence(information)` helper without markers still provides the
legacy six-section heuristic; `import_document` uses the generic defaults above.
Original page text or unfamiliar field names require separate evidence review.
Previously archived presence reports retain the heuristic used at capture time;
captures without a section-report version use the legacy behavior. The evidence
archive remains `category-research-raw-1`, with its paths, original records and
immutable earlier captures unchanged. Consumers of ingredient counters should
select that section explicitly or read the generic status map.

`status: saved` describes
artifact storage; `source_retrieval_status` and HTTP status describe retrieval.
Failed/truncated responses, artifacts containing only references, and image limits produce
partial capture/report status. Even a fully stored supplied record remains
`completeness: not_verified`. No claim of coverage across the category, feature regression,
certification audit, or schema design is performed by importing records.
