import type { SourceDocumentUIPart } from "ai";

import type { WebSourceTrace } from "@/lib/chat-events";
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

function citationFromWebSourceRecord(record: unknown): Citation | null {
  const data = asRecord(record);
  if (!data) return null;
  const url = readString(data, "url");
  const title = readString(data, "title");
  const excerpt = readString(data, "excerpt");
  if (!url || !title || !excerpt) return null;

  const contentHash = readString(data, "content_hash") ?? url;
  const publisher = readString(data, "publisher") ?? undefined;
  const jurisdiction = readString(data, "jurisdiction") ?? undefined;
  return {
    sourceId: `web:${contentHash}`,
    chunkId: contentHash,
    documentId: url,
    title,
    project: publisher ?? jurisdiction ?? "Official web source",
    phase: null,
    sourceType: (readString(data, "source_type") ?? "web_reference") as SourceType,
    pageOrSection: readString(data, "section"),
    excerpt,
    label: readString(data, "version_status"),
    url,
    publisher,
    jurisdiction,
    authorityClass: readString(data, "authority_class") ?? undefined,
    versionStatus: readString(data, "version_status") ?? undefined,
    effectiveDate: readString(data, "effective_date") ?? undefined,
    retrievedAt: readString(data, "retrieved_at") ?? undefined,
  };
}

export function citationFromWebSourceTrace(source: WebSourceTrace): Citation | null {
  if (!source.excerpt) return null;
  const contentHash = source.contentHash ?? source.url;
  return {
    sourceId: `web:${contentHash}`,
    chunkId: contentHash,
    documentId: source.url,
    title: source.title,
    project: source.publisher ?? source.jurisdiction ?? "Official web source",
    phase: null,
    sourceType: (source.sourceType ?? "web_reference") as SourceType,
    pageOrSection: source.section ?? null,
    excerpt: source.excerpt,
    label: source.versionStatus ?? null,
    url: source.url,
    publisher: source.publisher,
    jurisdiction: source.jurisdiction,
    authorityClass: source.authorityClass,
    versionStatus: source.versionStatus,
    effectiveDate: source.effectiveDate,
    retrievedAt: source.retrievedAt,
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
  const citations: Citation[] = [];
  if (Array.isArray(messageData.citations)) {
    for (const item of messageData.citations) {
      const citation = citationFromRecord(item);
      if (citation) citations.push(citation);
    }
  }

  const agent = asRecord(messageData.agent);
  const trace = asRecord(agent?.sourceTrace) ?? asRecord(messageData.sourceTrace);
  const web = asRecord(trace?.web);
  if (Array.isArray(web?.sources)) {
    for (const item of web.sources) {
      const citation = citationFromWebSourceRecord(item);
      if (citation) citations.push(citation);
    }
  }
  return dedupeCitations(citations);
}

export function isWebSourceType(sourceType: SourceType): boolean {
  return typeof sourceType === "string" && sourceType.startsWith("web_");
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
          "border-[color-mix(in_oklch,var(--sw-beam)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-beam)_14%,transparent)] text-[var(--sw-beam)] hover:bg-[color-mix(in_oklch,var(--sw-beam)_22%,transparent)]",
        panelClassName:
          "border-[color-mix(in_oklch,var(--sw-beam)_32%,transparent)] bg-[color-mix(in_oklch,var(--sw-beam)_10%,transparent)]",
      };
    case "doctrine":
      return {
        label: "Doctrine",
        chipClassName:
          "border-[color-mix(in_oklch,var(--sw-facet-blue)_45%,transparent)] bg-[color-mix(in_oklch,var(--sw-facet-blue)_18%,transparent)] text-[var(--sw-beam)] hover:bg-[color-mix(in_oklch,var(--sw-facet-blue)_28%,transparent)]",
        panelClassName:
          "border-[color-mix(in_oklch,var(--sw-facet-blue)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-facet-blue)_12%,transparent)]",
      };
    case "reference":
      return {
        label: "Reference",
        chipClassName:
          "border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_14%,transparent)] text-[var(--sw-caution)] hover:bg-[color-mix(in_oklch,var(--sw-caution)_22%,transparent)]",
        panelClassName:
          "border-[color-mix(in_oklch,var(--sw-caution)_32%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_10%,transparent)]",
      };
    case "web_legislation":
    case "web_planning":
    case "web_reference":
      return {
        label:
          sourceType === "web_legislation"
            ? "Official legislation"
            : sourceType === "web_planning"
              ? "Official planning source"
              : "Official web reference",
        chipClassName:
          "border-[color-mix(in_oklch,var(--sw-facet-blue)_45%,transparent)] bg-[color-mix(in_oklch,var(--sw-facet-blue)_18%,transparent)] text-[var(--sw-beam)] hover:bg-[color-mix(in_oklch,var(--sw-facet-blue)_28%,transparent)]",
        panelClassName:
          "border-[color-mix(in_oklch,var(--sw-facet-blue)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-facet-blue)_12%,transparent)]",
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
