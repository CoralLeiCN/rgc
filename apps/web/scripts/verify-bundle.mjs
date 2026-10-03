import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = fileURLToPath(new URL("../", import.meta.url));
const snapshot = path.join(app, "snapshot");
const manifest = JSON.parse(await readFile(path.join(snapshot, "manifest.json"), "utf8"));
const expected = ["manifest.json", ...Object.keys(manifest.files)].map(relative => path.join(snapshot, relative));
const routes = ["schema", "products", "products/[id]", "points", "compare", "analysis", "terrain", "extract-traits"];
let largest = 0;
for (const route of routes) {
  const tracePath = path.join(app, ".next/server/app/api", route, "route.js.nft.json");
  const trace = JSON.parse(await readFile(tracePath, "utf8"));
  const files = new Set(trace.files.map(relative => path.resolve(path.dirname(tracePath), relative)));
  for (const file of expected) assert.ok(files.has(file), `Snapshot omitted from API trace: ${route}: ${path.basename(file)}`);
  let bytes = 0;
  for (const file of files) bytes += (await stat(file)).size;
  largest = Math.max(largest, bytes);
}
console.log(`Verified snapshot files in all ${routes.length} API traces; largest traced dependency set ${(largest / 1024 / 1024).toFixed(1)} MiB (before Vercel packaging).`);
