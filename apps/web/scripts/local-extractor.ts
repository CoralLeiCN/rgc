import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { Readable } from "node:stream";
import type { Snapshot } from "../lib/contracts";
import { createLocalExtractor } from "../lib/local-codex";

async function main() {
  const port = Number(process.env.CODEX_EXTRACTOR_PORT ?? 8787);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("CODEX_EXTRACTOR_PORT must be a port from 1024 to 65535.");
  const snapshot = JSON.parse(await readFile(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;
  const extractor = createLocalExtractor({ token: process.env.CODEX_EXTRACTOR_TOKEN ?? "", fields: snapshot.fields });
  const server = createServer({ maxHeaderSize: 8192, requestTimeout: 30_000, headersTimeout: 10_000 }, async (incoming, outgoing) => {
    try {
      const request = new Request(`http://127.0.0.1:${port}${incoming.url ?? "/"}`, {
        method: incoming.method, headers: incoming.headers as Record<string, string>,
        ...(incoming.method === "POST" ? { body: Readable.toWeb(incoming) as ReadableStream<Uint8Array>, duplex: "half" } : {}),
      } as RequestInit);
      const response = await extractor.handle(request);
      outgoing.writeHead(response.status, Object.fromEntries(response.headers));
      outgoing.end(Buffer.from(await response.arrayBuffer()));
    } catch { if (!outgoing.headersSent) outgoing.writeHead(400, { "Content-Type": "application/json", "Cache-Control": "no-store" }); outgoing.end('{"error":{"code":"INVALID_REQUEST","message":"Invalid extraction request."}}'); }
  });
  server.keepAliveTimeout = 5_000;
  server.on("clientError", (_error, socket) => socket.end("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"));
  const shutdown = async () => {
    server.close(); server.closeAllConnections();
    await extractor.close();
  };
  process.once("SIGINT", shutdown); process.once("SIGTERM", shutdown);
  await new Promise<void>((resolve, reject) => { server.once("error", reject); server.listen(port, "127.0.0.1", resolve); });
  console.log(`Local extraction bridge listening at http://127.0.0.1:${port}/extract. Token required; no request data is logged.`);
}

main().catch(error => { console.error(error instanceof Error && /CODEX_EXTRACTOR_(TOKEN|PORT)/.test(error.message) ? error.message : "Local extraction bridge could not start."); process.exitCode = 1; });
