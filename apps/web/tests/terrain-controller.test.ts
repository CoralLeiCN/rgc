import test from "node:test";
import assert from "node:assert/strict";
import { TerrainRenderQueue, type TerrainOperation } from "../lib/client/terrain-controller";

function harness(run: (operation: TerrainOperation) => Promise<void>) {
  let id = 0; const frames = new Map<number, () => void>(); const errors: unknown[] = [];
  const queue = new TerrainRenderQueue(run, callback => { frames.set(++id, callback); return id; }, key => { frames.delete(key); }, error => { errors.push(error); });
  return { queue, frames, errors, async frame() { const entry = frames.entries().next().value; if (entry) { frames.delete(entry[0]); entry[1](); } await Promise.resolve(); await Promise.resolve(); } };
}
test("rotation defers geometry and coalesces slider updates until pointer release", async () => {
  const calls: TerrainOperation[] = [], h = harness(async operation => { calls.push(operation); });
  h.queue.setDragging(true); h.queue.invalidate("geometry"); h.queue.invalidate("draft"); h.queue.invalidate("geometry");
  assert.equal(h.frames.size, 0); await h.frame(); assert.deepEqual(calls, []);
  h.queue.setDragging(false); await h.frame(); assert.deepEqual(calls, ["geometry"]); assert.equal(h.frames.size, 0);
});
test("draft, camera, gap, selection and layer updates never request terrain geometry", async () => {
  const calls: TerrainOperation[] = [], h = harness(async operation => { calls.push(operation); });
  for (let i = 0; i < 100; i++) h.queue.invalidate("draft");
  h.queue.invalidate("camera"); h.queue.invalidate("selection"); h.queue.invalidate("appearance"); h.queue.invalidate("gap");
  while (h.frames.size) await h.frame();
  assert.deepEqual(calls, ["camera", "appearance", "selection", "draft", "gap"]);
});
test("busy renderer serializes commands and retains updates received during an unfinished render", async () => {
  let release!: () => void; const calls: TerrainOperation[] = [];
  const h = harness(async operation => { calls.push(operation); if (operation === "geometry") await new Promise<void>(resolve => { release = resolve; }); });
  h.queue.invalidate("geometry"); await h.frame();
  h.queue.invalidate("draft");h.queue.invalidate("resize");h.queue.invalidate("camera");assert.equal(h.frames.size, 0);
  release(); await Promise.resolve(); await Promise.resolve();
  while (h.frames.size) await h.frame();assert.deepEqual(calls, ["geometry", "camera", "draft", "resize"]);
});
test("drag beginning after frame scheduling still prevents work, and disposal cancels queued callbacks", async () => {
  const calls: TerrainOperation[] = [], h = harness(async operation => { calls.push(operation); });
  h.queue.invalidate("geometry");h.queue.setDragging(true);await h.frame();assert.deepEqual(calls, []);
  h.queue.setDragging(false);assert.equal(h.frames.size, 1);h.queue.dispose();await h.frame();assert.deepEqual(calls, []);
});
test("renderer failure is reported once and stops the queue", async () => {
  const error = new Error("WebGL unavailable"); const h = harness(async () => { throw error; });
  h.queue.invalidate("geometry");await h.frame();h.queue.invalidate("draft");await h.frame();assert.deepEqual(h.errors, [error]);assert.equal(h.frames.size, 0);
});
