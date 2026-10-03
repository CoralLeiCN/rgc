import { readFileSync } from "node:fs";
import { handlePredictPrice } from "../lib/server/predict-price";

const cases = JSON.parse(readFileSync(0, "utf8")) as { body: string; headers?: Record<string, string> }[];
async function main() {
  const results = [];
  for (const item of cases) {
    const response = await handlePredictPrice(new Request("http://localhost:3000/api/predict-price", {
      method: "POST", headers: item.headers || { "Content-Type": "application/json" }, body: item.body,
    }));
    results.push({ status: response.status, cacheControl: response.headers.get("cache-control"), body: await response.json() });
  }
  process.stdout.write(JSON.stringify(results));
}
void main();
