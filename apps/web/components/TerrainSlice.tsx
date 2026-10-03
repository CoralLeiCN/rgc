"use client";

import { useMemo } from "react";
import type { TerrainResponse } from "../lib/contracts";
import { buildTerrainGeometry } from "../lib/client/terrain-geometry";
import { sliceTerrain, type PriceSlice, type SliceBand } from "../lib/client/terrain-slice";

export interface PriceSection { price: number; bands: SliceBand[]; baseline: number; ceiling: number; label: string; unit: string | null; }

export function TerrainSliceSection({ section }: { section: PriceSection }) {
  const { price, bands, baseline, label, unit } = section;
  const ceiling = Math.max(baseline + 1, section.ceiling);
  const x = (score: number) => 60 + score * 5.5;
  const y = (height: number) => 205 - (height - baseline) / (ceiling - baseline) * 165;
  return <section className="terrain-slice-section" aria-label={`Cake slice at £${price.toFixed(2)} per 100 g`}>
    <div className="terrain-slice-section-heading"><div><p className="eyebrow">INSIDE THE CAKE</p><h3>Slice at £{price.toFixed(2)} / 100 g</h3></div><span>{label}{unit ? ` · ${unit}` : ""}</span></div>
    {bands.length ? <svg viewBox="0 0 640 250" role="img" aria-label={`Interpolated colour layers at £${price.toFixed(2)} per 100 g, across demo trait scores. Height is ${label}${unit ? ` in ${unit}` : ""}.`}>
      {[0, .25, .5, .75, 1].map(t => <g key={t}><line x1="60" x2="610" y1={205 - t * 165} y2={205 - t * 165} className="terrain-svg-grid" /><text x="50" y={209 - t * 165} textAnchor="end" className="terrain-svg-tick">{(baseline + t * (ceiling - baseline)).toFixed(1)}</text><text x={60 + t * 550} y="225" textAnchor="middle" className="terrain-svg-tick">{(t * 100).toFixed(0)}</text></g>)}
      {bands.map((band, index) => <polygon key={index} points={`${x(band.score[0])},${y(band.bottom[0])} ${x(band.score[1])},${y(band.bottom[1])} ${x(band.score[1])},${y(band.top[1])} ${x(band.score[0])},${y(band.top[0])}`} fill={band.color}><title>{band.label}: demo scores {Math.min(...band.score).toFixed(1)}–{Math.max(...band.score).toFixed(1)}</title></polygon>)}
      <text x="335" y="247" textAnchor="middle" className="terrain-svg-title">TRAIT SCORE · DEMO</text>
    </svg> : <p className="terrain-slice-empty" role="status">No supported layers at this price. Move the cut to another price point.</p>}
    <p className="terrain-slice-caption">Interpolated layer composition at this price. Gaps indicate missing surface support.</p>
  </section>;
}

/** The exact section remains available without WebGL. */
export function TerrainSliceProjection({ data, smoothness, slice }: { data: TerrainResponse; smoothness: number; slice: PriceSlice }) {
  const geometry = useMemo(() => buildTerrainGeometry(data, { resolution: 24, smoothness }), [data, smoothness]);
  const bands = useMemo(() => sliceTerrain(geometry, slice).bands, [geometry, slice]);
  return <TerrainSliceSection section={{ price: slice.price, bands, baseline: geometry.baseline, ceiling: Math.max(...data.rows.map(row => row.z)), label: data.z.label, unit: data.z.unit }} />;
}
