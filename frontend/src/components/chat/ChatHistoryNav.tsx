import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus } from "lucide-react";
import { useState } from "react";

import { ChatSessionList } from "@/components/chat/ChatSessionList";
import { chatThreadQueryKey } from "@/components/chat/chat-query-keys";
import { api } from "@/lib/api";
import type { ChatThread } from "@/lib/types/chat";
import { cn } from "@/lib/utils";

type ChatHistoryNavProps = {
  projectId: string;
  activeThreadId?: string;
  onSelectThread: (threadId: string) => void;
  onCreateSession: (thread: ChatThread) => void;
  onActiveThreadDeleted: () => void;
};

export function ChatHistoryNav({
  projectId,
  activeThreadId,
  onSelectThread,
  onCreateSession,
  onActiveThreadDeleted,
}: ChatHistoryNavProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const createSessionMutation = useMutation({
    mutationFn: () => api.createThread(undefined, projectId),
    onSuccess: (thread) => {
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) => [
        thread,
        ...(current ?? []),
      ]);
      onCreateSession(thread);
    },
    onError: () => {
      setError("Could not create chat.");
    },
  });

  function createSession() {
    setError(null);
    createSessionMutation.mutate();
  }

  return (
    <div className="flex min-h-0 max-h-[min(24rem,52%)] flex-col">
      <section className="flex min-h-0 flex-1 flex-col" aria-label="Chats">
        <header className="shrink-0 px-3 py-2">
          <div className="flex items-center gap-2 px-1.5 py-1.5">
            <MessageSquare
              className="size-4 shrink-0 text-[var(--cockpit-workflow-icon)]"
              aria-hidden
            />
            <h2 className="min-w-0 flex-1 text-sm font-semibold">Chats</h2>
            <button
              type="button"
              className={cn(
                "shrink-0 text-muted-foreground transition-colors",
                "hover:text-foreground",
                "disabled:pointer-events-none disabled:opacity-50",
              )}
              disabled={createSessionMutation.isPending}
              aria-label="New chat"
              title="New chat"
              onClick={createSession}
            >
              <Plus className="size-4" aria-hidden />
            </button>
          </div>
          {error ? <p className="mt-1 px-1.5 text-xs text-destructive">{error}</p> : null}
        </header>

        <ChatSessionList
          variant="nav"
          activeThreadId={activeThreadId}
          projectId={projectId}
          onSelectThread={onSelectThread}
          onCreateSession={onCreateSession}
          onActiveThreadDeleted={onActiveThreadDeleted}
        />
      </section>
    </div>
  );
}
