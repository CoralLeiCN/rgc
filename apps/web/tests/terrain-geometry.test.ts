import test from "node:test";
import assert from "node:assert/strict";
import type { FieldDefinition, TerrainResponse } from "../lib/contracts";
import { buildTerrainGeometry, projectTerrainDraft, terrainLayers } from "../lib/client/terrain-geometry";

const field: FieldDefinition = { key: "composition.cocoa_percentage", label: "Cocoa", group: "composition", known: 3, conflicts: 0, numeric: true, numericKnown: 3, type: "number", unit: "%", scope: null, description: "", qualifier: "", minimum: 0, maximum: 100, allowedValues: [], modelRole: null, modelSelected: false, modelDefinition: null };
function data(): TerrainResponse {
  return { color: { key: "kind", label: "Kind", fields: [] }, z: { key: field.key, label: "Cocoa", unit: "%", fields: [field] }, rows: [
    { id: "a", name: "A", price: 2, score: 40, z: 30, categories: { "kind=value:dark": .75, "kind=state:unknown": .25 } },
    { id: "b", name: "B", price: 2.5, score: 50, z: 50, categories: { "kind=value:dark": .25, "kind=value:milk": .75 } },
    { id: "c", name: "C", price: 3, score: 60, z: 80, categories: { "kind=value:milk": 1 } }
  ], categories: [{ key: "kind=value:dark", label: "Dark", count: 2 }, { key: "kind=value:milk", label: "Milk", count: 2 }, { key: "kind=state:unknown", label: "Unknown", count: 1 }], totalMatched: 3, pricedCount: 3, completeCount: 3, excludedCount: 0, sampled: false, limit: 500, priceRange: [2, 3], range: "full", requestedRange: "full", rangeFallbackReason: null, belowRangeCount: 0, aboveRangeCount: 0, missingScoreCount: 0, missingZCount: 0, scoreDefinition: "Illustrative", scoreVersion: "trait-demo-1" };
}
test("local layers partition a convex height, preserve row coordinates, and leave unsupported holes", () => {
  const input = data(), before = structuredClone(input); const geometry = buildTerrainGeometry(input, { smoothness: .6 });
  assert.deepEqual(input, before); assert.equal(geometry.resolution, 24); assert.ok(geometry.cells.length > 0);
  assert.ok(geometry.nodes.some(node => node === null)); assert.ok(geometry.cells.length < 23 * 23);
  for (const node of geometry.nodes) if (node) {
    assert.ok(node.z >= 30 - 1e-10 && node.z <= 80 + 1e-10); assert.ok(Math.abs(node.shares.reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
    assert.ok(node.shares.every(share => share >= 0 && share <= 1));
  }
  for (let i = 1; i < geometry.meshes.length; i++) {
    const previous = geometry.meshes[i - 1], current = geometry.meshes[i], half = current.z.length / 2;
    for (let vertex = 0; vertex < half; vertex++) assert.ok(Math.abs(current.z[vertex] - previous.z[vertex + half]) < 1e-10);
  }
  const bottom = geometry.meshes[0]; assert.ok(bottom.z.slice(0, bottom.z.length / 2).every(z => z === geometry.baseline));
});
test("each layer is a closed triangle mesh with bounded grid size", () => {
  const geometry = buildTerrainGeometry(data(), { resolution: 1000, smoothness: .8 }); assert.equal(geometry.resolution, 32);
  for (const mesh of geometry.meshes) {
    assert.ok(mesh.x.length <= 32 * 32 * 2); assert.equal(mesh.i.length, mesh.j.length); assert.equal(mesh.j.length, mesh.k.length);
    const edges = new Map<string, number>();
    for (let face = 0; face < mesh.i.length; face++) {
      const triangle = [mesh.i[face], mesh.j[face], mesh.k[face]];
      for (const vertex of triangle) assert.ok(vertex >= 0 && vertex < mesh.x.length && Number.isFinite(mesh.z[vertex]));
      for (let side = 0; side < 3; side++) { const edge = [triangle[side], triangle[(side + 1) % 3]].sort((a, b) => a - b).join(":"); edges.set(edge, (edges.get(edge) || 0) + 1); }
    }
    assert.ok([...edges.values()].every(count => count === 2), "Every mesh boundary closes on a side or adjacent face");
  }
});
test("negative numeric values use an explicit baseline without inverted layer thickness", () => {
  const input = data(); input.rows[0].z = -20; input.rows[1].z = -5; input.rows[2].z = 10;
  const result = buildTerrainGeometry(input); assert.equal(result.baseline, -20);
  for (const mesh of result.meshes) { assert.ok(mesh.thickness.every(value => value >= 0)); assert.ok(mesh.z.every(value => value >= -20 - 1e-10 && value <= 10 + 1e-10)); }
});
test("many categories keep explicit evidence states and partition every original category once", () => {
  const input = data(); input.categories = Array.from({ length: 30 }, (_, i) => ({ key: `kind=value:${i}`, label: `Kind ${i}`, count: 30 - i }));
  input.categories.push({ key: "kind=state:unknown", label: "Unknown", count: 1 }, { key: "other=state:unknown", label: "Other unknown", count: 1 }, { key: "kind=state:conflict", label: "Conflict", count: 1 }, { key: "kind=state:not_applicable", label: "N/A", count: 1 });
  input.rows = input.rows.map(row => ({ ...row, categories: Object.fromEntries(input.categories.map(item => [item.key, 1 / input.categories.length])) }));
  const layers = terrainLayers(input); assert.ok(layers.length <= 9);
  for (const state of ["unknown", "conflict", "not_applicable"]) assert.ok(layers.some(layer => layer.key === `state:${state}`));
  assert.deepEqual(layers.flatMap(layer => layer.members).sort(), input.categories.map(item => item.key).sort());
  assert.ok(layers.some(layer => layer.key === "__other__"));
  assert.deepEqual(terrainLayers(input), layers);
});
test("empty and constant coordinate cohorts remain finite", () => {
  const input = data(); input.rows = []; input.categories = []; input.priceRange = null;
  assert.equal(buildTerrainGeometry(input).cells.length, 0);
  input.rows = [{ id: "a", name: "A", price: 5, score: 50, z: 0, categories: { "kind=value:dark": 1 } }];input.categories = [{ key: "kind=value:dark", label: "Dark", count: 1 }]; input.priceRange = [5, 5];
  const result = buildTerrainGeometry(input); assert.ok(result.xDomain[1] > result.xDomain[0]); assert.ok(result.nodes.filter(Boolean).every(node => Number.isFinite(node!.z)));
  assert.ok(result.meshes.every(mesh => mesh.i.length === 0), "Zero-height categories cannot paint opaque phantom surfaces");
});
test("configured product projects exact raw Z and rejects missing or invalid values", () => {
  const input = data(), draft = { name: "Own", price: 120, score: 70, traits: { [field.key]: 65 } };
  assert.deepEqual(projectTerrainDraft(draft, input), { name: "Own", price: 120, score: 70, z: 65 });
  assert.equal(projectTerrainDraft({ ...draft, traits: {} }, input), null);
  assert.equal(projectTerrainDraft({ ...draft, traits: { [field.key]: 101 } }, input), null);
  assert.equal(projectTerrainDraft({ ...draft, score: Number.NaN }, input), null);
});
test("family numeric aggregates cannot become draft height", () => {
  const input = data(), second = { ...field, key: "composition.other" };
  input.z = { key: "family:composition", label: "Composition", unit: "index", fields: [field, second] };
  const draft = { name: "Own", price: 3, score: 75, traits: { [field.key]: 50, [second.key]: 30 } };
  assert.equal(projectTerrainDraft(draft, input), null);
  assert.equal(projectTerrainDraft({ ...draft, traits: {} }, input), null);
});
