# Application specification

## Evidence explorer

The app reads a verified immutable snapshot and serves bounded cohorts, matrix
rows, terrain data and selected source evidence. Listing, observation and draft
identities remain separate. See [API contracts](../../apps/web/lib/contracts.ts)
and the [deployment architecture](../vercel-architecture.md).

The chart uses an observed unit price, the disclosed prototype trait score and
one selected numeric leaf. Categorical layers and smoothed surfaces are visual
summaries; they do not establish causal price contributions. Missing values and
unsupported surface regions remain visible. Price slicing changes the view,
not the underlying observations or analytical population.

## Product configuration and extraction

Draft edits remain local. Users may supply text and supported photos to extract
candidate traits, review evidence and apply selected candidates to a draft.
Candidates retain uncertainty and do not become observed data or training inputs.

The server supports configured API extraction, a local signed-in Codex process,
or an authenticated bridge. Credentials remain server-side. Enforce origin,
input-size, timeout and schema checks. Missing providers return an explicit
unavailable state. Hosted deployment does not run the local CLI directly.

## Review and prediction

Persistent data corrections use the processing package's review store and
source identity checks. Agent inferences do not acquire human review status.
A prediction uses its separately verified model artifact and supported input
domain. Label synthetic or prototype behavior explicitly and report unsupported
inputs rather than fabricating a result.

Research populations, live results, source inventories and example-specific
interpretations belong in private documents. The app's configured artifact
references remain the source of deployment metadata.
