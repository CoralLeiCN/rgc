import "server-only";
import { Buffer } from "node:buffer";
import type {
  CompareResponse, ErrorResponse, Point, PointsResponse, Product, ProductResponse, ProductsResponse,
  SchemaResponse, Snapshot,
} from "../contracts";
import { findProduct, loadEvidence, loadSnapshot } from "./data";
import { analyzePrices } from "./analysis";
import { ApiError, invalid } from "./errors";
import {
  assertParameters, availableAxes, axisValue, COHORT_KEYS, coverage, fieldFamilies, filterProducts,
  finite, parseAxes, parseCohort, positiveInteger, productFamilyCoverage,
} from "./query";

export const MAX_RESPONSE_BYTES = 4_000_000;
const CACHE_CONTROL = "public, max-age=0, s-maxage=60, stale-while-revalidate=300";

export function boundedJson(value: unknown, revision: string): Response {
  const body = JSON.stringify(value);
  if (Buffer.byteLength(body, "utf8") > MAX_RESPONSE_BYTES) {
    throw new ApiError(500, "RESPONSE_TOO_LARGE", "This result exceeds the response limit. Narrow the selection.");
  }
  return new Response(body, { headers: {
    "Content-Type": "application/json; charset=utf-8", "Cache-Control": CACHE_CONTROL,
    "X-Content-Type-Options": "nosniff", "X-Dataset-Revision": revision,
  } });
}

async function respond(request: Request, allowed: readonly string[], operation: (params: URLSearchParams, snapshot: Snapshot) => unknown | Promise<unknown>): Promise<Response> {
  try {
    const params = new URL(request.url).searchParams;
    assertParameters(params, allowed);
    const snapshot = await loadSnapshot();
    return boundedJson(await operation(params, snapshot), snapshot.meta.revision);
  } catch (error: unknown) {
    const status = error instanceof ApiError ? error.status : 500;
    const body: ErrorResponse = { error: {
      code: error instanceof ApiError ? error.code : "INTERNAL_ERROR",
      message: error instanceof ApiError ? error.message : "The collection could not be loaded. Please try again.",
    } };
    return Response.json(body, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  }
}

export function handleSchema(request: Request): Promise<Response> {
  return respond(request, [], (_params, snapshot): SchemaResponse => {
    const sources = new Map<string, number>();
    for (const product of snapshot.products) sources.set(product.source, (sources.get(product.source) ?? 0) + 1);
    return {
      meta: snapshot.meta, contract: snapshot.contract, fields: snapshot.fields,
      sources: [...sources].sort(([a], [b]) => a.localeCompare(b)).map(([key, count]) => ({ key, count })),
      axes: availableAxes(snapshot.fields),
    };
  });
}

export function handleProducts(request: Request): Promise<Response> {
  return respond(request, [...COHORT_KEYS, "page", "pageSize"], (params, snapshot): ProductsResponse => {
    const page = positiveInteger(params, "page", 1);
    const pageSize = positiveInteger(params, "pageSize", 25, 50);
    const products = filterProducts(snapshot.products, parseCohort(params, snapshot));
    const totalPages = Math.ceil(products.length / pageSize);
    return {
      products: page > totalPages ? [] : products.slice((page - 1) * pageSize, page * pageSize),
      total: products.length, page, pageSize, totalPages, coverage: coverage(products, snapshot.fields),
    };
  });
}

export function handleProduct(request: Request, id: string): Promise<Response> {
  return respond(request, [], async (_params, snapshot): Promise<ProductResponse> => {
    const product = findProduct(snapshot, id);
    return { product, evidence: await loadEvidence(product) };
  });
}

export function handlePoints(request: Request): Promise<Response> {
  return respond(request, [...COHORT_KEYS, "x", "y", "z", "limit"], (params, snapshot): PointsResponse => {
    const limit = positiveInteger(params, "limit", 500, 2_000);
    const axes = parseAxes(params, snapshot.fields);
    const products = filterProducts(snapshot.products, parseCohort(params, snapshot));
    const complete: { product: Product; point: Omit<Point, "familyCoverage"> }[] = [];
    for (const product of products) {
      const values = axes.map((axis) => axisValue(product, axis.key, snapshot.fields.length));
      if (values.every(finite)) {
        complete.push({ product, point: { id: product.id, name: product.name, source: product.source, role: product.role,
          x: values[0], y: values[1], z: values[2] } });
      }
    }
    // Stable ID order and evenly spaced selection avoid a source-order prefix sample.
    complete.sort((a, b) => a.point.id.localeCompare(b.point.id));
    const sampled = complete.length > limit;
    const selected = sampled ? Array.from({ length: limit }, (_, index) => complete[Math.floor(index * complete.length / limit)]) : complete;
    const families = fieldFamilies(snapshot.fields);
    const points = selected.map(({ product, point }) => ({ ...point, familyCoverage: productFamilyCoverage(product, families) }));
    return { points, axes, totalMatched: products.length, completeCount: complete.length,
      excludedCount: products.length - complete.length, sampled, limit };
  });
}

export function handleCompare(request: Request): Promise<Response> {
  return respond(request, ["ids"], (params, snapshot): CompareResponse => {
    const raw = params.get("ids");
    if (!raw || raw.length > 2_048) invalid("Provide up to four listing IDs.");
    const ids = [...new Set(raw.split(","))];
    if (ids.length > 4 || ids.some((id) => !id || id.length > 256)) invalid("Provide up to four distinct listing IDs.");
    return { products: ids.map((id) => findProduct(snapshot, id)) };
  });
}

export function handleAnalysis(request: Request): Promise<Response> {
  return respond(request, [...COHORT_KEYS, "range", "scoreMode"], (params, snapshot) => {
    const range = params.get("range") ?? "core";
    if (range !== "core" && range !== "full") invalid("Price range must be core or full.");
    const scoreMode = params.get("scoreMode");
    if (scoreMode !== null && scoreMode !== "demo") invalid("Score mode must be demo, or omitted for observed-data analysis.");
    return analyzePrices(filterProducts(snapshot.products, parseCohort(params, snapshot)), snapshot.fields, range, scoreMode ?? undefined);
  });
}
