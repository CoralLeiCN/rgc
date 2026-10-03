# RGC Pricing Review: hackathon proposal

Status: proposed experience for a two-person team, updated 3 October 2026.
The primary audience is retail category managers, buyers, and pricing teams,
including retailers such as Tesco. Brand new-product testing is secondary.
Collection and a schema-based silver snapshot exist; reviewed modeling inputs
and a fitted pricing model remain to build. The
[real collection explorer](visuals/collection-explorer.html) now connects 3,743
listings, 2,134 price observations and 103 tracked traits to a dynamic matrix,
an observed-price point cloud and an evidence panel. The snapshot admits zero
rows for training. See [integration status](collection-integration.md).

Latest visual direction: a LiDAR-style
[price point cloud](layered-price-landscape.md) with 500 fictional products.
Colored samples reveal stacked trait contributions, with an exact selected-product
breakdown and scan-slice/peel interactions. White anchors show full benchmarks;
actual and proposed prices share the same vertical scale. The
[interactive point cloud](visuals/layered-price-landscape.html) is the latest
review artifact. The conditional surface and fit views below remain analytical
companions. All current visual fixtures are fictional; layer samples are display
marks, not additional product records.

## Product promise

**Test a price. Explain the decision.**

A category manager selects a SKU, checks its position against a declared market
benchmark, tests a proposed selling price, and documents evidence supporting or
challenging the decision. Insufficient evidence is a valid outcome. Tesco is an
audience example, not a claimed customer or data partner.

The [project brief](intention.md) and [specification](spec.md) define the scope.
Value-for-money scoring and brand-premium rankings remain deferred research.

## Main visualization: 3D Price Terrain

Use a 3D conditional price surface above a product-trait matrix, with a persistent
price-review panel on the right. Two numeric traits locate a product horizontally;
height shows price. Its benchmark lies on the selected-context surface, while
current and proposed prices connect vertically to it. Highlight the conditional
fitting curve through the selected product and show a precise 2D cross-section.

An all-trait fit view uses each product's full-vector benchmark as x, a chosen
trait as y and observed price as z. Its z = x plane is the equality reference,
so all model inputs remain represented in each benchmark. It is not another
regression fitted through the predictions. The matrix exposes exact attributes.

Keep visible traits separate from model inputs and the benchmark reference
context. Changing axes does not refit the model. For a conditional terrain, hold
other traits explicitly fixed and show matching-context peers. Broader comparison
uses the all-trait fit view. Brand, retailer, claims and missing evidence remain
inspectable in the matrix and evidence panel.

The [3D design plan](3d-price-landscape.md) defines the math, interaction, tooling
and next steps. The [interactive 3D concept](visuals/price-terrain.html) uses
108 fictional products and a hand-authored function, with no fitted model or
calibrated intervals. Earlier [research](visualization-research-plan.md) and the
[reference board](visuals/visualization-reference-board.html) retain relevant
multidimensional matrix and animation examples.

## Optional analytical lens: the price-justification map

Each eligible SKU occupies one point in a comparable cohort:

- Horizontal axis: model-estimated benchmark, in GBP per 100 g for this study.
- Vertical axis: observed price, on exactly the same unit/tax/promotion basis.
- Diagonal: observed price equals benchmark. Distance expresses a price gap,
  not a causal brand premium, margin, or universal overpricing judgment.
- Selection: show that SKU's prediction interval, current-price circle and
  proposed-price diamond. Use its actual interval rather than a decorative
  global confidence band.
- Color: retailer or declared segment; shape and text distinguish observed and
  proposed values. Keep marker sizes equal unless a meaningful quantity exists.

The benchmark must declare its reference selling context. An estimate for the
observed retailer and a pooled-market estimate answer different questions.
Existing training products require held-out or out-of-fold estimates, grouped
by related product family. Their own outcomes must not directly establish the
benchmark against which they are judged.

The signature interaction is a **relative-position lens**: retain each product's
identity and horizontal benchmark position, but transition the vertical scale
from observed price to `(observed / benchmark - 1) * 100`. The equality diagonal
becomes a zero-gap reference line. This helps the reviewer distinguish a high
ticket price from a high price relative to measured attributes and the chosen
context. It is an explicit analytical view, not a quality score.

Then edit the proposed pack price. Convert it to the displayed unit basis and
move only the proposal marker. The benchmark and its interval stay fixed. Show
current price, proposed price, change from current, and gap to benchmark as
separate quantities. A proposal inside an interval is not proof of commercial
acceptability or expected shopper response.

## Linked views that complete the decision

### Comparable range and price ladder

Selecting a SKU filters a declared comparison set by product form, measured
attributes, size, selling context, and usable evidence. Show horizontal rows with
each peer's price and the selected SKU's current/proposed markers. Keep matching
rules, remaining differences, and missing fields inspectable.

For the retailer's own assortment, connect each SKU's current and proposed price
in a before/after price ladder. Highlight changed ordering and compressed or
widened gaps between retailer-defined tiers. Tiers need explicit definitions;
prices do not establish quality. Use pack prices for a shelf-ticket question and
normalized prices for a unit-value comparison, with a visible basis switch.

This describes price relationships. Forecasting customer substitution,
cannibalization, demand, or margin requires additional data and validation.
Without an actual retailer assortment, label the set as sampled public listings
or an illustrative range.

### Evidence for the decision

Use a compact panel with three parts: supporting evidence, challenging evidence,
and unknowns. A model residual is not a reason by itself. Pair it with named
comparables, observed attributes, explicit references, and source dates.

For a feature explanation, show a supported pair of predicted prices with the
changed feature and fixed context stated. Independent feature contrasts are not
additive shares of the ticket price. Keep uncertainty and identification limits
visible when attributes are sparse or correlated.

Export a short pricing-review note: selected SKU, current/proposed price,
benchmark and interval, comparison basis, named comparables, evidence links,
limitations, model version, and the reviewer's rationale. This records a draft
decision; it does not execute or publish a price change.

## Visual direction

Use an editorial header, a dark navy analytical workspace, contour lines,
tabular numerals, a turquoise fitting curve and violet proposal. This direction is
inspired by inspected RGC material from 2023; the current homepage was inaccessible.
Exact proposed tokens and reference limits are documented in the research plan.
Motion should preserve product identity across filtering, dimension changes and
price scenarios. The main page combines an overview with precise comparisons.

```text
RGC PRICING REVIEW      Cohort | Price basis | Context | Snapshot | Model status

3D PRICE TERRAIN                               SELECTED SKU
Two trait axes + price elevation               Current / proposed pack price
Surface, fitting curve and product price gaps  Benchmark + interval if validated
[Trait terrain] [All-trait fit]                Supporting / challenging / unknown
                                               Named comparables and sources

SELECTED FITTING CURVE / PRECISE CROSS-SECTION
PRODUCT × TRAIT MATRIX                         [Save review note]
Exact values, claims, unknowns, sortable columns and pinned peer comparisons
```

The earlier [interactive visual sketch](visuals/pricing-review-concept.html) demonstrates
selection, the relative-position lens, proposed-price changes, and a linked
comparison view. All figures are labeled illustrative. It uses fictional products
and preset demonstration intervals; no model, Tesco data, real evidence
verification, or commercial recommendation is implied.

## Hackathon scope and delivery

Build one UK chocolate-bar cohort, one price-review scenario, and the linked
3D terrain, all-trait fit view, comparison matrix and evidence panel. Make the
similarity atlas, full price-ladder extension and note
export secondary to completing the core path. Decide source/feature eligibility
and numerical release criteria from reviewed data before model evaluation.
The 3,743 source listings are not 3,743 independent model-ready products, and a few
presentation examples do not establish a sufficient training set.

| Work | Person A: data and model | Person B: visualization |
| --- | --- | --- |
| Define | Review cohort, families, features, price/weight basis and benchmark context | Agree fields, units, support states and selection behavior |
| Build | Produce derived features with evidence; fit and validate a baseline/regression; expose supported conditional slices | Connect 3D surface, fitting curve, all-trait view and comparison matrix to real data |
| Validate | Evaluate on held-out families; inspect error, interval coverage and sparse inputs | Verify units, stable benchmark, missing-data states and source drill-down |
| Present | Freeze versioned model/data and a reproducible scenario | Rehearse and record the working decision flow |

The model/UI contract needs SKU/family identifiers, observed price, quantity,
normalized price, benchmark context/type/version, prediction interval and level,
out-of-fold/hold-out status where relevant, proposed price, both price deltas,
eligible peers, evidence references, and supported/experimental/unsupported
status. Proposed price is a scenario input, not a model feature or training label.

Use the existing Python collection tools plus a small modeling layer and a local
browser interface. The 3D concept uses Plotly.js and plain JavaScript with a
vendored WebGL bundle. React, TanStack Table and Motion remain optional for a
larger application. Preload evidence and freeze the model artifact
for the presentation. If a reliable model is not achieved, show a clearly labeled
experimental result or an evidence-based peer comparison without an invented
model interval.

## Challenge alignment and two-minute demo

The [EAT_HACK brief](https://eat-hack.notion.site/Eat-Hack-Challenge-Brief-3dfeee0bbcf3807f9183d1787cbce382?pvs=74)
positions Retail Futures around decisions for retailers and brands. Its scoring
weights are originality/thinking 30%, build/execution 30%, value/relevance 25%,
and demo/communication 15%. Emphasize a working, evidenced pricing decision.

| Time | Demonstration |
| --- | --- |
| 0-15 seconds | State one retailer's proposed SKU price change and why it needs review. Label an invented scenario clearly. |
| 15-40 seconds | Orbit the price terrain, select the SKU and reveal its fitting curve and fixed trait context. |
| 40-70 seconds | Edit the proposed pack price. Show the moving proposal and fixed benchmark; switch to all-trait fit to include broader product contexts. |
| 70-100 seconds | Open a real comparable and source evidence; show a material unknown or conflicting observation. |
| 100-120 seconds | State what the evidence supports, what remains uncertain, and which validation was performed. |

The brief requires submission by 17:30 London time, a video no longer than two
minutes, and publicly accessible submission links. Disclose substantial work
that predates the event. Live deployment receives no extra judging points.
Publication and repository visibility changes are separate actions.

## Acceptance checks and limits

- Unit prices use confirmed net edible weight. Shipping weights, promotions,
  and conflicting tax bases are reviewed before eligibility.
- Missing attributes remain unknown; observed claims are not verified quality.
- Family grouping prevents validation leakage; benchmark context and reference
  choices are visible and valid for the selected SKU/retailer.
- Proposed-price edits leave benchmark inputs, estimate and interval fixed.
- Absolute and relative views agree arithmetically; change from current price
  and gap to benchmark remain distinct.
- Peer sets and assortment tiers have inspectable definitions. Public coverage
  is not a complete Tesco assortment or a sales-weighted market. There are no
  assumed cost, sales, elasticity or margin inputs.
- Explanations link to source facts or actual model results, and insufficient
  evidence remains a valid outcome.
- Replace the concept's synthetic figures with reviewed data and measured model
  results before claiming an operational pricing tool.
