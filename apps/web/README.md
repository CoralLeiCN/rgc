# Piece of Cake Pricing on Vercel

Next.js serves the React dashboard and collection/extraction APIs from one
Vercel project. The verified immutable collection lives in private `snapshot/`
files. Browser requests fetch bounded cohorts, terrain rows and selected evidence.
See the [architecture](../../docs/vercel-architecture.md),
[API interfaces](lib/contracts.ts) and [current proof](../../docs/lifecycle/plan.md#proof).

## Run locally

Use Node 24 and npm. From the repository root:

```sh
cd apps/web
npm ci
npm run dev
```

Open `http://localhost:3000`. The dashboard is `/`.

```sh
npm run typecheck
npm run build
npm start
```

Build verifies snapshot hashes, counts, evidence shards and packaged assets,
then checks snapshot inclusion in all seven API function traces. It does not
fetch Hugging Face or run Python. No database or external credentials are needed
to explore the collection; image/text extraction needs one provider below.

## Terrain and product configuration

X is observed GBP/100g, Y is a read-only trait-derived demo score and Z is one
numeric leaf trait in its original units. Family cards navigate their member
traits and show full coverage breakdowns on hover/focus/tap. Parent families
cannot supply colour layers or height. Choose a leaf enum, numeric, boolean or
string-list trait for colour: enums retain categories; numbers use five labelled
ranges fixed to the whole snapshot. Missing evidence states remain explicit.

The closed layered terrain smooths nearby numeric values without moving exact
product dots. Layer thickness is a visual category share, not a causal price
contribution. Unsupported areas remain open; smoothing and layer highlighting
are adjustable. Rotation defers geometry work, and a 2D projection provides a
fallback. The default view shows 289 complete observations; excluded counts are
available in the help control, and incomplete products remain in the matrix.

The configurator accepts typed traits, edible mass and a proposed-price slider.
Its demo score is calculated using the same fixed recipe as observed products:
base 20 with at least one recognized input, cocoa percentage × 0.30, and 10 each
for explicit organic, Fairtrade, bean-to-bar, single-origin and gift-pack claims.
The score cannot be edited directly. Price changes only the draft's price position.
This is a disclosed prototype recipe, not the teammate's fitted model.

Upload a PNG/JPEG/WebP image (up to 2 MiB) and/or description (up to 12,000
characters) to extract candidate traits. Review evidence and explicitly apply
selected candidates; the current draft and proposed price are preserved.
Copying a selected listing/resetting the draft clears stale extraction review.
Drafts stay local and never enter observed gap, brand or training analyses.
Original source evidence remains under a disclosure in the configurator.

Core range uses full-cohort Tukey bounds and discloses omitted tails. Full range
includes every usable price. Gap finder highlights interior empty price bands;
brand analysis ranks known brands with at least three observations by median
unit price. Neither establishes demand, sales, margin or a like-for-like premium.
The dashboard uses `/api/analysis` for observed-price statistics.

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

The bridge is implemented, but live extraction
could not be verified here: Codex's local app-server initialization is blocked by
this workspace (`Operation not permitted`). No Tailscale tunnel has been published.
Tailscale was not found in the checked CLI/app locations. Provider configuration
and a live text/image extraction still need completion on the laptop.

## Vercel setup

Project `rgc` in team `ptyyyy-s-projects` uses Next.js and Node 24.x, London
(`lhr1`) functions, `npm ci` and `npm run build`. This app's ignored
`.vercel/project.json` records the existing link. When connecting the whole Git
repository, set Root Directory to `apps/web` and keep the framework output default.

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
Keep the resulting `snapshot/` and manifest together. A missing/stale manifest
fails the build. The pinned Plotly bundle and its licence live in `public/vendor/`. Build verifies
them against `public/asset-manifest.json`; there is no prototype asset-copy step.
No raw archives or model training run on page requests.

## Current preview

The [terrain preview](https://rgc-hqvkpvxpj-ptyyyy-s-projects.vercel.app) is READY
with Vercel sign-in protection. The cloud build and hosted route/asset checks
passed. This is a preview; production and earlier previews remain unchanged.
Extraction correctly reports missing provider configuration.

## Validation limits

The snapshot has 3,743 listings, 103 traits and zero eligible model rows. The test fixtures added during this demo have been removed. TypeScript,
production build and data/asset integrity checks validate the current app.
See the lifecycle plan for hosted verification.

Browser layout/WebGL rendering and live model extraction remain separate from
build and HTTP checks. This sandbox cannot launch the browser or Codex's
in-process app-server. No fitted pricing benchmark is connected.
