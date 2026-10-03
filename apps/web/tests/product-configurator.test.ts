// Exercise the production controlled form without a browser or external data writes.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { transformSync } from "esbuild";
import type { FieldDefinition, Product, SchemaResponse } from "../lib/contracts";
import * as display from "../lib/client/display";
import * as families from "../lib/client/families";
import * as draftHelpers from "../lib/client/product-draft";
import * as traitDemo from "../lib/trait-demo";

type VirtualNode = { type: unknown; props: Record<string, unknown>; key?: string };
function field(key: string, group: string, type: string): FieldDefinition {
  return { key, group, type, label: key, known: 1, conflicts: 0, numeric: type === "number", numericKnown: type === "number" ? 1 : 0, unit: null, scope: "product", description: key, qualifier: "", minimum: type === "number" ? 0 : null, maximum: key === "composition.cocoa_percentage" ? 100 : null, allowedValues: [], modelRole: null, modelSelected: false, modelDefinition: null };
}
const fields = [field("identity.name", "identity", "string"), field("quantity.total_edible_weight_g", "quantity", "number"), field("composition.cocoa_percentage", "composition", "number"), field("certifications.test", "certifications", "boolean")];
const selected: Product = {
  id: "selected", name: "Selected chocolate", source: "test", brand: null, retailer: null, role: "retail", reviewStatus: "unreviewed", known: 1, conflicts: 0, latestPriceConflict: false, sourceListingIds: [],
  attributes: { "composition.cocoa_percentage": { status: "known", value: 80, unit: null, reviewStatus: "unreviewed" } },
  prices: [{ observation_id: "price", observed_at: null, currency: "GBP", displayed_price: 4, displayed_price_per_100g_gbp: 2, total_edible_weight_g: 200, quantity_status: "known", model_eligible: false }]
};

function configuratorHarness() {
  let cursor = 0;
  const hooks: unknown[] = [];
  let draft = draftHelpers.createProductDraft();
  let currentSelection: Product | null = selected;
  let loading = false;
  let changes = 0;
  let tree: VirtualNode;
  const jsx = (type: unknown, props: Record<string, unknown>, key?: string) => ({ type, props, key });
  let extractionSession: string | undefined;
  const extractionComponent = () => null;
  const react = {
    useState(initial: unknown) { const index = cursor++; if (!(index in hooks)) hooks[index] = initial; return [hooks[index], (value: unknown) => { hooks[index] = typeof value === "function" ? (value as (previous: unknown) => unknown)(hooks[index]) : value; }]; },
    useMemo(compute: () => unknown) { return compute(); }
  };
  const module = { exports: {} as Record<string, unknown> };
  vm.runInNewContext(transformSync(readFileSync(path.join(process.cwd(), "components/ProductConfigurator.tsx"), "utf8"), { loader: "tsx", format: "cjs", jsx: "automatic", target: "es2022" }).code, {
    module, exports: module.exports, document: { getElementById: () => ({ focus() {} }) },
    require(name: string) {
      if (name === "react") return react;
      if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (name === "../lib/client/display") return display;
      if (name === "../lib/client/families") return families;
      if (name === "../lib/client/product-draft") return draftHelpers;
      if (name === "../lib/trait-demo") return traitDemo;
      if (name === "./ProductExtraction") return { ProductExtraction: extractionComponent };
      if (name === "./HelpTip") return { HelpTip: () => null };
      if (name === "./Icons") return { Icon: () => null };
      throw new Error(`Unexpected form import ${name}`);
    }
  });
  const component = module.exports.ProductConfigurator as (props: Record<string, unknown>) => VirtualNode;
  const schema = { fields, contract: { groups: ["identity", "quantity", "composition", "certifications"] } } as SchemaResponse;
  const descendants = (value: unknown): VirtualNode[] => {
    if (Array.isArray(value)) return value.flatMap(descendants);
    if (!value || typeof value !== "object" || !("props" in value)) return [];
    const node = value as VirtualNode;
    if (node.type === extractionComponent) extractionSession = node.key;
    if (typeof node.type === "function") return descendants(node.type(node.props));
    return [node, ...descendants(node.props.children)];
  };
  const text = (value: unknown): string => {
    if (Array.isArray(value)) return value.map(text).join("");
    if (value && typeof value === "object" && "props" in value) return text((value as VirtualNode).props.children);
    return typeof value === "string" || typeof value === "number" ? String(value) : "";
  };
  function render() {
    cursor = 0;
    tree = component({ schema, draft, selectedProduct: currentSelection, selectedLoading: loading, children: jsx("span", { children: "Original source evidence" }), onChange(next: draftHelpers.ProductDraft) { changes++; draft = next; } });
    descendants(tree);
  }
  function find(predicate: (node: VirtualNode) => boolean) { const node = descendants(tree).find(predicate); assert.ok(node); return node; }
  render();
  return {
    input(id: string, value: string) { const node = find(node => node.props.id === id); (node.props.onChange as (event: unknown) => void)({ target: { value } }); render(); },
    click(label: string) { const node = find(node => node.type === "button" && text(node.props.children) === label); (node.props.onClick as () => void)(); render(); },
    select(product: Product | null, pending = false) { currentSelection = product; loading = pending; render(); },
    nodes: () => descendants(tree), getDraft: () => draft, changeCount: () => changes, extractionSession: () => extractionSession,
    find, text
  };
}

test("configurator preserves edits on source selection and copies only after explicit action", () => {
  const form = configuratorHarness();
  const initialSession = form.extractionSession();
  assert.equal(form.changeCount(), 0, "Rendering a selected listing does not overwrite the draft");
  form.input("configured-product-name", "My launch product");
  form.input("configured-product-price", "7.50");
  form.select({ ...selected, name: "Another source product" });
  assert.equal(form.extractionSession(), initialSession, "Normal edits and selection changes preserve pending review");
  assert.equal(form.getDraft().name, "My launch product");
  assert.equal(form.getDraft().packPrice, "7.50");
  form.click("Use selected listing");
  assert.notEqual(form.extractionSession(), initialSession, "Explicit import starts a fresh extraction session");
  const importedSession = form.extractionSession();
  assert.equal(form.getDraft().name, "Another source product");
  assert.equal(form.getDraft().values["composition.cocoa_percentage"], "80");
  form.click("Reset");
  assert.notEqual(form.extractionSession(), importedSession, "Reset unmounts extraction so its cleanup aborts pending work");
  assert.deepEqual(form.getDraft(), draftHelpers.createProductDraft());
  form.select(null, true);
  assert.equal(form.find(node => node.type === "button" && form.text(node.props.children) === "Use selected listing").props.disabled, true);
});

test("configurator derives a readonly score while the proposed price slider only changes price", () => {
  const form = configuratorHarness();
  form.input("configure-composition-cocoa_percentage", "70");
  assert.equal(draftHelpers.evaluateDraft(form.getDraft(), fields).score.score, 41);
  assert.equal(form.find(node => node.props.id === "configured-product-score").type, "output");
  assert.equal(form.nodes().some(node => node.type === "input" && node.props.id === "configured-product-score"), false);
  form.input("configured-product-price-slider", "7.77");
  assert.equal(form.getDraft().packPrice, "7.77");
  assert.equal(draftHelpers.evaluateDraft(form.getDraft(), fields).score.score, 41);
  form.input("configured-product-price", "55.55");
  assert.ok(Number(form.find(node => node.props.id === "configured-product-price-slider").props.max) >= 55.55);
  form.input("configure-certifications-test", "false");
  assert.equal(draftHelpers.evaluateDraft(form.getDraft(), fields).traits["certifications.test"], false);
  form.input("configure-certifications-test", "");
  assert.equal(Object.hasOwn(draftHelpers.evaluateDraft(form.getDraft(), fields).traits, "certifications.test"), false);
  form.input("configure-composition-cocoa_percentage", "120");
  assert.equal(form.find(node => node.props.id === "configure-composition-cocoa_percentage").props["aria-invalid"], true);
  assert.equal(draftHelpers.evaluateDraft(form.getDraft(), fields).marker, null);
  assert.ok(form.nodes().some(node => node.props.className === "config-validation-status"));
  form.input("configured-trait-search", "identity.name");
  assert.equal(form.nodes().filter(node => node.type === "input" && node.props.id === "configured-product-name").length, 1, "Reserved name has only one editor");
  assert.ok(form.nodes().some(node => node.props.className === "config-reserved-field"));
  const evidence = form.find(node => node.type === "details" && node.props.className === "config-source-evidence");
  assert.equal(evidence.props.open, undefined, "Original evidence starts collapsed");
  assert.match(form.text(evidence.props.children), /Original source evidence/);
});
