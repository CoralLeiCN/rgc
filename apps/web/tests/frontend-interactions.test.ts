// Controller regression proof with a fake renderer; this does not measure browser GPU performance.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { cloudAppearance, type CloudFamily } from "../lib/client/cloud-family";
import type { PointsResponse } from "../lib/contracts";

// Reuse tsx's installed compiler without adding a test-only DOM or compiler dependency.
const projectRequire = createRequire(path.join(process.cwd(), "package.json"));
const compiler = projectRequire(projectRequire.resolve("esbuild", { paths: [path.dirname(projectRequire.resolve("tsx"))] })) as {
  transformSync: (source: string, options: { loader: string; format: string; target: string; jsx: string }) => { code: string };
};

type Callback = (...args: unknown[]) => unknown;
type VirtualNode = { type: unknown; props: Record<string, unknown> };
type Effect = { deps: unknown[]; cleanup?: () => void };
type Ref = { current: unknown };

function cloudHarness() {
  let cursor = 0;
  let clock = 0;
  let frameId = 0;
  const hooks: unknown[] = [];
  let pending: { index: number; effect: () => void | (() => void); deps: unknown[] }[] = [];
  const frames = new Map<number, () => void>();
  const nodeEvents = new Map<string, Callback>();
  const windowEvents = new Map<string, { callback: Callback; capture: boolean }[]>();
  const selections: string[] = [];
  const calls = { react: [] as { traces: Record<string, unknown>[]; layout: Record<string, unknown>; config: Record<string, unknown> }[], restyle: [] as unknown[], relayout: [] as unknown[], resize: 0, purge: 0 };
  let resizeCallback: (() => void) | undefined;
  const element = {
    on(event: string, callback: Callback) { nodeEvents.set(event, callback); },
    removeAllListeners() { nodeEvents.clear(); },
  };
  const renderer = {
    async react(_node: unknown, traces: Record<string, unknown>[], layout: Record<string, unknown>, config: Record<string, unknown>) { calls.react.push({ traces, layout, config }); },
    async restyle(_node: unknown, update: unknown, traces: unknown) { calls.restyle.push({ update, traces }); },
    async relayout(_node: unknown, layout: unknown) { calls.relayout.push(layout); },
    purge() { calls.purge++; },
    Plots: { async resize() { calls.resize++; } },
  };
  const captureValue = (options: unknown) => typeof options === "object" && options !== null ? Boolean((options as { capture?: boolean }).capture) : options === true;
  const fakeWindow = {
    Plotly: renderer,
    requestAnimationFrame(callback: () => void) { frames.set(++frameId, callback); return frameId; },
    cancelAnimationFrame(id: number) { frames.delete(id); },
    addEventListener(event: string, callback: Callback, options?: unknown) {
      windowEvents.set(event, [...(windowEvents.get(event) ?? []), { callback, capture: captureValue(options) }]);
    },
    removeEventListener(event: string, callback: Callback, options?: unknown) {
      windowEvents.set(event, (windowEvents.get(event) ?? []).filter((listener) => listener.callback !== callback || listener.capture !== captureValue(options)));
    },
  };
  const react = {
    memo: (component: unknown) => component,
    useRef(initial: unknown) { const index = cursor++; return hooks[index] ?? (hooks[index] = { current: initial }); },
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = initial;
      return [hooks[index], (value: unknown) => { hooks[index] = typeof value === "function" ? (value as (previous: unknown) => unknown)(hooks[index]) : value; }];
    },
    useEffect(effect: () => void | (() => void), deps: unknown[]) {
      const index = cursor++;
      const previous = hooks[index] as Effect | undefined;
      if (!previous || deps.some((dependency, offset) => !Object.is(previous.deps[offset], dependency))) pending.push({ index, effect, deps });
    },
  };
  const jsx = (type: unknown, props: Record<string, unknown>): VirtualNode => ({ type, props });
  const exports: Record<string, unknown> = {};
  const source = readFileSync(path.join(process.cwd(), "components/PointCloud.tsx"), "utf8");
  const compiled = compiler.transformSync(source, { loader: "tsx", format: "cjs", target: "es2022", jsx: "automatic" }).code;
  const module = { exports };
  vm.runInNewContext(compiled, {
    exports, module,
    require(specifier: string) {
      if (specifier === "react") return react;
      if (specifier === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (specifier === "../lib/client/display") return { unitLabel: (value: string) => value };
      if (specifier === "../lib/client/cloud-family") return { cloudAppearance };
      if (specifier === "./Icons") return { Icon: () => null };
      throw new Error(`Unexpected controller import: ${specifier}`);
    },
    window: fakeWindow,
    document: {},
    ResizeObserver: class { constructor(callback: () => void) { resizeCallback = callback; } observe() {} disconnect() {} },
    structuredClone,
    performance: { now: () => clock },
  }, { filename: "PointCloud.controller-test.cjs" });
  const component = module.exports.PointCloud as (props: { data: PointsResponse; selectedId: string | null; onSelect: (id: string) => void; family?: CloudFamily | null }) => VirtualNode;
  const onSelect = (id: string) => selections.push(id);
  let tree: VirtualNode;
  const descendants = (value: unknown): VirtualNode[] => {
    if (Array.isArray(value)) return value.flatMap(descendants);
    if (!value || typeof value !== "object" || !("props" in value)) return [];
    const node = value as VirtualNode;
    return [node, ...descendants(node.props.children)];
  };
  function render(data: PointsResponse, selectedId: string | null = null, family: CloudFamily | null = null) {
    cursor = 0;
    pending = [];
    tree = component({ data, selectedId, onSelect, family });
    const chart = descendants(tree).find((node) => node.props.className === "point-cloud");
    assert.ok(chart, "The production component exposes a chart container");
    (chart.props.ref as Ref).current = element;
    for (const { index, effect, deps } of pending) {
      (hooks[index] as Effect | undefined)?.cleanup?.();
      hooks[index] = { deps, cleanup: effect() };
    }
  }
  async function settle() {
    for (let turn = 0; turn < 8; turn++) {
      await Promise.resolve();
      const callbacks = [...frames.values()]; frames.clear();
      for (const callback of callbacks) callback();
    }
  }
  function pointer(event: string, x: number, y: number) {
    const chart = descendants(tree).find((node) => node.props.className === "point-cloud");
    const handler = chart?.props[event];
    if (typeof handler === "function") handler({ clientX: x, clientY: y, button: 0 });
  }
  function windowEvent(event: string, capture: boolean, details: unknown = {}) {
    for (const listener of windowEvents.get(event) ?? []) if (listener.capture === capture) listener.callback(details);
  }
  function releaseWithPlotlyClick(id: string) {
    // Plotly may emit from its target/bubbling handler before window bubble listeners.
    windowEvent("pointerup", true);
    nodeEvents.get("plotly_click")?.({ points: [{ customdata: id }] });
    windowEvent("pointerup", false);
  }
  return {
    calls, selections, render, settle, pointer, windowEvent, releaseWithPlotlyClick,
    plotEvent: (event: string, details: unknown) => nodeEvents.get(event)?.(details),
    advance: (milliseconds: number) => { clock += milliseconds; },
    resize: () => resizeCallback?.(),
    camera: (index: number) => { const buttons = descendants(tree).filter((node) => node.type === "button"); (buttons[index].props.onClick as () => void)(); },
    dispose: () => { for (const hook of hooks) (hook as Effect | undefined)?.cleanup?.(); },
  };
}

const familyCoverage = { composition: { known: 1, unknown: 1, conflict: 0, not_applicable: 0, reviewed: 0, total: 2 } };
const dataset: PointsResponse = {
  axes: [{ key: "weight", label: "Weight", unit: "g" }, { key: "cocoa", label: "Cocoa", unit: "%" }, { key: "price", label: "Price", unit: "GBP" }],
  points: [{ id: "a", name: "First", source: "test", role: "retail", familyCoverage, x: 100, y: 70, z: 2.5 }, { id: "b", name: "Second", source: "test", role: "brand", familyCoverage, x: 90, y: 85, z: 3 }],
  totalMatched: 2, completeCount: 2, excludedCount: 0, sampled: false, limit: 500,
};

test("production PointCloud isolates camera and selection updates from complete geometry", async () => {
  const harness = cloudHarness();
  harness.render(dataset);
  await harness.settle();
  assert.equal(harness.calls.react.length, 1);
  assert.equal(harness.calls.react[0].traces.length, 2);
  assert.equal(harness.calls.react[0].config.plotGlPixelRatio, 1);
  for (const trace of harness.calls.react[0].traces) assert.equal((trace.marker as { opacity: number }).opacity, 1);
  for (let index = 0; index < 40; index++) harness.plotEvent("plotly_relayout", { "scene.camera": { eye: { x: index, y: 1, z: 1 } } });
  await harness.settle();
  assert.equal(harness.calls.react.length, 1, "Orbit events never redraw the whole cloud");
  assert.equal(harness.calls.restyle.length, 0);

  harness.pointer("onPointerDownCapture", 100, 100);
  harness.releaseWithPlotlyClick("b");
  assert.deepEqual(harness.selections, ["b"], "An ordinary click survives Plotly/window event ordering");
  harness.render(dataset, "b");
  await harness.settle();
  assert.equal(harness.calls.restyle.length, 1);
  assert.equal(harness.calls.react.length, 1, "Selection changes only the highlight trace");

  harness.camera(1);
  await harness.settle();
  assert.equal(harness.calls.relayout.length, 1);
  assert.equal(harness.calls.react.length, 1, "Camera buttons perform camera-only updates");
  harness.dispose();
  assert.equal(harness.calls.purge, 1);
});

test("production PointCloud defers geometry during orbit and suppresses drag-triggered selection", async () => {
  const harness = cloudHarness();
  harness.render(dataset);
  await harness.settle();
  harness.pointer("onPointerDownCapture", 100, 100);
  // Movement can leave the chart bounds; tracking must still recognize the drag.
  harness.windowEvent("pointermove", true, { clientX: 150, clientY: 150 });
  harness.windowEvent("pointermove", false, { clientX: 150, clientY: 150 });
  const changed = { ...dataset, points: dataset.points.map((point) => ({ ...point, z: point.z + 1 })) };
  const latest = { ...dataset, points: dataset.points.map((point) => ({ ...point, z: point.z + 2 })) };
  harness.render(changed);
  harness.render(latest);
  harness.resize();
  await harness.settle();
  assert.equal(harness.calls.react.length, 1, "Cohort updates remain queued during dragging");
  assert.equal(harness.calls.resize, 0, "Resizing is deferred while orbiting");
  harness.plotEvent("plotly_click", { points: [{ customdata: "b" }] });
  harness.releaseWithPlotlyClick("b");
  assert.deepEqual(harness.selections, [], "Dragging must not select a hovered product");
  await harness.settle();
  assert.equal(harness.calls.react.length, 2, "One render flushes the latest pending cohort after release");
  assert.equal(harness.calls.resize, 1, "A resize received during dragging is replayed after release");
  assert.deepEqual(Array.from(harness.calls.react[1].traces[0].z as number[]), latest.points.map((point) => point.z));
  harness.advance(200);
  harness.pointer("onPointerDownCapture", 150, 150);
  harness.releaseWithPlotlyClick("a");
  assert.deepEqual(harness.selections, ["a"], "A later ordinary click still selects");
  harness.dispose();
});

test("production API hook hides previous selections and ignores aborted responses arriving late", async () => {
  let cursor = 0;
  const hooks: unknown[] = [];
  let pending: { index: number; effect: () => void | (() => void); deps: unknown[] }[] = [];
  const requests: { url: string; signal: AbortSignal; resolve: (body: unknown) => void }[] = [];
  const react = {
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = initial;
      return [hooks[index], (value: unknown) => { hooks[index] = typeof value === "function" ? (value as (previous: unknown) => unknown)(hooks[index]) : value; }];
    },
    useCallback(callback: unknown) { cursor++; return callback; },
    useEffect(effect: () => void | (() => void), deps: unknown[]) {
      const index = cursor++;
      const previous = hooks[index] as Effect | undefined;
      if (!previous || deps.some((dependency, offset) => !Object.is(previous.deps[offset], dependency))) pending.push({ index, effect, deps });
    },
  };
  const module = { exports: {} as Record<string, unknown> };
  const source = readFileSync(path.join(process.cwd(), "lib/client/api.ts"), "utf8");
  vm.runInNewContext(compiler.transformSync(source, { loader: "ts", format: "cjs", target: "es2022", jsx: "automatic" }).code, {
    module, exports: module.exports, require: (specifier: string) => { assert.equal(specifier, "react"); return react; },
    AbortController, URLSearchParams,
    fetch(url: string, options: { signal: AbortSignal }) {
      return new Promise((resolve) => { requests.push({ url, signal: options.signal, resolve: (body) => resolve({ ok: true, json: async () => body }) }); });
    },
  }, { filename: "api.controller-test.cjs" });
  const useApi = module.exports.useApi as (url: string | null) => { data: unknown; loading: boolean; error: string | null; retry: () => void };
  const render = (url: string | null) => {
    cursor = 0; pending = [];
    const state = useApi(url);
    for (const { index, effect, deps } of pending) {
      (hooks[index] as Effect | undefined)?.cleanup?.();
      hooks[index] = { deps, cleanup: effect() };
    }
    return state;
  };
  const settle = async () => { for (let index = 0; index < 8; index++) await Promise.resolve(); };
  assert.equal(render("/api/products/a").loading, true);
  requests[0].resolve({ id: "a" });
  await settle();
  assert.deepEqual(render("/api/products/a").data, { id: "a" });

  const changing = render("/api/products/b");
  assert.equal(changing.data, null, "Previous product evidence is hidden immediately on selection change");
  assert.equal(changing.loading, true);
  assert.equal(requests[0].signal.aborted, true);
  render("/api/products/c");
  assert.equal(requests[1].signal.aborted, true);
  requests[2].resolve({ id: "c" });
  await settle();
  requests[1].resolve({ id: "b" }); // Deliberately emulate a transport that still resolves after abort.
  await settle();
  assert.deepEqual(render("/api/products/c").data, { id: "c" });
  assert.equal(render(null).data, null, "Clearing selection immediately hides old evidence");
  assert.equal(requests[2].signal.aborted, true);
  for (const hook of hooks) (hook as Effect | undefined)?.cleanup?.();
});


test("family focus recolours existing coordinates after orbit without resetting geometry or selection", async () => {
  const harness = cloudHarness();
  const composition = { id: "composition", label: "Composition", color: "#aabbcc" };
  harness.render(dataset, "a");
  await harness.settle();
  harness.pointer("onPointerDownCapture", 100, 100);
  harness.windowEvent("pointermove", true, { clientX: 180, clientY: 180 });
  harness.render(dataset, "b", composition);
  await harness.settle();
  assert.equal(harness.calls.restyle.length, 0, "Appearance stays queued during an orbit");
  harness.releaseWithPlotlyClick("a");
  await harness.settle();
  assert.equal(harness.calls.react.length, 1, "Family focus never rebuilds geometry");
  assert.equal(harness.calls.relayout.length, 0, "Family focus never resets the camera");
  const changes = harness.calls.restyle as { update: Record<string, unknown>; traces: number[] }[];
  assert.deepEqual(Array.from(changes[0].traces), [0]);
  assert.deepEqual(Array.from((changes[0].update["marker.color"] as string[][])[0]), ["#aabbcc", "#aabbcc"]);
  assert.deepEqual(Array.from((changes[0].update["marker.symbol"] as string[][])[0]), ["circle-open", "circle-open"]);
  assert.ok(!("x" in changes[0].update), "Only appearance, not coordinates, is restyled");
  assert.deepEqual(Array.from((changes[1].update.customdata as string[][])[0]), ["b"], "Concurrent selection is retained");
  harness.render(dataset, "b", null);
  await harness.settle();
  assert.equal(harness.calls.react.length, 1);
  assert.deepEqual(Array.from((changes[2].update["marker.color"] as string[][])[0]), ["#89e6ca", "#b7a4f7"]);
  harness.dispose();
});

test("family cloud evidence distinguishes unknown, partial, complete, conflicting and not applicable", () => {
  const family = { id: "composition", label: "Composition", color: "#aabbcc" };
  const point = dataset.points[0];
  const style = (counts: Partial<typeof familyCoverage.composition>) => cloudAppearance({ ...point, familyCoverage: { composition: { ...familyCoverage.composition, ...counts } } }, family);
  assert.equal(style({}).symbol, "circle-open");
  assert.equal(style({ known: 2, unknown: 0 }).symbol, "circle");
  assert.equal(style({ known: 0, unknown: 2 }).color, "#607481");
  assert.equal(style({ known: 0, unknown: 0, not_applicable: 2 }).symbol, "square-open");
  assert.equal(style({ known: 1, unknown: 0, conflict: 1 }).symbol, "diamond");
  assert.match(style({}).detail, /1\/2 traits known/);
  assert.equal(cloudAppearance({ ...point, familyCoverage: {} }, family).detail, "Family coverage unavailable");
});
