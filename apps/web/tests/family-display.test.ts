import assert from "node:assert/strict";
import test from "node:test";
import type { Attribute, FieldDefinition, Product } from "../lib/contracts";
import { buildFamilyLayout, familyColor, familyCoverage, familyEvidenceField, familyKeys, toggleFamily, type FamilyColumnSettings } from "../lib/client/families";

function field(key: string, group: string, known = 10, modelSelected = false): FieldDefinition {
  return { key, group, label: key.replaceAll(".", " "), description: `Evidence for ${key}`, known, conflicts: 0, numeric: false, numericKnown: 0, type: "boolean", unit: null, scope: "product", qualifier: "", minimum: null, maximum: null, allowedValues: [], modelRole: null, modelSelected, modelDefinition: null };
}
const fields = [
  field("composition.cocoa", "composition", 90, true), field("composition.nuts", "composition", 60, true), field("composition.sugar", "composition", 30),
  field("certifications.organic", "certifications", 70, true), field("certifications.fairtrade", "certifications", 40, true),
  field("identity.name", "identity", 100), field("storage.temperature", "storage", 20)
];
const groups = ["identity", "composition", "certifications", "storage"];
const settings: FamilyColumnSettings = { group: "all", search: "", limit: 1, modelOnly: false, pinned: [], expandedFamilies: ["composition", "certifications"] };
function product(attributes: Record<string, Attribute> = {}): Product {
  return { id: "one", name: "A source listing", source: "source", brand: null, retailer: null, role: "unknown", reviewStatus: "unreviewed", attributes, known: 0, conflicts: 0, prices: [], latestPriceConflict: false, sourceListingIds: [] };
}
function value(status: Attribute["status"], content: Attribute["value"] = null): Attribute {
  return { status, value: content, unit: null, reviewStatus: "unreviewed" };
}

test("families expand independently in published order with a per-family limit", () => {
  const layout = buildFamilyLayout(fields, groups, settings);
  assert.deepEqual(layout.families.map(family => family.key), groups);
  assert.deepEqual(layout.visibleFields.map(item => item.key), ["composition.cocoa", "certifications.organic"]);
  assert.equal(layout.families.find(family => family.key === "composition")?.hiddenMatchingCount, 2);
  const expanded = toggleFamily(settings, "storage");
  assert.deepEqual(expanded.expandedFamilies, ["composition", "certifications", "storage"]);
  assert.deepEqual(settings.expandedFamilies, ["composition", "certifications"], "Presentation changes do not mutate previous settings");
  const collapsed = toggleFamily(expanded, "composition");
  assert.deepEqual(collapsed.expandedFamilies, ["certifications", "storage"]);
});

test("pinned traits survive collapse, search, and model filters without duplicate detail columns", () => {
  const pinned = ["composition.cocoa", "composition.cocoa", "identity.name", "missing.field"];
  const layout = buildFamilyLayout(fields, groups, { ...settings, pinned, limit: 99 });
  const keys = layout.visibleFields.map(item => item.key);
  assert.deepEqual(layout.pinned.map(item => item.key), ["composition.cocoa", "identity.name"]);
  assert.equal(keys.length, new Set(keys).size);
  assert.equal(keys.filter(key => key === "composition.cocoa").length, 1);
  const filtered = buildFamilyLayout(fields, groups, { ...settings, pinned, expandedFamilies: [], search: "fairtrade", modelOnly: true });
  assert.deepEqual(filtered.pinned.map(item => item.key), ["composition.cocoa", "identity.name"]);
  assert.deepEqual(filtered.families.map(family => family.key), ["certifications"]);
  assert.equal(filtered.families[0].matchingFields.length, 1);
  assert.equal(filtered.families[0].allFields.length, 2, "Coverage denominator stays the complete schema family");
  assert.equal(filtered.families[0].visibleFields.length, 0);
});

test("search-empty layouts retain pinned context and show-all reveals each field once", () => {
  const empty = buildFamilyLayout(fields, groups, { ...settings, search: "not a trait", pinned: ["identity.name"] });
  assert.equal(empty.families.length, 0);
  assert.equal(empty.matchingCount, 0);
  assert.deepEqual(empty.visibleFields.map(item => item.key), ["identity.name"]);
  const all = buildFamilyLayout(fields, groups, { ...settings, expandedFamilies: groups, pinned: ["composition.cocoa"], limit: fields.length });
  assert.deepEqual(new Set(all.visibleFields.map(item => item.key)), new Set(fields.map(item => item.key)));
  assert.equal(all.visibleFields.length, fields.length);
  assert.ok(all.families.every(family => family.hiddenMatchingCount === 0));
});

test("family evidence counts preserve false, zero, missing, conflict and not applicable", () => {
  const evidenceFields = Array.from({ length: 6 }, (_, index) => field(`evidence.${index}`, "evidence"));
  const row = product({
    "evidence.0": value("known", false), "evidence.1": { ...value("known", 0), reviewStatus: "reviewed" },
    "evidence.2": value("unknown"), "evidence.3": value("conflict"), "evidence.4": value("not_applicable")
  });
  assert.deepEqual(familyCoverage(row, evidenceFields), { known: 2, unknown: 2, conflict: 1, not_applicable: 1, reviewed: 1, total: 6 });
  assert.deepEqual(familyCoverage(row, [...evidenceFields, evidenceFields[0]]), familyCoverage(row, evidenceFields), "Repeated field references cannot inflate coverage");
  assert.deepEqual(familyCoverage(row, []), { known: 0, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: 0 });
});

test("filtered and limited family presentation cannot alter evidence denominators", () => {
  const layout = buildFamilyLayout(fields, groups, { ...settings, group: "composition", search: "nuts", modelOnly: true, pinned: ["composition.nuts"] });
  assert.equal(layout.families.length, 1);
  assert.equal(layout.families[0].allFields.length, 3);
  assert.equal(layout.families[0].matchingFields.length, 1);
  assert.equal(layout.families[0].visibleFields.length, 0, "An already pinned match is never duplicated");
  assert.equal(layout.families[0].pinnedMatchingCount, 1);
  const coverage = familyCoverage(product({ "composition.nuts": value("known", false) }), layout.families[0].allFields);
  assert.equal(coverage.known, 1);
  assert.equal(coverage.total, 3);
  assert.equal(coverage.unknown, 2);
});

test("family identities use flat schema groups and stable colors without invented parent groups", () => {
  const extended = [...fields, field("custom.value", "custom.group")];
  assert.deepEqual(familyKeys(extended, [...groups, "absent", "composition"]), [...groups, "custom.group"]);
  assert.equal(familyColor("composition"), familyColor("composition"));
  assert.equal(familyColor("custom.group"), familyColor("custom.group"));
  assert.match(familyColor("custom.group"), /^#[a-f0-9]{6}$/);
  assert.notEqual(familyColor("composition"), familyColor("certifications"));
});

test("opening family coverage selects relevant evidence, prioritizing conflicts", () => {
  const composition = fields.filter(item => item.group === "composition");
  assert.equal(familyEvidenceField(product({ "composition.cocoa": value("known", 80), "composition.nuts": value("conflict") }), composition), "composition.nuts");
  assert.equal(familyEvidenceField(product({ "composition.nuts": value("known", false) }), composition), "composition.nuts");
  assert.equal(familyEvidenceField(product(), composition), "composition.cocoa");
  assert.equal(familyEvidenceField(product(), []), undefined);
});
