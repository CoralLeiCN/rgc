"use client";

import { memo, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { TerrainResponse } from "../lib/contracts";
import { buildTerrainGeometry, rowLayerColor, type TerrainDraftPoint, type TerrainGeometry } from "../lib/client/terrain-geometry";
import { TerrainRenderQueue } from "../lib/client/terrain-controller";
import { loadPlotly } from "../lib/client/plotly";
import { retainedBySlice, sliceTerrain, type PriceSlice } from "../lib/client/terrain-slice";
import { TerrainSliceSection, type PriceSection } from "./TerrainSlice";

type Plotly = Awaited<ReturnType<typeof loadPlotly>>;
type PlotEvent = { points?: { customdata?: unknown; curveNumber?: number; pointNumber?: number }[]; [key: string]: unknown };
type PlotElement = HTMLDivElement & { on?: (event: string, handler: (event: PlotEvent) => void) => void; removeAllListeners?: () => void };
type HoverDetails = { key: string; x: number; y: number; kind: string; title: string; values: [string, string][]; note?: string };
export const terrainCamera = { eye: { x: -1.65, y: -1.7, z: 1.25 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: -.08 } };
const escapeText = (value: string) => value.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);

export const TerrainViewport = memo(function TerrainViewport({ data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap = null, slice = null }: {
  data: TerrainResponse; smoothness: number; highlightedLayer: string | null; selectedId: string | null; onSelect: (id: string) => void;
  draft: TerrainDraftPoint | null; onUnavailable: () => void; gap?: { lower: number; upper: number } | null; slice?: PriceSlice | null;
}) {
  const element = useRef<PlotElement>(null); const queue = useRef<TerrainRenderQueue | null>(null);
  const latest = useRef({ data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap, slice });
  latest.current = { data, smoothness, highlightedLayer, selectedId, onSelect, draft, onUnavailable, gap, slice };
  const camera = useRef<Record<string, unknown>>(structuredClone(terrainCamera));
  const pointer = useRef<{ x: number; y: number; moved: boolean } | null>(null); const suppressClickUntil = useRef(0);
  const hoverPosition = useRef<{ x: number; y: number } | null>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<HoverDetails | null>(null);
  const [section, setSection] = useState<PriceSection | null>(null);
  const [surfaceVisible, setSurfaceVisible] = useState(true);
  const [loading, setLoading] = useState(true); const [supportedCells, setSupportedCells] = useState<number | null>(null);
  useLayoutEffect(() => {
    if (!hover || !tooltip.current || !element.current) return;
    const bounds = element.current;
    tooltip.current.style.left = `${Math.max(10, Math.min(hover.x + 14, bounds.clientWidth - tooltip.current.offsetWidth - 10))}px`;
    tooltip.current.style.top = `${Math.max(10, Math.min(hover.y + 14, bounds.clientHeight - tooltip.current.offsetHeight - 10))}px`;
  }, [hover]);
  useEffect(() => { queue.current?.invalidate("geometry"); }, [data, smoothness]);
  useEffect(() => { queue.current?.invalidate("slice"); }, [slice]);
  useEffect(() => { queue.current?.invalidate("draft"); }, [draft]);
  useEffect(() => { queue.current?.invalidate("selection"); }, [selectedId]);
  useEffect(() => { queue.current?.invalidate("appearance"); }, [highlightedLayer]);
  useEffect(() => { queue.current?.invalidate("gap"); }, [gap]);

  useEffect(() => {
    const node = element.current; if (!node) return;
    let disposed = false, ready = false, installed = false; let renderer: Plotly | null = null; let geometry: TerrainGeometry | null = null; let fullGeometry: TerrainGeometry | null = null;
    const pointUpdate = (kind: "selection" | "draft") => {
      const current = latest.current;
      const candidate = kind === "draft" ? current.draft : current.data.rows.find(row => row.id === current.selectedId);
      const point = candidate && retainedBySlice(candidate.price, current.slice) ? candidate : null;
      return { x: [point ? [point.price] : []], y: [point ? [point.score] : []], z: [point ? [point.z] : []], text: [point ? [escapeText(point.name)] : []], customdata: [point && "id" in point ? [point.id] : []] };
    };
    const layerColors = () => geometry!.meshes.map(({ layer }) => !latest.current.highlightedLayer || latest.current.highlightedLayer === layer.key ? layer.color : "#3b535d");
    const axisRanges = () => {
      const current = latest.current;
      return {
        x: [Math.min(fullGeometry!.xDomain[0], current.draft?.price ?? Infinity), Math.max(fullGeometry!.xDomain[1], current.draft?.price ?? -Infinity)],
        z: [Math.min(fullGeometry!.baseline, current.draft?.z ?? Infinity), Math.max(fullGeometry!.baseline + 1, ...current.data.rows.map(row => row.z), current.draft?.z ?? -Infinity)],
      };
    };
    const gapUpdate = () => {
      const current = latest.current, selectedGap = current.gap;
      const lower = selectedGap ? Math.max(selectedGap.lower, current.slice?.keep === "higher" ? current.slice.price : -Infinity) : 0;
      const upper = selectedGap ? Math.min(selectedGap.upper, current.slice?.keep === "lower" ? current.slice.price : Infinity) : 0;
      const value = selectedGap && upper >= lower ? { lower, upper } : null;
      return { x: [value ? [value.lower, value.upper, value.upper, value.lower, value.lower] : []], y: [value ? [0, 0, 100, 100, 0] : []], z: [value ? Array(5).fill(geometry!.baseline) : []] };
    };
    const controller = new TerrainRenderQueue(async operation => {
      if (!renderer || disposed) return;
      if (operation === "geometry" || operation === "slice" || !ready) {
        setHover(null);
        const current = latest.current;
        // Geometry is computed inside the serialized queue, only after pointer dragging has ended.
        if (operation === "geometry" || !fullGeometry) fullGeometry = buildTerrainGeometry(current.data, { resolution: 24, smoothness: current.smoothness });
        const sliced = sliceTerrain(fullGeometry, current.slice);
        geometry = { ...fullGeometry, meshes: sliced.meshes.filter(mesh => mesh.i.length > 0) };
        const rows = current.data.rows.filter(row => retainedBySlice(row.price, current.slice));
        const sectionData = current.slice ? { price: current.slice.price, bands: sliced.bands, baseline: geometry.baseline, ceiling: Math.max(...current.data.rows.map(row => row.z)), label: current.data.z.label, unit: current.data.z.unit } : null;
        const colors = layerColors(); const selected = pointUpdate("selection"), configured = pointUpdate("draft");
        const unit = current.data.z.unit ? ` ${escapeText(current.data.z.unit)}` : "";
        const meshes = geometry.meshes.map((mesh, index) => ({
          type: "mesh3d", name: mesh.layer.label, x: mesh.x, y: mesh.y, z: mesh.z, i: mesh.i, j: mesh.j, k: mesh.k,
          color: colors[index], opacity: 1, flatshading: false, lighting: { ambient: .72, diffuse: .75, specular: .12, roughness: .9, fresnel: .1 }, lightposition: { x: -1000, y: -800, z: 1800 },
          hoverinfo: "none"
        }));
        const markerTrace = (name: string, values: ReturnType<typeof pointUpdate>, color: string, symbol: string, size: number) => ({
          type: "scatter3d", mode: "markers", name, x: values.x[0], y: values.y[0], z: values.z[0], text: values.text[0], customdata: values.customdata[0],
          marker: { color, size, symbol, opacity: 1, line: { color: "#10272b", width: 1 } }, hoverinfo: "none"
        });
        const axis = (title: string) => ({ title: { text: title, font: { size: 11, color: "#b4cfc9" } }, backgroundcolor: "#0a191d", showbackground: true, gridcolor: "#253b42", zerolinecolor: "#547378", tickfont: { color: "#9cb7b8", size: 10 }, showspikes: false, nticks: 5 });
        const ranges = axisRanges();
        await renderer.react(node, [
          ...meshes,
          { type: "scatter3d", mode: "markers", name: "Observed products", x: rows.map(row => row.price), y: rows.map(row => row.score), z: rows.map(row => row.z), customdata: rows.map(row => row.id), text: rows.map(row => escapeText(row.name)), marker: { size: 2.8, opacity: 1, color: rows.map(row => rowLayerColor(row, geometry!.layers)), line: { color: "#d8f3e8", width: .5 } }, hoverinfo: "none" },
          markerTrace("Selected product", selected, "#f8ffe8", "circle", 6),
          markerTrace("Your product · demo score", configured, "#eaff75", "diamond", 8),
          { type: "scatter3d", mode: "lines", name: "Selected observed price gap", x: gapUpdate().x[0], y: gapUpdate().y[0], z: gapUpdate().z[0], line: { color: "#f5d690", width: 5 }, hoverinfo: "none" }
        ], {
          paper_bgcolor: "#0a191d", margin: { l: 0, r: 0, t: 0, b: 0 }, autosize: true, showlegend: false, uirevision: "trait-terrain-camera-v1",
          scene: { xaxis: { ...axis("PRICE · £ / 100g"), range: ranges.x }, yaxis: { ...axis("TRAIT SCORE · DEMO"), range: [0, 100] }, zaxis: { ...axis(`${escapeText(current.data.z.label)}${unit}`), range: ranges.z }, camera: structuredClone(camera.current), aspectmode: "manual", aspectratio: { x: 1.25, y: 1.1, z: .8 }, dragmode: "orbit", bgcolor: "#0a191d", hovermode: false }
        }, { displayModeBar: false, responsive: false, scrollZoom: false, plotGlPixelRatio: 1, doubleClick: false });
        if (disposed) { renderer.purge(node); return; }
        ready = true; setLoading(false); setSupportedCells(geometry.cells.length); setSurfaceVisible(geometry.meshes.length > 0); setSection(sectionData);
        if (!installed) {
          node.on?.("plotly_relayout", event => {
            setHover(null);
            if (event["scene.camera"] && typeof event["scene.camera"] === "object") camera.current = structuredClone(event["scene.camera"] as Record<string, unknown>);
          });
          node.on?.("plotly_hover", event => {
            const point = event.points?.[0], position = hoverPosition.current, current = latest.current;
            if (!point || !position || pointer.current || !geometry) return;
            const curve = point.curveNumber, index = point.pointNumber;
            if (typeof curve !== "number" || typeof index !== "number") return;
            const unit = current.data.z.unit ? ` ${current.data.z.unit}` : "";
            let details: Omit<HoverDetails, "key" | "x" | "y"> | null = null;
            const row = typeof point.customdata === "string" ? current.data.rows.find(row => row.id === point.customdata) : null;
            const isDraft = curve === geometry.meshes.length + 2;
            const product = isDraft ? current.draft : row;
            if (product) {
              details = { kind: isDraft ? "Your proposed product" : "Observed product", title: product.name, values: [
                [isDraft ? "Proposed price" : "Observed price", `£${product.price.toFixed(2)} / 100 g`],
                ["Trait score · demo", product.score.toFixed(1)],
                [current.data.z.label, `${product.z.toFixed(2)}${unit}`],
              ] };
            } else if (curve < geometry.meshes.length) {
              const mesh = geometry.meshes[curve];
              if (index >= 0 && index < mesh.shares.length) details = { kind: "Terrain layer", title: mesh.layer.label, values: [
                ["Local category share", `${(mesh.shares[index] * 100).toFixed(1)}%`],
                ["Layer thickness", `${mesh.thickness[index].toFixed(2)}${unit}`],
                ["Price coordinate", `£${mesh.x[index].toFixed(2)} / 100 g`],
                ["Trait score · demo", mesh.y[index].toFixed(1)],
              ], note: "Smoothed composition; thickness does not measure a pricing effect." };
            } else if (curve === geometry.meshes.length + 3 && current.gap) {
              details = { kind: "Observed price gap", title: "Empty observed price band", values: [
                ["Price range", `£${current.gap.lower.toFixed(2)}–£${current.gap.upper.toFixed(2)} / 100 g`],
              ] };
            }
            if (!details) { setHover(null); return; }
            const key = `${curve}:${index}`;
            setHover(previous => previous?.key === key && previous.x === position.x && previous.y === position.y ? previous : { ...details, ...position, key });
          });
          node.on?.("plotly_unhover", () => setHover(null));
          node.on?.("plotly_click", event => {
            if (pointer.current?.moved || performance.now() < suppressClickUntil.current) return;
            const id = event.points?.[0]?.customdata;
            if (typeof id === "string") latest.current.onSelect(id);
          });
          node.on?.("plotly_webglcontextlost", () => latest.current.onUnavailable()); installed = true;
        }
      } else if (operation === "camera") { setHover(null); await renderer.relayout(node, { "scene.camera": structuredClone(camera.current) }); }
      else if (operation === "selection") { setHover(null); await renderer.restyle(node, pointUpdate("selection"), [geometry!.meshes.length + 1]); }
      else if (operation === "draft") { setHover(null); await renderer.restyle(node, pointUpdate("draft"), [geometry!.meshes.length + 2]); const ranges = axisRanges(); await renderer.relayout(node, { "scene.xaxis.range": ranges.x, "scene.zaxis.range": ranges.z }); }
      else if (operation === "gap") { setHover(null); await renderer.restyle(node, gapUpdate(), [geometry!.meshes.length + 3]); }
      else if (operation === "appearance" && geometry!.meshes.length) await renderer.restyle(node, { color: layerColors() }, geometry!.meshes.map((_, i) => i));
      else if (operation === "resize") { setHover(null); await renderer.Plots.resize(node); }
    }, callback => window.requestAnimationFrame(callback), id => window.cancelAnimationFrame(id), () => { if (!disposed) latest.current.onUnavailable(); });
    queue.current = controller;
    const stopDrag = () => { if (pointer.current?.moved) suppressClickUntil.current = performance.now() + 200; pointer.current = null; controller.setDragging(false); };
    const trackDrag = (event: PointerEvent) => { if (pointer.current && Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) > 4) pointer.current.moved = true; };
    window.addEventListener("pointermove", trackDrag, true); window.addEventListener("pointerup", stopDrag, true); window.addEventListener("pointercancel", stopDrag, true); window.addEventListener("blur", stopDrag);
    const resize = new ResizeObserver(() => controller.invalidate("resize")); resize.observe(node);
    void loadPlotly().then(value => { if (!disposed) { renderer = value; controller.invalidate("geometry"); } }).catch(() => { if (!disposed) latest.current.onUnavailable(); });
    return () => { disposed = true; controller.dispose(); queue.current = null; resize.disconnect(); window.removeEventListener("pointermove", trackDrag, true); window.removeEventListener("pointerup", stopDrag, true); window.removeEventListener("pointercancel", stopDrag, true); window.removeEventListener("blur", stopDrag); node.removeAllListeners?.(); renderer?.purge(node); };
  }, []);
  return <><div className="terrain-viewport-shell">
    <div className="terrain-camera-controls">{slice && <button type="button" onClick={() => { camera.current = { eye: { x: slice.keep === "higher" ? -2.5 : 2.5, y: 0, z: 0 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } }; queue.current?.invalidate("camera"); }}>Face slice</button>}<button type="button" onClick={() => { camera.current = structuredClone(terrainCamera); queue.current?.invalidate("camera"); }}>Reset camera</button><button type="button" onClick={() => { camera.current = { eye: { x: 0, y: 0, z: 2.7 }, up: { x: 0, y: 1, z: 0 }, center: { x: 0, y: 0, z: 0 } }; queue.current?.invalidate("camera"); }}>Top view</button></div>
    <div ref={element} className="terrain-viewport" role="img" aria-label={`Layered terrain with ${data.rows.filter(row => retainedBySlice(row.price, slice)).length} exact product points${slice ? `, cut at £${slice.price.toFixed(2)} per 100 g` : ""}. Horizontal axes are observed price and demo trait score. Height is ${data.z.label}. Use 2D projection for keyboard-accessible points.`}
      onPointerMove={event => { const bounds = event.currentTarget.getBoundingClientRect(); hoverPosition.current = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }; }}
      onPointerLeave={() => { hoverPosition.current = null; setHover(null); }}
      onPointerDownCapture={event => { if (event.button !== 0) return; setHover(null); pointer.current = { x: event.clientX, y: event.clientY, moved: false }; queue.current?.setDragging(true); }} />
    {hover && <div ref={tooltip} className="terrain-hover" role="tooltip"><span className="terrain-hover-kind">{hover.kind}</span><strong>{hover.title}</strong><dl>{hover.values.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>{hover.note && <p>{hover.note}</p>}</div>}
    {loading && <div className="terrain-render-status" role="status"><span className="loading-orbit" />Building the trait landscape…</div>}
    {!loading && <p className="terrain-gesture">Drag to orbit · click a product · layers show local composition{!surfaceVisible && slice ? " · No cake remains on this side of the cut" : supportedCells === 0 ? " · Too little nearby evidence to join a surface" : ""}</p>}
  </div>{slice && section && section.price === slice.price && <TerrainSliceSection section={section} />}</>;
});
