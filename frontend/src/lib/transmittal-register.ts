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
