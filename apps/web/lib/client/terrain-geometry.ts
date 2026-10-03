import type { FieldDefinition, JsonValue, TerrainResponse } from "../contracts";

type Row = TerrainResponse["rows"][number];
export interface TerrainLayer { key: string; label: string; color: string; members: string[]; median: number; }
export interface TerrainNode { x: number; y: number; z: number; shares: number[]; support: number; }
export interface TerrainMesh { layer: TerrainLayer; x: number[]; y: number[]; z: number[]; i: number[]; j: number[]; k: number[]; shares: number[]; thickness: number[]; }
export interface TerrainGeometry { layers: TerrainLayer[]; meshes: TerrainMesh[]; nodes: (TerrainNode | null)[]; cells: number[]; baseline: number; resolution: number; xDomain: [number, number]; yDomain: [number, number]; }
export interface ConfiguredTerrainProduct { name: string; price: number; score: number; traits: Record<string, JsonValue>; }
export interface TerrainDraftPoint { name: string; price: number; score: number; z: number; }
const states: Record<string, { label: string; color: string }> = {
  unknown: { label: "Unknown", color: "#8495a3" }, conflict: { label: "Conflicting evidence", color: "#f09278" },
  not_applicable: { label: "Not applicable", color: "#b2a2ca" }, truncated: { label: "Truncated evidence", color: "#d6b270" }, empty: { label: "Empty value", color: "#c0c8ce" }
};
const stateOf = (key: string) => key.match(/=state:(unknown|conflict|not_applicable|truncated|empty)$/)?.[1];
function categoryColor(key: string) {
  let hash = 2166136261;
  for (const char of key) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return `hsl(${(hash >>> 0) % 360}, 65%, 65%)`;
}
function weightedMedian(items: { value: number; weight: number }[]) {
  const sorted = items.sort((a, b) => a.value - b.value); const half = sorted.reduce((sum, item) => sum + item.weight, 0) / 2;
  let weight = 0;
  for (const item of sorted) { weight += item.weight; if (weight >= half) return item.value; }
  return 0;
}
/** State groups stay explicit; at most eight named layers plus one Other layer. */
export function terrainLayers(data: Pick<TerrainResponse, "categories" | "rows">): TerrainLayer[] {
  const grouped = new Map<string, { key: string; label: string; color: string; members: string[]; count: number }>();
  for (const category of data.categories) {
    const state = stateOf(category.key); const key = state ? `state:${state}` : category.key;
    const existing = grouped.get(key);
    if (existing) { existing.members.push(category.key); existing.count += category.count; }
    else grouped.set(key, { key, label: state ? states[state].label : category.label, color: state ? states[state].color : categoryColor(key), members: [category.key], count: category.count });
  }
  const stateLayers = [...grouped.values()].filter(item => item.key.startsWith("state:"));
  const known = [...grouped.values()].filter(item => !item.key.startsWith("state:")).sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
  const count = Math.max(0, 8 - stateLayers.length); const layers = [...stateLayers, ...known.slice(0, count)];
  const rest = known.slice(count);
  if (rest.length) layers.push({ key: "__other__", label: "Other categories", color: "#789a98", members: rest.flatMap(item => item.members), count: rest.reduce((sum, item) => sum + item.count, 0) });
  return layers.map(layer => ({ ...layer, median: weightedMedian(data.rows.map(row => ({ value: row.z, weight: layer.members.reduce((sum, key) => sum + (row.categories[key] || 0), 0) })).filter(item => item.weight > 0)) })).sort((a, b) => a.median - b.median || a.key.localeCompare(b.key));
}
function domain(minimum: number, maximum: number): [number, number] {
  if (maximum > minimum) return [minimum, maximum];
  const padding = Math.max(Math.abs(minimum) * .05, .5); return [minimum - padding, maximum + padding];
}
export function terrainPriceDomain(data: Pick<TerrainResponse, "rows" | "priceRange">): [number, number] {
  const prices = data.rows.map(row => row.price).filter(Number.isFinite);
  return prices.length ? domain(data.priceRange?.[0] ?? Math.min(...prices), data.priceRange?.[1] ?? Math.max(...prices)) : [0, 1];
}
/** Compact positive kernel: weighted heights cannot overshoot observed Z and unsupported cells remain holes. */
export function buildTerrainGeometry(data: Pick<TerrainResponse, "rows" | "categories" | "priceRange">, options: { resolution?: number; smoothness?: number } = {}): TerrainGeometry {
  const resolution = Math.max(8, Math.min(32, Math.round(options.resolution ?? 24)));
  const smoothness = Math.max(0, Math.min(1, options.smoothness ?? .5)); const radius = .085 + smoothness * .16;
  const rows = data.rows.filter(row => [row.price, row.score, row.z].every(Number.isFinite));
  const layers = terrainLayers({ rows, categories: data.categories });
  const xDomain = terrainPriceDomain({ ...data, rows });
  const yDomain: [number, number] = [0, 100];
  const baseline = Math.min(0, ...rows.map(row => row.z)); const nodes: (TerrainNode | null)[] = [];
  const prepared = rows.map(row => ({ row, x: (row.price - xDomain[0]) / (xDomain[1] - xDomain[0]), y: row.score / 100, shares: layers.map(layer => layer.members.reduce((sum, key) => sum + (row.categories[key] || 0), 0)) }));
  for (let y = 0; y < resolution; y++) for (let x = 0; x < resolution; x++) {
    const u = x / (resolution - 1), v = y / (resolution - 1); let weight = 0, height = 0; const shares = layers.map(() => 0);
    for (const item of prepared) {
      const distance = (item.x - u) ** 2 + (item.y - v) ** 2; if (distance >= radius ** 2) continue;
      const kernel = (1 - distance / radius ** 2) ** 2; weight += kernel; height += item.row.z * kernel;
      for (let layer = 0; layer < shares.length; layer++) shares[layer] += item.shares[layer] * kernel;
    }
    if (weight <= 1e-12) { nodes.push(null); continue; }
    const shareTotal = shares.reduce((sum, value) => sum + value, 0);
    nodes.push({ x: xDomain[0] + u * (xDomain[1] - xDomain[0]), y: v * 100, z: height / weight, shares: shares.map(value => shareTotal > 0 ? value / shareTotal : 0), support: weight });
  }
  const cells: number[] = [];
  for (let y = 0; y < resolution - 1; y++) for (let x = 0; x < resolution - 1; x++) {
    const a = y * resolution + x;
    if ([a, a + 1, a + resolution, a + resolution + 1].every(index => nodes[index])) cells.push(a);
  }
  const used = [...new Set(cells.flatMap(a => [a, a + 1, a + resolution, a + resolution + 1]))].sort((a, b) => a - b);
  const indices = new Map(used.map((value, index) => [value, index])); const n = used.length;
  const meshes = layers.map((layer, layerIndex): TerrainMesh => {
    const mesh: TerrainMesh = { layer, x: [], y: [], z: [], i: [], j: [], k: [], shares: [], thickness: [] };
    // A zero-thickness layer must not paint over a neighbouring category's surface.
    const layerCells = cells.filter(a => [a, a + 1, a + resolution, a + resolution + 1].some(index => (nodes[index]!.z - baseline) * nodes[index]!.shares[layerIndex] > 1e-10));
    const layerCellSet = new Set(layerCells);
    for (const top of [false, true]) for (const index of used) {
      const node = nodes[index]!; const height = Math.max(0, node.z - baseline);
      const below = node.shares.slice(0, layerIndex).reduce((sum, share) => sum + share, 0); const share = node.shares[layerIndex];
      mesh.x.push(node.x); mesh.y.push(node.y); mesh.z.push(baseline + height * (below + (top ? share : 0))); mesh.shares.push(share); mesh.thickness.push(height * share);
    }
    const triangle = (a: number, b: number, c: number) => { mesh.i.push(a); mesh.j.push(b); mesh.k.push(c); };
    const wall = (a: number, b: number) => { triangle(a, b, b + n); triangle(a, b + n, a + n); };
    for (const a of layerCells) {
      const b = a + 1, c = a + resolution, d = c + 1; const ia = indices.get(a)!, ib = indices.get(b)!, ic = indices.get(c)!, id = indices.get(d)!;
      triangle(ia + n, ib + n, id + n); triangle(ia + n, id + n, ic + n); triangle(ia, id, ib); triangle(ia, ic, id);
      if (!layerCellSet.has(a - resolution)) wall(ia, ib);
      if (a % resolution === resolution - 2 || !layerCellSet.has(a + 1)) wall(ib, id);
      if (!layerCellSet.has(a + resolution)) wall(id, ic);
      if (a % resolution === 0 || !layerCellSet.has(a - 1)) wall(ic, ia);
    }
    return mesh;
  });
  return { layers, meshes, nodes, cells, baseline, resolution, xDomain, yDomain };
}
function validNumeric(value: JsonValue | undefined, field: FieldDefinition): value is number {
  return typeof value === "number" && Number.isFinite(value) && (field.type !== "integer" || Number.isInteger(value)) && (field.minimum === null || value >= field.minimum) && (field.maximum === null || value <= field.maximum);
}
/** Drafts use exactly the API's Z metadata; unknown values are never silently invented. */
export function projectTerrainDraft(product: ConfiguredTerrainProduct | null | undefined, data: TerrainResponse): TerrainDraftPoint | null {
  if (!product || !Number.isFinite(product.price) || product.price < 0 || !Number.isFinite(product.score) || product.score < 0 || product.score > 100) return null;
  if (data.z.key.startsWith("family:")) return null;
  const field = data.z.fields[0], value = product.traits[data.z.key];
  if (!field || !validNumeric(value, field)) return null;
  return { name: product.name, price: product.price, score: product.score, z: value };
}
export function rowLayerColor(row: Row, layers: TerrainLayer[]) {
  let highest = -1, color = "#e0f8ed";
  for (const layer of layers) { const share = layer.members.reduce((sum, key) => sum + (row.categories[key] || 0), 0); if (share > highest) { highest = share; color = layer.color; } }
  return color;
}
