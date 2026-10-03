# Multidimensional pricing review: research and design plan

Researched 3 October 2026. Proposed design for review, not an implemented product.
Update: the [3D Price Terrain design](3d-price-landscape.md) is now the latest
hero-view direction. The multidimensional matrix and interaction research below
remain relevant; parallel coordinates are an optional future analytical lens.
This updates the visual direction in [the hackathon proposal](hackathon-proposal.md).
The [reference board](visuals/visualization-reference-board.html) brings together
the example links and a proposed page layout. The existing price-map prototype
remains a separate, fictional-data sketch.

## Recommendation

Build one coordinated workspace with **parallel coordinates above a product-trait
matrix, and a persistent price-review panel on the right**. The matrix is the
precise comparison surface; the chart reveals patterns and narrows the cohort.
The existing price-versus-benchmark scatter becomes an optional analytical lens.

This answers three different questions without changing pages:

1. Which products share the traits I am investigating?
2. Exactly how do those products differ, including categorical and missing data?
3. What evidence supports or challenges the selected product's proposed price?

The memorable interaction is to select a range on a trait axis and watch the
same products become prominent in the chart and matrix. Pin a few peers, add
another trait, then test a price while their identities remain visible.

## Existing examples to review

These are external examples, not screenshots of our implementation. Interactive
examples require JavaScript. Documentation, example source and available static
previews were inspected; their interactions were not browser-tested in this
workspace.

| Priority | Existing example | What to try | What to borrow |
| --- | --- | --- | --- |
| 1 | [Plotly: parallel coordinates](https://plotly.com/javascript/parallel-coordinates-plot/) | Drag along an axis to constrain its range; drag an axis title to reorder dimensions. | The central numeric exploration interaction. Each polyline represents one product. |
| 2 | [LineUp live demo](https://lineup.js.org/app/) and [feature overview](https://lineup.js.org/) | Sort, filter and group columns; inspect numeric cell encodings beside categorical fields. | A precise product-trait matrix with compact bars and values. Omit composite ranking scores from our MVP. |
| 3 | [D3: brushable parallel coordinates](https://observablehq.com/@d3/brushable-parallel-coordinates) | Brush ranges on several axes. | A restrained visual treatment and a clear example of narrowing a multidimensional cohort. |
| 4 | [ECharts: parallel nutrients](https://echarts.apache.org/examples/en/editor.html?c=parallel-nutrients) | Explore many nutritional dimensions; inspect the provided source. | A dense numeric overview reference. Our page should expose fewer active axes and use fewer colors. |
| 5 | [Plotly: linked categorical and numeric views](https://plotly.com/javascript/parallel-categories-diagram/#parallel-categories-linked-brushing) | Select points and category ribbons in the linked example. | A later categorical exploration lens. Ribbon width means record count, not price contribution. |
| 6 | [ECharts: scatterplot matrix](https://echarts.apache.org/examples/en/editor.html?c=scatter-nutrients-matrix) | Compare pairs of variables across the grid. | An optional analyst lens for relationships hidden by adjacent parallel axes. Too dense for the buyer's default view. |
| 7 | [Motion: reorder example](https://examples.motion.dev/react/reorder-items) and [shared card transition](https://examples.motion.dev/react/app-store) | Reorder items; open and close a card. | Smooth dimension controls and a selected-product detail transition. |

Start with examples 1, 2 and 7: together they explain the proposed interaction,
business usability and motion direction.

## Really Good Culture as a design reference

The requested [live homepage](https://reallygoodculture.com/) returned HTTP 429
to direct requests and could not be inspected through the web reader. Its current
layout, fonts, exact palette and animation implementation are therefore
unverified. Do not claim that it uses any particular animation library.

I visually inspected pages 1 and 35 of RGC's official
[July 2023 Future of Spirits report](https://cdn.reallygoodculture.com/reports/the-future-of-spirits.pdf#page=1).
This is an older brand reference, not proof of the current website's styling.
It uses oversized condensed headings, strong black/white contrast, generous
space, product cutouts, metallic purple lettering and a turquoise accent badge.

Translate that direction into a restrained application: an editorial header,
light reading surfaces, a dark chart canvas, turquoise selection and a muted
violet proposal. Keep decorative chrome away from numeric marks and labels.
This is our design interpretation; it does not reproduce a verified brand kit.

Proposed tokens, chosen for this concept rather than sampled brand values:

| Role | Proposed value | Use |
| --- | --- | --- |
| Page | `#F5F5F0` | Warm light background and table |
| Chart | `#171C20` | Dark analytical canvas |
| Main text | `#202725` | Text on light surfaces |
| Chart text | `#E9EFED` | Axes, values and labels |
| Selected product | `#59DFC3` | Chart line; pair with a name and selection symbol |
| Proposed price | `#B8A3F5` | Diamond marker and explicitly labeled scenario |
| Light-surface link | `#006653` | Readable emphasis on light surfaces |

Use a condensed display style only for the page title; use a neutral sans serif
and tabular numerals for the application. Check contrast on actual components.
Any metallic accent belongs in the title treatment, never the data scale.

## One-page composition

Target a desktop review at approximately 1440 by 900. A smaller laptop can scroll
within the matrix; it should not shrink all labels to fit an entire dataset.

```text
RGC / PRICING REVIEW       Cohort · Price basis · Source snapshot · Model status
Explore traits: [Cocoa %] [Net weight] [Sugar*] [Unit price] [+ Add dimension]
Filter: [Brand] [Retailer] [Claims]       3 products pinned · Show missing values

┌──────────────────────────────────────────────┬──────────────────────────────┐
│ NUMERIC TRAIT EXPLORER                        │ PRICE REVIEW                 │
│ Parallel coordinates with selected SKU and   │ Selected product             │
│ pinned peers highlighted over a muted cohort │ Current → proposed price     │
│                                              │ Benchmark + interval*        │
│ Drag to select a range. Reorder / add axes.   │ Same price basis + context   │
│ [Traits] [Price position]                    │                              │
├──────────────────────────────────────────────┤ Supporting / challenging     │
│ PRODUCT × TRAIT MATRIX                       │ evidence and unknowns        │
│ Product | £/100g | Cocoa | Weight | Claims    │                              │
│ Pinned peers; sortable bars, numbers, labels  │ Sources and review note      │
│ Add/reorder columns; missing = Unknown       │                              │
└──────────────────────────────────────────────┴──────────────────────────────┘
* Only available with supported data / validated model outputs.
```

The left side takes roughly 72% of the content width; the right panel takes 28%.
The chart uses about half the left-side height, with the matrix below it.
Selecting a matrix row or using product search selects the same SKU everywhere.
Individual line hover/click is an enhancement to verify in a technical spike,
not a dependency of the core workflow.

### Handle many dimensions without making the chart unreadable

- Keep roughly 4–7 active numeric axes, depending on available width and real
  feature coverage. Start with fewer if the reviewed data supports fewer.
- A searchable dimension picker groups fields into product composition, pack,
  claims, selling context and model outputs. Show units and completeness before
  adding a field. Adding a display axis does not add a regression feature.
- Numeric examples include cocoa percentage, verified net grams and GBP/100 g.
  Sugar per 100 g is eligible only if extracted and reviewed; its presence is
  not established by this research. Keep price-derived outputs visibly grouped.
- Brand and retailer are nominal categories. Use filters and matrix columns;
  do not imply an ordered numeric scale. Claims have explicit declared,
  not-declared/negative-evidence and unknown states as appropriate to the source.
  A claim being absent from a page is not proof that it is false.
- Each numeric axis retains its own labeled units and fixed domain while
  brushing. An explicit rescale command can change domains. Parallel-axis height
  does not imply equal units or that higher is better.
- Multiple axis filters intersect. Show active constraints, matched listing
  count, distinct-family count and exclusions. A visual sample must declare its
  sampling; do not report sample counts as the full cohort.
- Missing traits never become zero. Keep those records accessible in the
  matrix, show missing counts, and state when an active axis/filter excludes
  them. Do not connect a line through an invented measurement.
- Pin up to three or four products for comparison. If a pinned SKU is outside
  the current filter, retain it in a labeled pinned section rather than counting
  it among the matching products.

The matrix can expose many more fields than the chart through grouped columns,
horizontal scrolling, frozen product/price columns and saved trait selections.
Exact values remain available beside in-cell bars. Avoid normalizing mixed
traits into an unexplained quality heatmap or an arbitrary overall value score.

### Separate exploration from price explanation

The chart shows observed relationships; it cannot prove that a trait caused a
price premium. The price-review panel supplies the declared benchmark context,
actual model results where available, uncertainty and source evidence.

Keep four states distinct: visible dimensions, exploration filters, benchmark
reference context and proposed selling price. Brushing a cohort does not silently
refit the model or redefine the benchmark. Changing a proposal moves its marker
and calculated price deltas only. A deliberate benchmark-context change requires
supported recomputation and a visible context/version update.

The current price map remains useful in the chart area's optional Price position
lens. Preserve selected IDs and color across lenses; a simple crossfade is
acceptable. Do not assume arbitrary chart types can morph accurately by default.

For an explanation of individual traits, use a supported conditional comparison
with other inputs and reference levels stated. Feature contributions, if later
added, must disclose the model's scale; a log-price contribution is not an
additive pound amount or an ingredient cost.

## Tools and animation plan

**Recommended MVP: React + Plotly.js + TanStack Table + Motion.** Use existing
Python collection/model work behind a frozen data artifact. An API is optional
for the first demonstration. Pin tested dependency versions at implementation.

| Tool | Role and evidence | Decision for this team |
| --- | --- | --- |
| [Plotly.js](https://plotly.com/javascript/parallel-coordinates-plot/) | Built-in numeric parallel coordinates, axis constraints and axis reordering; [React integration](https://plotly.com/javascript/react/) is documented. | First choice because dynamic dimensions are central. Customize layout/fonts/colors. Verify controlled filter/selection synchronization before styling. |
| [TanStack Table](https://tanstack.com/table/v8/docs/guide/column-ordering) | Controlled column ordering; its guide also explains interaction with pinning and grouping. | Use for the styled comparison matrix. Add explicit move-left/right controls first; drag-and-drop can follow. Match docs to the installed version. |
| [Motion](https://motion.dev/docs/react-layout-animations) | Layout and shared-element animation for React components. | Animate dimension controls, panel expansion and selection accents. The chart library owns chart marks. Motion layout animation is not an automatic SVG/chart morphing engine. |
| [Apache ECharts](https://echarts.apache.org/examples/en/editor.html?c=parallel-nutrients) | Alternative chart library with a parallel-coordinates example and [data transitions](https://echarts.apache.org/handbook/en/how-to/animation/transition/). | Strong alternative if the team prefers its chart controls. Build axis-order controls explicitly; do not assume native label dragging. Choose one chart engine. |
| [LineUp.js](https://lineup.js.org/) | Existing mixed-attribute table, filters, grouping and cell encodings. | Excellent design reference; optional replacement for the custom matrix if its styling/API fits in a short spike. Do not build both table systems. |
| [D3](https://observablehq.com/@d3/brushable-parallel-coordinates) | A brushable parallel-coordinate implementation. | Maximum control, but more interaction code. Reserve for a specific unsupported requirement. |
| [GSAP](https://gsap.com/docs/v3/Plugins/ScrollTrigger/) | Timeline and scroll-linked animation capabilities. | Useful for a promotional story, lower priority for a fixed analytical workspace. Motion is sufficient for this MVP's interface. |
| [Rive](https://www.rive.app/) | Editor/runtime for authored interactive animation. | Optional small brand animation after the data interaction works. Extra asset authoring is hard to justify for two people. |

Do not install every library in this table. The recommended stack has one chart
engine, one table engine and one interface animation library. Existing small SVG
price markers can remain if replacing them adds no value.

Suggested motion timings are design targets, not measured performance:

| Trigger | Motion | Purpose |
| --- | --- | --- |
| Select a product | 120–180 ms emphasis change across views | Locate the same product quickly |
| Apply a trait filter | 150–250 ms fade/dim; update counts immediately | Show which products remain; avoid rerouting unrelated marks |
| Add/reorder a dimension | 200–350 ms control reflow; chart redraw or short crossfade | Preserve orientation; do not promise unsupported axis interpolation |
| Open source evidence | 200–300 ms panel expansion | Keep the selected product in context |
| Change proposed price | Direct tracking while dragging, at most a brief settle | Show the exact scenario, with a fixed benchmark |

Use a subtle selection halo only on the selected product. Keep axes crisp and
labels still. Provide reduced-motion behavior and keyboard alternatives to
brushing/reordering. Avoid animated counters that temporarily show false prices.

## Two-person delivery plan

1. **Agree the page and data contract.** Review examples 1, 2 and 7. Inventory
   actual feature coverage; agree stable product/listing/family IDs, units,
   categorical states, source links and benchmark status. Confirm which numeric
   axes are defensible. Use explicitly fictional fixtures until data is ready.
2. **Run a 30–45 minute integration spike.** Person B proves axis add/remove,
   reordering, brushing-to-table filtering and table-to-chart highlighting.
   Person A supplies representative complete, missing and conflicting records.
   Preserve selected IDs across filters; verify no event-update loops. If an
   interaction fails, simplify to controls rather than starting another engine.
3. **Build the working comparison.** Person A produces the reviewed cohort and
   benchmark artifact where validation supports it. Person B implements the
   matrix, chart and shared selection/filter state; reuse the fixed-benchmark
   scenario behavior from the existing concept.
4. **Apply the visual system and targeted motion.** Add typography, spacing,
   tokens, accessible selection states and source drill-down. Keep the complete
   decision flow usable with animation disabled.
5. **Verify and record.** Check arithmetic, unknown values, consistent cohort
   counts, units, stable benchmark, keyboard controls and browser performance on
   the demo machine. Freeze one evidence-backed story for the two-minute video.

MVP: one reviewed cohort, dynamic axes/columns, coordinated filtering, pinned
comparisons, one selected product, one proposed-price control and real evidence.
Defer categorical ribbons, scatterplot matrix, 3D scenes and elaborate chart
morphing. If the model is not adequately validated, demonstrate the evidence
explorer with explicit model-unavailable status.

Demo story: start with a proposed price; narrow comparable products using two
traits; pin peers and add another dimension; inspect a meaningful difference or
unknown; move the proposed price against a fixed supported benchmark; finish
with the evidence and limitation that determine the draft decision.

## Verification limits

The RGC PDF was downloaded and rendered locally for visual inspection. The
ECharts parallel-nutrients source and its official static preview were also
inspected. Live reference interactions, current RGC homepage styling, package
compatibility and animation performance still require a normal browser and the
implementation spike. This plan makes no claim that the collected 1,849 source
records have already been normalized, deduplicated or modeled.
