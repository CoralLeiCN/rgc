# Price Terrain: a 3D pricing review

Latest clarification: [the layered price landscape](layered-price-landscape.md)
extends the user's stacked-bar reference into solid colored strata. Its
[interactive concept](visuals/layered-price-landscape.html) is the newest visual
study. This earlier single-surface design remains a separate analytical view.

Updated 3 October 2026. This is the latest visual direction, following the
request for a geospatial-style 3D experience. It supersedes parallel coordinates
as the proposed hero view while retaining the precise trait matrix.

Open the [interactive Price Terrain concept](visuals/price-terrain.html).
It uses local JavaScript and a vendored Plotly WebGL bundle, so it needs no API
key, package installation, remote service or network request. A browser with
WebGL support is required. It can be opened directly, or served from the repo:

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory docs
```

Then visit `http://localhost:8080/visuals/price-terrain.html`.

## The visual idea

Use the visual language of a terrain map: a shaded mesh, elevation contours,
product markers, vertical stems and an orbitable camera. Its coordinates are
product traits, not latitude and longitude. Its elevation is price per 100 g,
not a quality score. The interface says this explicitly.

The scene occupies most of the page. A compact product/price panel stays beside
it; a trait table stays below. A small cross-section makes the selected price gap
readable without perspective distortion. The dark navy, turquoise and violet
direction develops the earlier design study; it does not claim to reproduce
RGC's inaccessible current homepage.

## 1. Trait terrain: the regression relationship as a surface

For a selected product with full trait vector `a`, choose two numeric traits:

- `x`: for example cocoa percentage.
- `y`: for example verified net weight.
- `z`: predicted unit price, evaluated with all other traits fixed at `a`.

The conditional surface is:

```text
surface(x, y) = model(x, y, selected_product_other_traits)
```

The selected product has three marks at the same horizontal coordinates:

| Mark | Height | Meaning |
| --- | --- | --- |
| Open mint marker | Its model benchmark | Its point on the conditional surface |
| Filled light circle | Observed unit price | Where it currently sits relative to that benchmark |
| Violet diamond | Proposed unit price | The scenario being reviewed |

A vertical connector shows the price gap. It can extend above or below the
surface. Neither direction establishes commercial acceptability or product
quality. The numerical difference stays visible in the side panel.

### The fitting line the user asked for

Two visible explanatory traits produce a surface. Hold the depth trait at the
selected product's value to obtain a one-dimensional curve through that surface:

```text
curve(x) = model(x, selected_y, selected_product_other_traits)
```

Highlight it in mint. The benchmark marker lies on the curve; the current and
proposed price markers can lie above or below it. Show the same curve in a small
2D cross-section beneath the scene. A linear model in the plotted price scale
may produce a line/plane; a nonlinear or transformed model may produce a curve
and curved surface. Do not bend the surface just for visual drama.

### The comparison rule matters

Every visible peer must share the fixed traits used for the surface, or its own
benchmark generally will not lie on it. The concept shows only exact-context
matches in terrain mode, and displays that rule and resulting count.

In real data, exact matching may leave very few peers. Preserve that result and
use the all-trait view for broader comparison. Do not silently project unmatched
products onto someone else's surface or label their vertical difference a model
residual. An adjusted-price view could be a separate future analysis with its
transformation explained.

## 2. All-trait fit: a faithful view of a large trait matrix

A three-dimensional plot cannot give dozens of independent traits their own
axes at once. The all-trait view therefore uses the full model estimate as an
explicit summary:

```text
x = model(each_product_full_trait_vector)
y = selected numeric trait, used for visual separation
z = observed unit price
reference plane: z = x
```

Each product's open benchmark marker lies on the agreement plane. Its observed
price and proposed-price marker share the same x/y coordinate, so their vertical
distance to the plane is an exact price gap. Other supported model features still
contribute to x, even though they are not individual visible axes.

This plane is an equality reference, not an additional regression fitted through
the predictions. The selected line is the agreement line at the selected depth.
Changing the depth trait changes the view, not the model or prices. The matrix
exposes the individual attributes behind each estimate.

For existing training SKUs, production benchmarks must follow the project's
held-out/out-of-fold rules. A conditional surface through an existing product
must use the same eligible model context as its benchmark, for example that
product's held-out fold model; do not mix an OOF anchor with an unrelated full-fit
surface and claim they should agree.

## 3. Later: a product atlas using many traits for location

An optional overview could embed a reviewed mixed-trait representation into a
two-dimensional similarity map, then use height for price. Products with similar
compositions and declared attributes would form local neighborhoods.

Keep price and model residuals out of the similarity coordinates if the intended
meaning is similarity of non-price traits. Explicitly choose categorical
encoding, feature weighting, missing-data handling and normalization. Validate
neighborhoods in the original feature space and explain which traits make the
selected products similar. Freeze/version the embedding so filtering does not
move every product around.

UMAP is a possible exploration method, not a guaranteed commercial segmentation.
Its axes are not named business dimensions and screen distance is not an exact
product-difference measure. The [Google PAIR explanation](https://pair-code.github.io/understanding-umap/)
is useful for reviewing how these maps should be interpreted.

At each fixed map coordinate, show the product's own prediction anchor and its
observed price with a vertical stem. Do not fabricate a smooth fitted price
surface over an embedding: a 2D embedding cannot generally be inverted into a
unique full product vector. If an interpolated mesh is added for orientation,
label it as interpolation and separate it from model results.

Select a product in this atlas to enter its explainable trait terrain. This is
the eventual cinematic interaction: category overview, product focus, fitted
curve, then proposed-price movement. The atlas is not implemented in this sketch.

## What the current concept implements

- Orbit/zoom and animated 3D, top and side camera presets.
- A shaded conditional surface with projected contours and a highlighted curve.
- Two distinct numeric axes chosen from cocoa, net weight and sugar.
- Matching-context peer markers and their observed-to-benchmark stems.
- An all-trait fit view with the equality plane and all 108 fictional products.
- Product selection from a point, native selector, or table.
- Proposed pack-price input and slider, correct conversion to GBP/100 g, and
  separate change-from-current and gap-to-benchmark figures.
- A linked 2D cross-section and full trait matrix for precise reading.
- Keyboard-operable selection/input controls and reduced-motion camera presets.
- A local chart dependency and readable fallback when chart initialization fails.

The synthetic records cover three fictional brand contexts and six modeled
traits. Brand is a label, not an independently estimated effect. Categorical
values are explicit synthetic facts; production missing claims must remain
unknown. The price function is hand-authored and nonlinear. It is not a trained
regression, and no calibrated prediction interval is invented.

## Tools and existing 3D examples

| Tool / reference | Role in this design |
| --- | --- |
| [Plotly surface and contour examples](https://plotly.com/javascript/3d-surface-plots/) | The implemented terrain: evaluated grid with contour projection. |
| [Plotly 3D lines](https://plotly.com/javascript/3d-line-plots/) | Curves and connectors within the same 3D coordinates. |
| [Plotly 3D scatter](https://plotly.com/javascript/3d-scatter-plots/) | Product, benchmark and scenario markers. |
| [deck.gl point-cloud example](https://deck.gl/examples/point-cloud-layer) | Review the spatial exploration feel for a future product atlas. |
| [deck.gl views documentation](https://deck.gl/docs/developer-guide/views) | OrbitView supports non-geographic 3D information visualization. A real-world basemap is unnecessary for trait space. |

Use Plotly for this hackathon implementation: it combines the required chart
primitives in one engine. The prototype pins the 3.1.0 gl3d bundle, includes its
license and makes no claim that this is the latest release. Keep its data layer
independent so a later deck.gl atlas can reuse IDs, model values and selection.
Custom shaders and a second rendering engine are not required for this demo.

## Next implementation steps for two people

1. **Person A: analytical contract.** Supply reviewed SKU/family IDs, traits,
   units, source references, prediction context/version and supported ranges.
   Return exact per-SKU benchmarks plus evaluable conditional slices where
   supported. Complete the baseline and family-separated validation.
2. **Person B: production scene.** Replace fixtures without changing their
   semantics. Keep chart selection linked to the table and evidence panel.
   Mask unsupported surface cells, preserve missing traits, and label sparse
   contexts instead of drawing an unjustified smooth landscape.
3. **Together: uncertainty and evidence.** Add a selected-product prediction
   interval only when calibrated. Keep it visually distinct from the residual
   connector. Validate any surface uncertainty bands before rendering them.
4. **Polish and demo.** Verify GPU/browser behavior, units, labels, overlapping
   products, selection and reduced motion. Add source drill-down. Rehearse:
   rotate terrain, select a product, expose its curve, move the proposal, then
   switch to all-trait fit to demonstrate that other traits remain accounted for.

Do not interpolate price values for animation: the marker should track the input
directly. Camera travel can ease over about 650 ms and is disabled for reduced
motion. Keep orbit user-controlled, avoid constant spinning, and preserve a
precision cross-section for the actual pricing conversation.

## Validation status

The concept's JavaScript and arithmetic/state behavior are checked separately
from browser rendering. Checks passed for all 108 fixture identities and every
distinct axis pair: matching-peer anchors equal the corresponding slice value.
They also covered fixed benchmarks/surfaces under proposal edits, pack/unit
conversion, agreement-plane geometry, linked selection, axis collisions, invalid
input and reset behavior. UI state checks use a mocked chart engine and do not
verify WebGL. The workspace prevents Chromium from starting because
of a macOS process permission error; WebGL appearance and live pointer behavior
therefore require a normal-browser review. Starting a local preview server was
also denied here; opening the HTML file directly remains the review path.
No deployment, real price update or
model training is performed by this artifact.
