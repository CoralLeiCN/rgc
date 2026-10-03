import type { CSSProperties } from "react";
import type { Coverage, FieldDefinition } from "../lib/contracts";
import { number, unitLabel } from "../lib/client/display";
import { familyColor } from "../lib/client/families";

/** Uses the full family catalogue and current-cohort counts, never demo weights. */
export function FamilyTraitBreakdown({ group, fields, coverage, total }: {
  group: string; fields: FieldDefinition[]; coverage?: Record<string, Coverage>; total?: number;
}) {
  return <div className="family-trait-breakdown" tabIndex={0} style={{ "--family-color": familyColor(group) } as CSSProperties}>
    <p className="family-breakdown-summary">{fields.length} traits{typeof total === "number" ? ` · ${number(total)} matching listings` : " · coverage loading"}</p>
    <ul className="family-breakdown-list">{fields.map(field => {
      const counts = coverage?.[field.key];
      const ratio = counts && counts.total > 0 ? counts.known / counts.total : null;
      const states = counts ? `${number(counts.known)} known, ${number(counts.unknown)} unknown, ${number(counts.conflict)} conflicting, ${number(counts.not_applicable)} not applicable` : "Coverage unavailable";
      return <li key={field.key}>
        <div className="family-breakdown-row"><strong>{field.label}</strong><span>{ratio === null ? "—" : `${Math.round(ratio * 100)}% known`}</span></div>
        <div className="family-breakdown-meta"><span>{field.type}{field.unit ? ` · ${unitLabel(field.unit)}` : ""}</span>{counts && <span>{number(counts.known)} / {number(counts.total)} known</span>}</div>
        <div className="family-breakdown-meter" role="img" aria-label={states} title={states}>{counts && counts.total > 0 && <><i className="breakdown-known" style={{ width: `${counts.known / counts.total * 100}%` }} /><i className="breakdown-unknown" style={{ width: `${counts.unknown / counts.total * 100}%` }} /><i className="breakdown-conflict" style={{ width: `${counts.conflict / counts.total * 100}%` }} /><i className="breakdown-na" style={{ width: `${counts.not_applicable / counts.total * 100}%` }} /></>}</div>
        {(counts?.conflict || counts?.not_applicable) ? <span className="family-breakdown-states">{counts.conflict} conflict · {counts.not_applicable} not applicable</span> : null}
        {field.description && <p className="family-breakdown-description">{field.description}</p>}
      </li>;
    })}</ul>
    <p className="family-breakdown-footnote">Known values describe source evidence. These percentages are independent of the fictional pricing score.</p>
  </div>;
}
