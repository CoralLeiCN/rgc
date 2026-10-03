import { MAX_EXTRACTION_IMAGES, MAX_TOTAL_IMAGE_BYTES } from "../extraction-contract";

export const MAX_UPLOAD_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_IMAGE_EDGE = 2400;
const PREPARED_IMAGE_BYTES = Math.floor(MAX_TOTAL_IMAGE_BYTES / MAX_EXTRACTION_IMAGES);
const imageTypes = new Set(["image/png", "image/jpeg", "image/webp"]);

export interface PreparedImage { file: File; originalName: string; resized: boolean; }

/** Decode in the browser so orientation is respected and originals stay intact. */
export async function prepareExtractionImage(file: File): Promise<PreparedImage> {
  if (!imageTypes.has(file.type)) throw new Error("Choose PNG, JPEG or WebP photos.");
  if (!file.size || file.size > MAX_UPLOAD_IMAGE_BYTES) throw new Error("Choose photos up to 20 MiB each.");
  const url = URL.createObjectURL(file);
  const image = new Image();
  try {
    image.src = url;
    await image.decode().catch(() => { throw new Error(`Could not read ${file.name}. Choose another photo.`); });
    if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 40_000_000) throw new Error("Choose photos with at most 40 megapixels.");
    if (file.size <= PREPARED_IMAGE_BYTES && Math.max(image.naturalWidth, image.naturalHeight) <= MAX_IMAGE_EDGE) return { file, originalName: file.name, resized: false };

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) throw new Error("This browser could not prepare the photo. Try a smaller image.");
    let scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
    for (let attempt = 0; attempt < 5; attempt++) {
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      context.fillStyle = "#fff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      for (const quality of [0.9, 0.8, 0.7]) {
        const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, "image/jpeg", quality));
        if (blob && blob.size <= PREPARED_IMAGE_BYTES) {
          const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
          return { file: new File([blob], name, { type: "image/jpeg" }), originalName: file.name, resized: true };
        }
      }
      scale *= 0.8;
    }
    throw new Error(`Could not resize ${file.name} for upload. Try a smaller photo.`);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function encodeExtractionImage(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 8192) binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  return btoa(binary);
}
