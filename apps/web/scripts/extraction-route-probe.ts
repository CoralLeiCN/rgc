import { readFileSync } from "node:fs";
import { handleExtractTraits } from "../lib/server/extract-traits";

const cases = JSON.parse(readFileSync(0, "utf8")) as { headers: Record<string, string> }[];
async function main() {
  const results = [];
  for (const item of cases) {
    let providerCalls = 0;
    const response = await handleExtractTraits(new Request("http://localhost:3000/api/extract-traits", {
      method: "POST", headers: { "Content-Type": "application/json", ...item.headers },
      body: JSON.stringify({ description: "Test packaging", images: [{ mimeType: "image/jpeg", data: "/9j/" }] }),
    }), {
      fields: [], settings: { provider: "codex", bridgeUrl: "https://extractor.test/extract", bridgeToken: "x".repeat(32) },
      fetch: async () => {
        providerCalls++;
        return Response.json({ traits: [], warnings: [] });
      },
    });
    results.push({ status: response.status, providerCalls, body: await response.json() });
  }
  process.stdout.write(JSON.stringify(results));
}
void main();
