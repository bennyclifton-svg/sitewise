import {
  parseEmbeddedDecision,
  type EmbeddedDecision,
} from "@/components/project/DecisionControl";
import { splitMarkdownSections } from "@/lib/markdown-sections";

const FFE_HEADING_RE = /^ffe schedule$/i;
const BRIEF_HEADING_RE = /^(brief|brief and scope)$/i;
const FFE_TABLE_HEADER_RE =
  /^\|\s*Item\s*\|\s*Location\s*\|\s*Qty\s*\|\s*Finish\s*\|\s*Status\s*\|\s*Notes\s*\|$/i;
const DECISION_FENCE_RE =
  /```pmp-decision(?:-group)?\s*\n([\s\S]*?)\n```/g;

/** Finish catalog ids that belong in the FFE Schedule table. */
const FINISH_DECISION_IDS = new Set([
  "flooring-finish",
  "external-cladding",
  "roofing-system",
  "kitchen-benchtop",
  "kitchen-joinery-grade",
  "wet-area-finish",
  "window-frame",
  "glazing-type",
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

/**
 * Display-only: move FFE Schedule `pmp-decision` fences into the schedule
 * table as rows with a Finish-column marker. Canonical markdown (and
 * persistence) keep the fences; callers apply this after grouping.
 *
 * Finish-catalog fences still living under Brief (legacy drafts) are
 * relocated into the FFE table when that table exists.
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

  const lines = withoutFences.split("\n");
  const headerIndex = lines.findIndex((line) =>
    FFE_TABLE_HEADER_RE.test(line.trim()),
  );
  if (headerIndex < 0) {
    return sectionMarkdown;
  }

  for (const decision of decisions) {
    foldedById.set(decision.id, decision);
  }

  let insertAt = headerIndex + 1;
  if (insertAt < lines.length && /^\|?\s*:?-{3,}/.test(lines[insertAt].trim())) {
    insertAt += 1;
  }
  while (insertAt < lines.length && lines[insertAt].trim().startsWith("|")) {
    insertAt += 1;
  }

  const rows = decisions.map((decision) => {
    const status =
      (decision.source ?? "").toLowerCase() === "user"
        ? "Confirmed"
        : "To be confirmed";
    return `| ${escapeCell(decision.label)} | TBC | TBC | ${formatFfeDecisionMarker(decision.id)} | ${status} | — |`;
  });

  const next = [...lines.slice(0, insertAt), ...rows, ...lines.slice(insertAt)];
  return next
    .join("\n")
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

function escapeCell(value: string): string {
  return value.replace(/\|/g, "\\|").trim();
}
