import { ChatPanel } from "@/components/chat/ChatPanel";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type { ResourceEvent } from "@/lib/chat-events";
import { cn } from "@/lib/utils";

type ChatRailProps = {
  thread: ChatThread | null;
  messages: ChatMessage[];
  chatRevision: number;
  chatLoading: boolean;
  crossProject: boolean;
  selectedCitationId: string | null;
  onCrossProjectChange: (value: boolean) => void;
  onConversationUpdate: () => void;
  onResourceEvent?: (event: ResourceEvent) => void;
  onUserSubmit?: () => void;
  onSelectCitation: (citation: Citation | null) => void;
  layout?: "rail" | "main";
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
};

export function ChatRail({
  thread,
  messages,
  chatRevision,
  chatLoading,
  crossProject,
  selectedCitationId,
  onCrossProjectChange,
  onConversationUpdate,
  onResourceEvent,
  onUserSubmit,
  onSelectCitation,
  layout = "rail",
  collapsed = false,
  onCollapsedChange,
}: ChatRailProps) {
  return (
    <div className={cn("flex flex-col", collapsed ? "shrink-0" : "min-h-0 flex-1")}>
      <div
        className={cn(
          layout === "main"
            ? collapsed
              ? "flex shrink-0 flex-col px-6 py-2"
              : "flex min-h-0 flex-1 flex-col px-6 py-3"
            : collapsed
              ? "flex shrink-0 flex-col px-3 py-2"
              : "flex min-h-0 flex-1 flex-col px-3 py-3",
        )}
      >
        {chatLoading || !thread ? (
          <p className="text-sm text-muted-foreground" role="status">
            Loading chat...
          </p>
        ) : (
          <ChatPanel
            key={`${thread.id}-${chatRevision}`}
            threadId={thread.id}
            initialMessages={messages}
            onConversationUpdate={onConversationUpdate}
            onResourceEvent={onResourceEvent}
            onUserSubmit={onUserSubmit}
            layout={layout === "main" ? "main" : "rail"}
            collapsed={collapsed}
            collapsible={layout === "main"}
            onCollapsedChange={onCollapsedChange}
            agentMode
            projectId={thread.project_id}
            showScopeControls
            crossProject={crossProject}
            onCrossProjectChange={onCrossProjectChange}
            selectedCitationId={selectedCitationId}
            onSelectCitation={onSelectCitation}
          />
        )}
      </div>
    </div>
  );
}
