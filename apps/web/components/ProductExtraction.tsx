"use client";

import { useEffect, useRef, useState } from "react";
import type { FieldDefinition } from "../lib/contracts";
import { MAX_DESCRIPTION_LENGTH, MAX_IMAGE_BYTES, type ExtractionRequest, type ExtractionResponse } from "../lib/extraction-contract";
import { applyExtractedTraits, type ProductDraft } from "../lib/client/product-draft";
import { humanize } from "../lib/client/display";
import { HelpTip } from "./HelpTip";
import { Icon } from "./Icons";

interface Props { fields: FieldDefinition[]; draft: ProductDraft; onChange: (draft: ProductDraft) => void; }

const imageTypes = new Set(["image/png", "image/jpeg", "image/webp"]);

async function encodeImage(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 8192) binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  return btoa(binary);
}

export function ProductExtraction({ fields, draft, onChange }: Props) {
  const [description, setDescription] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const imageInput = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!image) { setPreview(null); return; }
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  useEffect(() => () => { generation.current++; request.current?.abort(); }, []);

  function invalidate() {
    generation.current++;
    request.current?.abort(); request.current = null;
    setLoading(false); setResult(null); setChosen([]); setError(""); setNotice("");
  }
  function selectImage(file: File | null) {
    invalidate();
    if (file && (!imageTypes.has(file.type) || file.size > MAX_IMAGE_BYTES)) {
      setImage(null);
      if (imageInput.current) imageInput.current.value = "";
      setError("Choose a PNG, JPEG or WebP image up to 2 MiB.");
      return;
    }
    setImage(file);
    if (!file && imageInput.current) imageInput.current.value = "";
  }
  async function extract() {
    if (loading || (!description.trim() && !image)) return;
    invalidate();
    if (description.length > MAX_DESCRIPTION_LENGTH) { setError("Keep the description within 12,000 characters."); return; }
    const token = generation.current;
    const controller = new AbortController(); request.current = controller;
    setLoading(true);
    try {
      const body: ExtractionRequest = { description: description.trim() };
      if (image) body.image = { mimeType: image.type, data: await encodeImage(image) };
      if (controller.signal.aborted || token !== generation.current) return;
      const response = await fetch("/api/extract-traits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal });
      const payload = await response.json().catch(() => null);
      if (controller.signal.aborted || token !== generation.current) return;
      if (!response.ok) {
        const message = typeof payload?.error?.message === "string" ? payload.error.message : response.status === 503 ? "Trait extraction is not configured. Connect the server to the Codex bridge or configure the OpenAI provider, then retry." : "Trait extraction failed. Please try again.";
        throw new Error(message);
      }
      if (!payload || !Array.isArray(payload.traits) || !Array.isArray(payload.warnings) || typeof payload.model !== "string" || !["openai", "codex"].includes(payload.provider)) throw new Error("The extraction service returned an unreadable response. Please try again.");
      const extracted = payload as ExtractionResponse;
      setResult(extracted); setChosen(extracted.traits.map(trait => trait.key));
    } catch (cause) {
      if (!controller.signal.aborted && token === generation.current) setError(cause instanceof Error ? cause.message : "Trait extraction failed. Please try again.");
    } finally {
      if (token === generation.current) { setLoading(false); request.current = null; }
    }
  }
  function apply() {
    if (!result || loading || !chosen.length) return;
    const candidates = result.traits.filter(trait => chosen.includes(trait.key));
    onChange(applyExtractedTraits(draft, candidates, fields));
    setNotice(`${candidates.length} reviewed trait${candidates.length === 1 ? "" : "s"} applied. Pack price unchanged.`);
    setResult(null); setChosen([]);
  }
  const fieldByKey = new Map(fields.map(field => [field.key, field]));

  return <section className="config-extraction" aria-labelledby="config-extraction-title">
    <div className="heading-with-help"><h3 id="config-extraction-title">Start with a product</h3><HelpTip label="About extracting product traits"><p>Add a product description, packaging image, or both. Press Extract traits to send these inputs to the configured model provider. Review the candidate values and supporting evidence before applying them.</p><p>Applying selected candidates replaces matching draft inputs, including name or edible weight when present. Other edits and pack price stay unchanged. Traits calculate the prototype score only after you apply them. Images and descriptions stay in this local form until you request extraction; the app does not save them to the collection.</p></HelpTip></div>
    <label className="config-extract-label" htmlFor="config-product-description">Product description</label>
    <textarea id="config-product-description" rows={3} maxLength={MAX_DESCRIPTION_LENGTH} value={description} placeholder="Paste the packaging text or describe the product…" onChange={event => { invalidate(); setDescription(event.target.value); }} />
    <div className="config-extract-inputs"><label className="config-image-upload" htmlFor="config-product-image"><Icon name="plus" size={13} />{image ? "Change image" : "Add packaging image"}</label><span>PNG / JPEG / WebP · 2 MiB</span></div>
    <input className="sr-only" id="config-product-image" ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" aria-describedby="config-image-guidance" onChange={event => selectImage(event.target.files?.[0] ?? null)} />
    <span className="sr-only" id="config-image-guidance">PNG, JPEG or WebP image up to 2 MiB.</span>
    {image && <div className="config-image-preview">{preview && <img src={preview} alt="Selected packaging preview" />}<span title={image.name}>{image.name}</span><button type="button" aria-label="Remove packaging image" onClick={() => selectImage(null)}><Icon name="close" size={13} /></button></div>}
    <div className="config-extract-actions"><button type="button" className="button" disabled={loading || (!description.trim() && !image)} onClick={extract}><Icon name={loading ? "refresh" : "layers"} size={13} />{loading ? "Extracting…" : "Extract traits"}</button>{loading && <button type="button" className="text-button" onClick={invalidate}>Cancel</button>}</div>
    {loading && <p className="config-extract-status" role="status">Reading product evidence…</p>}
    {error && <p className="config-extract-error" role="alert">{error}</p>}
    {notice && <p className="config-extract-status" role="status">{notice}</p>}
    {result && <div className="config-extract-review"><div className="config-review-heading"><h4>Review extracted traits</h4><span>{result.traits.length} candidates</span></div><p className="config-extract-provider">{result.provider === "codex" ? "Codex" : "OpenAI"} · {result.model}</p>{result.warnings.length > 0 && <div className="config-extract-warnings" role="status">{result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</div>}{result.traits.length === 0 ? <p className="config-extract-status">No supported traits found. Add clearer text or a readable packaging image.</p> : <><div className="config-candidate-list">{result.traits.map(trait => {
      const field = fieldByKey.get(trait.key);
      const value = Array.isArray(trait.value) ? trait.value.join(", ") : typeof trait.value === "boolean" ? trait.value ? "Yes" : "No" : String(trait.value);
      return <div className="config-candidate" key={trait.key}><label><input type="checkbox" checked={chosen.includes(trait.key)} onChange={event => setChosen(current => event.target.checked ? [...current, trait.key] : current.filter(key => key !== trait.key))} /><span><span>{field?.label ?? humanize(trait.key)}</span><strong>{value}</strong></span></label><HelpTip label={`Evidence for ${field?.label ?? trait.key}`}><p>{trait.evidence || "No evidence text was returned."}</p><p>Applying this candidate replaces the matching draft input.</p></HelpTip></div>;
    })}</div><div className="config-apply-row"><button type="button" className="button" onClick={apply} disabled={!chosen.length}>Apply extracted traits<span>{chosen.length}</span></button><HelpTip label="About applying extracted traits"><p>Apply only checked candidates. Matching draft values will be replaced; all other edits and pack price are preserved. Name and edible weight update their top inputs. The trait-derived score recalculates after applying.</p></HelpTip></div></>}</div>}
  </section>;
}
