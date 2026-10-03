# Product Feature Classification and Pricing Specification

Status: the raw collection plugin and a UK chocolate corpus are implemented.
The analytical schema, pricing model, brand price-testing application, and
value-for-money scoring remain proposed.

The [intention](intention.md) records the requested product scope. This document
turns that scope into proposed data, modeling, and acceptance requirements.
Implementation choices below are proposals, not additional statements of intent.

## 1. Scope and delivery order

| Stage | Requested outcome | Implementation status |
| --- | --- | --- |
| 1 | Collect and preserve broad original product information, images, and prices through a portable agent plugin; derive a feature schema from the collected products, then fit a regression model explaining feature contributions. | Raw collection implemented; analytical schema and model remain proposed. |
| 2 | Let a brand test the price of a newly designed product using that model. | Follows a validated category model. |
| 3 | Score category value for money and assess brand premium. | Research only; scoring implementation is deferred. |

The product must support many categories over time. Chocolate sold in the United
Kingdom is the current collection study and an example for later categories.
The market describes where products are sold. Country of
manufacture is a separate attribute where relevant.

Start collection with category boundaries and a minimal product identity and
provenance envelope. Preserve original product information and images, and use a
broad, source-driven JSON file for each product. A complete feature taxonomy or
category profile is not a prerequisite for collecting products.

After broad collection, derive a complete analytical schema for the collected
scope, including category-specific attributes, variant identity, units,
comparison groups, and pricing basis. Extend it when further collection reveals
new information. The raw collection contract remains independent of this later
schema. Adding a category may require source extractors and an analytical
profile, without changes to the category-agnostic core. Each category/market
study has its own dataset, model eligibility, validation, and price-test domain;
a model validated for chocolate does not automatically support another category.

Product-information collection must be delivered as an agent plugin usable
across multiple agent harnesses. An agent harness is the runtime that executes
an agent and supplies its tools. The proposed portability design is in section
2.4. Packaging follows Agent Plugins 1.0.0; native harness support still needs
to be demonstrated.

The repository's documentation, code, comments, identifiers, tests, and
application copy must use English, regardless of the prompt language.

## 2. Core workflows

### 2.1 Research a category

1. Define the category, market, category boundaries, collection period, and
   intended source coverage. Use minimal identity and provenance fields; no
   complete feature schema or normalization rule is required yet.
2. Discover a broad set of products across sources, brands, product forms, sizes,
   category-specific attributes, packaging, promotional claims, and price ranges.
3. Use the collection plugin to preserve original source pages/text and product
   images, with a broad product JSON covering relevant source information,
   prices, packaging, and promotional material. Retain unfamiliar fields and
   claims without forcing them into a predetermined taxonomy.
4. After collecting many products, review the corpus and derive the analytical
   category schema. Classify features from the preserved evidence, resolve
   duplicates, and review ambiguous or missing data.
5. Define comparable groups, price basis, normalization, and model eligibility;
   produce a coverage and quality report before fitting a model.

Collection aims for as many distinct products and varieties as practicable.
There is no invented fixed product-count requirement. Report the number found,
the sources searched, coverage gaps, failed extraction, and excluded products.
Multiple listings of one product increase price observations, not unique product
coverage. An incomplete search must not be described as the entire target market.

### 2.2 Fit and inspect a pricing model

1. Select the eligible observations and comparable product group.
2. Build model inputs from the reviewed feature schema.
3. Fit an interpretable regression and evaluate it on held-out data.
4. Present feature estimates, reference levels, uncertainty, support counts,
   validation results, and limitations.

The output must distinguish an estimated conditional price association from a
causal effect. A coefficient cannot by itself establish that adding a claim or
ingredient causes the corresponding price change.

### 2.3 Test a newly designed product

1. A brand describes a proposed product using the model's feature schema.
2. The user selects supported market, product-group, and pricing context.
3. The model estimates a price and prediction interval, with feature comparisons
   and warnings about unsupported inputs.
4. If the user supplies a proposed selling price, compare it with the model's
   estimate in both currency and percentage terms.

This is a test against observed market pricing. It does not estimate demand,
profit, or the revenue-maximizing price; those quantities require other data.

### 2.4 Product-information collection agent plugin

The plugin covers discovery and collection for a category study: prices, basic
product information, product features, packaging emphasis, promotional claims,
and their source evidence. It produces per-product raw bundles with original
pages/text, original images, and broad source-driven JSON. The JSON is an index
and record of collected information, not a complete analytical schema imposed
before collection. Later schema derivation and normalized analysis use these
preserved bundles. Regression fitting, new-product price testing, and deferred
scoring remain application responsibilities.

The design has three parts:

| Part | Responsibility |
| --- | --- |
| Portable collection core | Apply the study scope, preserve original evidence and images, and produce broad product JSON and the common collection result without requiring a complete feature taxonomy. |
| Standard plugin package | Expose a discoverable Agent Skill in the Agent Plugins format; the calling harness supplies discovery/retrieval tools and can invoke the bundled CLI or Python API. |
| Source extractors | Capture source information and images without discarding unfamiliar fields; allow new sources and categories without changing the common raw result envelope. Later analytical profiles may guide derived extraction without replacing the raw collection. |

#### Input and output contract

Use a versioned, structured request/result contract; JSON is the initial proposed
representation. Native tool names and packaging may differ between harnesses,
but the meanings of these inputs and outputs must be consistent.

| Direction | Content |
| --- | --- |
| Request | Envelope contract version, study identifier, category, market, category boundaries, source scope, collection window, requested information, and coverage goals where defined. Existing analytical profiles or comparison bases are optional references, not collection prerequisites or field filters. |
| Result metadata | Envelope contract version, study/category identifiers, collection run identifier, collection time, completion status, and declared tool/extraction capabilities used. |
| Result bundles | Per-product identity/provenance envelopes, broad source-driven product JSON, timestamped raw page/text evidence, original product images, artifact metadata, and collection history, following section 3. Later interpretations carry their own schema/version and evidence references. |
| Result report | Sources attempted and reached, unique product coverage, missingness, extraction limitations, inaccessible sources, failures, and reasons the study scope was only partially covered. |

The request must carry or explicitly reference the study scope. It does not need
a complete category profile. The plugin must not depend on unstated previous
conversation, one harness's internal session identifiers, or hardcoded local
output paths.
Evidence references must remain resolvable by the consuming application; an
opaque host-local identifier alone is insufficient.

#### Compatibility and incomplete collection

Each harness integration must declare the capabilities it provides and how it delivers the
result bundle. If a requested source or packaging/image extraction capability is
unavailable, record the limitation, preserve unknown values, and return partial
results where useful. Missing capabilities or inaccessible sources must not
produce invented data or an unqualified successful-completion claim.

Validate integrations against the same request/result contract and supplied evidence
fixtures. Support must be demonstrated in at least two selected agent harnesses
before describing the plugin as compatible with multiple harnesses. Live search
can discover different products across hosts; conformance means compatible
envelope meanings, artifact preservation, and evidence handling, not identical
live-search results or identical product-specific field sets.

The implemented package at
[plugins/category-research](../plugins/category-research/README.md) follows the
[Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification): a
root `plugin.json` manifest and `skills/category-research/SKILL.md` component.
The bundled Python 3.9+ standard-library core is callable through a CLI or
`category_research.import_document`; another plugin can compose those entry
points directly. The package has no MCP component.

Discovery remains an agent workflow using its available public-source tools.
The importer archives a supplied versioned raw collection document; current UK
chocolate inputs use `draft-raw-1`. It does not claim an automatic exhaustive
market search. Its
[import contract](../plugins/category-research/skills/category-research/references/import-contract.md)
defines the implemented envelope, exact-byte preservation, arbitrary source
fields, failure reporting, image retrieval, and append-only captures. Native
installation and execution in multiple harnesses have not yet been tested.

## 3. Data contract

Collection uses a minimal common envelope and extensible product information.
It preserves sources before committing to the complete analytical schema.
Source-reported facts, later interpretations, and normalized model inputs must
remain distinguishable. A product can have multiple sources and prices across
retailers and dates without becoming multiple distinct products.

### 3.1 Per-product raw archive

The archive uses a current product index, immutable source/image artifacts, and
timestamped history. The implemented plugin layout is:

```text
collections/<category>/<market>/products/<product_id>/
    product.json
    sources/
        <capture_id>/<artifact_number>.<source_format>
    images/
        <capture_id>/<image_id>.<original_extension>
    history/
        <capture_id>.json
```

For the chocolate example, category and market directory identifiers may be
`chocolate` and `uk`. Equivalent bundles may be delivered by another harness;
the directory layout must not become a dependency on a particular host path.

`product.json` should cover as much relevant product information as the sources
provide. Retain source-specific fields and sections, original reported values,
units, descriptions, ingredients or other category information, prices and
offers, packaging details, and promotional claims. Preserve information that
has no normalized feature yet. Do not limit collection to the fields used by
the five-product illustration or by an eventual pricing model.

The source-driven JSON needs only a minimal envelope for product identity,
category/market, collection history, and source/artifact references. Product
information may vary between products. Preserve conflicting source statements
with their separate provenance rather than selecting a value silently. A
normalized label, visual interpretation, summary, OCR transcription, or computed
unit price must be identifiable as derived and reference its supporting source;
it must not replace the original page text, reported price, or image.

Keep original retrieved page or structured-source content in `sources/` when
available. A captured text representation can be stored alongside it; record
whether it is original source text or a generated extraction. If only text was
retrievable, preserve that text and state the missing original-page limitation.
Record source URL, publisher/retailer, capture time and timezone, retrieval
method, content type, relative file path, and a content hash for each saved
artifact. SHA-256 is the proposed hash algorithm. Retain the original product
image bytes and format in `images/`, including available packaging panels, with
the image URL, associated product/source, capture time, and hash. Record missing
or inaccessible images rather than substituting an image or implying that every
panel has been captured.

Append new source/image captures and collection records instead of overwriting
earlier evidence. `product.json` may be the current index, with timestamped JSON
capture records in `history/` preserving earlier evidence and source conflicts. Analytical
schema changes must not rewrite raw artifacts. Capture timestamps are collection
times, not a claim that a price was valid throughout a period. Keep any stated
offer dates separately.

The existing
[five-product JSON](../examples/collections/uk-chocolate-five-products.json) is a
narrow illustrative derived sample. Its `draft-1` field set is not the canonical
raw schema, a complete category taxonomy, or an implemented plugin contract.
Do not relabel a reconstruction from that sample as the original historical
page/image capture.

| Collection record | Minimal content and preservation rule |
| --- | --- |
| Study envelope | Study ID, category, market, scope/boundaries, collection window, source scope, and envelope version. A complete analytical profile is not required. |
| Product envelope | Local product ID, category/market, available source identifiers and source-reported identity, artifact references, and collection history. Keep identity matches provisional when ambiguous. |
| Source-driven product information | As much relevant source information as can be captured, with source/section references and original reported values and units. Allow fields and sections beyond any current taxonomy. |
| Raw source/image artifact | Original content where retrieved, URL, publisher, capture timestamp/timezone, retrieval method, content type, relative path, hash, and declared capture limitations. |
| Collection record | Run ID, capture time, sources/artifacts added, outcomes, missing information or capabilities, and references to retained history. |

### 3.2 Later analytical schema and feature classification

After broad collection, derive a complete schema for the information and
comparisons in the collected category scope. Review source-specific fields,
units, claims, product forms, identity, and missingness across many products.
Version the resulting profile and mappings; extend them as new information is
collected. Schema development must not discard original fields or unclassified
claims from the raw archive.

Keep derived product variants, classified features, and price observations
separate from raw artifacts and from one another. The following contract applies
to the later analytical dataset, not as a prerequisite for collection:

| Record | Required content |
| --- | --- |
| Category profile | Category ID and profile version, typed attribute definitions, applicable units, identity and product-family rules, comparable-group definitions, extraction guidance, and supported price/normalization bases. |
| Category study | Category/profile version, market, included/excluded product forms, comparable groups, collection window, currency and price definition, quantity/normalization basis, source coverage. |
| Product variant | Internal ID, category/profile version, source identifiers where available, product name, brand, variant, product form, and applicable selling-unit/quantity information. Edible weight and pack count belong to profiles where relevant. |
| Product information | Derived category-specific attributes with types, units, raw source references, and mapping/schema version. Ingredients, cocoa percentage, nutrition, and dietary information are chocolate examples. Missing information remains missing. |
| Source evidence | References to preserved source/image artifacts, source URL, collection time, and the location supporting each extracted feature. |
| Classified feature | Feature name, normalized value, value type, evidence reference, extraction method, review status, and schema version. |
| Price observation | Product ID, source/retailer, observation time, currency, displayed selling-unit price, available regular price, promotional status/mechanics, applicable quantity and units, normalized price and basis where used, availability, and known tax basis. |
| Model version | Category/profile, study and data versions, target price basis, eligibility rules, feature schema, missing-value policy, model formula, reference levels, default prediction context, training/validation split, fitted parameters, evaluation, and supported input domain. |

Analytical identity resolution must follow the derived category profile. For
chocolate, distinguish flavor, ingredients, weight, and pack configuration.
Other categories use their own variant-defining attributes. Use source
identifiers when available and review ambiguous matches. Preserve the relationship between related sizes
or variants for validation grouping.

Use an extensible category-specific vocabulary, with feature types, units,
allowed values, and unknown-value rules defined by the derived profile. Each
analytical dataset must record the profile version used. Preserve newly
discovered attributes or claims for review and possible schema extension. The
following chocolate attributes illustrate one profile rather than an exhaustive
or universal list:

| Feature family | Examples and classification rules |
| --- | --- |
| Identity | Brand, product range, chocolate type, product form. |
| Composition | Cocoa percentage, nut presence and type, fillings, fruit, caramel, other inclusions. A "may contain nuts" allergen warning is separate from nuts as an ingredient. |
| Claims and certifications | Fairtrade or another specifically named scheme, organic, vegan, single origin. Keep general fair-trade wording separate from a named certification mark. |
| Size and packaging | Net weight, pack count, wrapper/box format, visible material descriptions, gift presentation, packaging claims. Unknown material must not be guessed. |
| Promotional emphasis | Exact visible claims and their normalized themes, including origin, craftsmanship, sustainability, flavor, quality, or gifting when actually stated. |

During collection, capture every identifiable packaging and promotional
emphasis, including claims that do not yet have a normalized feature. A fixed
initial vocabulary must not silently discard new claim types. Retain supporting
text and image references so the classification can be revisited.

For presence/absence attributes, distinguish `present`, `absent`, and `unknown`.
Missing text or unreadable packaging is `unknown`, not evidence of absence.
Record whether a claim appears on packaging, in retailer copy, or in other
promotional material. A seller's claim is an observed claim; it does not alone
verify certification, composition, or product quality.

Collection may combine structured source retrieval, page/text capture, and image
retrieval. Later analytical extraction may combine text extraction, image/OCR
extraction, classification, and manual review. Preserve the originals throughout.
The exact tools remain undecided. Classification accuracy must be evaluated
against a reviewed sample; a confidence score alone is insufficient.

### 3.3 Prices and comparability

For analysis, each category study defines currency, selling-unit price,
tax/promotion basis, applicable quantities, and any normalization rule. A price
per item, pack, mass, or volume may be appropriate depending on the category. Do
not require edible weight or price per 100 g for every product category.

Collection retains original price text, currency, quantities, and offers as
reported, even when their normalization or model eligibility is unresolved.
Computed prices belong to the derived layer and retain links to the originals.

For the UK example, the initial proposal is GBP regular consumer pack price on a
consistent recorded tax basis. Also retain the displayed price and promotions.
If no regular price is observable, do not infer it from a discount label; exclude
that observation from the regular-price model or use a separately defined
displayed-price analysis.

For this chocolate example, normalize by total edible weight:

```text
price_per_100g = pack_price_gbp / total_edible_weight_g * 100
```

Validate currency, positive price, applicable quantity units, and arithmetic.
Keep missing or ambiguous quantities for coverage reporting but exclude them
from models that require those quantities. Store promotions separately so
discounted and regular prices are not mixed silently. Record paid shipping
separately if observed.

Define comparable groups before modeling. Bars, assorted gift boxes, and baking
chocolate illustrate groups that may have different pricing mechanisms. Price
per 100 g does not alone make them interchangeable. Use separate group models or group terms and
supported interactions, and report the chosen boundary.

## 4. Dataset readiness

Before fitting, report:

- Unique variants, related product families, brands, retailers, dates, and
  comparable groups.
- Coverage across category-specific feature values, applicable sizes/quantities,
  and price ranges.
- Missingness, unknown labels, disputed matches, and extraction review results.
- Exclusions and their reasons, including inconsistent price or quantity data.
- Rare features, correlated features, and combinations absent from the sample.

"Enough data" means enough independent products and variation for the intended
comparisons, with acceptable validation and uncertainty. It is not established
by an arbitrary row count. A feature seen only in one brand may be inseparable
from that brand's effect; repeated retailer listings do not solve this problem.
Mark such estimates as unsupported, combine levels transparently, or collect
more varied products instead of reporting a confident contribution.

Sampling and retailer coverage determine what population the model describes.
Without sales data, it describes the sampled listings and does not represent a
sales-weighted market average.

## 5. Pricing regression

### 5.1 Initial model proposal

Start with a hedonic regression: relate observed prices to measured product
characteristics. Each category study selects its target, normalization, and
terms using its own profile and comparable groups; validate the model for that
study. The proposed target for the UK chocolate example is the log of regular
GBP price per 100 g:

```text
log(price_per_100g_i) = intercept
    + product_feature_terms_i
    + brand_term_i
    + size_and_pack_terms_i
    + retailer_term_i
    + collection_period_term_i
    + error_i
```

Use available variation to choose terms; a constant collection period does not
need a fitted time effect. For chocolate, include pack-size terms because unit
normalization does not remove quantity discounts. Use the applicable
quantity/size terms for each category. Add interactions only when there is
adequate support and an explicit reason. Compare against a simple category/group
baseline and keep the formula interpretable.

Specify reference levels for categorical features. Review rank deficiency,
correlation, sparse levels, influential observations, residual behavior, and
stability across sources and reasonable model choices. Account for dependence
between observations of the same product when estimating uncertainty.

For an established statistical use of this method, see the
[BLS explanation of hedonic quality adjustment](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm).
Applying it to UK chocolate is this specification's proposal and requires its own
validation.

### 5.2 Feature contributions

For a log-price model's indicator coefficient `beta`, report the estimated percentage price
difference relative to its reference as `100 * (exp(beta) - 1)`, holding the
other modeled terms fixed. Report continuous features with their unit or an
explicit input change. With interactions, calculate the contrast for the actual
product context rather than displaying one unconditional coefficient.

For another target scale, use the corresponding model interpretation and
prediction contrasts in its declared units. Record that interpretation in the
model metadata.

Each result must identify its reference, sample support, uncertainty, and
conditioning variables. Log-scale contributions are additive in log space;
percentage effects are multiplicative. Do not present percentages or currency
contrasts as additive shares of the final selling price.

For a supported product profile, also express a feature contrast as the
difference between two predicted prices with the feature changed and all other
inputs held fixed. State both profiles and the selling-unit basis of that currency
difference.

If two attributes cannot be distinguished in the data, say so. A Fairtrade term
may capture correlated brand, origin, quality, or retail positioning that the
dataset does not adequately measure.

### 5.3 Validation and model release

Split by product family so repeated retailer listings, duplicate observations,
and closely related variants do not leak into both training and validation.
Learn preprocessing from training data only. Each model must document how it
handles missing values in training and prediction, including any unknown levels,
imputation, or required-input rejection; use that same fitted policy in both.
If future-period prediction is claimed, also validate on a later collection
period. If support for unseen
brands is claimed, evaluate a suitable brand-held-out prediction path.

Measure price error on the original scale and in the study's currency and target
units, for example MAE in GBP per 100 g for the UK chocolate study, and
relative error, alongside prediction-interval coverage. Compare with the simple
baseline and report errors by supported group, size, brand, and retailer where
the sample permits. A high training R-squared is not a release criterion.

Exponentiating a log prediction does not automatically produce an expected
arithmetic price. State whether the output is a median or mean estimate; a mean
requires a justified retransformation adjustment and original-scale validation.
Use prediction intervals for a new product, not only coefficient confidence
intervals.

Numeric coverage, extraction-quality, and prediction-error release thresholds
remain open decisions. Define them for the study before judging a model ready.
If the data or validation is inadequate, retain the dataset report and mark the
model experimental or unavailable for supported price testing.

## 6. New-product price test

### 6.1 Inputs

Require category, market, comparable group, applicable selling-unit/quantity
information, and the features required by the selected model. Use the same
category profile, vocabulary, and units as training.
Unknown values remain unknown. Optional inputs include an observed brand, a
supported retailer/time context, and a proposed selling price. When context is
omitted, use and display the model's documented default within its validated
domain. If no such default exists, require the relevant context before testing.

The proposed selling price uses the study's currency and declared selling unit,
on the same tax and promotion basis as the selected model. For UK chocolate this
is a GBP pack price for the described pack. Compare it with the corresponding
selling-unit estimate; convert both prices consistently when displaying
normalized-price comparisons.

An unknown brand must not receive a fabricated brand coefficient. A proposed
fallback is a separately fitted and validated model without brand terms. Label
that estimate as a brand-unspecified market benchmark: other features may still
absorb brand-associated differences. A known-brand scenario uses its
fitted term and states the reference. Unsupported retailer, category, or feature
levels must be handled explicitly rather than silently mapped to a reference.

### 6.2 Outputs

- Estimated price in the study's currency and target units, with the corresponding
  selling-unit price and estimate type stated. For UK chocolate, this is GBP per
  100 g and the implied pack price.
- A prediction interval on the same price basis.
- Context-specific feature contrasts relative to stated references.
- When supplied, proposed-price difference: `proposed - predicted`, and
  `100 * (proposed / predicted - 1)`.
- Data/model version, comparable group, and evidence/validation context.
- Flags for missing inputs, unseen levels, poorly supported combinations, and
  extrapolation beyond observed ranges.

Reject mathematically invalid inputs. For unsupported valid inputs, either
decline to produce a supported prediction or provide an explicitly experimental
estimate, depending on the model's documented domain policy. A design using
individually familiar features can still be an unsupported combination.

## 7. Deferred value-for-money and brand-premium research

This section is research for stage 3, not a requirement to implement a score now.
The planned product and price dataset can support an adjusted-price comparison;
it cannot by itself establish consumer utility, sensory quality, or causal brand
value. Value for money and brand-associated price differences are related but
distinct quantities.

### 7.1 Methods to investigate

| Method | What it can estimate | Data required | Main limitation |
| --- | --- | --- | --- |
| Hedonic price regression | Conditional price differences associated with attributes and brands. | The planned product/price data, with comparable size, retailer, time, and selling conditions. | Omitted quality and correlated features affect estimates; a brand term is an association. [BLS](https://www.bls.gov/cpi/quality-adjustment/questions-and-answers.htm) provides a statistical application of hedonic regression. |
| Matched-product comparison | Price differences between products with similar measured attributes. | Products with overlapping category-specific features and selling context; composition, claims, format, and size are chocolate examples. | Check balance and reject comparisons without overlap; unmeasured quality remains a possible explanation. This is a proposed product application of [Rosenbaum and Rubin's matched-sampling method](https://dash.harvard.edu/entities/publication/73120378-8487-6bd4-e053-0100007fdf3b). |
| Choice-based conjoint / discrete-choice experiment | Consumer willingness to pay for features and brand identities. | A separately collected consumer study with varied prices and attributes. | Sampling, experimental design, a meaningful no-purchase option, and hypothetical-choice bias affect interpretation. See [Ben-Akiva, McFadden, and Train](https://eml.berkeley.edu/~train/papers/foundations.pdf). |
| Randomized brand-information experiment | The effect of disclosed brand information on preference or willingness to pay in the tested setting. | A new experiment holding the physical product constant while randomly varying brand information, with a monetary outcome if monetary premium is the target. | A blind taste ranking alone does not yield a monetary premium. Related food-category evidence is [Bronnenberg, Dube, and Sanders' private-label blind taste experiment](https://www.nber.org/papers/w25214). |

The last two methods require new consumer or experimental data, which is not
assumed to exist. They are research options, not additions to the initial build.

### 7.2 Candidate measures

In a log-price model with additive brand terms, a conditional brand-associated
price difference relative to an explicit reference brand is:

```text
brand_difference_percent = 100 * (exp(alpha_brand - alpha_reference) - 1)
```

This comparison needs adequate feature overlap and the same selling context.
With interactions, calculate the contrast at specified product attributes.
It is not proof of the price effect of renaming the same physical product.

A candidate adjusted-price indicator is:

```text
adjusted_price_indicator = log(benchmark_price / observed_price)
```

Define the benchmark using the same attributes and selling context, with an
explicit reference brand or stated brand distribution supported by the data.
Larger values mean a lower observed price relative to that benchmark. Use
held-out or out-of-fold predictions when evaluating products from the dataset,
so their own prices do not directly determine their benchmark.

A percentile within a defined comparable cohort could map the indicator onto a
0-100 score. This is a proposed scoring convention, not a universal scientific
definition of value for money. The cohort, benchmark, price basis, and uncertainty
must be visible, and scores would be relative to that cohort.

Do not label `observed_price - predicted_price` as brand premium. That residual
also includes omitted attributes, selling conditions, and prediction error.
Refitting without brand does not create a price with brand value removed:
correlated attributes can retain brand-associated differences.

For a simple choice model with linear price utility, an attribute's marginal
willingness to pay can be estimated as:

```text
WTP_attribute = -beta_attribute / beta_price
```

This uses consumer choices rather than listed prices. The ratio requires an
identified price effect, uncertainty estimates, and an appropriate utility
specification; a near-zero price coefficient makes it unstable. See the
[Goett, Hudson, and Train choice-study application](https://eml.berkeley.edu/~train/papers/RetailEnergy.pdf).

### 7.3 Research recommendation

First investigate an attribute-adjusted price indicator and conditional brand
comparisons using the planned category dataset, with matched-product checks and
uncertainty. Treat this as a price-position assessment. Consumer-value claims or
causal brand-information effects would need separately designed studies. Keep
the scoring implementation deferred until its definition and evidence are
agreed.

## 8. Acceptance scenarios for stages 1 and 2

The chocolate-specific scenarios below illustrate one category profile. General
category and plugin conformance scenarios apply across supported studies.

| Scenario | Expected behavior |
| --- | --- |
| Collection starts before a complete category schema exists. | Accept minimal study scope, identity, and provenance; preserve broad source information and images without requiring a feature taxonomy. |
| A product page contains an unfamiliar relevant field or claim. | Preserve the original source and source-specific information in the product bundle for later schema derivation. |
| A product is collected again with a changed price or claim. | Append timestamped source captures and collection history; preserve earlier evidence and identify the current JSON index. |
| A later schema normalizes a source field differently. | Create a versioned derived interpretation with evidence references; retain the original reported value and artifact. |
| A study uses a category whose comparison basis is price per item. | Preserve its original quantities and prices during collection; derive its analytical profile without requiring cocoa percentage, edible weight, or GBP per 100 g. |
| Another category is added. | Reuse the minimal collection/evidence envelope, then derive its own analytical profile, dataset, and validated model domain from collected information. |
| The same study request and evidence fixture are supplied through two supported harness adapters. | Both return valid collection envelopes and preserved raw bundles with compatible provenance meanings, original image/page handling, and explicit missingness; arbitrary source-specific fields remain supported. |
| A harness cannot retrieve packaging images requested by the study. | Preserve packaging attributes supported by available text, mark unsupported attributes unknown, and declare the missing image capability/evidence and coverage limitation. |
| The same variant appears at two retailers. | One product identity and two sourced price observations; no duplicate product-coverage claim. |
| A 200 g pack costs GBP 4.00. | Retain GBP 4.00 pack price and calculate GBP 2.00 per 100 g. |
| A listing supplies only a promotional price. | Preserve it as displayed price; do not invent a regular price. |
| Packaging is unavailable and retailer text omits Fairtrade. | Classify certification status as unknown. |
| A listing says "may contain nuts" but lists no nuts as an ingredient. | Preserve the allergen warning separately; do not infer a nut ingredient. |
| A visible packaging claim has no existing feature label. | Preserve the original image/text, claim, and source context for later schema derivation and classification review. |
| A certification appears only in one brand. | Flag identification/support limits; do not claim a separately established causal certification premium. |
| A dataset contains repeated offers and related sizes. | Keep product families together during held-out validation. |
| A brand tests a supported new product. | Return price, prediction interval, feature references, and the selected model/context. |
| The design has an unseen brand or unsupported feature combination. | Use a validated, labeled fallback where available or report insufficient support. |
| A user supplies a proposed selling price. | Show its currency and percentage difference from the estimate. |
| A user supplies a GBP pack price while the model target is GBP per 100 g. | Convert consistently and compare pack price with the implied pack estimate on the same price basis. |
| A user omits optional selling context. | Display and use a validated documented default, or require context if none exists. |
| No reliable model passes the study's release criteria. | Show data/validation limitations and do not claim a supported price estimate. |

## 9. Decisions still to make

- The category boundaries and included product forms for the current UK chocolate
  study, and the category/market for subsequent studies.
- The first supported agent harnesses, adapter packaging, transport, capability
  mappings, and result/evidence delivery.
- Which sources are accessible and suitable, and what evidence can be retained
  under their access and usage conditions.
- The collection window and source/retailer coverage.
- The analytical category schema derived after broad collection, comparable
  groups, and exact quantity/consumer-price basis before modeling.
- Coverage targets, extraction review plan, and numerical model release criteria.
- The delivery surface and implementation stack.
- Whether stage 3 will define value for money as an adjusted-price comparison or
  include separately collected consumer utility/quality evidence.

These decisions do not block documenting the intention. They must be resolved
before the corresponding implementation or release commitment.
