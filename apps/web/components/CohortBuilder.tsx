"use client";

import { useEffect, useState } from "react";
import type { CohortQuery, FieldDefinition, RuleOperator, SchemaResponse, TraitRule } from "../lib/contracts";
import { humanize, operators, ruleLabel, unitLabel, valueLabel } from "../lib/client/display";
import { Icon } from "./Icons";
import { HelpTip } from "./HelpTip";

interface Props { schema: SchemaResponse; cohort: CohortQuery; onChange: (value: CohortQuery) => void; requestedTrait?: { key: string; request: number } | null; }

export function CohortBuilder({ schema, cohort, onChange, requestedTrait }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [fieldKey, setFieldKey] = useState("composition.cocoa_percentage");
  const [operator, setOperator] = useState<RuleOperator>("range");
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const field = schema.fields.find(item => item.key === fieldKey) || schema.fields[0];
  const rules = cohort.rules || [];
  const choices = field.type === "boolean" ? [true, false] : field.allowedValues;
  const change = (next: Partial<CohortQuery>) => onChange({ ...cohort, ...next });

  useEffect(() => {
    if (!requestedTrait) return;
    const next = schema.fields.find(field => field.key === requestedTrait.key);
    if (!next) return;
    setExpanded(true); setFieldKey(next.key); setOperator(operators(next)[0].key);
    setMin(""); setMax(""); setValue(String(next.type === "boolean" ? true : next.allowedValues[0] ?? "")); setError("");
  }, [requestedTrait, schema.fields]);

  function chooseField(key: string) {
    const next = schema.fields.find(item => item.key === key)!;
    setFieldKey(key); setOperator(operators(next)[0].key); setMin(""); setMax("");
    setValue(String(next.type === "boolean" ? true : next.allowedValues[0] ?? "")); setError("");
  }
  function addRule() {
    if (rules.length >= 12) { setError("You can combine up to 12 conditions. Remove one to add another."); return; }
    const rule: TraitRule = { field: field.key, operator };
    if (operator === "range") {
      const low = min.trim() ? Number(min) : null, high = max.trim() ? Number(max) : null;
      const bounds = [low, high].filter((item): item is number => item !== null);
      if (!bounds.length) { setError("Enter a minimum or maximum for this condition."); return; }
      if (bounds.some(item => !Number.isFinite(item))) { setError("Enter valid, finite numbers."); return; }
      if (field.type === "integer" && bounds.some(item => !Number.isInteger(item))) { setError("This trait uses whole numbers."); return; }
      if (low !== null && high !== null && low > high) { setError("The minimum must not exceed the maximum."); return; }
      if (bounds.some(item => field.minimum !== null && item < field.minimum || field.maximum !== null && item > field.maximum)) {
        setError(`Use the schema range: ${field.minimum ?? "no minimum"} to ${field.maximum ?? "no maximum"} ${unitLabel(field.unit)}.`); return;
      }
      rule.min = low; rule.max = high;
    }
    if (operator === "equals") {
      const selected = choices.find(item => String(item) === (value || String(choices[0])));
      if (selected === undefined) { setError("Select a value from the trait vocabulary."); return; }
      rule.value = selected;
    }
    change({ rules: [...rules, rule] }); setError("");
  }
  const activeFilters = (cohort.search?.trim() ? 1 : 0) + [cohort.role, cohort.source, cohort.status].filter(item => item && item !== "all").length + rules.length;

  return <section id="cohort" className="cohort panel" aria-labelledby="cohort-title">
    <div className="cohort-toolbar">
      <label className="search-box"><Icon name="search" /><span className="sr-only">Find a source listing</span><input type="search" value={cohort.search || ""} onChange={event => change({ search: event.target.value })} placeholder="Search products, brands or retailers" /></label>
      <label className="compact-select"><span>Source</span><select value={cohort.source || "all"} onChange={event => change({ source: event.target.value })}><option value="all">All sources</option>{schema.sources.map(source => <option key={source.key} value={source.key}>{source.key} ({source.count})</option>)}</select></label>
      <label className="compact-select"><span>Seller</span><select value={cohort.role || "all"} onChange={event => change({ role: event.target.value as CohortQuery["role"] })}><option value="all">All roles</option><option value="retail">Retailer</option><option value="brand">Brand</option><option value="unknown">Unknown role</option></select></label>
      <label className="compact-select"><span>Evidence</span><select value={cohort.status || "all"} onChange={event => change({ status: event.target.value as CohortQuery["status"] })}><option value="all">All listings</option><option value="priced">Unit price available</option><option value="unpriced">Unit price unavailable</option><option value="conflicts">Conflicting evidence</option></select></label>
      <button className={`button filter-toggle ${expanded ? "active" : ""}`} aria-expanded={expanded} aria-controls="trait-conditions" onClick={() => setExpanded(!expanded)}><Icon name="sliders" size={16} />Trait filters{rules.length > 0 && <span className="count-badge">{rules.length}</span>}</button>
      {activeFilters > 0 && <button className="text-button" onClick={() => { onChange({ search: "", source: "all", role: "all", status: "all", rules: [] }); setError(""); }}>Reset</button>}
    </div>
    <div id="trait-conditions" className="trait-conditions" hidden={!expanded}>
      <div className="section-heading tight"><div><p className="eyebrow">BUILD A COMPARABLE COHORT</p><div className="heading-with-help"><h2 id="cohort-title">Choose what matters.</h2><HelpTip label="About cohort conditions"><p>Combine up to 12 conditions. Every condition must match for a listing to appear.</p><p>Numeric bounds follow the schema. Unknown, conflicting and not-applicable values remain distinct; unknown never becomes zero or false.</p></HelpTip></div></div><span className="subtle">{rules.length}/12 conditions</span></div>
      <form className="rule-form" onSubmit={event => { event.preventDefault(); addRule(); }}>
        <div className="rule-field"><div className="label-with-help"><label htmlFor="cohort-trait">Product trait</label><HelpTip label={`About ${field.label.toLowerCase()}`}><p>{field.description}</p>{field.qualifier && <p>{field.qualifier}</p>}</HelpTip></div><select id="cohort-trait" value={field.key} onChange={event => chooseField(event.target.value)}>{schema.contract.groups.map(group => <optgroup label={humanize(group)} key={group}>{schema.fields.filter(item => item.group === group).map(item => <option key={item.key} value={item.key}>{item.label}</option>)}</optgroup>)}</select></div>
        <label><span>Condition</span><select value={operator} onChange={event => { setOperator(event.target.value as RuleOperator); setError(""); }}>{operators(field).map(item => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
        {operator === "range" && <div className="range-inputs"><label><span>Minimum {unitLabel(field.unit)}</span><input type="number" value={min} onChange={event => setMin(event.target.value)} min={field.minimum ?? undefined} max={field.maximum ?? undefined} step={field.type === "integer" ? 1 : "any"} placeholder="Any" /></label><span className="range-dash">–</span><label><span>Maximum {unitLabel(field.unit)}</span><input type="number" value={max} onChange={event => setMax(event.target.value)} min={field.minimum ?? undefined} max={field.maximum ?? undefined} step={field.type === "integer" ? 1 : "any"} placeholder="Any" /></label></div>}
        {operator === "equals" && <label className="rule-value"><span>Trait value</span><select value={value || String(choices[0])} onChange={event => setValue(event.target.value)}>{choices.map(item => <option key={String(item)} value={String(item)}>{humanize(valueLabel(item))}</option>)}</select></label>}
        <button type="submit" className="button primary add-condition" disabled={rules.length >= 12}><Icon name="plus" size={16} />Add condition</button>
      </form>
      {error && <p className="inline-error" role="alert">{error}</p>}
    </div>
    {rules.length > 0 && <div className="active-rules" aria-label="Active trait conditions"><span className="eyebrow">MATCH ALL</span>{rules.map((rule, index) => <button className="chip" key={`${rule.field}-${index}`} aria-label={`Remove ${ruleLabel(rule, schema.fields)}`} onClick={() => change({ rules: rules.filter((_, at) => at !== index) })}>{ruleLabel(rule, schema.fields)}<Icon name="close" size={12} /></button>)}<button className="text-button" onClick={() => change({ rules: [] })}>Clear conditions</button></div>}
  </section>;
}

export function TraitSelect({ fields, value, onChange, id }: { fields: FieldDefinition[]; value: string; onChange: (value: string) => void; id?: string }) {
  const groups = [...new Set(fields.map(field => field.group))];
  return <select id={id} value={value} onChange={event => onChange(event.target.value)}>{groups.map(group => <optgroup key={group} label={humanize(group)}>{fields.filter(field => field.group === group).map(field => <option value={field.key} key={field.key}>{field.label}</option>)}</optgroup>)}</select>;
}
