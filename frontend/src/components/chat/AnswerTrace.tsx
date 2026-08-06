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
    "border-[color-mix(in_oklch,var(--sw-beam)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-beam)_14%,transparent)] text-[var(--sw-beam)]",
  documents:
    "border-[color-mix(in_oklch,var(--sw-positive)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-positive)_14%,transparent)] text-[var(--sw-positive)]",
  knowledge:
    "border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_14%,transparent)] text-[var(--sw-caution)]",
  tools:
    "border-[color-mix(in_oklch,var(--sw-facet-blue)_45%,transparent)] bg-[color-mix(in_oklch,var(--sw-facet-blue)_18%,transparent)] text-[var(--sw-beam)]",
  model: "border-border bg-muted/60 text-muted-foreground",
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
