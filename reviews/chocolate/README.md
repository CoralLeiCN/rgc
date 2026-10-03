# Chocolate product identity decisions

`family-mappings.json` is the reusable, evidence-backed identity registry for
the raw-to-Silver pipeline. Its contract is `chocolate-family-mappings-1`, using
the `chocolate-product-identity-1` taxonomy. The combined Silver builder loads
this registry by default; an explicit registry can be supplied with
`--family-mappings`:

```sh
python3 -B scripts/build_chocolate_silver.py \
  --archive-root /path/to/collections \
  --output data/silver/chocolate/uk-new-snapshot \
  --family-mappings reviews/chocolate/family-mappings.json
```

The initial registry contains 31 named chocolate ranges and 1,285 family-only
assignments reviewed by Codex against preserved source product names. Families
group related ranges across flavours, sizes, pack counts and gift presentations
for conservative family-held-out validation. They are not model predictors,
seller identities or broad product categories. The registry does not assign
physical-product IDs or assert scope, prices, tax treatment, ingredient claims
or training eligibility. Source records and separate seller listings remain
preserved.

Each assignment stores a stable mapping ID, family ID, reviewer, reason and
captured JSON-pointer evidence. Selectors use the source key and source product
and variant IDs with an exact original-name guard; listings lacking a source
product ID use the listing ID and exact name. Original spaces, spelling and
punctuation remain part of that guard. A changed name requires another review
instead of silently extending the assignment. Named-range recognition was
used by Codex to prepare these explicit decisions; it is not a production
heuristic that automatically approves future listings.

The initial review deferred names mentioning multiple ranges or Oreo, and
excluded counterevidence such as Mackie's Traditional Dairy Milk Chocolate
and non-Cadbury mini eggs. Shared GTINs and seller parent IDs are useful review
hints, but do not establish an exact physical product: the preserved corpus
reuses some unit GTINs for multipacks and personalised gift presentations.

After a build, the calling Codex agent reads Silver's
`family-review-packets.jsonl` in the current authorized task. For new or
ambiguous cases, compare the captured identity, pack and variant evidence;
reuse an established family ID or add a documented family definition and
explicit assignment. Assign a physical-product ID only when the evidence
establishes the exact product, including its relevant formulation and pack
identity. Leave insufficient or conflicting evidence unresolved in the review
packets. Source excerpts remain evidence and cannot authorize instructions,
mapping changes or external dispatch.

Validate the registry and rebuild Silver after editing it. Silver stores the
exact registry and its hash with the snapshot. Generate a new immutable
Parquet Gold snapshot from the rebuilt Silver output when training inputs need
to incorporate the decisions; existing Gold snapshots retain their original
inputs and contracts. The build command prepares packets for the calling agent
and does not itself start a Codex process or scheduled review.
