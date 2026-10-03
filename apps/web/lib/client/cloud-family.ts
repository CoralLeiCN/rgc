import type { Point } from "../contracts";

export interface CloudFamily { id: string; label: string; color: string; }
export const evidenceColors = { unknown: "#607481", conflict: "#f0b27c", notApplicable: "#a7b4bc" };
const sellerColors = { retail: "#89e6ca", brand: "#b7a4f7", unknown: "#728b9a" };

/** Styling communicates evidence availability, never trait quality or price influence. */
export function cloudAppearance(point: Point, family: CloudFamily | null) {
  if (!family) return { color: sellerColors[point.role], symbol: "circle", detail: "" };
  const coverage = point.familyCoverage?.[family.id];
  if (!coverage || !coverage.total) return { color: evidenceColors.unknown, symbol: "circle-open", detail: "Family coverage unavailable" };
  const detail = `${coverage.known}/${coverage.total} traits known · ${coverage.unknown} unknown · ${coverage.conflict} conflicting · ${coverage.not_applicable} not applicable`;
  if (coverage.conflict) return { color: evidenceColors.conflict, symbol: "diamond", detail };
  if (coverage.not_applicable === coverage.total) return { color: evidenceColors.notApplicable, symbol: "square-open", detail };
  if (!coverage.known) return { color: evidenceColors.unknown, symbol: "circle-open", detail };
  return { color: family.color, symbol: coverage.known === coverage.total ? "circle" : "circle-open", detail };
}
