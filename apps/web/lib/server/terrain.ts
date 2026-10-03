import "server-only";
import type { ErrorResponse, FieldDefinition, JsonValue, Product, Snapshot, TerrainDimension, TerrainResponse } from "../contracts";
import { calculateTraitDemoScore, TRAIT_DEMO_DEFINITION, TRAIT_DEMO_VERSION } from "../trait-demo";
import { loadSnapshot } from "./data";
import { ApiError, invalid } from "./errors";
import { boundedJson } from "./handlers";
import { quantile } from "./analysis";
import { assertParameters, attribute, axisValue, COHORT_KEYS, filterProducts, finite, parseCohort, positiveInteger } from "./query";

const COLOR_TYPES = new Set(["enum", "boolean", "string_list", "number", "integer"]);
const NUMERIC_TYPES = new Set(["number", "integer"]);
const boundsCache = new WeakMap<Snapshot, Record<string, { min: number; max: number }>>();

function dimension(key: string, fields: FieldDefinition[], numeric: boolean): TerrainDimension {
  const members = fields.filter(field => field.key === key && (numeric ? NUMERIC_TYPES : COLOR_TYPES).has(field.type));
  if (!members.length) invalid(numeric ? "Z requires one numeric leaf trait." : "Colour requires one numeric, enum, boolean or string-list leaf trait. Parent families are navigation only.");
  return { key, label: members[0].label, fields: members };
}

function numericValue(product: Product, field: FieldDefinition): number | null {
  const value = attribute(product, field.key);
  if (value.status !== "known" || value.truncated || !finite(value.value)) return null;
  if (field.type === "integer" && !Number.isInteger(value.value)) return null;
  if (field.minimum !== null && value.value < field.minimum || field.maximum !== null && value.value > field.maximum) return null;
  return value.value;
}

/** Calibration is frozen to the immutable whole snapshot, never the current cohort. */
function calibration(snapshot: Snapshot): Record<string, { min: number; max: number }> {
  const cached = boundsCache.get(snapshot);
  if (cached) return cached;
  const result: Record<string, { min: number; max: number }> = {};
  for (const field of snapshot.fields.filter(field => NUMERIC_TYPES.has(field.type))) {
    let min = Infinity, max = -Infinity;
    for (const product of snapshot.products) {
      const value = numericValue(product, field);
      if (value !== null) { min = Math.min(min, value); max = Math.max(max, value); }
    }
    if (Number.isFinite(min)) result[field.key] = { min, max };
  }
  boundsCache.set(snapshot, result);
  return result;
}

function zValue(product: Product, z: TerrainResponse["z"]): number | null {
  return numericValue(product, z.fields[0]);
}

function scoringTraits(product: Product): Record<string, JsonValue> {
  return Object.fromEntries(Object.entries(product.attributes)
    .filter(([, value]) => value.status === "known" && !value.truncated)
    .map(([key, value]) => [key, value.value]));
}

const STATE_LABELS: Record<string, string> = { unknown: "Unknown", conflict: "Conflict", not_applicable: "Not applicable", truncated: "Truncated", empty: "No values listed" };

/** One leaf trait supplies the layers; list values share that trait's visual weight. */
function categoryShares(product: Product, fields: FieldDefinition[], bounds: Record<string, { min: number; max: number }>): { shares: Record<string, number>; labels: Record<string, string> } {
  const shares: Record<string, number> = {}, labels: Record<string, string> = {};
  for (const field of fields) {
    const item = attribute(product, field.key);
    let state: string | null = item.status === "known" ? item.truncated ? "truncated" : null : item.status;
    let values: (string | boolean)[] = [];
    if (!state) {
      if (NUMERIC_TYPES.has(field.type)) {
        const value = numericValue(product, field), calibration = bounds[field.key];
        if (value !== null && calibration) {
          const width = (calibration.max - calibration.min) / 5;
          const band = width === 0 ? 0 : Math.min(4, Math.floor((value - calibration.min) / width));
          const lower = calibration.min + band * width, upper = calibration.min + (band + 1) * width;
          const format = (number: number) => new Intl.NumberFormat("en-GB", { maximumSignificantDigits: 6 }).format(number);
          const key = `${field.key}=range:${band}`;
          shares[key] = 1;
          labels[key] = `${field.label}: ${width === 0 ? format(lower) : `${format(lower)} ≤ value ${band === 4 ? "≤" : "<"} ${format(upper)}`}${field.unit ? ` ${field.unit}` : ""}`;
          continue;
        }
        state = "unknown";
      } else if (field.type === "boolean" && typeof item.value === "boolean") values = [item.value];
      else if (field.type === "enum" && typeof item.value === "string" && field.allowedValues.includes(item.value)) values = [item.value];
      else if (field.type === "string_list" && Array.isArray(item.value) && item.value.every(value => typeof value === "string" && value.trim().length > 0)) {
        values = [...new Set(item.value as string[])];
        if (!values.length) state = "empty";
      } else state = "unknown";
    }
    if (state) {
      const key = `${field.key}=state:${state}`;
      shares[key] = 1 / fields.length;
      labels[key] = `${field.label}: ${STATE_LABELS[state] ?? "Unknown"}`;
    } else for (const value of values) {
      const key = `${field.key}=value:${encodeURIComponent(String(value))}`;
      shares[key] = 1 / fields.length / values.length;
      labels[key] = `${field.label}: ${String(value)}`;
    }
  }
  return { shares, labels };
}

export function buildTerrain(snapshot: Snapshot, params: URLSearchParams): TerrainResponse {
  assertParameters(params, [...COHORT_KEYS, "color", "z", "limit", "range"]);
  const color = dimension(params.get("color") ?? "composition.chocolate_type", snapshot.fields, false);
  const selectedZ = dimension(params.get("z") ?? "composition.cocoa_percentage", snapshot.fields, true);
  const z: TerrainResponse["z"] = { ...selectedZ, unit: selectedZ.fields[0].unit };
  const colorBounds = color.fields.some(field => NUMERIC_TYPES.has(field.type)) ? calibration(snapshot) : {};
  const limit = positiveInteger(params, "limit", 1_000, 2_000);
  const requestedRange = params.get("range") ?? "core";
  if (requestedRange !== "core" && requestedRange !== "full") invalid("Price range must be core or full.");
  const products = filterProducts(snapshot.products, parseCohort(params, snapshot));
  const priced = products.flatMap(product => {
    const price = axisValue(product, "displayed_unit", snapshot.fields.length);
    return price === null ? [] : [{ product, price }];
  });
  const prices = priced.map(row => row.price).sort((a, b) => a - b);
  const q1 = prices.length ? quantile(prices, .25) : null, q3 = prices.length ? quantile(prices, .75) : null;
  const fallback = requestedRange === "core" && q1 !== null && q1 === q3;
  const range = fallback ? "full" : requestedRange;
  const priceRange: [number, number] | null = !prices.length ? null : range === "full"
    ? [prices[0], prices[prices.length - 1]]
    : [Math.max(prices[0], q1! - 1.5 * (q3! - q1!)), Math.min(prices[prices.length - 1], q3! + 1.5 * (q3! - q1!))];
  const complete: TerrainResponse["rows"] = [];
  const categories = new Map<string, { key: string; label: string; count: number }>();
  let belowRangeCount = 0, aboveRangeCount = 0, missingScoreCount = 0, missingZCount = 0;
  for (const { product, price } of priced) {
    if (price < priceRange![0]) { belowRangeCount++; continue; }
    if (price > priceRange![1]) { aboveRangeCount++; continue; }
    const score = calculateTraitDemoScore(scoringTraits(product)).score, value = zValue(product, z);
    if (score === null) missingScoreCount++;
    if (value === null) missingZCount++;
    if (score === null || value === null) continue;
    const grouping = categoryShares(product, color.fields, colorBounds);
    complete.push({ id: product.id, name: product.name, price, score, z: value, categories: grouping.shares });
    for (const [key, label] of Object.entries(grouping.labels)) {
      const existing = categories.get(key);
      if (existing) existing.count++;
      else categories.set(key, { key, label, count: 1 });
    }
  }
  complete.sort((a, b) => a.id.localeCompare(b.id));
  const sampled = complete.length > limit;
  const rows = sampled ? Array.from({ length: limit }, (_, index) => complete[Math.floor(index * complete.length / limit)]) : complete;
  return {
    color, z, rows, categories: [...categories.values()].sort((a, b) => b.count - a.count || a.key.localeCompare(b.key)),
    totalMatched: products.length, pricedCount: priced.length, completeCount: complete.length,
    excludedCount: products.length - complete.length, sampled, limit, priceRange, requestedRange, range,
    rangeFallbackReason: fallback ? "The interquartile range is zero; showing the full observed price range." : null,
    belowRangeCount, aboveRangeCount, missingScoreCount, missingZCount,
    scoreDefinition: TRAIT_DEMO_DEFINITION, scoreVersion: TRAIT_DEMO_VERSION,
  };
}

export async function handleTerrain(request: Request): Promise<Response> {
  try {
    const params = new URL(request.url).searchParams;
    assertParameters(params, [...COHORT_KEYS, "color", "z", "limit", "range"]);
    const snapshot = await loadSnapshot();
    return boundedJson(buildTerrain(snapshot, params), snapshot.meta.revision);
  } catch (error: unknown) {
    const status = error instanceof ApiError ? error.status : 500;
    const body: ErrorResponse = { error: { code: error instanceof ApiError ? error.code : "INTERNAL_ERROR", message: error instanceof ApiError ? error.message : "The terrain could not be loaded. Please try again." } };
    return Response.json(body, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  }
}
