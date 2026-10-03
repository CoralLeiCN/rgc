import { readFileSync } from "node:fs";
import { allocatePrice } from "../lib/server/pricing-core";

const inputs = JSON.parse(readFileSync(0, "utf8")) as { reference: number; contributions: number[]; raw: number }[];
process.stdout.write(JSON.stringify(inputs.map(input => {
  try { return allocatePrice(input.reference, input.contributions, input.raw); }
  catch (error) { return { error: error instanceof Error ? error.message : "Unavailable" }; }
})));
