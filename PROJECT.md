# retail frontier

## What we built

retail frontier helps brands and retail buyers investigate product features and
price positioning, starting with chocolate sold in the UK. The decision we aim
to support is whether a proposed product's features and price are comparable with
products in a chosen retail context.

We built a reusable workflow that preserves original product information,
ingredient lists, packaging claims and seller prices. It combines deduplication
within each seller, typed feature standardization, price normalization and
evidence review, while keeping listings from different sellers distinct. Every
derived interpretation links back to source evidence, and missing or conflicting
information remains visible.

The working product produces reproducible datasets, review reports, eligibility
decisions and immutable Parquet Gold training snapshots. An experimental OLS
trainer is implemented. All 2,134 Gold candidates are included automatically without eligibility fields, and current-price preparation produces 630 unit-price targets.
Actual missing quantities and identities still constrain real fitting. The web
form now serves the published LightGBM synthetic fixture with price predictions
and signed SHAP field contributions. Validated market benchmarks and AI
explanations remain planned.

## Our data

| Aspect | Details |
| --- | --- |
| Scope | Chocolate listings from UK retailers and direct brand stores. |
| Record | One product offered by one seller; the same product at different shops retains separate listings and prices. |
| Collected fields | Prices, pack sizes, ingredients, nutrition, descriptions, packaging and promotional claims, where available. |
| Source evidence | Source links, capture dates, original text and available images. |
| Bronze / raw archive | Original records, source evidence and capture history. |
| Silver dataset | Standardized features, comparable price units and review flags; missing or conflicting information stays visible. |
| Gold snapshots | One immutable Parquet training population with verified contracts and evidence provenance; eligibility columns are removed. |
| Current status | All Gold candidates are model eligible under the user instruction; actual missing inputs still limit training, and UK market coverage is unverified. |
| Demo sample | Five illustrative records from the study. |

## How it works

The [data flow diagram](docs/data/chocolate-silver.md#data-flow) shows the path
the bronze/raw, silver and Gold stages, with descriptions of their
purpose, outputs and current status.

| Part of the product | Current status |
| --- | --- |
| Collect and preserve original product records, source artifacts and capture history. | Implemented through the collection plugin. |
| Deduplicate within sellers, standardize supported chocolate features and normalize supported prices. | Implemented through the combined silver pipeline. Listings from different sellers retain separate identities. |
| Retain evidence references, missing values, conflicts and review requirements. | Implemented in derived records and quality/review reports. |
| Prepare eligible model inputs and keep related product families together during validation splits. | Helpers implemented. Gold includes all 2,134 candidates without an eligibility flag; current-price preparation produces 630 targets per 100 g. |
| Export immutable Gold and train an experimental OLS model. | Export and trainer implemented. Current-price targets use collected displayed prices; missing quantities and identities still limit fitting. |
| Predict a demo price and inspect field SHAP contributions. | Implemented locally using the published LightGBM synthetic fixture; real market accuracy and intervals are unvalidated. |
| Validate pricing benchmarks, compare retailer contexts and generate AI explanations. | Proposed designs; market validation and AI explanations remain pending. |

The standalone [processing plugin](plugins/category-processing/README.md)
packages this workflow for other product categories. It accepts category
profiles, reports mapping gaps and unfamiliar source fields, and prepares
frozen model inputs when reviewed records are eligible. Chocolate and coffee
profiles are included, and a profile generator creates working contracts from
an explicit category definition.

The [implementation plan](docs/lifecycle/plan.md) records verification and
remaining work. The [pricing design](docs/data/chocolate-modeling-design.md) and
[explanation design](docs/data/analysis/lightgbm-shap-explanation-design.md) describe
the proposed modelling stage.

## Limitations

The current chocolate study uses collected displayed selling prices as its
regular-price proxy. The web demo uses a historical synthetic fixture with
`regular-consumer-price-1`; that fixture does not estimate current market prices.
For the current study, a separate verified regular-price target is not
required. Where edible pack weight is available, the target is current GBP per
100 g; regressions use its natural logarithm.

Displayed prices may include promotions, membership conditions or temporary
offers. These effects are not separated from product features, brand or retailer
associations. Source tax inclusion is not independently verified or harmonized.
Prices describe their recorded source captures and may span different dates;
they do not establish live prices or a common observation window.

Eligibility records the user's selection instruction. It does not supply missing
quantities, product identities or predictor values. The current snapshot yields
630 normalized targets from 2,134 candidates; 1,503 lack edible weight and one
lacks a usable current price. Exact variant IDs are still missing. Models must
report their actual usable sample and remaining fitting constraints. Observed
associations do not establish causal feature premiums or willingness to pay.

The [training target specification](docs/data/chocolate-modeling-design.md#1-population-and-price-target)
defines this assumption and its versioned preparation.

## Running the current product

Run the commands from the repository root with Python 3.9 or later. The example
below imports five illustrative records into an archive without fetching pages
or images. It adapts the bundled sample to the collection plugin's import
envelope and preserves each original product and the sample metadata.

```sh
python3 -B - <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, "plugins/category-research")
from category_research import import_document

sample = json.loads(Path("examples/collections/uk-chocolate-five-products.json").read_text())
document = {
    "contract_version": "1",
    "study": {
        "study_id": sample["study_id"] + "-demo",
        "category": sample["category"],
        "market": "uk",
        "source_sample_metadata": {k: v for k, v in sample.items() if k != "products"},
    },
    "products": [{
        "product_id": product["product_id"],
        "source_url": product["sources"]["retailer"],
        "information": product,
        "collection_notes": ["Illustrative record; original pages were not fetched by this demo."],
    } for product in sample["products"]],
}
output = Path("data/product-demo")
result = import_document(document, output)
print(output / result["report_path"])
PY
```

Inspect the returned report and the archived records under
`data/product-demo/chocolate/uk`. This demonstrates record preservation and
capture history. The sample's completeness remains unverified, and the demo
does not establish model readiness.

For the full processing workflow, use a collected raw archive and the pinned
contracts described in the [README](README), [silver guide](docs/data/chocolate-silver.md)
and [dataset contract guide](docs/data/dataset-contracts.md). Raw datasets and contract
caches are supplied separately from this checkout.

## Inferred Gold refit limitations

Gold training now treats every candidate as eligible under the user's explicit
instruction of 3 October 2026. Original review/eligibility decisions remain
provenance. The published `lightgbm_without_brand` inferred refit uses
`current-consumer-price-1`: collected displayed prices are the regular-price
proxy, with promotions, membership effects and tax taken as displayed. It
uses 55 Waitrose bar observations across 15 established families; missing
price, pack mass and family grouping restrict numerical use despite admission.
The fitted feature set excludes brand. Recipe, single-pack status and cocoa
percentage basis remain unestablished; missing feature values retain native
missing routes. The final holdout has three families and supplies no credible
market-release claim, Ocado score or calibrated prediction interval.
See the [refit record](docs/data/analysis/lightgbm-without-brand-inferred-refit.md).
