import type { AnalysisResponse, Coverage, FieldDefinition } from "../contracts";

const TRAIT_COLOURS = ["#91e7c9", "#b9a7f3", "#ebb894", "#84c7ef", "#e9a1c7", "#d5d58b", "#7cc9bd", "#abbded", "#e5a69a", "#b4cf8a"];

/** Stable positive illustration weights, independent of trait values and coverage. */
function demoWeight(key: string): number {
  let hash = 2166136261;
  for (const char of `trait-drilldown-1:${key}`) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return 1 + (hash >>> 0) / 0xffffffff * 9;
}

export interface TraitDrilldown {
  series: { key: string; label: string; color: string }[];
  bins: { index: number; score: number | null; contributions: Record<string, number> }[];
  remainingCount: number;
}

/** Disaggregate the existing fictional parent layer; never invent trait effects. */
export function buildTraitDrilldown(data: AnalysisResponse, fields: readonly FieldDefinition[], coverage: Record<string, Coverage> | undefined, family: string): TraitDrilldown | null {
  const members = fields.filter(field => field.group === family);
  if (!members.length || !data.demoScores?.families.includes(family)) return null;
  const ranked = [...members].sort((a, b) => (coverage?.[b.key]?.known || 0) - (coverage?.[a.key]?.known || 0) || a.key.localeCompare(b.key, "en"));
  const top = ranked.slice(0, 10);
  const remainingCount = members.length - top.length;
  const otherKey = `${family}.__other__`;
  const series = top.map((field, index) => ({ key: field.key, label: field.label, color: TRAIT_COLOURS[index] }));
  if (remainingCount) series.push({ key: otherKey, label: "Other traits", color: "#647c8c" });
  const weightSum = members.reduce((sum, field) => sum + demoWeight(field.key), 0);
  return {
    series, remainingCount,
    bins: data.demoScores.bins.map(bin => {
      const score = bin.score === null ? null : bin.families[family];
      let allocated = 0;
      const contributions = Object.fromEntries(series.map((item, index) => {
        const value = score == null ? 0 : index === series.length - 1 ? score - allocated : score * demoWeight(item.key) / weightSum;
        allocated += value;
        return [item.key, value];
      }));
      return { index: bin.index, score: score ?? null, contributions };
    })
  };
}
