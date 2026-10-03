import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import type { AnalysisResponse, Coverage, Snapshot } from "../lib/contracts";
import { buildTraitDrilldown } from "../lib/client/trait-drilldown";
import { handleAnalysis } from "../lib/server/handlers";

const snapshot = JSON.parse(readFileSync(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;
const load = async () => (await (await handleAnalysis(new Request("http://localhost/api/analysis?scoreMode=demo"))).json()) as AnalysisResponse;

test("family drilldown ranks ten actual traits by cohort coverage and retains all remainder", async () => {
  const data = await load();
  const family = snapshot.fields.filter(field => field.group === "identity");
  const coverage: Record<string, Coverage> = Object.fromEntries(family.map((field, index) => [field.key, { known: index, unknown: 20 - index, conflict: 0, not_applicable: 0, total: 20, reviewed: 0 }]));
  const result = buildTraitDrilldown(data, snapshot.fields, coverage, "identity")!;
  assert.equal(result.series.length, 11);
  assert.deepEqual(result.series.slice(0, 10).map(item => item.key), family.slice().reverse().slice(0, 10).map(field => field.key));
  assert.equal(result.series[10].label, "Other traits");
  assert.equal(result.remainingCount, family.length - 10);
});

test("each family's trait layers reconcile to its existing score without mutating observed analysis", async () => {
  const data = await load();
  const before = structuredClone(data);
  for (const family of data.demoScores!.families) {
    const result = buildTraitDrilldown(data, snapshot.fields, undefined, family)!;
    const memberCount = snapshot.fields.filter(field => field.group === family).length;
    assert.equal(result.series.length, memberCount > 10 ? 11 : memberCount);
    for (const bin of result.bins) {
      const parent = data.demoScores!.bins.find(item => item.index === bin.index)!;
      assert.equal(bin.score, parent.score === null ? null : parent.families[family]);
      assert.ok(Math.abs(Object.values(bin.contributions).reduce((sum, value) => sum + value, 0) - (bin.score ?? 0)) < 1e-10);
      assert.ok(Object.values(bin.contributions).every(value => value >= 0));
    }
  }
  assert.deepEqual(data, before);
});

test("coverage changes which traits are shown, never the family score; missing metadata has no invented series", async () => {
  const data = await load();
  const first = buildTraitDrilldown(data, snapshot.fields, undefined, "composition")!;
  const coverage = Object.fromEntries(snapshot.fields.map(field => [field.key, { known: field.key === "composition.sweeteners" ? 100 : 0, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: 100 }]));
  const second = buildTraitDrilldown(data, snapshot.fields, coverage, "composition")!;
  assert.equal(second.series[0].key, "composition.sweeteners");
  assert.deepEqual(first.bins.map(bin => bin.score), second.bins.map(bin => bin.score));
  assert.equal(buildTraitDrilldown(data, snapshot.fields, coverage, "missing"), null);
  assert.equal(buildTraitDrilldown({ ...data, demoScores: undefined }, snapshot.fields, coverage, "identity"), null);
});
