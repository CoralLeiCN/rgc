import type { JsonValue } from "./contracts";

export const TRAIT_DEMO_VERSION = "trait-demo-1" as const;
export const TRAIT_DEMO_BASE = 20;
export const TRAIT_DEMO_RULES = [
  { field: "composition.cocoa_percentage", label: "Cocoa percentage", kind: "percentage", maxPoints: 30, definition: "0.30 points per cocoa percentage point; valid range 0–100%." },
  { field: "certifications.organic_claim", label: "Organic claim", kind: "claim", maxPoints: 10, definition: "10 points when the organic claim is explicitly present; 0 when explicitly absent." },
  { field: "certifications.fairtrade_claim", label: "Fairtrade claim", kind: "claim", maxPoints: 10, definition: "10 points when the Fairtrade claim is explicitly present; 0 when explicitly absent." },
  { field: "processing.bean_to_bar_claim", label: "Bean-to-bar claim", kind: "claim", maxPoints: 10, definition: "10 points when the bean-to-bar claim is explicitly present; 0 when explicitly absent." },
  { field: "origin.single_origin_claim", label: "Single-origin claim", kind: "claim", maxPoints: 10, definition: "10 points when the single-origin claim is explicitly present; 0 when explicitly absent." },
  { field: "packaging.gift_pack_claim", label: "Gift-pack claim", kind: "claim", maxPoints: 10, definition: "10 points when the gift-pack claim is explicitly present; 0 when explicitly absent." },
] as const;

export const TRAIT_DEMO_DEFINITION = "Prototype trait recipe, not a fitted pricing model or quality rating: base 20 when at least one recognized scoring input is known; cocoa percentage × 0.30 (up to 30); plus 10 each for explicit organic, Fairtrade, bean-to-bar, single-origin and gift-pack claims. Explicitly absent claims add 0. Missing, conflicting, truncated and invalid inputs are omitted, not inferred absent. No recognized inputs means no score. Maximum 100. Identities and prices never affect this score; model or training eligibility is unchanged.";

export interface TraitDemoScore {
  score: number | null; contributions: Record<string, number>; knownInputs: number;
  definition: string; version: typeof TRAIT_DEMO_VERSION;
}

/** Callers pass only known, non-conflicting, non-truncated values, never evidence envelopes. */
export function calculateTraitDemoScore(traits: Record<string, JsonValue>): TraitDemoScore {
  const contributions: Record<string, number> = {};
  let knownInputs = 0;
  for (const rule of TRAIT_DEMO_RULES) {
    if (!Object.hasOwn(traits, rule.field)) continue;
    const value = traits[rule.field];
    if (rule.kind === "percentage") {
      if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 100) continue;
      contributions[rule.field] = value / 100 * rule.maxPoints;
    } else {
      if (value !== "present" && value !== "absent") continue;
      contributions[rule.field] = value === "present" ? rule.maxPoints : 0;
    }
    knownInputs++;
  }
  if (knownInputs) contributions.base = TRAIT_DEMO_BASE;
  const score = knownInputs ? Object.values(contributions).reduce((sum, value) => sum + value, 0) : null;
  return { score, contributions, knownInputs, definition: TRAIT_DEMO_DEFINITION, version: TRAIT_DEMO_VERSION };
}
