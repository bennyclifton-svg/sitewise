import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { CircleStop, Send } from "lucide-react";
import { useMemo, useState, useSyncExternalStore } from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { ChatEmptyState } from "@/components/chat/ChatEmptyState";
import { ChatErrorBanner } from "@/components/chat/ChatErrorBanner";
import { SourcePassagePanel } from "@/components/chat/SourcePassagePanel";
import { StreamingIndicator } from "@/components/chat/StreamingIndicator";
import { UserMessage } from "@/components/chat/UserMessage";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  artefactsFromMessage,
  toolStatusesFromMessage,
  type ArtefactEvent,
  type ToolStatusEvent,
} from "@/lib/chat-events";
import {
  classifyChatError,
  messageDataById,
  toUiMessages,
} from "@/lib/chat-ui";
import {
  getSelectedChatModel,
  subscribeSelectedChatModel,
} from "@/lib/chat-model";
import { env } from "@/lib/env";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage } from "@/lib/types/chat";

type ChatPanelProps = {
  threadId: string;
  initialMessages: ChatMessage[];
  isFirstConversation?: boolean;
  onConversationUpdate?: () => void;
  compact?: boolean;
  scopeLabel?: string;
  showScopeControls?: boolean;
  crossProject?: boolean;
  onCrossProjectChange?: (value: boolean) => void;
  agentMode?: boolean;
  projectId?: string | null;
};

export function ChatPanel({
  threadId,
  initialMessages,
  isFirstConversation = false,
  onConversationUpdate,
  compact = false,
  scopeLabel,
  showScopeControls = false,
  crossProject = false,
  onCrossProjectChange,
  agentMode = false,
  projectId,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const persistedMessageData = useMemo(
    () => messageDataById(initialMessages),
    [initialMessages],
  );
  const chatModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectedChatModel,
    () => null,
  );

  const transport = useMemo(() => {
    const selectedModel = chatModel ?? getSelectedChatModel();
    const params = new URLSearchParams();
    if (crossProject) {
      params.set("cross_project", "true");
    }
    if (selectedModel) {
      params.set("chat_model", selectedModel);
    }
    const query = params.toString();
    const streamPath = agentMode
      ? "/chat/agent/stream"
      : `/chat/stream${query ? `?${query}` : ""}`;
    return new DefaultChatTransport({
      api: `${env.apiBaseUrl.replace(/\/$/, "")}${streamPath}`,
      headers: async (): Promise<Record<string, string>> => {
        const token = await getAccessToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
      },
      prepareSendMessagesRequest: ({ id, messages, body }) => ({
        body: {
          ...body,
          thread_id: id,
          messages,
          ...(!agentMode && selectedModel ? { chat_model: selectedModel } : {}),
        },
      }),
    });
  }, [agentMode, crossProject, chatModel]);

  const { messages, sendMessage, status, error, stop } = useChat({
    id: threadId,
    messages: toUiMessages(initialMessages),
    transport,
    onData: (part) => {
      if (
        part.type === "data-clerk-status" &&
        typeof part.data === "object" &&
        part.data !== null &&
        "message" in part.data &&
        typeof part.data.message === "string"
      ) {
        setStatusMessage(part.data.message);
      }
    },
    onFinish: () => {
      setStatusMessage(null);
      onConversationUpdate?.();
    },
    onError: () => {
      setStatusMessage(null);
    },
  });

  const isBusy = status === "submitted" || status === "streaming";
  const chatError = error ? classifyChatError(error) : null;

  const { artefactsByMessageId, toolEventsByMessageId } = useMemo(() => {
    const nextTools = new Map<string, ToolStatusEvent[]>();
    const nextArtefacts = new Map<string, ArtefactEvent[]>();

    for (const message of messages) {
      if (message.role !== "assistant") continue;
      const toolEvents = toolStatusesFromMessage(message);
      const artefacts = artefactsFromMessage(message);
      if (toolEvents.length > 0) nextTools.set(message.id, toolEvents);
      if (artefacts.length > 0) nextArtefacts.set(message.id, artefacts);
    }

    return {
      artefactsByMessageId: nextArtefacts,
      toolEventsByMessageId: nextTools,
    };
  }, [messages]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isBusy) return;
    setInput("");
    await sendMessage({ text });
  }

  async function handleStop() {
    stop();
    try {
      await api.cancelAgentTurn(threadId);
    } catch {
      setStatusMessage("Cancellation requested");
    }
  }

  return (
    <div className={compact ? "grid gap-4" : "grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]"}>
      <div className="flex min-h-[28rem] flex-col gap-4">
        {showScopeControls ? (
          <div className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-xs">
            <div className="min-w-0">
              <p className="font-medium">
                {crossProject ? "Cross-project search" : "Project-only search"}
              </p>
              <p className="truncate text-muted-foreground">
                {crossProject
                  ? "Searches all available project evidence you can access."
                  : scopeLabel ??
                    "Searches this active project plus SiteWise platform knowledge."}
              </p>
            </div>
            <label className="inline-flex shrink-0 items-center gap-2">
              <input
                type="checkbox"
                className="size-4 rounded border-border accent-foreground"
                checked={crossProject}
                onChange={(event) => onCrossProjectChange?.(event.target.checked)}
              />
              <span>Cross-project</span>
            </label>
          </div>
        ) : null}

        <div className="flex-1 space-y-3 overflow-y-auto rounded-md border p-4">
          {messages.length === 0 ? (
            <ChatEmptyState variant={isFirstConversation ? "first-time" : "thread"} />
          ) : (
            messages.map((message) => {
              const text = message.parts
                .filter((part) => part.type === "text")
                .map((part) => part.text)
                .join("");

              if (message.role === "assistant") {
                return (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    messageData={persistedMessageData.get(message.id)}
                    toolEvents={toolEventsByMessageId.get(message.id)}
                    artefacts={artefactsByMessageId.get(message.id)}
                    projectId={projectId}
                    selectedCitationId={selectedCitation?.sourceId ?? null}
                    onSelectCitation={setSelectedCitation}
                  />
                );
              }

              return <UserMessage key={message.id} text={text} />;
            })
          )}

          {isBusy ? <StreamingIndicator message={statusMessage} /> : null}
        </div>

        {chatError ? (
          <ChatErrorBanner message={chatError.message} kind={chatError.kind} />
        ) : null}

        <form className="flex gap-2" onSubmit={(event) => void handleSubmit(event)}>
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about your project documents…"
            disabled={isBusy}
            aria-label="Message"
          />
          <Button type="submit" disabled={isBusy || input.trim() === ""}>
            <Send className="size-4" aria-hidden />
            {isBusy ? "Sending…" : "Send"}
          </Button>
          {isBusy ? (
            <Button type="button" variant="outline" onClick={() => void handleStop()}>
              <CircleStop className="size-4" aria-hidden />
              Stop
            </Button>
          ) : null}
        </form>
      </div>

      <SourcePassagePanel citation={selectedCitation} />
    </div>
  );
}
