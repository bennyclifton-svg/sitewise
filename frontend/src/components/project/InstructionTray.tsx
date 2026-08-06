import { useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";

import { StreamingIndicator } from "@/components/chat/StreamingIndicator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { truncateQuote, type InstructionItem } from "@/lib/instruction-tray";
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
    // Sticky over scrolling document text, so it needs the opaque overlay token:
    // `--background` is transparent inside the dark cockpit panels.
    <section
      data-instruction-ui
      aria-label="Queued changes"
      className="sw-surface sw-contact sticky bottom-0 z-40 text-popover-foreground hover:translate-y-0 print:hidden"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2">
        <button
          type="button"
          className="flex items-center gap-2 text-sm font-semibold"
          onClick={() => setIsCollapsed((current) => !current)}
          aria-expanded={!isCollapsed}
        >
          {isCollapsed ? (
            <ChevronUp className="size-4" aria-hidden />
          ) : (
            <ChevronDown className="size-4" aria-hidden />
          )}
          {label} queued
        </button>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onClearAll} disabled={isApplying}>
            Clear all
          </Button>
          <Button size="sm" onClick={onApply} disabled={isApplying}>
            {isApplying ? "Applying…" : `Apply ${label}`}
          </Button>
        </div>
      </header>
      {isApplying ? (
        <div className="border-b px-4 py-2.5">
          <StreamingIndicator
            className="w-full"
            message="Revising the sections you marked…"
          />
        </div>
      ) : null}
      {error ? (
        <p className="border-b bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {isCollapsed ? null : (
        <ul className="max-h-64 divide-y overflow-y-auto">
          {items.map((item) => (
            <li
              key={item.id}
              className={cn(
                "flex items-start justify-between gap-3 px-4 py-2.5",
                item.error && "bg-destructive/5",
              )}
            >
              <div className="min-w-0">
                <Badge variant="secondary" className="mb-1">
                  {item.sectionHeading}
                </Badge>
                <blockquote className="border-l-2 pl-2 text-xs text-muted-foreground">
                  {truncateQuote(item.quotedText, 120)}
                </blockquote>
                <p className="mt-1 text-sm">{item.instruction}</p>
                {item.error ? (
                  <p className="mt-1 text-xs text-destructive">{item.error}</p>
                ) : null}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="shrink-0"
                aria-label={`Remove instruction: ${item.instruction}`}
                onClick={() => onRemove(item.id)}
                disabled={isApplying}
              >
                <X className="size-4" aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
