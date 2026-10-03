import assert from "node:assert/strict";
import { buildTerrainGeometry, type TerrainMesh } from "../lib/client/terrain-geometry";
import { retainedBySlice, sliceTerrain } from "../lib/client/terrain-slice";
import type { TerrainResponse } from "../lib/contracts";

function fixture(scores = [0, 20, 40, 60, 80, 100], varying = false): Pick<TerrainResponse, "rows" | "categories" | "priceRange"> {
  const rows = Array.from({ length: 11 }, (_, i) => 1 + i / 5).flatMap(price => scores.map(score => ({
    id: `${price}:${score}`, name: "Slice verification", price, score,
    z: varying ? 8 + price + score / 30 : 10,
    categories: { a: varying ? .2 + score / 200 : .25, b: varying ? .8 - score / 200 : .75 },
  })));
  return { rows, categories: [{ key: "a", label: "A", count: rows.length }, { key: "b", label: "B", count: rows.length }], priceRange: [1, 3] };
}

function volume(mesh: TerrainMesh): number {
  const determinant = (a: number, b: number, c: number) => mesh.x[a] * (mesh.y[b] * mesh.z[c] - mesh.z[b] * mesh.y[c]) - mesh.y[a] * (mesh.x[b] * mesh.z[c] - mesh.z[b] * mesh.x[c]) + mesh.z[a] * (mesh.x[b] * mesh.y[c] - mesh.y[b] * mesh.x[c]);
  return mesh.i.reduce((sum, a, i) => sum + determinant(a, mesh.j[i], mesh.k[i]) / 6, 0);
}

function closed(mesh: TerrainMesh) {
  const edges = new Map<string, number>();
  for (let face = 0; face < mesh.i.length; face++) {
    const vertices = [mesh.i[face], mesh.j[face], mesh.k[face]];
    for (let i = 0; i < 3; i++) {
      const key = [vertices[i], vertices[(i + 1) % 3]].sort((a, b) => a - b).join(":");
      edges.set(key, (edges.get(key) ?? 0) + 1);
    }
  }
  assert.ok([...edges.values()].every(count => count === 2), "Every edge must belong to two faces, including the exposed cut");
}

const flat = buildTerrainGeometry(fixture(), { resolution: 8, smoothness: 1 });
const original = JSON.stringify(flat);
for (const price of [1, 1.75, 2, 1 + 4 / 7, 3]) {
  const lower = sliceTerrain(flat, { price, keep: "lower" });
  const higher = sliceTerrain(flat, { price, keep: "higher" });
  flat.meshes.forEach((mesh, index) => {
    const fullVolume = volume(mesh);
    assert.ok(Math.abs(volume(lower.meshes[index]) - fullVolume * (price - 1) / 2) < 1e-7, "Flat cake volume must follow the retained price interval");
    assert.ok(Math.abs(volume(lower.meshes[index]) + volume(higher.meshes[index]) - fullVolume) < 1e-7, "Both sides must partition the original volume");
    closed(lower.meshes[index]); closed(higher.meshes[index]);
    assert.ok(lower.meshes[index].x.every(x => x <= price + 1e-10));
    assert.ok(higher.meshes[index].x.every(x => x >= price - 1e-10));
  });
  assert.ok(lower.bands.length && higher.bands.length, "Both sides must expose section bands, including at the price boundaries");
}
assert.equal(JSON.stringify(flat), original, "Slicing must preserve the original geometry");
assert.equal(sliceTerrain(flat, null).meshes, flat.meshes, "Restore must use the complete original meshes");

const varying = buildTerrainGeometry(fixture(undefined, true), { resolution: 24, smoothness: .5 });
for (const price of [1.13, 1.75, 2.47, 2.96]) {
  const lower = sliceTerrain(varying, { price, keep: "lower" });
  const higher = sliceTerrain(varying, { price, keep: "higher" });
  varying.meshes.forEach((mesh, index) => {
    assert.ok(Math.abs(volume(lower.meshes[index]) + volume(higher.meshes[index]) - volume(mesh)) < 1e-6, "Cuts must preserve sloped surfaces and varying layer volumes");
    closed(lower.meshes[index]); closed(higher.meshes[index]);
  });
  const sections = (bands: typeof lower.bands) => bands.map(band => [band.key, ...[0, 1].sort((a, b) => band.score[a] - band.score[b]).flatMap(i => [band.score[i], band.bottom[i], band.top[i]].map(value => value.toFixed(8)))].join(":")).sort();
  assert.deepEqual(sections(lower.bands), sections(higher.bands), "The same price must yield the same slice from either side");
}

const holes = buildTerrainGeometry(fixture([0, 10, 90, 100]), { resolution: 24, smoothness: .5 });
const section = sliceTerrain(holes, { price: 2, keep: "higher" });
assert.ok(section.bands.length > 0);
assert.ok(section.bands.every(band => Math.max(...band.score) < 40 || Math.min(...band.score) > 60), "Section faces must preserve unsupported gaps");
const removed = sliceTerrain(flat, { price: 4, keep: "higher" });
assert.ok(removed.meshes.every(mesh => mesh.i.length === 0));
assert.equal(removed.bands.length, 0);
assert.throws(() => sliceTerrain(flat, { price: NaN, keep: "higher" }));
assert.equal(retainedBySlice(2, { price: 2, keep: "higher" }), true);
assert.equal(retainedBySlice(2, { price: 2, keep: "lower" }), true);
assert.equal(retainedBySlice(1.99, { price: 2, keep: "higher" }), false);
console.log("Verified price-slice volume conservation, closed faces, both sides, grid boundaries, support gaps, restoration and point inclusion.");
