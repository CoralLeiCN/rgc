# Piece of Cake Pricing on Vercel

Next.js serves the React dashboard and collection/extraction APIs from one
Vercel project. The verified immutable collection lives in private `snapshot/`
files, derived from published Gold inferred data. The immutable source revision
and manifest hash are pinned in [collection-dataset.json](collection-dataset.json).
Browser requests fetch bounded cohorts, terrain rows and selected evidence.
See the [architecture](../../docs/vercel-architecture.md),
[API interfaces](lib/contracts.ts) and [current proof](../../docs/lifecycle/plan.md#verification).

## Run locally

Use Node 24 and npm. From the repository root:

```sh
python3 -B scripts/fetch_web_pricing_model.py
cd apps/web
npm ci
npm run dev
```

Open `http://localhost:3000`. The dashboard is `/`.

```sh
npm run typecheck
npm run verify:terrain
npm run build
npm start
```

Build prepares the pinned pricing model if it is absent, then verifies snapshot
hashes, counts, evidence shards and packaged assets,
then checks snapshot inclusion in all eight API function traces and the pinned
pricing model in the prediction trace. It does not
fetch the collection snapshot or run Python. A clean build downloads the two
immutable model artifacts; cached builds verify them offline. No database or external credentials are needed
to explore the collection. Local development uses signed-in Codex for image/text
extraction unless an explicit provider, bridge URL or OpenAI API key is configured.

## Terrain and product configuration

X is observed GBP/100g, Y is a read-only trait-derived demo score and Z is one
numeric leaf trait in its original units. Family cards show trait counts and
coverage; clicking a card opens its member traits. Parent families
cannot supply colour layers or height. Choose a leaf enum, numeric, boolean or
string-list trait for colour: enums retain categories; numbers use five labelled
ranges fixed to the whole snapshot. Missing evidence states remain explicit.

The closed layered terrain smooths nearby numeric values without moving exact
product dots. Layer thickness is a visual category share, not a causal price
contribution. Unsupported areas remain open; smoothing and layer highlighting
are adjustable. Rotation defers geometry work, and a 2D projection provides a
fallback. Excluded counts are available in the help control; incomplete products remain in the matrix.

Chart hover details use an HTML tooltip with explicit text and background colours.
Product points show the name, observed or proposed unit price, demo trait score
and selected height value. The tooltip stays within the chart and clears when
the pointer leaves, dragging starts or the chart data changes.

Enable **Slice the cake by price**, then move the GBP/100g slider to inspect a
vertical section. Choose which side to keep, use **Face slice** to look directly
at the cut, and **Restore whole cake** to reset it. The diagram below the chart
shows the exact interpolated section across demo trait scores, including gaps
in surface support. It is also available in 2D projection mode. Point coordinates
and cohort statistics retain their original basis; the view hides points on the
removed side. The slider is bounded to the displayed price range.

The configurator accepts typed traits, edible mass and a proposed-price slider.
Its demo score is calculated using the same fixed recipe as observed products:
base 20 with at least one recognized input, cocoa percentage × 0.30, and 10 each
for explicit organic, Fairtrade, bean-to-bar, single-origin and gift-pack claims.
The score cannot be edited directly. Price changes only the draft's price position.
This is a disclosed prototype recipe, not the teammate's fitted model.

Choose **Use example photos** to load the supplied front and back photos of
the bundled demonstration product, or upload your own images.
Add or remove up to two readable PNG/JPEG/WebP photos, each at most 20 MiB and
40 megapixels before preparation. A new upload appends when room remains or
replaces both photos when two are selected. Optionally add a description of up
to 12,000 characters. The browser resizes images as needed to at most 2,400
pixels on the longest edge and
compresses each to at most 1 MiB for extraction. Selecting the example replaces
the photos and clears the description after successful preparation; **Extract
traits** submits the current inputs to the configured provider.
Review evidence and explicitly apply selected candidates; applying candidates
merges them into the current draft and preserves the proposed price.
Copying a selected listing/resetting the draft clears stale extraction review.
Drafts stay local and never enter observed gap, brand or training analyses.
Original source evidence remains under a disclosure in the configurator.

The upload and pricing panels have distinct component identities. Draft edits
retain selected photos in one upload panel; copying a listing or resetting the
draft clears both panels' prior sessions.
Extraction checks the browser origin against the requested host, so both
`localhost` and `127.0.0.1` work when opened at their matching local address.

Bundled demonstration images are verified through `public/asset-manifest.json`.
Image preparation creates temporary browser copies. Selecting an example does
not supply prefilled extracted traits, model support or a training row. Review
component scope and the wording of claims before applying any candidates.

Core range uses full-cohort Tukey bounds and discloses omitted tails. Full range
includes every usable price. Gap finder highlights interior empty price bands;
brand analysis ranks known brands with at least three observations by median
unit price. Neither establishes demand, sales, margin or a like-for-like premium.
The dashboard uses `/api/analysis` for observed-price statistics.

## Direct local extraction with ChatGPT sign-in

The local Next.js server can invoke Codex directly. Install the Codex CLI and
run `codex login` to complete its ChatGPT OAuth sign-in, then confirm
`codex login status`. From `apps/web`, run `npm run dev` and use **Extract traits**
in the product configurator. Local development defaults to `codex-local` when
no provider, bridge URL or OpenAI API key is configured.

To explicitly select this mode, including for a local production server, set
this server-only value in the ignored `apps/web/.env.local` and restart Next.js:

```dotenv
TRAIT_EXTRACTOR_PROVIDER=codex-local
```

`CODEX_EXECUTABLE` optionally names the installed binary. The child requires
ChatGPT sign-in and removes API key environment variables. It reuses the CLI's
existing authentication store; OAuth tokens stay on the laptop. Inference uses
Codex subscription access and requires network connectivity. See
[Codex authentication](https://learn.chatgpt.com/docs/auth).

Direct local mode admits one extraction at a time with a 90-second deadline and
uses the same private temporary files, disabled tools and schema validation as
the bridge below. Review candidates and apply selected traits to the draft.
Vercel rejects `codex-local`; configure the HTTPS bridge for hosted access.

## Extraction provider A: OpenAI API

Set server environment variables locally in an ignored `.env.local`, or securely
in Vercel Project Settings → Environment Variables. Never use `NEXT_PUBLIC_` or
put keys into the browser, source control or chat.

| Variable | Value |
| --- | --- |
| `TRAIT_EXTRACTOR_PROVIDER` | `openai` |
| `OPENAI_API_KEY` | Your API key |
| `OPENAI_EXTRACTION_MODEL` | Optional; defaults to `gpt-4.1-mini` |

Redeploy after changing Vercel environment variables. The adapter uses Responses
with image inputs, structured output and `store:false`, then validates candidates
against the published schema. Missing setup returns an honest 503 state in the UI.

## Extraction provider B: local Codex subscription

This option invokes the locally installed Codex CLI using its existing ChatGPT
sign-in. Vercel calls a token-protected laptop bridge; OAuth credentials remain
on the laptop. Inference still uses Codex service/usage limits. It is not an
offline model. See [authentication](https://learn.chatgpt.com/docs/auth) and
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

From `apps/web`, confirm `codex login status`. Create a strong 32–512 character
secret in your password manager and enter it without echoing it in zsh:

```sh
read -s 'CODEX_EXTRACTOR_TOKEN?Bridge token: '
export CODEX_EXTRACTOR_TOKEN
npm run extractor:local
```

The bridge listens on `127.0.0.1:8787`. `CODEX_EXECUTABLE` can specify the Codex
binary and `CODEX_EXTRACTOR_PORT` can change the port. It accepts only authenticated
`POST /extract`, one request at a time, with a 90-second deadline. Private input/
output files are deleted afterward. It disables shell/browser/MCP tools, uses a
read-only sandbox and never logs request content or credentials.

Vercel cannot directly reach a private tailnet address. Once Tailscale is
installed, signed in and Funnel is enabled for your account, run in another terminal:

```sh
tailscale funnel --bg 8787
```

Use its returned HTTPS address followed by `/extract`. Funnel makes the bridge
network-reachable; the bridge bearer token remains mandatory. Keep the laptop
awake and connected. See [Funnel setup](https://tailscale.com/docs/features/tailscale-funnel).
To stop publishing that service:

```sh
tailscale funnel --bg 8787 off
```

Configure these server-only Vercel variables, then redeploy:

| Variable | Value |
| --- | --- |
| `TRAIT_EXTRACTOR_PROVIDER` | `codex` |
| `CODEX_EXTRACTOR_URL` | The Funnel HTTPS address ending in `/extract` |
| `CODEX_EXTRACTOR_TOKEN` | The same bridge secret |

No OpenAI API key is required for this provider. Vercel revalidates the returned
traits. Do not remove the preview's access protection to set this up.

Validate the configured extraction provider in the intended environment before
release. Local sign-in does not establish hosted bridge configuration or network
availability. Keep live verification receipts in ignored local documents.

## Vercel setup

Use the configured Next.js project and Node runtime. When connecting the Git
repository, set Root Directory to `apps/web`; the ignored `.vercel/project.json`
records the local project link. Keep organization and deployment receipts private.

```sh
vercel login
vercel link
vercel deploy
```

Preview deployments retain Vercel Authentication; production is separate.
`next.config.ts` includes snapshot JSON in server function traces, never public
assets. Extraction has a 120-second function budget for the optional laptop hop.

## Refresh data and assets

Prepare verified data using the [collection integration commands](../../docs/collection-integration.md).
From the repository root, `uv run python -B scripts/build_web_snapshot.py`
downloads the pinned Gold inferred export into the ignored cache and rebuilds
the private JSON. `--snapshot` rebuilds a verified cache offline. The build
checks the JSON source identity against `collection-dataset.json`; update the
reference and regenerate together when selecting a new immutable collection.
Keep the resulting `snapshot/` and manifest together. A missing/stale manifest
fails the build. The pinned Plotly bundle and its licence live in `public/vendor/`. Build verifies
them against `public/asset-manifest.json`; there is no prototype asset-copy step.
The Vercel ignore rule excludes only the app's root README; the vendor README
is a required asset included in deployment and integrity checks.
No raw archives or model training run on page requests.

## Validation

Run TypeScript, production build, data/asset integrity and relevant browser checks.
A valid snapshot or successful build does not establish extraction accuracy or
model readiness. Preserve actual deployment receipts, population counts and
research results in ignored documents. Verify provider setup before using extraction.

## Synthetic price prediction

The product configurator includes **Predict a price**, using the published
LightGBM without brand fixture. Confirm a single chocolate bar pack, supply
50–150 g edible weight, choose dark/milk/white, plain/inclusion/filled, nuts
evidence and Waitrose/Ocado, then press **Predict demo price**. Type, retailer
and weight share the draft inputs. The result shows GBP/pack and GBP/100 g,
signed field allocations, family percentages, raw SHAP and the model reference.
Other schema fields are listed as not modeled. The form labels generated
training data and the lack of intervals validated on real products.

`python3 -B scripts/fetch_web_pricing_model.py --offline` verifies cached bytes.
`npm run verify:model` checks immutable model hashes. The two artifacts stay in ignored `model-cache/`. `npm run prepare:model`
downloads absent files at the immutable revision and verifies their hashes;
prebuild runs this preparation so clean Vercel builds work. Cached files are
verified and corrupt bytes fail the build. Requests never download models or
invoke Python. No inference credentials
are required; extraction still needs its separate provider configuration.
`POST /api/predict-price` accepts only model fields and explicit scope; it rejects
proposed price, unknown categories, missing required fields and weights outside
the fitted range. Legacy nuts `absent` needs user review before the model's
`explicitly_absent` choice. See [the serving architecture](../../docs/vercel-architecture.md).

The web runtime computes exact stored-path SHAP in Node and is checked against
LightGBM 4.6.0 native contributions across 324 input combinations. Pounds and
percentages use proportional exponential allocation; raw SHAP units are log
GBP/100 g. These allocations describe this prediction relative to its reference.
The hosted preview documented above has not been redeployed with this addition.

The Gold inferred adapter reports `training_rows` for the complete nested Gold
training population. It verifies source quality counts separately and retains
`eligible_model_inputs` and per-price source review flags as historical Silver
provenance. Source eligibility counts do not select the Gold modeling view.
