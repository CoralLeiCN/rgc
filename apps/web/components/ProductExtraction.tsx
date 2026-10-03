"use client";

import { useEffect, useRef, useState } from "react";
import type { FieldDefinition } from "../lib/contracts";
import { MAX_DESCRIPTION_LENGTH, MAX_EXTRACTION_IMAGES, type ExtractionRequest, type ExtractionResponse } from "../lib/extraction-contract";
import { applyExtractedTraits, type ProductDraft } from "../lib/client/product-draft";
import { encodeExtractionImage, prepareExtractionImage, type PreparedImage } from "../lib/client/extraction-images";
import { humanize } from "../lib/client/display";
import { HelpTip } from "./HelpTip";
import { Icon } from "./Icons";

interface Props { fields: FieldDefinition[]; draft: ProductDraft; onChange: (draft: ProductDraft) => void; }

const examplePhotos = [
  { url: "/examples/well-and-truly/front.jpg", name: "Well&Truly front.jpg", label: "Front of Well&Truly Fudge & Brownie chocolate" },
  { url: "/examples/well-and-truly/back.jpg", name: "Well&Truly back.jpg", label: "Back of Well&Truly chocolate with ingredients and nutrition" },
];

export function ProductExtraction({ fields, draft, onChange }: Props) {
  const [description, setDescription] = useState("");
  const [images, setImages] = useState<PreparedImage[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [preparing, setPreparing] = useState(false);
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const imageInput = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const urls = images.map(image => URL.createObjectURL(image.file));
    setPreviews(urls);
    return () => urls.forEach(url => URL.revokeObjectURL(url));
  }, [images]);
  useEffect(() => () => { generation.current++; request.current?.abort(); }, []);

  function invalidate() {
    generation.current++;
    request.current?.abort(); request.current = null;
    setLoading(false); setPreparing(false); setResult(null); setChosen([]); setError(""); setNotice("");
  }
  async function selectImages(files: File[]) {
    if (!files.length) return;
    invalidate();
    const existing = images.length === MAX_EXTRACTION_IMAGES ? [] : images;
    if (existing.length + files.length > MAX_EXTRACTION_IMAGES) {
      setError("Use up to two photos of the same product. Remove a photo before adding another.");
      return;
    }
    const token = generation.current;
    setPreparing(true);
    try {
      const prepared: PreparedImage[] = [];
      for (const file of files) prepared.push(await prepareExtractionImage(file));
      if (token !== generation.current) return;
      setImages([...existing, ...prepared]);
    } catch (cause) {
      if (token === generation.current) setError(cause instanceof Error ? cause.message : "Could not prepare the photos. Try again.");
    } finally {
      if (token === generation.current) setPreparing(false);
    }
  }
  async function selectExample() {
    invalidate();
    const token = generation.current;
    const controller = new AbortController(); request.current = controller;
    setPreparing(true);
    try {
      const prepared: PreparedImage[] = [];
      for (const photo of examplePhotos) {
        const response = await fetch(photo.url, { signal: controller.signal });
        if (!response.ok) throw new Error("The example photos could not be loaded. Try again or upload your own.");
        const file = new File([await response.blob()], photo.name, { type: "image/jpeg" });
        prepared.push(await prepareExtractionImage(file));
        if (token !== generation.current) return;
      }
      setImages(prepared); setDescription("");
      setNotice("Example photos loaded. Press Extract traits to read the packaging.");
    } catch (cause) {
      if (!controller.signal.aborted && token === generation.current) setError(cause instanceof Error ? cause.message : "Could not load the example photos.");
    } finally {
      if (token === generation.current) { setPreparing(false); request.current = null; }
    }
  }
  async function extract() {
    if (loading || preparing || (!description.trim() && !images.length)) return;
    invalidate();
    if (description.length > MAX_DESCRIPTION_LENGTH) { setError("Keep the description within 12,000 characters."); return; }
    const token = generation.current;
    const controller = new AbortController(); request.current = controller;
    setLoading(true);
    try {
      const body: ExtractionRequest = { description: description.trim() };
      body.images = await Promise.all(images.map(async ({ file }) => ({ mimeType: file.type, data: await encodeExtractionImage(file) })));
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
    <div className="heading-with-help"><h3 id="config-extraction-title">Start with a product</h3><HelpTip label="About extracting product traits"><p>Choose the example or add up to two photos of your product, such as the front and back. You can also add a description. Photos are resized in your browser when needed. Press Extract traits to send these inputs to the configured model provider, then review the values and evidence before applying them.</p><p>Applying selected candidates replaces matching draft inputs, including name or edible weight when present. Other edits and pack price stay unchanged. Traits calculate the prototype score only after you apply them. Images and descriptions stay in this local form until you request extraction; the app does not save them to the collection.</p></HelpTip></div>
    <div className="config-example">
      <div className="config-example-photos">{examplePhotos.map(photo => <img key={photo.url} src={photo.url} alt={photo.label} loading="lazy" />)}</div>
      <div><span className="config-example-label">Try an example</span><strong>Well&amp;Truly</strong><span>Fudge &amp; Brownie · 30 g</span><button type="button" className="text-button" disabled={preparing} onClick={selectExample}>Use example photos</button></div>
    </div>
    <label className="config-extract-label" htmlFor="config-product-description">Product description</label>
    <textarea id="config-product-description" rows={3} disabled={preparing} maxLength={MAX_DESCRIPTION_LENGTH} value={description} placeholder="Paste the packaging text or describe the product…" onChange={event => { invalidate(); setDescription(event.target.value); }} />
    <div className="config-extract-inputs"><label className={`config-image-upload${preparing ? " is-disabled" : ""}`} htmlFor="config-product-image"><Icon name="plus" size={13} />{images.length === MAX_EXTRACTION_IMAGES ? "Replace photos" : "Upload your photos"}</label><span>Up to 2 photos · PNG / JPEG / WebP · 20 MiB each</span></div>
    <input className="sr-only" id="config-product-image" ref={imageInput} type="file" multiple disabled={preparing} accept="image/png,image/jpeg,image/webp" aria-describedby="config-image-guidance" onChange={event => { const files = Array.from(event.target.files ?? []); event.target.value = ""; void selectImages(files); }} />
    <span className="sr-only" id="config-image-guidance">Up to two PNG, JPEG or WebP photos of one product, up to 20 MiB and 40 megapixels each. Large photos are resized automatically. When two photos are selected, a new upload replaces them.</span>
    {images.map((image, index) => <div className="config-image-preview" key={`${index}-${image.originalName}`}>{previews[index] && <img src={previews[index]} alt={`Selected packaging photo ${index + 1}`} />}<span title={image.originalName}>{image.originalName}{image.resized && <small>Resized for upload</small>}</span><button type="button" aria-label={`Remove photo ${index + 1}: ${image.originalName}`} onClick={() => { invalidate(); setImages(current => current.filter((_, item) => item !== index)); }}><Icon name="close" size={13} /></button></div>)}
    <div className="config-extract-actions"><button type="button" className="button" disabled={loading || preparing || (!description.trim() && !images.length)} onClick={extract}><Icon name={loading ? "refresh" : "layers"} size={13} />{loading ? "Extracting…" : "Extract traits"}</button>{(loading || preparing) && <button type="button" className="text-button" onClick={invalidate}>Cancel</button>}</div>
    {preparing && <p className="config-extract-status" role="status">Preparing photos…</p>}
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
