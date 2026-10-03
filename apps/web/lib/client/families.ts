import type { Coverage, FieldDefinition, Product } from "../contracts";
import { attribute, humanize } from "./display";

/** These settings describe presentation only; they never change a product cohort. */
export interface FamilyColumnSettings {
  group: string;
  search: string;
  limit: number;
  modelOnly: boolean;
  pinned: string[];
  expandedFamilies: string[];
}

export interface TraitFamily {
  key: string;
  label: string;
  color: string;
  /** Coverage always uses the complete schema family, independent of display filters. */
  allFields: FieldDefinition[];
  matchingFields: FieldDefinition[];
  visibleFields: FieldDefinition[];
  hiddenMatchingCount: number;
  pinnedMatchingCount: number;
  expanded: boolean;
}

export interface FamilyLayout {
  pinned: FieldDefinition[];
  families: TraitFamily[];
  visibleFields: FieldDefinition[];
  matchingCount: number;
}

const familyColors: Record<string, string> = {
  identity: "#8fbada", composition: "#93e4c7", dietary: "#d6ca91",
  certifications: "#bca5ef", nutrition: "#8bcad1", origin: "#e9b78c",
  packaging: "#c4bded", processing: "#dfabbe", storage: "#95bca7",
  marketing: "#bdc68c", quantity: "#97b0ed"
};
const fallbackColors = ["#9bc7d3", "#d2b695", "#b6c5a1", "#bea9d6", "#d2a7b0", "#a9bde2"];

/** Stable group identities: no hue is a quality, importance or price-contribution score. */
export function familyColor(group: string) {
  if (familyColors[group]) return familyColors[group];
  let hash = 0;
  for (const character of group) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return fallbackColors[hash % fallbackColors.length];
}

export function familyLabel(group: string) {
  const label = humanize(group);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** Preserve published flat family order, then append any newly supplied field groups. */
export function familyKeys(fields: FieldDefinition[], groups: string[] = []) {
  const present = new Set(fields.map(field => field.group));
  return [...new Set([...groups, ...fields.map(field => field.group)])].filter(group => present.has(group));
}

function matches(field: FieldDefinition, settings: FamilyColumnSettings) {
  const query = settings.search.trim().toLowerCase();
  return (!settings.modelOnly || field.modelSelected) && (!query || `${field.label} ${field.key} ${field.description}`.toLowerCase().includes(query));
}

export function buildFamilyLayout(fields: FieldDefinition[], groups: string[], settings: FamilyColumnSettings): FamilyLayout {
  const byKey = new Map(fields.map(field => [field.key, field]));
  const pinned = [...new Set(settings.pinned)].map(key => byKey.get(key)).filter((field): field is FieldDefinition => Boolean(field));
  const pinnedKeys = new Set(pinned.map(field => field.key));
  const limit = Number.isFinite(settings.limit) ? Math.max(0, Math.floor(settings.limit)) : fields.length;
  const families = familyKeys(fields, groups).filter(group => settings.group === "all" || group === settings.group).map(key => {
    const allFields = fields.filter(field => field.group === key);
    const matchingFields = allFields.filter(field => matches(field, settings));
    const unpinned = matchingFields.filter(field => !pinnedKeys.has(field.key)).sort((left, right) => right.known - left.known || left.key.localeCompare(right.key));
    const expanded = settings.expandedFamilies.includes(key);
    const visibleFields = expanded ? unpinned.slice(0, limit) : [];
    return {
      key, label: familyLabel(key), color: familyColor(key), allFields, matchingFields,
      visibleFields, hiddenMatchingCount: unpinned.length - visibleFields.length,
      pinnedMatchingCount: matchingFields.length - unpinned.length, expanded
    };
  }).filter(family => family.matchingFields.length > 0);
  return { pinned, families, visibleFields: [...pinned, ...families.flatMap(family => family.visibleFields)], matchingCount: families.reduce((total, family) => total + family.matchingFields.length, 0) };
}

export function toggleFamily(settings: FamilyColumnSettings, group: string): FamilyColumnSettings {
  const expanded = new Set(settings.expandedFamilies);
  if (expanded.has(group)) expanded.delete(group); else expanded.add(group);
  return { ...settings, expandedFamilies: [...expanded] };
}

/** Known false and zero count as supported values. Missing fields remain unknown. */
export function familyCoverage(product: Product, fields: FieldDefinition[]): Coverage {
  const unique = [...new Map(fields.map(field => [field.key, field])).values()];
  const result: Coverage = { known: 0, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: unique.length };
  for (const field of unique) {
    const value = attribute(product, field.key);
    result[value.status]++;
    if (value.reviewStatus === "reviewed") result.reviewed++;
  }
  return result;
}

export function familyCoverageLabel(counts: Coverage) {
  return `${counts.known} of ${counts.total} known; ${counts.unknown} unknown; ${counts.conflict} conflicting; ${counts.not_applicable} not applicable`;
}

/** Open evidence within the selected family, prioritizing a conflict for inspection. */
export function familyEvidenceField(product: Product, fields: FieldDefinition[]) {
  return (fields.find(field => attribute(product, field.key).status === "conflict") || fields.find(field => attribute(product, field.key).status === "known") || fields[0])?.key;
}
