import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { ChatSessionList } from "@/components/chat/ChatSessionList";
import { ThreadTitle } from "@/components/chat/ThreadTitle";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadLoading, setThreadLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadErrorKind, setLoadErrorKind] = useState<"auth" | "forbidden" | "not-found" | "generic">(
    "generic",
  );

  useEffect(() => {
    if (!threadId) return;
    const id = threadId;

    let cancelled = false;

    async function loadThread() {
      setThreadLoading(true);
      try {
        const data = await api.getThread(id);
        if (!cancelled) setThread(data);
      } catch (error) {
        if (!cancelled) {
          setLoadError(formatLoadError(error));
          setLoadErrorKind(classifyLoadError(error));
        }
      } finally {
        if (!cancelled) setThreadLoading(false);
      }
    }

    void loadThread();
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  useEffect(() => {
    if (!threadId) return;
    const id = threadId;

    let cancelled = false;

    async function loadMessages() {
      setMessagesLoading(true);
      setLoadError(null);
      try {
        const data = await api.getThreadMessages(id);
        if (!cancelled) setMessages(data);
      } catch (error) {
        if (!cancelled) {
          setLoadError(formatLoadError(error));
          setLoadErrorKind(classifyLoadError(error));
        }
      } finally {
        if (!cancelled) setMessagesLoading(false);
      }
    }

    void loadMessages();
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const isLoading = threadLoading || messagesLoading;

  async function refreshConversation() {
    if (!threadId) return;
    try {
      const [threadData, messageData] = await Promise.all([
        api.getThread(threadId),
        api.getThreadMessages(threadId),
      ]);
      setThread(threadData);
      // Keep ChatPanel mounted; remounting resets scroll through full history.
      setMessages(messageData);
    } catch {
      // Best-effort refresh after streaming completes.
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {threadLoading ? (
            <div className="space-y-2">
              <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
              <div className="h-4 w-64 animate-pulse rounded-md bg-muted" />
            </div>
          ) : thread ? (
            <>
              <ThreadTitle
                threadId={thread.id}
                initialTitle={thread.title}
                onTitleChange={(title) =>
                  setThread((current) => (current ? { ...current, title } : current))
                }
              />
              <p className="mt-1 text-sm text-muted-foreground">
                Grounded answers with verifiable citations from your project corpus.
              </p>
            </>
          ) : (
            <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
          )}
        </div>
        <Button asChild variant="outline">
          <Link to="/">Back home</Link>
        </Button>
      </div>

      <ChatSessionList
        activeThreadId={threadId}
        projectId={thread?.project_id ?? null}
      />

      <Card>
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
          <CardDescription>
            Click any citation chip to inspect the source passage alongside the answer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground" role="status">
              Loading conversation…
            </p>
          ) : loadError ? (
            <LoadErrorState kind={loadErrorKind} message={loadError} />
          ) : threadId ? (
            <ChatPanel
              key={threadId}
              threadId={threadId}
              initialMessages={messages}
              onConversationUpdate={() => void refreshConversation()}
              agentMode={thread?.project_id != null}
              projectId={thread?.project_id ?? null}
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function classifyLoadError(
  error: unknown,
): "auth" | "forbidden" | "not-found" | "generic" {
  if (error instanceof ApiError) {
    if (error.status === 401) return "auth";
    if (error.status === 403) return "forbidden";
    if (error.status === 404) return "not-found";
  }
  return "generic";
}

function formatLoadError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your session has expired. Sign in again to continue.";
    }
    if (error.status === 403) {
      return "You do not have access to this conversation.";
    }
    if (error.status === 404) {
      return "Conversation not found.";
    }
    if (error.isNetworkError) {
      return "Could not reach the backend. Is it running on port 8000?";
    }
    return error.message;
  }
  return "Could not load this conversation.";
}

function LoadErrorState({
  kind,
  message,
}: {
  kind: "auth" | "forbidden" | "not-found" | "generic";
  message: string;
}) {
  return (
    <div className="space-y-3" role="alert">
      <p className="text-sm text-destructive">{message}</p>
      {kind === "auth" ? (
        <Button asChild variant="outline" size="sm">
          <Link to="/login">Sign in again</Link>
        </Button>
      ) : null}
      {kind === "not-found" || kind === "forbidden" ? (
        <Button asChild variant="outline" size="sm">
          <Link to="/">Back home</Link>
        </Button>
      ) : null}
    </div>
  );
}
