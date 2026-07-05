import { History } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ChatSessionList } from "@/components/chat/ChatSessionList";
import { Button } from "@/components/ui/button";
import type { ChatThread } from "@/lib/types/chat";

type ChatHistoryPopoverProps = {
  activeThreadId?: string;
  projectId: string;
  onSelectThread: (threadId: string) => void;
  onCreateSession: (thread: ChatThread) => void;
  onActiveThreadDeleted: () => void;
};

export function ChatHistoryPopover({
  activeThreadId,
  projectId,
  onSelectThread,
  onCreateSession,
  onActiveThreadDeleted,
}: ChatHistoryPopoverProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Chat history"
        title="Chat history"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <History className="size-4" aria-hidden />
      </Button>

      {open ? (
        <div
          className="absolute top-full left-0 z-50 mt-1 w-[min(18rem,calc(100vw-2rem))] rounded-md border bg-popover p-2 shadow-md"
          role="dialog"
          aria-label="Chat history"
        >
          <ChatSessionList
            variant="popover"
            activeThreadId={activeThreadId}
            projectId={projectId}
            onSelectThread={(threadId) => {
              onSelectThread(threadId);
              setOpen(false);
            }}
            onCreateSession={(thread) => {
              onCreateSession(thread);
              setOpen(false);
            }}
            onActiveThreadDeleted={() => {
              onActiveThreadDeleted();
              setOpen(false);
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
