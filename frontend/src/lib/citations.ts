import type { SourceDocumentUIPart } from "ai";

import type { AssistantMessageMeta, Citation, SourceType } from "@/lib/types/citation";

type ClerkProviderMetadata = {
  clerk?: {
    chunkId?: string;
    documentId?: string;
    project?: string;
    phase?: string | null;
    sourceType?: SourceType;
    pageOrSection?: string | null;
    excerpt?: string;
    label?: string | null;
  };
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }
  return null;
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

export function citationFromRecord(record: unknown): Citation | null {
  const data = asRecord(record);
  if (!data) return null;

  const sourceId = readString(data, "sourceId") ?? readString(data, "chunkId");
  const chunkId = readString(data, "chunkId") ?? sourceId;
  const documentId = readString(data, "documentId");
  const title = readString(data, "title");
  const excerpt = readString(data, "excerpt");

  if (!sourceId || !chunkId || !documentId || !title || !excerpt) {
    return null;
  }

  return {
    sourceId,
    chunkId,
    documentId,
    title,
    project: readString(data, "project") ?? "Unknown project",
    phase: readString(data, "phase"),
    sourceType: readString(data, "sourceType") as SourceType,
    pageOrSection: readString(data, "pageOrSection"),
    excerpt,
    label: readString(data, "label"),
  };
}

export function citationFromSourcePart(part: SourceDocumentUIPart): Citation | null {
  const metadata = (part.providerMetadata ?? {}) as ClerkProviderMetadata;
  const clerk = metadata.clerk;
  const excerpt = clerk?.excerpt ?? "";
  if (!excerpt) return null;

  return {
    sourceId: part.sourceId,
    chunkId: clerk?.chunkId ?? part.sourceId,
    documentId: clerk?.documentId ?? part.sourceId,
    title: part.title ?? part.filename ?? "Source document",
    project: clerk?.project ?? "Unknown project",
    phase: clerk?.phase ?? null,
    sourceType: clerk?.sourceType ?? null,
    pageOrSection: clerk?.pageOrSection ?? null,
    excerpt,
    label: clerk?.label ?? null,
  };
}

export function dedupeCitations(citations: Citation[]): Citation[] {
  const seen = new Set<string>();
  const unique: Citation[] = [];
  for (const citation of citations) {
    if (seen.has(citation.sourceId)) continue;
    seen.add(citation.sourceId);
    unique.push(citation);
  }
  return unique;
}

export function citationsFromMessageData(
  messageData: Record<string, unknown> | null | undefined,
): Citation[] {
  if (!messageData) return [];
  const raw = messageData.citations;
  if (!Array.isArray(raw)) return [];

  const citations: Citation[] = [];
  for (const item of raw) {
    const citation = citationFromRecord(item);
    if (citation) citations.push(citation);
  }
  return dedupeCitations(citations);
}

export function assistantMetaFromMessageData(
  messageData: Record<string, unknown> | null | undefined,
): AssistantMessageMeta | null {
  if (!messageData) return null;

  const assumptions = Array.isArray(messageData.assumptions)
    ? messageData.assumptions.filter((item): item is string => typeof item === "string")
    : [];

  return {
    evidenceSufficient: messageData.evidenceSufficient !== false,
    assumptions,
    workflowDeferred: messageData.workflowDeferred === true,
    workflowNote:
      typeof messageData.workflowNote === "string" ? messageData.workflowNote : null,
  };
}

export type SourceTypeStyle = {
  label: string;
  chipClassName: string;
  panelClassName: string;
};

export function sourceTypeStyle(sourceType: SourceType): SourceTypeStyle {
  switch (sourceType) {
    case "project_evidence":
      return {
        label: "Project evidence",
        chipClassName:
          "border-sky-200 bg-sky-50 text-sky-900 hover:bg-sky-100 dark:border-sky-900/60 dark:bg-sky-950/50 dark:text-sky-100",
        panelClassName: "border-sky-200 bg-sky-50/60 dark:border-sky-900/60 dark:bg-sky-950/30",
      };
    case "doctrine":
      return {
        label: "Doctrine",
        chipClassName:
          "border-violet-200 bg-violet-50 text-violet-900 hover:bg-violet-100 dark:border-violet-900/60 dark:bg-violet-950/50 dark:text-violet-100",
        panelClassName:
          "border-violet-200 bg-violet-50/60 dark:border-violet-900/60 dark:bg-violet-950/30",
      };
    case "reference":
      return {
        label: "Reference",
        chipClassName:
          "border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-100",
        panelClassName:
          "border-amber-200 bg-amber-50/60 dark:border-amber-900/60 dark:bg-amber-950/30",
      };
    default:
      return {
        label: "Source",
        chipClassName:
          "border-border bg-muted text-foreground hover:bg-muted/80",
        panelClassName: "border-border bg-muted/40",
      };
  }
}
