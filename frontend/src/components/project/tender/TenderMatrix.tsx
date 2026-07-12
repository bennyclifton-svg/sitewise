import { useVirtualizer } from "@tanstack/react-virtual";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCheck,
  CircleHelp,
  Flag,
  LoaderCircle,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ChangeEvent } from "react";
import type {
  TenderComparison,
  TenderMatrixCell,
  TenderMatrixMappingChoice,
  TenderMatrixResponse,
  TenderQaItem,
  TenderQuote,
} from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import {
  formatTenderMoney,
  formatTenderPercent,
  formatTenderStatus,
  tenderStatusCellTint,
  tenderStatusGlyph,
  tenderStatusTextTone,
} from "./format";

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
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [qaNote, setQaNote] = useState<string | null>(null);
  const [qaError, setQaError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMatrix() {
      setIsLoading(true);
      setError(null);
      try {
        const [matrixData, comparisonData, queue] = await Promise.all([
          api.getTenderMatrix(comparisonId),
          api.getTenderComparison(comparisonId),
          api.getTenderQaQueue(comparisonId),
        ]);
        if (cancelled) return;
        setMatrix(matrixData);
        setComparison(comparisonData);
        setQaItems(queue.items);
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
  const qaByCell = useMemo(() => groupQaByCell(qaItems), [qaItems]);
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

  const qaPath = `/projects/${projectId}/tender/${comparisonId}/qa`;
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
          ? `${accepted} ${result.skipped_documents} document${result.skipped_documents === 1 ? "" : "s"} still need classification in the QA console.`
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
    try {
      await api.resolveTenderQaItem(item.id, {
        action: "accept",
        corrected_value: null,
        reason: null,
      });
      const remaining = await reloadQueue();
      if (
        activeKey &&
        !remaining.some((candidate) => qaItemKey(candidate) === activeKey)
      ) {
        setActiveCell(null);
      }
    } catch (resolveError) {
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
    setActiveCell((current) =>
      current && current.quoteId === next.quoteId && current.cellCode === next.cellCode
        ? null
        : next,
    );
  }

  async function resolveMappingChoice(mappingId: string, cellCode: string) {
    await api.resolveTenderQaItem(mappingId, {
      action: "correct",
      corrected_value: { cell_code: cellCode },
      reason: "Inline matrix mapping override",
    });
    setMatrix((current) => updateMatrixChoice(current, mappingId, cellCode));
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
              ? ` ? ${anchoredCount} marked on cells below`
              : ""}
            {qaItems.length - anchoredCount > 0
              ? `, ${qaItems.length - anchoredCount} in the QA console`
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
            <Button asChild size="sm" variant="outline">
              <Link to={qaPath}>QA console</Link>
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-[var(--ok-bg)] px-4 py-2">
          <p className="flex items-center gap-1.5 text-sm text-[var(--ok-text)]">
            <Check className="size-4 shrink-0" aria-hidden />
            All findings reviewed ? ready to build the report.
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

      {activeCell && (activeItems.length > 0 || (activeQuote && ((matrix?.groups.flatMap((g) => g.cells).find((c) => c.code === activeCell.cellCode)?.quotes[activeCell.quoteId]?.mapping_choices?.length ?? 0) > 0))) ? (
        <div className="border-b bg-background px-4 py-3">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium">
              {cellNames.get(activeCell.cellCode) ?? activeCell.cellCode}
              <span className="ml-2 font-mono text-xs text-muted-foreground">
                {activeCell.cellCode}
              </span>
              {activeQuote ? (
                <span className="ml-2 text-xs text-muted-foreground">
                  {activeQuote.builderName}
                </span>
              ) : null}
            </p>
            <button
              type="button"
              className="cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Close questions"
              onClick={() => setActiveCell(null)}
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>
          {activeCell
            ? (() => {
                const activeMatrixCell = matrix?.groups
                  .flatMap((group) => group.cells)
                  .find((cell) => cell.code === activeCell.cellCode);
                const choices =
                  activeMatrixCell?.quotes[activeCell.quoteId]?.mapping_choices ?? [];
                if (!choices.length || !activeQuote) return null;
                return (
                  <div className="mt-2 space-y-2">
                    {choices.map((choice) => (
                      <MappingChoiceControl
                        key={choice.mapping_id}
                        choice={choice}
                        quoteName={activeQuote.builderName}
                        cellName={activeMatrixCell?.name ?? activeCell.cellCode}
                        onChange={resolveMappingChoice}
                      />
                    ))}
                  </div>
                );
              })()
            : null}
          <ul className="mt-2 space-y-1.5">
            {activeItems.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-card px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm">{qaQuestion(item)}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Impact {formatTenderMoney(item.report_impact_cents)} ? Confidence{" "}
                    {formatTenderPercent(item.confidence)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <Button
                    type="button"
                    size="xs"
                    variant="secondary"
                    disabled={resolving !== null}
                    onClick={() => void acceptItem(item)}
                  >
                    {resolving === item.id ? (
                      <LoaderCircle className="size-3 animate-spin" aria-hidden />
                    ) : (
                      <Check className="size-3" aria-hidden />
                    )}
                    Accept
                  </Button>
                  <Button asChild size="xs" variant="ghost">
                    <Link to={qaPath}>Edit in console</Link>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="overflow-x-auto">
        <div className="min-w-[54rem]">
          <div
            className="grid border-b bg-background text-xs font-medium text-muted-foreground"
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
        </div>
      </div>
    </section>
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

        if (questions.length || mappingChoices.length) {
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
              aria-label={`${statusLabel} ? ${questions.length} question${questions.length === 1 ? "" : "s"} for ${row.cell.name}, ${quote.builderName}`}
              onClick={() => onToggleCell({ quoteId: quote.id, cellCode: row.cell.code })}
            >
              {content}
            </button>
          );
        }

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
      })}
    </div>
  );
}


function MappingChoiceControl({
  choice,
  quoteName,
  cellName,
  onChange,
}: {
  choice: TenderMatrixMappingChoice;
  quoteName: string;
  cellName: string;
  onChange: (mappingId: string, cellCode: string) => Promise<void>;
}) {
  const [selected, setSelected] = useState(choice.selected_cell_code);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextCellCode = event.target.value;
    setSelected(nextCellCode);
    setIsSaving(true);
    setError(null);
    try {
      await onChange(choice.mapping_id, nextCellCode);
    } catch {
      setSelected(choice.selected_cell_code);
      setError("Could not save");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <select
        aria-label={`Mapping choice for ${quoteName} ${cellName}`}
        className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
        value={selected}
        disabled={choice.locked || isSaving}
        onChange={handleChange}
      >
        {choice.candidates.map((candidate) => (
          <option
            key={candidate.cell_code}
            value={candidate.cell_code}
            className="bg-white text-neutral-900"
            style={{ color: "#111111", backgroundColor: "#ffffff" }}
          >
            {candidate.name ?? candidate.cell_code}
          </option>
        ))}
      </select>
      {choice.locked ? (
        <p className="mt-1 text-[0.68rem] text-muted-foreground">Locked</p>
      ) : null}
      {error ? <p className="mt-1 text-[0.68rem] text-destructive">{error}</p> : null}
    </div>
  );
}

function updateMatrixChoice(
  matrix: TenderMatrixResponse | null,
  mappingId: string,
  selectedCellCode: string,
): TenderMatrixResponse | null {
  if (!matrix) return matrix;
  return {
    ...matrix,
    groups: matrix.groups.map((group) => ({
      ...group,
      cells: group.cells.map((cell) => ({
        ...cell,
        quotes: Object.fromEntries(
          Object.entries(cell.quotes).map(([quoteId, quoteCell]) => [
            quoteId,
            {
              ...quoteCell,
              mapping_choices: (quoteCell.mapping_choices ?? []).map((choice) =>
                choice.mapping_id === mappingId
                  ? { ...choice, selected_cell_code: selectedCellCode, locked: true }
                  : choice,
              ),
            },
          ]),
        ),
      })),
    })),
  };
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

function cellKey(quoteId: string, cellCode: string): string {
  return `${quoteId}:${cellCode}`;
}

function qaItemKey(item: TenderQaItem): string | null {
  const quoteId = readString(item.payload.quote_id);
  const cellCode = readString(item.payload.cell_code);
  if (!quoteId || !cellCode) return null;
  return cellKey(quoteId, cellCode);
}

function groupQaByCell(items: TenderQaItem[]): Map<string, TenderQaItem[]> {
  const map = new Map<string, TenderQaItem[]>();
  for (const item of items) {
    const key = qaItemKey(item);
    if (!key) continue;
    const existing = map.get(key);
    if (existing) {
      existing.push(item);
    } else {
      map.set(key, [item]);
    }
  }
  return map;
}

function cellNameIndex(matrix: TenderMatrixResponse | null): Map<string, string> {
  const map = new Map<string, string>();
  for (const group of matrix?.groups ?? []) {
    for (const cell of group.cells) map.set(cell.code, cell.name);
  }
  return map;
}

function qaQuestion(item: TenderQaItem): string {
  const payload = item.payload;
  if (item.entity_type === "cell_status") {
    const status = readString(payload.status);
    const amount = readNumber(payload.amount_cents);
    const statusLabel = status ? formatTenderStatus(status) : "this reading";
    return amount !== null
      ? `Read as ${statusLabel} at ${formatTenderMoney(amount)} ? is this correctly allocated?`
      : `Read as ${statusLabel} ? is this correctly allocated?`;
  }
  if (item.entity_type === "mapping") {
    const description = readString(payload.description_raw);
    return description
      ? `"${description}" was mapped to this line item ? is that where it belongs?`
      : "Confirm this line item mapping.";
  }
  if (item.entity_type === "flag") {
    return readString(payload.headline) ?? "Review this flag.";
  }
  return readString(payload.filename) ?? "Review this document classification.";
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

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
