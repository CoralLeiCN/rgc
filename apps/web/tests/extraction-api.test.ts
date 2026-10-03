import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import type { Snapshot } from "../lib/contracts";
import { handleExtractTraits } from "../lib/server/extract-traits";
import { extractionSchema, validateExtractionOutput } from "../lib/server/extraction-core";

const { fields } = JSON.parse(readFileSync(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;
const input = (body: unknown, headers: Record<string, string> = {}) => new Request("https://app.test/api/extract-traits", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
const candidate = { traits: [{ key: "composition.cocoa_percentage", value: 70, evidence: "70% cocoa" }], warnings: [] };
const finished = (body = candidate) => Response.json({ status: "completed", output: [{ type: "message", content: [{ type: "output_text", text: JSON.stringify(body) }] }] });

test("OpenAI extraction sends private image/text structured output and returns typed review candidates", async () => {
  let sent: Record<string, unknown> = {};
  const png = Buffer.from([137,80,78,71,13,10,26,10,0]).toString("base64");
  const fetcher = (async (url: unknown, options: RequestInit) => {
    assert.equal(url, "https://api.openai.com/v1/responses");
    assert.equal(options.redirect, "error");
    sent = JSON.parse(String(options.body));
    assert.equal(new Headers(options.headers).get("authorization"), "Bearer test-only-key");
    return finished();
  }) as typeof fetch;
  const response = await handleExtractTraits(input({ description: "70% cocoa", image: { mimeType: "image/png", data: png } }), { fields, settings: { apiKey: "test-only-key" }, fetch: fetcher });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(sent.store, false);
  assert.deepEqual((sent.text as { format: unknown }).format, { type: "json_schema", name: "product_traits", strict: true, schema: extractionSchema(fields) });
  assert.match(JSON.stringify(sent.input), /input_image/);
  assert.match(JSON.stringify(sent.input), /70% cocoa/);
  const result = await response.json();
  assert.equal(result.provider, "openai");
  assert.deepEqual(result.traits, candidate.traits);
  assert.equal(JSON.stringify(result).includes("test-only-key"), false);
});

test("unconfigured extraction, invalid origin and invalid uploads never call a provider", async () => {
  let calls = 0;
  const dependencies = { fields, settings: {}, fetch: (async () => { calls++; return finished(); }) as typeof fetch };
  assert.equal((await handleExtractTraits(input({ description: "70% cocoa" }), dependencies)).status, 503);
  assert.equal((await handleExtractTraits(input({ description: "70% cocoa" }, { origin: "https://other.test" }), dependencies)).status, 403);
  for (const body of [{ description: "" }, { description: "x".repeat(12_001) }, { description: "x", score: 99 }, { description: "x", image: { mimeType: "image/svg+xml", data: "AAAA" } }, { description: "x", image: { mimeType: "image/png", data: "AAAA" } }]) {
    assert.equal((await handleExtractTraits(input(body), dependencies)).status, 400);
  }
  assert.equal((await handleExtractTraits(input({ description: "x" }, { "content-length": "3000001" }), dependencies)).status, 413);
  assert.equal(calls, 0);
});

test("runtime validation omits unsupported or ungrounded candidates and rejects duplicate keys", () => {
  const result = validateExtractionOutput({ traits: [
    candidate.traits[0],
    { key: "nutrition.fat_g_per_100g", value: 200, evidence: "200g fat" },
    { key: "dietary.vegan_claim", value: "present", evidence: "" },
    { key: "packaging.materials", value: ["unobtainium"], evidence: "unobtainium" },
    { key: "unknown", value: "x", evidence: "x" }
  ], warnings: [] }, fields);
  assert.deepEqual(result.traits, candidate.traits);
  assert.equal(result.warnings.length, 4);
  assert.throws(() => validateExtractionOutput({ traits: [candidate.traits[0], candidate.traits[0]], warnings: [] }, fields));
  assert.equal(validateExtractionOutput({ traits: [{ key: "composition.allergen_ingredients", value: [], evidence: "None listed" }], warnings: [] }, fields).traits.length, 1);
});

test("Codex bridge requests are authenticated, bounded to configured HTTPS, and revalidated", async () => {
  let calls = 0;
  const token = "test-only-bridge-secret-32-characters-long";
  const fetcher = (async (url: unknown, options: RequestInit) => {
    calls++;
    assert.equal(url, "https://laptop.test.ts.net/extract");
    assert.equal(new Headers(options.headers).get("authorization"), `Bearer ${token}`);
    assert.deepEqual(JSON.parse(String(options.body)), { description: "70% cocoa" });
    return Response.json(candidate);
  }) as typeof fetch;
  const settings = { provider: "codex", bridgeUrl: "https://laptop.test.ts.net/extract", bridgeToken: token };
  const response = await handleExtractTraits(input({ description: "70% cocoa" }), { fields, settings, fetch: fetcher });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).provider, "codex");
  assert.equal((await handleExtractTraits(input({ description: "x" }), { fields, settings: { ...settings, bridgeUrl: "http://127.0.0.1:8787/extract" }, fetch: fetcher })).status, 503);
  assert.equal(calls, 1);
});

test("provider failures, partial responses, refusal and timeouts never masquerade as extracted traits", async () => {
  const run = async (fetcher: typeof fetch) => handleExtractTraits(input({ description: "70% cocoa" }), { fields, settings: { apiKey: "test-key" }, fetch: fetcher });
  assert.equal((await run((async () => Response.json({}, { status: 429 })) as typeof fetch)).status, 429);
  assert.equal((await run((async () => Response.json({ status: "incomplete", output: [] })) as typeof fetch)).status, 502);
  assert.equal((await run((async () => Response.json({ status: "completed", output: [{ content: [{ type: "refusal" }] }] })) as typeof fetch)).status, 422);
  const response = await run((async () => { throw Object.assign(new Error("private provider details"), { name: "TimeoutError" }); }) as typeof fetch);
  assert.equal(response.status, 504);
  assert.equal((await response.text()).includes("private provider details"), false);
});
