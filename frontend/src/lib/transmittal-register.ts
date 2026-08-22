import { splitMarkdownSections } from "@/lib/markdown-sections";
import type { EvidencePreview } from "@/lib/types/project";

export type TransmittalDocumentRow = {
  documentNumber: string;
  title: string;
  revision: string;
  category: string;
};

const TRANSMITTAL_HEADING_RE =
  /^(?:Transmittal|Project Documents|Information to review)\b/i;

export function isTransmittalHeading(heading: string): boolean {
  return TRANSMITTAL_HEADING_RE.test(heading.trim());
}

export function displayTransmittalHeading(heading: string): string {
  return heading.trim().replace(TRANSMITTAL_HEADING_RE, "Transmittal");
}

function normalizeCell(value: string | null | undefined): string {
  const trimmed = (value ?? "").trim();
  if (!trimmed || trimmed === "—" || trimmed === "-") return "";
  return trimmed;
}

function normalizeKey(value: string): string {
  return normalizeCell(value).toLowerCase();
}

function parseTableRows(sectionBody: string): TransmittalDocumentRow[] {
  const rows: TransmittalDocumentRow[] = [];
  for (const line of sectionBody.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("|")) continue;
    const cells = trimmed
      .replace(/<!--\s*clerk:block[^>]*-->/gi, "")
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());
    if (cells.length < 4) continue;
    const [documentNumber, title, revision, category] = cells;
    if (/^-{3,}$/.test(documentNumber.replaceAll(":", ""))) continue;
    if (/^document number$/i.test(documentNumber)) continue;
    if (/^no source documents/i.test(title)) continue;
    rows.push({
      documentNumber: normalizeCell(documentNumber),
      title: normalizeCell(title),
      revision: normalizeCell(revision),
      category: normalizeCell(category),
    });
  }
  return rows;
}

function tableValue(value: string | null | undefined): string {
  const trimmed = (value ?? "").trim().replaceAll("|", "\\|");
  return trimmed || "—";
}

function evidencePath(item: EvidencePreview): string {
  return (item.relative_path || item.filename || "").trim();
}

function evidenceTitle(item: EvidencePreview): string {
  const title = (item.title ?? "").trim();
  if (title) return title;
  const filename = item.filename || item.relative_path.split("/").pop() || "";
  return filename.replace(/\.[^.]+$/, "") || "—";
}

function transmittalHeading(count: number): string {
  const noun = count === 1 ? "document" : "documents";
  return `## Transmittal (${count} ${noun})`;
}

function renderTransmittalTable(evidence: EvidencePreview[]): string {
  const seen = new Set<string>();
  const rows: string[][] = [];
  for (const item of evidence) {
    const path = evidencePath(item);
    if (!path || seen.has(path)) continue;
    seen.add(path);
    rows.push([
      tableValue(item.document_number),
      tableValue(evidenceTitle(item)),
      tableValue(item.revision),
      tableValue(item.category),
    ]);
  }
  rows.sort(
    (left, right) =>
      left[0].localeCompare(right[0], undefined, { numeric: true }) ||
      left[1].localeCompare(right[1], undefined, { sensitivity: "accent" }),
  );
  const lines = [
    "| Document number | Title | Rev | Category |",
    "| --- | --- | --- | --- |",
  ];
  if (rows.length === 0) {
    lines.push("| — | No source documents currently issued | — | — |");
  } else {
    lines.push(...rows.map((row) => `| ${row.join(" | ")} |`));
  }
  return lines.join("\n");
}

const TRANSMITTAL_SECTION_RE =
  /^##\s+(?:Transmittal|Project Documents|Information to review)\b[^\n]*$/im;

export function replaceTransmittalSection(
  markdown: string,
  evidence: EvidencePreview[],
): string {
  const count = new Set(
    evidence.map(evidencePath).filter((path) => path.length > 0),
  ).size;
  const replacement = `${transmittalHeading(count)}\n${renderTransmittalTable(evidence)}`;
  const match = TRANSMITTAL_SECTION_RE.exec(markdown);
  if (!match || match.index === undefined) {
    throw new Error("Draft has no Transmittal / Project Documents section");
  }
  const start = match.index;
  const afterHeading = match.index + match[0].length;
  const rest = markdown.slice(afterHeading);
  const nextHeading = /^##\s+/m.exec(rest);
  const end = nextHeading ? afterHeading + nextHeading.index : markdown.length;
  const suffix = markdown.slice(end).replace(/^\n+/, "");
  if (suffix) {
    return `${markdown.slice(0, start)}${replacement}\n\n${suffix}`;
  }
  return `${markdown.slice(0, start)}${replacement}\n`;
}

export function parseTransmittalRows(markdown: string): TransmittalDocumentRow[] {
  const section = splitMarkdownSections(markdown).find((entry) =>
    isTransmittalHeading(entry.heading),
  );
  if (!section) return [];
  const body = markdown.slice(section.start, section.end);
  const withoutHeading = body.replace(/^##\s+[^\n]*\n?/, "");
  return parseTableRows(withoutHeading);
}

function evidenceMatchKey(row: {
  documentNumber?: string | null;
  title?: string | null;
  revision?: string | null;
}): string {
  return [
    normalizeKey(row.documentNumber ?? ""),
    normalizeKey(row.title ?? ""),
    normalizeKey(row.revision ?? ""),
  ].join("\u0000");
}

function evidenceLooseKey(row: {
  documentNumber?: string | null;
  title?: string | null;
}): string {
  return [
    normalizeKey(row.documentNumber ?? ""),
    normalizeKey(row.title ?? ""),
  ].join("\u0000");
}

export function matchTransmittalEvidenceIds(
  rows: TransmittalDocumentRow[],
  evidence: EvidencePreview[],
): string[] {
  const byExact = new Map<string, string[]>();
  const byLoose = new Map<string, string[]>();
  for (const item of evidence) {
    const exact = evidenceMatchKey({
      documentNumber: item.document_number,
      title: item.title,
      revision: item.revision,
    });
    const loose = evidenceLooseKey({
      documentNumber: item.document_number,
      title: item.title,
    });
    const exactBucket = byExact.get(exact) ?? [];
    exactBucket.push(item.id);
    byExact.set(exact, exactBucket);
    const looseBucket = byLoose.get(loose) ?? [];
    looseBucket.push(item.id);
    byLoose.set(loose, looseBucket);
  }

  const matched: string[] = [];
  const used = new Set<string>();
  for (const row of rows) {
    const exactCandidates = byExact.get(evidenceMatchKey(row)) ?? [];
    const looseCandidates = byLoose.get(evidenceLooseKey(row)) ?? [];
    const candidate =
      exactCandidates.find((id) => !used.has(id)) ??
      looseCandidates.find((id) => !used.has(id)) ??
      evidence.find((item) => {
        if (used.has(item.id)) return false;
        const title = normalizeKey(item.title);
        const stem = normalizeKey(item.filename.replace(/\.[^.]+$/, ""));
        const rowTitle = normalizeKey(row.title);
        return Boolean(rowTitle) && (title === rowTitle || stem === rowTitle);
      })?.id;
    if (!candidate || used.has(candidate)) continue;
    used.add(candidate);
    matched.push(candidate);
  }
  return matched;
}
