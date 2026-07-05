import type { SourceDocumentUIPart, UIMessage } from "ai";

import { citationFromRecord, dedupeCitations } from "@/lib/citations";
import type { ChatMessage } from "@/lib/types/chat";

export type ChatErrorKind =
  | "auth"
  | "forbidden"
  | "grounding"
  | "retrieval"
  | "rate_limit"
  | "tool"
  | "partial_pipeline"
  | "network"
  | "generic";

export function toUiMessage(message: ChatMessage): UIMessage {
  const parts: UIMessage["parts"] = [{ type: "text", text: message.content }];

  const citations = message.message_data?.citations;
  if (Array.isArray(citations)) {
    const uniqueCitations = dedupeCitations(
      citations
        .map((item) => citationFromRecord(item))
        .filter((citation): citation is NonNullable<ReturnType<typeof citationFromRecord>> =>
          citation !== null,
        ),
    );
    for (const citation of uniqueCitations) {
      const sourcePart: SourceDocumentUIPart = {
        type: "source-document",
        sourceId: citation.sourceId,
        mediaType: mediaTypeForSource(citation.sourceType),
        title: citation.title,
        filename: citation.title,
        providerMetadata: {
          clerk: {
            chunkId: citation.chunkId,
            documentId: citation.documentId,
            project: citation.project,
            phase: citation.phase,
            sourceType: citation.sourceType,
            pageOrSection: citation.pageOrSection,
            excerpt: citation.excerpt,
            label: citation.label,
          },
        },
      };
      parts.push(sourcePart);
    }
  }

  return {
    id: message.id,
    role: message.role as UIMessage["role"],
    parts,
  };
}

export function toUiMessages(messages: ChatMessage[]): UIMessage[] {
  return messages.map(toUiMessage);
}

export function messageDataById(messages: ChatMessage[]): Map<string, Record<string, unknown>> {
  const map = new Map<string, Record<string, unknown>>();
  for (const message of messages) {
    if (message.message_data) {
      map.set(message.id, message.message_data);
    }
  }
  return map;
}

function mediaTypeForSource(sourceType: string | null): string {
  if (sourceType === "doctrine" || sourceType === "reference") {
    return "text/markdown";
  }
  return "application/pdf";
}

export function classifyChatError(error: Error): { kind: ChatErrorKind; message: string } {
  const text = error.message.trim();
  const lower = text.toLowerCase();

  if (
    text.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("not signed in") ||
    lower.includes("session expired")
  ) {
    return {
      kind: "auth",
      message: "Your session has expired. Sign in again to continue.",
    };
  }

  if (text.includes("403") || lower.includes("forbidden")) {
    return {
      kind: "forbidden",
      message: "You do not have access to this conversation.",
    };
  }

  if (
    text.includes("429") ||
    lower.includes("rate limit") ||
    lower.includes("too many requests")
  ) {
    return {
      kind: "rate_limit",
      message:
        "Clerk is being rate limited. Wait a moment, then retry this turn.",
    };
  }

  if (
    lower.includes("could not be verified against retrieved sources") ||
    lower.includes("grounding")
  ) {
    return {
      kind: "grounding",
      message:
        "Clerk could not verify the answer against retrieved sources. Try rephrasing your question or narrowing the topic.",
    };
  }

  if (lower.includes("retriev") || lower.includes("corpus")) {
    return {
      kind: "retrieval",
      message:
        "Clerk had trouble searching your project documents. Check that ingestion has completed, then try again.",
      };
  }

  if (
    lower.includes("partial pipeline") ||
    (lower.includes("pipeline") && lower.includes("incomplete"))
  ) {
    return {
      kind: "partial_pipeline",
      message:
        "The workflow stopped before all steps completed. Review any saved artefacts, then retry the remaining step.",
    };
  }

  if (
    lower.includes("tool failed") ||
    lower.includes("tool call") ||
    lower.includes("mcp")
  ) {
    return {
      kind: "tool",
      message:
        "A Clerk tool failed while handling this turn. Retry once; if it repeats, check the project data and tool logs.",
    };
  }

  if (
    lower.includes("failed to fetch") ||
    lower.includes("network") ||
    lower.includes("could not reach")
  ) {
    return {
      kind: "network",
      message: "Could not reach the backend. Is it running on port 8000?",
    };
  }

  return {
    kind: "generic",
    message: text || "Something went wrong while streaming the response.",
  };
}

export function formatChatError(error: Error): string {
  return classifyChatError(error).message;
}
