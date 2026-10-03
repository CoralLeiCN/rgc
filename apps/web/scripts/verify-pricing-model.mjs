import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";

const app = new URL("../", import.meta.url);
const reference = JSON.parse(await readFile(new URL("pricing-model.json", app), "utf8"));
const prepare = process.argv.includes("--fetch");
if (prepare) await mkdir(new URL("model-cache/", app), { recursive: true });
for (const [name, entry] of Object.entries(reference.files)) {
  const target = new URL(`model-cache/${name}`, app);
  let data;
  let downloaded = false;
  try { data = await readFile(target); }
  catch (error) {
    if (!prepare || error.code !== "ENOENT") throw error;
    const url = `https://huggingface.co/datasets/${reference.repoId}/resolve/${reference.revision}/${reference.path}/${name}`;
    const response = await fetch(url, { signal: AbortSignal.timeout(60_000) });
    assert.ok(response.ok && response.body, `Pinned pricing model fetch failed: ${name}`);
    const reader = response.body.getReader();
    const chunks = []; let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > entry.byteLength) { await reader.cancel(); throw new Error(`Pinned pricing model exceeds size: ${name}`); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    data = Buffer.concat(chunks); downloaded = true;
  }
  assert.equal(data.length, entry.byteLength, `Pricing model size: ${name}`);
  assert.equal(createHash("sha256").update(data).digest("hex"), entry.sha256, `Pricing model hash: ${name}`);
  if (downloaded) await writeFile(target, data);
}
const model = JSON.parse(await readFile(new URL("model-cache/model.json", app), "utf8"));
assert.equal(model.identity.fixture, true);
assert.equal(model.release_ready, false);
console.log("Verified immutable synthetic pricing model; inference requires no network or Python runtime.");
