import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Evidence, Product, Snapshot } from "../contracts";
import { ApiError } from "./errors";

const snapshotRoot = path.join(process.cwd(), "snapshot");
let snapshotPromise: Promise<Snapshot> | undefined;
const evidencePromises = new Map<string, Promise<Record<string, Evidence>>>();

/** Immutable deployment data is shared by requests in this function instance. */
export function loadSnapshot(): Promise<Snapshot> {
  if (!snapshotPromise) {
    snapshotPromise = readFile(path.join(snapshotRoot, "index.json"), "utf8")
      .then((raw) => JSON.parse(raw) as Snapshot)
      .catch((error: unknown) => { snapshotPromise = undefined; throw error; });
  }
  return snapshotPromise;
}

export function findProduct(snapshot: Snapshot, id: string): Product {
  const product = snapshot.products.find((entry) => entry.id === id);
  if (!product) throw new ApiError(404, "NOT_FOUND", "This listing is not in the deployed snapshot.");
  return product;
}

/** Source filenames come exclusively from the verified index, never query text. */
export async function loadEvidence(product: Product): Promise<Evidence> {
  if (!/^[a-z0-9-]+$/.test(product.source)) throw new Error("Invalid snapshot source key");
  let promise = evidencePromises.get(product.source);
  if (!promise) {
    promise = readFile(path.join(snapshotRoot, "evidence", `${product.source}.json`), "utf8")
      .then((raw) => JSON.parse(raw) as Record<string, Evidence>)
      .catch((error: unknown) => { evidencePromises.delete(product.source); throw error; });
    evidencePromises.set(product.source, promise);
  }
  const shard = await promise;
  if (!Object.hasOwn(shard, product.id)) throw new Error("Snapshot evidence is missing");
  return shard[product.id];
}
