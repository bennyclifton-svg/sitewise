import { CircleStop, Mic, Send } from "lucide-react";
import { useEffect, useRef } from "react";

import { AgentRuntimeSelector } from "@/components/chat/AgentRuntimeSelector";
import { LlmModelSelector } from "@/components/LlmModelSelector";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const MIN_TEXTAREA_ROWS = 1;
const MAX_TEXTAREA_ROWS = 6;

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  isBusy: boolean;
  agentMode?: boolean;
  crossProject?: boolean;
  onCrossProjectChange?: (value: boolean) => void;
  showScopeControls?: boolean;
};

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  isBusy,
  agentMode = false,
  crossProject = false,
  onCrossProjectChange,
  showScopeControls = false,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const lineHeight = Number.parseInt(getComputedStyle(textarea).lineHeight, 10) || 20;
    const maxHeight = lineHeight * MAX_TEXTAREA_ROWS;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, [value]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isBusy && value.trim()) {
        onSubmit();
      }
    }
  }

  return (
    <div className="shrink-0 rounded-lg border bg-background shadow-sm">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your project documents…"
        disabled={isBusy}
        aria-label="Message"
        rows={MIN_TEXTAREA_ROWS}
        className="block w-full resize-none border-0 bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-70"
      />

      <div className="flex items-center justify-between gap-2 border-t px-2 py-1.5">
        {showScopeControls ? (
          <div
            className="inline-flex shrink-0 rounded-md border p-0.5 text-xs"
            role="group"
            aria-label="Search scope"
          >
            <button
              type="button"
              className={cn(
                "rounded px-2 py-0.5 transition-colors",
                !crossProject ? "bg-muted font-medium" : "text-muted-foreground hover:text-foreground",
              )}
              aria-pressed={!crossProject}
              onClick={() => onCrossProjectChange?.(false)}
            >
              Project
            </button>
            <button
              type="button"
              className={cn(
                "rounded px-2 py-0.5 transition-colors",
                crossProject ? "bg-muted font-medium" : "text-muted-foreground hover:text-foreground",
              )}
              aria-pressed={crossProject}
              onClick={() => onCrossProjectChange?.(true)}
            >
              Cross-project
            </button>
          </div>
        ) : (
          <span />
        )}

        <div className="flex min-w-0 items-center gap-0.5">
          {agentMode ? <AgentRuntimeSelector compact /> : null}
          <LlmModelSelector compact />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            disabled
            aria-label="Voice input coming soon"
            title="Voice input coming soon"
          >
            <Mic className="size-4" aria-hidden />
          </Button>
          {isBusy ? (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Stop"
              title="Stop"
              onClick={() => onStop?.()}
            >
              <CircleStop className="size-4" aria-hidden />
            </Button>
          ) : (
            <Button
              type="button"
              size="icon-sm"
              aria-label="Send message"
              title="Send message"
              disabled={value.trim() === ""}
              onClick={onSubmit}
            >
              <Send className="size-4" aria-hidden />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
