"use client";

import type { CSSProperties } from "react";
import type { Attribute, FieldDefinition, Product, ProductsResponse, SchemaResponse } from "../lib/contracts";
import { attribute, attributeLabel, money, number, unitPrice } from "../lib/client/display";
import { buildFamilyLayout, familyColor, familyCoverage, familyCoverageLabel, familyEvidenceField, familyKeys, familyLabel, toggleFamily, type FamilyColumnSettings, type TraitFamily } from "../lib/client/families";
import { ErrorState, Icon, Loading } from "./Icons";
import { HelpTip } from "./HelpTip";

export type ColumnSettings = FamilyColumnSettings;
export function visibleFields(fields: FieldDefinition[], settings: ColumnSettings) {
  return buildFamilyLayout(fields, [], settings).visibleFields;
}
export const familyStyle = (group: string) => ({ "--family-color": familyColor(group) }) as CSSProperties;

export function TraitValue({ value, onClick }: { value: Attribute; onClick?: () => void }) {
  const label = attributeLabel(value);
  return <button className={`trait-value ${value.status}`} onClick={onClick} title={label}><span className="state-dot" aria-hidden="true" /><span>{label}</span>{value.truncated && <span className="truncated-indicator" aria-label="Open the evidence panel for the full value">↗</span>}</button>;
}

export function FamilyCoverageSummary({ product, family, onSelect }: { product: Product; family: TraitFamily; onSelect: (id: string, field?: string) => void }) {
  const counts = familyCoverage(product, family.allFields);
  const label = `${family.label} evidence for ${product.name}: ${familyCoverageLabel(counts)}. Coverage of all ${counts.total} schema traits in this family.`;
  return <button className="family-coverage-summary" style={familyStyle(family.key)} onClick={() => onSelect(product.id, familyEvidenceField(product, family.allFields))} aria-label={`Inspect ${label}`} title={label}>
    <span className="family-known-count"><strong>{counts.known}<span>/{counts.total}</span></strong><span>known</span></span>
    <span className="family-coverage-bar" aria-hidden="true"><i className="family-known" style={{ width: `${counts.total ? counts.known / counts.total * 100 : 0}%` }} /><i className="family-unknown" style={{ width: `${counts.total ? counts.unknown / counts.total * 100 : 0}%` }} /><i className="family-conflict" style={{ width: `${counts.total ? counts.conflict / counts.total * 100 : 0}%` }} /><i className="family-not-applicable" style={{ width: `${counts.total ? counts.not_applicable / counts.total * 100 : 0}%` }} /></span>
    <span className="family-state-counts"><span className={counts.conflict ? "has-conflicts" : undefined}>{counts.conflict} conflict</span><span>{counts.not_applicable} N/A</span><span>{counts.unknown} unknown</span></span>
  </button>;
}

export function FamilyHeader({ family, settings, onSettings, activeFamily, onFocusFamily, compact = false }: { family: TraitFamily; settings: ColumnSettings; onSettings: (settings: ColumnSettings) => void; activeFamily?: string | null; onFocusFamily?: (group: string | null) => void; compact?: boolean }) {
  const matching = family.matchingFields.length;
  const detailCount = family.visibleFields.length;
  return <div className={`family-header-content ${compact ? "compact" : ""}`} style={familyStyle(family.key)}>
    <button className="family-expander" aria-expanded={family.expanded} aria-label={`${family.expanded ? "Collapse" : "Expand"} ${family.label} family; ${matching} matching traits, ${family.allFields.length} total`} onClick={() => onSettings(toggleFamily(settings, family.key))}>
      <span className="family-label"><span className="family-swatch" aria-hidden="true" />{family.label}<Icon name="chevron" size={12} style={{ transform: family.expanded ? "rotate(90deg)" : undefined }} /></span>
      <span className="family-header-meta">{family.expanded ? `${detailCount} open` : "Coverage"} · {matching < family.allFields.length ? `${matching} matching / ` : ""}{family.allFields.length} traits{family.pinnedMatchingCount > 0 ? ` · ${family.pinnedMatchingCount} pinned` : ""}</span>
    </button>
    {onFocusFamily && <button className={`family-focus ${activeFamily === family.key ? "is-active" : ""}`} aria-label={`${activeFamily === family.key ? "Clear" : "Highlight"} ${family.label} in the price chart`} aria-pressed={activeFamily === family.key} title={activeFamily === family.key ? "Clear the price chart family highlight" : `Highlight ${family.label.toLowerCase()} in the price chart`} onClick={() => onFocusFamily(activeFamily === family.key ? null : family.key)}><Icon name="grid" size={13} /></button>}
  </div>;
}

interface Props {
  schema: SchemaResponse; data: ProductsResponse | null; loading: boolean; error: string | null; onRetry: () => void;
  fields: FieldDefinition[]; settings: ColumnSettings; onSettings: (settings: ColumnSettings) => void;
  selectedId: string | null; compared: string[]; onSelect: (id: string, field?: string) => void;
  onCompare: (id: string) => void; onPage: (page: number) => void; onPin: (key: string) => void;
  activeFamily?: string | null; onFocusFamily?: (group: string | null) => void;
}

export function TraitMatrix({ schema, data, loading, error, onRetry, settings, onSettings, selectedId, compared, onSelect, onCompare, onPage, onPin, activeFamily, onFocusFamily }: Props) {
  const change = (partial: Partial<ColumnSettings>) => onSettings({ ...settings, ...partial });
  const layout = buildFamilyLayout(schema.fields, schema.contract.groups, settings);
  const allGroups = familyKeys(schema.fields, schema.contract.groups);
  const shownKeys = layout.families.map(family => family.key);
  const allOpen = shownKeys.length > 0 && shownKeys.every(key => settings.expandedFamilies.includes(key));
  const anyOpen = shownKeys.some(key => settings.expandedFamilies.includes(key));
  const needsMore = layout.families.some(family => family.expanded && family.hiddenMatchingCount > 0);
  const hasSearch = Boolean(settings.search.trim() || settings.modelOnly);

  function fieldHeading(field: FieldDefinition, pinned: boolean) {
    return <th scope="col" key={field.key} className={`individual-trait-heading ${pinned ? "pinned-heading" : ""}`} style={familyStyle(field.group)}><div className="column-heading"><button className="column-title" onClick={() => { if (selectedId) onSelect(selectedId, field.key); }} title={field.description}>{field.label}</button><button className={`pin-button ${settings.pinned.includes(field.key) ? "is-pinned" : ""}`} onClick={() => onPin(field.key)} aria-label={`${settings.pinned.includes(field.key) ? "Unpin" : "Pin"} ${field.label}`} aria-pressed={settings.pinned.includes(field.key)}><Icon name="pin" size={12} /></button></div><small>{number(data?.coverage[field.key]?.known || 0)} known in cohort {field.modelSelected && <span className="model-dot" title="Selected pricing input" aria-label="Selected pricing input">◆</span>}</small></th>;
  }

  return <section id="trait-matrix" className="matrix panel family-matrix" aria-labelledby="matrix-title">
    <div className="section-heading"><div><p className="eyebrow"><span className="section-index">04</span> PRODUCT INTELLIGENCE</p><div className="heading-with-help"><h2 id="matrix-title">The traits behind the price.</h2><HelpTip label="About the trait matrix"><p>Expand several families to compare their traits. Product names and observed prices stay visible while scrolling.</p><p>Family colors identify schema groups. Coverage counts supported values across every trait in a family; unknown, conflict and not applicable remain distinct. It is evidence completeness, not quality, importance or the chart’s demo score.</p><p>Trait search and pricing-input controls affect displayed columns. Pinned values remain visible once even if their family is collapsed or filtered. Select a value to inspect its source evidence.</p></HelpTip></div></div><div className="section-counter" aria-live="polite"><strong>{data ? number(data.total) : "—"}</strong> listings <span>/</span> {layout.families.length} families <span>/</span> {layout.visibleFields.length} open traits</div></div>
    <div className="matrix-toolbar">
      <label><span>Trait family</span><select value={settings.group} onChange={event => change({ group: event.target.value })}><option value="all">All {allGroups.length} families</option>{allGroups.map(group => <option key={group} value={group}>{familyLabel(group)}</option>)}</select></label>
      <label className="matrix-search"><span>Find a trait</span><div className="input-with-icon"><Icon name="search" size={15} /><input type="search" placeholder="Cocoa, organic, origin…" value={settings.search} onChange={event => change({ search: event.target.value })} /></div></label>
      <div className="matrix-limit-control"><div className="label-with-help"><label htmlFor="matrix-trait-limit">Traits per family</label><HelpTip label="About the trait limit"><p>Each expanded family shows the selected number of matching unpinned traits, ordered by snapshot evidence coverage. Pinned traits are additional and appear once. Choose Show all to reveal every matching trait.</p></HelpTip></div><select id="matrix-trait-limit" value={settings.limit} onChange={event => change({ limit: Number(event.target.value) })}><option value={4}>Top 4 + pinned</option><option value={8}>Top 8 + pinned</option><option value={16}>Top 16 + pinned</option><option value={schema.fields.length}>Show all traits</option></select></div>
      <label className="checkbox-label"><input type="checkbox" checked={settings.modelOnly} onChange={event => change({ modelOnly: event.target.checked })} /><span>Pricing inputs only</span></label>
    </div>
    <div className="family-controls"><span className="subtle">{layout.matchingCount} matching traits</span><div className="family-open-actions"><button className="text-button" disabled={allOpen || !shownKeys.length} onClick={() => change({ expandedFamilies: [...new Set([...settings.expandedFamilies, ...shownKeys])] })}>Expand all shown</button><span>/</span><button className="text-button" disabled={!anyOpen} onClick={() => change({ expandedFamilies: settings.expandedFamilies.filter(key => !shownKeys.includes(key)) })}>Collapse shown</button></div></div>
    <div className="matrix-family-navigator" aria-label="Trait family expansion controls">{layout.families.map(family => <button key={family.key} style={familyStyle(family.key)} className={`family-nav-chip ${family.expanded ? "expanded" : ""} ${activeFamily === family.key ? "focused" : ""}`} aria-expanded={family.expanded} aria-label={`${family.expanded ? "Collapse" : "Expand"} ${family.label} traits`} onClick={() => onSettings(toggleFamily(settings, family.key))}><span className="family-swatch" />{family.label}<span>{family.allFields.length}</span><Icon name="chevron" size={11} style={{ transform: family.expanded ? "rotate(90deg)" : undefined }} /></button>)}</div>
    {layout.pinned.length > 0 && <div className="pinned-traits"><span className="eyebrow"><Icon name="pin" size={12} />PINNED<HelpTip label="About pinned traits"><p>Pinned values stay visible once, even when a family is collapsed or filtered. Click a pin again to remove it.</p></HelpTip></span>{layout.pinned.map(field => <button key={field.key} className="chip family-pin-chip" style={familyStyle(field.group)} onClick={() => onPin(field.key)} aria-label={`Unpin ${field.label}`}><span className="family-swatch" />{field.label}<Icon name="close" size={12} /></button>)}</div>}
    {needsMore && <p className="family-limit-note"><button className="text-button" onClick={() => change({ limit: schema.fields.length })}>Show every matching trait</button></p>}
    {layout.families.length === 0 && <div className="family-empty" role="status"><Icon name="search" size={18} /><p>No matching families · {layout.pinned.length} pinned traits</p><button className="text-button" onClick={() => change({ search: "", group: "all", modelOnly: false })}>Reset trait controls</button></div>}
    {hasSearch && layout.families.length > 0 && <p className="family-search-note">{layout.matchingCount} matching traits · {layout.families.length} families <button className="text-button" disabled={allOpen} onClick={() => change({ expandedFamilies: [...new Set([...settings.expandedFamilies, ...shownKeys])] })}>Expand matching families</button></p>}
    <div className="matrix-status" aria-live="polite">{loading && <Loading text="Loading the matching listings…" />}{error && <ErrorState message={error} onRetry={onRetry} />}</div>
    {data && data.total === 0 && <div className="empty-state"><Icon name="search" size={28} /><div className="heading-with-help"><h3>No matching listings.</h3><HelpTip label="About an empty cohort"><p>Broaden a condition or reset the cohort filters to explore the collection.</p></HelpTip></div></div>}
    {data && data.total > 0 && <>
      <div className="table-scroll family-table-scroll" tabIndex={0} aria-label="Product trait families; scroll horizontally for more families and vertically for listings">
        <table className="trait-table"><caption className="sr-only">Source listings and observed prices stay visible while scrolling. Family headers expand independently. Collapsed family coverage uses all schema traits, including unknown, conflicting and not-applicable evidence. Pinned values appear once.</caption>
          <thead><tr className="family-band"><th scope="col" rowSpan={2} className="product-column">Source listing <span className="subtle">Select to inspect</span></th><th scope="col" rowSpan={2} className="price-column">Displayed price<small>£ /100 g · context unreviewed</small></th>{layout.pinned.length > 0 && <th scope="colgroup" colSpan={layout.pinned.length} className="pinned-band"><span><Icon name="pin" size={13} />Pinned traits</span><small>{layout.pinned.length} individual columns · always visible</small></th>}{layout.families.map(family => <th scope="colgroup" key={family.key} colSpan={Math.max(1, family.visibleFields.length)} className={`family-group-heading ${family.expanded ? "expanded" : "collapsed"} ${activeFamily === family.key ? "family-active" : ""}`} style={familyStyle(family.key)}><FamilyHeader family={family} settings={settings} onSettings={onSettings} activeFamily={activeFamily} onFocusFamily={onFocusFamily} /></th>)}</tr>
          <tr className="family-trait-headings">{layout.pinned.map(field => fieldHeading(field, true))}{layout.families.flatMap(family => family.visibleFields.length ? family.visibleFields.map(field => fieldHeading(field, false)) : [<th scope="col" key={`coverage-${family.key}`} className="family-summary-heading" style={familyStyle(family.key)}><span>Family evidence coverage</span><small>All {family.allFields.length} traits{family.expanded && family.pinnedMatchingCount === family.matchingFields.length ? " · matches are pinned" : ""}</small></th>])}</tr></thead>
          <tbody>{data.products.map(product => {
            const price = unitPrice(product), shortlisted = compared.includes(product.id);
            return <tr key={product.id} className={selectedId === product.id ? "selected-row" : undefined}>
              <th scope="row" className="product-column"><div className="product-cell"><button className={`compare-mini ${shortlisted ? "in-comparison" : ""}`} onClick={() => onCompare(product.id)} disabled={!shortlisted && compared.length >= 4} aria-pressed={shortlisted} aria-label={`${shortlisted ? "Remove" : "Add"} ${product.name} ${shortlisted ? "from" : "to"} comparison`}><Icon name={shortlisted ? "check" : "plus"} size={13} /></button><button className="product-name-button" onClick={() => onSelect(product.id)}><span title={product.name}>{product.name}</span><small><i className={`seller-dot ${product.role}`} />{product.brand || product.source} · {product.source}</small></button></div></th>
              <td className="price-column"><button className={`price-value ${price === null ? "unavailable" : ""}`} onClick={() => onSelect(product.id)}>{price === null ? product.latestPriceConflict ? "Conflicting" : "Unavailable" : money(price)}</button></td>
              {layout.pinned.map(field => <td key={field.key} className="pinned-trait-cell"><TraitValue value={attribute(product, field.key)} onClick={() => onSelect(product.id, field.key)} /></td>)}
              {layout.families.flatMap(family => family.visibleFields.length ? family.visibleFields.map(field => <td key={field.key} className="family-trait-cell" style={familyStyle(family.key)}><TraitValue value={attribute(product, field.key)} onClick={() => onSelect(product.id, field.key)} /></td>) : [<td key={`coverage-${family.key}`} className="family-summary-cell" style={familyStyle(family.key)}><FamilyCoverageSummary product={product} family={family} onSelect={onSelect} /></td>])}
            </tr>;
          })}</tbody>
        </table>
      </div>
      <div className="matrix-footer"><p><span className="state-dot known-dot" />Known <span className="state-dot unknown-dot" />Unknown <span className="state-dot conflict-dot" />Conflict <span className="state-dot not-applicable-dot" />N/A</p><nav className="pagination" aria-label="Product pages"><button className="icon-button" disabled={data.page <= 1 || loading} onClick={() => onPage(data.page - 1)} aria-label="Previous page"><Icon name="chevron" size={16} style={{ transform: "rotate(180deg)" }} /></button><span>Page {data.page} of {data.totalPages}</span><button className="icon-button" disabled={data.page >= data.totalPages || loading} onClick={() => onPage(data.page + 1)} aria-label="Next page"><Icon name="chevron" size={16} /></button></nav></div>
    </>}
  </section>;
}
