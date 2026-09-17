import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ChatComposer } from "@/components/chat/ChatComposer";
import { chatThreadQueryKey } from "@/components/chat/chat-query-keys";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatThread } from "@/lib/types/chat";

export function NewChatPanel({ projectId, onCreated, collapsed = false, onCollapsedChange }: {
  projectId: string;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  onCreated: (thread: ChatThread, text: string) => void;
}) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(true);
  const pending = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);

  async function submit() {
    const text = input.trim();
    if (!text || pending.current) return;
    pending.current = true;
    setCreating(true);
    setError(null);
    try {
      const thread = await api.createThread(undefined, projectId);
      queryClient.setQueryData<ChatThread[]>(chatThreadQueryKey, (current) => [
        thread, ...(current ?? []).filter((item) => item.id !== thread.id),
      ]);
      // Navigation away must not send the draft or reopen this conversation.
      if (active.current) onCreated(thread, text);
    } catch {
      if (active.current) setError("Could not create chat. Try sending again.");
    } finally {
      pending.current = false;
      if (active.current) setCreating(false);
    }
  }

  return (
    <div className={cn(
      "flex flex-col gap-3 px-4 pb-3 lg:px-6",
      collapsed ? "shrink-0 pt-2" : "min-h-0 flex-1",
    )} aria-label="New chat">
      {!collapsed ? <div className="min-h-0 flex-1" /> : null}
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      {creating ? <p role="status" className="text-sm text-muted-foreground">Starting chat…</p> : null}
      <fieldset disabled={creating} className="min-w-0">
        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={() => void submit()}
          isBusy={false}
          collapsed={collapsed}
          collapsible
          onCollapsedChange={onCollapsedChange}
        />
      </fieldset>
    </div>
  );
}
