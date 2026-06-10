import type { UIMessage } from "ai";

import { CitationChip } from "@/components/chat/CitationChip";
import { InsufficientEvidenceBanner } from "@/components/chat/InsufficientEvidenceBanner";
import {
  assistantMetaFromMessageData,
  citationFromSourcePart,
  citationsFromMessageData,
} from "@/lib/citations";
import type { Citation } from "@/lib/types/citation";

type AssistantMessageProps = {
  message: UIMessage;
  messageData?: Record<string, unknown> | null;
  selectedCitationId: string | null;
  onSelectCitation: (citation: Citation) => void;
};

function extractCitations(
  message: UIMessage,
  messageData?: Record<string, unknown> | null,
): Citation[] {
  const fromParts = message.parts
    .filter((part) => part.type === "source-document")
    .map((part) => citationFromSourcePart(part))
    .filter((citation): citation is Citation => citation !== null);

  if (fromParts.length > 0) {
    return dedupeCitations(fromParts);
  }

  return citationsFromMessageData(messageData);
}

function dedupeCitations(citations: Citation[]): Citation[] {
  const seen = new Set<string>();
  const unique: Citation[] = [];
  for (const citation of citations) {
    if (seen.has(citation.sourceId)) continue;
    seen.add(citation.sourceId);
    unique.push(citation);
  }
  return unique;
}

export function AssistantMessage({
  message,
  messageData,
  selectedCitationId,
  onSelectCitation,
}: AssistantMessageProps) {
  const citations = extractCitations(message, messageData);
  const meta = assistantMetaFromMessageData(messageData);
  const text = message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("");

  return (
    <article className="rounded-lg border bg-card px-4 py-3 text-sm shadow-xs">
      <div className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        Clerk
      </div>

      {meta && !meta.evidenceSufficient ? <InsufficientEvidenceBanner /> : null}

      <div className="mt-2 space-y-2 whitespace-pre-wrap leading-relaxed">{text}</div>

      {citations.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {citations.map((citation, index) => (
            <CitationChip
              key={citation.sourceId}
              citation={citation}
              index={index}
              selected={selectedCitationId === citation.sourceId}
              onSelect={onSelectCitation}
            />
          ))}
        </div>
      ) : null}
    </article>
  );
}
