import "server-only";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import reference from "../../pricing-model.json";
import { createPricingEngine, type FixtureModel, type PricingEngine } from "./pricing-core";

let cached: Promise<PricingEngine> | undefined;
export function loadPricingEngine(): Promise<PricingEngine> {
  if (!cached) cached = (async () => {
    const files = await Promise.all(Object.entries(reference.files).map(async ([name, entry]) => {
      const bytes = await readFile(path.join(process.cwd(), "model-cache", name));
      if (bytes.length !== entry.byteLength || createHash("sha256").update(bytes).digest("hex") !== entry.sha256) throw new Error("Pricing model integrity mismatch");
      return [name, JSON.parse(bytes.toString("utf8"))] as const;
    }));
    const contents = Object.fromEntries(files);
    const model = contents["model.json"] as FixtureModel;
    const manifest = contents["manifest.json"];
    if (manifest.run_id !== reference.runId || manifest.fixture !== true || manifest.model_id !== reference.modelId
        || manifest.managed_files["model.json"].sha256 !== reference.files["model.json"].sha256
        || createHash("sha256").update(JSON.stringify(model.booster)).digest("hex") !== model.booster_sha256) throw new Error("Pricing model identity mismatch");
    return createPricingEngine(model);
  })().catch(error => { cached = undefined; throw error; });
  return cached;
}
export const pricingIdentity = { runId: reference.runId, revision: reference.revision };
