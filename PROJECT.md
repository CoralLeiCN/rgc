# retail frontier

**Track:** Retail Futures. This document explains the project using the
[EAT_HACK requirements](docs/eat-hack-track-two.md).

## Project description

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

The working product produces reproducible datasets, review reports and
eligibility decisions for later modelling. Interpretable pricing benchmarks,
LightGBM predictions and AI explanations are planned; chocolate evidence still
requires review before training and validated price testing.

This approach makes data quality and uncertainty part of the retail decision
process. It helps teams identify which evidence needs checking before using a
price comparison. We built the project during EAT_HACK with no substantial
pre-existing project work.

## Retail problem and intended decision

A brand designing a chocolate product or a buyer evaluating its price needs
comparable evidence about ingredients, claims, pack quantities and selling
context. Listings can repeat, use different units or leave key facts unresolved.
These differences affect how useful a price comparison is.

Our intended decision is to assess a proposed product's price positioning within
a supported retail context. The current workflow establishes the evidence and
review needed for that assessment. A validated pricing benchmark remains a
development goal. Observed price associations alone cannot establish consumer
willingness to pay, demand or causal effects of individual features.

## Approach and implementation status

| Part of the product | Current status |
| --- | --- |
| Collect and preserve original product records, source artifacts and capture history. | Implemented through the collection plugin. |
| Deduplicate within sellers, standardize supported chocolate features and normalize supported prices. | Implemented through the combined silver pipeline. Listings from different sellers retain separate identities. |
| Retain evidence references, missing values, conflicts and review requirements. | Implemented in derived records and quality/review reports. |
| Prepare eligible model inputs and keep related product families together during validation splits. | Helpers implemented. Current chocolate evidence requires review and has no eligible reviewed training inputs. |
| Fit pricing benchmarks, compare retailer contexts and explain predictions with SHAP and AI. | Proposed designs; fitting, validation and explanations remain pending. |

The [implementation plan](docs/lifecycle/plan.md) records verification and
remaining work. The [pricing design](docs/chocolate-modeling-design.md) and
[explanation design](docs/analysis/lightgbm-shap-explanation-design.md) describe
the proposed modelling stage.

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
output = Path("data/hackathon-demo")
result = import_document(document, output)
print(output / result["report_path"])
PY
```

Inspect the returned report and the archived records under
`data/hackathon-demo/chocolate/uk`. This demonstrates record preservation and
capture history. The sample's completeness remains unverified, and the demo
does not establish model readiness.

For the full processing workflow, use a collected raw archive and the pinned
contracts described in the [README](README), [silver guide](docs/chocolate-silver.md)
and [dataset contract guide](docs/dataset-contracts.md). Raw datasets and contract
caches are supplied separately from this checkout.

## Judging criteria and evidence

| Criterion | Weight | What this project can demonstrate | Evidence still needed |
| --- | --- | --- | --- |
| Originality & Thinking | 30% | A workflow connecting source evidence, seller context and explicit review to the intended pricing decision. | Explain why these choices improve the chosen user's workflow. |
| Build & Execution | 30% | Working collection and processing code, immutable captures, reproducible outputs and review gates. | Record the working workflow in the demo; present proposed models as planned work. |
| Value & Relevance | 25% | A concrete pricing problem for a brand or retail buyer, with traceable product evidence. | Validate usefulness with a user or worked decision; evaluate prediction accuracy after eligible inputs and fitting are available. |
| Demo & Communication | 15% | A clear walkthrough from a product record to preserved evidence and review status. | Produce the public video and explain the current capability and its limits. |

## Submission fields

| Submission field | Content or status |
| --- | --- |
| Project name | retail frontier |
| Team members | Names have not been provided. |
| Track | Retail Futures |
| Project description | The 169-word description above fits the required 100–200 words. |
| Work built during EAT_HACK | The team confirms no substantial project work existed before the event. The implemented workflow was built during EAT_HACK; modelling remains planned. |
| Video URL | Not yet provided. The video must be at most two minutes and show the working product and what was built during EAT_HACK. |
| Repository URL | [CoralLeiCN/rgc](https://github.com/CoralLeiCN/rgc), from the configured Git remote. Public access has not been verified. The README contains running instructions. |
| Best Brand vote | The team's three favourite brands from The Shelf have not been provided. This vote does not affect project judging. |
| Live product URL | Optional; none provided. Deployment adds no judging points. |

Verify every submitted link is publicly accessible without signing in or
requesting permission. Team names, the video and brand selections still need to
be added before submission.
