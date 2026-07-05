import type { ToolStatusEvent } from "@/lib/chat-events";
import { answerTraceItems, type AnswerTraceTone } from "@/lib/answer-trace";
import type { Citation } from "@/lib/types/citation";
import { cn } from "@/lib/utils";

type AnswerTraceProps = {
  agentMode?: boolean;
  messageData?: Record<string, unknown> | null;
  toolEvents?: ToolStatusEvent[];
  citations?: Citation[];
};

const toneClassName: Record<AnswerTraceTone, string> = {
  context:
    "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-100",
  documents:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/35 dark:text-emerald-100",
  knowledge:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-100",
  tools:
    "border-violet-200 bg-violet-50 text-violet-900 dark:border-violet-900/60 dark:bg-violet-950/35 dark:text-violet-100",
  model:
    "border-border bg-muted/60 text-muted-foreground dark:bg-muted/30",
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
            "inline-flex max-w-full items-center rounded-full border px-2 py-0.5 leading-5",
            toneClassName[item.tone],
          )}
        >
          <span className="truncate">{item.label}</span>
        </span>
      ))}
    </div>
  );
}
