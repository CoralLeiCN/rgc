import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const destination = fileURLToPath(new URL("../public/", import.meta.url));
const manifestPath = path.join(destination, "asset-manifest.json");
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
for (const [relative, expected] of Object.entries(manifest.files)) {
  assert.match(relative, /^(?:vendor\/[a-zA-Z0-9._-]+|examples\/[a-z0-9-]+\/[a-z0-9-]+\.(?:jpg|jpeg|png|webp))$/, "Unsafe asset path");
  const bytes = await readFile(path.join(destination, relative));
  assert.equal(bytes.byteLength, expected.byteLength, `Asset size differs: ${relative}`);
  assert.equal(digest(bytes), expected.sha256, `Asset hash differs: ${relative}`);
}
console.log(`Verified ${Object.keys(manifest.files).length} visualization and example assets.`);
