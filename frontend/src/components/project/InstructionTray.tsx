import { useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";

import { StreamingIndicator } from "@/components/chat/StreamingIndicator";
import { Button } from "@/components/ui/button";
import type { InstructionItem } from "@/lib/instruction-tray";
import { cn } from "@/lib/utils";

export function InstructionTray({
  items,
  isApplying = false,
  error = null,
  onRemove,
  onClearAll,
  onApply,
}: {
  items: InstructionItem[];
  isApplying?: boolean;
  /** Why the last apply failed. Belongs here, next to the button that failed. */
  error?: string | null;
  onRemove: (id: string) => void;
  onClearAll: () => void;
  onApply: () => void;
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (items.length === 0) return null;

  const label = items.length === 1 ? "1 change" : `${items.length} changes`;

  return (
    <section
      data-instruction-ui
      aria-label="Queued changes"
      className="border-b print:hidden"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
        <button
          type="button"
          className="flex min-w-0 items-center gap-1.5 text-xs font-semibold"
          onClick={() => setIsCollapsed((current) => !current)}
          aria-expanded={!isCollapsed}
        >
          {isCollapsed ? (
            <ChevronUp className="size-3.5 shrink-0" aria-hidden />
          ) : (
            <ChevronDown className="size-3.5 shrink-0" aria-hidden />
          )}
          <span className="truncate">{label} queued</span>
        </button>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={onClearAll}
            disabled={isApplying}
          >
            Clear all
          </Button>
          <Button
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={onApply}
            disabled={isApplying}
          >
            {isApplying ? "Applying…" : `Apply ${label}`}
          </Button>
        </div>
      </header>
      {isApplying ? (
        <div className="border-t px-3 py-2">
          <StreamingIndicator
            className="w-full"
            message="Revising the sections you marked…"
          />
        </div>
      ) : null}
      {error ? (
        <p className="border-t bg-destructive/5 px-3 py-1.5 text-xs text-destructive">
          {error}
        </p>
      ) : null}
      {isCollapsed ? null : (
        <ul className="max-h-48 overflow-y-auto border-t">
          {items.map((item) => (
            <li
              key={item.id}
              className={cn(
                "sw-table-row border-b px-3 py-1.5 text-xs text-muted-foreground last:border-b-0",
                item.error && "bg-destructive/5",
              )}
            >
              <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1 truncate" title={item.instruction}>
                  <span className="font-medium text-foreground">
                    {item.sectionHeading}
                  </span>
                  <span className="text-muted-foreground"> — {item.instruction}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  className="shrink-0"
                  aria-label={`Remove instruction: ${item.instruction}`}
                  onClick={() => onRemove(item.id)}
                  disabled={isApplying}
                >
                  <X className="size-3.5" aria-hidden />
                </Button>
              </div>
              {item.error ? (
                <p className="mt-0.5 text-destructive">{item.error}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
