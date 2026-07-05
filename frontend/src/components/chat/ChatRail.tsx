import { MessageSquarePlus } from "lucide-react";

import { ChatHistoryPopover } from "@/components/chat/ChatHistoryPopover";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

type ChatRailProps = {
  projectId: string;
  projectTitle: string;
  thread: ChatThread | null;
  messages: ChatMessage[];
  chatRevision: number;
  chatLoading: boolean;
  crossProject: boolean;
  selectedCitationId: string | null;
  onCrossProjectChange: (value: boolean) => void;
  onConversationUpdate: () => void;
  onSelectThread: (threadId: string) => void;
  onCreateThread: (thread: ChatThread) => void;
  onActiveThreadDeleted: () => void;
  onSelectCitation: (citation: Citation | null) => void;
};

export function ChatRail({
  projectId,
  projectTitle,
  thread,
  messages,
  chatRevision,
  chatLoading,
  crossProject,
  selectedCitationId,
  onCrossProjectChange,
  onConversationUpdate,
  onSelectThread,
  onCreateThread,
  onActiveThreadDeleted,
  onSelectCitation,
}: ChatRailProps) {
  const threadTitle = thread?.title ?? `${projectTitle} project chat`;

  async function handleNewChat() {
    try {
      const created = await api.createThread(undefined, projectId);
      onCreateThread(created);
    } catch {
      // Parent surfaces load errors via its own error state.
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center gap-2 border-b px-3 py-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Clerk</h2>
          <p className="truncate text-xs text-muted-foreground">{threadTitle}</p>
        </div>
        <ChatHistoryPopover
          activeThreadId={thread?.id}
          projectId={projectId}
          onSelectThread={onSelectThread}
          onCreateSession={onCreateThread}
          onActiveThreadDeleted={onActiveThreadDeleted}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="New chat"
          title="New chat"
          onClick={() => void handleNewChat()}
        >
          <MessageSquarePlus className="size-4" aria-hidden />
        </Button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col px-3 py-3">
        {chatLoading || !thread ? (
          <p className="text-sm text-muted-foreground" role="status">
            Loading chat...
          </p>
        ) : (
          <ChatPanel
            key={`${thread.id}-${chatRevision}`}
            threadId={thread.id}
            initialMessages={messages}
            isFirstConversation={messages.length === 0}
            onConversationUpdate={onConversationUpdate}
            layout="rail"
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
