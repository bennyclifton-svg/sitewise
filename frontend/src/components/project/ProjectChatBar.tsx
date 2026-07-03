import { Bot, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

export function ProjectChatBar({
  thread,
  messages,
  chatRevision,
  chatLoading,
  projectTitle,
  crossProject,
  scopeLabel,
  onCrossProjectChange,
  onConversationUpdate,
}: {
  thread: ChatThread | null;
  messages: ChatMessage[];
  chatRevision: number;
  chatLoading: boolean;
  projectTitle: string;
  crossProject: boolean;
  scopeLabel: string;
  onCrossProjectChange: (value: boolean) => void;
  onConversationUpdate: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className="border-t bg-background" aria-label="Project chat">
      <header className="flex min-h-14 items-center justify-between gap-3 px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-md bg-muted">
            <Bot className="size-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">Clerk</h2>
            <p className="truncate text-xs text-muted-foreground">
              {thread ? thread.title ?? `${projectTitle} project chat` : "Opening project chat"}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={crossProject ? "secondary" : "outline"}>
            {crossProject ? "Cross-project" : "Project"}
          </Badge>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setExpanded((current) => !current)}
          >
            {expanded ? (
              <ChevronDown className="size-4" aria-hidden />
            ) : (
              <ChevronUp className="size-4" aria-hidden />
            )}
            {expanded ? "Hide" : "Chat"}
          </Button>
        </div>
      </header>

      {expanded ? (
        <div className="border-t p-4">
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
              compact
              agentMode
              projectId={thread.project_id}
              showScopeControls
              scopeLabel={scopeLabel}
              crossProject={crossProject}
              onCrossProjectChange={onCrossProjectChange}
            />
          )}
        </div>
      ) : null}
    </section>
  );
}
