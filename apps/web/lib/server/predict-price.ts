import { predictPrice } from "./pricing-core";
import { loadPricingEngine, pricingIdentity } from "./pricing-model";

const response = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

export async function handlePredictPrice(request: Request): Promise<Response> {
  const origin = request.headers.get("origin");
  const url = new URL(request.url);
  const expectedOrigin = `${url.protocol}//${request.headers.get("host") || url.host}`;
  if (origin && origin !== expectedOrigin) return response({ error: { code: "INVALID_ORIGIN", message: "Use price prediction from this workspace." } }, 403);
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") return response({ error: { code: "INVALID_INPUT", message: "Supply product inputs as JSON." } }, 400);
  let input: unknown;
  try {
    const reader = request.body?.getReader();
    if (!reader) throw new Error("Empty input");
    const chunks: Uint8Array[] = []; let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > 4096) { await reader.cancel(); return response({ error: { code: "INPUT_TOO_LARGE", message: "Product inputs exceed the size limit." } }, 413); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch { return response({ error: { code: "INVALID_INPUT", message: "Supply valid product inputs as JSON." } }, 400); }
  let engine;
  try { engine = await loadPricingEngine(); }
  catch { return response({ error: { code: "MODEL_UNAVAILABLE", message: "The synthetic pricing demo is unavailable. Its model files need verification." } }, 503); }
  try { return response(predictPrice(engine, input, pricingIdentity)); }
  catch (error) { return response({ error: { code: "UNSUPPORTED_PRODUCT", message: error instanceof Error ? error.message : "This product cannot be predicted." } }, 422); }
}
