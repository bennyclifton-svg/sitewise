import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, MessageSquarePlus, Pencil, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { ChatThread } from "@/lib/types/chat";
import { cn } from "@/lib/utils";

type ChatSessionListProps = {
  activeThreadId?: string;
  projectId?: string | null;
};

const chatThreadQueryKey = ["chat", "threads"] as const;

export function ChatSessionList({ activeThreadId, projectId }: ChatSessionListProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const threadsQuery = useQuery({
    queryKey: chatThreadQueryKey,
    queryFn: api.listThreads,
  });
  const threads = useMemo(
    () =>
      projectId
        ? (threadsQuery.data ?? []).filter((thread) => thread.project_id === projectId)
        : (threadsQuery.data ?? []),
    [projectId, threadsQuery.data],
  );

  const createSessionMutation = useMutation({
    mutationFn: () => api.createThread(undefined, projectId ?? undefined),
    onSuccess: (thread) => {
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) => [
        thread,
        ...(current ?? []),
      ]);
      navigate(`/chat/${thread.id}`);
    },
    onError: () => {
      setError("Could not create session.");
    },
  });

  const renameSessionMutation = useMutation({
    mutationFn: ({ threadId, title }: { threadId: string; title: string }) =>
      api.updateThreadTitle(threadId, title),
    onSuccess: (thread) => {
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) =>
        (current ?? []).map((item) => (item.id === thread.id ? thread : item)),
      );
      setEditingId(null);
    },
    onError: () => {
      setError("Could not rename session.");
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: async (threadId: string) => {
      await api.deleteThread(threadId);
      return threadId;
    },
    onSuccess: (threadId) => {
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) =>
        (current ?? []).filter((thread) => thread.id !== threadId),
      );
      setConfirmingDeleteId(null);
      if (threadId === activeThreadId) navigate("/");
    },
    onError: () => {
      setError("Could not delete session.");
    },
  });

  function createSession() {
    setError(null);
    createSessionMutation.mutate();
  }

  function saveTitle(threadId: string) {
    const title = draftTitle.trim();
    if (!title) return;
    setError(null);
    renameSessionMutation.mutate({ threadId, title });
  }

  function deleteSession(threadId: string) {
    setError(null);
    deleteSessionMutation.mutate(threadId);
  }

  const visibleError =
    error ?? (threadsQuery.isError ? "Could not load sessions." : null);

  return (
    <aside className="grid gap-3 rounded-md border p-3" aria-label="Chat sessions">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Sessions</h2>
        <Button
          type="button"
          size="icon-sm"
          variant="outline"
          aria-label="New session"
          title="New session"
          disabled={createSessionMutation.isPending}
          onClick={createSession}
        >
          <MessageSquarePlus className="size-4" aria-hidden />
        </Button>
      </div>

      {visibleError ? <p className="text-xs text-destructive">{visibleError}</p> : null}

      <div className="grid gap-2">
        {threads.map((thread) => {
          const title = thread.title ?? "Untitled chat";
          const isEditing = editingId === thread.id;
          const isConfirmingDelete = confirmingDeleteId === thread.id;
          return (
            <div
              key={thread.id}
              className={cn(
                "grid gap-2 rounded-md border p-2",
                thread.id === activeThreadId && "border-primary/50 bg-muted/40",
              )}
            >
              {isEditing ? (
                <div className="flex gap-1">
                  <Input
                    aria-label="Thread title"
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                  />
                  <Button
                    type="button"
                    size="icon-sm"
                    aria-label="Save title"
                    title="Save title"
                    disabled={renameSessionMutation.isPending}
                    onClick={() => saveTitle(thread.id)}
                  >
                    <Check className="size-4" aria-hidden />
                  </Button>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="outline"
                    aria-label="Cancel rename"
                    title="Cancel rename"
                    onClick={() => setEditingId(null)}
                  >
                    <X className="size-4" aria-hidden />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <Link
                    to={`/chat/${thread.id}`}
                    className="min-w-0 flex-1 truncate text-sm hover:underline"
                  >
                    {title}
                  </Link>
                  {isConfirmingDelete ? (
                    <>
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="destructive"
                        aria-label={`Confirm delete ${title}`}
                        title="Confirm delete"
                        disabled={deleteSessionMutation.isPending}
                        onClick={() => deleteSession(thread.id)}
                      >
                        <Check className="size-3" aria-hidden />
                      </Button>
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Cancel delete ${title}`}
                        title="Cancel delete"
                        onClick={() => setConfirmingDeleteId(null)}
                      >
                        <X className="size-3" aria-hidden />
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Rename ${title}`}
                        title="Rename"
                        onClick={() => {
                          setEditingId(thread.id);
                          setDraftTitle(title);
                        }}
                      >
                        <Pencil className="size-3" aria-hidden />
                      </Button>
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Delete ${title}`}
                        title="Delete"
                        onClick={() => setConfirmingDeleteId(thread.id)}
                      >
                        <Trash2 className="size-3" aria-hidden />
                      </Button>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
