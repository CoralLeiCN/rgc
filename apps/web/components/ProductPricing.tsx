"use client";

import { useEffect, useRef, useState } from "react";
import type { FieldDefinition } from "../lib/contracts";
import { money, humanize } from "../lib/client/display";
import type { ProductDraft } from "../lib/client/product-draft";
import { PRICING_FIELDS, type PricingResult } from "../lib/pricing-contract";
import { HelpTip } from "./HelpTip";

const signedMoney = (value: number) => `${value < 0 ? "−" : "+"}${money(Math.abs(value))}`;
const percent = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
const familyLabel = (key: string) => key === "selling_context" ? "Selling context" : humanize(key);

export function ProductPricing({ draft, fields, onChange }: { draft: ProductDraft; fields: FieldDefinition[]; onChange: (draft: ProductDraft) => void }) {
  const [scopeConfirmed, setScopeConfirmed] = useState(false);
  const [stored, setStored] = useState<{ key: string; prediction: PricingResult } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const type = draft.values["composition.chocolate_type"] || "";
  const retailer = draft.values["identity.retailer"] || "";
  const recipe = draft.pricing?.recipeClass || "";
  // Legacy "absent" is not evidence of explicit absence under this model policy.
  const nuts = draft.pricing?.nutsPresence || (draft.values["composition.nuts_presence"] === "present" ? "present" : "");
  const input = { scope: scopeConfirmed ? "single_pack_chocolate_bar" : "", "quantity.total_edible_weight_g": draft.weightGrams.trim() ? Number(draft.weightGrams) : null,
    "composition.chocolate_type": type, "composition.recipe_class": recipe, "composition.nuts_presence": nuts, "identity.retailer": retailer };
  const inputKey = JSON.stringify(input);
  const currentKey = useRef(inputKey); currentKey.current = inputKey;
  const prediction = stored?.key === inputKey ? stored.prediction : null;
  const excluded = fields.filter(field => !PRICING_FIELDS.some(modeled => modeled.key === field.key));
  useEffect(() => {
    request.current?.abort(); setLoading(false); setError(""); setStored(null);
    return () => { request.current?.abort(); };
  }, [inputKey]);
  const updateTrait = (key: string, value: string) => onChange({ ...draft, values: { ...draft.values, [key]: value } });
  const updatePricing = (key: "recipeClass" | "nutsPresence", value: string) => onChange({ ...draft, pricing: { ...draft.pricing, [key]: value } });
  async function predict() {
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    const key = inputKey; setLoading(true); setError(""); setStored(null);
    try {
      const response = await fetch("/api/predict-price", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal: controller.signal });
      const payload = await response.json();
      if (controller.signal.aborted || currentKey.current !== key) return;
      if (!response.ok) throw new Error(payload?.error?.message || "Price prediction is unavailable.");
      if (payload.fixture !== true || payload.releaseReady !== false || !Array.isArray(payload.attributions) || !Number.isFinite(payload.packGbp)) throw new Error("The pricing result could not be verified.");
      setStored({ key, prediction: payload as PricingResult });
    } catch (cause) {
      if (!controller.signal.aborted && currentKey.current === key) setError(cause instanceof Error ? cause.message : "Price prediction is unavailable.");
    } finally {
      if (!controller.signal.aborted && currentKey.current === key) setLoading(false);
    }
  }
  const ready = scopeConfirmed && type && retailer && recipe && nuts && input["quantity.total_edible_weight_g"] !== null;

  return <section className="config-pricing" aria-labelledby="config-pricing-title">
    <div className="heading-with-help"><h3 id="config-pricing-title">Predict a price</h3><HelpTip label="About the synthetic pricing demo"><p>This LightGBM model was trained on generated test data. Its prices and SHAP contributions illustrate the prediction workflow. Accuracy on real products has not been established.</p><p>The model accepts five fields for a single standard chocolate bar pack: 50–150 g, dark/milk/white, plain/inclusion/filled, nuts evidence and Waitrose/Ocado. Proposed price is excluded from prediction. Extraction and other trait inputs are available separately.</p><p>The historical fixture uses regular-consumer-price-1. It retains that basis; it has no validated current-market prediction interval.</p></HelpTip></div>
    <p className="pricing-disclosure">Trained on generated test data. These estimates are illustrative.</p>
    <label className="pricing-scope"><input type="checkbox" checked={scopeConfirmed} onChange={event => setScopeConfirmed(event.target.checked)} /><span>This is one standard chocolate bar pack.</span></label>
    <p className="pricing-weight">Uses edible weight above: {draft.weightGrams || "Unspecified"} g · supported range 50–150 g</p>
    <div className="pricing-inputs">
      <label htmlFor="pricing-type">Chocolate type<select id="pricing-type" value={type} onChange={event => updateTrait("composition.chocolate_type", event.target.value)}><option value="">Choose type</option>{type && !["dark", "milk", "white"].includes(type) && <option value={type}>{humanize(type)} · unsupported</option>}{["dark", "milk", "white"].map(value => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
      <label htmlFor="pricing-retailer">Retailer<select id="pricing-retailer" value={retailer} onChange={event => updateTrait("identity.retailer", event.target.value)}><option value="">Choose retailer</option>{retailer && !["Waitrose", "Ocado"].includes(retailer) && <option value={retailer}>{retailer} · unsupported</option>}{["Waitrose", "Ocado"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <label htmlFor="pricing-recipe">Recipe class<select id="pricing-recipe" value={recipe} onChange={event => updatePricing("recipeClass", event.target.value)}><option value="">Choose recipe</option>{["plain", "inclusion", "filled"].map(value => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
      <label htmlFor="pricing-nuts">Nuts as ingredients<select id="pricing-nuts" value={nuts} onChange={event => updatePricing("nutsPresence", event.target.value)}><option value="">Review nuts evidence</option><option value="present">Present</option><option value="explicitly_absent">Explicitly absent</option><option value="unknown">Unknown</option></select></label>
    </div>
    <button className="button" type="button" disabled={!ready || loading} onClick={predict}>{loading ? "Predicting…" : "Predict demo price"}</button>
    {loading && <p className="config-extract-status" role="status">Calculating the price and SHAP contributions…</p>}
    {error && <p className="config-input-error" role="alert">{error}</p>}
    {prediction && <div className="pricing-result" aria-live="polite">
      <div className="pricing-estimate"><span>Predicted demo pack price</span><output>{money(prediction.packGbp)}</output><small>{money(prediction.unitGbp)} /100 g</small></div>
      <p className="pricing-disclosure">No interval validated on real products is available.</p>
      <div className="heading-with-help"><h4>What contributes to this price?</h4><HelpTip label="About price contributions"><p>Raw SHAP values add up in log GBP per 100 g. The displayed pounds and percentages allocate the difference from the model reference proportionally through the exponential transformation. They describe this model prediction; they do not establish ingredient costs or effects of changing a trait.</p><p>The reference and all signed contributions add up to the predicted pack price, and their unrounded percentages add up to 100%. Display rounding can change totals. Negative contributions and a reference above 100% are valid.</p><p>SHAP is computed exactly using stored tree path counts, with no background sample or approximation, and checked against native LightGBM 4.6.0.</p></HelpTip></div>
      <div className="pricing-table-scroll" tabIndex={0} aria-label="Model reference and field price allocations"><table className="pricing-contributions"><caption>Allocation of the predicted demo pack price</caption><thead><tr><th>Field</th><th>£ / pack</th><th>Share</th></tr></thead><tbody>
        <tr><th scope="row">Model reference</th><td>{money(prediction.referencePackGbp)}</td><td>{prediction.referencePercent.toFixed(1)}%</td></tr>
        {prediction.attributions.map(field => <tr key={field.key}><th scope="row">{field.label}<small>{field.key === "quantity.total_edible_weight_g" ? `${field.value} g` : humanize(String(field.value))}</small></th><td className={field.packGbp < 0 ? "pricing-negative" : "pricing-positive"}>{signedMoney(field.packGbp)}</td><td>{percent(field.percent)}</td></tr>)}
        <tr className="pricing-total"><th scope="row">Predicted price</th><td>{money(prediction.packGbp)}</td><td>100%</td></tr>
      </tbody></table></div>
      <details className="pricing-details"><summary>Family contributions</summary><dl>{prediction.families.map(family => <div key={family.key}><dt>{familyLabel(family.key)}</dt><dd>{percent(family.percent)}</dd></div>)}</dl></details>
      <details className="pricing-details"><summary>Raw SHAP values</summary><dl><div><dt>Reference · log £/100 g</dt><dd>{prediction.referenceLog.toFixed(6)}</dd></div>{prediction.attributions.map(field => <div key={field.key}><dt>{field.label}</dt><dd>{field.shapLog.toFixed(6)}</dd></div>)}<div><dt>Prediction · log £/100 g</dt><dd>{prediction.predictedLog.toFixed(6)}</dd></div></dl><p>{prediction.treeCount} trees · smallest reached leaf: {prediction.minimumLeafFamilies} synthetic families</p></details>
      <details className="pricing-details"><summary>{excluded.length} schema fields not modeled</summary><p>{excluded.map(field => field.label).join(", ")}. These fields have no SHAP contribution in this model.</p></details>
      <p className="pricing-provenance">LightGBM without brand · <a href={`https://huggingface.co/datasets/CoralLeiCN/rgc-collections/tree/${prediction.revision}/model/lightgbm_without_brand/fixtures/${prediction.runId}`} target="_blank" rel="noreferrer">Synthetic model source</a></p>
    </div>}
  </section>;
}
