import "server-only";
import type { ExtractionRequest, ExtractionResponse } from "../extraction-contract";
import type { FieldDefinition } from "../contracts";
import { loadSnapshot } from "./data";
import { ApiError } from "./errors";
import { extractionInstructions, extractionSchema, readExtractionInput, validateExtractionInput, validateExtractionOutput } from "./extraction-core";

type Settings = { provider?: string; apiKey?: string; model?: string; bridgeUrl?: string; bridgeToken?: string };
type Dependencies = { fetch?: typeof fetch; fields?: FieldDefinition[]; settings?: Settings };
const response = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
let inFlight = 0;

async function providerJson(fetcher: typeof fetch, url: string, init: RequestInit): Promise<unknown> {
  const upstream = await fetcher(url, { ...init, redirect: "error" });
  if (!upstream.ok) {
    if (upstream.status === 429) throw new ApiError(429, "EXTRACTOR_BUSY", "The extractor is at its usage limit. Try again shortly.");
    if (upstream.status === 401 || upstream.status === 403) throw new ApiError(503, "EXTRACTOR_AUTH", "The extractor connection needs its credentials checked.");
    throw new ApiError(502, "EXTRACTOR_UNAVAILABLE", "The extractor could not complete this request. Try again shortly.");
  }
  // Output is compact candidate JSON, never an unbounded provider transcript.
  const reader = upstream.body?.getReader();
  if (!reader) throw new ApiError(502, "INVALID_MODEL_OUTPUT", "The extractor returned no result.");
  let bytes = 0; const chunks: Uint8Array[] = [];
  try { while (true) { const { value, done } = await reader.read(); if (done) break; bytes += value.byteLength; if (bytes > 300_000) { await reader.cancel(); throw new ApiError(502, "INVALID_MODEL_OUTPUT", "The extractor result was too large."); } chunks.push(value); } } finally { reader.releaseLock(); }
  try { return JSON.parse(Buffer.concat(chunks).toString("utf8")); } catch { throw new ApiError(502, "INVALID_MODEL_OUTPUT", "The extractor returned unreadable JSON."); }
}

export async function extractWithProvider(input: ExtractionRequest, fields: FieldDefinition[], settings: Settings, fetcher = fetch): Promise<ExtractionResponse> {
  const validatedInput = validateExtractionInput(input);
  const provider = settings.provider || (settings.bridgeUrl ? "codex" : "openai");
  const signal = AbortSignal.timeout(provider === "codex" ? 100_000 : 45_000);
  if (provider === "codex") {
    let url: URL;
    try { url = new URL(settings.bridgeUrl || ""); } catch { throw new ApiError(503, "EXTRACTOR_NOT_CONFIGURED", "The local Codex extractor is not connected yet."); }
    if (url.protocol !== "https:" || url.username || url.password || !settings.bridgeToken || settings.bridgeToken.length < 32) throw new ApiError(503, "EXTRACTOR_NOT_CONFIGURED", "Configure the local extractor HTTPS URL and its server-side secret.");
    const result = await providerJson(fetcher, url.href, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${settings.bridgeToken}` }, body: JSON.stringify(validatedInput), signal });
    const validated = validateExtractionOutput(result, fields);
    return { provider: "codex", model: "Codex on your laptop", ...validated };
  }
  if (provider !== "openai") throw new ApiError(503, "EXTRACTOR_NOT_CONFIGURED", "Choose an extraction provider in the server configuration.");
  if (!settings.apiKey) throw new ApiError(503, "EXTRACTOR_NOT_CONFIGURED", "Trait extraction is not connected yet. Configure OpenAI or the local Codex bridge in Vercel.");
  const model = settings.model || "gpt-4.1-mini";
  const content: Record<string, unknown>[] = [{ type: "input_text", text: validatedInput.description || "Extract supported traits visible across these product images." }];
  for (const image of validatedInput.images) content.push({ type: "input_image", image_url: `data:${image.mimeType};base64,${image.data}`, detail: "high" });
  const raw = await providerJson(fetcher, "https://api.openai.com/v1/responses", {
    method: "POST", signal, headers: { "Content-Type": "application/json", Authorization: `Bearer ${settings.apiKey}` },
    body: JSON.stringify({ model, store: false, max_output_tokens: 6000, instructions: extractionInstructions(fields), input: [{ role: "user", content }], text: { format: { type: "json_schema", name: "product_traits", strict: true, schema: extractionSchema(fields) } } })
  }) as { status?: string; output?: { content?: { type?: string; text?: string }[] }[] };
  if (raw.status !== "completed" || !Array.isArray(raw.output)) throw new ApiError(502, "INCOMPLETE_EXTRACTION", "Extraction did not finish. Try a clearer image or a shorter description.");
  if (raw.output.some(item => item.content?.some(part => part.type === "refusal"))) throw new ApiError(422, "EXTRACTION_REFUSED", "This input could not be analysed. Try another product image or description.");
  const texts = raw.output.flatMap(item => (item.content || []).filter(part => part.type === "output_text" && typeof part.text === "string").map(part => part.text!));
  let parsed: unknown;
  try { parsed = JSON.parse(texts.join("")); } catch { throw new ApiError(502, "INVALID_MODEL_OUTPUT", "The extractor returned unreadable traits."); }
  return { provider: "openai", model, ...validateExtractionOutput(parsed, fields) };
}

export async function handleExtractTraits(request: Request, dependencies: Dependencies = {}): Promise<Response> {
  let acquired = false;
  try {
    const origin = request.headers.get("origin");
    if (origin && origin !== new URL(request.url).origin) throw new ApiError(403, "INVALID_ORIGIN", "Use the extractor from this workspace.");
    const input = await readExtractionInput(request);
    if (inFlight >= 2) throw new ApiError(429, "EXTRACTOR_BUSY", "Two extractions are already running. Try again shortly.");
    inFlight++; acquired = true;
    const fields = dependencies.fields || (await loadSnapshot()).fields;
    const settings = dependencies.settings || { provider: process.env.TRAIT_EXTRACTOR_PROVIDER, apiKey: process.env.OPENAI_API_KEY, model: process.env.OPENAI_EXTRACTION_MODEL, bridgeUrl: process.env.CODEX_EXTRACTOR_URL, bridgeToken: process.env.CODEX_EXTRACTOR_TOKEN };
    return response(await extractWithProvider(input, fields, settings, dependencies.fetch));
  } catch (error) {
    const timedOut = error instanceof Error && ["TimeoutError", "AbortError"].includes(error.name);
    const code = error instanceof ApiError ? error.code : timedOut ? "EXTRACTOR_TIMEOUT" : "EXTRACTOR_UNAVAILABLE";
    const message = error instanceof ApiError ? error.message : timedOut ? "Extraction timed out. Try a simpler input or check that the local laptop is awake." : "The extraction service could not be reached.";
    return response({ error: { code, message } }, error instanceof ApiError ? error.status : timedOut ? 504 : 502);
  } finally { if (acquired) inFlight--; }
}
