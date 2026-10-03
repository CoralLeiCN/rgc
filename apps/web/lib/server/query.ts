import type {
  Attribute, CohortQuery, Coverage, FieldDefinition, Product, Snapshot, TraitRule,
} from "../contracts";
import { invalid } from "./errors";

export const COHORT_KEYS = ["search", "source", "role", "status", "rules"] as const;
const STATES = new Set(["known", "unknown", "conflict", "not_applicable", "reviewed"]);
const UNKNOWN: Attribute = { value: null, status: "unknown", unit: null, reviewStatus: "unreviewed" };

export function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function attribute(product: Product, key: string): Attribute {
  return Object.hasOwn(product.attributes, key) ? product.attributes[key] : UNKNOWN;
}

export function assertParameters(params: URLSearchParams, allowed: readonly string[]): void {
  const seen = new Set<string>();
  for (const [key] of params) {
    if (!allowed.includes(key)) invalid(`Unsupported parameter: ${key.slice(0, 80)}.`);
    if (seen.has(key)) invalid(`Parameter ${key} must appear only once.`);
    seen.add(key);
  }
}

export function positiveInteger(params: URLSearchParams, key: string, fallback: number, maximum = Number.MAX_SAFE_INTEGER): number {
  const raw = params.get(key);
  if (raw === null) return fallback;
  if (!/^\d+$/.test(raw)) invalid(`${key} must be a positive whole number.`);
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > maximum) invalid(`${key} must be between 1 and ${maximum}.`);
  return value;
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateRule(input: unknown, fields: Map<string, FieldDefinition>): TraitRule {
  if (!record(input) || typeof input.field !== "string" || typeof input.operator !== "string") {
    invalid("Each trait condition needs a field and operator.");
  }
  const field = fields.get(input.field);
  if (!field) invalid("A trait condition references an unknown schema field.");
  const allowedKeys = input.operator === "range" ? ["field", "operator", "min", "max"] :
    input.operator === "equals" ? ["field", "operator", "value"] : ["field", "operator"];
  if (Object.keys(input).some((key) => !allowedKeys.includes(key))) invalid("A trait condition contains unsupported properties.");

  if (STATES.has(input.operator)) return { field: field.key, operator: input.operator as TraitRule["operator"] };
  if (input.operator === "range") {
    if (!field.numeric || !["number", "integer"].includes(field.type)) invalid("Range conditions require a numeric trait.");
    const min = input.min ?? null;
    const max = input.max ?? null;
    const bounds = [min, max].filter((value) => value !== null);
    if (!bounds.length) invalid("A numeric range needs at least one bound.");
    if (!bounds.every(finite)) invalid("Range bounds must be finite JSON numbers.");
    if (field.type === "integer" && bounds.some((value) => !Number.isInteger(value))) invalid("This trait requires whole-number bounds.");
    if (bounds.some((value) => (field.minimum !== null && value < field.minimum) || (field.maximum !== null && value > field.maximum))) {
      invalid("Range bounds must stay within the schema's declared limits.");
    }
    if (finite(min) && finite(max) && min > max) invalid("Minimum must not exceed maximum.");
    return { field: field.key, operator: "range", min: min as number | null, max: max as number | null };
  }
  if (input.operator === "equals") {
    const values = field.type === "boolean" ? [true, false] : field.type === "enum" ? field.allowedValues : [];
    if (!values.some((value) => value === input.value)) invalid("Equals conditions require a typed value from the trait's vocabulary.");
    return { field: field.key, operator: "equals", value: input.value as string | number | boolean };
  }
  invalid("Unsupported trait condition operator.");
}

export function parseCohort(params: URLSearchParams, snapshot: Snapshot): CohortQuery {
  const search = (params.get("search") ?? "").trim();
  if (search.length > 200) invalid("Search is limited to 200 characters.");
  const source = params.get("source") ?? "all";
  if (source !== "all" && !snapshot.products.some((product) => product.source === source)) invalid("Unknown collection source.");
  const role = params.get("role") ?? "all";
  if (!["all", "brand", "retail", "unknown"].includes(role)) invalid("Unknown seller role.");
  const status = params.get("status") ?? "all";
  if (!["all", "priced", "unpriced", "conflicts"].includes(status)) invalid("Unknown price/quality status.");
  const rawRules = params.get("rules");
  let rules: TraitRule[] = [];
  if (rawRules !== null) {
    if (rawRules.length > 8_000) invalid("Trait conditions exceed the query size limit.");
    let decoded: unknown;
    try { decoded = JSON.parse(rawRules); } catch { invalid("Trait conditions must be a JSON array."); }
    if (!Array.isArray(decoded) || decoded.length > 12) invalid("Provide an array of at most 12 trait conditions.");
    const fields = new Map(snapshot.fields.map((field) => [field.key, field]));
    rules = decoded.map((rule: unknown) => validateRule(rule, fields));
  }
  return { search, source, role: role as CohortQuery["role"], status: status as CohortQuery["status"], rules };
}

export function matchesRule(product: Product, rule: TraitRule): boolean {
  const value = attribute(product, rule.field);
  if (rule.operator === "reviewed") return value.reviewStatus === "reviewed";
  if (STATES.has(rule.operator)) return value.status === rule.operator;
  if (value.status !== "known") return false;
  if (rule.operator === "equals") return value.value === rule.value;
  return rule.operator === "range" && finite(value.value) &&
    (rule.min == null || value.value >= rule.min) && (rule.max == null || value.value <= rule.max);
}

/** Positive GBP per 100g from the same latest observation with a known edible weight. */
export function observedUnitPrice(product: Product): number | null {
  const price = product.prices[0];
  if (!price || price.currency !== "GBP" || product.latestPriceConflict) return null;
  if (price.quantity_status !== "known" || !finite(price.total_edible_weight_g) || price.total_edible_weight_g <= 0) return null;
  const value = price.displayed_price_per_100g_gbp;
  return finite(value) && value > 0 ? value : null;
}

export function filterProducts(products: Product[], query: CohortQuery): Product[] {
  const search = (query.search ?? "").toLocaleLowerCase("en-GB");
  return products.filter((product) => {
    if (search && ![product.name, product.brand, product.retailer, product.source, product.id].join(" ").toLocaleLowerCase("en-GB").includes(search)) return false;
    if (query.source && query.source !== "all" && product.source !== query.source) return false;
    if (query.role && query.role !== "all" && product.role !== query.role) return false;
    if (query.status === "conflicts" && !(product.conflicts > 0 || product.latestPriceConflict)) return false;
    const priced = observedUnitPrice(product) !== null;
    if (query.status === "priced" && !priced || query.status === "unpriced" && priced) return false;
    return (query.rules ?? []).every((rule) => matchesRule(product, rule));
  });
}

export function coverage(products: Product[], fields: FieldDefinition[]): Record<string, Coverage> {
  return Object.fromEntries(fields.map((field) => {
    const counts: Coverage = { known: 0, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: products.length };
    for (const product of products) {
      const value = attribute(product, field.key);
      counts[value.status]++;
      if (value.reviewStatus === "reviewed") counts.reviewed++;
    }
    return [field.key, counts];
  }));
}
