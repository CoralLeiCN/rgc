import type { Attribute, EvidenceAttribute, FieldDefinition, JsonValue, Product, RuleOperator, TraitRule } from "../contracts";

export const number = (value: number) => value.toLocaleString("en-GB");
export const money = (value: number) => `£${value.toFixed(2)}`;
export const humanize = (value: string) => value.replaceAll("_", " ");
export function unitLabel(unit: string | null | undefined) {
  if (!unit) return "";
  return ({ g_per_100g: "g /100 g", kcal_per_100g: "kcal /100 g", kJ_per_100g: "kJ /100 g", GBP_per_100g: "£ /100 g", celsius: "°C", percent: "%" } as Record<string, string>)[unit] || unit;
}
export function valueLabel(value: JsonValue): string {
  if (value === null) return "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.map(valueLabel).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
export function attribute(product: Product, key: string): Attribute {
  return product.attributes[key] || { value: null, status: "unknown", unit: null, reviewStatus: "unreviewed" };
}
export function attributeLabel(value: Attribute | EvidenceAttribute) {
  if (value.status !== "known") return ({ unknown: "Unknown", conflict: "Conflict", not_applicable: "Not applicable" })[value.status];
  return valueLabel(value.value) + (value.unit ? ` ${unitLabel(value.unit)}` : "");
}
export function unitPrice(product: Product) {
  const price = product.prices[0];
  if (product.latestPriceConflict || price?.currency !== "GBP" || price.quantity_status !== "known" || !Number.isFinite(price.total_edible_weight_g) || !(Number(price.total_edible_weight_g) > 0)) return null;
  const value = price.displayed_price_per_100g_gbp;
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
}
export const stateOperators: { key: RuleOperator; label: string }[] = [
  { key: "known", label: "Has a value" }, { key: "unknown", label: "Unknown" },
  { key: "conflict", label: "Conflicting" }, { key: "not_applicable", label: "Not applicable" },
  { key: "reviewed", label: "Reviewed" }
];
export function operators(field: FieldDefinition) {
  if (field.numeric) return [{ key: "range" as const, label: "Within range" }, ...stateOperators];
  if (field.type === "enum" || field.type === "boolean") return [{ key: "equals" as const, label: "Equals" }, ...stateOperators];
  return stateOperators;
}
export function ruleLabel(rule: TraitRule, fields: FieldDefinition[]) {
  const field = fields.find(item => item.key === rule.field);
  const title = field?.label || rule.field;
  if (rule.operator === "range") return `${title}: ${rule.min ?? "any"} – ${rule.max ?? "any"} ${unitLabel(field?.unit)}`.trim();
  if (rule.operator === "equals") return `${title}: ${humanize(valueLabel(rule.value ?? null))}`;
  return `${title}: ${stateOperators.find(item => item.key === rule.operator)?.label || rule.operator}`;
}
export function dateLabel(value: string | null | undefined) {
  if (!value) return "Time unknown";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(parsed);
}
export function safeExternalUrl(value: string) {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : null; } catch { return null; }
}
