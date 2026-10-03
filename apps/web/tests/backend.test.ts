import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test, { before } from "node:test";
import type { Attribute, FieldDefinition, Product, ProductsResponse, PointsResponse, SchemaResponse, ProductResponse, Snapshot } from "../lib/contracts";
import { loadSnapshot } from "../lib/server/data";
import { ApiError } from "../lib/server/errors";
import { boundedJson, handleCompare, handlePoints, handleProduct, handleProducts, handleSchema, MAX_RESPONSE_BYTES } from "../lib/server/handlers";
import { axisValue, coverage, fieldFamilies, filterProducts, matchesRule, parseCohort, productFamilyCoverage } from "../lib/server/query";
import { GET as schemaGET } from "../app/api/schema/route";
import { GET as productGET } from "../app/api/products/[id]/route";

const request = (pathname: string, query: Record<string, string> = {}) => new Request(`https://example.test${pathname}?${new URLSearchParams(query)}`);
let snapshot: Snapshot;
before(async () => { snapshot = await loadSnapshot(); });

async function json<T>(response: Response): Promise<T> {
  assert.equal(response.status, 200);
  const text = await response.text();
  assert.ok(Buffer.byteLength(text) <= MAX_RESPONSE_BYTES);
  assert.equal(response.headers.get("x-dataset-revision"), snapshot.meta.revision);
  assert.match(response.headers.get("cache-control") ?? "", /s-maxage=60/);
  return JSON.parse(text) as T;
}

async function invalidResponse(response: Response, status = 400) {
  assert.equal(response.status, status);
  assert.equal(response.headers.get("cache-control"), "no-store");
  const body = await response.json();
  assert.deepEqual(Object.keys(body), ["error"]);
  assert.equal(typeof body.error.code, "string");
  assert.equal(typeof body.error.message, "string");
  assert.equal(/\/Users\/|\.ts:|stack/i.test(body.error.message), false);
}

test("schema route exposes all snapshot fields and axes without product records", async () => {
  const body = await json<SchemaResponse>(await schemaGET(request("/api/schema")));
  assert.equal(body.meta.schemaValidatedListings, snapshot.products.length);
  assert.equal(body.fields.length, 103);
  assert.equal(body.contract.selectedPredictors.length, 11);
  assert.equal(body.sources.reduce((count, source) => count + source.count, 0), snapshot.products.length);
  assert.equal(body.axes.length, snapshot.fields.filter((field) => field.numeric).length + 5);
  assert.equal(Object.hasOwn(body, "products"), false);
  assert.equal(body.meta.counts.eligible_model_inputs, 0);
});

test("pagination is bounded while coverage describes the complete cohort", async () => {
  const first = await json<ProductsResponse>(await handleProducts(request("/api/products")));
  const second = await json<ProductsResponse>(await handleProducts(request("/api/products", { page: "2" })));
  assert.equal(first.products.length, 25);
  assert.equal(first.total, snapshot.products.length);
  assert.equal(first.totalPages, Math.ceil(snapshot.products.length / 25));
  assert.equal(first.coverage["identity.name"].total, snapshot.products.length);
  assert.equal(first.coverage["identity.name"].known, snapshot.products.length);
  assert.equal(first.products.some((product) => second.products.some((other) => other.id === product.id)), false);
  for (const counts of Object.values(first.coverage)) {
    assert.equal(counts.known + counts.unknown + counts.conflict + counts.not_applicable, first.total);
  }
  const empty = await json<ProductsResponse>(await handleProducts(request("/api/products", { search: "no-such-collection-product-123456789" })));
  assert.equal(empty.total, 0);
  assert.equal(empty.totalPages, 0);
  assert.deepEqual(empty.products, []);
  assert.equal(empty.coverage["identity.name"].total, 0);
  const outOfRange = await json<ProductsResponse>(await handleProducts(request("/api/products", { page: String(Number.MAX_SAFE_INTEGER) })));
  assert.deepEqual(outOfRange.products, []);
});

test("cohort numeric conditions and source/role selectors constrain both records and coverage", async () => {
  const body = await json<ProductsResponse>(await handleProducts(request("/api/products", {
    rules: JSON.stringify([{ field: "composition.cocoa_percentage", operator: "range", min: 70, max: 85 }]), status: "priced", pageSize: "50",
  })));
  assert.ok(body.total > 0);
  assert.ok(body.products.length <= 50);
  assert.equal(body.coverage["composition.cocoa_percentage"].known, body.total);
  for (const product of body.products) {
    const cocoa = product.attributes["composition.cocoa_percentage"];
    assert.equal(cocoa.status, "known");
    assert.ok(typeof cocoa.value === "number" && cocoa.value >= 70 && cocoa.value <= 85);
    assert.equal(product.prices[0].currency, "GBP");
    assert.equal(product.latestPriceConflict, false);
  }
  const source = snapshot.products[0].source;
  const sourced = await json<ProductsResponse>(await handleProducts(request("/api/products", { source })));
  assert.equal(sourced.total, snapshot.products.filter((product) => product.source === source).length);
  assert.ok(sourced.products.every((product) => product.source === source));
  const brands = await json<ProductsResponse>(await handleProducts(request("/api/products", { role: "brand" })));
  assert.ok(brands.products.every((product) => product.role === "brand"));
});

test("unsupported, repeated and malformed query parameters consistently return 400", async () => {
  const badQueries: Record<string, string>[] = [
    { pageSize: "51" }, { pageSize: "0" }, { page: "1.5" }, { page: "1e2" }, { page: "-1" },
    { page: "9007199254740992" }, { role: "wholesale" }, { source: "../../secret" }, { status: "ready" },
    { search: "x".repeat(201) }, { rules: "not-json" }, { rules: "{}" }, { rules: "null" },
    { rules: JSON.stringify(Array.from({ length: 13 }, () => ({ field: "identity.name", operator: "known" }))) },
    { rules: " ".repeat(8_001) },
    { unexpected: "yes" },
  ];
  for (const query of badQueries) await invalidResponse(await handleProducts(request("/api/products", query)));
  await invalidResponse(await handleProducts(new Request("https://example.test/api/products?page=1&page=2")));
  await invalidResponse(await handleSchema(request("/api/schema", { source: "all" })));
  await invalidResponse(await handleProduct(request("/api/products/id", { source: "all" }), snapshot.products[0].id));
});

test("typed rule validation enforces schema bounds, operators and permitted vocabulary", () => {
  const invalidRules = [
    [{ field: "missing", operator: "known" }], [{ field: "identity.name", operator: "execute" }],
    [{ field: "identity.name", operator: "range", min: 2 }], [{ field: "identity.name", operator: "equals", value: "foo" }],
    [{ field: "composition.cocoa_percentage", operator: "range" }],
    [{ field: "composition.cocoa_percentage", operator: "range", min: null, max: null }],
    [{ field: "composition.cocoa_percentage", operator: "range", min: "70" }],
    [{ field: "composition.cocoa_percentage", operator: "range", min: -1 }],
    [{ field: "composition.cocoa_percentage", operator: "range", max: 101 }],
    [{ field: "composition.cocoa_percentage", operator: "range", min: 80, max: 70 }],
    [{ field: "quantity.pack_count", operator: "range", min: 1.5 }],
    [{ field: "identity.name", operator: "known", value: true }],
    [{ field: "dietary.vegan_claim", operator: "equals", value: "invented-vocabulary" }], [null], [[]],
  ];
  for (const rules of invalidRules) {
    assert.throws(() => parseCohort(new URLSearchParams({ rules: JSON.stringify(rules) }), snapshot), ApiError);
  }
  assert.throws(() => parseCohort(new URLSearchParams({ rules: '[{"field":"composition.cocoa_percentage","operator":"range","max":1e309}]' }), snapshot), ApiError);
  const unbounded = parseCohort(new URLSearchParams({ rules: '[{"field":"composition.cocoa_percentage","operator":"range","min":70}]' }), snapshot);
  assert.deepEqual(unbounded.rules, [{ field: "composition.cocoa_percentage", operator: "range", min: 70, max: null }]);
});

test("unknown, false, conflict, not-applicable and reviewed unknown remain distinct", () => {
  const definition: FieldDefinition = { ...snapshot.fields[0], key: "test.boolean", type: "boolean", numeric: false, allowedValues: [] };
  const fields = [definition];
  const makeProduct = (id: string, value: Attribute | undefined): Product => ({
    ...snapshot.products[0], id, attributes: value ? { [definition.key]: value } : {},
  });
  const attr = (status: Attribute["status"], value: Attribute["value"], reviewStatus: Attribute["reviewStatus"] = "unreviewed"): Attribute =>
    ({ status, value, reviewStatus, unit: null });
  const products = [
    makeProduct("false", attr("known", false)), makeProduct("unknown", undefined), makeProduct("conflict", attr("conflict", false)),
    makeProduct("reviewed-unknown", attr("unknown", null, "reviewed")), makeProduct("not-applicable", attr("not_applicable", null)),
  ];
  const condition = parseCohort(new URLSearchParams({ rules: JSON.stringify([{ field: definition.key, operator: "equals", value: false }]) }), { ...snapshot, fields });
  assert.deepEqual(filterProducts(products, condition).map((product) => product.id), ["false"]);
  assert.throws(() => parseCohort(new URLSearchParams({ rules: JSON.stringify([{ field: definition.key, operator: "equals", value: "false" }]) }), { ...snapshot, fields }), ApiError);
  assert.equal(matchesRule(products[3], { field: definition.key, operator: "reviewed" }), true);
  assert.equal(matchesRule(products[1], { field: definition.key, operator: "unknown" }), true);
  assert.deepEqual(filterProducts(products, { rules: [
    { field: definition.key, operator: "unknown" }, { field: definition.key, operator: "reviewed" },
  ] }).map((product) => product.id), ["reviewed-unknown"]);
  assert.deepEqual(coverage(products, fields)[definition.key], { known: 1, unknown: 2, conflict: 1, not_applicable: 1, reviewed: 1, total: 5 });
});

test("price axes require same-observation weight, GBP and an unambiguous latest observation", () => {
  const product: Product = { ...snapshot.products[0], latestPriceConflict: false, prices: [{
    observation_id: "fixture", observed_at: "2026-10-03T10:00:00Z", currency: "GBP", displayed_price: 5,
    displayed_price_per_100g_gbp: 2.5, total_edible_weight_g: 200, quantity_status: "known", model_eligible: false,
  }] };
  assert.equal(axisValue(product, "displayed_unit", 103), 2.5);
  assert.equal(axisValue({ ...product, latestPriceConflict: true }, "displayed_unit", 103), null);
  assert.equal(axisValue({ ...product, latestPriceConflict: true }, "observation_weight", 103), null);
  assert.equal(axisValue({ ...product, prices: [{ ...product.prices[0], currency: "USD" }] }, "displayed_pack", 103), null);
  assert.equal(axisValue({ ...product, prices: [{ ...product.prices[0], quantity_status: "unknown" }] }, "displayed_unit", 103), null);
  assert.equal(axisValue({ ...product, prices: [{ ...product.prices[0], total_edible_weight_g: 0 }] }, "displayed_unit", 103), null);
  assert.equal(axisValue({ ...product, attributes: {} }, "composition.cocoa_percentage", 103), null);
  assert.equal(axisValue({ ...product, attributes: { test: { value: 0, status: "known", unit: null, reviewStatus: "unreviewed" } } }, "test", 103), 0);
});

test("default cloud preserves incomplete matrix listings and labels deterministic sampling", async () => {
  const defaults = await json<PointsResponse>(await handlePoints(request("/api/points")));
  assert.equal(defaults.totalMatched, snapshot.products.length);
  assert.equal(defaults.completeCount, 338);
  assert.equal(defaults.excludedCount, snapshot.products.length - 338);
  assert.equal(defaults.sampled, false);
  assert.ok(defaults.points.every((point) => [point.x, point.y, point.z].every(Number.isFinite)));
  const query = { x: "coverage", y: "conflicts", z: "coverage", limit: "500" };
  const sampled = await json<PointsResponse>(await handlePoints(request("/api/points", query)));
  const repeated = await json<PointsResponse>(await handlePoints(request("/api/points", query)));
  assert.equal(sampled.totalMatched, snapshot.products.length);
  assert.equal(sampled.completeCount, snapshot.products.length);
  assert.equal(sampled.points.length, 500);
  assert.equal(new Set(sampled.points.map((point) => point.id)).size, 500);
  assert.equal(sampled.excludedCount, 0);
  assert.equal(sampled.sampled, true);
  assert.deepEqual(repeated.points, sampled.points);
  await invalidResponse(await handlePoints(request("/api/points", { limit: "2001" })));
  await invalidResponse(await handlePoints(request("/api/points", { x: "identity.name" })));
});

test("family coverage counts all declared group members and keeps missing states separate", () => {
  const field = (key: string, group: string, modelSelected = false): FieldDefinition => ({
    ...snapshot.fields[0], key, group, modelSelected,
  });
  const fields = [
    field("elsewhere.zero", "composition", true), field("elsewhere.false", "composition"),
    field("elsewhere.omitted", "composition"), field("elsewhere.reviewedUnknown", "composition"),
    field("elsewhere.conflict", "composition"), field("elsewhere.notApplicable", "composition"),
    field("composition.other", "packaging"),
  ];
  const attr = (status: Attribute["status"], value: Attribute["value"], reviewStatus: Attribute["reviewStatus"] = "unreviewed"): Attribute =>
    ({ status, value, reviewStatus, unit: null });
  const product: Product = { ...snapshot.products[0], attributes: {
    "elsewhere.zero": attr("known", 0), "elsewhere.false": attr("known", false, "reviewed"),
    "elsewhere.reviewedUnknown": attr("unknown", null, "reviewed"), "elsewhere.conflict": attr("conflict", [10, 20]),
    "elsewhere.notApplicable": attr("not_applicable", null), "composition.other": attr("known", "paper"),
  } };
  const families = fieldFamilies(fields);
  assert.deepEqual([...families.keys()], ["composition", "packaging"], "Only explicit flat group membership defines a family");
  const result = productFamilyCoverage(product, families);
  assert.deepEqual(result.composition, { known: 2, unknown: 2, conflict: 1, not_applicable: 1, reviewed: 2, total: 6 });
  assert.deepEqual(result.packaging, { known: 1, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: 1 });
  const changedValues: Product = { ...product, attributes: { ...product.attributes,
    "elsewhere.zero": attr("known", 1_000_000), "elsewhere.false": attr("known", true, "reviewed"),
  } };
  assert.deepEqual(productFamilyCoverage(changedValues, families), result, "Raw trait magnitude and truth values are not importance or coverage weights");
  assert.deepEqual(productFamilyCoverage(product, fieldFamilies(fields.map((definition) => ({ ...definition, modelSelected: !definition.modelSelected })))), result,
    "Coverage includes the whole family regardless of predictor selection");
});

test("every plotted point contains complete family evidence counts with no additional evidence fetch", async () => {
  const result = await json<PointsResponse>(await handlePoints(request("/api/points")));
  const groups = [...new Set(snapshot.fields.map((field) => field.group))];
  const products = new Map(snapshot.products.map((product) => [product.id, product]));
  for (const point of result.points) {
    const product = products.get(point.id);
    assert.ok(product);
    assert.deepEqual(Object.keys(point.familyCoverage).sort(), [...groups].sort());
    for (const group of groups) {
      const fields = snapshot.fields.filter((field) => field.group === group);
      const counts = point.familyCoverage[group];
      const values: (Attribute | undefined)[] = fields.map((field) => product.attributes[field.key]);
      assert.equal(counts.total, fields.length);
      assert.equal(counts.known, values.filter((value) => value?.status === "known").length);
      assert.equal(counts.unknown, values.filter((value) => !value || value.status === "unknown").length);
      assert.equal(counts.conflict, values.filter((value) => value?.status === "conflict").length);
      assert.equal(counts.not_applicable, values.filter((value) => value?.status === "not_applicable").length);
      assert.equal(counts.reviewed, values.filter((value) => value?.reviewStatus === "reviewed").length);
      assert.equal(counts.known + counts.unknown + counts.conflict + counts.not_applicable, counts.total);
    }
    assert.equal(Object.values(point.familyCoverage).reduce((total, counts) => total + counts.total, 0), snapshot.fields.length);
    assert.equal(Object.values(point.familyCoverage).reduce((total, counts) => total + counts.known, 0), product.known);
  }
});

test("all-family evidence stays below the response ceiling at the maximum point cap", async (context) => {
  const response = await handlePoints(request("/api/points", { x: "coverage", y: "conflicts", z: "coverage", limit: "2000" }));
  assert.equal(response.status, 200);
  const raw = await response.text();
  const bytes = Buffer.byteLength(raw, "utf8");
  assert.ok(bytes < MAX_RESPONSE_BYTES);
  const body = JSON.parse(raw) as PointsResponse;
  assert.equal(body.points.length, 2_000);
  assert.equal(body.completeCount, snapshot.products.length);
  assert.equal(body.sampled, true);
  assert.equal(Object.keys(body.points[0].familyCoverage).length, new Set(snapshot.fields.map((field) => field.group)).size);
  context.diagnostic(`Maximum point response with all family counts: ${bytes} bytes`);
});

test("product route returns original full evidence and rejects unknown or path-like IDs", async () => {
  const product = snapshot.products.find((entry) => Object.values(entry.attributes).some((value) => value.truncated));
  assert.ok(product);
  const body = await json<ProductResponse>(await productGET(request(`/api/products/${product.id}`), { params: Promise.resolve({ id: product.id }) }));
  assert.equal(body.product.id, product.id);
  const shard = JSON.parse(await readFile(path.join(process.cwd(), "snapshot", "evidence", `${product.source}.json`), "utf8"));
  assert.deepEqual(body.evidence, shard[product.id]);
  const field = Object.keys(product.attributes).find((key) => product.attributes[key].truncated);
  assert.ok(field);
  assert.notDeepEqual(body.evidence.attributes[field].value, product.attributes[field].value);
  await invalidResponse(await handleProduct(request("/api/products/missing"), "not-a-listing"), 404);
  await invalidResponse(await handleProduct(request("/api/products/invalid"), "../../snapshot/index.json"), 404);
});

test("comparison preserves order, deduplicates selections and refuses more than four", async () => {
  const [first, second] = snapshot.products;
  const result = await json<{ products: Product[] }>(await handleCompare(request("/api/compare", { ids: `${second.id},${first.id},${second.id}` })));
  assert.deepEqual(result.products.map((product) => product.id), [second.id, first.id]);
  await invalidResponse(await handleCompare(request("/api/compare")));
  await invalidResponse(await handleCompare(request("/api/compare", { ids: `${first.id},` })));
  await invalidResponse(await handleCompare(request("/api/compare", { ids: snapshot.products.slice(0, 5).map((product) => product.id).join(",") })));
  await invalidResponse(await handleCompare(request("/api/compare", { ids: "missing" })), 404);
});

test("the response ceiling counts UTF-8 bytes and accepts ordinary payloads", () => {
  const result = boundedJson({ ok: true }, snapshot.meta.revision);
  assert.equal(result.status, 200);
  assert.throws(() => boundedJson({ text: "😀".repeat(MAX_RESPONSE_BYTES / 4) }, snapshot.meta.revision), (error: unknown) =>
    error instanceof ApiError && error.code === "RESPONSE_TOO_LARGE");
});
