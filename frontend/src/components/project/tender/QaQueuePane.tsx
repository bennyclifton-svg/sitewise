import { CircleAlert, CircleDollarSign } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { TenderQaItem } from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import { formatTenderMoney, formatTenderPercent, formatTenderStage } from "./format";

export function QaQueuePane({
  items,
  selectedId,
  onSelect,
}: {
  items: TenderQaItem[];
  selectedId: string | null;
  onSelect: (itemId: string) => void;
}) {
  return (
    <section className="flex min-h-0 flex-col rounded-md border bg-card shadow-sm">
      <header className="border-b px-3 py-3">
        <p className="cockpit-zone-title">Queue</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {items.length} {items.length === 1 ? "item" : "items"} needing review
        </p>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {items.length ? (
          <div className="divide-y">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={cn(
                  "block w-full px-3 py-3 text-left transition-colors hover:bg-muted/70",
                  selectedId === item.id && "bg-muted",
                )}
                onClick={() => onSelect(item.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{primaryLabel(item)}</p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {secondaryLabel(item)}
                    </p>
                  </div>
                  <Badge variant="outline" className="shrink-0">
                    {formatTenderStage(item.entity_type)}
                  </Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <CircleDollarSign className="size-3.5" aria-hidden />
                    {formatTenderMoney(item.report_impact_cents)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CircleAlert className="size-3.5" aria-hidden />
                    {formatTenderPercent(item.confidence)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex h-full min-h-64 items-center justify-center p-4 text-center text-sm text-muted-foreground">
            QA queue is clear.
          </div>
        )}
      </div>
    </section>
  );
}

function primaryLabel(item: TenderQaItem): string {
  const payload = item.payload;
  if (typeof payload.headline === "string") return payload.headline;
  if (typeof payload.description_raw === "string") return payload.description_raw;
  if (typeof payload.filename === "string") return payload.filename;
  if (typeof payload.cell_code === "string") return `Cell ${payload.cell_code}`;
  return formatTenderStage(item.entity_type);
}

function secondaryLabel(item: TenderQaItem): string {
  const payload = item.payload;
  const bits = [
    typeof payload.cell_code === "string" ? payload.cell_code : null,
    typeof payload.status === "string" ? formatTenderStage(payload.status) : null,
    typeof payload.severity === "string" ? formatTenderStage(payload.severity) : null,
    typeof payload.doc_type === "string" ? formatTenderStage(payload.doc_type) : null,
  ];
  return bits.filter((bit): bit is string => bit !== null).join(" / ") || item.id;
}
