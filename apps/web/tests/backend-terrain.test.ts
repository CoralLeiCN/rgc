import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import type { Attribute, FieldDefinition, JsonValue, Product, Snapshot, TerrainResponse } from "../lib/contracts";
import { calculateTraitDemoScore, TRAIT_DEMO_BASE, TRAIT_DEMO_RULES } from "../lib/trait-demo";
import { buildTerrain, handleTerrain } from "../lib/server/terrain";

const snapshot = JSON.parse(readFileSync(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;
const field = (key: string) => snapshot.fields.find(item => item.key === key)!;
const known = (value: JsonValue): Attribute => ({ value, status: "known", unit: null, reviewStatus: "unreviewed" });
const row = (id: string, price = 5, attributes: Record<string, Attribute> = {}): Product => ({
  id, name: id, brand: null, retailer: null, source: "test", role: "retail", reviewStatus: "unreviewed", attributes,
  known: Object.values(attributes).filter(value => value.status === "known").length, conflicts: 0,
  prices: [{ observation_id: `obs-${id}`, observed_at: "2026-01-01", currency: "GBP", displayed_price: price, displayed_price_per_100g_gbp: price, total_edible_weight_g: 100, quantity_status: "known", model_eligible: false }],
  latestPriceConflict: false, sourceListingIds: [id],
});
const fixture = (products: Product[], fields = snapshot.fields): Snapshot => ({ ...snapshot, products, fields });
const request = (params: Record<string, string> = {}) => new Request(`http://localhost/api/terrain?${new URLSearchParams(params)}`);
const load = async (params: Record<string, string> = {}) => {
  const response = await handleTerrain(request(params));
  assert.equal(response.status, 200);
  return await response.json() as TerrainResponse;
};

test("shared trait score is an explicit additive recipe independent of identity and price", () => {
  for (const rule of TRAIT_DEMO_RULES) assert.ok(field(rule.field), "All scoring rules use real schema keys");
  const traits = Object.fromEntries(TRAIT_DEMO_RULES.map(rule => [rule.field, rule.kind === "percentage" ? 100 : "present"]));
  const result = calculateTraitDemoScore(traits);
  assert.equal(result.score, 100);
  assert.equal(result.knownInputs, 6);
  assert.equal(Object.values(result.contributions).reduce((sum, value) => sum + value, 0), 100);
  assert.equal(result.contributions.base, TRAIT_DEMO_BASE);
  assert.equal(result.version, "trait-demo-1");
  assert.deepEqual(calculateTraitDemoScore({ ...traits, "identity.name": "Different name", price: 1_000_000 }), result);
  assert.equal(calculateTraitDemoScore({ "composition.cocoa_percentage": 70 }).score, 41);
  assert.equal(calculateTraitDemoScore({ "composition.cocoa_percentage": 0 }).score, 20);
  assert.equal(calculateTraitDemoScore({ "certifications.organic_claim": "absent" }).score, 20);
  for (const traits of [{}, { price: 20 }, { "composition.cocoa_percentage": 101 }, { "composition.cocoa_percentage": -1 }, { "composition.cocoa_percentage": "70" }, { "composition.cocoa_percentage": NaN }, { "certifications.organic_claim": true }, { "certifications.organic_claim": "unknown" }]) {
    const score = calculateTraitDemoScore(traits as Record<string, JsonValue>);
    assert.equal(score.score, null);
    assert.equal(score.knownInputs, 0);
    assert.deepEqual(score.contributions, {});
  }
});

test("actual terrain endpoint obeys observed-price bounds, count identities and category share sums", async t => {
  const response = await handleTerrain(request());
  const bytes = await response.text();
  assert.equal(response.status, 200);
  assert.ok(Buffer.byteLength(bytes) < 4_000_000);
  const data = JSON.parse(bytes) as TerrainResponse;
  assert.equal(data.totalMatched, snapshot.products.length);
  assert.equal(data.limit, 1_000);
  assert.equal(data.color.key, "composition.chocolate_type");
  assert.equal(data.z.key, "composition.cocoa_percentage");
  assert.equal(data.completeCount + data.excludedCount, data.totalMatched);
  assert.ok(data.completeCount <= data.pricedCount);
  assert.ok(data.rows.length > 0 && data.rows.length <= data.limit);
  for (const result of data.rows) {
    const product = snapshot.products.find(product => product.id === result.id)!;
    assert.equal(result.price, product.prices[0].displayed_price_per_100g_gbp);
    assert.ok(result.price >= data.priceRange![0] && result.price <= data.priceRange![1]);
    assert.ok(result.score >= 0 && result.score <= 100);
    assert.ok(Number.isFinite(result.z));
    assert.ok(Math.abs(Object.values(result.categories).reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
  }
  t.diagnostic(JSON.stringify({ total: data.totalMatched, priced: data.pricedCount, complete: data.completeCount, missingScore: data.missingScoreCount, missingZ: data.missingZCount, below: data.belowRangeCount, above: data.aboveRangeCount, bytes: Buffer.byteLength(bytes) }));
});

test("strict terrain query validation rejects wrong schema types, unknown keys and malformed cohort rules", async () => {
  const cases: Record<string, string>[] = [
    { color: "identity.name" }, { color: "no-such-field" },
    { color: "family:storage" }, { color: "family:composition" }, { z: "family:composition" }, { z: "composition.chocolate_type" }, { z: "family:dietary" },
    { limit: "0" }, { limit: "2001" }, { limit: "1.5" }, { range: "other" }, { unknown: "yes" },
    { source: "../snapshot" }, { search: "x".repeat(201) }, { rules: "{}" },
    { rules: JSON.stringify([{ field: "composition.cocoa_percentage", operator: "equals", value: 80 }]) },
  ];
  for (const params of cases) {
    const response = await handleTerrain(request(params));
    assert.equal(response.status, 400, JSON.stringify(params));
    assert.equal(response.headers.get("Cache-Control"), "no-store");
  }
  assert.equal((await handleTerrain(new Request("http://localhost/api/terrain?color=composition.chocolate_type&color=family:identity"))).status, 400);
});

test("unknown, conflicting and truncated scoring or Z attributes are excluded without changing model eligibility", () => {
  const data = fixture([
    row("valid", 5, { "composition.cocoa_percentage": known(80) }),
    ...["unknown", "conflict", "not_applicable"].map(status => row(status, 5, { "composition.cocoa_percentage": { ...known(80), status: status as Attribute["status"] } })),
    row("truncated", 5, { "composition.cocoa_percentage": { ...known(80), truncated: true } }),
    row("unknown-score", 5, { "storage.temperature_min_c": known(-5) }),
  ]);
  const before = JSON.stringify(data);
  const result = buildTerrain(data, new URLSearchParams({ range: "full" }));
  assert.deepEqual(result.rows.map(row => row.id), ["valid"]);
  assert.equal(result.rows[0].score, 44);
  assert.equal(result.missingScoreCount, 5);
  assert.equal(result.missingZCount, 5);
  assert.equal(JSON.stringify(data), before);
  const knownAbsent = buildTerrain(fixture([row("absent", 5, { "certifications.organic_claim": known("absent"), "storage.temperature_min_c": known(-5) })]), new URLSearchParams({ z: "storage.temperature_min_c" }));
  assert.equal(knownAbsent.rows[0].score, 20);
  assert.equal(knownAbsent.rows[0].z, -5, "A valid negative raw numeric value is retained");
});

test("leaf categorical values retain missing states and split list values without blending parent families", () => {
  const products = [
    row("multi", 5, { "composition.cocoa_percentage": known(70), "composition.inclusions": known(["nut", "salt", "nut"]) }),
    row("missing", 5, { "composition.cocoa_percentage": known(70) }),
    ...["not_applicable", "conflict"].map(status => row(status, 5, { "composition.cocoa_percentage": known(70), "composition.inclusions": { ...known(null), status: status as Attribute["status"] } })),
    row("empty", 5, { "composition.cocoa_percentage": known(70), "composition.inclusions": known([]) }),
    row("truncated", 5, { "composition.cocoa_percentage": known(70), "composition.inclusions": { ...known(["nut"]), truncated: true } }),
  ];
  const result = buildTerrain(fixture(products), new URLSearchParams({ color: "composition.inclusions" }));
  assert.deepEqual(result.rows.find(row => row.id === "multi")!.categories, { "composition.inclusions=value:nut": .5, "composition.inclusions=value:salt": .5 });
  for (const state of ["unknown", "not_applicable", "conflict", "truncated", "empty"]) assert.ok(result.categories.some(category => category.key.endsWith(`=state:${state}`)));
  for (const row of result.rows) assert.equal(Object.values(row.categories).reduce((sum, share) => sum + share, 0), 1);
  const boolean: FieldDefinition = { ...field("composition.chocolate_type"), key: "composition.flag", type: "boolean", allowedValues: [] };
  const booleans = buildTerrain(fixture([row("false", 5, { "composition.cocoa_percentage": known(70), "composition.flag": known(false) })], [...snapshot.fields, boolean]), new URLSearchParams({ color: "composition.flag" }));
  assert.deepEqual(booleans.rows[0].categories, { "composition.flag=value:false": 1 });
});

test("numeric colour bands use immutable snapshot bounds; Z stays a single raw trait", () => {
  const products = [
    row("low", 1, { "composition.cocoa_percentage": known(20), "storage.temperature_min_c": known(-10) }),
    row("middle", 2, { "composition.cocoa_percentage": known(60), "storage.temperature_min_c": known(0) }),
    row("high", 3, { "composition.cocoa_percentage": known(100), "storage.temperature_min_c": known(10) }),
    row("missing", 4, { "composition.cocoa_percentage": known(70) }),
  ];
  const data = fixture(products);
  const all = buildTerrain(data, new URLSearchParams({ color: "storage.temperature_min_c", range: "full" }));
  assert.deepEqual(all.rows.find(row => row.id === "low")!.categories, { "storage.temperature_min_c=range:0": 1 });
  assert.deepEqual(all.rows.find(row => row.id === "middle")!.categories, { "storage.temperature_min_c=range:2": 1 });
  assert.deepEqual(all.rows.find(row => row.id === "high")!.categories, { "storage.temperature_min_c=range:4": 1 });
  assert.deepEqual(all.rows.find(row => row.id === "missing")!.categories, { "storage.temperature_min_c=state:unknown": 1 });
  assert.equal(all.rows.find(row => row.id === "middle")!.z, 60);
  assert.equal(all.z.unit, field("composition.cocoa_percentage").unit);
  assert.ok(all.categories.some(category => category.label.includes("-10")));
  const filtered = buildTerrain(data, new URLSearchParams({ color: "storage.temperature_min_c", range: "full", search: "middle" }));
  assert.deepEqual(filtered.rows, all.rows.filter(row => row.id === "middle"));
  assert.equal(filtered.categories[0].label, all.categories.find(category => category.key === filtered.categories[0].key)!.label);
  const constant = buildTerrain(fixture([products[0]]), new URLSearchParams({ color: "storage.temperature_min_c" }));
  assert.equal(constant.categories[0].label, `${field("storage.temperature_min_c").label}: -10 ${field("storage.temperature_min_c").unit}`);
  assert.throws(() => buildTerrain(data, new URLSearchParams({ z: "family:composition" })), /one numeric leaf/);
  assert.throws(() => buildTerrain(data, new URLSearchParams({ color: "family:composition" })), /Parent families/);
});

test("core price range uses the full priced cohort before completeness, preserves bounds and discloses tails", () => {
  const data = fixture(Array.from({ length: 21 }, (_, index) => row(`p${index}`, index === 20 ? 1000 : index + 1, { "composition.cocoa_percentage": known(70) })));
  const core = buildTerrain(data, new URLSearchParams()), full = buildTerrain(data, new URLSearchParams({ range: "full" }));
  assert.equal(core.pricedCount, 21);
  assert.equal(core.completeCount, 20);
  assert.equal(core.aboveRangeCount, 1);
  assert.equal(core.belowRangeCount, 0);
  assert.equal(full.completeCount, 21);
  assert.deepEqual(full.priceRange, [1, 1000]);
  assert.ok(full.rows.some(row => row.price === full.priceRange![1]), "Maximum observed price is included");
  const equal = buildTerrain(fixture([row("one", 3, { "composition.cocoa_percentage": known(70) })]), new URLSearchParams());
  assert.equal(equal.range, "full");
  assert.equal(equal.requestedRange, "core");
  assert.ok(equal.rangeFallbackReason);
  assert.deepEqual(equal.priceRange, [3, 3]);
});

test("stable ID sampling follows completeness and cohort rules; category counts are pre-sampling", () => {
  const data = fixture(Array.from({ length: 2050 }, (_, index) => row(`p${String(index).padStart(4, "0")}`, 5, { "composition.cocoa_percentage": known(index % 101) })));
  const params = new URLSearchParams({ limit: "2000", range: "full", rules: JSON.stringify([{ field: "composition.cocoa_percentage", operator: "range", min: 0 }]) });
  const result = buildTerrain(data, params);
  assert.equal(result.completeCount, 2050);
  assert.equal(result.rows.length, 2000);
  assert.equal(result.sampled, true);
  assert.equal(new Set(result.rows.map(row => row.id)).size, 2000);
  assert.equal(result.categories[0].count, 2050);
  assert.deepEqual(result.rows, buildTerrain(fixture([...data.products].reverse()), params).rows);
  const filtered = buildTerrain(data, new URLSearchParams({ rules: JSON.stringify([{ field: "composition.cocoa_percentage", operator: "range", min: 90 }]) }));
  assert.ok(filtered.rows.every(row => row.z >= 90));
  const empty = buildTerrain(data, new URLSearchParams({ search: "no-such-terrain-listing" }));
  assert.equal(empty.totalMatched, 0);
  assert.equal(empty.priceRange, null);
  assert.deepEqual(empty.rows, []);
});

test("terrain excludes conflicting prices, wrong currency and unproven same-observation weights", () => {
  const base = row("valid", 5, { "composition.cocoa_percentage": known(70) });
  const variants = [
    { ...base, id: "conflict", latestPriceConflict: true },
    { ...base, id: "currency", prices: [{ ...base.prices[0], currency: "USD" }] },
    { ...base, id: "quantity", prices: [{ ...base.prices[0], quantity_status: "unknown" }] },
    { ...base, id: "zero", prices: [{ ...base.prices[0], total_edible_weight_g: 0 }] },
  ];
  const result = buildTerrain(fixture([base, ...variants]), new URLSearchParams());
  assert.equal(result.pricedCount, 1);
  assert.deepEqual(result.rows.map(row => row.id), ["valid"]);
});

test("full snapshot leaf selections stay within the response cap", async () => {
  for (const params of [
    { color: "composition.cocoa_percentage", z: "nutrition.sugars_g_per_100g", limit: "2000", range: "full" },
    { color: "composition.chocolate_type", z: "composition.cocoa_percentage", limit: "2000", range: "full" },
  ]) {
    const response = await handleTerrain(request(params));
    assert.equal(response.status, 200);
    assert.ok(Buffer.byteLength(await response.text()) < 4_000_000);
  }
  const filtered = await load({ status: "unpriced" });
  assert.equal(filtered.pricedCount, 0);
  assert.equal(filtered.rows.length, 0);
});
