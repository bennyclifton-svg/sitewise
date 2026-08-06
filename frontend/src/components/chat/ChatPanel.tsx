import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { ArrowDown, ChevronDown, ChevronUp } from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { ChatComposer } from "@/components/chat/ChatComposer";
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
import { getAccessToken } from "@/lib/auth";
import {
  artefactsFromMessage,
  documentSelectionFromPart,
  resourceFromPart,
  toolStatusesFromMessage,
  workflowRunsFromMessage,
  type ArtefactEvent,
  type DocumentSelectionEvent,
  type ResourceEvent,
  type ToolStatusEvent,
  type WorkflowRunRef,
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
import { cn } from "@/lib/utils";

type ChatPanelProps = {
  threadId: string;
  initialMessages: ChatMessage[];
  onConversationUpdate?: () => void;
  onResourceEvent?: (event: ResourceEvent) => void;
  onDocumentSelectionEvent?: (event: DocumentSelectionEvent) => void;
  onUserSubmit?: () => void;
  layout?: "page" | "rail" | "main";
  collapsed?: boolean;
  collapsible?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  showScopeControls?: boolean;
  crossProject?: boolean;
  onCrossProjectChange?: (value: boolean) => void;
  agentMode?: boolean;
  projectId?: string | null;
  selectedDocumentIds?: string[];
  selectedCitationId?: string | null;
  onSelectCitation?: (citation: Citation | null) => void;
};

export function ChatPanel({
  threadId,
  initialMessages,
  onConversationUpdate,
  onResourceEvent,
  onDocumentSelectionEvent,
  onUserSubmit,
  layout = "page",
  collapsed = false,
  collapsible = false,
  onCollapsedChange,
  showScopeControls = false,
  crossProject = false,
  onCrossProjectChange,
  agentMode = false,
  projectId,
  selectedDocumentIds = [],
  selectedCitationId = null,
  onSelectCitation,
}: ChatPanelProps) {
  const isRail = layout === "rail";
  const isMain = layout === "main";
  const isEmbedded = isRail || isMain;
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [internalSelectedCitation, setInternalSelectedCitation] = useState<Citation | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);
  // Programmatic pin-to-bottom sets scrollTop synchronously, which fires
  // onScroll in the same turn. Ignore that echo so it cannot flip
  // showScrollButton and re-enter the message-scroll effect.
  const ignoreScrollSyncRef = useRef(false);
  // Mirrors showScrollButton so the pin path can skip setState entirely when
  // the value is unchanged. A no-op setState still counts towards React's
  // nested-update limit while the fiber has pending work, and the pin effect
  // runs once per stream delta — 50 deltas was enough to abort the stream
  // with "Maximum update depth exceeded".
  const showScrollButtonRef = useRef(false);
  const applyShowScrollButton = useCallback((next: boolean) => {
    if (showScrollButtonRef.current === next) return;
    showScrollButtonRef.current = next;
    setShowScrollButton(next);
  }, []);
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

  const activeCitationId =
    onSelectCitation !== undefined ? selectedCitationId : internalSelectedCitation?.sourceId ?? null;

  function togglePanelCollapsed() {
    const next = !collapsed;
    onCollapsedChange?.(next);
  }

  function handleSelectCitation(citation: Citation | null) {
    if (onSelectCitation) {
      onSelectCitation(citation);
      return;
    }
    setInternalSelectedCitation(citation);
  }

  const transport = useMemo(() => {
    const selectedModel = chatModel ?? getSelectedChatModel();
    const selectedAgentModel = agentModel ?? getSelectedAgentModel();
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
                ...(selectedAgentModel ? { agent_model: selectedAgentModel } : {}),
              }
            : selectedModel
              ? { chat_model: selectedModel }
              : {}),
        },
      }),
    });
  }, [
    agentMode,
    crossProject,
    chatModel,
    agentModel,
  ]);

  const { messages, sendMessage, status, error, stop } = useChat({
    id: threadId,
    messages: toUiMessages(initialMessages),
    transport,
    onData: (part) => {
      const resource = resourceFromPart(part);
      if (resource) onResourceEvent?.(resource);
      const documentSelection = documentSelectionFromPart(part);
      if (documentSelection) onDocumentSelectionEvent?.(documentSelection);
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
    if (ignoreScrollSyncRef.current) return;
    const history = historyRef.current;
    if (!history) return;
    const distanceFromBottom =
      history.scrollHeight - history.clientHeight - history.scrollTop;
    applyShowScrollButton(distanceFromBottom > 32);
  }, [applyShowScrollButton]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const history = historyRef.current;
    if (!history) return;
    ignoreScrollSyncRef.current = true;
    if (behavior === "smooth" && typeof history.scrollTo === "function") {
      history.scrollTo({ top: history.scrollHeight, behavior: "smooth" });
    } else {
      // Direct assignment jumps without animating through prior messages.
      history.scrollTop = history.scrollHeight;
    }
    applyShowScrollButton(false);
    requestAnimationFrame(() => {
      ignoreScrollSyncRef.current = false;
    });
  }, [applyShowScrollButton]);

  useEffect(() => {
    if (collapsed) return;
    // While streaming, keep the viewport pinned. Do not key this effect on
    // showScrollButton — onScroll echoes from scrollTop assignment used to
    // flip that flag and exceed React's maximum update depth.
    if (isBusy) {
      scrollToBottom("auto");
      return;
    }
    updateScrollButton();
  }, [collapsed, isBusy, messages, scrollToBottom, updateScrollButton]);

  const wasCollapsedRef = useRef(collapsed);

  // History stays mounted while collapsed; still pin to latest on expand in
  // case layout height changed while the panel was hidden.
  useLayoutEffect(() => {
    const justExpanded = wasCollapsedRef.current && !collapsed;
    wasCollapsedRef.current = collapsed;
    if (!justExpanded) return;
    scrollToBottom("auto");
    const frame = requestAnimationFrame(() => {
      scrollToBottom("auto");
    });
    return () => cancelAnimationFrame(frame);
  }, [collapsed, scrollToBottom]);

  const { artefactsByMessageId, toolEventsByMessageId, workflowRunsByMessageId } =
    useMemo(() => {
      const nextTools = new Map<string, ToolStatusEvent[]>();
      const nextArtefacts = new Map<string, ArtefactEvent[]>();
      const nextRuns = new Map<string, WorkflowRunRef[]>();

      for (const message of messages) {
        if (message.role !== "assistant") continue;
        const toolEvents = toolStatusesFromMessage(message);
        const artefacts = artefactsFromMessage(message);
        const workflowRuns = workflowRunsFromMessage(message);
        if (toolEvents.length > 0) nextTools.set(message.id, toolEvents);
        if (artefacts.length > 0) nextArtefacts.set(message.id, artefacts);
        if (workflowRuns.length > 0) nextRuns.set(message.id, workflowRuns);
      }

      return {
        artefactsByMessageId: nextArtefacts,
        toolEventsByMessageId: nextTools,
        workflowRunsByMessageId: nextRuns,
      };
    }, [messages]);

  async function handleSubmit() {
    const text = input.trim();
    if (!text || isBusy) return;
    const submittedDocumentIds = [...selectedDocumentIds];
    setInput("");
    onUserSubmit?.();
    if (agentMode && submittedDocumentIds.length) {
      await sendMessage(
        { text },
        { body: { selected_document_ids: submittedDocumentIds } },
      );
      return;
    }
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

  const shellClass = collapsed
    ? "shrink-0"
    : isEmbedded
      ? "flex min-h-0 flex-1 flex-col gap-3"
      : "grid min-h-0 gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]";
  const chatColumnClass = collapsed
    ? "shrink-0"
    : isEmbedded
      ? "flex min-h-0 flex-1 flex-col gap-3"
      : "flex h-[min(42rem,calc(100vh-16rem))] min-h-[28rem] min-w-0 flex-col gap-4";
  const historyClass = isEmbedded
    ? "cockpit-scroll flex h-full min-h-0 flex-col gap-2 overflow-y-auto px-1"
    : "cockpit-scroll flex h-full min-h-0 flex-col gap-3 overflow-y-auto rounded-md border p-4";

  return (
    <div className={shellClass}>
      <div className={chatColumnClass}>
        <div
          className={cn("relative min-h-0 flex-1", collapsed && "hidden")}
          aria-hidden={collapsed || undefined}
        >
            <div
              ref={historyRef}
              role="log"
              aria-label="Conversation history"
              onScroll={updateScrollButton}
              className={historyClass}
            >
              {messages.map((message) => {
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
                      workflowRuns={workflowRunsByMessageId.get(message.id)}
                      agentMode={agentMode}
                      projectId={projectId}
                      selectedCitationId={activeCitationId}
                      onSelectCitation={handleSelectCitation}
                    />
                  );
                }

                return <UserMessage key={message.id} text={text} />;
              })}

              {isBusy ? <StreamingIndicator message={statusMessage} /> : null}
            </div>

            {showScrollButton && !collapsed ? (
              <Button
                type="button"
                size="icon"
                variant="secondary"
                className="absolute right-3 bottom-3"
                aria-label="Scroll to latest message"
                title="Scroll to latest message"
                onClick={() => scrollToBottom("smooth")}
              >
                <ArrowDown className="size-4" aria-hidden />
              </Button>
            ) : null}
          </div>

        {chatError ? (
          <ChatErrorBanner message={chatError.message} kind={chatError.kind} />
        ) : null}

        {collapsible ? (
          <div className="flex shrink-0 items-center justify-end">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={collapsed ? "Expand chat" : "Collapse chat"}
              title={collapsed ? "Expand chat" : "Collapse chat"}
              onClick={togglePanelCollapsed}
            >
              {collapsed ? (
                <ChevronUp className="size-4" aria-hidden />
              ) : (
                <ChevronDown className="size-4" aria-hidden />
              )}
            </Button>
          </div>
        ) : null}

        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={() => void handleSubmit()}
          onStop={() => void handleStop()}
          isBusy={isBusy}
          crossProject={crossProject}
          onCrossProjectChange={onCrossProjectChange}
          showScopeControls={showScopeControls}
        />
      </div>

      {!isEmbedded ? (
        <SourcePassagePanel citation={internalSelectedCitation} />
      ) : null}
    </div>
  );
}
