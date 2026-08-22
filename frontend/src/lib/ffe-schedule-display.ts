import {
  parseEmbeddedDecision,
  type EmbeddedDecision,
} from "@/components/project/DecisionControl";
import { splitMarkdownSections } from "@/lib/markdown-sections";
import {
  citationColumnIndexFromHeaders,
  type RegisterCitationLayout,
} from "@/lib/pmp-register-tables";
import { editableTableCells, formatTableRow } from "@/lib/table-row-edit";

const FFE_HEADING_RE = /^ffe schedule$/i;
const BRIEF_HEADING_RE = /^(brief|brief and scope)$/i;
const FFE_TABLE_HEADER_RE =
  /^\|\s*Item\s*\|\s*Location\s*\|(?:.*\|\s*)?Finish\s*\|/i;
const DECISION_FENCE_RE =
  /```pmp-decision(?:-group)?\s*\n([\s\S]*?)\n```/g;

/** Finish catalog ids that used to render as FFE dropdown rows. */
export const FINISH_DECISION_IDS = new Set([
  "flooring-finish",
  "external-cladding",
  "roofing-system",
  "kitchen-benchtop",
  "kitchen-joinery-grade",
  "wet-area-finish",
  "window-frame",
  "glazing-type",
]);

const FINISH_DECISION_ROW_LABELS = new Set([
  "primary flooring finish",
  "primary external cladding",
  "roofing system",
  "kitchen benchtop",
  "kitchen joinery grade",
  "wet-area floor and wall finish",
  "window and external door frames",
  "glazing performance",
]);

const FINISH_ITEM_MATCHERS: { ids: string[]; pattern: RegExp }[] = [
  { ids: ["external-cladding"], pattern: /\b(external\s+cladding|facade\s+cladding|cladding)\b/i },
  { ids: ["roofing-system"], pattern: /\broof/i },
  { ids: ["flooring-finish"], pattern: /\b(floor finish|flooring)\b/i },
  {
    ids: ["kitchen-benchtop", "kitchen-joinery-grade"],
    pattern: /\b(kitchen|benchtop|joinery)\b/i,
  },
  { ids: ["wet-area-finish"], pattern: /\b(tile|wet[-\s]?area)\b/i },
  { ids: ["window-frame", "glazing-type"], pattern: /\b(window|glazing)\b/i },
];

const FFE_PLACEHOLDERS = new Set([
  "",
  "—",
  "-",
  "tbc",
  "to be confirmed",
  "not evidenced",
  "typical",
  "user provided",
  "assumption",
  "assumption / not evidenced",
  "profile",
]);

export const FFE_DECISION_MARKER_RE =
  /^\{\{pmp-decision:([a-z0-9]+(?:-[a-z0-9]+)*)\}\}$/i;

export function formatFfeDecisionMarker(decisionId: string): string {
  return `{{pmp-decision:${decisionId}}}`;
}

export function parseFfeDecisionMarker(text: string): string | null {
  const match = text.trim().match(FFE_DECISION_MARKER_RE);
  return match?.[1] ?? null;
}

export type FoldFfeScheduleResult = {
  markdown: string;
  foldedById: Map<string, EmbeddedDecision>;
};

export type FfeTableLayout = RegisterCitationLayout & {
  finishColumnIndex: number;
  commentColumnIndex: number | null;
  renameHeaders: Record<string, string>;
};

/**
 * Display-only: hide finish-catalog `pmp-decision` fences so they are not
 * rendered as a second FFE list. Canonical markdown keeps the fences.
 * Matching selected labels are applied onto existing rows at render time.
 */
export function foldFfeScheduleDecisions(markdown: string): FoldFfeScheduleResult {
  const foldedById = new Map<string, EmbeddedDecision>();
  const sections = splitMarkdownSections(markdown);
  if (!sections.length) {
    return { markdown, foldedById };
  }

  const ffeSection = sections.find((section) =>
    FFE_HEADING_RE.test(section.heading.trim()),
  );
  const ffeBody = ffeSection
    ? markdown.slice(ffeSection.start, ffeSection.end)
    : "";
  const hasFfeTable = Boolean(
    ffeBody.split("\n").some((line) => FFE_TABLE_HEADER_RE.test(line.trim())),
  );

  let changed = false;
  const parts: string[] = [];
  let cursor = 0;
  const relocatedFromBrief: EmbeddedDecision[] = [];

  for (const section of sections) {
    if (section.start > cursor) {
      parts.push(markdown.slice(cursor, section.start));
    }
    const original = markdown.slice(section.start, section.end);
    const heading = section.heading.trim();

    if (hasFfeTable && BRIEF_HEADING_RE.test(heading)) {
      const { markdown: next, removed } = stripFinishDecisions(original);
      if (removed.length) {
        changed = true;
        relocatedFromBrief.push(...removed);
      }
      parts.push(next);
      cursor = section.end;
      continue;
    }

    if (FFE_HEADING_RE.test(heading)) {
      const folded = foldSection(original, foldedById, relocatedFromBrief);
      if (folded !== original || relocatedFromBrief.length) changed = true;
      parts.push(folded);
      cursor = section.end;
      continue;
    }

    parts.push(original);
    cursor = section.end;
  }

  if (cursor < markdown.length) {
    parts.push(markdown.slice(cursor));
  }

  return {
    markdown: changed ? parts.join("") : markdown,
    foldedById,
  };
}

export function isFfePlaceholder(value: string): boolean {
  return FFE_PLACEHOLDERS.has(value.trim().toLowerCase());
}

export function isFfeDecisionDuplicateRow(
  itemName: string,
  foldedById?: ReadonlyMap<string, EmbeddedDecision>,
): boolean {
  const key = itemName.trim().toLowerCase();
  if (!key) return false;
  if (FINISH_DECISION_ROW_LABELS.has(key)) return true;
  if (!foldedById) return false;
  for (const decision of foldedById.values()) {
    if (decision.label.trim().toLowerCase() === key) return true;
  }
  return false;
}

export function selectedFinishForItem(
  itemName: string,
  foldedById?: ReadonlyMap<string, EmbeddedDecision>,
): string | null {
  if (!foldedById?.size) return null;
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const matcher of FINISH_ITEM_MATCHERS) {
    if (!matcher.pattern.test(itemName)) continue;
    for (const id of matcher.ids) {
      const decision = foldedById.get(id);
      if (!decision) continue;
      const label = selectedOptionLabel(decision);
      if (!label || seen.has(label.toLowerCase())) continue;
      seen.add(label.toLowerCase());
      labels.push(label);
    }
  }
  return labels.length ? labels.join("; ") : null;
}

export function presentFfeFinish(
  itemName: string,
  finishText: string,
  foldedById?: ReadonlyMap<string, EmbeddedDecision>,
): string {
  const markerId = parseFfeDecisionMarker(finishText);
  if (markerId && foldedById?.get(markerId)) {
    return selectedOptionLabel(foldedById.get(markerId)!) || "TBC";
  }
  if (!isFfePlaceholder(finishText)) return finishText.trim();
  return selectedFinishForItem(itemName, foldedById) ?? "TBC";
}

export function presentFfeComment(text: string): string {
  return isFfePlaceholder(text) ? "" : text.trim();
}

export function ffeTableLayoutFromHeaders(
  headers: readonly string[],
): FfeTableLayout | null {
  const normalized = headers.map((header) =>
    header.trim().toLowerCase().replace(/\s+/g, " "),
  );
  const item = normalized.indexOf("item");
  const finish = normalized.indexOf("finish");
  if (item < 0 || finish < 0) return null;
  const dropColumnIndexes: number[] = [];
  let commentColumnIndex: number | null = null;
  normalized.forEach((header, index) => {
    if (header === "qty" || header === "quantity" || header === "status") {
      dropColumnIndexes.push(index);
      return;
    }
    if (header === "notes" || header === "comment") {
      commentColumnIndex = index;
    }
  });
  const citationColumnIndex = citationColumnIndexFromHeaders(headers);
  return {
    dropColumnIndexes,
    finishColumnIndex: finish,
    commentColumnIndex,
    citationColumnIndex,
    appendCitation: citationColumnIndex === null,
    blankCitationHeader: true,
    renameHeaders: { notes: "Comment" },
  };
}

export function projectFfeScheduleRow(
  sourceRow: string,
  layout?: FfeTableLayout | null,
): {
  cells: string[];
  commit: (cells: readonly string[]) => string;
} {
  const cells = editableTableCells(sourceRow);
  if (layout && layout.dropColumnIndexes.length === 0) {
    return {
      cells,
      commit: (next) => formatTableRow([...next]),
    };
  }
  if (cells.length === 6) {
    return {
      cells: [cells[0], cells[1], cells[3], cells[5]],
      commit: (next) =>
        formatTableRow([
          next[0] ?? cells[0],
          next[1] ?? cells[1],
          cells[2],
          next[2] ?? cells[3],
          cells[4],
          next[3] ?? cells[5],
        ]),
    };
  }
  if (cells.length === 5) {
    return {
      cells: [cells[0], cells[1], cells[3], presentFfeComment(cells[4])],
      commit: (next) =>
        formatTableRow([
          next[0] ?? cells[0],
          next[1] ?? cells[1],
          cells[2],
          next[2] ?? cells[3],
          next[3] ?? cells[4],
        ]),
    };
  }
  return {
    cells,
    commit: (next) => formatTableRow([...next]),
  };
}

function selectedOptionLabel(decision: EmbeddedDecision): string {
  const selected = decision.options.find(
    (option) => option.value === decision.selected,
  );
  return (selected?.label || decision.selected || "").trim();
}

function stripFinishDecisions(sectionMarkdown: string): {
  markdown: string;
  removed: EmbeddedDecision[];
} {
  const removed: EmbeddedDecision[] = [];
  const markdown = sectionMarkdown.replace(
    DECISION_FENCE_RE,
    (raw, body: string) => {
      const decisions = parseFenceBody(body);
      const finish = decisions.filter((decision) =>
        FINISH_DECISION_IDS.has(decision.id),
      );
      const keep = decisions.filter(
        (decision) => !FINISH_DECISION_IDS.has(decision.id),
      );
      if (!finish.length) return raw;
      removed.push(...finish);
      if (!keep.length) return "";
      if (keep.length === 1) {
        return serializeDecisionFence(keep[0]);
      }
      return `\`\`\`pmp-decision-group\n${JSON.stringify(
        keep.map((decision) => JSON.stringify(decisionPayload(decision))),
      )}\n\`\`\``;
    },
  );
  return {
    markdown: markdown.replace(/\n{3,}/g, "\n\n"),
    removed,
  };
}

function foldSection(
  sectionMarkdown: string,
  foldedById: Map<string, EmbeddedDecision>,
  extra: EmbeddedDecision[] = [],
): string {
  const byId = new Map<string, EmbeddedDecision>();
  for (const decision of extra) {
    byId.set(decision.id, decision);
  }

  const withoutFences = sectionMarkdown.replace(
    DECISION_FENCE_RE,
    (_raw, body: string) => {
      for (const decision of parseFenceBody(body)) {
        byId.set(decision.id, decision);
      }
      return "";
    },
  );

  const decisions = [...byId.values()];
  if (!decisions.length) return sectionMarkdown;

  for (const decision of decisions) {
    foldedById.set(decision.id, decision);
  }

  return withoutFences
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+\n/g, "\n");
}

function parseFenceBody(body: string): EmbeddedDecision[] {
  const trimmed = body.trim();
  if (!trimmed) return [];
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (Array.isArray(parsed)) {
      return parsed
        .map((entry) =>
          parseEmbeddedDecision(
            typeof entry === "string" ? entry : JSON.stringify(entry),
          ),
        )
        .filter((decision): decision is EmbeddedDecision => decision !== null);
    }
  } catch {
    // Single-decision fences are objects, not arrays.
  }
  const single = parseEmbeddedDecision(trimmed);
  return single ? [single] : [];
}

function decisionPayload(decision: EmbeddedDecision): Record<string, unknown> {
  return {
    id: decision.id,
    ...(decision.section ? { section: decision.section } : {}),
    label: decision.label,
    options: decision.options,
    selected: decision.selected,
    ...(decision.source ? { source: decision.source } : {}),
    ...(typeof decision.evidenced === "boolean"
      ? { evidenced: decision.evidenced }
      : {}),
    ...(decision.rationale ? { rationale: decision.rationale } : {}),
  };
}

function serializeDecisionFence(decision: EmbeddedDecision): string {
  return `\`\`\`pmp-decision\n${JSON.stringify(decisionPayload(decision))}\n\`\`\``;
}
