import { useVirtualizer } from "@tanstack/react-virtual";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCheck,
  CircleHelp,
  Flag,
  LoaderCircle,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  TenderComparison,
  TenderMappingChoiceTarget,
  TenderMatrixCell,
  TenderMatrixQuoteCell,
  TenderMatrixQuoteTotal,
  TenderMatrixResponse,
  TenderProjectTrade,
  TenderQaItem,
  TenderQaResolveRequest,
  TenderQuote,
  TenderTaxonomyCell,
} from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import {
  formatTenderMoney,
  formatTenderStatus,
  tenderStatusCellTint,
  tenderStatusGlyph,
  tenderStatusTextTone,
} from "./format";
import { MatrixQaStrip } from "./MatrixQaStrip";
import { QuoteLedgerPanel } from "./QuoteLedgerPanel";
import { NOT_ITEMISED_CODE, TenderCellDrilldown } from "./TenderCellDrilldown";
import { cellKey, groupQaByCell, qaItemKey, unanchoredQaItems } from "./qa";
import { pageEvidenceFromPayload } from "./evidence";

const UNALLOCATED_CELL_CODE = "99.01";

type MatrixRow =
  | { kind: "group"; id: string; groupName: string }
  | { kind: "cell"; id: string; groupName: string; cell: TenderMatrixCell };

type ActiveCell = { quoteId: string; cellCode: string };

const GROUP_ROW_PX = 32;
const CELL_ROW_PX = 36;

export function TenderMatrix({
  projectId,
  comparisonId,
}: {
  projectId: string;
  comparisonId: string;
}) {
  const [matrix, setMatrix] = useState<TenderMatrixResponse | null>(null);
  const [comparison, setComparison] = useState<TenderComparison | null>(null);
  const [qaItems, setQaItems] = useState<TenderQaItem[]>([]);
  const [taxonomy, setTaxonomy] = useState<TenderTaxonomyCell[]>([]);
  const [trades, setTrades] = useState<TenderProjectTrade[]>([]);
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [qaNote, setQaNote] = useState<string | null>(null);
  const [qaError, setQaError] = useState<string | null>(null);
  const [adjudicationError, setAdjudicationError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ledgerQuoteId, setLedgerQuoteId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMatrix() {
      setIsLoading(true);
      setError(null);
      try {
        const [matrixData, comparisonData, queue, taxonomyCells, tradesData] =
          await Promise.all([
            api.getTenderMatrix(comparisonId),
            api.getTenderComparison(comparisonId),
            api.getTenderQaQueue(comparisonId),
            api.getTenderTaxonomy(),
            api.getTenderTrades(comparisonId),
          ]);
        if (cancelled) return;
        setMatrix(matrixData);
        setComparison(comparisonData);
        setQaItems(queue.items);
        setTaxonomy(taxonomyCells);
        setTrades(tradesData.trades);
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

  const quotes = useMemo(() => quoteColumns(matrix, comparison?.quotes ?? []), [comparison, matrix]);
  const totalsByQuote = useMemo(() => {
    const map = new Map<string, TenderMatrixQuoteTotal>();
    for (const total of matrix?.totals ?? []) map.set(total.quote_id, total);
    return map;
  }, [matrix]);
  const rows = useMemo(
    () => flattenRows(matrix, quotes, totalsByQuote),
    [matrix, quotes, totalsByQuote],
  );
  const qaByCell = useMemo(() => groupQaByCell(qaItems), [qaItems]);
  const unanchoredItems = useMemo(() => unanchoredQaItems(qaItems), [qaItems]);
  const cellNames = useMemo(() => cellNameIndex(matrix), [matrix]);
  const anchoredCount = useMemo(
    () => [...qaByCell.values()].reduce((sum, items) => sum + items.length, 0),
    [qaByCell],
  );
  const lowestTotal = useMemo(() => {
    const totals = quotes
      .map((quote) => quote.totalCents)
      .filter((total): total is number => typeof total === "number");
    return totals.length > 1 ? Math.min(...totals) : null;
  }, [quotes]);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (index) =>
      rows[index]?.kind === "group" ? GROUP_ROW_PX : CELL_ROW_PX,
    overscan: 12,
  });

  const reportPath = `/projects/${projectId}/tender/${comparisonId}/report`;
  const activeKey = activeCell ? cellKey(activeCell.quoteId, activeCell.cellCode) : null;
  const activeItems = activeKey ? qaByCell.get(activeKey) ?? [] : [];
  const activeQuote = activeCell
    ? quotes.find((quote) => quote.id === activeCell.quoteId)
    : null;

  async function reloadQueue(): Promise<TenderQaItem[]> {
    const queue = await api.getTenderQaQueue(comparisonId);
    setQaItems(queue.items);
    return queue.items;
  }

  async function acceptAll() {
    setResolving("all");
    setQaError(null);
    setQaNote(null);
    try {
      const result = await api.acceptAllTenderQa(comparisonId);
      await reloadQueue();
      setActiveCell(null);
      const accepted = `Accepted ${result.accepted} recommendation${result.accepted === 1 ? "" : "s"}.`;
      setQaNote(
        result.skipped_documents > 0
          ? `${accepted} ${result.skipped_documents} document${result.skipped_documents === 1 ? "" : "s"} still need classification below.`
          : accepted,
      );
    } catch (acceptError) {
      setQaError(
        acceptError instanceof ApiError
          ? acceptError.message
          : "Could not accept recommendations.",
      );
    } finally {
      setResolving(null);
    }
  }

  async function acceptItem(item: TenderQaItem) {
    setResolving(item.id);
    setQaError(null);
    setQaNote(null);
    const previousItems = qaItems;
    const optimisticItems = qaItems.filter((candidate) => candidate.id !== item.id);
    setQaItems(optimisticItems);
    prefetchQaImage(optimisticItems[0]);
    try {
      await api.resolveTenderQaItem(item.id, {
        action: "accept",
        corrected_value: null,
        reason: null,
      });
      if (
        activeKey &&
        !optimisticItems.some((candidate) => qaItemKey(candidate) === activeKey)
      ) {
        setActiveCell(null);
      }
    } catch (resolveError) {
      setQaItems(previousItems);
      setQaError(
        resolveError instanceof ApiError
          ? resolveError.message
          : "Could not resolve QA item.",
      );
    } finally {
      setResolving(null);
    }
  }

  function toggleCell(next: ActiveCell) {
    setQaError(null);
    setAdjudicationError(null);
    setActiveCell((current) =>
      current && current.quoteId === next.quoteId && current.cellCode === next.cellCode
        ? null
        : next,
    );
  }

  async function resolveMappingChoice(
    mappingId: string,
    target: TenderMappingChoiceTarget,
  ) {
    await api.resolveTenderQaItem(mappingId, {
      action: "correct",
      corrected_value: target,
      reason: "Inline matrix mapping override",
    });
    const [matrixData, queue] = await Promise.all([
      api.getTenderMatrix(comparisonId),
      api.getTenderQaQueue(comparisonId),
    ]);
    setMatrix(matrixData);
    setQaItems(queue.items);
  }

  async function resolveQaItem(item: TenderQaItem, request: TenderQaResolveRequest) {
    setResolving(item.id);
    setAdjudicationError(null);
    try {
      await api.resolveTenderQaItem(item.id, request);
      const [matrixData, queue] = await Promise.all([
        api.getTenderMatrix(comparisonId),
        api.getTenderQaQueue(comparisonId),
      ]);
      setMatrix(matrixData);
      setQaItems(queue.items);
      if (
        activeKey &&
        !queue.items.some((candidate) => qaItemKey(candidate) === activeKey)
      ) {
        setActiveCell(null);
      }
    } catch (resolveError) {
      setAdjudicationError(
        resolveError instanceof ApiError
          ? resolveError.message
          : "Could not resolve QA item.",
      );
    } finally {
      setResolving(null);
    }
  }

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
            {rows.filter((row) => row.kind === "cell").length} line items across {quotes.length} quotes
          </p>
        </div>
        <MatrixLegend />
      </header>

      {qaItems.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-[var(--warn-bg)] px-4 py-2">
          <p className="flex items-center gap-1.5 text-sm text-[var(--warn-text)]">
            <CircleHelp className="size-4 shrink-0" aria-hidden />
            {qaItems.length} question{qaItems.length === 1 ? "" : "s"} from the analysis
            {anchoredCount > 0
              ? ` - ${anchoredCount} marked on cells below`
              : ""}
            {unanchoredItems.length > 0
              ? `, ${unanchoredItems.length} at quote or document level`
              : ""}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              disabled={resolving !== null}
              onClick={() => void acceptAll()}
            >
              {resolving === "all" ? (
                <LoaderCircle className="size-4 animate-spin" aria-hidden />
              ) : (
                <CheckCheck className="size-4" aria-hidden />
              )}
              Accept all recommendations
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-[var(--ok-bg)] px-4 py-2">
          <p className="flex items-center gap-1.5 text-sm text-[var(--ok-text)]">
            <Check className="size-4 shrink-0" aria-hidden />
            All findings reviewed — ready to build the report.
          </p>
          <Button asChild size="sm">
            <Link to={reportPath}>
              Continue to report
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </Button>
        </div>
      )}

      {qaNote ? (
        <p className="border-b bg-muted px-4 py-2 text-sm text-muted-foreground">{qaNote}</p>
      ) : null}
      {qaError ? (
        <p className="border-b border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
          {qaError}
        </p>
      ) : null}

      <MatrixQaStrip
        items={unanchoredItems}
        taxonomy={taxonomy}
        resolving={resolving}
        error={adjudicationError}
        onAccept={(item) => void acceptItem(item)}
        onResolve={resolveQaItem}
      />

      {activeCell
        ? (() => {
            const activeMatrixCell =
              rows
                .filter((row): row is Extract<MatrixRow, { kind: "cell" }> => row.kind === "cell")
                .find((row) => row.cell.code === activeCell.cellCode)?.cell ??
              matrix?.groups
                .flatMap((group) => group.cells)
                .find((cell) => cell.code === activeCell.cellCode);
            const choices =
              activeMatrixCell?.quotes[activeCell.quoteId]?.mapping_choices ?? [];
            return (
              <TenderCellDrilldown
                comparisonId={comparisonId}
                cellCode={activeCell.cellCode}
                cellName={
                  cellNames.get(activeCell.cellCode) ??
                  activeMatrixCell?.name ??
                  activeCell.cellCode
                }
                quoteId={activeCell.quoteId}
                quoteName={activeQuote?.builderName ?? null}
                items={activeItems}
                choices={choices}
                taxonomy={taxonomy}
                trades={trades}
                resolving={resolving}
                error={adjudicationError}
                onClose={() => setActiveCell(null)}
                onAccept={(item) => void acceptItem(item)}
                onResolve={resolveQaItem}
                onMappingChoice={resolveMappingChoice}
              />
            );
          })()
        : null}

      {ledgerQuoteId ? (
        <QuoteLedgerPanel
          comparisonId={comparisonId}
          quoteId={ledgerQuoteId}
          onClose={() => setLedgerQuoteId(null)}
        />
      ) : null}

      <div className="overflow-x-auto">
        <div className="min-w-[54rem]">
          <div
            className="grid overflow-y-hidden border-b bg-background text-xs font-medium text-muted-foreground [scrollbar-gutter:stable]"
            style={{ gridTemplateColumns: gridColumns(quotes.length) }}
          >
            <div className="px-3 py-2">Line item</div>
            {quotes.map((quote) => (
              <div key={quote.id} className="border-l px-2 py-2">
                <span className="block truncate" title={quote.builderName}>
                  {quote.builderName}
                </span>
                <span className="block font-mono text-[0.68rem] font-normal tabular-nums">
                  {formatTenderMoney(quote.totalCents)}
                  {lowestTotal !== null && quote.totalCents === lowestTotal ? (
                    <span className="ml-1.5 font-sans text-[var(--ok-text)]">Lowest</span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="mt-0.5 text-[0.65rem] font-normal text-foreground underline-offset-2 hover:underline"
                  onClick={() =>
                    setLedgerQuoteId((current) =>
                      current === quote.id ? null : quote.id,
                    )
                  }
                >
                  Ledger
                </button>
              </div>
            ))}
          </div>

          <div ref={scrollRef} className="h-[42rem] overflow-auto [scrollbar-gutter:stable]">
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
                      <div className="flex h-8 items-center border-b bg-muted/70 px-3 text-xs font-semibold">
                        {row.groupName}
                      </div>
                    ) : (
                      <MatrixCellRow
                        row={row}
                        quotes={quotes}
                        qaByCell={qaByCell}
                        activeCell={activeCell}
                        onToggleCell={toggleCell}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <MatrixTotalsRow quotes={quotes} totalsByQuote={totalsByQuote} />
        </div>
      </div>
    </section>
  );
}

function prefetchQaImage(item: TenderQaItem | undefined): void {
  if (!item) return;
  const imagePath = pageEvidenceFromPayload(item.payload).imagePath;
  if (!imagePath) return;
  const image = new Image();
  image.src = imagePath;
}

function MatrixTotalsRow({
  quotes,
  totalsByQuote,
}: {
  quotes: MatrixQuote[];
  totalsByQuote: Map<string, TenderMatrixQuoteTotal>;
}) {
  if (!quotes.length) return null;
  return (
    <div
      className="grid overflow-y-hidden border-t-2 bg-background [scrollbar-gutter:stable]"
      style={{ gridTemplateColumns: gridColumns(quotes.length) }}
    >
      <div className="px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        Total (ex GST)
      </div>
      {quotes.map((quote) => {
        const total = totalsByQuote.get(quote.id);
        return (
          <div key={quote.id} className="border-l px-2 py-2">
            {total ? (
              <>
                <span className="block font-mono text-sm font-semibold tabular-nums">
                  {formatTenderMoney(total.computed_total_cents)}
                </span>
                <TotalReconciliation total={total} />
              </>
            ) : (
              <span className="block text-xs text-muted-foreground">
                No total
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function TotalReconciliation({ total }: { total: TenderMatrixQuoteTotal }) {
  if (total.reconciliation === "match") {
    return (
      <span className="mt-0.5 inline-flex items-center gap-1 rounded-sm bg-[var(--ok-bg)] px-1 py-0.5 text-[0.68rem] font-medium text-[var(--ok-text)]">
        <Check className="size-3 shrink-0" aria-hidden />
        Matches stated total
      </span>
    );
  }
  if (total.reconciliation === "mismatch") {
    const delta = total.delta_cents ?? 0;
    const sign = delta > 0 ? "+" : "-";
    return (
      <span className="mt-0.5 inline-flex items-center gap-1 rounded-sm bg-[var(--alert-bg)] px-1 py-0.5 text-[0.68rem] font-medium text-[var(--alert-text)]">
        <AlertCircle className="size-3 shrink-0" aria-hidden />
        {`Stated ${formatTenderMoney(total.stated_total_cents)} (${sign}${formatTenderMoney(Math.abs(delta))})`}
      </span>
    );
  }
  return (
    <span className="mt-0.5 block text-[0.68rem] text-muted-foreground">
      Not stated in quote
    </span>
  );
}

function MatrixCellRow({
  row,
  quotes,
  qaByCell,
  activeCell,
  onToggleCell,
}: {
  row: Extract<MatrixRow, { kind: "cell" }>;
  quotes: MatrixQuote[];
  qaByCell: Map<string, TenderQaItem[]>;
  activeCell: ActiveCell | null;
  onToggleCell: (cell: ActiveCell) => void;
}) {
  return (
    <div
      className="grid h-9 border-b bg-card text-sm"
      style={{ gridTemplateColumns: gridColumns(quotes.length) }}
    >
      <div className="flex min-w-0 items-center gap-2 px-3">
        <span className="w-10 shrink-0 font-mono text-[0.68rem] text-muted-foreground">
          {row.cell.code}
        </span>
        <span className="truncate font-medium" title={row.cell.name}>
          {row.cell.name}
        </span>
      </div>
      {quotes.map((quote) => {
        const cell = row.cell.quotes[quote.id];
        if (!cell) {
          return (
            <div
              key={quote.id}
              className="flex items-center border-l px-2 text-xs text-muted-foreground"
            >
              &ndash;
            </div>
          );
        }
        const questions = qaByCell.get(cellKey(quote.id, row.cell.code)) ?? [];
        const mappingChoices = cell.mapping_choices ?? [];
        const isActive =
          activeCell?.quoteId === quote.id && activeCell?.cellCode === row.cell.code;
        const statusLabel = formatTenderStatus(cell.status);
        const isNotItemised = row.cell.code === NOT_ITEMISED_CODE;
        const content = (
          <>
            <span
              className={cn(
                "w-4 shrink-0 text-center font-semibold",
                tenderStatusTextTone(cell.status),
              )}
              aria-hidden
            >
              {tenderStatusGlyph(cell.status)}
            </span>
            <span className="min-w-0 flex-1 truncate text-right font-mono text-xs tabular-nums">
              {cell.amount_cents !== null && cell.amount_cents !== undefined
                ? formatTenderMoney(cell.amount_cents)
                : "?"}
            </span>
            {cell.flags.length ? (
              <span
                className="flex shrink-0 items-center text-[var(--alert-text)]"
                title={cell.flags.join("; ")}
              >
                <Flag className="size-3" aria-hidden />
                {cell.flags.length > 1 ? (
                  <span className="ml-0.5 text-[0.65rem] tabular-nums">{cell.flags.length}</span>
                ) : null}
              </span>
            ) : null}
            {questions.length ? (
              <span
                className="grid size-4 shrink-0 place-items-center rounded-full bg-[var(--warn-text)] text-[0.65rem] font-bold text-background"
                aria-hidden
              >
                {questions.length}
              </span>
            ) : null}
            {mappingChoices.length ? (
              <span
                className="grid size-4 shrink-0 place-items-center rounded-full bg-primary text-[0.65rem] font-bold text-primary-foreground"
                title="Mapping choices"
                aria-hidden
              >
                {mappingChoices.length}
              </span>
            ) : null}
          </>
        );

        if (isNotItemised) {
          return (
            <div
              key={quote.id}
              className={cn(
                "flex items-center gap-1.5 border-l px-2",
                tenderStatusCellTint(cell.status),
              )}
              title={statusLabel}
            >
              {content}
            </div>
          );
        }

        return (
          <button
            key={quote.id}
            type="button"
            className={cn(
              "flex cursor-pointer items-center gap-1.5 border-l px-2 text-left transition-colors hover:brightness-95 dark:hover:brightness-110",
              tenderStatusCellTint(cell.status),
              isActive && "ring-2 ring-[var(--warn-text)] ring-inset",
            )}
            title={statusLabel}
            aria-label={`${statusLabel} — line items for ${row.cell.name}, ${quote.builderName}`}
            onClick={() => onToggleCell({ quoteId: quote.id, cellCode: row.cell.code })}
          >
            {content}
          </button>
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
  ] as const;
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([status, label]) => (
        <span
          key={status}
          className={cn(
            "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-xs font-medium",
            tenderStatusCellTint(status),
            tenderStatusTextTone(status),
          )}
        >
          <span aria-hidden>{tenderStatusGlyph(status)}</span>
          {label}
        </span>
      ))}
    </div>
  );
}

type MatrixQuote = {
  id: string;
  builderName: string;
  totalCents: number | null;
};

function gridColumns(quoteCount: number): string {
  return `16rem repeat(${quoteCount}, minmax(9.5rem, 1fr))`;
}

function cellNameIndex(matrix: TenderMatrixResponse | null): Map<string, string> {
  const map = new Map<string, string>();
  for (const group of matrix?.groups ?? []) {
    for (const cell of group.cells) map.set(cell.code, cell.name);
  }
  map.set(UNALLOCATED_CELL_CODE, "Unallocated / uncategorised");
  map.set(NOT_ITEMISED_CODE, "Not itemised in quote");
  return map;
}

function flattenRows(
  matrix: TenderMatrixResponse | null,
  quotes: MatrixQuote[],
  totalsByQuote: Map<string, TenderMatrixQuoteTotal>,
): MatrixRow[] {
  if (!matrix) return [];
  const rows: MatrixRow[] = matrix.groups.flatMap((group) => [
    { kind: "group" as const, id: `group:${group.name}`, groupName: group.name },
    ...group.cells.map((cell) => ({
      kind: "cell" as const,
      id: `cell:${group.name}:${cell.code}`,
      groupName: group.name,
      cell,
    })),
  ]);

  const hasUnallocated = matrix.groups.some((group) =>
    group.cells.some((cell) => cell.code === UNALLOCATED_CELL_CODE),
  );
  if (!hasUnallocated && quotes.length) {
    rows.push(
      {
        kind: "group",
        id: "group:Unallocated",
        groupName: "Unallocated",
      },
      {
        kind: "cell",
        id: `cell:Unallocated:${UNALLOCATED_CELL_CODE}`,
        groupName: "Unallocated",
        cell: syntheticAmountCell(
          UNALLOCATED_CELL_CODE,
          "Unallocated / uncategorised",
          quotes,
          totalsByQuote,
          (total) => total.unallocated_cents ?? 0,
          "included",
        ),
      },
    );
  }

  if (quotes.length) {
    rows.push(
      {
        kind: "group",
        id: "group:Reconciliation",
        groupName: "Reconciliation",
      },
      {
        kind: "cell",
        id: `cell:Reconciliation:${NOT_ITEMISED_CODE}`,
        groupName: "Reconciliation",
        cell: syntheticAmountCell(
          NOT_ITEMISED_CODE,
          "Not itemised in quote",
          quotes,
          totalsByQuote,
          (total) => total.not_itemised_cents ?? 0,
          "silent_ambiguous",
        ),
      },
    );
  }

  return rows;
}

function syntheticAmountCell(
  code: string,
  name: string,
  quotes: MatrixQuote[],
  totalsByQuote: Map<string, TenderMatrixQuoteTotal>,
  amountOf: (total: TenderMatrixQuoteTotal) => number,
  status: string,
): TenderMatrixCell {
  const quoteCells: Record<string, TenderMatrixQuoteCell> = {};
  for (const quote of quotes) {
    const total = totalsByQuote.get(quote.id);
    quoteCells[quote.id] = {
      status,
      amount_cents: total ? amountOf(total) : 0,
      flags: [],
      mapping_choices: [],
    };
  }
  return { code, name, quotes: quoteCells };
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
