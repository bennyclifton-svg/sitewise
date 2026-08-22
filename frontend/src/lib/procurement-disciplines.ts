import type { ProcurementRequest, ProcurementRequestKind } from "@/lib/types/project";

/** Fallback consultant disciplines when the PMP register is unavailable. */
export const DEFAULT_CONSULTANT_DISCIPLINES = [
  "Architect",
  "Landscape",
  "Interior Design",
  "Structural",
  "Civil",
  "Hydraulic",
  "Electrical",
  "Mechanical",
  "Geotechnical",
  "Surveyor",
  "BASIX",
  "ESD",
  "Certifier",
  "Town Planner",
  "Heritage",
  "Archaeology",
  "Fire Engineer",
  "Fire Services",
  "BCA",
  "Acoustic",
  "Access",
  "Roof Access",
  "Facade",
  "Traffic",
  "Arborist",
  "Ecology",
  "Bushfire",
] as const;

export const DEFAULT_TRADE_PACKAGES = [
  "Main works",
  "Electrical services",
  "Mechanical services",
  "Hydraulic services",
  "Structural steel",
  "Facade",
  "Fire services",
] as const;

export type ProcurementWorkbenchTab = "consultant_rfp" | "trade_rft";

export function kindShortLabel(kind: ProcurementRequestKind): string {
  if (kind === "consultant_rfp") return "Consultant";
  if (kind === "trade_rfq") return "Supplier quote";
  if (kind === "contractor_eoi") return "EOI";
  return "Trade package";
}

export function isTradePackageKind(kind: ProcurementRequestKind): boolean {
  return kind === "trade_rft" || kind === "trade_rfq";
}

/** Infer create-kind from a typed target: known consultants stay RFPs. */
export function kindForTargetName(
  targetName: string,
  pmpDisciplines: readonly string[] = [],
  existing: readonly ProcurementRequest[] = [],
): "consultant_rfp" | "trade_rft" {
  const key = targetName.trim().toLowerCase();
  if (!key) return "trade_rft";
  const existingMatch = existing.find(
    (request) => request.target_name.trim().toLowerCase() === key,
  );
  if (existingMatch?.kind === "consultant_rfp") return "consultant_rfp";
  if (existingMatch && isTradePackageKind(existingMatch.kind)) return "trade_rft";
  const consultantNames = new Set(
    [...pmpDisciplines, ...DEFAULT_CONSULTANT_DISCIPLINES].map((name) =>
      name.trim().toLowerCase(),
    ),
  );
  return consultantNames.has(key) ? "consultant_rfp" : "trade_rft";
}

export function workbenchTabForKind(
  kind: ProcurementRequestKind,
): ProcurementWorkbenchTab {
  return kind === "consultant_rfp" ? "consultant_rfp" : "trade_rft";
}

export function requestMatchesWorkbenchTab(
  kind: ProcurementRequestKind,
  tab: ProcurementWorkbenchTab,
): boolean {
  if (tab === "consultant_rfp") return kind === "consultant_rfp";
  return isTradePackageKind(kind);
}

/** Kind order so like packages group together in the chip row. */
const REQUEST_KIND_SORT_ORDER: Record<ProcurementRequestKind, number> = {
  consultant_rfp: 0,
  trade_rfq: 1,
  trade_rft: 1,
  contractor_eoi: 2,
};

/** Chip label once kind is already selected. Always the current/latest draft. */
export function requestChipLabel(request: ProcurementRequest): string {
  const version = request.current_draft?.version ?? request.revision;
  if (request.kind === "trade_rfq") {
    return `${request.target_name} RFQ v${version}`;
  }
  return `${request.target_name} v${version}`;
}

/** Most recently updated request. Ties break with the open-list sort. */
export function latestRequest(
  requests: readonly ProcurementRequest[],
): ProcurementRequest | null {
  if (!requests.length) return null;
  return [...requests].sort((left, right) => {
    const timeDelta = right.updated_at.localeCompare(left.updated_at);
    if (timeDelta !== 0) return timeDelta;
    return compareProcurementRequests(left, right);
  })[0] ?? null;
}

export function latestRequestForKind(
  requests: readonly ProcurementRequest[],
  kind: ProcurementRequestKind,
): ProcurementRequest | null {
  return latestRequest(requests.filter((request) => request.kind === kind));
}

export function latestRequestForTab(
  requests: readonly ProcurementRequest[],
  tab: ProcurementWorkbenchTab,
): ProcurementRequest | null {
  return latestRequest(
    requests.filter((request) =>
      requestMatchesWorkbenchTab(request.kind, tab),
    ),
  );
}

/** Stable open-list order: Consultant → Trade package (RFT/RFQ) → EOI. */
export function compareProcurementRequests(
  left: ProcurementRequest,
  right: ProcurementRequest,
): number {
  const kindDelta =
    (REQUEST_KIND_SORT_ORDER[left.kind] ?? 99) -
    (REQUEST_KIND_SORT_ORDER[right.kind] ?? 99);
  if (kindDelta !== 0) return kindDelta;
  return left.target_name.localeCompare(right.target_name, undefined, {
    sensitivity: "base",
  });
}

/**
 * Pull discipline names from a PMP Consultants table.
 * Accepts either "Discipline" or legacy "Consultant" as the first column header.
 */
export function disciplinesFromPmpMarkdown(markdown: string): string[] {
  const sectionMatch = markdown.match(
    /^##\s+Consultants\s*\n([\s\S]*?)(?=^##\s|(?![\s\S]))/im,
  );
  if (!sectionMatch) return [];
  const body = sectionMatch[1];
  const rows = body
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|"));
  if (rows.length < 2) return [];

  const headerCells = splitRow(rows[0]);
  const disciplineIndex = headerCells.findIndex((cell) => {
    const normalised = cell.toLowerCase();
    return (
      normalised === "discipline" ||
      normalised === "consultant" ||
      normalised === "role"
    );
  });
  if (disciplineIndex < 0) return [];

  const seen = new Set<string>();
  const disciplines: string[] = [];
  for (const row of rows.slice(1)) {
    if (/^\|[\s|:-]+$/.test(row)) continue;
    const cells = splitRow(row);
    const raw = cells[disciplineIndex]?.trim() ?? "";
    if (!raw || /^[-—–]+$/.test(raw)) continue;
    const key = raw.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    disciplines.push(raw);
  }
  return disciplines;
}

function splitRow(line: string): string[] {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

export function mergeDisciplineOptions(
  preferred: string[],
  fallback: readonly string[],
  existingTargets: string[],
): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const name of [...preferred, ...existingTargets, ...fallback]) {
    const trimmed = name.trim();
    if (!trimmed) continue;
    const key = trimmed.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    ordered.push(trimmed);
  }
  return ordered;
}
