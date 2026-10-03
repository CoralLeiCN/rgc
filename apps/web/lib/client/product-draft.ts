import type { FieldDefinition, JsonValue, Product } from "../contracts";
import { calculateTraitDemoScore, type TraitDemoScore } from "../trait-demo";
import { unitPrice } from "./display";

/** Local, unreviewed user inputs. Never persisted into the observed collection. */
export interface ProductDraft {
  name: string; packPrice: string; weightGrams: string;
  values: Record<string, string>;
}
export interface ConfiguredProductMarker { name: string; price: number; score: number; }
export interface DraftEvaluation {
  pricePer100g: number | null; errors: Record<string, string>;
  traits: Record<string, JsonValue>; configuredCount: number;
  score: TraitDemoScore;
  marker: ConfiguredProductMarker | null;
}

export function createProductDraft(): ProductDraft {
  return { name: "My product", packPrice: "3.50", weightGrams: "100", values: {} };
}

/** Only copy known values; conflicting/unknown/N/A evidence is not an input. */
export function draftFromProduct(product: Product, fields: FieldDefinition[]): ProductDraft {
  const values: Record<string, string> = {};
  for (const field of fields) {
    if (field.key === "identity.name" || field.key === "quantity.total_edible_weight_g") continue;
    const attribute = product.attributes[field.key];
    if (attribute?.status !== "known" || attribute.value === null || attribute.truncated) continue;
    values[field.key] = typeof attribute.value === "object" ? JSON.stringify(attribute.value) : String(attribute.value);
  }
  const latest = product.prices[0];
  const price = unitPrice(product);
  // Reuse pack price and edible mass only from the same usable observation.
  const packKnown = price !== null && latest && typeof latest.displayed_price === "number" && Number.isFinite(latest.displayed_price) && latest.displayed_price > 0;
  return {
    name: product.name, packPrice: packKnown ? String(latest.displayed_price) : "",
    weightGrams: packKnown ? String(latest.total_edible_weight_g) : "",
    values
  };
}

function parseTrait(raw: string, field: FieldDefinition): { value?: JsonValue; error?: string } {
  const text = raw.trim();
  if (!text) return {};
  if (field.type === "number" || field.type === "integer") {
    const value = Number(text);
    if (!Number.isFinite(value)) return { error: "Enter a finite number." };
    if (field.type === "integer" && !Number.isInteger(value)) return { error: "Enter a whole number." };
    if (field.minimum !== null && value < field.minimum) return { error: `Minimum ${field.minimum}.` };
    if (field.maximum !== null && value > field.maximum) return { error: `Maximum ${field.maximum}.` };
    return { value };
  }
  if (field.type === "enum" || field.type === "boolean") {
    const allowed = field.type === "boolean" ? [true, false] : field.allowedValues;
    const value = allowed.find(item => String(item) === text);
    return value === undefined ? { error: "Choose a value from the schema." } : { value };
  }
  if (field.type === "string_list") {
    let items: unknown;
    const explicitList = text.startsWith("[");
    if (explicitList) {
      try { items = JSON.parse(text); } catch { return { error: "Enter a valid list or comma-separated values." }; }
    } else items = text.split(/[,\n]/).map(item => item.trim()).filter(Boolean);
    if (!Array.isArray(items) || !items.every(item => typeof item === "string" && item.trim().length > 0)) return { error: "Each list item must be non-empty text." };
    const values = [...new Set((items as string[]).map(item => item.trim()))];
    if (!values.length) return explicitList ? { value: [] } : { error: "Enter list items or clear the input." };
    if (field.allowedValues.length && values.some(item => !field.allowedValues.includes(item))) return { error: "Use the allowed values shown in trait help." };
    return { value: values };
  }
  if (field.type === "string") return { value: text };
  return { error: "This trait type is not supported by the configurator." };
}

export function evaluateDraft(draft: ProductDraft, fields: FieldDefinition[]): DraftEvaluation {
  const errors: Record<string, string> = {};
  const traits: Record<string, JsonValue> = {};
  const packPrice = Number(draft.packPrice), weight = Number(draft.weightGrams);
  if (!draft.packPrice.trim() || !Number.isFinite(packPrice) || packPrice <= 0) errors.packPrice = "Enter a pack price greater than zero.";
  if (!draft.weightGrams.trim() || !Number.isFinite(weight) || weight <= 0) errors.weightGrams = "Enter edible weight greater than zero.";
  let pricePer100g = errors.packPrice || errors.weightGrams ? null : packPrice / weight * 100;
  if (pricePer100g !== null && (!Number.isFinite(pricePer100g) || pricePer100g <= 0)) {
    pricePer100g = null; errors.packPrice = "Price and weight must give a finite positive unit price.";
  }
  for (const field of fields) {
    const raw = field.key === "identity.name" ? draft.name : field.key === "quantity.total_edible_weight_g" ? draft.weightGrams : draft.values[field.key] || "";
    const result = parseTrait(raw, field);
    if (result.error) errors[field.key] = result.error;
    else if (result.value !== undefined) traits[field.key] = result.value;
  }
  const score = calculateTraitDemoScore(traits);
  return {
    pricePer100g, errors, traits, configuredCount: Object.keys(traits).length,
    score,
    marker: pricePer100g !== null && score.score !== null && !Object.keys(errors).length ? { name: draft.name.trim() || "My product", price: pricePer100g, score: score.score } : null
  };
}

/** Apply only reviewed candidate keys to the current draft; prices are never extracted. */
export function applyExtractedTraits(draft: ProductDraft, candidates: { key: string; value: JsonValue }[], fields: FieldDefinition[]): ProductDraft {
  const next = { ...draft, values: { ...draft.values } };
  const definitions = new Map(fields.map(field => [field.key, field]));
  for (const candidate of candidates) {
    const field = definitions.get(candidate.key);
    if (!field || candidate.value === null) continue;
    const raw = typeof candidate.value === "object" ? JSON.stringify(candidate.value) : String(candidate.value);
    const parsed = parseTrait(raw, field);
    if (parsed.error || parsed.value === undefined) continue;
    if (field.key === "identity.name") next.name = raw;
    else if (field.key === "quantity.total_edible_weight_g") {
      if (typeof parsed.value === "number" && parsed.value > 0) next.weightGrams = raw;
    } else next.values[field.key] = raw;
  }
  return next;
}
