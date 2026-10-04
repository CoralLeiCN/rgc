# App specification

This document defines the application requirements for the
[app intention](intent.md). The [shared specification index](../spec.md) connects
all three feature specifications. The [data specification](../data/spec.md)
owns raw preservation, processing and analytical data contracts; the
[model specification](../model/spec.md) owns numerical methods, model validation
and release requirements. The [lifecycle plan](../lifecycle/plan.md) records
implementation and verification evidence. Original section numbers are retained
so references to moved requirements remain recognizable.

### 2.3 Review a retailer price or test a newly designed product

1. A retailer selects an existing SKU or proposed listing, or a brand describes
   a proposed product, using the model's feature schema.
2. The user selects supported market, product group and pricing context.
3. The model estimates a price and prediction interval, with feature comparisons
   and warnings about unsupported inputs.
4. If the user supplies a proposed selling price, compare it with the model's
   estimate in both currency and percentage terms.

This is a test against observed market pricing. It does not estimate demand,
profit or the price that maximizes revenue; those quantities require other data.

The primary delivery audience is retail category managers, buyers, and pricing
teams. Display evidence supporting and challenging a decision and allow an
insufficient-evidence outcome. A target retailer such as Tesco is a user persona,
not a claim that its internal data or full assortment is available.

For an existing product used in model development, obtain a held-out or
out-of-fold benchmark with related product families kept together. Changing only
the proposed price must not refit the model or change its benchmark. Keep
within-retailer estimates distinct from pooled-market or other reference-context
benchmarks, and display the chosen context. Retailer price-ladder views show
recorded/proposed price relationships, not predicted substitution or sales.

#### Synthetic product price demo

The user authorized the published `lightgbm_without_brand` fixture for the web
form. [The serving guide](../data/analysis/web-fixture-pricing.md) owns the immutable
reference, accepted keys, missing-evidence semantics and attribution validation.
`POST /api/predict-price` uses five supported inputs and explicit single bar pack
scope, returns synthetic GBP/100 g and GBP/pack with exact stored-path field
SHAP, and rejects extra keys including proposed price. It retains the fixture's
historical `regular-consumer-price-1` basis; the current study's displayed-price
proxy does not rewrite that artifact. The Node implementation is verified
against LightGBM 4.6.0 native predictions and each contribution.

The form exposes model reference, signed field/family allocations using
[section 5.2.1 of the model specification](../model/spec.md#521-trait-and-trait-family-percentages-of-predicted-price),
raw log contributions, excluded schema fields and synthetic status. No
real-data interval or causal feature premium is claimed. Changing modeled
inputs cancels stale work; proposed price never enters prediction. Local model
files must pass immutable hash/identity checks before serving; missing or corrupt
files return unavailable. Inputs remain local scenarios and do not enter training.

## 6. Retailer price review and new product price test

### 6.1 Inputs

Require category, market, comparable group, applicable selling unit/quantity
information, and the features required by the selected model. Use the same
category profile, vocabulary, and units as training.
Unknown values remain unknown. Optional inputs include an observed brand, a
supported retailer/time context, and a proposed selling price. When context is
omitted, use and display the model's documented default within its validated
domain. If no such default exists, require the relevant context before testing.

The proposed selling price uses the study's currency and declared selling unit,
on the same tax and promotion basis as the selected model. For UK chocolate this
is a GBP pack price for the described pack. Compare it with the corresponding
selling unit estimate; convert both prices consistently for comparisons of
normalized prices.

For an unknown brand, a proposed fallback is a separately fitted and validated
model without brand terms. Label it as a market benchmark with no specified
brand; other features can still absorb differences associated with brand. Use
the fitted term and state the reference for a known brand. Handle unsupported
brands, retailers, categories and feature levels explicitly; fabricated brand
coefficients or silent mapping to references are invalid.

### 6.2 Outputs

- Estimated price in the study's currency and target units, with the corresponding
  selling unit price and estimate type stated. For UK chocolate, this is GBP per
  100 g and the implied pack price.
- A prediction interval on the same price basis.
- Feature contrasts in the selected context relative to stated references.
- Individual trait contributions, one signed percentage of the final predicted
  price per modeled trait family, and a separate model reference percentage,
  using [section 5.2.1's allocation and availability checks](../model/spec.md#521-trait-and-trait-family-percentages-of-predicted-price).
- When supplied, difference between proposed and predicted prices: `proposed - predicted`, and
  `100 * (proposed / predicted - 1)`.
- Data/model version, comparable group, and evidence/validation context.
- For an existing SKU, its current price and the held-out/out-of-fold status of
  its benchmark; a separate proposed-price marker must leave that benchmark fixed.
- For a retailer range review, selected comparable products and before/after
  price gaps, with the price basis and available assortment coverage stated.
- Flags for missing inputs, unseen levels, poorly supported combinations, and
  extrapolation beyond observed ranges.

Reject mathematically invalid inputs. For unsupported valid inputs, either
decline to produce a supported prediction or provide an explicitly experimental
estimate, depending on the model's documented domain policy. A design using
individually familiar features can still be an unsupported combination.

### 6.3 Vercel evidence explorer and product configuration

The selected application architecture is a Next.js App Router frontend and
same-origin Route Handler backend deployed together on Vercel. The
[architecture and API contract](../vercel-architecture.md) defines interfaces,
limits and deployment; `apps/web` is the deployment root. Verification and
hosted-release status belong to the lifecycle plan. A previous deployment's
checks do not establish that a later local implementation is hosted or visually
verified.

The application consumes Gold inferred `gold-inferred-5b539b9c4adbb011a40d7792`
at immutable revision `812a03a5faaced471a2a20f4c389865ed5675826`, pinned by
`apps/web/collection-dataset.json`. The adapter verifies every managed file,
the authoritative Parquet `record_json` logical hash and nested Gold training
provenance. It loads the copied schema, profile, mappings and model design and
validates every product before emitting private server-side JSON. The 2,159
accepted trait additions retain source evidence, methods and review states.
The immutable export retains `regular-consumer-price-1`, with zero stored
source-eligible inputs; the current loader exposes all 2,134 candidates.
The current-price training study has its own policy. The app build rejects
collection JSON that differs from its immutable pin. The reader checks the verified
snapshot's schema/catalog and typed constraints independently of current
training identity and target-policy requirements. A derived manifest hashes
the server snapshot and evidence shards. Refreshes are explicit preparation and
deployment operations; functions do not download or process Hugging Face data
on each request. Original captures and machine contracts remain unchanged.

Read-only GET routes provide schema definitions, paginated filtered source
listings, bounded terrain coordinates, price analysis, complete
single-listing evidence and an ordered comparison of up to four listings.
`POST /api/extract-traits` is a separate model-assisted candidate-extraction
operation. It sends explicitly submitted inputs to a configured provider but
performs no dataset, evidence-review or draft persistence writes. The application
requires no database. Provider configuration is required only for extraction.

The configurator renders one extraction panel and one prediction panel with
distinct component identities. Draft edits preserve selected photos. Explicit
listing-copy and reset actions clear both panels' prior session state.
Extraction compares a supplied Origin to the request protocol and Host header,
falling back to the URL host when Host is absent. A foreign origin receives 403
before inputs are dispatched to a provider.

#### Cohort, families and evidence

Schema-driven conditions use types, units, vocabulary, numeric bounds and
known/unknown/conflict/not-applicable states. Conditions combine with AND and
share the cohort across the terrain, observed-price analysis, matrix and
comparison. Source, role, product-type, search and price-availability controls
remain available. Missing attributes mean unknown, never false or zero.

The schema contains flat families derived from each field's `group`. Families
organize navigation and evidence comparison; they are not synthetic composite
traits or related-product validation families. Multiple families can expand
simultaneously in the matrix and shortlist, sharing expansion and trait settings.
Collapsed summaries count every field's evidence state, including fields hidden
by search, per-family limits or the pricing-input toggle. Pinned traits remain
visible without duplicate columns. Selected model predictors are identified
separately. Coverage is not quality, model influence or a price contribution.

The workspace is branded Piece of Cake Pricing, with subtitle FMCG Pricing made
easy. The four top summary cards are removed. Explanations sit in question-mark
controls beside headings, accessible on hover, keyboard focus and tap,
dismissible by Escape/outside click and positioned outside clipping panels.
Actual values, labels, errors and the prototype-score disclosure remain visible.
Family cards show trait counts and evidence coverage. Clicking or activating a
card with the keyboard opens its member traits; hovering or focusing the card
does not open a popover. Member traits expose types/units and definition help.
Leaf-trait actions configure filters, color or numeric height.

Terrain hover details render as HTML with explicit contrasting colours and stay
inside the chart. Product points show their name, observed or proposed GBP/100g,
demo trait score and selected height trait with its unit. Layer and gap details
remain available. Leaving the chart, starting a drag or changing its data/camera
clears the tooltip. Hover content must not intercept product selection or orbit
gestures.

#### Primary terrain and shared prototype score

The primary chart is a layered 3D terrain with X = observed GBP/100g,
Y = trait-derived prototype score on a 0–100 scale, and Z = one selected numeric
leaf field in its original units. The score is explicitly disclosed as a demo,
not a fitted pricing prediction or a quality rating. Observed rows and configured
products use the same `trait-demo-1` recipe in `apps/web/lib/trait-demo.ts`:

- Base 20 only when at least one recognized input is known.
- Cocoa percentage multiplied by 0.30, with valid input 0–100 and up to 30 points.
- Ten points each for explicit organic, Fairtrade, bean-to-bar, single-origin
  and gift-pack claims; explicitly absent claims contribute zero.

Missing, conflicting, truncated and invalid scoring inputs are omitted, not
inferred absent. With no recognized inputs the score is null. Names, prices,
review state and cohort membership do not add score points. This prototype does
not alter source review, model eligibility, model-design features or the
requirements for supported price testing. The score is never manually editable.

Displayed prices in this explorer remain observational evidence. The current
chocolate study uses them as the regular-price proxy under
`current-consumer-price-1`, with the assumptions and requirements in the
[model specification](../model/spec.md#current-chocolate-study-price-target).
Historical regular-price studies retain their original target contract.

`GET /api/terrain` applies the common cohort and core/full price range, returning
exact price/score/Z rows and color-category shares. Default sampling is bounded
to 1,000 rows, with a 2,000-row maximum and deterministic selection when needed.
The response reports the matched/priced/complete counts, sampled status,
below/above-range counts and missing-score/missing-Z counts; missing coordinate
counts are within the displayed range and may overlap. A missing score or Z
excludes the listing from terrain geometry, not from the matrix or independently
computed observed-price analysis.

Only an individual leaf field can supply color: numeric/integer, enum, boolean
or string-list. Parent families are navigation containers, not color bars or
height indices. Numeric color values use five equal-width bands calibrated to
valid known values in the immutable full snapshot; cohort filtering does not
recompute their boundaries. A categorical single value gets its whole visual
share. A string-list field divides its share equally among distinct values.
Unknown, conflict, not-applicable, truncated and explicitly empty-list states
remain distinct. Z accepts only a single numeric field in raw units; family
aggregation and normalized family means are rejected.

The browser builds a 24 × 24 surface grid in price/score space using positive
local weights to average neighboring Z values. Unsupported cells stay open;
weighted heights do not overshoot the contributing observed Z values. Smoothing
changes the surface only. Layers divide the height above the explicit
`min(0, observed Z)` baseline using local category shares. They are ordered by
weighted median Z, with up to eight named/state layers plus Other categories.
Layer thickness is illustrative composition, not causal pricing influence,
model attribution, cost or measured product quality. Exact dots retain their
original price, calculated score and raw Z; they are never snapped to the smooth
surface. Legend highlighting preserves the underlying coordinates and cohort.
A 2D projection with explicit selection provides a fallback when WebGL fails.

A price cut is an optional vertical plane at a selected GBP/100g value. The user
can move it with a keyboard-accessible slider, keep the higher or lower prices,
face the slice and restore the full cake. Surface triangles are clipped at that
plane with linear interpolation of their upper and lower layer boundaries;
new vertical faces close each layer. Unsupported areas remain gaps. Slicing
reuses the original smoothed geometry and its layer order rather than refitting
on the retained products. Camera rotation does not rebuild the geometry.

A matching SVG section shows layer height against demo trait score at the exact
selected price, also in 2D mode. The chart hides points on the removed side and
discloses the retained count; their original coordinates, cohort analyses and
source data are preserved. Price and height scales use the full terrain and
configured draft, so moving the cut does not rescale the cake. Empty sections
explain that the selected price lacks surface support. Slider prices stay within
the displayed price domain, rounded outward to whole pennies.

Retired chart components, the legacy points endpoint and ID-seeded score mode
are removed. Only the current terrain and its 2D fallback are supported.

#### Local product draft and candidate extraction

The right column provides editable name, proposed GBP pack price, edible weight
and schema-typed traits. Families expand independently and can be searched.
Blank traits remain unspecified; numeric zero is retained where permitted;
enum/list vocabulary and numeric bounds are validated. Price is normalized from
the draft's own pack price and edible mass. A proposed-price slider complements
the exact numeric input and expands to include larger typed prices. Price edits
do not change the calculated score. A read-only output and rule breakdown expose
the score and known-input count.

An explicit action can copy a selected listing's known, untruncated attributes
and usable price/weight from the same observation. Ordinary source selection
preserves draft edits. Source evidence stays accessible in a collapsed section.
The marker requires valid price, weight, a known score and the selected numeric
Z trait; invalid or missing coordinates suppress it. Out-of-range draft prices
can extend display axes without changing the observed cohort/range or clamping
the draft onto an invented price. Drafts never enter source listings, terrain
smoothing, gap calculations, brand statistics or model training.

The extractor accepts a description of at most 12,000 characters and/or up to two
PNG, JPEG or WebP images. The browser accepts readable originals of at most
20 MiB and 40 megapixels each, resizes as needed to at most 2,400 pixels on the
longest edge and compresses each prepared image to at most 1 MiB.
`POST /api/extract-traits` receives JSON
`{description, images?: [{mimeType, data}]}`, where `data` is canonical base64
without a data-URL prefix. Legacy single `image` requests remain accepted. The
server permits 2 MiB per image within the combined decoded image budget of
2 MiB; the total JSON body cap is 3,000,000 bytes. Validation checks body limits,
image signatures and field values. Both provider adapters receive every
submitted image. The response
contains provider/model metadata, candidate `{key, value, evidence}` traits and
warnings. Unsupported or schema-invalid candidates are omitted; missing values
are never filled automatically. Generated candidate claims are not independently
verified source facts, and neither extraction nor applying them grants model
eligibility.

**Use example photos** loads the supplied Well&Truly Fudge & Brownie Oat M!lk
Chocolate, 30 g, front and back photos from
`apps/web/public/examples/well-and-truly/front.jpg` and `back.jpg`. The repository
retains their original JPEG bytes and checks their SHA-256 hashes through the
public asset manifest; browser preparation creates temporary copies. Users can
select the example or add/remove their own photos within the two-image limit.
Uploads append when room remains and replace the selected pair when two are
present. Successful example preparation replaces the photos and clears the
description. Example selection does not call an extraction provider or prefill
candidates. **Extract traits** submits the current inputs. Sample photos are
app demo assets outside the immutable collection and training snapshots.

Extraction instructions preserve label scope and qualifiers. The sample's
43% minimum cocoa statement applies to its chocolate component and cannot be
emitted as an exact whole-product cocoa percentage. “Fairly traded” does not
establish a named Fairtrade certification. Extraction remains subject to review,
and the existing score stays unavailable when no recognized scoring trait is
supported by the selected evidence.

Image previews and description inputs remain local until extraction is requested.
The user reviews checkboxes and evidence, then explicitly applies candidates.
Apply merges into the latest draft, replacing only checked matching inputs;
name and edible weight map to their top inputs and proposed pack price is
unchanged. The score recalculates from applied traits. Async results never
modify edits on arrival. Editing extraction inputs, Reset, source import or
unmount cancels/discards stale extraction work; previews release their object
URLs. Reset/source import clear the extraction session. Drafts and candidates
have no application persistence, and errors never trigger fabricated fallback
extraction.

The extraction route supports server-configured OpenAI, an authenticated HTTPS
Codex bridge, or `codex-local` on a Next.js server running on the laptop. Local
development selects `codex-local` when no explicit provider, bridge URL or OpenAI
API key is configured. Direct local mode reuses the installed CLI's ChatGPT OAuth
sign-in, forces the ChatGPT authentication method, admits one extraction at a
time and aborts after 90 seconds. It shares the bridge's disposable files,
disabled tools and schema validation. Vercel rejects direct local mode; hosted
Codex access uses the HTTPS bridge. Provider credentials remain server-side.
The bridge is a separate laptop process intended for the requested Tailscale
connection and limits work to one extraction at a time. Missing configuration
returns 503 with a setup message. Live validation status is recorded in the
[lifecycle plan](../lifecycle/plan.md#proof). The extraction service is separate
from the locally connected synthetic pricing fixture and the teammate's
research model.

#### Observed-price analysis and future model boundary

The read-only analysis endpoint applies cohort filters to all matching listings,
independent of matrix pagination or complete terrain coordinates. Only positive
displayed GBP/100g with known same-observation weight and no latest-price
conflict enters price analysis. Core-range bins lie within full-cohort
Q1 - 1.5 IQR to Q3 + 1.5 IQR, clipped to observed limits; Full includes all usable
prices. Tail counts remain explicit and zero-IQR Core falls back to Full.
Summary and brand statistics always use the full priced cohort.

The gap finder reports empty interior bin runs bounded by occupied bins, with
adjacent-bin counts and at least 20 in-range priced listings and five distinct
in-range prices. Selecting a gap highlights its price interval on the terrain;
changing cohort/range invalidates the selection. Gaps describe collected supply
at the stated resolution, not demand, opportunity or a recommended price.
Brands with at least three priced listings are ranked by median observed price,
with percent difference from the cohort median and counts beyond full-cohort
Tukey fences. R-7 quantiles weight each seller listing equally. Unknown brands
remain in totals but are unranked; rankings are capped at 30 with exclusions
reported. Higher price positioning does not imply sales, profitability, quality,
a model residual or causal brand premium.

The interface preserves snapshot/review/model-readiness status. An unreviewed
observed price, selected predictor or prototype score is not a fitted benchmark.
Review writes,
database persistence, model fitting and supported price recommendations are
outside the current explorer contract.

The teammate owns model development. A future hosted adapter must agree on
versions, listing/observation identity, price/score basis and support before it
can replace the current demo recipe. That integration is not part of this change.

## 8. Acceptance scenarios for stages 1 and 2

These application scenarios describe supported price testing. The
[model acceptance scenarios](../model/spec.md#8-acceptance-scenarios-for-stages-1-and-2)
define the validation required before supported estimates can be claimed; the
synthetic demo retains its explicit limitations. The
[data specification](../data/spec.md) owns collection and processing acceptance
scenarios.

| Scenario | Expected behavior |
| --- | --- |
| A brand tests a supported new product. | Return price, prediction interval, feature references, and the selected model/context. |
| A retailer reviews an existing SKU included in model development. | Use a held-out or out-of-fold benchmark with product families kept together; show its current price and evidence. |
| A retailer changes only a proposed price. | Keep model inputs and benchmark fixed; update its gap and position in the selected range. |
| Public price data is available without sales or cost data. | Report price positioning and observed/proposed range gaps; do not fabricate margin, elasticity, revenue lift, or cannibalization. |
| A user supplies a proposed selling price. | Show its currency and percentage difference from the estimate. |
| A user supplies a GBP pack price while the model target is GBP per 100 g. | Convert consistently and compare pack price with the implied pack estimate on the same price basis. |
| A user omits optional selling context. | Display and use a validated documented default, or require context if none exists. |

## 9. Decisions still to make

- Hosted preview verification and access configuration for the selected Vercel
  application; the Next.js frontend/backend stack is decided.

Resolve these decisions before the corresponding implementation or release commitment.
