import { createHash } from "node:crypto";
import type { DemoScores, PriceHistogramBin } from "../contracts";

const VERSION = "demo-score-1" as const;

/** Stable illustration seed; input values contain identities only, never evidence or prices. */
function seededUnit(...identities: string[]): number {
  return createHash("sha256").update(JSON.stringify([VERSION, ...identities])).digest().readUInt32BE(0) / 0xffffffff;
}

export function listingDemoScore(listingId: string, familyKeys: readonly string[]): { score: number; families: Record<string, number> } {
  const keys = [...new Set(familyKeys)];
  if (!keys.length) throw new Error("Demo scores require a schema family");
  const score = 100 * seededUnit("score", listingId);
  const weights = keys.map((key) => 1 + 9 * seededUnit("family", listingId, key));
  const totalWeight = weights.reduce((total, weight) => total + weight, 0);
  let allocated = 0;
  const families = Object.fromEntries(keys.map((key, index) => {
    const contribution = index === keys.length - 1 ? score - allocated : score * weights[index] / totalWeight;
    allocated += contribution;
    return [key, contribution];
  }));
  return { score, families };
}

/** Average fictional contributions over exactly the rows counted in each observed price bin. */
export function buildDemoScores(familyKeys: readonly string[], bins: readonly PriceHistogramBin[], items: readonly { listingId: string; index: number }[]): DemoScores {
  const families = [...new Set(familyKeys)];
  const totals = new Map(bins.map((bin) => [bin.index, { count: 0, score: 0, families: Object.fromEntries(families.map((key) => [key, 0])) }]));
  for (const item of items) {
    const bin = totals.get(item.index);
    if (!bin) throw new Error("Demo score references an unknown histogram bin");
    const generated = listingDemoScore(item.listingId, families);
    bin.count++;
    bin.score += generated.score;
    for (const family of families) bin.families[family] += generated.families[family];
  }
  return {
    label: "Demo pricing score — fictional",
    definition: "Mean fictional score for listings in each displayed price band. Scores and positive family weights are seeded only by listing IDs and schema family IDs, independently of observed prices, raw traits and evidence coverage. These are illustrative values, not a fitted model, quality assessment or measured trait contribution.",
    version: VERSION, range: [0, 100], families,
    bins: bins.map((bin) => {
      const total = totals.get(bin.index)!;
      if (total.count !== bin.count) throw new Error("Demo and observed histogram counts disagree");
      if (!total.count) return { index: bin.index, score: null, families: total.families };
      const score = total.score / total.count;
      let allocated = 0;
      const contributions = Object.fromEntries(families.map((family, index) => {
        const value = index === families.length - 1 ? score - allocated : total.families[family] / total.count;
        allocated += value;
        return [family, value];
      }));
      return { index: bin.index, score, families: contributions };
    }),
  };
}
