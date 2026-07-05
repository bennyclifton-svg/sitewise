import type { UIMessage } from "ai";

import { ArtefactCard } from "@/components/chat/ArtefactCard";
import { CitationChip } from "@/components/chat/CitationChip";
import { InsufficientEvidenceBanner } from "@/components/chat/InsufficientEvidenceBanner";
import { ToolCallChip } from "@/components/chat/ToolCallChip";
import {
  assistantMetaFromMessageData,
  citationFromSourcePart,
  citationsFromMessageData,
  dedupeCitations,
} from "@/lib/citations";
import type { ArtefactEvent, ToolStatusEvent } from "@/lib/chat-events";
import type { Citation } from "@/lib/types/citation";

type AssistantMessageProps = {
  message: UIMessage;
  messageData?: Record<string, unknown> | null;
  toolEvents?: ToolStatusEvent[];
  artefacts?: ArtefactEvent[];
  projectId?: string | null;
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

  return dedupeCitations([
    ...fromParts,
    ...citationsFromMessageData(messageData),
  ]);
}

export function AssistantMessage({
  message,
  messageData,
  toolEvents = [],
  artefacts = [],
  projectId,
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

      {toolEvents.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {toolEvents.map((event, index) => (
            <ToolCallChip
              key={`${event.tool}-${event.state}-${index}`}
              event={event}
            />
          ))}
        </div>
      ) : null}

      {artefacts.map((artefact, index) => (
        <ArtefactCard
          key={`${artefact.workflowType ?? "artefact"}-${artefact.draftId ?? index}`}
          artefact={artefact}
          projectId={projectId}
        />
      ))}

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
