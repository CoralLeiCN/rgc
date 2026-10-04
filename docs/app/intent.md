# App intention

The application helps retail category managers, buyers and pricing teams explore
product evidence, compare an assortment and explain a SKU's proposed price.
Brand product developers are a related audience. Retailer examples such as Tesco
identify the intended users; internal retailer data or a customer relationship
is not assumed.

This is the app part of the [project intention](../intention.md). The
[data intention](../data/intent.md) owns collection and meaningful analytical data, and the
[model intention](../model/intent.md) owns pricing research and model validation. This
document records requested experiences and constraints. The [app specification](spec.md),
[application architecture](../vercel-architecture.md),
[integration notes](../collection-integration.md) and
[lifecycle plan](../lifecycle/plan.md) own implementation and validation status.

## Piece of Cake Pricing workspace

The workspace is **Piece of Cake Pricing**, with subtitle **FMCG Pricing made
easy.** It serves a two-person hackathon team presenting to retail pricing
teams. The requested delivery platform is Vercel for both frontend and backend.
The application architecture defines a Next.js app, server APIs and a pinned,
verified collection snapshot. Frontend, backend and platform implementation are
delegated to subagents after architecture design.

The requested experience covers evidence exploration, a declared prototype trait
score, product configuration and candidate extraction. Users can cut vertically
through the cake at selected price points to inspect its layer composition.
The user subsequently authorized the published LightGBM without brand fixture
for a clearly labelled synthetic prediction demo. The form should calculate a
price from supported inputs and show signed SHAP field contributions relative
to the model reference. Real market benchmarks retain their separate review
and validation requirements.

The synthetic fixture supports single chocolate bar packs and retains its
historical `regular-consumer-price-1` basis. The current chocolate study's price
policy does not retarget that demo. The
[fixture serving guide](../data/analysis/web-fixture-pricing.md) owns its supported
inputs and serving contract.

The user requested that the app consume the published Gold inferred collection.
Use its accepted derived attributes with preserved source evidence, review states,
missingness and immutable provenance. Dataset adoption does not establish model
readiness. Application requests use their pinned snapshot and do not
automatically adopt a new Gold release or model artifact.

The earlier evidence-explorer scope used a UK chocolate snapshot with 3,743
source listings, 2,134 price observations and 103 traits. Those were seller
listings, not reviewed independent products. Its published model-input gate
reported zero passing rows, and no fitted pricing model, supported benchmark,
prediction interval or recommended selling price was connected. That earlier
application scope subsequently expanded with the synthetic fixture demo
authorization above. These historical counts and gates do not establish the
current application or model status; consult the integration notes for the
selected snapshot and connected behavior.

## Terrain and trait exploration

The primary visualization is a layered 3D terrain. X is observed GBP per 100 g;
Y is a reproducible prototype score calculated from known traits; Z is one
selected numeric leaf trait in its original units. Exact product points retain
all three coordinates. The terrain smooths nearby numeric values with positive
local weights and leaves unsupported areas open. Colored layers divide height
above a declared baseline; their thickness is a visual composition, not a price
contribution, cost share, model coefficient or quality measure. A 2D projection
provides an accessible alternative when 3D is unavailable.

The user rejected aggregating an entire parent family into a color bar or height
index. The published schema has flat families containing individual fields, not
a migrated nested family hierarchy. Families organize navigation, definitions,
filters and matrix comparison. Color is selected from one leaf field: number,
integer, enum, boolean or string list. Numeric colors use five equal-width bands
calibrated to the immutable full snapshot; filtering does not redefine a band's
meaning. A multi-valued list splits its visual share equally between its distinct
values. Unknown, conflicting, not-applicable and truncated evidence stay explicit.
Z accepts a single numeric leaf; family means and normalized family indices are
excluded.

Retailers can build a cohort with source, role, product-type, search and typed
trait conditions, then inspect the same evidence in a dynamic matrix and an
up-to-four-product comparison. Several trait families can expand at once;
pinning and per-family limits preserve manageable detail without changing
coverage denominators. The family browser exposes Filter, Colour and Height
actions for eligible leaf traits. Legend highlighting and surface smoothing
change presentation, not the cohort or original product coordinates.

The gap finder and brand analysis continue to use observed prices from the full
filtered listing collection, independently of matrix pagination and terrain
coordinate completeness. Gaps identify empty interior price bands at the chosen
resolution. Brands stand out by higher median observed price positioning within
the cohort; sales, profit, causal brand premium and demand are not inferred.
Core/full price ranges disclose excluded tails, while brand statistics retain
the full priced cohort.

## Configure a proposed product

The right column lets a retailer specify a proposed product with schema-typed
traits, pack price and edible weight. A price slider and precise numeric input
move its proposed GBP/100 g position. Score is read-only and recalculated from
traits using the shared, declared six-input prototype recipe. Prices and names
do not affect the score. No recognized scoring inputs means no score; unknown
claims are not treated as absent. A visible demo/prototype disclosure and an
inspectable rule breakdown distinguish this recipe from the separate pricing
research.

A valid configured product appears at its exact proposed price, calculated
score and selected raw numeric trait. Invalid or missing coordinates suppress
the marker instead of inventing values. A price beyond the observed range can
extend the display axes while preserving the observed cohort and range. The
draft never becomes a source listing or enters gap or brand statistics.

An explicit action can copy known, untruncated values from a selected listing;
ordinary source selection preserves edits. Product descriptions and packaging
images can also be submitted for model-assisted trait extraction. Results are
candidates with evidence and warnings. The retailer reviews and selects them,
then explicitly applies them to the draft. Applying candidates can replace
matching name, weight or trait inputs, but never changes proposed pack price.
Original source evidence remains available in a collapsed disclosure.

Keep the supplied front and back photos of Well&Truly Fudge & Brownie Oat M!lk
Chocolate, 30 g, as repository demo data and offer them as a selectable example
in the extraction panel. Users can also upload their own photos, including both
sides of a pack. Selecting an example loads its images for the same explicit
extraction and review workflow; it does not supply prefilled traits. Preserve
original photos and prepare temporary browser copies that fit request limits.
Retain label qualifiers: component cocoa minimums and “fairly traded” wording
must not imply an exact whole-product cocoa percentage or a named certification.
Demo photos and local drafts stay outside the training corpus.

Enable local image/text trait extraction through the installed Codex CLI using
its ChatGPT OAuth sign-in. The local Next.js server should invoke it directly,
with candidates still requiring explicit review and Apply. Hosted extraction
supports a configured OpenAI API provider or authenticated Codex bridge,
including the requested laptop connection through Tailscale. The extraction
model has a separate purpose from the synthetic pricing fixture and its field
SHAP explanation. Missing provider configuration produces an explicit error.
Record successful live extraction separately from hosted bridge and network
availability.

## Persistent review of standardized data

Provide an interface for users to inspect a standardized Silver value, open its
original Bronze evidence and see whether its method is `parsed`, `inferred` or
human `reviewed`. All three can be used; precedence for the same fact is
`reviewed > parsed > inferred`. Show missing information, parsing errors and
conflicts distinctly. Repeated components and observations must identify the
subject being reviewed.

Users can confirm a value or revise it, save the decision and inspect earlier
decisions. Persist each correction so it survives reprocessing and appears in
subsequent Silver builds when applicable. Downstream users who discover an error
can return to the source field and correct it. Saved decisions provide evidence
for improving models, parsing rules and regression tests over time.

The [data specification](../data/spec.md#persistent-corrections-and-replay) owns
correction identity, history and replay. This durable review workflow is requested
work; the existing local product draft and candidate Apply action do not
implement it.

## Price review and interpretation

The intended validated workflow lets a retailer review an existing SKU, proposed
listing or price change against a supported model and comparable range. A brand
can also test a newly designed product. Declare category, market, comparison
group and selling context, then report the estimate, prediction interval and
supported comparisons. Unsupported designs require an explanation of missing
support. A prototype trait score does not fulfill this validated workflow.

Supported price testing requires validated benchmarks and uncertainty, including
held-out or out-of-fold results for training products. The model intention owns
these requirements and the deferred research into category value for money and
brand premium. A price residual alone cannot establish brand premium, quality
or consumer value. Descriptive brand median rankings in the application measure
observed price positioning only.

The teammate's pricing research and upstream experimental training remain
separate from this application. The later authorization permits the published
synthetic fixture for local price prediction and field SHAP demonstration;
deployment of that feature and validation of a real market benchmark require
their own evidence in the integration notes. If market validation remains
inadequate, keep evidence exploration, the explicit prototype score and the
authorized synthetic demo accurately labelled, without claiming optimal pricing,
value for money or causal brand premium. The [model specification](../model/spec.md) remains
authoritative for model readiness and interpretation.

## Presentation and maintained application

Use a restrained professional palette, explicit units, legible comparisons and
inspectable assumptions. Explanatory prose belongs in accessible question-mark
help beside headings, available on hover, focus and tap. Actual values, field
labels, errors and demo-score disclosure remain visible. Remove the four top
summary cards. Avoid factory metaphors and unsupported claims of market-wide
coverage.

Maintain one current application and its operational documentation. Retire
visual studies, generated static explorers, intermediate design notes and tests
added for the hackathon at the user's request. No compatibility support is
retained for those prototypes. The active terrain, product configuration,
extraction workflow and declared trait-derived demo score remain in scope.
