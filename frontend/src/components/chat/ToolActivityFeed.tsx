import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import type { ToolStatusEvent } from "@/lib/chat-events";
import { toolActivityLines } from "@/lib/tool-activity";

type ToolActivityFeedProps = {
  events: ToolStatusEvent[];
};

const VISIBLE_LINES = 2;

export function ToolActivityFeed({ events }: ToolActivityFeedProps) {
  const lines = toolActivityLines(events);
  const [expanded, setExpanded] = useState(false);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const hasRunning = lines.some((line) => line.state === "running");
  const visible = expanded ? lines : lines.slice(-VISIBLE_LINES);
  const latestLineLabel = lines.at(-1)?.label;

  useEffect(() => {
    if (expanded) return;
    const node = scrollerRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [expanded, latestLineLabel, lines.length]);

  if (lines.length === 0) return null;

  return (
    <div className="mt-3 max-w-lg" aria-label="Tool activity">
      <div
        ref={scrollerRef}
        className={cn(
          "relative overflow-hidden font-mono text-[11px] leading-5 tracking-wide text-muted-foreground",
          expanded ? "max-h-40 overflow-y-auto" : "h-10",
          !expanded && lines.length > VISIBLE_LINES
            ? "[mask-image:linear-gradient(to_bottom,transparent,black_35%,black)]"
            : null,
        )}
        role="status"
        aria-live="polite"
        aria-busy={hasRunning}
      >
        <ul className="flex flex-col justify-end gap-0.5">
          {visible.map((line, index) => {
            const isLatest = index === visible.length - 1;
            return (
              <li
                key={line.id}
                className={cn(
                  "flex min-w-0 items-baseline gap-2 transition-opacity duration-300 ease-out",
                  isLatest ? "opacity-100" : "opacity-45",
                  line.state === "error" && "text-destructive",
                )}
              >
                <span
                  className={cn(
                    "mt-[0.35rem] size-1 shrink-0 rounded-full",
                    line.state === "running" &&
                      "bg-[var(--azure)] animate-pulse",
                    line.state === "done" && "bg-muted-foreground/45",
                    line.state === "error" && "bg-destructive",
                  )}
                  aria-hidden
                />
                <span className="min-w-0 truncate" title={line.detail ?? line.label}>
                  {line.label}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {lines.length > VISIBLE_LINES ? (
        <button
          type="button"
          className="mt-1 font-mono text-[10px] tracking-[0.12em] text-muted-foreground/80 uppercase transition-colors hover:text-foreground"
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Hide log" : `Show all · ${lines.length}`}
        </button>
      ) : null}
    </div>
  );
}
