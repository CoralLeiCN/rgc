// Production component exercised with a renderer double; not a browser/GPU benchmark.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import { transformSync } from "esbuild";
import { TerrainRenderQueue } from "../lib/client/terrain-controller";
import { buildTerrainGeometry, rowLayerColor, type TerrainDraftPoint } from "../lib/client/terrain-geometry";
import type { TerrainResponse } from "../lib/contracts";

type VNode = { type: unknown; props: Record<string, unknown> };
type Effect = { deps: unknown[]; cleanup?: () => void };
type Callback = (event?: unknown) => void;
const descendants = (value: unknown): VNode[] => Array.isArray(value) ? value.flatMap(descendants) : value && typeof value === "object" && "props" in value ? [value as VNode, ...descendants((value as VNode).props.children)] : [];
function harness() {
  let cursor = 0, frameId = 0, time = 0, geometryBuilds = 0;
  const hooks: unknown[] = [], frames = new Map<number, () => void>(), events = new Map<string, Callback>(), windowEvents = new Map<string, Callback[]>();
  let effects: { index: number; deps: unknown[]; effect: () => void | (() => void) }[] = [];
  const selected: string[] = [];let unavailable = 0;
  const calls = { react: [] as { traces: Record<string, unknown>[]; layout: Record<string, unknown>; config: Record<string, unknown> }[], restyle: [] as { update: Record<string, unknown>; traces: number[] }[], relayout: [] as Record<string, unknown>[], purge: 0 };
  const renderer = { async react(_element: unknown, traces: Record<string, unknown>[], layout: Record<string, unknown>, config: Record<string, unknown>) { calls.react.push({ traces, layout, config }); }, async restyle(_element: unknown, update: Record<string, unknown>, traces: number[]) { calls.restyle.push({ update, traces }); }, async relayout(_element: unknown, layout: Record<string, unknown>) { calls.relayout.push(layout); }, purge() { calls.purge++; }, Plots: { async resize() {} } };
  const element = { on(name: string, callback: Callback) { events.set(name, callback); }, removeAllListeners() { events.clear(); } };
  const react = {
    memo: (component: unknown) => component,
    useRef(initial: unknown) { const i = cursor++;return hooks[i] ?? (hooks[i] = { current: initial }); },
    useState(initial: unknown) { const i = cursor++; if (!(i in hooks)) hooks[i] = initial;return [hooks[i], (value: unknown) => { hooks[i] = value; }]; },
    useEffect(effect: () => void | (() => void), deps: unknown[]) { const index = cursor++, previous = hooks[index] as Effect | undefined;if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) effects.push({ index, deps, effect }); }
  };
  const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props });const module = { exports: {} as Record<string, unknown> };
  vm.runInNewContext(transformSync(readFileSync("components/TerrainViewport.tsx", "utf8"), { loader: "tsx", format: "cjs", target: "es2022", jsx: "automatic" }).code, {
    module, exports: module.exports, structuredClone, performance: { now: () => time },
    require(name: string) {
      if (name === "react") return react;
      if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (name === "./PointCloud") return { loadPlotly: async () => renderer };
      if (name === "../lib/client/terrain-controller") return { TerrainRenderQueue };
      if (name === "../lib/client/terrain-geometry") return { rowLayerColor, buildTerrainGeometry: (...args: Parameters<typeof buildTerrainGeometry>) => { geometryBuilds++;return buildTerrainGeometry(...args); } };
      throw new Error(`Unexpected terrain import ${name}`);
    },
    ResizeObserver: class { observe() {} disconnect() {} },
    window: { requestAnimationFrame(callback: () => void) { frames.set(++frameId, callback);return frameId; }, cancelAnimationFrame(id: number) { frames.delete(id); }, addEventListener(name: string, callback: Callback) { windowEvents.set(name, [...(windowEvents.get(name) || []), callback]); }, removeEventListener(name: string, callback: Callback) { windowEvents.set(name, (windowEvents.get(name) || []).filter(item => item !== callback)); } }
  });
  const component = module.exports.TerrainViewport as (props: Record<string, unknown>) => VNode;let tree: VNode;
  const onSelect = (id: string) => selected.push(id), onUnavailable = () => { unavailable++; };
  return {
    calls, selected, geometryBuilds: () => geometryBuilds, unavailable: () => unavailable,
    render(data: TerrainResponse, props: Record<string, unknown> = {}) {
      cursor = 0;effects = [];tree = component({ data, smoothness: .5, highlightedLayer: null, selectedId: null, draft: null, onSelect, onUnavailable, ...props });
      const node = descendants(tree).find(node => node.props.className === "terrain-viewport")!;(node.props.ref as { current: unknown }).current = element;
      for (const item of effects) { (hooks[item.index] as Effect | undefined)?.cleanup?.();hooks[item.index] = { deps: item.deps, cleanup: item.effect() }; }
    },
    async settle() { for (let i = 0; i < 15; i++) { await Promise.resolve();const callbacks = [...frames.values()];frames.clear();callbacks.forEach(callback => callback()); } },
    plot(name: string, event: unknown = {}) { events.get(name)?.(event); },
    pointerDown() { const node = descendants(tree).find(node => node.props.className === "terrain-viewport")!;(node.props.onPointerDownCapture as Callback)({ button: 0, clientX: 100, clientY: 100 }); },
    window(name: string, event: unknown = {}) { windowEvents.get(name)?.forEach(callback => callback(event)); },
    camera() { const button = descendants(tree).find(node => node.type === "button")!;(button.props.onClick as () => void)(); },
    advance() { time += 250; },
    dispose() { for (const hook of hooks) (hook as Effect | undefined)?.cleanup?.(); }
  };
}
const data: TerrainResponse = {
  color: { key: "kind", label: "Kind", fields: [] }, z: { key: "cocoa", label: "Cocoa", unit: "%", fields: [] },
  rows: [{ id: "a", name: "A", price: 2, score: 40, z: 50, categories: { "kind=value:dark": 1 } }, { id: "b", name: "B", price: 3, score: 60, z: 80, categories: { "kind=value:milk": 1 } }],
  categories: [{ key: "kind=value:dark", label: "Dark", count: 1 }, { key: "kind=value:milk", label: "Milk", count: 1 }],
  totalMatched: 2, pricedCount: 2, completeCount: 2, excludedCount: 0, sampled: false, limit: 500, priceRange: [2, 3], range: "full", requestedRange: "full", rangeFallbackReason: null, belowRangeCount: 0, aboveRangeCount: 0, missingScoreCount: 0, missingZCount: 0, scoreDefinition: "Illustrative", scoreVersion: "trait-demo-1"
};
test("production terrain keeps exact coordinates, opaque bounded layers and a negative-X/Y camera", async () => {
  const h = harness();h.render(data);await h.settle();assert.equal(h.calls.react.length, 1);
  const plot = h.calls.react[0], scene = plot.layout.scene as { camera: { eye: { x: number; y: number; z: number } } };
  assert.ok(scene.camera.eye.x < 0 && scene.camera.eye.y < 0 && scene.camera.eye.z > 0);assert.equal(plot.config.plotGlPixelRatio, 1);
  const meshes = plot.traces.filter(trace => trace.type === "mesh3d");assert.ok(meshes.length <= 9);assert.ok(meshes.every(trace => trace.opacity === 1));
  const points = plot.traces.find(trace => trace.name === "Observed products")!;
  assert.deepEqual(Array.from(points.x as number[]), [2, 3]);assert.deepEqual(Array.from(points.y as number[]), [40, 60]);assert.deepEqual(Array.from(points.z as number[]), [50, 80]);h.dispose();
});
test("production terrain orbit never rebuilds geometry and price-slider changes restyle only the draft", async () => {
  const h = harness();h.render(data);await h.settle();
  for (let i = 0; i < 40; i++) h.plot("plotly_relayout", { "scene.camera": { eye: { x: -i, y: -1, z: 1 } } });
  const draft: TerrainDraftPoint = { name: "Own", price: 100, score: 73, z: 91 };
  h.render(data, { draft });await h.settle();assert.equal(h.calls.react.length, 1);assert.equal(h.geometryBuilds(), 1);
  assert.equal(h.calls.restyle.length, 1);assert.deepEqual(Array.from(h.calls.restyle[0].traces), [4]);assert.deepEqual(Array.from((h.calls.restyle[0].update.x as number[][])[0]), [100]);
  h.camera();await h.settle();assert.equal(h.calls.relayout.length, 1);assert.equal(h.geometryBuilds(), 1);h.dispose();
});
test("production terrain queues data during drag, suppresses accidental clicks and flushes the latest geometry once", async () => {
  const h = harness();h.render(data);await h.settle();h.pointerDown();h.window("pointermove", { clientX: 180, clientY: 140 });
  h.render({ ...data, rows: data.rows.map(row => ({ ...row, z: row.z + 1 })) });
  const latest = { ...data, rows: data.rows.map(row => ({ ...row, z: row.z + 2 })) };h.render(latest);await h.settle();assert.equal(h.geometryBuilds(), 1);
  h.window("pointerup");h.plot("plotly_click", { points: [{ customdata: "a" }] });await h.settle();assert.deepEqual(h.selected, []);assert.equal(h.geometryBuilds(), 2);assert.equal(h.calls.react.length, 2);
  const points = h.calls.react[1].traces.find(trace => trace.name === "Observed products")!;assert.deepEqual(Array.from(points.z as number[]), [52, 82]);
  h.advance();h.pointerDown();h.window("pointerup");h.plot("plotly_click", { points: [{ customdata: "b" }] });assert.deepEqual(h.selected, ["b"]);h.dispose();
});
test("production terrain routes WebGL loss to the accessible fallback", async () => {
  const h = harness();h.render(data);await h.settle();h.plot("plotly_webglcontextlost");assert.equal(h.unavailable(), 1);h.dispose();assert.equal(h.calls.purge, 1);
});
