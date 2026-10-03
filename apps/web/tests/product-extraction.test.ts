// Run the production extraction controller with explicit async responses and minimal React hooks.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { transformSync } from "esbuild";
import type { FieldDefinition } from "../lib/contracts";
import * as contract from "../lib/extraction-contract";
import * as draftHelpers from "../lib/client/product-draft";
import * as display from "../lib/client/display";

type Node = { type: unknown; props: Record<string, unknown> };
type Effect = { deps: unknown[]; cleanup?: () => void };
type Request = { url: string; options: RequestInit; resolve: (value: unknown) => void };
const fields: FieldDefinition[] = [
  { key: "identity.name", type: "string" },
  { key: "quantity.total_edible_weight_g", type: "number", minimum: 0 },
  { key: "composition.cocoa_percentage", type: "number", minimum: 0, maximum: 100 },
  { key: "composition.nut_types", type: "string_list", allowedValues: ["almond", "hazelnut"] }
].map(field => ({ label: field.key, group: field.key.split(".")[0], known: 0, conflicts: 0, numeric: false, numericKnown: 0, unit: null, scope: "product", description: "", qualifier: "", minimum: null, maximum: null, allowedValues: [], modelRole: null, modelSelected: false, modelDefinition: null, ...field }));

function harness() {
  let cursor = 0, objectId = 0, changes = 0;
  let draft = draftHelpers.createProductDraft();
  const hooks: unknown[] = [];
  const pending: Request[] = [];
  const revoked: string[] = [];
  let effects: { index: number; effect: () => void | (() => void); deps: unknown[] }[] = [];
  let tree: Node;
  const react = {
    useState(initial: unknown) { const index = cursor++; if (!(index in hooks)) hooks[index] = initial; return [hooks[index], (value: unknown) => { hooks[index] = typeof value === "function" ? (value as (current: unknown) => unknown)(hooks[index]) : value; }]; },
    useRef(initial: unknown) { const index = cursor++; return hooks[index] ?? (hooks[index] = { current: initial }); },
    useEffect(effect: () => void | (() => void), deps: unknown[]) { const index = cursor++; const old = hooks[index] as Effect | undefined; if (!old || deps.some((value, at) => !Object.is(value, old.deps[at]))) effects.push({ index, effect, deps }); }
  };
  const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props });
  const module = { exports: {} as Record<string, unknown> };
  vm.runInNewContext(transformSync(readFileSync(path.join(process.cwd(), "components/ProductExtraction.tsx"), "utf8"), { loader: "tsx", format: "cjs", jsx: "automatic", target: "es2022" }).code, {
    module, exports: module.exports, AbortController, Uint8Array, btoa,
    URL: { createObjectURL: () => `blob:preview-${++objectId}`, revokeObjectURL: (url: string) => revoked.push(url) },
    fetch: (url: string, options: RequestInit) => new Promise(resolve => pending.push({ url, options, resolve })),
    require(name: string) {
      if (name === "react") return react;
      if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (name === "../lib/extraction-contract") return contract;
      if (name === "../lib/client/product-draft") return draftHelpers;
      if (name === "../lib/client/display") return display;
      if (name === "./HelpTip") return { HelpTip: () => null };
      if (name === "./Icons") return { Icon: () => null };
      throw new Error(`Unexpected extraction import: ${name}`);
    }
  });
  const component = module.exports.ProductExtraction as (props: unknown) => Node;
  function nodes(value: unknown = tree): Node[] {
    if (Array.isArray(value)) return value.flatMap(item => nodes(item ?? null));
    if (!value || typeof value !== "object" || !("props" in value)) return [];
    const node = value as Node;
    if (typeof node.type === "function") return nodes(node.type(node.props));
    return [node, ...nodes(node.props.children ?? null)];
  }
  function text(value: unknown): string {
    if (Array.isArray(value)) return value.map(text).join("");
    if (value && typeof value === "object" && "props" in value) return text((value as Node).props.children);
    return typeof value === "string" || typeof value === "number" ? String(value) : "";
  }
  function find(predicate: (node: Node) => boolean) { const node = nodes().find(predicate); assert.ok(node); return node; }
  function render() {
    cursor = 0; effects = [];
    tree = component({ fields, draft, onChange(next: draftHelpers.ProductDraft) { draft = next; changes++; } });
    const input = find(node => node.props.id === "config-product-image");
    const ref = input.props.ref as { current: unknown }; if (!ref.current) ref.current = { value: "" };
    for (const { index, effect, deps } of effects) { (hooks[index] as Effect | undefined)?.cleanup?.(); hooks[index] = { deps, cleanup: effect() }; }
  }
  render();
  return {
    pending, revoked, nodes, find, text, render,
    input(value: string) { (find(node => node.props.id === "config-product-description").props.onChange as (event: unknown) => void)({ target: { value } }); render(); },
    image(file: File | null) { (find(node => node.props.id === "config-product-image").props.onChange as (event: unknown) => void)({ target: { files: file ? [file] : [] } }); render(); render(); },
    fileInput: () => (find(node => node.props.id === "config-product-image").props.ref as { current: { value: string } }).current,
    click(label: string) { const result = (find(node => node.type === "button" && text(node.props.children).startsWith(label)).props.onClick as () => unknown)(); render(); return result; },
    check(index: number, checked: boolean) { (nodes().filter(node => node.type === "input" && node.props.type === "checkbox")[index].props.onChange as (event: unknown) => void)({ target: { checked } }); render(); },
    edit(partial: Partial<draftHelpers.ProductDraft>) { draft = { ...draft, ...partial }; render(); },
    async respond(index: number, payload: unknown, status = 200) { pending[index].resolve({ ok: status < 400, status, json: async () => payload }); await new Promise(resolve => setImmediate(resolve)); render(); },
    getDraft: () => draft, changes: () => changes,
    dispose() { for (const hook of hooks) (hook as Effect | undefined)?.cleanup?.(); }
  };
}

const candidates: contract.ExtractionResponse = { provider: "codex", model: "test-model", warnings: [], traits: [
  { key: "composition.cocoa_percentage", value: 75, evidence: "75% cocoa" },
  { key: "identity.name", value: "Extracted bar", evidence: "Extracted bar" },
  { key: "quantity.total_edible_weight_g", value: 80, evidence: "80 g" }
] };

test("extraction requires review and merges selected candidates into the latest draft only on apply", async () => {
  const form = harness();
  form.input("Extracted bar, 75% cocoa, 80 g");
  const extracting = form.click("Extract traits");
  form.edit({ packPrice: "7.15", name: "My edited name" });
  await form.respond(0, candidates); await extracting;
  assert.equal(form.changes(), 0, "Async response never edits the draft");
  assert.equal(form.getDraft().name, "My edited name");
  form.check(1, false);
  form.click("Apply extracted traits");
  assert.equal(form.changes(), 1);
  assert.equal(form.getDraft().packPrice, "7.15");
  assert.equal(form.getDraft().name, "My edited name", "Unchecked candidate preserves the latest edit");
  assert.equal(form.getDraft().weightGrams, "80");
  assert.equal(draftHelpers.evaluateDraft(form.getDraft(), fields).score.score, 42.5);
  assert.equal(form.nodes().some(node => node.props.className === "config-extract-review"), false);
  form.dispose();
});

test("changing extraction inputs aborts requests and suppresses stale candidates", async () => {
  const form = harness();
  form.input("Old description"); const older = form.click("Extract traits");
  form.input("Current description");
  assert.equal(form.pending[0].options.signal?.aborted, true);
  const latest = form.click("Extract traits");
  await form.respond(0, candidates); await older;
  assert.equal(form.nodes().some(node => node.props.className === "config-extract-review"), false);
  await form.respond(1, { ...candidates, traits: candidates.traits.slice(0, 1) }); await latest;
  assert.equal(form.nodes().filter(node => node.props.className === "config-candidate").length, 1);
  form.input("Edited after extraction");
  assert.equal(form.nodes().some(node => node.props.className === "config-extract-review"), false);
  const pending = form.click("Extract traits"); form.dispose();
  assert.equal(form.pending[2].options.signal?.aborted, true);
  await form.respond(2, candidates); await pending;
  assert.equal(form.changes(), 0);
});

test("image inputs are bounded, sent as base64 only, and preview URLs are released", async () => {
  const form = harness();
  form.image(new File(["no"], "wrong.gif", { type: "image/gif" }));
  assert.match(form.text(form.find(node => node.props.role === "alert").props.children), /PNG, JPEG or WebP/);
  form.image(new File([new Uint8Array(contract.MAX_IMAGE_BYTES + 1)], "large.png", { type: "image/png" }));
  assert.match(form.text(form.find(node => node.props.role === "alert").props.children), /2 MiB/);
  form.image(new File(["image bytes"], "label.png", { type: "image/png" }));
  assert.equal(form.find(node => node.type === "img").props.src, "blob:preview-1");
  const pending = form.click("Extract traits");
  await new Promise(resolve => setImmediate(resolve));
  const body = JSON.parse(String(form.pending[0].options.body));
  assert.equal(body.image.data, btoa("image bytes"));
  assert.equal(body.image.mimeType, "image/png");
  assert.equal(body.description, "");
  await form.respond(0, { error: { message: "Connect the Codex bridge before extracting." } }, 503); await pending;
  assert.match(form.text(form.find(node => node.props.role === "alert").props.children), /Connect the Codex bridge/);
  assert.equal(form.changes(), 0);
  form.image(new File(["replacement"], "second.webp", { type: "image/webp" }));
  assert.deepEqual(form.revoked, ["blob:preview-1"]);
  form.fileInput().value = "C:\\fakepath\\second.webp";
  form.image(null);
  assert.equal(form.fileInput().value, "", "Removing an image lets the browser fire change for the same file again");
  form.image(new File(["replacement"], "second.webp", { type: "image/webp" }));
  assert.equal(form.find(node => node.type === "img").props.src, "blob:preview-3");
  form.dispose();
  assert.deepEqual(form.revoked, ["blob:preview-1", "blob:preview-2", "blob:preview-3"]);
});
