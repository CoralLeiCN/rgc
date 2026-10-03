"use client";

import { useCallback, useMemo, useState } from "react";
import type { FieldDefinition, SchemaResponse, TerrainResponse } from "../lib/contracts";
import { projectTerrainDraft, rowLayerColor, terrainLayers, type ConfiguredTerrainProduct, type TerrainDraftPoint, type TerrainLayer } from "../lib/client/terrain-geometry";
import { familyLabel } from "../lib/client/families";
import { money, number } from "../lib/client/display";
import { TerrainViewport } from "./TerrainViewport";
import { HelpTip } from "./HelpTip";

type Gap = { lower: number; upper: number } | null;
export interface TerrainExplorerProps {
  schema: SchemaResponse; data: TerrainResponse | null; loading: boolean; error: string | null; onRetry: () => void;
  color: string; z: string; onColor: (key: string) => void; onZ: (key: string) => void;
  range: "core" | "full"; onRange: (range: "core" | "full") => void;
  selectedId: string | null; onSelect: (id: string) => void; configuredProduct?: ConfiguredTerrainProduct | null; gap?: Gap;
}
const categorical = (field: FieldDefinition) => ["enum", "boolean", "string_list"].includes(field.type);
function DimensionOptions({ fields, numeric }: { fields: FieldDefinition[]; numeric: boolean }) {
  const groups = [...new Set(fields.map(field => field.group))];
  return <>{groups.map(group => {
    const members = fields.filter(field => field.group === group && (numeric ? field.numeric : field.numeric || categorical(field)));
    return members.length ? <optgroup key={group} label={familyLabel(group)}>{members.map(field => <option key={field.key} value={field.key}>{field.label}{field.unit ? ` (${field.unit})` : ""}</option>)}</optgroup> : null;
  })}</>;
}
function expandedDomain(values: number[]): [number, number] {
  const min = Math.min(...values), max = Math.max(...values), padding = Math.max((max - min) * .07, Math.abs(max) * .02, .1);
  return [min - padding, max + padding];
}
function TerrainProjection({ data, draft, layers, selectedId, onSelect, gap }: { data: TerrainResponse; draft: TerrainDraftPoint | null; layers: TerrainLayer[]; selectedId: string | null; onSelect: (id: string) => void; gap: Gap }) {
  const colours = useMemo(() => new Map(data.rows.map(row => [row.id, rowLayerColor(row, layers)])), [data, layers]);
  const prices = data.rows.map(row => row.price); if (draft) prices.push(draft.price); if (gap) prices.push(gap.lower, gap.upper);
  const xs = expandedDomain(prices.length ? prices : [0, 1]); const zs = expandedDomain([...data.rows.map(row => row.z), ...(draft ? [draft.z] : []), 0]);
  const x = (value: number) => 55 + (value - xs[0]) / (xs[1] - xs[0]) * 485;
  const y = (value: number, axis: "score" | "z") => { const d = axis === "score" ? [0, 100] : zs; return 268 - (value - d[0]) / (d[1] - d[0]) * 235; };
  const selected = data.rows.find(row => row.id === selectedId);
  return <div className="terrain-projection">
    <div className="terrain-projection-charts">{(["score", "z"] as const).map(axis => <svg key={axis} viewBox="0 0 575 315" role="img" aria-label={`Exact product projection: price against ${axis === "score" ? "demo trait score" : data.z.label}`}>
      <text x="55" y="18" className="terrain-svg-title">{axis === "score" ? "TRAIT SCORE · DEMO" : data.z.label.toUpperCase()}</text>
      {gap && <rect x={x(gap.lower)} y={33} width={x(gap.upper) - x(gap.lower)} height={235} className="terrain-gap-band" />}
      {[0, .25, .5, .75, 1].map(t => <g key={t}><line x1="55" x2="540" y1={268 - t * 235} y2={268 - t * 235} className="terrain-svg-grid" /><text x="47" y={272 - t * 235} textAnchor="end" className="terrain-svg-tick">{(axis === "score" ? t * 100 : zs[0] + t * (zs[1] - zs[0])).toFixed(1)}</text><text x={55 + t * 485} y="290" textAnchor="middle" className="terrain-svg-tick">£{(xs[0] + t * (xs[1] - xs[0])).toFixed(2)}</text></g>)}
      {data.rows.map(row => <circle key={row.id} cx={x(row.price)} cy={y(row[axis], axis)} r={row.id === selectedId ? 5 : 2.8} fill={row.id === selectedId ? "#f5ffe3" : colours.get(row.id)} stroke={row.id === selectedId ? "#e8fd90" : "none"} onClick={() => onSelect(row.id)}><title>{row.name}: £{row.price.toFixed(2)}/100g, trait score {row.score.toFixed(1)}, {data.z.label} {row.z.toFixed(2)}</title></circle>)}
      {draft && <g transform={`translate(${x(draft.price)},${y(draft[axis], axis)})`}><path d="M0 -7L7 0L0 7L-7 0Z" fill="#eaff75" stroke="#0d2827" /><title>{draft.name}: your product, exact configured coordinates</title></g>}
      <text x="298" y="312" textAnchor="middle" className="terrain-svg-title">PRICE · £ / 100g</text>
    </svg>)}</div>
    <label className="terrain-point-picker">Inspect a product<select value={selectedId && selected ? selectedId : ""} onChange={event => { if (event.target.value) onSelect(event.target.value); }}><option value="">Choose an observed product</option>{data.rows.map(row => <option value={row.id} key={row.id}>{row.name} · {money(row.price)}/100g · score {row.score.toFixed(1)}</option>)}</select></label>
    {selected && <dl className="terrain-selected-values"><div><dt>Observed price</dt><dd>{money(selected.price)} /100g</dd></div><div><dt>Trait score · demo</dt><dd>{selected.score.toFixed(2)}</dd></div><div><dt>{data.z.label}</dt><dd>{selected.z.toFixed(2)} {data.z.unit}</dd></div></dl>}
  </div>;
}

export function TerrainExplorer({ schema, data, loading, error, onRetry, color, z, onColor, onZ, range, onRange, selectedId, onSelect, configuredProduct, gap = null }: TerrainExplorerProps) {
  const [view, setView] = useState<"3d" | "2d">("3d"); const [unavailable, setUnavailable] = useState(false);
  const [smoothness, setSmoothness] = useState(.5); const [highlight, setHighlight] = useState<string | null>(null);
  const layers = useMemo(() => data ? terrainLayers(data) : [], [data]);
  const draft = useMemo(() => data ? projectTerrainDraft(configuredProduct, data) : null, [configuredProduct, data]);
  const fail = useCallback(() => { setUnavailable(true); setView("2d"); }, []);
  const outOfRange = draft && data?.priceRange && (draft.price < data.priceRange[0] || draft.price > data.priceRange[1]);
  const validHighlight = layers.some(layer => layer.key === highlight) ? highlight : null;
  return <section className="landscape-section terrain-explorer" id="price-landscape" aria-labelledby="terrain-title">
    <div className="section-heading"><div><p className="eyebrow"><span className="section-index">01</span> THE PRICING LANDSCAPE</p><div className="heading-with-help"><h2 id="terrain-title">Every layer tells a story.</h2><HelpTip label="About the pricing terrain"><p>X is observed price per 100g, Y is a reproducible trait-derived demo score, and height is one selected numeric trait in its original units. These scores are illustrative, not fitted pricing predictions.</p><p>The smooth surface averages nearby numeric values with positive local weights. Unsupported areas stay open. Colours divide height above an explicit baseline using nearby category shares; layer thickness is not a causal price contribution. Numeric colour traits use five bands calibrated to the full snapshot.</p><p>Exact product dots remain at their original coordinates. Up to eight named colour layers and Other categories are shown. Unknown, conflicting and not-applicable evidence have explicit colours. Layers are ordered by their weighted median numeric value.</p>{data && <p>{data.scoreDefinition}</p>}</HelpTip></div></div><span className="tag demo-score-badge">TRAIT SCORE · DEMO</span></div>
    <div className="terrain-dimensions"><label>COLOUR LAYERS<select value={color} onChange={event => { setHighlight(null); onColor(event.target.value); }}><DimensionOptions fields={schema.fields} numeric={false} /></select></label><span className="terrain-dimension-link" aria-hidden="true">×</span><label>HEIGHT · Z<select value={z} onChange={event => onZ(event.target.value)}><DimensionOptions fields={schema.fields} numeric /></select></label><div className="terrain-view-switch" role="group" aria-label="Terrain display"><button type="button" aria-pressed={view === "3d"} onClick={() => { setUnavailable(false); setView("3d"); }}>3D terrain</button><button type="button" aria-pressed={view === "2d"} onClick={() => setView("2d")}>2D projection</button></div></div>
    <div className="terrain-toolbar"><div role="group" aria-label="Terrain price range"><button type="button" aria-pressed={range === "core"} onClick={() => onRange("core")}>Core range</button><button type="button" aria-pressed={range === "full"} onClick={() => onRange("full")}>Full range</button><HelpTip label="About terrain price ranges"><p>Core uses the observed cohort’s interquartile fences; Full uses all its observed prices. Missing trait scores or height values remain excluded from the terrain and available in the matrix. A configured product can extend the display axes without changing the observed cohort or its price range.</p>{data?.rangeFallbackReason && <p>{data.rangeFallbackReason}</p>}</HelpTip></div><label className="terrain-smoothness">Surface smoothing<input type="range" min="0" max="1" step=".05" value={smoothness} onChange={event => setSmoothness(Number(event.target.value))} disabled={view === "2d"} /><span>{Math.round(smoothness * 100)}%</span></label></div>
    {error ? <div className="empty-state" role="alert"><h3>The landscape could not load.</h3><p>{error}</p><button type="button" className="button" onClick={onRetry}>Try again</button></div> : data ? <>
      {loading && <div className="terrain-update-status" role="status">Updating the selected cohort…</div>}
      {unavailable && <p className="terrain-fallback-notice" role="status">3D is unavailable here. These projections preserve every product’s exact coordinates.</p>}
      {data.rows.length ? view === "3d" ? <TerrainViewport data={data} smoothness={smoothness} highlightedLayer={validHighlight} selectedId={selectedId} onSelect={onSelect} draft={draft} onUnavailable={fail} gap={gap} /> : <TerrainProjection data={data} draft={draft} layers={layers} selectedId={selectedId} onSelect={onSelect} gap={gap} /> : <div className="empty-state"><h3>No products have all three coordinates.</h3><p>Choose another numeric trait or broaden the cohort. Missing values remain visible in the matrix.</p></div>}
      <div className="terrain-layer-legend" role="group" aria-label="Terrain colour layers">{layers.map(layer => <button type="button" key={layer.key} aria-pressed={validHighlight === layer.key} onClick={() => setHighlight(validHighlight === layer.key ? null : layer.key)}><i style={{ background: layer.color }} />{layer.label}</button>)}</div>
      <div className="terrain-footnotes"><span>{number(data.rows.length)} products{data.sampled ? ` sampled from ${number(data.completeCount)}` : ""} · {data.z.label}</span><HelpTip label="About terrain evidence and coverage"><p>{number(data.totalMatched)} matching listings; {number(data.pricedCount)} have usable prices. {number(data.completeCount)} have complete coordinates in this range; {number(data.excludedCount)} are excluded.</p><p>{number(data.belowRangeCount)} priced listings below this range; {number(data.aboveRangeCount)} above. Within the range, {number(data.missingScoreCount)} lack a trait score and {number(data.missingZCount)} lack height; these missing counts may overlap.</p><p>The closed colour layers start at {Math.min(0, ...data.rows.map(row => row.z)).toFixed(2)} {data.z.unit || ""}. The 24 × 24 grid joins only supported neighbours. Smoothing changes the surface, never product coordinates.</p></HelpTip>{gap && <span className="terrain-gap-label">Selected observed gap: {money(gap.lower)}–{money(gap.upper)} /100g</span>}</div>
      {configuredProduct && <div className="terrain-draft-status" role="status"><span className="terrain-draft-diamond" aria-hidden="true">◇</span><strong>{configuredProduct.name || "Your product"}</strong>{draft ? <span>{money(draft.price)} /100g · score {draft.score.toFixed(1)} · {data.z.label} {draft.z.toFixed(2)} {data.z.unit}{outOfRange ? " · outside the observed price range; display extends to its exact price" : ""}</span> : <span>Add a valid {data.z.label.toLowerCase()} value to place your product in this view.</span>}</div>}
    </> : <div className="empty-state" role="status"><span className="loading-orbit" /><h3>Preparing the trait landscape…</h3></div>}
  </section>;
}
