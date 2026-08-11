import type { ProcurementRequest, ProcurementRequestKind } from "@/lib/types/project";

/** Fallback consultant disciplines when the PMP register is unavailable. */
export const DEFAULT_CONSULTANT_DISCIPLINES = [
  "Architect",
  "Structural engineer",
  "Hydraulic engineer",
  "Electrical services engineer",
  "Mechanical services engineer",
  "Geotechnical engineer",
  "Surveyor",
  "BASIX / energy assessor",
  "Certifier",
  "Town planner",
  "Heritage consultant",
  "Fire engineer",
  "Sustainability consultant",
  "ICT / AV / security consultant",
  "Acoustic consultant",
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

export function kindShortLabel(kind: ProcurementRequestKind): string {
  if (kind === "consultant_rfp") return "Consultant";
  if (kind === "trade_rfq") return "Supplier quote";
  if (kind === "contractor_eoi") return "EOI";
  return "Trade package";
}

/** Fast-scan label for the open-document combobox. Always the current/latest draft. */
export function requestOptionLabel(request: ProcurementRequest): string {
  const version = request.current_draft?.version ?? request.revision;
  return `${request.target_name} · ${kindShortLabel(request.kind)} · v${version}`;
}

/**
 * Pull discipline names from a PMP Consultants table.
 * Accepts either "Discipline" or legacy "Consultant" as the first column header.
 */
export function disciplinesFromPmpMarkdown(markdown: string): string[] {
  const sectionMatch = markdown.match(
    /^##\s+Consultants\s*\n([\s\S]*?)(?=^##\s|\Z)/im,
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
