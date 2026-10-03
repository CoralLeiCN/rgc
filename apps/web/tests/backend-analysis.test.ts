import assert from "node:assert/strict";
import test, { before } from "node:test";
import type { AnalysisResponse, Attribute, FieldDefinition, Product, Snapshot } from "../lib/contracts";
import { GET } from "../app/api/analysis/route";
import { analyzePrices, familyEvidenceState, quantile } from "../lib/server/analysis";
import { loadSnapshot } from "../lib/server/data";
import { MAX_RESPONSE_BYTES } from "../lib/server/handlers";

let snapshot: Snapshot;
before(async () => { snapshot = await loadSnapshot(); });
const request = (query: Record<string, string> = {}) => new Request(`https://example.test/api/analysis?${new URLSearchParams(query)}`);
const attribute = (status: Attribute["status"], value: Attribute["value"]): Attribute => ({ status, value, unit: null, reviewStatus: "unreviewed" });
function listing(id: string, price: number, brand: string | null): Product {
  return { ...snapshot.products[0], id, name: id, brand, known: brand ? 1 : 0, conflicts: 0, latestPriceConflict: false,
    attributes: brand ? { "identity.brand": attribute("known", brand) } : {},
    prices: [{ observation_id: `observation-${id}`, observed_at: "2026-10-03T12:00:00Z", currency: "GBP", displayed_price: price,
      displayed_price_per_100g_gbp: price, quantity_status: "known", total_edible_weight_g: 100, model_eligible: false }],
  };
}

test("analysis route covers the entire filtered cohort and all histogram counts reconcile", async (context) => {
  const response = await GET(request());
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("x-dataset-revision"), snapshot.meta.revision);
  const raw = await response.text();
  assert.ok(Buffer.byteLength(raw) < MAX_RESPONSE_BYTES);
  const body = JSON.parse(raw) as AnalysisResponse;
  assert.equal(body.totalMatched, 3_743);
  assert.equal(body.pricedCount, 892);
  assert.equal(body.pricedCount + body.excludedPriceCount, body.totalMatched);
  assert.equal(body.histogram.status, "ready");
  assert.equal(body.histogram.bins.length, 20);
  assert.equal(body.histogram.bins.reduce((count, bin) => count + bin.count, 0), body.histogram.plottedCount);
  assert.equal(body.histogram.brands.reduce((count, brand) => count + brand.count, 0), body.histogram.plottedCount);
  assert.equal(body.histogram.plottedCount + body.histogram.belowRangeCount + body.histogram.aboveRangeCount, body.pricedCount);
  assert.ok(body.histogram.brands.filter((brand) => brand.kind === "brand").length <= 6);
  const groups = [...new Set(snapshot.fields.map((field) => field.group))].sort();
  for (const bin of body.histogram.bins) {
    assert.equal(Object.values(bin.brands).reduce((sum, count) => sum + count, 0), bin.count);
    assert.deepEqual(Object.keys(bin.familyStates).sort(), groups);
    for (const states of Object.values(bin.familyStates)) assert.equal(Object.values(states).reduce((sum, count) => sum + count, 0), bin.count);
  }
  assert.ok(body.summary);
  assert.equal(body.histogram.bins[0].lower, body.histogram.lower);
  assert.equal(body.histogram.bins[19].upper, body.histogram.upper);
  assert.equal(body.histogram.bins[19].upperInclusive, true);
  assert.ok(body.histogram.bins.slice(0, 19).every((bin) => !bin.upperInclusive));
  assert.ok(body.brandAnalysis.ranking.length <= 30);
  assert.ok(body.brandAnalysis.ranking.every((brand) => brand.pricedCount >= 3));
  assert.ok(body.brandAnalysis.ranking.every((brand, index, ranking) => index === 0 || ranking[index - 1].median >= brand.median));
  context.diagnostic(JSON.stringify({ bytes: Buffer.byteLength(raw), pricedCount: body.pricedCount, median: body.summary.median,
    gaps: body.gaps.items.length, rankedBrands: body.brandAnalysis.ranking.length, unknownBrandPricedCount: body.unknownBrandPricedCount,
    plottedCount: body.histogram.plottedCount, belowRange: body.histogram.belowRangeCount, aboveRange: body.histogram.aboveRangeCount,
    lowOutliers: body.summary.lowOutlierCount, highOutliers: body.summary.highOutlierCount }));
});

test("analysis uses cohort filters and rejects pagination/bin/axis and duplicate parameters", async () => {
  const response = await GET(request({ role: "brand", rules: '[{"field":"composition.cocoa_percentage","operator":"range","min":70}]' }));
  assert.equal(response.status, 200);
  const body = await response.json() as AnalysisResponse;
  const matched = snapshot.products.filter((product) => product.role === "brand" && product.attributes["composition.cocoa_percentage"]?.status === "known" &&
    typeof product.attributes["composition.cocoa_percentage"].value === "number" && product.attributes["composition.cocoa_percentage"].value >= 70);
  assert.equal(body.totalMatched, matched.length);
  assert.ok(body.totalMatched < snapshot.products.length);
  const invalidQueries: Record<string, string>[] = [{ page: "1" }, { bins: "10" }, { x: "coverage" }, { source: "../../secret" }, { range: "trimmed" }];
  for (const query of invalidQueries) {
    assert.equal((await GET(request(query))).status, 400);
  }
  assert.equal((await GET(new Request("https://example.test/api/analysis?role=brand&role=retail"))).status, 400);
});

test("histogram has fixed full-range bins, includes the maximum and combines minor/unknown brands", () => {
  const products = Array.from({ length: 21 }, (_, index) => listing(`p${index}`, index + 1, index < 18 ? `Brand ${Math.floor(index / 3)}` : null));
  const result = analyzePrices(products, snapshot.fields);
  assert.equal(result.histogram.bins.length, 20);
  assert.equal(result.histogram.bins[0].count, 1);
  assert.equal(result.histogram.bins[19].count, 2, "20 and the maximum 21 share the inclusive last bin");
  assert.equal(result.histogram.bins[19].brands.other, 2);
  assert.equal(result.unknownBrandPricedCount, 3);
  assert.equal(result.histogram.brands.length, 7);
  assert.equal(result.histogram.brands.find((brand) => brand.kind === "other")?.count, 3);
  assert.equal(result.brandAnalysis.ranking.length, 6);
});

test("gap finder reports only interior empty runs and adjacent occupied counts", () => {
  const products = [1, 5, 9, 13, 21].flatMap((price, group) => Array.from({ length: 4 }, (_, index) => listing(`${group}-${index}`, price, "Fixture brand")));
  const result = analyzePrices(products, snapshot.fields);
  assert.equal(result.gaps.status, "ready");
  assert.equal(result.gaps.items.length, 4);
  assert.deepEqual(result.gaps.items[0], { lower: 14, upper: 20, upperInclusive: false, emptyBinCount: 6,
    leftBinIndex: 12, rightBinIndex: 19, leftListingCount: 4, rightListingCount: 4 });
  for (const gap of result.gaps.items) {
    assert.ok(gap.lower > 1 && gap.upper < 21, "Tails are excluded");
    assert.ok(products.every((product) => product.prices[0].displayed_price_per_100g_gbp! < gap.lower || product.prices[0].displayed_price_per_100g_gbp! >= gap.upper));
  }
  assert.equal(analyzePrices(products.slice(0, 19), snapshot.fields).gaps.status, "insufficient_sample");
  const concentrated = products.map((product, index) => listing(product.id, index % 4 + 1, "Fixture brand"));
  assert.equal(analyzePrices(concentrated, snapshot.fields).gaps.status, "insufficient_spread");
});

test("empty and constant-price cohorts carry explicit readiness instead of misleading intervals", () => {
  const empty = analyzePrices([], snapshot.fields);
  assert.equal(empty.summary, null);
  assert.equal(empty.histogram.status, "no_prices");
  assert.deepEqual(empty.histogram.bins, []);
  assert.equal(empty.gaps.status, "insufficient_sample");
  assert.equal(empty.brandAnalysis.status, "insufficient_sample");
  const constant = analyzePrices(Array.from({ length: 20 }, (_, index) => listing(String(index), 5, "Constant")), snapshot.fields);
  assert.equal(constant.histogram.status, "insufficient_spread");
  assert.deepEqual(constant.histogram.bins, []);
  assert.equal(constant.gaps.status, "insufficient_spread");
  assert.equal(constant.brandAnalysis.ranking[0].premiumPercent, 0);
  assert.equal(constant.summary?.lowOutlierCount, 0);
  assert.equal(constant.summary?.highOutlierCount, 0);
});

test("brand ranking uses medians and full-cohort Tukey fences with both outlier directions", () => {
  const products: Product[] = [
    ...Array.from({ length: 15 }, (_, index) => listing(`normal-${index}`, 10 + index % 5, "Normal")),
    ...Array.from({ length: 3 }, (_, index) => listing(`low-${index}`, 1, "Low")),
    ...Array.from({ length: 3 }, (_, index) => listing(`high-${index}`, 100, "High")),
    listing("unknown", 999, null),
  ];
  const result = analyzePrices(products, snapshot.fields);
  assert.equal(result.summary?.median, 12);
  assert.equal(result.summary?.q1, 10.25);
  assert.equal(result.summary?.q3, 14);
  assert.equal(result.summary?.lowerFence, 4.625);
  assert.equal(result.summary?.upperFence, 19.625);
  assert.equal(result.summary?.lowOutlierCount, 3);
  assert.equal(result.summary?.highOutlierCount, 4);
  assert.deepEqual(result.brandAnalysis.ranking.map((brand) => brand.brand), ["High", "Normal", "Low"]);
  assert.equal(result.brandAnalysis.ranking[0].highOutlierCount, 3);
  assert.equal(result.brandAnalysis.ranking[2].lowOutlierCount, 3);
  assert.equal(result.brandAnalysis.ranking[0].premiumPercent, (100 / 12 - 1) * 100);
  const medianNotMean = analyzePrices([
    ...[1, 1, 100].map((price, index) => listing(`a${index}`, price, "A")),
    ...[2, 2, 2].map((price, index) => listing(`b${index}`, price, "B")),
  ], snapshot.fields);
  assert.deepEqual(medianNotMean.brandAnalysis.ranking.map((brand) => brand.brand), ["B", "A"]);
  assert.equal(quantile([1, 2, 3, 4], 0.25), 1.75);
});

test("brand sample thresholds, unknown identities and top-30 truncation are explicit", () => {
  const products = Array.from({ length: 31 }, (_, brand) => Array.from({ length: 3 }, (_, index) => listing(`${brand}-${index}`, brand + 1, `Brand ${String(brand).padStart(2, "0")}`))).flat();
  products.push(listing("small-1", 1000, "Small"), listing("small-2", 1000, "Small"));
  const conflicted = listing("conflicted-brand", 1000, "Claimed brand");
  conflicted.attributes["identity.brand"] = attribute("conflict", "Claimed brand");
  products.push(conflicted);
  const result = analyzePrices(products, snapshot.fields);
  assert.equal(result.brandAnalysis.totalNamedBrands, 32);
  assert.equal(result.brandAnalysis.eligibleBrandCount, 31);
  assert.equal(result.brandAnalysis.excludedBrandCount, 1);
  assert.equal(result.brandAnalysis.truncatedBrandCount, 1);
  assert.equal(result.brandAnalysis.ranking.length, 30);
  assert.equal(result.brandAnalysis.ranking[0].brand, "Brand 30");
  assert.equal(result.unknownBrandPricedCount, 1);
  assert.ok(result.brandAnalysis.ranking.every((brand) => brand.brand !== "Small" && brand.brand !== "Claimed brand"));
});

test("family histogram segments use complete membership and preserve conflict/none/N-A distinctions", () => {
  const fields: FieldDefinition[] = ["a", "b"].map((key) => ({ ...snapshot.fields[0], key, group: "composition" }));
  const products: Product[] = [
    { ...listing("complete", 1, null), attributes: { a: attribute("known", 0), b: attribute("known", false) } },
    { ...listing("partial", 2, null), attributes: { a: attribute("known", 1000) } },
    { ...listing("none", 3, null), attributes: {} },
    { ...listing("conflict", 4, null), attributes: { a: attribute("known", 1), b: attribute("conflict", [1, 2]) } },
    { ...listing("n-a", 5, null), attributes: { a: attribute("not_applicable", null), b: attribute("not_applicable", null) } },
  ];
  const result = analyzePrices(products, fields);
  const states = result.histogram.bins.map((bin) => bin.familyStates.composition);
  for (const key of ["complete", "partial", "none", "conflict", "notApplicable"] as const) assert.equal(states.reduce((sum, value) => sum + value[key], 0), 1);
  assert.equal(familyEvidenceState({ known: 0, unknown: 1, conflict: 0, not_applicable: 1, reviewed: 0, total: 2 }), "none");
});

test("analysis excludes unusable prices and never treats unreviewed as model-eligible", () => {
  const valid = listing("valid", 5, "Brand");
  const excluded = [
    { ...listing("conflict", 5, "Brand"), latestPriceConflict: true },
    ...[{ currency: "EUR" }, { quantity_status: "unknown" }, { total_edible_weight_g: 0 }, { displayed_price_per_100g_gbp: null }, { displayed_price_per_100g_gbp: -1 }]
      .map((update, index) => ({ ...listing(`invalid-${index}`, 5, "Brand"), prices: [{ ...valid.prices[0], ...update }] })),
  ];
  const result = analyzePrices([valid, ...excluded], snapshot.fields);
  assert.equal(result.pricedCount, 1);
  assert.equal(result.excludedPriceCount, 6);
  assert.equal(valid.prices[0].model_eligible, false);
  assert.equal(valid.attributes["identity.brand"].reviewStatus, "unreviewed");
});

test("core range includes exact Tukey boundaries, discloses both tails and gates gaps on displayed rows", () => {
  const prices = [3.9, 4, 10, 10, 10, 10, 11, 11, 12, 12, 12, 13, 13, 14, 14, 14, 15, 20, 20.1, 21, 30];
  const products = prices.map((price, index) => listing(String(index), price, "Fixture"));
  const core = analyzePrices(products, snapshot.fields);
  assert.equal(core.histogram.range, "core");
  assert.equal(core.histogram.lower, 4);
  assert.equal(core.histogram.upper, 20);
  assert.equal(core.histogram.plottedCount, 17);
  assert.equal(core.histogram.belowRangeCount, 1);
  assert.equal(core.histogram.aboveRangeCount, 3);
  assert.equal(core.histogram.bins[0].count, 1, "Exact lower fence remains included");
  assert.equal(core.histogram.bins[19].count, 1, "Exact upper fence remains included");
  assert.equal(core.gaps.analyzedPricedCount, 17);
  assert.equal(core.gaps.status, "insufficient_sample");
  const full = analyzePrices(products, snapshot.fields, "full");
  assert.equal(full.histogram.range, "full");
  assert.equal(full.histogram.lower, 3.9);
  assert.equal(full.histogram.upper, 30);
  assert.equal(full.histogram.plottedCount, 21);
  assert.equal(full.histogram.belowRangeCount + full.histogram.aboveRangeCount, 0);
  assert.equal(full.gaps.status, "ready");
  assert.deepEqual(core.summary, full.summary);
  assert.deepEqual(core.brandAnalysis, full.brandAnalysis);
});

test("range changes keep full-cohort brand identities and ranking while series counts describe plotted rows", () => {
  const products = [
    ...Array.from({ length: 15 }, (_, index) => listing(`normal-${index}`, 10 + index % 5, "Normal")),
    ...Array.from({ length: 3 }, (_, index) => listing(`low-${index}`, 1, "Low")),
    ...Array.from({ length: 3 }, (_, index) => listing(`high-${index}`, 100, "High")),
    listing("unknown", 999, null),
  ];
  const core = analyzePrices(products, snapshot.fields), full = analyzePrices(products, snapshot.fields, "full");
  assert.deepEqual(core.histogram.brands.map(({ key, label }) => ({ key, label })), full.histogram.brands.map(({ key, label }) => ({ key, label })));
  assert.equal(core.histogram.brands.find((brand) => brand.label === "High")?.count, 0);
  assert.equal(full.histogram.brands.find((brand) => brand.label === "High")?.count, 3);
  assert.equal(core.histogram.brands.reduce((count, brand) => count + brand.count, 0), core.histogram.plottedCount);
  assert.deepEqual(core.brandAnalysis, full.brandAnalysis);
  assert.equal(core.unknownBrandPricedCount, full.unknownBrandPricedCount);
});

test("zero-IQR core selection explicitly falls back to the full range", () => {
  const products = [...Array.from({ length: 20 }, (_, index) => listing(String(index), 5, "Fixture")), listing("tail", 100, "Tail")];
  const result = analyzePrices(products, snapshot.fields);
  assert.equal(result.summary?.q1, result.summary?.q3);
  assert.equal(result.histogram.range, "full");
  assert.match(result.histogram.rangeFallbackReason ?? "", /interquartile range is zero/i);
  assert.equal(result.histogram.upper, 100);
  assert.equal(result.histogram.plottedCount, 21);
  assert.equal(result.histogram.aboveRangeCount, 0);
  assert.equal(result.summary?.highOutlierCount, 1, "Full-cohort outlier statistics do not change with the display fallback");
});
