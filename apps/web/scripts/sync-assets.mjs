import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = fileURLToPath(new URL("../", import.meta.url));
const source = path.resolve(app, "../../docs/visuals");
const destination = path.join(app, "public");
const manifestPath = path.join(destination, "asset-manifest.json");
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
if (process.argv.includes("--verify")) {
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  for (const [relative, expected] of Object.entries(manifest.files)) {
    assert.match(relative, /^(vendor|studies)\/[a-zA-Z0-9._-]+$/, "Unsafe asset path");
    const bytes = await readFile(path.join(destination, relative));
    assert.equal(bytes.byteLength, expected.byteLength, `Asset size differs: ${relative}`);
    assert.equal(digest(bytes), expected.sha256, `Asset hash differs: ${relative}`);
  }
  console.log(`Verified ${Object.keys(manifest.files).length} vendored visualization assets.`);
} else {
  const files = {};
  const inputs = [
    ["vendor/plotly-gl3d-3.1.0.min.js", "vendor/plotly-gl3d-3.1.0.min.js"],
    ["vendor/plotly-LICENSE.txt", "vendor/plotly-LICENSE.txt"],
    ["vendor/README.md", "vendor/README.md"],
    ...["layered-price-landscape.html", "layered-price-landscape.css", "layered-price-landscape.js", "layered-price-model.js", "price-terrain-model.js", "price-terrain.css"].map(name => [name, `studies/${name}`]),
    ["../layered-price-landscape.md", "studies/layered-price-landscape.md"],
  ];
  for (const [input, output] of inputs) {
    let bytes = await readFile(path.join(source, input));
    if (input === "layered-price-landscape.html") {
      bytes = Buffer.from(bytes.toString("utf8")
        .replaceAll('src="vendor/', 'src="/vendor/')
        .replaceAll('href="visualization-reference-board.html"', 'href="/"')
        .replaceAll('href="collection-explorer.html"', 'href="/"')
        .replaceAll('href="../layered-price-landscape.md"', 'href="layered-price-landscape.md"')
        .replace(/<a href="price-terrain\.html">[^<]*<\/a>/g, ""));
    }
    await mkdir(path.dirname(path.join(destination, output)), { recursive: true });
    await writeFile(path.join(destination, output), bytes);
    files[output] = { sha256: digest(bytes), byteLength: bytes.byteLength };
  }
  await writeFile(manifestPath, JSON.stringify({ formatVersion: 1, files }, null, 2) + "\n");
  console.log(`Synchronized ${Object.keys(files).length} visualization assets from docs/visuals.`);
}
