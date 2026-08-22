import type { ToolStatusEvent } from "@/lib/chat-events";
import { answerTraceItems, type AnswerTraceTone } from "@/lib/answer-trace";
import type { Citation } from "@/lib/types/citation";
import { cn } from "@/lib/utils";
import { Globe2 } from "lucide-react";

type AnswerTraceProps = {
  agentMode?: boolean;
  messageData?: Record<string, unknown> | null;
  toolEvents?: ToolStatusEvent[];
  citations?: Citation[];
};

const toneClassName: Record<AnswerTraceTone, string> = {
  context:
    "border-[var(--brand-border)] bg-[var(--brand-subtle)] text-[var(--brand-text)]",
  documents:
    "border-[var(--ok-border)] bg-[var(--ok-bg)] text-[var(--ok-text)]",
  knowledge:
    "border-border bg-muted/60 text-foreground",
  web:
    "border-[var(--brand-border)] bg-[var(--brand-subtle)] text-[var(--brand-text)]",
  tools:
    "border-[var(--brand-border)] bg-[var(--brand-subtle)] text-[var(--brand-text)]",
  model: "border-border bg-muted/60 text-foreground",
};

export function AnswerTrace({
  agentMode = false,
  messageData,
  toolEvents = [],
  citations = [],
}: AnswerTraceProps) {
  const items = answerTraceItems({
    agentMode,
    messageData,
    toolEvents,
    citations,
  });

  if (items.length === 0) return null;

  return (
    <div
      aria-label="Answer trace"
      className="mt-3 flex flex-wrap items-center gap-1.5 text-[0.6875rem]"
    >
      {items.map((item) => (
        <span
          key={item.key}
          title={item.title}
          className={cn(
            "inline-flex max-w-full items-center gap-1.5 rounded-full border px-2 py-0.5 leading-5",
            toneClassName[item.tone],
          )}
        >
          {item.tone === "web" ? (
            <Globe2
              aria-label="Internet source"
              role="img"
              className="size-3 shrink-0"
            />
          ) : null}
          <span className="truncate">{item.label}</span>
        </span>
      ))}
    </div>
  );
}
