import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { ArrowDown } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { ChatEmptyState } from "@/components/chat/ChatEmptyState";
import { ChatErrorBanner } from "@/components/chat/ChatErrorBanner";
import { SourcePassagePanel } from "@/components/chat/SourcePassagePanel";
import { StreamingIndicator } from "@/components/chat/StreamingIndicator";
import { UserMessage } from "@/components/chat/UserMessage";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
  getSelectedAgentModel,
  subscribeSelectedAgentModel,
} from "@/lib/agent-model";
import {
  getSelectedAgentRuntime,
  subscribeSelectedAgentRuntime,
} from "@/lib/agent-runtime";
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
  layout?: "page" | "rail";
  showScopeControls?: boolean;
  crossProject?: boolean;
  onCrossProjectChange?: (value: boolean) => void;
  agentMode?: boolean;
  projectId?: string | null;
  selectedCitationId?: string | null;
  onSelectCitation?: (citation: Citation | null) => void;
};

export function ChatPanel({
  threadId,
  initialMessages,
  isFirstConversation = false,
  onConversationUpdate,
  layout = "page",
  showScopeControls = false,
  crossProject = false,
  onCrossProjectChange,
  agentMode = false,
  projectId,
  selectedCitationId = null,
  onSelectCitation,
}: ChatPanelProps) {
  const isRail = layout === "rail";
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [internalSelectedCitation, setInternalSelectedCitation] = useState<Citation | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);
  const persistedMessageData = useMemo(
    () => messageDataById(initialMessages),
    [initialMessages],
  );
  const chatModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectedChatModel,
    () => null,
  );
  const agentModel = useSyncExternalStore(
    subscribeSelectedAgentModel,
    getSelectedAgentModel,
    () => null,
  );
  const agentRuntime = useSyncExternalStore(
    subscribeSelectedAgentRuntime,
    getSelectedAgentRuntime,
    () => null,
  );

  const activeCitationId =
    onSelectCitation !== undefined ? selectedCitationId : internalSelectedCitation?.sourceId ?? null;

  function handleSelectCitation(citation: Citation | null) {
    if (onSelectCitation) {
      onSelectCitation(citation);
      return;
    }
    setInternalSelectedCitation(citation);
  }

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
          ...(agentMode
            ? {
                ...(agentModel ? { agent_model: agentModel } : {}),
                ...(agentRuntime ? { agent_runtime: agentRuntime } : {}),
              }
            : selectedModel
              ? { chat_model: selectedModel }
              : {}),
        },
      }),
    });
  }, [agentMode, crossProject, chatModel, agentModel, agentRuntime]);

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

  const updateScrollButton = useCallback(() => {
    const history = historyRef.current;
    if (!history) return;
    const distanceFromBottom =
      history.scrollHeight - history.clientHeight - history.scrollTop;
    setShowScrollButton(distanceFromBottom > 32);
  }, []);

  const scrollToBottom = useCallback(() => {
    const history = historyRef.current;
    if (!history) return;
    history.scrollTop = history.scrollHeight;
    setShowScrollButton(false);
  }, []);

  useEffect(() => {
    if (isBusy || !showScrollButton) {
      scrollToBottom();
      return;
    }
    updateScrollButton();
  }, [isBusy, messages, scrollToBottom, showScrollButton, updateScrollButton]);

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

  async function handleSubmit() {
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

  const shellClass = isRail
    ? "flex min-h-0 flex-1 flex-col gap-3"
    : "grid min-h-0 gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]";
  const chatColumnClass = isRail
    ? "flex min-h-0 flex-1 flex-col gap-3"
    : "flex h-[min(42rem,calc(100vh-16rem))] min-h-[28rem] min-w-0 flex-col gap-4";
  const historyClass = isRail
    ? "cockpit-scroll flex h-full min-h-0 flex-col gap-2 overflow-y-auto scroll-smooth pr-1"
    : "cockpit-scroll flex h-full min-h-0 flex-col gap-3 overflow-y-auto rounded-md border p-4 scroll-smooth";

  return (
    <div className={shellClass}>
      <div className={chatColumnClass}>
        <div className="relative min-h-0 flex-1">
          <div
            ref={historyRef}
            role="log"
            aria-label="Conversation history"
            onScroll={updateScrollButton}
            className={historyClass}
          >
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
                      selectedCitationId={activeCitationId}
                      onSelectCitation={handleSelectCitation}
                    />
                  );
                }

                return <UserMessage key={message.id} text={text} />;
              })
            )}

            {isBusy ? <StreamingIndicator message={statusMessage} /> : null}
          </div>

          {showScrollButton ? (
            <Button
              type="button"
              size="icon"
              variant="secondary"
              className="absolute right-3 bottom-3 shadow-md"
              aria-label="Scroll to latest message"
              title="Scroll to latest message"
              onClick={scrollToBottom}
            >
              <ArrowDown className="size-4" aria-hidden />
            </Button>
          ) : null}
        </div>

        {chatError ? (
          <ChatErrorBanner message={chatError.message} kind={chatError.kind} />
        ) : null}

        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={() => void handleSubmit()}
          onStop={() => void handleStop()}
          isBusy={isBusy}
          agentMode={agentMode}
          crossProject={crossProject}
          onCrossProjectChange={onCrossProjectChange}
          showScopeControls={showScopeControls}
        />
      </div>

      {!isRail ? (
        <SourcePassagePanel citation={internalSelectedCitation} />
      ) : null}
    </div>
  );
}
