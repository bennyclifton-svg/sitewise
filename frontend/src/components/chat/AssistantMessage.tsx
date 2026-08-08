import type { UIMessage } from "ai";

import { AnswerTrace } from "@/components/chat/AnswerTrace";
import { ArtefactCard } from "@/components/chat/ArtefactCard";
import { CitationChip } from "@/components/chat/CitationChip";
import { InsufficientEvidenceBanner } from "@/components/chat/InsufficientEvidenceBanner";
import { ToolActivityFeed } from "@/components/chat/ToolActivityFeed";
import { WorkflowRunCard } from "@/components/chat/WorkflowRunCard";
import { CopyContentButton } from "@/components/project/CopyContentButton";
import {
  assistantMetaFromMessageData,
  citationFromSourcePart,
  citationFromWebSourceTrace,
  citationsFromMessageData,
  dedupeCitations,
} from "@/lib/citations";
import type {
  ArtefactEvent,
  ToolStatusEvent,
  WorkflowRunRef,
} from "@/lib/chat-events";
import type { Citation } from "@/lib/types/citation";

type AssistantMessageProps = {
  message: UIMessage;
  messageData?: Record<string, unknown> | null;
  toolEvents?: ToolStatusEvent[];
  artefacts?: ArtefactEvent[];
  workflowRuns?: WorkflowRunRef[];
  agentMode?: boolean;
  projectId?: string | null;
  selectedCitationId: string | null;
  onSelectCitation: (citation: Citation) => void;
};

function extractCitations(
  message: UIMessage,
  messageData?: Record<string, unknown> | null,
  toolEvents: ToolStatusEvent[] = [],
): Citation[] {
  const fromParts = message.parts
    .filter((part) => part.type === "source-document")
    .map((part) => citationFromSourcePart(part))
    .filter((citation): citation is Citation => citation !== null);

  return dedupeCitations([
    ...fromParts,
    ...citationsFromMessageData(messageData),
    ...toolEvents
      .map((event) =>
        event.webSource ? citationFromWebSourceTrace(event.webSource) : null,
      )
      .filter((citation): citation is Citation => citation !== null),
  ]);
}

export function AssistantMessage({
  message,
  messageData,
  toolEvents = [],
  artefacts = [],
  workflowRuns = [],
  agentMode = false,
  projectId,
  selectedCitationId,
  onSelectCitation,
}: AssistantMessageProps) {
  const citations = extractCitations(message, messageData, toolEvents);
  const meta = assistantMetaFromMessageData(messageData);
  const text = message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("");

  return (
    <article
      aria-label="Assistant message"
      className="group relative mr-8 max-w-[92%] self-start rounded-lg border border-white/6 bg-black/20 px-3 py-2 text-sm"
    >
      {text.trim() ? (
        <div className="absolute top-1.5 right-1.5 z-10 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          <CopyContentButton
            content={text}
            label="Copy response"
            className="bg-black/40 hover:bg-black/55"
          />
        </div>
      ) : null}

      {meta && !meta.evidenceSufficient ? (
        <div className="mb-2">
          <InsufficientEvidenceBanner />
        </div>
      ) : null}

      <div className="space-y-2 whitespace-pre-wrap leading-relaxed pr-8">{text}</div>

      <AnswerTrace
        agentMode={agentMode}
        messageData={messageData}
        toolEvents={toolEvents}
        citations={citations}
      />

      {toolEvents.length > 0 ? <ToolActivityFeed events={toolEvents} /> : null}

      {artefacts.map((artefact, index) => (
        <ArtefactCard
          key={`${artefact.workflowType ?? "artefact"}-${artefact.draftId ?? index}`}
          artefact={artefact}
          projectId={projectId}
        />
      ))}

      {workflowRuns.map((runRef) => (
        <WorkflowRunCard
          key={runRef.runId}
          runRef={runRef}
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
