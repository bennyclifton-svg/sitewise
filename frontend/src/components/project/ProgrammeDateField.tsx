import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  addMonths,
  formatCompactDate,
  formatMonthYear,
  parseIsoDate,
  startOfMonth,
  toIsoDate,
} from "@/lib/programme";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];
const DATE_TITLE = new Intl.DateTimeFormat("en-AU", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function ProgrammeDateField({
  value,
  ariaLabel,
  onChange,
}: {
  value: string;
  ariaLabel: string;
  onChange: (next: string) => void;
}) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(startOfMonth(value));
  const [panel, setPanel] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        className={cn(
          "program-gantt-field flex h-5 w-full items-center gap-0.5 px-0.5 text-left",
          "text-[10px] leading-5 md:text-[10px]",
        )}
        title={DATE_TITLE.format(parseIsoDate(value))}
        onClick={() => {
          if (open) {
            setOpen(false);
            return;
          }
          setMonth(startOfMonth(value));
          const box = rootRef.current?.getBoundingClientRect();
          if (box) setPanel({ top: box.bottom + 4, left: box.left });
          setOpen(true);
        }}
      >
        <Calendar className="size-3 shrink-0 text-[var(--sw-text-tertiary)]" aria-hidden />
        <span className="truncate">{formatCompactDate(value)}</span>
      </button>
      {open
        ? createPortal(
        <div
          ref={panelRef}
          role="dialog"
          aria-label="Choose date"
          className="sw-surface sw-contact program-gantt-calendar fixed z-50 p-2"
          style={{ top: panel.top, left: panel.left }}
        >
          <div className="mb-1 flex items-center justify-between gap-1">
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              aria-label="Previous month"
              onClick={() => setMonth(addMonths(month, -1))}
            >
              <ChevronLeft className="size-3.5" aria-hidden />
            </Button>
            <span className="text-xs text-[var(--sw-text-primary)]">{formatMonthYear(month)}</span>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              aria-label="Next month"
              onClick={() => setMonth(addMonths(month, 1))}
            >
              <ChevronRight className="size-3.5" aria-hidden />
            </Button>
          </div>
          <div className="grid grid-cols-7 gap-px text-center text-[10px] text-[var(--sw-text-tertiary)]">
            {WEEKDAYS.map((day, index) => (
              <span key={`${day}-${index}`} className="h-5 leading-5">
                {day}
              </span>
            ))}
            {monthCells(month).map((cell) => (
              <button
                key={cell.iso}
                type="button"
                className={cn(
                  "h-6 text-xs leading-6",
                  cell.inMonth
                    ? "text-[var(--sw-text-secondary)]"
                    : "text-[var(--sw-text-tertiary)]/50",
                  cell.iso === value && "bg-[var(--sw-beam)] text-[var(--sw-void)]",
                )}
                onClick={() => {
                  onChange(cell.iso);
                  setOpen(false);
                }}
              >
                {cell.day}
              </button>
            ))}
          </div>
        </div>,
        document.body,
      )
        : null}
    </div>
  );
}

function monthCells(monthStart: string): { iso: string; day: number; inMonth: boolean }[] {
  const start = parseIsoDate(monthStart);
  const weekday = (start.getUTCDay() + 6) % 7;
  const first = new Date(start);
  first.setUTCDate(1 - weekday);
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(first);
    date.setUTCDate(first.getUTCDate() + index);
    return {
      iso: toIsoDate(date),
      day: date.getUTCDate(),
      inMonth: date.getUTCMonth() === start.getUTCMonth(),
    };
  });
}
