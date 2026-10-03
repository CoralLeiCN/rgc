"use client";

import { memo, useEffect, useRef, useState } from "react";
import type { TerrainResponse } from "../lib/contracts";
import { buildTerrainGeometry, rowLayerColor, type TerrainDraftPoint, type TerrainGeometry } from "../lib/client/terrain-geometry";
import { TerrainRenderQueue } from "../lib/client/terrain-controller";
import { loadPlotly } from "./PointCloud";

type Plotly = Awaited<ReturnType<typeof loadPlotly>>;
type PlotEvent = { points?: { customdata?: unknown }[]; [key: string]: unknown };
type PlotElement = HTMLDivElement & { on?: (event: string, handler: (event: PlotEvent) => void) => void; removeAllListeners?: () => void };
export const terrainCamera = { eye: { x: -1.65, y: -1.7, z: 1.25 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: -.08 } };
const escapeText = (value: string) => value.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);

export const TerrainViewport = memo(function TerrainViewport({ data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap = null }: {
  data: TerrainResponse; smoothness: number; highlightedLayer: string | null; selectedId: string | null; onSelect: (id: string) => void;
  draft: TerrainDraftPoint | null; onUnavailable: () => void; gap?: { lower: number; upper: number } | null;
}) {
  const element = useRef<PlotElement>(null); const queue = useRef<TerrainRenderQueue | null>(null);
  const latest = useRef({ data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap });
  latest.current = { data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap };
  const camera = useRef<Record<string, unknown>>(structuredClone(terrainCamera));
  const pointer = useRef<{ x: number; y: number; moved: boolean } | null>(null); const suppressClickUntil = useRef(0);
  const [loading, setLoading] = useState(true); const [supportedCells, setSupportedCells] = useState<number | null>(null);
  useEffect(() => { queue.current?.invalidate("geometry"); }, [data, smoothness]);
  useEffect(() => { queue.current?.invalidate("draft"); }, [draft]);
  useEffect(() => { queue.current?.invalidate("selection"); }, [selectedId]);
  useEffect(() => { queue.current?.invalidate("appearance"); }, [highlightedLayer]);
  useEffect(() => { queue.current?.invalidate("gap"); }, [gap]);

  useEffect(() => {
    const node = element.current; if (!node) return;
    let disposed = false, ready = false, installed = false; let renderer: Plotly | null = null; let geometry: TerrainGeometry | null = null;
    const pointUpdate = (kind: "selection" | "draft") => {
      const current = latest.current;
      const point = kind === "draft" ? current.draft : current.data.rows.find(row => row.id === current.selectedId);
      return { x: [point ? [point.price] : []], y: [point ? [point.score] : []], z: [point ? [point.z] : []], text: [point ? [escapeText(point.name)] : []], customdata: [point && "id" in point ? [point.id] : []] };
    };
    const layerColors = () => geometry!.meshes.map(({ layer }) => !latest.current.highlightedLayer || latest.current.highlightedLayer === layer.key ? layer.color : "#3b535d");
    const gapUpdate = () => {
      const value = latest.current.gap;
      return { x: [value ? [value.lower, value.upper, value.upper, value.lower, value.lower] : []], y: [value ? [0, 0, 100, 100, 0] : []], z: [value ? Array(5).fill(geometry!.baseline) : []] };
    };
    const controller = new TerrainRenderQueue(async operation => {
      if (!renderer || disposed) return;
      if (operation === "geometry" || !ready) {
        const current = latest.current;
        // Geometry is computed inside the serialized queue, only after pointer dragging has ended.
        geometry = buildTerrainGeometry(current.data, { resolution: 24, smoothness: current.smoothness });
        geometry.meshes = geometry.meshes.filter(mesh => mesh.i.length > 0);
        const colors = layerColors(); const selected = pointUpdate("selection"), configured = pointUpdate("draft");
        const unit = current.data.z.unit ? ` ${escapeText(current.data.z.unit)}` : "";
        const meshes = geometry.meshes.map((mesh, index) => ({
          type: "mesh3d", name: mesh.layer.label, x: mesh.x, y: mesh.y, z: mesh.z, i: mesh.i, j: mesh.j, k: mesh.k,
          color: colors[index], opacity: 1, flatshading: false, lighting: { ambient: .72, diffuse: .75, specular: .12, roughness: .9, fresnel: .1 }, lightposition: { x: -1000, y: -800, z: 1800 },
          text: mesh.shares.map((share, i) => `<b>${escapeText(mesh.layer.label)}</b><br>Local category share ${(share * 100).toFixed(1)}%<br>Layer thickness ${mesh.thickness[i].toFixed(2)}${unit}`),
          hovertemplate: "%{text}<br>Price £%{x:.2f}/100g · score %{y:.1f}<extra>Smoothed composition · not a pricing effect</extra>"
        }));
        const markerTrace = (name: string, values: ReturnType<typeof pointUpdate>, color: string, symbol: string, size: number) => ({
          type: "scatter3d", mode: "markers", name, x: values.x[0], y: values.y[0], z: values.z[0], text: values.text[0], customdata: values.customdata[0],
          marker: { color, size, symbol, opacity: 1, line: { color: "#10272b", width: 1 } }, hovertemplate: `<b>%{text}</b><br>Price £%{x:.2f}/100g<br>Trait score %{y:.1f}<br>${escapeText(current.data.z.label)} %{z:.2f}${unit}<extra>${name}</extra>`
        });
        const axis = (title: string) => ({ title: { text: title, font: { size: 11, color: "#b4cfc9" } }, backgroundcolor: "#0a191d", showbackground: true, gridcolor: "#253b42", zerolinecolor: "#547378", tickfont: { color: "#9cb7b8", size: 10 }, showspikes: false, nticks: 5 });
        await renderer.react(node, [
          ...meshes,
          { type: "scatter3d", mode: "markers", name: "Observed products", x: current.data.rows.map(row => row.price), y: current.data.rows.map(row => row.score), z: current.data.rows.map(row => row.z), customdata: current.data.rows.map(row => row.id), text: current.data.rows.map(row => escapeText(row.name)), marker: { size: 2.8, opacity: 1, color: current.data.rows.map(row => rowLayerColor(row, geometry!.layers)), line: { color: "#d8f3e8", width: .5 } }, hovertemplate: `<b>%{text}</b><br>Observed price £%{x:.2f}/100g<br>Trait score %{y:.1f}<br>${escapeText(current.data.z.label)} %{z:.2f}${unit}<extra>Exact product coordinates</extra>` },
          markerTrace("Selected product", selected, "#f8ffe8", "circle", 6),
          markerTrace("Your product · demo score", configured, "#eaff75", "diamond", 8),
          { type: "scatter3d", mode: "lines", name: "Selected observed price gap", x: gapUpdate().x[0], y: gapUpdate().y[0], z: gapUpdate().z[0], line: { color: "#f5d690", width: 5 }, hovertemplate: "Selected observed price gap<br>£%{x:.2f}/100g<extra>Empty observed price band</extra>" }
        ], {
          paper_bgcolor: "#0a191d", margin: { l: 0, r: 0, t: 0, b: 0 }, autosize: true, showlegend: false, uirevision: "trait-terrain-camera-v1",
          hoverlabel: { bgcolor: "#e6f4ed", bordercolor: "#a5e8cf", font: { family: "Arial, sans-serif", size: 12, color: "#142d28" } },
          scene: { xaxis: axis("PRICE · £ / 100g"), yaxis: { ...axis("TRAIT SCORE · DEMO"), range: [0, 100] }, zaxis: axis(`${escapeText(current.data.z.label)}${unit}`), camera: structuredClone(camera.current), aspectmode: "manual", aspectratio: { x: 1.25, y: 1.1, z: .8 }, dragmode: "orbit", bgcolor: "#0a191d" }
        }, { displayModeBar: false, responsive: false, scrollZoom: false, plotGlPixelRatio: 1, doubleClick: false });
        if (disposed) { renderer.purge(node); return; }
        ready = true; setLoading(false); setSupportedCells(geometry.cells.length);
        if (!installed) {
          node.on?.("plotly_relayout", event => {
            if (event["scene.camera"] && typeof event["scene.camera"] === "object") camera.current = structuredClone(event["scene.camera"] as Record<string, unknown>);
          });
          node.on?.("plotly_click", event => {
            if (pointer.current?.moved || performance.now() < suppressClickUntil.current) return;
            const id = event.points?.[0]?.customdata;
            if (typeof id === "string") latest.current.onSelect(id);
          });
          node.on?.("plotly_webglcontextlost", () => latest.current.onUnavailable()); installed = true;
        }
      } else if (operation === "camera") await renderer.relayout(node, { "scene.camera": structuredClone(camera.current) });
      else if (operation === "selection") await renderer.restyle(node, pointUpdate("selection"), [geometry!.meshes.length + 1]);
      else if (operation === "draft") await renderer.restyle(node, pointUpdate("draft"), [geometry!.meshes.length + 2]);
      else if (operation === "gap") await renderer.restyle(node, gapUpdate(), [geometry!.meshes.length + 3]);
      else if (operation === "appearance" && geometry!.meshes.length) await renderer.restyle(node, { color: layerColors() }, geometry!.meshes.map((_, i) => i));
      else if (operation === "resize") await renderer.Plots.resize(node);
    }, callback => window.requestAnimationFrame(callback), id => window.cancelAnimationFrame(id), () => { if (!disposed) latest.current.onUnavailable(); });
    queue.current = controller;
    const stopDrag = () => { if (pointer.current?.moved) suppressClickUntil.current = performance.now() + 200; pointer.current = null; controller.setDragging(false); };
    const trackDrag = (event: PointerEvent) => { if (pointer.current && Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) > 4) pointer.current.moved = true; };
    window.addEventListener("pointermove", trackDrag, true); window.addEventListener("pointerup", stopDrag, true); window.addEventListener("pointercancel", stopDrag, true); window.addEventListener("blur", stopDrag);
    const resize = new ResizeObserver(() => controller.invalidate("resize")); resize.observe(node);
    void loadPlotly().then(value => { if (!disposed) { renderer = value; controller.invalidate("geometry"); } }).catch(() => { if (!disposed) latest.current.onUnavailable(); });
    return () => { disposed = true; controller.dispose(); queue.current = null; resize.disconnect(); window.removeEventListener("pointermove", trackDrag, true); window.removeEventListener("pointerup", stopDrag, true); window.removeEventListener("pointercancel", stopDrag, true); window.removeEventListener("blur", stopDrag); node.removeAllListeners?.(); renderer?.purge(node); };
  }, []);
  return <div className="terrain-viewport-shell">
    <div className="terrain-camera-controls"><button type="button" onClick={() => { camera.current = structuredClone(terrainCamera); queue.current?.invalidate("camera"); }}>Reset camera</button><button type="button" onClick={() => { camera.current = { eye: { x: 0, y: 0, z: 2.7 }, up: { x: 0, y: 1, z: 0 }, center: { x: 0, y: 0, z: 0 } }; queue.current?.invalidate("camera"); }}>Top view</button></div>
    <div ref={element} className="terrain-viewport" role="img" aria-label={`Layered terrain with ${data.rows.length} exact product points. Horizontal axes are observed price and demo trait score. Height is ${data.z.label}. Use 2D projection for keyboard-accessible points.`} onPointerDownCapture={event => { if (event.button !== 0) return; pointer.current = { x: event.clientX, y: event.clientY, moved: false }; queue.current?.setDragging(true); }} />
    {loading && <div className="terrain-render-status" role="status"><span className="loading-orbit" />Building the trait landscape…</div>}
    {!loading && <p className="terrain-gesture">Drag to orbit · click a product · layers show local composition{supportedCells === 0 ? " · Too little nearby evidence to join a surface" : ""}</p>}
  </div>;
});
