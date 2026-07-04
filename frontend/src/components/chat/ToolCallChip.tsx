import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { ToolStatusEvent } from "@/lib/chat-events";

type ToolCallChipProps = {
  event: ToolStatusEvent;
};

const stateTone: Record<ToolStatusEvent["state"], string> = {
  running: "border-blue-200 bg-blue-50 text-blue-800",
  done: "border-emerald-200 bg-emerald-50 text-emerald-800",
  error: "border-destructive/30 bg-destructive/10 text-destructive",
};

const stateLabel: Record<ToolStatusEvent["state"], string> = {
  running: "Running",
  done: "Done",
  error: "Error",
};

export function ToolCallChip({ event }: ToolCallChipProps) {
  const [expanded, setExpanded] = useState(false);
  const Icon =
    event.state === "running"
      ? Loader2
      : event.state === "done"
        ? CheckCircle2
        : AlertCircle;
  const ToggleIcon = expanded ? ChevronDown : ChevronRight;

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors",
          stateTone[event.state],
        )}
        aria-expanded={expanded}
        aria-label={`${stateLabel[event.state]} ${event.tool}`}
        title={event.message}
        onClick={() => setExpanded((current) => !current)}
      >
        <Icon
          className={cn("size-3", event.state === "running" && "animate-spin")}
          aria-hidden
        />
        <span className="max-w-44 truncate">{event.tool}</span>
        {event.percent !== undefined ? (
          <span className="tabular-nums">{Math.round(event.percent)}%</span>
        ) : null}
        <ToggleIcon className="size-3" aria-hidden />
      </button>
      {expanded ? (
        <span className="max-w-xs rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground shadow-xs">
          {event.message}
          {event.stage ? ` · Stage: ${event.stage}` : null}
        </span>
      ) : null}
    </span>
  );
}
