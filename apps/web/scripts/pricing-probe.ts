/** Batch probe for cross-runtime validation against native LightGBM. */
import { readFileSync } from "node:fs";
import { createPricingEngine, predictPrice } from "../lib/server/pricing-core";
import reference from "../pricing-model.json";

const engine = createPricingEngine(JSON.parse(readFileSync(new URL("../model-cache/model.json", import.meta.url), "utf8")));
const inputs = JSON.parse(readFileSync(0, "utf8")) as unknown[];
process.stdout.write(JSON.stringify(inputs.map(input => {
  try { return predictPrice(engine, input, { runId: reference.runId, revision: reference.revision }); }
  catch (error) { return { error: error instanceof Error ? error.message : "Unavailable" }; }
})));
