import type { TerrainGeometry, TerrainMesh } from "./terrain-geometry";

export interface PriceSlice { price: number; keep: "higher" | "lower"; }
export interface SliceBand { key: string; label: string; color: string; score: [number, number]; bottom: [number, number]; top: [number, number]; }
export interface SlicedTerrain { meshes: TerrainMesh[]; bands: SliceBand[]; }
interface Column { x: number; y: number; bottom: number; top: number; share: number; }

export function retainedBySlice(price: number, slice: PriceSlice | null): boolean {
  return !slice || (slice.keep === "higher" ? price >= slice.price : price <= slice.price);
}

/** Clip each existing surface triangle; interpolated columns preserve its planes. */
function clip(columns: Column[], slice: PriceSlice): Column[] {
  const result: Column[] = [];
  for (let i = 0; i < columns.length; i++) {
    const a = columns[i], b = columns[(i + 1) % columns.length];
    const aInside = retainedBySlice(a.x, slice), bInside = retainedBySlice(b.x, slice);
    if (aInside) result.push(a);
    if (aInside !== bInside) {
      const t = (slice.price - a.x) / (b.x - a.x);
      const mix = (key: "y" | "bottom" | "top" | "share") => a[key] + t * (b[key] - a[key]);
      result.push({ x: slice.price, y: mix("y"), bottom: mix("bottom"), top: mix("top"), share: mix("share") });
    }
  }
  return result;
}

/** Close the exposed layer faces while preserving unsupported gaps and source meshes. */
export function sliceTerrain(geometry: TerrainGeometry, slice: PriceSlice | null): SlicedTerrain {
  if (!slice) return { meshes: geometry.meshes, bands: [] };
  if (!Number.isFinite(slice.price)) throw new Error("The slice price must be finite.");
  const bands: SliceBand[] = [];
  const span = geometry.xDomain[1] - geometry.xDomain[0];
  const key = (point: Column) => `${Math.round((point.x - geometry.xDomain[0]) / span * 1e10)}:${Math.round(point.y * 1e8)}`;
  const meshes = geometry.meshes.map(source => {
    const mesh: TerrainMesh = { layer: source.layer, x: [], y: [], z: [], i: [], j: [], k: [], shares: [], thickness: [] };
    const vertices = new Map<string, number>();
    const edges = new Map<string, { a: Column; b: Column; count: number }>();
    const half = source.x.length / 2;
    const column = (index: number): Column => ({ x: source.x[index], y: source.y[index], bottom: source.z[index - half], top: source.z[index], share: source.shares[index] });
    const vertex = (point: Column) => {
      const id = key(point), existing = vertices.get(id);
      if (existing !== undefined) return existing;
      const index = mesh.x.length;
      for (const z of [point.bottom, point.top]) {
        mesh.x.push(point.x); mesh.y.push(point.y); mesh.z.push(z);
        mesh.shares.push(point.share); mesh.thickness.push(point.top - point.bottom);
      }
      vertices.set(id, index);
      return index;
    };
    const triangle = (a: number, b: number, c: number) => { mesh.i.push(a); mesh.j.push(b); mesh.k.push(c); };
    for (let face = 0; face < source.i.length; face++) {
      const indices = [source.i[face], source.j[face], source.k[face]];
      // Base terrain stores lower vertices first, followed by matching upper vertices.
      if (indices.some(index => index < half)) continue;
      const clipped = clip(indices.map(column), slice);
      const polygon = clipped.filter((point, i) => key(point) !== key(clipped[(i + 1) % clipped.length]));
      if (polygon.length < 3 || polygon.every(point => point.top - point.bottom <= 1e-10)) continue;
      const area = polygon.reduce((sum, point, i) => { const next = polygon[(i + 1) % polygon.length]; return sum + point.x * next.y - next.x * point.y; }, 0);
      if (Math.abs(area) <= span * 1e-12) continue;
      const ids = polygon.map(vertex);
      for (let i = 1; i < ids.length - 1; i++) {
        triangle(ids[0] + 1, ids[i] + 1, ids[i + 1] + 1);
        triangle(ids[0], ids[i + 1], ids[i]);
      }
      for (let i = 0; i < polygon.length; i++) {
        const a = polygon[i], b = polygon[(i + 1) % polygon.length];
        const edgeKey = [key(a), key(b)].sort().join("/");
        const existing = edges.get(edgeKey);
        if (existing) existing.count++;
        else edges.set(edgeKey, { a, b, count: 1 });
      }
    }
    for (const { a, b, count } of edges.values()) {
      if (count !== 1) continue;
      const ia = vertex(a), ib = vertex(b);
      triangle(ia, ib, ib + 1); triangle(ia, ib + 1, ia + 1);
      if (Math.abs(a.x - slice.price) <= span * 1e-10 && Math.abs(b.x - slice.price) <= span * 1e-10 && Math.abs(a.y - b.y) > 1e-10) {
        bands.push({ key: source.layer.key, label: source.layer.label, color: source.layer.color, score: [a.y, b.y], bottom: [a.bottom, b.bottom], top: [a.top, b.top] });
      }
    }
    return mesh;
  });
  // A cut at the domain edge has a section even if the retained volume is empty.
  if (!bands.length && (slice.keep === "higher" && slice.price === geometry.xDomain[1] || slice.keep === "lower" && slice.price === geometry.xDomain[0])) {
    return { meshes, bands: sliceTerrain(geometry, { ...slice, keep: slice.keep === "higher" ? "lower" : "higher" }).bands };
  }
  return { meshes, bands };
}
