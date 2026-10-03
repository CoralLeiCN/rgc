import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import type { Product, Snapshot } from "../lib/contracts";
import { applyExtractedTraits, createProductDraft, draftFromProduct, evaluateDraft } from "../lib/client/product-draft";

const snapshot = JSON.parse(readFileSync(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;
const fields = snapshot.fields;

test("draft scores derive from known traits and stay independent of proposed prices", () => {
  const draft = { ...createProductDraft(), packPrice: "4", weightGrams: "80" };
  const evaluated = evaluateDraft(draft, fields);
  assert.equal(evaluated.marker, null, "No recognized trait input means no invented score");
  assert.equal(evaluated.score.score, null);
  assert.equal(evaluated.pricePer100g, 5);
  assert.equal(evaluated.traits["quantity.total_edible_weight_g"], 80);
  const scoredDraft = { ...draft, values: { "composition.cocoa_percentage": "90", "certifications.organic_claim": "present" } };
  const scored = evaluateDraft(scoredDraft, fields);
  assert.deepEqual(scored.marker, { name: "My product", price: 5, score: 57 });
  assert.equal(scored.score.knownInputs, 2);
  assert.equal(scored.configuredCount, evaluated.configuredCount + 2);
  const moved = evaluateDraft({ ...scoredDraft, packPrice: "8", name: "A different label" }, fields);
  assert.equal(moved.marker?.price, 10);
  assert.equal(moved.marker?.score, 57);
  assert.deepEqual(moved.score, scored.score);
  const cleared = evaluateDraft({ ...scoredDraft, values: {} }, fields);
  assert.equal(cleared.marker, null);
});

test("blank traits stay unspecified; numeric zero, enum absent and typed lists are retained", () => {
  const result = evaluateDraft({ ...createProductDraft(), values: {
    "composition.cocoa_percentage": "0", "composition.milk_solids_percentage": " ",
    "dietary.vegan_claim": "absent", "composition.nut_types": '["almond","hazelnut","almond"]',
    "composition.allergen_ingredients": "[]",
    "origin.cocoa_countries": "Ghana, Ecuador\nPeru", "unknown.schema_key": "ignored"
  } }, fields);
  assert.deepEqual(result.errors, {});
  assert.equal(result.traits["composition.cocoa_percentage"], 0);
  assert.equal(result.traits["dietary.vegan_claim"], "absent");
  assert.deepEqual(result.traits["composition.nut_types"], ["almond", "hazelnut"]);
  assert.deepEqual(result.traits["composition.allergen_ingredients"], [], "An explicitly empty list is distinct from unspecified");
  assert.deepEqual(result.traits["origin.cocoa_countries"], ["Ghana", "Ecuador", "Peru"]);
  assert.equal("composition.milk_solids_percentage" in result.traits, false);
  assert.equal("unknown.schema_key" in result.traits, false);
});

test("invalid pack context or trait values cannot produce a misleading chart marker", () => {
  for (const edit of [{ packPrice: "" }, { packPrice: "-1" }, { packPrice: "Infinity" }, { weightGrams: "0" }, { weightGrams: "" }, { weightGrams: "1e-323", packPrice: "1e308" }]) {
    const result = evaluateDraft({ ...createProductDraft(), ...edit }, fields);
    assert.equal(result.marker, null);
    assert.ok(Object.keys(result.errors).length);
  }
  const result = evaluateDraft({ ...createProductDraft(), values: {
    "composition.cocoa_percentage": "101", "quantity.pack_count": "1.5",
    "dietary.vegan_claim": "maybe", "packaging.materials": "unobtainium",
    "origin.cocoa_countries": "[false]"
  } }, fields);
  assert.equal(result.marker, null);
  assert.equal(Object.keys(result.errors).length, 5);
});

test("copying a listing is independent, known-only, and uses the observed price's own weight", () => {
  const product: Product = {
    id: "test", name: "Source bar", brand: null, retailer: null, source: "source", role: "brand", reviewStatus: "unreviewed", known: 1, conflicts: 1, sourceListingIds: [], latestPriceConflict: false,
    attributes: {
      "composition.cocoa_percentage": { value: 70, status: "known", unit: "percent", reviewStatus: "unreviewed" },
      "dietary.vegan_claim": { value: "present", status: "conflict", unit: null, reviewStatus: "unreviewed" },
      "composition.ingredients_text": { value: "Incomplete…", status: "known", unit: null, reviewStatus: "unreviewed", truncated: true },
      "quantity.total_edible_weight_g": { value: 400, status: "known", unit: "g", reviewStatus: "unreviewed" }
    },
    prices: [{ observation_id: "price", observed_at: null, currency: "GBP", displayed_price: 4, displayed_price_per_100g_gbp: 5, total_edible_weight_g: 80, quantity_status: "known", model_eligible: false }]
  };
  const before = structuredClone(product);
  const draft = draftFromProduct(product, fields);
  assert.equal(draft.weightGrams, "80");
  assert.equal(draft.values["composition.cocoa_percentage"], "70");
  assert.equal("dietary.vegan_claim" in draft.values, false);
  assert.equal("composition.ingredients_text" in draft.values, false);
  assert.equal(evaluateDraft(draft, fields).marker?.price, 5);
  draft.values["composition.cocoa_percentage"] = "90";
  assert.deepEqual(product, before);
  assert.equal(evaluateDraft(draftFromProduct({ ...product, latestPriceConflict: true }, fields), fields).marker, null);
});

test("reviewed extraction merges into the latest draft without changing its proposed pack price", () => {
  const draft = { ...createProductDraft(), packPrice: "6.25", values: { "composition.cocoa_percentage": "30", "dietary.vegan_claim": "absent" } };
  const before = structuredClone(draft);
  const applied = applyExtractedTraits(draft, [
    { key: "identity.name", value: "Extracted bar" },
    { key: "quantity.total_edible_weight_g", value: 80 },
    { key: "composition.cocoa_percentage", value: 75 },
    { key: "composition.nut_types", value: ["almond", "hazelnut"] },
    { key: "unknown.price", value: 999 },
    { key: "composition.milk_solids_percentage", value: 101 }
  ], fields);
  assert.deepEqual(draft, before);
  assert.equal(applied.name, "Extracted bar");
  assert.equal(applied.weightGrams, "80");
  assert.equal(applied.packPrice, "6.25");
  assert.equal(applied.values["dietary.vegan_claim"], "absent");
  assert.equal(applied.values["composition.nut_types"], '["almond","hazelnut"]');
  assert.equal(applied.values["composition.cocoa_percentage"], "75");
  assert.equal("composition.milk_solids_percentage" in applied.values, false);
  assert.equal("unknown.price" in applied.values, false);
  assert.equal(evaluateDraft(applied, fields).score.score, 42.5);
});
