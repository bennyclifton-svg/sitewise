import { useState } from "react";

import {
  ChatPanel,
  type PendingChatInstruction,
} from "@/components/chat/ChatPanel";
import { useChatActivity } from "@/components/chat/chat-activity";
import { Button } from "@/components/ui/button";
import {
  mountedSessionsEqual,
  reconcileMountedChatSessions,
  type MountedChatSession,
} from "@/lib/chat-session-mounts";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type { DocumentSelectionEvent, ResourceEvent } from "@/lib/chat-events";
import { cn } from "@/lib/utils";

type ChatRailProps = {
  thread: ChatThread | null;
  messages: ChatMessage[];
  chatRevision: number;
  chatLoading: boolean;
  chatError?: string | null;
  onRetry?: () => void;
  selectedCitationId: string | null;
  onConversationUpdate: () => void;
  onResourceEvent?: (event: ResourceEvent) => void;
  onDocumentSelectionEvent?: (event: DocumentSelectionEvent) => void;
  onUserSubmit?: () => void;
  pendingInstruction?: PendingChatInstruction | null;
  onPendingInstructionConsumed?: (id: number) => void;
  selectedDocumentIds?: string[];
  onSelectCitation: (citation: Citation | null) => void;
  layout?: "rail" | "main";
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
};

export function ChatRail({
  thread,
  messages,
  chatLoading,
  chatError,
  onRetry,
  selectedCitationId,
  onConversationUpdate,
  onResourceEvent,
  onDocumentSelectionEvent,
  onUserSubmit,
  pendingInstruction = null,
  onPendingInstructionConsumed,
  selectedDocumentIds,
  onSelectCitation,
  layout = "rail",
  collapsed = false,
  onCollapsedChange,
}: ChatRailProps) {
  const { busyThreadIds } = useChatActivity();
  const [mounted, setMounted] = useState<MountedChatSession[]>([]);
  const nextMounted = reconcileMountedChatSessions({
    current: mounted,
    activeThreadId: thread?.id ?? null,
    incoming: thread && !chatLoading ? { thread, messages } : null,
    busyThreadIds,
  });
  if (!mountedSessionsEqual(mounted, nextMounted)) {
    setMounted(nextMounted);
  }

  const showLoading = Boolean(
    !chatError &&
      ((chatLoading && !nextMounted.some((session) => session.thread.id === thread?.id)) ||
        (!thread && nextMounted.length === 0)),
  );

  return (
    <div className={cn("flex flex-col", collapsed ? "shrink-0" : "min-h-0 flex-1")}>
      <div
        className={cn(
          layout === "main"
            ? // Keep the workbench left gutter; sit closer to the repository.
              collapsed
              ? "flex w-full min-w-0 shrink-0 flex-col py-2 pl-4 pr-2 lg:pl-6 lg:pr-2"
              : "flex w-full min-w-0 min-h-0 flex-1 flex-col py-3 pl-4 pr-2 lg:pl-6 lg:pr-2"
            : collapsed
              ? "flex shrink-0 flex-col px-3 py-2"
              : "flex min-h-0 flex-1 flex-col px-3 py-3",
        )}
      >
        {chatError ? (
          <div
            className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
            role="alert"
          >
            <p className="font-medium">Chat unavailable</p>
            <p className="mt-1">{chatError}</p>
            {onRetry ? (
              <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onRetry}>
                Retry chat
              </Button>
            ) : null}
          </div>
        ) : null}
        {nextMounted.map((session) => {
          const isActive = !chatError && session.thread.id === thread?.id;
          return (
            <div
              key={session.thread.id}
              hidden={!isActive}
              className={cn(
                isActive ? "flex min-h-0 min-w-0 flex-1 flex-col" : "hidden",
              )}
            >
              <ChatPanel
                threadId={session.thread.id}
                initialMessages={session.messages}
                onConversationUpdate={onConversationUpdate}
                onResourceEvent={onResourceEvent}
                onDocumentSelectionEvent={onDocumentSelectionEvent}
                onUserSubmit={onUserSubmit}
                pendingInstruction={isActive ? pendingInstruction : null}
                onPendingInstructionConsumed={onPendingInstructionConsumed}
                layout={layout === "main" ? "main" : "rail"}
                collapsed={collapsed}
                collapsible={layout === "main"}
                onCollapsedChange={onCollapsedChange}
                agentMode
                projectId={session.thread.project_id}
                selectedDocumentIds={selectedDocumentIds}
                crossProject={false}
                selectedCitationId={isActive ? selectedCitationId : null}
                onSelectCitation={onSelectCitation}
              />
            </div>
          );
        })}
        {showLoading ? (
          <p className="text-sm text-muted-foreground" role="status">
            Loading chat...
          </p>
        ) : null}
      </div>
    </div>
  );
}
