"use client";

import { useState, type CSSProperties } from "react";
import type { Coverage, SchemaResponse } from "../lib/contracts";
import { number, unitLabel } from "../lib/client/display";
import { familyColor, familyKeys, familyLabel } from "../lib/client/families";
import { Icon } from "./Icons";
import { HelpTip } from "./HelpTip";

interface Props {
  schema: SchemaResponse; coverage?: Record<string, Coverage>; total?: number;
  activeFamily: string | null; onFocus: (family: string | null) => void;
  onFilterTrait?: (key: string) => void; onColorTrait?: (key: string) => void; onHeightTrait?: (key: string) => void;
  colorKey?: string; heightKey?: string;
}

export function FamilyNavigator({ schema, coverage, total, activeFamily, onFocus, onFilterTrait, onColorTrait, onHeightTrait, colorKey, heightKey }: Props) {
  const groups = familyKeys(schema.fields, schema.contract.groups);
  const [search, setSearch] = useState("");
  const members = schema.fields.filter(field => !activeFamily || field.group === activeFamily);
  const browsed = members.filter(field => `${field.label} ${field.key}`.toLowerCase().includes(search.trim().toLowerCase()));
  const categorical = (type: string) => ["enum", "boolean", "string_list", "number", "integer"].includes(type);
  const numeric = (type: string) => ["number", "integer"].includes(type);
  return <section id="families" className="family-navigator panel" aria-labelledby="family-navigator-title">
    <div className="family-nav-heading"><div><p className="eyebrow"><Icon name="layers" size={13} /> TRAIT WORKSPACE</p><div className="heading-with-help"><h2 id="family-navigator-title">Filter, colour, explore.</h2><HelpTip label="About trait families"><p>Select a family to browse its member traits. Use Filter to build cohort conditions, Colour layers for a numeric or categorical leaf trait, or Height for one numeric trait.</p><p>Parent families are navigation only. A leaf trait has no child traits: enum values become layers, and numeric values use labelled ranges calibrated to the full snapshot. Height keeps the selected trait’s original units.</p><p>Family cards show trait counts and evidence coverage. Coverage measures completeness, not quality or pricing importance.</p></HelpTip></div></div><button className={`button small ${activeFamily === null ? "primary" : ""}`} aria-pressed={activeFamily === null} onClick={() => onFocus(null)}>All families</button></div>
    <div className="family-nav-strip" aria-label="Trait families">{groups.map(group => {
      const fields = schema.fields.filter(field => field.group === group);
      const known = fields.reduce((sum, field) => sum + (coverage?.[field.key]?.known || 0), 0);
      const possible = (total || 0) * fields.length;
      const percent = possible && coverage ? Math.round(100 * known / possible) : null;
      return <button key={group} type="button" aria-label={`${familyLabel(group)} traits`} className={`family-nav-card ${activeFamily === group ? "is-active" : ""}`} style={{ "--family-color": familyColor(group) } as CSSProperties} aria-pressed={activeFamily === group} onClick={() => onFocus(activeFamily === group ? null : group)}>
        <span className="family-nav-name"><i aria-hidden="true" />{familyLabel(group)}</span><span className="family-nav-count">{fields.length}<small>traits</small></span>
        <span className="family-nav-meter" aria-hidden="true"><i style={{ width: `${percent || 0}%` }} /></span><span className="family-nav-coverage">{percent === null ? "Coverage unavailable" : `${percent}% values known`}</span>
      </button>;
    })}</div>
    <div className="family-browser-toolbar"><label><span className="sr-only">Find a trait to filter or map</span><input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder={activeFamily ? `Find a ${familyLabel(activeFamily).toLowerCase()} trait…` : "Find any trait to filter or map…"} /></label>{activeFamily && <strong>{familyLabel(activeFamily)}</strong>}</div>
    {(activeFamily || search.trim()) && <div className="family-trait-browser">{browsed.length ? browsed.map(field => <div className="family-trait-choice" key={field.key}><div><span>{field.label}</span><small>{field.type}{field.unit ? ` · ${unitLabel(field.unit)}` : ""}</small></div><HelpTip label={`About ${field.label.toLowerCase()}`}><p>{field.description}</p>{field.allowedValues.length > 0 && <p>Values: {field.allowedValues.join(", ")}.</p>}</HelpTip><button className="button small" onClick={() => onFilterTrait?.(field.key)}>Filter</button>{categorical(field.type) && <button className="button small" aria-pressed={colorKey === field.key} onClick={() => onColorTrait?.(field.key)}>Colour layers</button>}{numeric(field.type) && <button className="button small" aria-pressed={heightKey === field.key} onClick={() => onHeightTrait?.(field.key)}>Height</button>}</div>) : <p className="subtle">No matching traits.</p>}</div>}
    <p className="family-nav-note">{typeof total === "number" ? `${number(total)} matching listings` : "Coverage loading…"}</p>
  </section>;
}
