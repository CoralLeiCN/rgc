import type { JsonValue } from "./contracts";

export const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
export const MAX_TOTAL_IMAGE_BYTES = 2 * 1024 * 1024;
export const MAX_EXTRACTION_IMAGES = 2;
export const MAX_DESCRIPTION_LENGTH = 12_000;
export interface ExtractionImage { mimeType: string; data: string; }
export interface ExtractionRequest { description: string; images?: ExtractionImage[]; image?: ExtractionImage; }
export interface NormalizedExtractionRequest { description: string; images: ExtractionImage[]; }
export interface ExtractedTrait { key: string; value: JsonValue; evidence: string; }
export interface ExtractionResponse {
  provider: "openai" | "codex"; model: string;
  traits: ExtractedTrait[]; warnings: string[];
}
