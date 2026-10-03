"use client";

import type { Coverage, EvidenceAttribute, FieldDefinition, JsonValue, ProductResponse, SchemaResponse } from "../lib/contracts";
import { attribute, attributeLabel, dateLabel, humanize, money, number, unitLabel, unitPrice, valueLabel } from "../lib/client/display";
import { ErrorState, Icon, Loading } from "./Icons";
import { TraitSelect } from "./CohortBuilder";
import { HelpTip } from "./HelpTip";

interface Props {
  schema: SchemaResponse; data: ProductResponse | null; loading: boolean; error: string | null; onRetry: () => void;
  fieldKey: string; onField: (key: string) => void; pinned: string[]; onPin: (key: string) => void;
  compared: string[]; onCompare: (id: string) => void; coverage?: Coverage;
}

function JsonEvidence({ value }: { value: JsonValue }) {
  if (value === null || value === "" || Array.isArray(value) && value.length === 0) return <p className="subtle">No source reference is available for this trait.</p>;
  const items = Array.isArray(value) ? value : [value];
  return <div className="source-references">{items.map((item, index) => {
    if (item !== null && typeof item === "object" && !Array.isArray(item)) {
      return <div className="source-reference" key={index}>{Object.entries(item).map(([key, content]) => <div key={key}><span>{humanize(key)}</span><code>{valueLabel(content)}</code></div>)}</div>;
    }
    return <p key={index}>{valueLabel(item)}</p>;
  })}</div>;
}

function FieldDefinitionCard({ field, coverage, pinned, onPin }: { field: FieldDefinition; coverage?: Coverage; pinned: boolean; onPin: () => void }) {
  const segments = [
    { key: "known" as const, label: "Known", className: "known" }, { key: "unknown" as const, label: "Unknown", className: "unknown" },
    { key: "conflict" as const, label: "Conflict", className: "conflict" }, { key: "not_applicable" as const, label: "Not applicable", className: "not-applicable" }
  ];
  return <div className="field-definition"><div className="compact-heading-note"><span>Trait definition</span><HelpTip label={`About ${field.label.toLowerCase()}`}><p>{field.description}</p><p>{field.numeric ? `Allowed range: ${field.minimum ?? "no minimum"} to ${field.maximum ?? "no maximum"} ${unitLabel(field.unit)}.` : field.allowedValues.length ? `Allowed values: ${field.allowedValues.map(item => humanize(String(item))).join(", ")}.` : "Source text; unknown is a distinct evidence state."}</p>{field.qualifier && <p>{field.qualifier}</p>}<p>{field.modelSelected ? "Selected in the current pricing design. Populated values still need the published review and eligibility checks." : "Tracked by the schema; not selected in the current pricing design."}</p><p>Default scope: {field.scope || "unspecified"}. The value’s actual scope is shown with its evidence.</p>{coverage && <p>{number(coverage.known)} known · {number(coverage.unknown)} unknown · {number(coverage.conflict)} conflicts · {number(coverage.not_applicable)} not applicable · {number(coverage.reviewed)} reviewed across {number(coverage.total)} matching listings.</p>}</HelpTip></div><div className="field-definition-tags"><span>{humanize(field.type)}</span>{field.unit && <span>{unitLabel(field.unit)}</span>}{field.modelSelected && <span className="pricing-input">Pricing input</span>}</div>
    {coverage && <div className="field-coverage"><div className="coverage-track" role="img" aria-label={segments.map(segment => `${coverage[segment.key]} ${segment.label.toLowerCase()}`).join(", ")}>{segments.map(segment => <span key={segment.key} className={segment.className} style={{ width: `${coverage.total ? coverage[segment.key] / coverage.total * 100 : 0}%` }} />)}</div><div className="coverage-labels"><span><strong>{number(coverage.known)}</strong> known in cohort</span><span>{number(coverage.unknown)} unknown</span></div></div>}
    <button className={`text-button pin-trait ${pinned ? "pinned" : ""}`} onClick={onPin} aria-pressed={pinned}><Icon name="pin" size={13} />{pinned ? "Pinned to trait matrix" : "Pin trait to matrix"}</button>
  </div>;
}

function reviewRequirements(price: Record<string, JsonValue> | undefined) {
  const codes = Array.isArray(price?.exclusion_reasons) ? price.exclusion_reasons.filter((code): code is string => typeof code === "string") : [];
  const groups = [
    ["category_scope", "Confirm a comparable category scope."], ["physical_identity", "Review product and family identity."],
    ["observation_edible_quantity", "Validate this observation’s edible pack weight."], ["currency_or_tax", "Confirm currency and consumer tax basis."],
    ["regular_price", "Establish regular-price and promotion context."], ["observation_time", "Verify observation timing and availability."],
    ["cocoa_percentage", "Confirm the stated cocoa percentage’s meaning."], ["model_predictor", "Review the pricing inputs and their context."]
  ];
  return [...groups.filter(([prefix]) => codes.some(code => code.startsWith(prefix))).map(([, label]) => label), ...codes.filter(code => !groups.some(([prefix]) => code.startsWith(prefix))).map(humanize)];
}

export function EvidencePanel({ schema, data, loading, error, onRetry, fieldKey, onField, pinned, onPin, compared, onCompare, coverage }: Props) {
  const field = schema.fields.find(item => item.key === fieldKey) || schema.fields[0];
  const product = data?.product;
  const details = data?.evidence;
  const evidenceField: EvidenceAttribute | undefined = details?.attributes[field.key];
  const shownField = evidenceField || (product ? attribute(product, field.key) : null);
  const price = product ? unitPrice(product) : null;
  const latest = product?.prices[0];
  const shortlisted = product ? compared.includes(product.id) : false;
  const requirements = reviewRequirements(details?.prices[0]);
  const reviewStatus = evidenceField?.review_status || (shownField && "reviewStatus" in shownField ? shownField.reviewStatus : "unreviewed");
  const snapshotUrl = `https://huggingface.co/datasets/${schema.meta.repository}/tree/${schema.meta.revision}/${schema.meta.snapshotPrefix}`;

  return <aside id="evidence" className="evidence-panel panel" aria-labelledby="evidence-title">
    <div className="evidence-heading"><p className="eyebrow"><span className="section-index">↗</span> EVIDENCE INSPECTOR<HelpTip label="About source evidence"><p>Select a listing in the matrix or shortlist to inspect its observed price, traits and preserved source references.</p><p>These records come from the pinned collection snapshot. Populated traits and observed prices retain their own review status; they are independent of the chart’s demo pricing score.</p></HelpTip></p><span className="live-dot" title="Pinned collection snapshot" /></div>
    {loading && <Loading text="Loading listing and source evidence…" />}
    {error && <ErrorState message={error} onRetry={onRetry} />}
    {!loading && !error && !product && <div className="empty-inspector"><Icon name="grid" size={34} /><h2 id="evidence-title">Select a listing.</h2></div>}
    {product && <>
      <div className="selected-product"><div className="source-line"><i className={`seller-dot ${product.role}`} />{product.source}<span>{product.role === "unknown" ? "Role unknown" : product.role === "retail" ? "Retailer" : "Brand"}</span></div><h2 id="evidence-title">{product.name}</h2><p className="product-id">{product.id}</p>
        <button className={`button compare-product ${shortlisted ? "is-added" : ""}`} onClick={() => onCompare(product.id)} disabled={!shortlisted && compared.length >= 4} aria-pressed={shortlisted}><Icon name={shortlisted ? "check" : "plus"} size={15} />{shortlisted ? "Added to comparison" : "Add to comparison"}<span>{compared.length}/4</span></button>
      </div>
      <div className="price-card"><div><span className="eyebrow">OBSERVED UNIT PRICE<HelpTip label="About this observed price"><p>Unit prices use GBP and the edible pack weight recorded with the same observation. Regular-price, tax and promotion context remain subject to review.</p><p>{product.latestPriceConflict ? "Same-time observations disagree, so this listing has no single headline price." : latest ? "The latest dated observation is selected; undated observations rank last." : "No price observation is linked to this listing. Trait evidence remains available."}</p></HelpTip></span><span className="tag muted">Unreviewed context</span></div><p className={`headline-price ${price === null ? "no-price" : ""}`}>{price === null ? product.latestPriceConflict ? "Price conflict" : "Unavailable" : money(price)}{price !== null && <span>/ 100 g</span>}</p>{latest && !product.latestPriceConflict && <p>{`${latest.displayed_price === null ? "Unknown pack price" : `${latest.displayed_price.toFixed(2)} ${latest.currency || "currency unknown"}`} · ${latest.total_edible_weight_g === null ? "weight unknown" : `${latest.total_edible_weight_g} g observed weight`}`}</p>}<p className="observation-date">{latest ? `${dateLabel(latest.observed_at)} · ${product.prices.length} observation${product.prices.length === 1 ? "" : "s"}` : "0 observations"}</p></div>
      <div className="listing-coverage"><p><span className="label-with-help">Known product traits<HelpTip label="About evidence coverage"><p>Known traits have a supported source value. Unknown, conflicting and not-applicable states remain distinct.</p><p>Coverage describes completeness, not confidence or the demo pricing score.</p></HelpTip></span><strong>{product.known}<span> / {schema.fields.length}</span></strong></p><div className="coverage-track"><span className="known" style={{ width: `${product.known / schema.fields.length * 100}%` }} /></div>{product.conflicts > 0 && <small>{product.conflicts} conflicting traits</small>}</div>
    </>}
    <div className="trait-inspector"><label htmlFor="inspect-trait" className="eyebrow">INSPECT A PRODUCT TRAIT</label><TraitSelect id="inspect-trait" fields={schema.fields} value={field.key} onChange={onField} /><FieldDefinitionCard field={field} coverage={coverage} pinned={pinned.includes(field.key)} onPin={() => onPin(field.key)} />
      {product && shownField && <div className={`evidence-value ${shownField.status}`}><div className="evidence-state"><span><i className="state-dot" />{humanize(shownField.status)}</span><span>{humanize(reviewStatus)}</span></div><p className="extracted-value">{attributeLabel(shownField)}</p><p className="extraction-context">{shownField.scope ? `${shownField.scope} scope` : "Scope unspecified"}{evidenceField?.method ? ` · ${humanize(valueLabel(evidenceField.method))}` : ""}</p>{shownField.qualifier && <p className="evidence-qualifier">{shownField.qualifier}</p>}<details className="source-evidence"><summary>Source evidence references</summary><JsonEvidence value={evidenceField?.evidence ?? null} /></details></div>}
    </div>
    {product && details && <div className="listing-details"><div className="compact-heading-note section-help-heading"><span><i className="readiness-dot" />{latest?.model_eligible ? "Model input eligible" : "Review required"}</span><HelpTip label="About model readiness"><p>{latest?.model_eligible ? "The dataset marks this observation eligible. A fitted pricing benchmark is not connected to this workspace." : "This observation has not passed the dataset’s modeling checks."}</p>{requirements.length > 0 && <ul>{requirements.map(requirement => <li key={requirement}>{requirement}</li>)}</ul>}</HelpTip></div><details><summary>Price observation history <span className="count-badge">{details.prices.length}</span></summary>{details.prices.length ? details.prices.map((observation, index) => <div className="price-history" key={String(observation.observation_id || index)}><strong>{typeof observation.displayed_price === "number" ? observation.displayed_price.toFixed(2) : "Unknown price"} {typeof observation.currency === "string" ? observation.currency : ""}</strong><span>{dateLabel(typeof observation.observed_at === "string" ? observation.observed_at : null)}</span><dl>{["total_edible_weight_g", "quantity_status", "tax_basis", "promotion_status", "model_eligible"].filter(key => observation[key] !== undefined).map(key => <div key={key}><dt>{humanize(key)}</dt><dd>{valueLabel(observation[key])}</dd></div>)}</dl><code>{String(observation.observation_id || "")}</code><details className="price-source-details"><summary>Price and weight source evidence</summary><p className="eyebrow">PRICE REFERENCES</p><JsonEvidence value={observation.evidence ?? null} /><p className="eyebrow">QUANTITY REFERENCES</p><JsonEvidence value={observation.quantity_evidence ?? null} /><dl>{["raw_value", "review_status", "time_basis", "regular_price", "reference_price", "promotion"].filter(key => observation[key] !== undefined).map(key => <div key={key}><dt>{humanize(key)}</dt><dd>{valueLabel(observation[key])}</dd></div>)}</dl></details></div>) : <p>No normalized price observations in this snapshot.</p>}</details></div>}
    <a className="snapshot-link" href={snapshotUrl} target="_blank" rel="noreferrer">Open the pinned source snapshot<Icon name="arrow" size={14} /></a>
  </aside>;
}
