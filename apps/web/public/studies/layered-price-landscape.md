# Price point cloud

Latest design, 3 October 2026: a LiDAR-style point cloud containing **500 fictional
products**. It preserves the stacked-bar/lasagna idea: each trait has a color,
and its contribution occupies a vertical band above the preceding layers. Small
colored points replace the earlier solid surfaces. The price-review panel keeps
the corresponding exact stacked bar and component values visible.

- [Interactive point cloud](visuals/layered-price-landscape.html)
- [Static geometry preview](visuals/layered-price-preview.png)
- [Vector preview](visuals/layered-price-preview.svg)

The HTML uses a local Plotly dependency and can be opened directly. The PNG/SVG
are projections of the actual fixture geometry, not browser screenshots. This is
a LiDAR-inspired visual treatment of product data, not a physical scan or a map
of geographic locations.

## Visual encoding

| Element | Meaning |
| --- | --- |
| Ground-plane location | Two-dimensional projection of six trait-contribution values |
| Colored vertical band | One trait's contribution to the synthetic price output |
| Neutral foundation | Declared reference price |
| White product anchor | Full benchmark, in GBP per 100 g; one per product |
| Selected colored column | The selected product's contribution stack |
| Selected hollow marker | Full benchmark for that product |
| Selected white/violet marker | Actual price / proposed price on the same vertical unit scale |
| Vertical dashed connector | Gap between the benchmark and the proposal |

A vertical product profile corresponds to the stacked-bar reference. Each color
retains its meaning across products. The ground plane provides two layout
coordinates; height is cumulative price, with the full benchmark at the top.

There are exactly 500 product records, with IDs P001–P500. Each nonzero layer gets
1, 3 or 6 display samples, spaced evenly up its vertical span at the product's
unchanged ground-plane location. At the default top-four setting and density
three, there are **7,674 colored layer samples and 500 benchmark anchors**.
Selected-product markers and lines are additional overlays. A product count and
a separate layer-sample count are shown above the scene. More samples do not
mean more products, observations or model evidence.

## Grouping and geometry

Group by similarity of model explanations: the prototype computes two principal
components of centered price-contribution profiles. All six contributions share
currency units, so they are not rescaled to unit variance. The layout emphasizes
larger variations in model contribution. Actual and proposed prices are not
inputs to that layout. Positions stay fixed when top-N, density or proposal
controls change.

Projection is approximate and can hide differences. There is no connecting mesh,
interpolation across products, jitter or smoothed price surface. The colored
returns sample each product's own exact stack. The 3D view helps explore the
cohort; the breakdown provides the exact comparison for a retailer's review.

## Implemented interactions

- Orbit/zoom with 3D, side and top camera presets.
- Move a scan slice across the cloud; jump the slice to the selected product.
- Click a layer chip to hide higher trait bands. Hidden contributions still
  count toward the benchmark, and white anchors retain their full height.
- Show the top 3–6 traits; preserve omitted contributions in an Other layer.
- Change sample density and dot size without changing the product records.
- Select a product from a colored point, benchmark anchor, selector or bar chart.
- Inspect its complete stack, exact contribution amounts and price gap.
- Change proposed unit price while the map coordinates and benchmark stay fixed.
- Restore the full cloud or reset the proposal to the actual fixture unit price.

Top-N is ranked once by mean absolute contribution across the synthetic cohort.
Trait colors remain stable. The baseline has a separate neutral color. The
selected breakdown always shows the full stack, even when upper layers are hidden
in the point cloud. Eight representative bars link the cloud to the original
stacked-bar reference. All 500 products are selectable.

## Fictional records and contribution semantics

A fixed seed (20261003) generates 500 unique six-trait profiles across five
fictional brands. The traits are cocoa percentage, pack weight, sugar per 100 g,
organic status, nuts and single origin. Pack weights range from 60 to 100 g,
cocoa from 50 to 80%, and sugar from 5 to 15 g per 100 g. These are illustrative
fixtures, not reviewed products from the Hugging Face corpus. Brand is a display
label and is not an input to the price function.

The concept reuses the earlier hand-authored log-price function, evaluated in
pounds. It computes exact six-feature Shapley values for the **price output**
against one explicitly declared reference product. Contributions plus reference
therefore sum to the benchmark in pounds. Actual prices are fabricated deviations
around that benchmark. This prototype has no fitted model, causal interpretation,
verified trait premiums, retailer price feed or uncertainty estimate.

Reference: 50% cocoa, 100 g pack, 15 g sugar per 100 g; organic, nuts and single
origin all false. The synthetic function is monotone relative to this low-price
reference over the fixture domain, so displayed thicknesses are nonnegative.

That property must not be assumed for a real model. Negative attributions cannot
be represented as negative physical thickness. Real signed explanations need
separate positive/negative stacks or a signed waterfall with the same colors;
retain the net benchmark separately. Never take absolute values or discard
negative terms to obtain attractive layers.

The exact enumeration evaluates 64 coalitions for six inputs. This method does
not scale unchanged to hundreds of traits. A production model needs a suitable
explainer, documented reference and correlation treatment, and reconciliation
checks. Many traits can feed the map; top-N controls how many colors are legible.

## Implementation and review

The rotation investigation reduced the default scene from 17 traces to five
opaque batches and set WebGL pixel ratio to 1. Camera updates do not regenerate
geometry, end-of-drag clicks are ignored, and rapid scene updates coalesce.
All 500 product anchors and 7,674 default layer samples remain. See
[rotation investigation and real-data integration](collection-integration.md).
The [real collection explorer](visuals/collection-explorer.html) is now available
beside this fictional design study.

The cloud uses local [Plotly scatter3d](https://plotly.com/javascript/3d-scatter-plots/)
marker traces. A few lines highlight only the selected product's stack and price
gap. SVG stacked bars and the product breakdown remain usable if WebGL fails.
The model/geometry and interface code are separate. The earlier 108-product
single-surface prototype retains its original fixture set.

Regenerate the static preview from the shared model:

```sh
node docs/visuals/render-layered-price-preview.cjs
python3 -c 'import cairosvg; cairosvg.svg2png(url="docs/visuals/layered-price-preview.svg", write_to="docs/visuals/layered-price-preview.png")'
```

Checks cover 500 unique reproducible records, finite coordinates, nonnegative
contributions and exact benchmark reconciliation for every product at every
supported top-N setting. 172,450 display samples were checked across slice and
density settings to ensure each remained within its own product's layer.
Mocked interface checks covered 19 renders, including selection, price editing
and reset, layer peeling, slicing, density/size changes, camera controls and the
WebGL fallback. These checks do not verify browser rendering.

The static preview was rendered and visually inspected. Live WebGL rendering
and pointer behavior still require a normal-browser review because browser
startup is blocked in this workspace. No retailer prices were changed and
the prototype has not been deployed.
