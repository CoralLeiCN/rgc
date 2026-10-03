"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import type { FieldDefinition, Product, SchemaResponse } from "../lib/contracts";
import { humanize, money, unitLabel } from "../lib/client/display";
import { familyColor, familyKeys, familyLabel } from "../lib/client/families";
import { createProductDraft, draftFromProduct, evaluateDraft, type ProductDraft } from "../lib/client/product-draft";
import { TRAIT_DEMO_BASE, TRAIT_DEMO_RULES, TRAIT_DEMO_DEFINITION } from "../lib/trait-demo";
import { ProductExtraction } from "./ProductExtraction";
import { ProductPricing } from "./ProductPricing";
import { HelpTip } from "./HelpTip";
import { Icon } from "./Icons";

interface Props {
  schema: SchemaResponse;
  draft: ProductDraft;
  onChange: (draft: ProductDraft) => void;
  selectedProduct: Product | null;
  selectedLoading: boolean;
  children?: ReactNode;
}

const reservedInputs: Record<string, string> = {
  "identity.name": "configured-product-name",
  "quantity.total_edible_weight_g": "configured-product-weight"
};

function FieldHelp({ field }: { field: FieldDefinition }) {
  return <HelpTip label={`About ${field.label.toLowerCase()}`}>
    <p>{field.description}</p>
    {field.qualifier && <p>{field.qualifier}</p>}
    {field.type === "number" || field.type === "integer" ? <p>{field.type === "integer" ? "Whole numbers" : "Numeric value"}. Minimum: {field.minimum ?? "unspecified"}; maximum: {field.maximum ?? "unspecified"}{field.unit ? ` ${unitLabel(field.unit)}` : ""}.</p> : null}
    {field.allowedValues.length > 0 && <p>Allowed values: {field.allowedValues.map(String).join(", ")}.</p>}
    {field.type === "string_list" && <p>Enter comma-separated or newline-separated values, or a JSON array of strings. Leave the input empty to keep this trait unspecified; [] explicitly records an empty list.</p>}
    {field.modelSelected && <p>This trait is included in the published pricing design. The current prototype score uses only the six inputs listed in its score breakdown.</p>}
  </HelpTip>;
}

function TraitEditor({ field, value, error, onChange }: { field: FieldDefinition; value: string; error?: string; onChange: (value: string) => void }) {
  const id = `configure-${field.key.replaceAll(".", "-")}`;
  const common = { id, value, "aria-invalid": Boolean(error), "aria-describedby": error ? `${id}-error` : undefined };
  const numeric = field.type === "number" || field.type === "integer";
  const choices = field.type === "boolean" ? [true, false] : field.allowedValues;
  const useArea = field.type === "string_list" || field.key.endsWith("_text");
  return <div className={`config-trait-input ${error ? "has-error" : ""}`}>
    <div className="config-field-label"><label htmlFor={id}>{field.label}{field.unit && <span> / {unitLabel(field.unit)}</span>}</label><FieldHelp field={field} /></div>
    {field.type === "enum" || field.type === "boolean" ? <select {...common} onChange={event => onChange(event.target.value)}><option value="">Unspecified</option>{choices.map(choice => <option key={String(choice)} value={String(choice)}>{typeof choice === "boolean" ? choice ? "Yes" : "No" : humanize(String(choice))}</option>)}</select> : numeric ? <input {...common} type="number" inputMode={field.type === "integer" ? "numeric" : "decimal"} min={field.minimum ?? undefined} max={field.maximum ?? undefined} step={field.type === "integer" ? 1 : "any"} placeholder="Unspecified" onChange={event => onChange(event.target.value)} /> : useArea ? <textarea {...common} rows={2} placeholder={field.type === "string_list" ? field.allowedValues.length ? field.allowedValues.slice(0, 3).map(String).join(", ") : "Comma-separated values" : "Unspecified"} onChange={event => onChange(event.target.value)} /> : <input {...common} type="text" autoComplete="off" placeholder="Unspecified" onChange={event => onChange(event.target.value)} />}
    {error && <p id={`${id}-error`} className="config-input-error" role="alert">{error}</p>}
  </div>;
}

export function ProductConfigurator({ schema, draft, onChange, selectedProduct, selectedLoading, children }: Props) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<string[]>(["composition", "certifications"]);
  const [notice, setNotice] = useState("");
  const [sliderCeiling, setSliderCeiling] = useState(20);
  const [extractionSession, setExtractionSession] = useState(0);
  const evaluation = useMemo(() => evaluateDraft(draft, schema.fields), [draft, schema.fields]);
  const groups = useMemo(() => familyKeys(schema.fields, schema.contract.groups), [schema.fields, schema.contract.groups]);
  const normalizedQuery = query.trim().toLowerCase();
  const matches = (field: FieldDefinition, text = normalizedQuery) => !text || `${field.key} ${field.label} ${field.description} ${field.group}`.toLowerCase().includes(text);
  const shownFamilies = groups.map(group => ({ key: group, fields: schema.fields.filter(field => field.group === group && matches(field)) })).filter(group => group.fields.length > 0);
  const errorCount = new Set(Object.keys(evaluation.errors).map(key => key === "quantity.total_edible_weight_g" ? "weightGrams" : key === "identity.name" ? "name" : key)).size;
  const priceError = evaluation.errors.packPrice;
  const weightError = evaluation.errors.weightGrams || evaluation.errors["quantity.total_edible_weight_g"];
  const nameError = evaluation.errors.name || evaluation.errors["identity.name"];
  const priceValue = Number(draft.packPrice);
  const validPrice = Number.isFinite(priceValue) && priceValue > 0;
  const sliderMax = Math.max(sliderCeiling, validPrice ? Math.ceil(priceValue / 10) * 10 : 20);
  const sliderValue = validPrice ? priceValue : 0.01;
  const score = evaluation.score;
  const update = (partial: Partial<ProductDraft>) => { setNotice(""); onChange({ ...draft, ...partial }); };
  const updateValue = (key: string, value: string) => {
    const values = { ...draft.values };
    if (value === "") delete values[key]; else values[key] = value;
    update({ values, ...(key === "composition.nuts_presence" ? { pricing: { ...draft.pricing, nutsPresence: undefined } } : {}) });
  };
  function search(value: string) {
    setQuery(value);
    const text = value.trim().toLowerCase();
    if (text) setExpanded(current => [...new Set([...current, ...schema.fields.filter(field => matches(field, text)).map(field => field.group)])]);
  }
  function seedFromSelection() {
    if (!selectedProduct || selectedLoading) return;
    onChange(draftFromProduct(selectedProduct, schema.fields));
    setExtractionSession(current => current + 1);
    setNotice("Selected listing copied into your draft.");
  }
  function resetDraft() {
    onChange(createProductDraft());
    setExtractionSession(current => current + 1);
    setSliderCeiling(20);
    setNotice("Draft and extraction inputs reset.");
  }

  return <aside id="product-configurator" className="product-configurator panel" aria-labelledby="product-configurator-title">
    <div className="config-heading"><div><p className="eyebrow"><span className="config-marker-symbol" aria-hidden="true" />YOUR PRODUCT</p><div className="heading-with-help"><h2 id="product-configurator-title">Make it your own.</h2><HelpTip label="About your product draft"><p>Configure a product and place it on the price distribution. Pack price and edible weight determine its GBP per 100 g position. The trait-derived prototype score determines its vertical position in All families. Within a family, the chart shows your price guide without inventing a family score.</p><p>Six recognized traits calculate a transparent prototype score. It is not a fitted pricing model or quality rating. The separate price predictor uses a model trained on generated test data and labels its estimates as synthetic.</p><p>Use selected listing copies supported known values only when you press the button. Switching the selected source listing leaves your draft unchanged. Reset restores starting price inputs and leaves scoring traits unspecified.</p></HelpTip></div></div><span className="config-draft-tag">DRAFT</span></div>
    <div className="config-source-actions"><button type="button" className="button" onClick={seedFromSelection} disabled={selectedLoading || !selectedProduct}><Icon name="layers" size={14} />Use selected listing</button><button type="button" className="text-button" onClick={resetDraft}>Reset</button></div>
    <p className="config-selected-source" title={selectedProduct?.name} aria-live="polite">{selectedLoading ? "Loading selected listing…" : selectedProduct ? selectedProduct.name : "No listing selected"}</p>
    {notice && <p className="config-action-status" role="status">{notice}</p>}
    <ProductExtraction key={extractionSession} fields={schema.fields} draft={draft} onChange={onChange} />
    <form className="config-form" onSubmit={event => event.preventDefault()} noValidate>
      <div className="config-main-input"><div className="config-field-label"><label htmlFor="configured-product-name">Product name</label><HelpTip label="About the product name"><p>This name identifies your marker on the price chart. An empty name uses “My product” for the marker label.</p></HelpTip></div><input id="configured-product-name" type="text" value={draft.name} onChange={event => update({ name: event.target.value })} autoComplete="off" placeholder="My product" aria-invalid={Boolean(nameError)} aria-describedby={nameError ? "config-name-error" : undefined} />{nameError && <p className="config-input-error" id="config-name-error" role="alert">{nameError}</p>}</div>
      <div className="config-price-inputs"><div className="config-main-input"><div className="config-field-label"><label htmlFor="configured-product-price">Pack price / £</label><HelpTip label="About your pack price"><p>Enter the positive price for the whole edible pack. The chart uses pack price divided by edible weight, multiplied by 100, in GBP per 100 g.</p></HelpTip></div><input id="configured-product-price" type="number" inputMode="decimal" min={0} step="any" value={draft.packPrice} onChange={event => update({ packPrice: event.target.value })} placeholder="3.50" aria-invalid={Boolean(priceError)} aria-describedby={priceError ? "config-price-error" : undefined} />{priceError && <p className="config-input-error" id="config-price-error" role="alert">{priceError}</p>}</div><div className="config-main-input"><div className="config-field-label"><label htmlFor="configured-product-weight">Edible weight / g</label><HelpTip label="About edible pack weight"><p>Use the positive edible mass of the whole pack, excluding packaging. This input also configures the schema’s total edible weight trait.</p></HelpTip></div><input id="configured-product-weight" type="number" inputMode="decimal" min={0} step="any" value={draft.weightGrams} onChange={event => update({ weightGrams: event.target.value })} placeholder="100" aria-invalid={Boolean(weightError)} aria-describedby={weightError ? "config-weight-error" : undefined} />{weightError && <p className="config-input-error" id="config-weight-error" role="alert">{weightError}</p>}</div></div>
      <div className={`config-unit-price ${evaluation.pricePer100g === null ? "unavailable" : ""}`}><div><span className="eyebrow">YOUR UNIT PRICE</span><output aria-live="polite" htmlFor="configured-product-price configured-product-weight">{evaluation.pricePer100g === null ? "—" : money(evaluation.pricePer100g)}<span>/100 g</span></output></div><span className="config-price-icon" aria-hidden="true"><Icon name="arrow" size={19} /></span></div>
      <div className="config-price-slider"><div className="config-field-label"><label htmlFor="configured-product-price-slider">Proposed pack price</label><HelpTip label="About the proposed price slider"><p>Explore your proposed price in GBP for the whole pack. This changes its horizontal price position; the score stays calculated from your traits. Use the exact pack-price input for any amount. The slider range expands to include larger typed prices.</p></HelpTip></div><input id="configured-product-price-slider" type="range" min={0.01} max={sliderMax} step={0.01} value={sliderValue} onChange={event => { setSliderCeiling(sliderMax); update({ packPrice: Number(event.target.value).toFixed(2) }); }} aria-valuetext={`${money(sliderValue)} per pack`} aria-describedby={priceError ? "config-price-error" : undefined} style={{ "--price-progress": `${Math.max(0, Math.min(100, (sliderValue - 0.01) / (sliderMax - 0.01) * 100))}%` } as CSSProperties} /><div className="config-price-scale"><span>£0.01</span><span>{money(sliderMax)}</span></div></div>
      <div className="config-score"><div className="config-score-heading"><div className="label-with-help"><span id="configured-product-score-label">Trait-derived score</span><HelpTip label="About the trait-derived score"><p>{TRAIT_DEMO_DEFINITION}</p><p>Price edits never change the score. At least one recognized scoring input is required to display your marker. Missing traits remain unspecified.</p></HelpTip></div><output id="configured-product-score" aria-labelledby="configured-product-score-label" aria-live="polite">{score.score === null ? "—" : Number(score.score.toFixed(1))}<span>/100</span></output></div><div className="config-score-meta"><span>PROTOTYPE RECIPE</span><span>{score.knownInputs}/{TRAIT_DEMO_RULES.length} scoring inputs</span></div>{score.score === null && <p className="config-score-pending" role="status">Add a scoring trait to place your product.</p>}<details className="config-score-breakdown"><summary>Score breakdown<Icon name="chevron" size={12} /></summary><dl><div><dt>Base</dt><dd>{score.knownInputs ? `+${TRAIT_DEMO_BASE}` : "Unspecified"}</dd></div>{TRAIT_DEMO_RULES.map(rule => <div key={rule.field}><dt><span>{rule.label}</span><HelpTip label={`How ${rule.label.toLowerCase()} affects the score`}><p>{rule.definition}</p><p>Missing input stays unspecified.</p></HelpTip></dt><dd>{Object.hasOwn(score.contributions, rule.field) ? `+${Number(score.contributions[rule.field].toFixed(1))}` : "Unspecified"}</dd></div>)}</dl></details></div>
      <div className="config-traits-heading"><div className="heading-with-help"><h3>Product traits</h3><HelpTip label="About configuring traits"><p>Every schema trait is available by family or search. Clear an input to leave it unspecified. Unknown never becomes zero or false.</p><p>Name and total edible weight are edited in the top inputs. Their family rows link to those controls. These draft values are independent of source evidence. The six scoring inputs contribute to the prototype score; other traits remain available for product configuration.</p><p>An invalid input pauses the chart marker until it is corrected.</p></HelpTip></div><span>{evaluation.configuredCount}<span>/{schema.fields.length} configured</span></span></div>
      <div className="config-trait-search"><Icon name="search" size={14} /><label className="sr-only" htmlFor="configured-trait-search">Find a product trait</label><input id="configured-trait-search" type="search" value={query} onChange={event => search(event.target.value)} placeholder="Find a trait or family…" />{query && <button type="button" className="config-clear-search" onClick={() => setQuery("")} aria-label="Clear trait search"><Icon name="close" size={12} /></button>}</div>
      {errorCount > 0 && <div className="config-validation-status" role="status"><span>{errorCount} input{errorCount === 1 ? "" : "s"} to check · marker paused</span><button type="button" className="text-button" onClick={() => { setQuery(""); setExpanded(groups); }}>Show inputs</button></div>}
      <div className="config-families" aria-label="Schema trait editors">
        {shownFamilies.length === 0 && <div className="config-no-matches" role="status"><Icon name="search" size={20} /><span>No matching traits</span><button type="button" className="text-button" onClick={() => setQuery("")}>Clear search</button></div>}
        {shownFamilies.map(family => {
          const open = expanded.includes(family.key);
          const allFields = schema.fields.filter(field => field.group === family.key);
          const configured = allFields.filter(field => Object.hasOwn(evaluation.traits, field.key)).length;
          const errors = allFields.filter(field => evaluation.errors[field.key]).length;
          const contentId = `configure-family-${family.key.replaceAll(".", "-")}`;
          return <section key={family.key} className={`config-family ${open ? "is-open" : ""}`} style={{ "--family-color": familyColor(family.key) } as CSSProperties}>
            <button type="button" className="config-family-toggle" aria-expanded={open} aria-controls={contentId} onClick={() => setExpanded(current => current.includes(family.key) ? current.filter(key => key !== family.key) : [...current, family.key])}><span><i className="family-swatch" />{familyLabel(family.key)}{errors > 0 && <span className="config-family-error-count">{errors} error{errors === 1 ? "" : "s"}</span>}</span><span><span className="config-family-count">{configured}/{allFields.length}</span><Icon name="chevron" size={13} style={{ transform: open ? "rotate(90deg)" : undefined }} /></span></button>
            <div className="config-family-fields" id={contentId} hidden={!open}>{open && family.fields.map(field => reservedInputs[field.key] ? <div className="config-reserved-field" key={field.key}><div className="config-field-label"><span>{field.label}</span><FieldHelp field={field} /></div><button type="button" onClick={() => document.getElementById(reservedInputs[field.key])?.focus()}><span>{field.key === "identity.name" ? draft.name.trim() || "Unspecified" : draft.weightGrams.trim() ? `${draft.weightGrams} g` : "Unspecified"}</span><span>Edit above <Icon name="arrow" size={11} /></span></button></div> : <TraitEditor key={field.key} field={field} value={draft.values[field.key] || ""} error={evaluation.errors[field.key]} onChange={value => updateValue(field.key, value)} />)}</div>
          </section>;
        })}
      </div>
    </form>
    <ProductPricing key={extractionSession} draft={draft} fields={schema.fields} onChange={onChange} />
    {children && <details className="config-source-evidence"><summary><span><Icon name="layers" size={14} />Source evidence</span><Icon name="chevron" size={13} /></summary>{children}</details>}
  </aside>;
}
