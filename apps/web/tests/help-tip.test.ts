// Production interaction logic under a minimal DOM; browser rendering is a separate check.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { transformSync } from "esbuild";

type Node = { type: unknown; props: Record<string, unknown> };
type Effect = { deps: unknown[]; cleanup?: () => void };
type Handler = (event?: unknown) => void;

function helpHarness(customProps: Record<string, unknown> = {}) {
  let cursor = 0, timerId = 0;
  const hooks: unknown[] = [];
  const timers = new Map<number, () => void>();
  let effects: { index: number; effect: () => void | (() => void); deps: unknown[] }[] = [];
  const listeners = new Map<string, Set<Handler>>();
  const body = {};
  const innerLink = {};
  let tree: Node;
  function descendants(value: unknown): Node[] {
    if (Array.isArray(value)) return value.flatMap(descendants);
    if (!value || typeof value !== "object" || !("props" in value)) return [];
    const node = value as Node;
    return [node, ...descendants(node.props.children)];
  }
  const find = (predicate: (node: Node) => boolean) => descendants(tree).find(predicate);
  const document = {
    body, documentElement: { clientWidth: 320 }, activeElement: null as unknown,
    addEventListener(name: string, handler: Handler) { if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name)!.add(handler); },
    removeEventListener(name: string, handler: Handler) { listeners.get(name)?.delete(handler); }
  };
  const trigger = {
    contains: (value: unknown) => value === trigger,
    getBoundingClientRect: () => ({ left: 280, top: 200, right: 300, bottom: 220, width: 20, height: 20 }),
    focus() { document.activeElement = trigger; (find(node => node.type === "button")!.props.onFocus as Handler)(); }
  };
  const tooltip = {
    contains: (value: unknown) => value === tooltip || value === innerLink,
    getBoundingClientRect: () => {
      const style = find(node => node.props.role === "tooltip")?.props.style as Record<string, number> | undefined;
      return { width: Math.min(350, style?.maxWidth || 350), height: Math.min(200, style?.maxHeight || 420) };
    }
  };
  const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props });
  const react = {
    useId() { cursor++; return "help-id"; },
    useRef(initial: unknown) { const index = cursor++; return hooks[index] ?? (hooks[index] = { current: initial }); },
    useState(initial: unknown) { const index = cursor++; if (!(index in hooks)) hooks[index] = initial; return [hooks[index], (value: unknown) => { hooks[index] = typeof value === "function" ? (value as (prior: unknown) => unknown)(hooks[index]) : value; }]; },
    useLayoutEffect(effect: () => void | (() => void), deps: unknown[]) { const index = cursor++; const old = hooks[index] as Effect | undefined; if (!old || deps.some((value, at) => !Object.is(value, old.deps[at]))) effects.push({ index, effect, deps }); }
  };
  const module = { exports: {} as Record<string, unknown> };
  vm.runInNewContext(transformSync(readFileSync(path.join(process.cwd(), "components/HelpTip.tsx"), "utf8"), { loader: "tsx", format: "cjs", jsx: "automatic", target: "es2022" }).code, {
    module, exports: module.exports,
    require(name: string) {
      if (name === "react") return react;
      if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (name === "react-dom") return { createPortal: (children: unknown, target: unknown) => ({ type: "portal", props: { children, target } }) };
      throw new Error(`Unexpected import ${name}`);
    },
    document, window: { innerWidth: 320, innerHeight: 260, addEventListener() {}, removeEventListener() {} },
    setTimeout: (callback: () => void) => { timers.set(++timerId, callback); return timerId; }, clearTimeout: (id: number) => timers.delete(id),
    requestAnimationFrame: (callback: () => void) => { timers.set(++timerId, callback); return timerId; }, cancelAnimationFrame: (id: number) => timers.delete(id),
    ResizeObserver: class { observe() {} disconnect() {} }
  });
  const component = module.exports.HelpTip as (props: { label: string; children: string }) => Node;
  function render() {
    cursor = 0; effects = [];
    tree = component({ label: "About observed prices", children: "Preserved explanatory content.", ...customProps });
    const button = find(node => node.type === "button")!;
    (button.props.ref as { current: unknown }).current = trigger;
    const content = find(node => node.props.role === "tooltip");
    if (content) (content.props.ref as { current: unknown }).current = tooltip;
    for (const { index, effect, deps } of effects) {
      (hooks[index] as Effect | undefined)?.cleanup?.();
      hooks[index] = { deps, cleanup: effect() };
    }
  }
  const fire = (where: "trigger" | "tooltip", event: string, details: unknown = {}) => {
    const node = find(node => where === "trigger" ? node.type === "button" : node.props.role === "tooltip");
    assert.ok(node); (node.props[event] as Handler)(details); render(); render();
  };
  render();
  return {
    fire, find, body, trigger, tooltip, innerLink, document,
    open: () => Boolean(find(node => node.props.role === "tooltip")),
    event(name: string, details: unknown) { for (const handler of [...(listeners.get(name) || [])]) handler(details); render(); render(); },
    flush() { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach(callback => callback()); render(); render(); },
    dispose() { for (const hook of hooks) (hook as Effect | undefined)?.cleanup?.(); },
    listenerCount: () => [...listeners.values()].reduce((sum, set) => sum + set.size, 0),
    timerCount: () => timers.size
  };
}

test("HelpTip hover is hoverable, portalled and constrained to the viewport", () => {
  const help = helpHarness();
  assert.equal(help.open(), false);
  help.fire("trigger", "onMouseEnter");
  assert.equal(help.open(), true);
  assert.equal(help.find(node => node.type === "portal")?.props.target, help.body);
  const content = help.find(node => node.props.role === "tooltip")!;
  const style = content.props.style as { left: number; top: number; maxWidth: number; maxHeight: number };
  assert.ok(style.left >= 12 && style.left + style.maxWidth <= 308);
  assert.ok(style.top >= 12 && style.top + Math.min(200, style.maxHeight) <= 248);
  assert.equal(help.find(node => node.type === "button")?.props["aria-describedby"], content.props.id);
  help.fire("trigger", "onMouseLeave");
  help.fire("tooltip", "onPointerEnter");
  help.flush();
  assert.equal(help.open(), true, "Moving from trigger to the portal keeps content readable");
  help.fire("tooltip", "onPointerLeave");
  help.flush();
  assert.equal(help.open(), false);
  help.dispose();
});

test("HelpTip focus and tap open; Escape, second tap and outside pointer close", () => {
  const help = helpHarness();
  help.document.activeElement = help.trigger;
  help.fire("trigger", "onFocus");
  help.fire("trigger", "onClick");
  assert.equal(help.open(), true, "The focus preceding a tap does not immediately close it");
  help.fire("trigger", "onClick");
  assert.equal(help.open(), false);
  help.fire("trigger", "onFocus");
  let prevented = false;
  help.event("keydown", { key: "Escape", preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(help.open(), false);
  help.fire("trigger", "onClick");
  help.event("pointerdown", { target: {} });
  assert.equal(help.open(), false);
  help.dispose();
  assert.equal(help.listenerCount(), 0);
  assert.equal(help.timerCount(), 0);
});

test("HelpTip preserves reading when focus or touch moves into portal content", () => {
  const help = helpHarness();
  help.fire("trigger", "onFocus");
  help.fire("tooltip", "onPointerEnter");
  help.fire("tooltip", "onPointerDown");
  help.fire("trigger", "onBlur", { relatedTarget: null });
  help.flush();
  assert.equal(help.open(), true, "Tapping or scrolling the portal must not dismiss it");
  help.fire("trigger", "onBlur", { relatedTarget: help.innerLink });
  help.document.activeElement = help.innerLink;
  help.flush();
  assert.equal(help.open(), true);
  help.event("keydown", { key: "Escape", preventDefault() {} });
  assert.equal(help.open(), false);
  assert.equal(help.document.activeElement, help.trigger, "Escape returns focus from portal content");
  help.fire("trigger", "onFocus");
  help.fire("trigger", "onBlur", { relatedTarget: {} });
  help.flush();
  assert.equal(help.open(), false, "Keyboard focus leaving the help dismisses it");
  help.dispose();
});

test("a family-card trigger reveals details without changing selection until clicked", () => {
  let selected = 0;
  const help = helpHarness({ triggerContent: "Composition · 20 traits", triggerClassName: "family-nav-card", pressed: true, onTriggerClick: () => selected++ });
  const trigger = help.find(node => node.type === "button")!;
  assert.equal(trigger.props.children, "Composition · 20 traits");
  assert.equal(trigger.props.className, "family-nav-card");
  assert.equal(trigger.props["aria-pressed"], true);
  help.fire("trigger", "onMouseEnter");
  help.fire("trigger", "onFocus");
  assert.equal(help.open(), true);
  assert.equal(selected, 0);
  help.fire("trigger", "onClick");
  assert.equal(selected, 1);
  assert.equal(help.open(), true);
  help.dispose();
});
