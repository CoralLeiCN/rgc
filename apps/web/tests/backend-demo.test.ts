import assert from "node:assert/strict";
import test, { before } from "node:test";
import type { AnalysisResponse, Product, Snapshot } from "../lib/contracts";
import { GET } from "../app/api/analysis/route";
import { analyzePrices } from "../lib/server/analysis";
import { loadSnapshot } from "../lib/server/data";
import { listingDemoScore } from "../lib/server/demo-score";
import { MAX_RESPONSE_BYTES } from "../lib/server/handlers";

let snapshot: Snapshot;
before(async () => { snapshot = await loadSnapshot(); });
const request = (query = "") => new Request(`https://example.test/api/analysis?${query}`);
const near = (actual: number, expected: number) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} should equal ${expected} within rounding precision`);
function listing(id: string, price: number): Product {
  return { ...snapshot.products[0], id, name: id, brand: null, known: 0, conflicts: 0, latestPriceConflict: false, attributes: {},
    prices: [{ observation_id: `observation-${id}`, observed_at: "2026-10-03T12:00:00Z", currency: "GBP", displayed_price: price,
      displayed_price_per_100g_gbp: price, quantity_status: "known", total_edible_weight_g: 100, model_eligible: false }],
  };
}

test("demo scores are explicit opt-in and leave all real analysis fields unchanged", async (context) => {
  const ordinary = await GET(request());
  const demo = await GET(request("scoreMode=demo"));
  assert.equal(ordinary.status, 200);
  assert.equal(demo.status, 200);
  const baseline = await ordinary.json() as AnalysisResponse;
  assert.equal(Object.hasOwn(baseline, "demoScores"), false);
  const raw = await demo.text();
  assert.ok(Buffer.byteLength(raw) < MAX_RESPONSE_BYTES);
  const enhanced = JSON.parse(raw) as AnalysisResponse;
  const { demoScores, ...observed } = enhanced;
  assert.deepEqual(observed, baseline);
  assert.ok(demoScores);
  assert.match(demoScores.label, /demo.*fictional/i);
  assert.match(demoScores.definition, /independently of observed prices, raw traits and evidence coverage/);
  assert.equal(demoScores.version, "demo-score-1");
  assert.deepEqual(demoScores.range, [0, 100]);
  assert.deepEqual(demoScores.families, [...new Set(snapshot.fields.map((field) => field.group))]);
  assert.equal(demoScores.bins.length, enhanced.histogram.bins.length);
  for (const bin of demoScores.bins) {
    const histogramBin = enhanced.histogram.bins[bin.index];
    assert.equal(histogramBin.index, bin.index);
    assert.deepEqual(Object.keys(bin.families), demoScores.families);
    if (histogramBin.count === 0) {
      assert.equal(bin.score, null);
      assert.ok(Object.values(bin.families).every((value) => value === 0));
    } else {
      assert.ok(bin.score !== null && bin.score >= 0 && bin.score <= 100);
      assert.ok(Object.values(bin.families).every((value) => Number.isFinite(value) && value >= 0));
      near(Object.values(bin.families).reduce((sum, value) => sum + value, 0), bin.score);
    }
  }
  context.diagnostic(JSON.stringify({ demoBytes: Buffer.byteLength(raw), bins: demoScores.bins.length,
    emptyBins: demoScores.bins.filter((bin) => bin.score === null).length, families: demoScores.families.length }));
});

test("score mode accepts only demo or absence and remains subject to strict query validation", async () => {
  for (const mode of ["", "real", "false", "none", "DEMO"]) assert.equal((await GET(request(`scoreMode=${mode}`))).status, 400);
  assert.equal((await GET(request("scoreMode=demo&scoreMode=demo"))).status, 400);
  assert.equal((await GET(request("scoreMode=demo&range=invalid"))).status, 400);
  assert.equal((await GET(request("scoreMode=demo&unknown=true"))).status, 400);
});

test("per-listing fictional scores are deterministic, bounded, and independent of family evidence", () => {
  const families = ["composition", "certifications", "nutrition"];
  for (let index = 0; index < 100; index++) {
    const first = listingDemoScore(`fixture-${index}`, families);
    assert.deepEqual(listingDemoScore(`fixture-${index}`, families), first);
    assert.ok(first.score >= 0 && first.score <= 100);
    assert.ok(Object.values(first.families).every((value) => value >= 0));
    near(Object.values(first.families).reduce((sum, value) => sum + value, 0), first.score);
  }
  assert.notDeepEqual(listingDemoScore("fixture-a", families), listingDemoScore("fixture-b", families));
  assert.equal(listingDemoScore("fixture-a", families).score, listingDemoScore("fixture-a", ["other"]).score,
    "The scalar score depends only on stable listing identity");
});

test("moving listing prices changes only bin placement while synthetic values ignore raw traits and coverage", () => {
  const original = [listing("a", 5), listing("b", 10), listing("c", 15)];
  const changed = [listing("a", 15), listing("b", 10), listing("c", 5)].map((product) => ({ ...product, known: 100,
    attributes: { "composition.cocoa_percentage": { value: 99, status: "known" as const, unit: "%", reviewStatus: "reviewed" as const } },
  }));
  const first = analyzePrices(original, snapshot.fields, "full", "demo");
  const second = analyzePrices(changed, snapshot.fields, "full", "demo");
  assert.ok(first.demoScores && second.demoScores);
  assert.deepEqual(first.demoScores.bins[0].families, second.demoScores.bins[19].families);
  assert.equal(first.demoScores.bins[0].score, second.demoScores.bins[19].score);
  assert.deepEqual(first.demoScores.bins[19].families, second.demoScores.bins[0].families);
  assert.equal(first.demoScores.bins[10].score, second.demoScores.bins[10].score);
  const originalBefore = JSON.stringify(original);
  const subset = analyzePrices([original[0], original[2]], snapshot.fields, "full", "demo");
  assert.deepEqual(subset.demoScores?.bins[0], first.demoScores.bins[0], "A retained listing keeps its score when cohort membership changes");
  assert.equal(JSON.stringify(original), originalBefore, "Synthetic aggregation never mutates evidence or eligibility");
});

test("each displayed bin averages per-listing fictional contributions and range toggles preserve the underlying seeds", () => {
  const products = [...Array.from({ length: 20 }, (_, index) => listing(`fixture-${index}`, 5 + index)), listing("tail", 1000)];
  const families = [...new Set(snapshot.fields.map((field) => field.group))];
  for (const range of ["core", "full"] as const) {
    const result = analyzePrices(products, snapshot.fields, range, "demo");
    assert.ok(result.demoScores);
    for (const bin of result.histogram.bins) {
      const members = products.filter((product) => {
        const price = product.prices[0].displayed_price_per_100g_gbp!;
        return price >= bin.lower && (bin.upperInclusive ? price <= bin.upper : price < bin.upper);
      });
      assert.equal(members.length, bin.count);
      if (!members.length) continue;
      const values = members.map((product) => listingDemoScore(product.id, families));
      const actual = result.demoScores.bins[bin.index];
      near(actual.score!, values.reduce((sum, value) => sum + value.score, 0) / values.length);
      for (const family of families) near(actual.families[family], values.reduce((sum, value) => sum + value.families[family], 0) / values.length);
    }
    const plain = analyzePrices(products, snapshot.fields, range);
    const { demoScores: _demoScores, ...real } = result;
    assert.deepEqual(real, plain);
  }
});

test("empty and constant-price cohorts do not manufacture demo bins or scores", () => {
  for (const products of [[], [listing("a", 5), listing("b", 5)]]) {
    const result = analyzePrices(products, snapshot.fields, "core", "demo");
    assert.deepEqual(result.histogram.bins, []);
    assert.deepEqual(result.demoScores?.bins, []);
    assert.equal(result.demoScores?.families.length, 11);
  }
});
