"use client";

import { memo, useEffect, useRef, useState } from "react";
import type { PointsResponse } from "../lib/contracts";
import { unitLabel } from "../lib/client/display";
import { cloudAppearance, type CloudFamily } from "../lib/client/cloud-family";
import { Icon } from "./Icons";

type PlotEvent = { points?: { customdata?: unknown }[]; [key: string]: unknown };
type PlotElement = HTMLDivElement & { on?: (event: string, handler: (event: PlotEvent) => void) => void; removeAllListeners?: () => void; };
type Plotly = {
  react: (element: HTMLElement, traces: unknown[], layout: Record<string, unknown>, config: Record<string, unknown>) => Promise<unknown>;
  restyle: (element: HTMLElement, update: Record<string, unknown>, traces: number[]) => Promise<unknown>;
  relayout: (element: HTMLElement, layout: Record<string, unknown>) => Promise<unknown>;
  purge: (element: HTMLElement) => void;
  Plots: { resize: (element: HTMLElement) => Promise<unknown> };
};
declare global { interface Window { Plotly?: Plotly; } }
let plotlyPromise: Promise<Plotly> | null = null;

export function loadPlotly() {
  if (window.Plotly) return Promise.resolve(window.Plotly);
  if (!plotlyPromise) plotlyPromise = new Promise<Plotly>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/vendor/plotly-gl3d-3.1.0.min.js";
    script.async = true;
    script.onload = () => window.Plotly ? resolve(window.Plotly) : reject(new Error("The 3D renderer was unavailable."));
    script.onerror = () => { script.remove(); plotlyPromise = null; reject(new Error("The 3D renderer could not load.")); };
    document.head.appendChild(script);
  });
  return plotlyPromise;
}

const orbitCamera = { eye: { x: 1.6, y: -1.7, z: 1.0 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: -0.05 } };
const escapeText = (value: string) => value.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);

export const PointCloud = memo(function PointCloud({ data, selectedId, onSelect, family = null }: { data: PointsResponse; selectedId: string | null; onSelect: (id: string) => void; family?: CloudFamily | null }) {
  const element = useRef<PlotElement>(null);
  const plotly = useRef<Plotly | null>(null);
  const camera = useRef<Record<string, unknown>>(structuredClone(orbitCamera));
  const busy = useRef(false);
  const ready = useRef(false);
  const dragging = useRef(false);
  const pointer = useRef<{ x: number; y: number } | null>(null);
  const dragMoved = useRef(false);
  const suppressClickUntil = useRef(0);
  const frame = useRef<number | null>(null);
  const dirty = useRef<"data" | "appearance" | "selection" | null>("data");
  const dataRef = useRef(data);
  const familyRef = useRef(family);
  const selected = useRef(selectedId);
  const select = useRef(onSelect);
  const schedule = useRef<() => void>(() => {});
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"3d" | "top">("3d");

  // Selection and camera never become dependencies of the full-cloud render.
  useEffect(() => { select.current = onSelect; }, [onSelect]);
  useEffect(() => { dataRef.current = data; dirty.current = "data"; schedule.current(); }, [data]);
  useEffect(() => {
    selected.current = selectedId;
    if (!dirty.current) dirty.current = "selection";
    schedule.current();
  }, [selectedId]);
  useEffect(() => {
    familyRef.current = family;
    if (dirty.current !== "data") dirty.current = "appearance";
    schedule.current();
  }, [family]);

  useEffect(() => {
    const node = element.current;
    if (!node) return;
    let disposed = false;
    let resizeFrame: number | null = null;
    let resizePending = false;
    let listenersInstalled = false;
    function highlight() {
      const point = dataRef.current.points.find(item => item.id === selected.current);
      return { x: [point ? [point.x] : []], y: [point ? [point.y] : []], z: [point ? [point.z] : []], customdata: [point ? [point.id] : []], text: [point ? [escapeText(point.name)] : []] };
    }
    function appearance() {
      const styles = dataRef.current.points.map(item => cloudAppearance(item, familyRef.current));
      return {
        colors: styles.map(style => style.color), symbols: styles.map(style => style.symbol),
        text: dataRef.current.points.map((item, index) => `${escapeText(item.name)}${familyRef.current ? `<br>${escapeText(familyRef.current.label)}: ${escapeText(styles[index].detail)}` : ""}`)
      };
    }
    function requestRender() {
      if (disposed || !plotly.current || busy.current || dragging.current || frame.current !== null || !dirty.current) return;
      frame.current = window.requestAnimationFrame(() => { frame.current = null; void render(); });
    }
    async function render() {
      const renderer = plotly.current;
      if (!renderer || disposed || busy.current || dragging.current || !dirty.current) return;
      const operation = dirty.current; dirty.current = null; busy.current = true;
      try {
        if (operation === "selection" && ready.current) {
          await renderer.restyle(node!, highlight(), [1]);
        } else if (operation === "appearance" && ready.current) {
          const style = appearance();
          await renderer.restyle(node!, { "marker.color": [style.colors], "marker.symbol": [style.symbols], text: [style.text] }, [0]);
          if (disposed) return;
          // A selection may have arrived alongside the family change.
          await renderer.restyle(node!, highlight(), [1]);
        } else {
          const current = dataRef.current;
          const style = appearance();
          const point = current.points.find(item => item.id === selected.current);
          const axis = (index: number) => ({
            title: { text: `${escapeText(current.axes[index].label)}${current.axes[index].unit ? ` (${escapeText(unitLabel(current.axes[index].unit))})` : ""}`, font: { size: 10, color: "#9bafbb" } },
            backgroundcolor: "#0b151b", showbackground: true, gridcolor: "#20313b", zerolinecolor: "#344b58", linecolor: "#334853", tickfont: { size: 10, color: "#8198a5" }, showspikes: false, ticks: "", nticks: 5
          });
          await renderer.react(node!, [
            { type: "scatter3d", mode: "markers", name: "Source listings", x: current.points.map(item => item.x), y: current.points.map(item => item.y), z: current.points.map(item => item.z), customdata: current.points.map(item => item.id), text: style.text, hovertemplate: "<b>%{text}</b><br>X %{x:.2f} · Y %{y:.2f} · Z %{z:.2f}<extra>Observed listing</extra>", marker: { size: 3.3, opacity: 1, color: style.colors, symbol: style.symbols, line: { width: 0 } } },
            { type: "scatter3d", mode: "markers", name: "Selected listing", x: point ? [point.x] : [], y: point ? [point.y] : [], z: point ? [point.z] : [], customdata: point ? [point.id] : [], text: point ? [escapeText(point.name)] : [], hovertemplate: "<b>%{text}</b><extra>Selected listing</extra>", marker: { size: 7, opacity: 1, color: "#f4ffe0", line: { color: "#101b22", width: 1 } } }
          ], {
            paper_bgcolor: "#0b151b", plot_bgcolor: "#0b151b", margin: { l: 0, r: 0, t: 4, b: 0 }, showlegend: false, autosize: true,
            uirevision: "observed-market-camera", hoverlabel: { bgcolor: "#e6f4ed", bordercolor: "#89e6ca", font: { family: "Arial, sans-serif", size: 12, color: "#122921" } },
            scene: { xaxis: axis(0), yaxis: axis(1), zaxis: axis(2), camera: structuredClone(camera.current), aspectmode: "cube", dragmode: "orbit", bgcolor: "#0b151b" }
          }, { displayModeBar: false, responsive: false, scrollZoom: false, plotGlPixelRatio: 1, doubleClick: false });
          if (disposed) { renderer.purge(node!); return; }
          ready.current = true;
          if (!listenersInstalled) {
            node!.on?.("plotly_relayout", event => {
              if (event["scene.camera"] && typeof event["scene.camera"] === "object") camera.current = structuredClone(event["scene.camera"] as Record<string, unknown>);
            });
            node!.on?.("plotly_click", event => {
              if (dragMoved.current || dragging.current || performance.now() < suppressClickUntil.current) return;
              const id = event.points?.[0]?.customdata;
              if (typeof id === "string") select.current(id);
            });
            node!.on?.("plotly_webglcontextlost", () => { if (!disposed) setError(true); });
            listenersInstalled = true;
          }
          setLoading(false);
        }
      } catch {
        if (!disposed) { setError(true); setLoading(false); }
      } finally {
        busy.current = false;
        if (resizePending) requestResize();
        requestRender();
      }
    }
    schedule.current = requestRender;
    const stopDrag = () => {
      if (!dragging.current) return;
      dragging.current = false;
      if (dragMoved.current) suppressClickUntil.current = performance.now() + 180;
      pointer.current = null;
      if (resizePending) requestResize();
      requestRender();
    };
    const trackDrag = (event: PointerEvent) => {
      if (pointer.current && Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) > 4) dragMoved.current = true;
    };
    window.addEventListener("pointermove", trackDrag, true);
    window.addEventListener("pointerup", stopDrag, true);
    window.addEventListener("pointercancel", stopDrag, true);
    window.addEventListener("blur", stopDrag);
    function requestResize() {
      resizePending = true;
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => {
        resizeFrame = null;
        if (!disposed && ready.current && !busy.current && !dragging.current) {
          resizePending = false;
          void plotly.current?.Plots.resize(node!).catch(() => {});
        }
      });
    }
    const resize = new ResizeObserver(requestResize);
    resize.observe(node);
    void loadPlotly().then(renderer => { if (!disposed) { plotly.current = renderer; dirty.current = "data"; requestRender(); } }).catch(() => { if (!disposed) { setError(true); setLoading(false); } });
    return () => {
      disposed = true; ready.current = false; schedule.current = () => {};
      if (frame.current !== null) window.cancelAnimationFrame(frame.current);
      frame.current = null;
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      resize.disconnect(); window.removeEventListener("pointermove", trackDrag, true); window.removeEventListener("pointerup", stopDrag, true); window.removeEventListener("pointercancel", stopDrag, true); window.removeEventListener("blur", stopDrag);
      node.removeAllListeners?.(); plotly.current?.purge(node);
    };
  }, []);

  function changeView(next: "3d" | "top") {
    const nextCamera = next === "top" ? { eye: { x: 0, y: 0, z: 2.6 }, up: { x: 0, y: 1, z: 0 }, center: { x: 0, y: 0, z: 0 } } : orbitCamera;
    camera.current = structuredClone(nextCamera); setView(next);
    if (element.current && plotly.current && ready.current) void plotly.current.relayout(element.current, { "scene.camera": camera.current }).catch(() => setError(true));
  }

  return <div className={`point-cloud-shell ${error ? "render-failed" : ""}`}>
    <div className="camera-controls" aria-label="Chart camera"><button className={view === "3d" ? "active" : ""} aria-pressed={view === "3d"} onClick={() => changeView("3d")}><Icon name="cube" size={14} />3D</button><button className={view === "top" ? "active" : ""} aria-pressed={view === "top"} onClick={() => changeView("top")}><Icon name="grid" size={14} />Top</button></div>
    <div ref={element} className="point-cloud" role="img" aria-label={`Three-dimensional observed price cloud with ${data.points.length} source listings. ${family ? `Colours and symbols show ${family.label} evidence coverage.` : "Colours show seller roles."} Use the product matrix for keyboard-accessible values.`}
      onPointerDownCapture={event => { if (event.button !== 0) return; pointer.current = { x: event.clientX, y: event.clientY }; dragMoved.current = false; dragging.current = true; }}
      onPointerMoveCapture={event => { if (pointer.current && Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) > 4) dragMoved.current = true; }} />
    {loading && !error && <div className="chart-message" role="status"><span className="loading-orbit" />Preparing the observed market…</div>}
    {error && <div className="chart-message" role="status"><Icon name="grid" size={26} /><strong>3D view is unavailable in this browser.</strong><p>All listings and evidence remain available in the trait matrix.</p><a href="#trait-matrix" className="button">Explore the matrix</a></div>}
    {!loading && !error && <p className="chart-gesture"><span className="gesture-mouse" aria-hidden="true" />Drag to orbit · click a point to inspect</p>}
  </div>;
});
