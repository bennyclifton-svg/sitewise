import { useMutation, useQueryClient } from "@tanstack/react-query";
import { History, MessageSquarePlus } from "lucide-react";
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
      <div className="shrink-0 px-3 py-2">
        <button
          type="button"
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-sm transition-colors",
            "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
          )}
          disabled={createSessionMutation.isPending}
          aria-label="New chat"
          onClick={createSession}
        >
          <MessageSquarePlus className="size-4 shrink-0 text-sky-600" aria-hidden />
          <span className="truncate">New Chat</span>
        </button>
        {error ? <p className="mt-1 px-1.5 text-xs text-destructive">{error}</p> : null}
      </div>

      <section className="flex min-h-0 flex-1 flex-col" aria-label="Chat history">
        <header className="flex shrink-0 items-center gap-2 px-3 py-2">
          <History className="size-4 shrink-0" aria-hidden />
          <h2 className="text-sm font-semibold">History</h2>
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
