import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, MessageSquarePlus, MoreHorizontal, Pencil, Trash2, X } from "lucide-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useChatActivity } from "@/components/chat/chat-activity";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatThreadQueryKey } from "@/components/chat/chat-query-keys";
import { api } from "@/lib/api";
import type { ChatThread } from "@/lib/types/chat";
import { cn } from "@/lib/utils";

const ChatThreadActionsMenu = lazy(() =>
  import("@/components/chat/ChatThreadActionsMenu").then((module) => ({
    default: module.ChatThreadActionsMenu,
  })),
);

type ChatSessionListProps = {
  activeThreadId?: string;
  projectId?: string | null;
  variant?: "default" | "popover" | "nav";
  onSelectThread?: (threadId: string) => void;
  onCreateSession?: (thread: ChatThread) => void;
  onActiveThreadDeleted?: () => void;
};

type ThreadRecencyGroup = "today" | "yesterday" | "previous7" | "older";

const GROUP_LABELS: Record<ThreadRecencyGroup, string> = {
  today: "Today",
  yesterday: "Yesterday",
  previous7: "Previous 7 days",
  older: "Older",
};

function groupThreadsByRecency(threads: ChatThread[]): Record<ThreadRecencyGroup, ChatThread[]> {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfPrevious7 = new Date(startOfToday);
  startOfPrevious7.setDate(startOfPrevious7.getDate() - 7);

  const groups: Record<ThreadRecencyGroup, ChatThread[]> = {
    today: [],
    yesterday: [],
    previous7: [],
    older: [],
  };

  const sorted = [...threads].sort(
    (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
  );

  for (const thread of sorted) {
    const updatedAt = new Date(thread.updated_at);
    if (updatedAt >= startOfToday) {
      groups.today.push(thread);
    } else if (updatedAt >= startOfYesterday) {
      groups.yesterday.push(thread);
    } else if (updatedAt >= startOfPrevious7) {
      groups.previous7.push(thread);
    } else {
      groups.older.push(thread);
    }
  }

  return groups;
}

export function ChatSessionList({
  activeThreadId,
  projectId,
  variant = "default",
  onSelectThread,
  onCreateSession,
  onActiveThreadDeleted,
}: ChatSessionListProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [menuThreadId, setMenuThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isPopover = variant === "popover";
  const isNav = variant === "nav";
  const isCompactList = isPopover || isNav;
  const isEmbedded = Boolean(onSelectThread);
  const { busyThreadIds } = useChatActivity();

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
  const groupedThreads = useMemo(() => groupThreadsByRecency(threads), [threads]);

  const createSessionMutation = useMutation({
    mutationFn: () => api.createThread(undefined, projectId ?? undefined),
    onSuccess: (thread) => {
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) => [
        thread,
        ...(current ?? []),
      ]);
      if (onCreateSession) {
        onCreateSession(thread);
        return;
      }
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
      if (threadId === activeThreadId) {
        if (onActiveThreadDeleted) {
          onActiveThreadDeleted();
          return;
        }
        navigate("/");
      }
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

  function openThread(threadId: string) {
    if (onSelectThread) {
      onSelectThread(threadId);
      return;
    }
  }

  const visibleError =
    error ?? (threadsQuery.isError ? "Could not load sessions." : null);

  function renderThreadRow(thread: ChatThread) {
    const title = thread.title ?? "Untitled chat";
    const isEditing = editingId === thread.id;
    const isConfirmingDelete = confirmingDeleteId === thread.id;
    const isLive = busyThreadIds.has(thread.id);

    return (
      <div
        key={thread.id}
        className={cn(
          isNav
            ? cn(
                "flex w-full min-w-0 items-center gap-1 rounded-sm px-1.5 py-0.5 transition-colors",
                thread.id === activeThreadId
                  ? "bg-[var(--brand-subtle)] text-foreground"
                  : "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
              )
            : "grid gap-2 rounded-md border p-2",
          !isNav && thread.id === activeThreadId && "border-primary/50 bg-[var(--brand-subtle)]",
          isPopover && "border-transparent p-1.5",
        )}
      >
        {isEditing ? (
          <div className={cn("flex gap-1", isNav && "w-full")}>
            <Input
              aria-label="Thread title"
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              className={isNav ? "h-6 text-xs" : undefined}
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
          <div className="flex min-w-0 flex-1 items-center gap-1">
            {isEmbedded ? (
              <button
                type="button"
                aria-busy={isLive || undefined}
                className={cn(
                  "min-w-0 flex-1 truncate text-left",
                  isNav ? "text-xs leading-5 hover:text-foreground" : "text-sm hover:underline",
                  isLive && "streaming-status-live",
                )}
                onClick={() => openThread(thread.id)}
              >
                {title}
              </button>
            ) : (
              <Link
                to={`/chat/${thread.id}`}
                aria-busy={isLive || undefined}
                className={cn(
                  "min-w-0 flex-1 truncate text-sm hover:underline",
                  isLive && "streaming-status-live",
                )}
              >
                {title}
              </Link>
            )}
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
            ) : isNav ? (
              menuThreadId === thread.id ? (
                <Suspense
                  fallback={
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="ghost"
                      aria-label={`Actions for ${title}`}
                      title="Actions"
                      disabled
                    >
                      <MoreHorizontal className="size-3" aria-hidden />
                    </Button>
                  }
                >
                  <ChatThreadActionsMenu
                    title={title}
                    onClose={() => setMenuThreadId(null)}
                    onRename={() => {
                      setEditingId(thread.id);
                      setDraftTitle(title);
                    }}
                    onDelete={() => setConfirmingDeleteId(thread.id)}
                  />
                </Suspense>
              ) : (
                  <Button
                    type="button"
                    size="icon-xs"
                    variant="ghost"
                    aria-label={`Actions for ${title}`}
                    title="Actions"
                    aria-expanded="false"
                    onClick={() => setMenuThreadId(thread.id)}
                  >
                    <MoreHorizontal className="size-3" aria-hidden />
                  </Button>
              )
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
  }

  const threadGroups = isPopover
    ? (Object.keys(GROUP_LABELS) as ThreadRecencyGroup[]).filter(
        (group) => groupedThreads[group].length > 0,
      )
    : null;
  const sortedThreads = useMemo(
    () =>
      [...threads].sort(
        (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
      ),
    [threads],
  );

  const content = (
    <>
      {!isCompactList ? (
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
      ) : null}

      {visibleError ? <p className="text-xs text-destructive">{visibleError}</p> : null}

      <div className={isNav ? "flex flex-col" : "grid gap-2"}>
        {isPopover && threadGroups
          ? threadGroups.map((group) => (
              <section key={group} className="grid gap-1">
                <h3 className="px-1 text-[0.6875rem] font-medium tracking-wide text-muted-foreground uppercase">
                  {GROUP_LABELS[group]}
                </h3>
                {groupedThreads[group].map(renderThreadRow)}
              </section>
            ))
          : (isNav ? sortedThreads : threads).map(renderThreadRow)}
      </div>
    </>
  );

  if (isPopover) {
    return (
      <div className="max-h-[min(24rem,calc(100vh-12rem))] overflow-y-auto" aria-label="Chat sessions">
        {content}
      </div>
    );
  }

  if (isNav) {
    return (
      <div className="cockpit-scroll min-h-0 flex-1 overflow-y-auto px-3 pb-2" aria-label="Chat sessions">
        {content}
      </div>
    );
  }

  return (
    <aside className="grid gap-3 rounded-md border p-3" aria-label="Chat sessions">
      {content}
    </aside>
  );
}
