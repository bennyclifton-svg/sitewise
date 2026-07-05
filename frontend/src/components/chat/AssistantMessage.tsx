import type { UIMessage } from "ai";

import { AnswerTrace } from "@/components/chat/AnswerTrace";
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
  agentMode?: boolean;
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
  agentMode = false,
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
    <article
      aria-label="Assistant message"
      className="mr-8 max-w-[92%] self-start rounded-lg border border-white/6 bg-black/20 px-3 py-2 text-sm"
    >
      {meta && !meta.evidenceSufficient ? (
        <div className="mb-2">
          <InsufficientEvidenceBanner />
        </div>
      ) : null}

      <div className="space-y-2 whitespace-pre-wrap leading-relaxed">{text}</div>

      <AnswerTrace
        agentMode={agentMode}
        messageData={messageData}
        toolEvents={toolEvents}
        citations={citations}
      />

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
