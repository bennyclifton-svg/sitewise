import { useVirtualizer } from "@tanstack/react-virtual";
import { AlertCircle, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  TenderComparison,
  TenderMatrixCell,
  TenderMatrixResponse,
  TenderQuote,
} from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import {
  formatTenderMoney,
  formatTenderStatus,
  tenderStatusGlyph,
  tenderStatusTone,
} from "./format";

type MatrixRow =
  | { kind: "group"; id: string; groupName: string }
  | { kind: "cell"; id: string; groupName: string; cell: TenderMatrixCell };

export function TenderMatrix({ comparisonId }: { comparisonId: string }) {
  const [matrix, setMatrix] = useState<TenderMatrixResponse | null>(null);
  const [comparison, setComparison] = useState<TenderComparison | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMatrix() {
      setIsLoading(true);
      setError(null);
      try {
        const [matrixData, comparisonData] = await Promise.all([
          api.getTenderMatrix(comparisonId),
          api.getTenderComparison(comparisonId),
        ]);
        if (cancelled) return;
        setMatrix(matrixData);
        setComparison(comparisonData);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load comparison matrix.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadMatrix();
    return () => {
      cancelled = true;
    };
  }, [comparisonId]);

  const rows = useMemo(() => flattenRows(matrix), [matrix]);
  const quotes = useMemo(() => quoteColumns(matrix, comparison?.quotes ?? []), [comparison, matrix]);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (index) => (rows[index]?.kind === "group" ? 36 : 56),
    overscan: 8,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[42rem] items-center justify-center rounded-md border bg-card text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
        Loading matrix
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[42rem] items-center justify-center rounded-md border bg-card p-6 text-center">
        <div>
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  if (!matrix) return null;

  return (
    <section className="rounded-md border bg-card shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <p className="cockpit-zone-title">Comparison matrix</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {rows.filter((row) => row.kind === "cell").length} cells across {quotes.length} quotes
          </p>
        </div>
        <MatrixLegend />
      </header>

      <div className="overflow-x-auto">
        <div className="min-w-[54rem]">
          <div
            className="grid border-b bg-background text-xs font-medium text-muted-foreground"
            style={{ gridTemplateColumns: `17rem repeat(${quotes.length}, minmax(11rem, 1fr))` }}
          >
            <div className="px-3 py-2">Cell</div>
            {quotes.map((quote) => (
              <div key={quote.id} className="border-l px-3 py-2">
                <span className="block truncate">{quote.builderName}</span>
                <span className="block font-mono text-[0.68rem] font-normal tabular-nums">
                  {formatTenderMoney(quote.totalCents)}
                </span>
              </div>
            ))}
          </div>

          <div ref={scrollRef} className="h-[42rem] overflow-auto">
            <div
              className="relative"
              style={{ height: `${virtualizer.getTotalSize()}px` }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                  <div
                    key={row.id}
                    className="absolute top-0 right-0 left-0"
                    style={{ transform: `translateY(${virtualRow.start}px)` }}
                  >
                    {row.kind === "group" ? (
                      <div className="border-b bg-muted/70 px-3 py-2 text-xs font-semibold">
                        {row.groupName}
                      </div>
                    ) : (
                      <MatrixCellRow row={row} quotes={quotes} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MatrixCellRow({
  row,
  quotes,
}: {
  row: Extract<MatrixRow, { kind: "cell" }>;
  quotes: MatrixQuote[];
}) {
  return (
    <div
      className="grid min-h-14 border-b bg-card text-sm"
      style={{ gridTemplateColumns: `17rem repeat(${quotes.length}, minmax(11rem, 1fr))` }}
    >
      <div className="min-w-0 px-3 py-2">
        <p className="truncate font-medium">{row.cell.name}</p>
        <p className="mt-0.5 font-mono text-xs text-muted-foreground">{row.cell.code}</p>
      </div>
      {quotes.map((quote) => {
        const cell = row.cell.quotes[quote.id];
        return (
          <div key={quote.id} className="min-w-0 border-l px-3 py-2">
            {cell ? (
              <>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "grid size-6 place-items-center rounded-sm font-semibold",
                      tenderStatusTone(cell.status),
                    )}
                    title={formatTenderStatus(cell.status)}
                  >
                    {tenderStatusGlyph(cell.status)}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {formatTenderStatus(cell.status)}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs tabular-nums">
                  {formatTenderMoney(cell.amount_cents)}
                </p>
                {cell.flags.length ? (
                  <p className="mt-1 truncate text-xs text-destructive" title={cell.flags.join("; ")}>
                    {cell.flags.length} flag{cell.flags.length === 1 ? "" : "s"}
                  </p>
                ) : null}
              </>
            ) : (
              <span className="text-xs text-muted-foreground">No row</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function MatrixLegend() {
  const entries = [
    ["included", "Included"],
    ["pc", "Allowance"],
    ["excluded_explicit", "Excluded"],
    ["silent_ambiguous", "Not itemised"],
    ["not_required", "Not required"],
  ];
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([status, label]) => (
        <Badge key={status} variant="outline" className="gap-1.5">
          <span className={cn("grid size-4 place-items-center rounded-sm", tenderStatusTone(status))}>
            {tenderStatusGlyph(status)}
          </span>
          {label}
        </Badge>
      ))}
    </div>
  );
}

type MatrixQuote = {
  id: string;
  builderName: string;
  totalCents: number | null;
};

function flattenRows(matrix: TenderMatrixResponse | null): MatrixRow[] {
  if (!matrix) return [];
  return matrix.groups.flatMap((group) => [
    { kind: "group" as const, id: `group:${group.name}`, groupName: group.name },
    ...group.cells.map((cell) => ({
      kind: "cell" as const,
      id: `cell:${group.name}:${cell.code}`,
      groupName: group.name,
      cell,
    })),
  ]);
}

function quoteColumns(
  matrix: TenderMatrixResponse | null,
  quotes: TenderQuote[],
): MatrixQuote[] {
  if (quotes.length) {
    return quotes.map((quote) => ({
      id: quote.id,
      builderName: quote.builder_name,
      totalCents: quote.stated_total_cents,
    }));
  }
  const ids = new Set<string>();
  for (const group of matrix?.groups ?? []) {
    for (const cell of group.cells) {
      for (const quoteId of Object.keys(cell.quotes)) ids.add(quoteId);
    }
  }
  return [...ids].map((id) => ({ id, builderName: id, totalCents: null }));
}
