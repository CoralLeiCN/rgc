import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { lstat, readFile, readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../snapshot/", import.meta.url));
const manifest = JSON.parse(await readFile(path.join(root, "manifest.json"), "utf8"));
assert.equal(manifest.formatVersion, 1, "Unsupported snapshot manifest");
assert.match(manifest.revision, /^[a-f0-9]{40}$/, "Pinned source revision required");
assert.ok(manifest.files && Object.keys(manifest.files).length > 1, "Snapshot files missing");
const canonicalRoot = await realpath(root);
let bytes = 0;
for (const [relative, expected] of Object.entries(manifest.files)) {
  assert.match(relative, /^(index\.json|evidence\/[a-z0-9-]+\.json)$/, "Unsafe snapshot path");
  const location = path.join(root, relative);
  assert.equal((await lstat(location)).isSymbolicLink(), false, "Snapshot symlinks are forbidden");
  assert.ok((await realpath(location)).startsWith(canonicalRoot + path.sep), "Snapshot escapes its root");
  const content = await readFile(location);
  assert.equal(content.byteLength, expected.byteLength, `Byte count differs: ${relative}`);
  assert.equal(createHash("sha256").update(content).digest("hex"), expected.sha256, `Hash differs: ${relative}`);
  bytes += content.byteLength;
}
const snapshot = JSON.parse(await readFile(path.join(root, "index.json"), "utf8"));
assert.equal(snapshot.meta.revision, manifest.revision, "Snapshot revision differs");
assert.equal(snapshot.meta.datasetVersion, manifest.datasetVersion, "Snapshot dataset version differs");
assert.equal(snapshot.contract.schemaVersion, manifest.schemaVersion, "Snapshot schema version differs");
assert.equal(snapshot.meta.schemaVersion, manifest.schemaVersion, "Snapshot schema metadata differs");
assert.equal(snapshot.products.length, snapshot.meta.schemaValidatedListings, "Validated count differs");
const fields = new Set(snapshot.fields.map(field => field.key));
assert.equal(fields.size, snapshot.fields.length, "Duplicate field definition");
assert.ok(fields.size > 0, "Empty field catalogue");
const ids = new Set();
const sources = new Set();
for (const product of snapshot.products) {
  assert.ok(product.id && !ids.has(product.id), "Missing or duplicate listing ID");
  ids.add(product.id);
  assert.match(product.source, /^[a-z0-9-]+$/, "Unsafe source key");
  sources.add(product.source);
  assert.ok(manifest.files[`evidence/${product.source}.json`], "Source evidence omitted from manifest");
  for (const [key, attribute] of Object.entries(product.attributes)) {
    assert.ok(fields.has(key), `Unknown field: ${key}`);
    assert.ok(snapshot.contract.states.includes(attribute.status), `Invalid field status: ${key}`);
  }
}
const evidenceFiles = (await readdir(path.join(root, "evidence"))).sort();
assert.deepEqual(evidenceFiles, [...sources].map(source => `${source}.json`).sort(), "Evidence shard catalogue differs");
for (const source of sources) {
  const evidence = JSON.parse(await readFile(path.join(root, "evidence", `${source}.json`), "utf8"));
  const expected = snapshot.products.filter(product => product.source === source).map(product => product.id).sort();
  assert.deepEqual(Object.keys(evidence).sort(), expected, `Evidence listing IDs differ: ${source}`);
}
console.log(`Verified ${snapshot.products.length} listings, ${fields.size} traits and ${sources.size} evidence shards (${(bytes / 1024 / 1024).toFixed(1)} MiB); revision ${manifest.revision.slice(0, 12)}.`);
