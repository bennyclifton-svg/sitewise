import {
  Ban,
  Check,
  LoaderCircle,
  Pencil,
  Save,
  Search,
  Split,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  TenderQaItem,
  TenderQaResolveRequest,
  TenderTaxonomyCell,
  TenderTaxonomySearchResult,
} from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import {
  formatTenderMoney,
  formatTenderStage,
  formatTenderStatus,
} from "./format";

/* eslint-disable react-hooks/set-state-in-effect */

export type QaMode = "review" | "edit" | "split";

type SplitTarget = {
  id: string;
  cellCode: string;
  fraction: number;
};

const CELL_STATUSES = [
  "included",
  "excluded_explicit",
  "pc",
  "ps",
  "bundled",
  "not_required",
  "silent_ambiguous",
];

const FLAG_SEVERITIES = ["info", "caution", "warning"];
const DOCUMENT_TYPES = [
  "quote_letter",
  "inclusions_schedule",
  "tender_form",
  "boq",
  "trade_breakdown",
  "addendum",
  "drawing",
  "other",
];

export function QaAdjudicationPane({
  item,
  taxonomy,
  mode,
  isResolving,
  error,
  onModeChange,
  onResolve,
}: {
  item: TenderQaItem | null;
  taxonomy: TenderTaxonomyCell[];
  mode: QaMode;
  isResolving: boolean;
  error: string | null;
  onModeChange: (mode: QaMode) => void;
  onResolve: (request: TenderQaResolveRequest) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState("included");
  const [amount, setAmount] = useState("");
  const [cellQuery, setCellQuery] = useState("");
  const [selectedCell, setSelectedCell] = useState<TenderTaxonomyCell | null>(null);
  const [docType, setDocType] = useState("other");
  const [severity, setSeverity] = useState("info");
  const [headline, setHeadline] = useState("");
  const [detail, setDetail] = useState("");
  const [splits, setSplits] = useState<SplitTarget[]>([]);
  const [searchResults, setSearchResults] = useState<TenderTaxonomySearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    if (!item) return;
    const payload = item.payload;
    const cell = findTaxonomyCell(taxonomy, readString(payload.cell_code));
    setReason("");
    setStatus(readString(payload.status) ?? "included");
    setAmount(centsToDollarInput(readNumber(payload.amount_cents)));
    setCellQuery(cell ? `${cell.code} ${cell.name}` : (readString(payload.cell_code) ?? ""));
    setSelectedCell(cell);
    setDocType(readString(payload.doc_type) ?? "other");
    setSeverity(readString(payload.severity) ?? "info");
    setHeadline(readString(payload.headline) ?? "");
    setDetail(readString(payload.detail) ?? "");
    setSplits([
      {
        id: "primary",
        cellCode: cell?.code ?? readString(payload.cell_code) ?? "",
        fraction: 0.5,
      },
      { id: "secondary", cellCode: "", fraction: 0.5 },
    ]);
    setSearchResults([]);
    setSearchError(null);
  }, [item, taxonomy]);

  useEffect(() => {
    if (cellQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    let cancelled = false;
    const timeoutId = window.setTimeout(() => {
      api.searchTenderTaxonomy(cellQuery)
        .then((results) => {
          if (!cancelled) {
            setSearchResults(results);
            setSearchError(null);
          }
        })
        .catch((searchFailure: unknown) => {
          if (!cancelled) {
            setSearchResults([]);
            setSearchError(
              searchFailure instanceof ApiError
                ? searchFailure.message
                : "Taxonomy search failed.",
            );
          }
        });
    }, 180);
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [cellQuery]);

  const localMatches = useMemo(
    () => localTaxonomyMatches(taxonomy, cellQuery).slice(0, 6),
    [cellQuery, taxonomy],
  );
  const cellOptions = searchResults.length ? searchResults : localMatches;
  const selectedCellCode =
    selectedCell?.code ?? splits.find((split) => split.cellCode)?.cellCode ?? "";

  if (!item) {
    return (
      <section className="flex min-h-0 items-center justify-center rounded-md border bg-card p-6 text-center text-sm text-muted-foreground shadow-sm">
        QA queue is clear.
      </section>
    );
  }

  async function acceptItem() {
    await onResolve({
      action: "accept",
      corrected_value: null,
      reason: reason.trim() || null,
    });
  }

  async function suppressItem() {
    await onResolve({
      action: "suppress",
      corrected_value: null,
      reason: reason.trim() || null,
    });
  }

  async function saveCorrection() {
    if (!item) return;
    await onResolve({
      action: "correct",
      corrected_value: correctedValue(item, {
        status,
        amount,
        selectedCellCode,
        docType,
        severity,
        headline,
        detail,
        splits,
      }),
      reason: reason.trim() || null,
    });
  }

  function setSplitCell(index: number, cellCode: string) {
    setSplits((current) =>
      current.map((split, splitIndex) =>
        splitIndex === index ? { ...split, cellCode } : split,
      ),
    );
  }

  function setSplitFraction(index: number, fraction: number) {
    setSplits((current) =>
      current.map((split, splitIndex) =>
        splitIndex === index ? { ...split, fraction } : split,
      ),
    );
  }

  function normalizeSplitFractions() {
    setSplits((current) => {
      const total = current.reduce((sum, split) => sum + split.fraction, 0);
      if (total <= 0) {
        const equal = 1 / current.length;
        return current.map((split) => ({ ...split, fraction: equal }));
      }
      return current.map((split) => ({
        ...split,
        fraction: split.fraction / total,
      }));
    });
  }

  function addSplit() {
    setSplits((current) => {
      const next = [...current, { id: crypto.randomUUID(), cellCode: "", fraction: 0.1 }];
      const total = next.reduce((sum, split) => sum + split.fraction, 0);
      return next.map((split) => ({ ...split, fraction: split.fraction / total }));
    });
  }

  return (
    <section className="flex min-h-0 flex-col rounded-md border bg-card shadow-sm">
      <header className="border-b px-3 py-3">
        <p className="cockpit-zone-title">Adjudication</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {formatTenderStage(item.entity_type)} / {item.id}
        </p>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3">
        <NormalizedEntity item={item} />

        <div className="grid grid-cols-3 gap-1">
          <Button type="button" variant="secondary" disabled={isResolving} onClick={acceptItem}>
            {isResolving ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Check className="size-4" aria-hidden />
            )}
            Accept
          </Button>
          <Button
            type="button"
            variant={mode === "edit" ? "secondary" : "outline"}
            disabled={isResolving}
            onClick={() => onModeChange("edit")}
          >
            <Pencil className="size-4" aria-hidden />
            Edit
          </Button>
          <Button
            type="button"
            variant={mode === "split" ? "secondary" : "outline"}
            disabled={isResolving || item.entity_type !== "mapping"}
            onClick={() => onModeChange("split")}
          >
            <Split className="size-4" aria-hidden />
            Split
          </Button>
        </div>

        {mode === "edit" || mode === "split" ? (
          <div className="space-y-3 rounded-md border bg-background p-3">
            {item.entity_type === "cell_status" ? (
              <>
                <FieldLabel label="Status">
                  <select
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    value={status}
                    onChange={(event) => setStatus(event.target.value)}
                  >
                    {CELL_STATUSES.map((candidate) => (
                      <option key={candidate} value={candidate}>
                        {formatTenderStatus(candidate)}
                      </option>
                    ))}
                  </select>
                </FieldLabel>
                <FieldLabel label="Amount">
                  <input
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    inputMode="decimal"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    placeholder="0.00"
                  />
                </FieldLabel>
              </>
            ) : null}

            {item.entity_type === "mapping" ? (
              <>
                <TaxonomyPicker
                  query={cellQuery}
                  options={cellOptions}
                  error={searchError}
                  onQueryChange={setCellQuery}
                  onSelect={(cell) => {
                    setSelectedCell(cell);
                    setCellQuery(`${cell.code} ${cell.name}`);
                    setSplitCell(0, cell.code);
                  }}
                />
                {mode === "split" ? (
                  <div className="space-y-2">
                    {splits.map((split, index) => (
                      <div key={split.id} className="rounded-md border p-2">
                        <FieldLabel label={`Cell ${index + 1}`}>
                          <select
                            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                            value={split.cellCode}
                            onChange={(event) => setSplitCell(index, event.target.value)}
                          >
                            <option value="">Choose cell</option>
                            {taxonomy.map((cell) => (
                              <option key={cell.code} value={cell.code}>
                                {cell.code} {cell.name}
                              </option>
                            ))}
                          </select>
                        </FieldLabel>
                        <div className="mt-2 flex items-center gap-2">
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            className="min-w-0 flex-1"
                            value={split.fraction}
                            onChange={(event) =>
                              setSplitFraction(index, Number(event.target.value))
                            }
                            onPointerUp={normalizeSplitFractions}
                            onBlur={normalizeSplitFractions}
                          />
                          <span className="w-12 text-right text-xs tabular-nums">
                            {Math.round(split.fraction * 100)}%
                          </span>
                        </div>
                      </div>
                    ))}
                    <Button type="button" size="sm" variant="outline" onClick={addSplit}>
                      <Split className="size-4" aria-hidden />
                      Add split
                    </Button>
                  </div>
                ) : null}
              </>
            ) : null}

            {item.entity_type === "flag" ? (
              <>
                <FieldLabel label="Severity">
                  <select
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    value={severity}
                    onChange={(event) => setSeverity(event.target.value)}
                  >
                    {FLAG_SEVERITIES.map((candidate) => (
                      <option key={candidate} value={candidate}>
                        {formatTenderStage(candidate)}
                      </option>
                    ))}
                  </select>
                </FieldLabel>
                <FieldLabel label="Headline">
                  <input
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    value={headline}
                    onChange={(event) => setHeadline(event.target.value)}
                  />
                </FieldLabel>
                <FieldLabel label="Detail">
                  <textarea
                    className="min-h-24 w-full rounded-md border bg-background px-2 py-2 text-sm"
                    value={detail}
                    onChange={(event) => setDetail(event.target.value)}
                  />
                </FieldLabel>
              </>
            ) : null}

            {item.entity_type === "document_classification" ? (
              <FieldLabel label="Document type">
                <select
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={docType}
                  onChange={(event) => setDocType(event.target.value)}
                >
                  {DOCUMENT_TYPES.map((candidate) => (
                    <option key={candidate} value={candidate}>
                      {formatTenderStage(candidate)}
                    </option>
                  ))}
                </select>
              </FieldLabel>
            ) : null}
          </div>
        ) : null}

        <FieldLabel label="Reason">
          <textarea
            className="min-h-20 w-full rounded-md border bg-background px-2 py-2 text-sm"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </FieldLabel>

        {error ? (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>

      <footer className="flex flex-wrap gap-2 border-t p-3">
        <Button
          type="button"
          disabled={isResolving || mode === "review"}
          onClick={() => void saveCorrection()}
        >
          {isResolving ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <Save className="size-4" aria-hidden />
          )}
          Save correction
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={isResolving || item.entity_type !== "flag"}
          onClick={() => void suppressItem()}
        >
          <Ban className="size-4" aria-hidden />
          Suppress
        </Button>
      </footer>
    </section>
  );
}

function NormalizedEntity({ item }: { item: TenderQaItem }) {
  const payloadRows = Object.entries(item.payload).filter(
    ([, value]) =>
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null,
  );
  return (
    <div className="rounded-md border bg-background p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">{entityTitle(item)}</p>
        <span className="text-xs text-muted-foreground">
          {formatTenderMoney(item.report_impact_cents)}
        </span>
      </div>
      <dl className="mt-3 grid gap-2 text-xs">
        {payloadRows.slice(0, 8).map(([key, value]) => (
          <div key={key} className="grid grid-cols-[6rem_minmax(0,1fr)] gap-2">
            <dt className="truncate text-muted-foreground">{formatTenderStage(key)}</dt>
            <dd className="truncate font-medium" title={String(value ?? "")}>
              {String(value ?? "None")}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function FieldLabel({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function TaxonomyPicker({
  query,
  options,
  error,
  onQueryChange,
  onSelect,
}: {
  query: string;
  options: TenderTaxonomyCell[];
  error: string | null;
  onQueryChange: (query: string) => void;
  onSelect: (cell: TenderTaxonomyCell) => void;
}) {
  return (
    <div>
      <FieldLabel label="Taxonomy cell">
        <div className="relative">
          <Search className="pointer-events-none absolute top-2.5 left-2 size-4 text-muted-foreground" />
          <input
            className="h-9 w-full rounded-md border bg-background pr-2 pl-8 text-sm"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
      </FieldLabel>
      {error ? <p className="mt-1 text-xs text-destructive">{error}</p> : null}
      {options.length ? (
        <div className="mt-2 max-h-48 overflow-y-auto rounded-md border bg-background">
          {options.map((cell) => (
            <button
              key={cell.code}
              type="button"
              className={cn(
                "block w-full border-b px-2 py-2 text-left text-xs last:border-b-0",
                "hover:bg-muted",
              )}
              onClick={() => onSelect(cell)}
            >
              <span className="font-mono font-medium">{cell.code}</span>{" "}
              <span className="font-medium">{cell.name}</span>
              <span className="ml-2 text-muted-foreground">{cell.group}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function correctedValue(
  item: TenderQaItem,
  form: {
    status: string;
    amount: string;
    selectedCellCode: string;
    docType: string;
    severity: string;
    headline: string;
    detail: string;
    splits: SplitTarget[];
  },
): Record<string, unknown> {
  if (item.entity_type === "cell_status") {
    return {
      status: form.status,
      amount_cents: dollarsToCents(form.amount),
    };
  }
  if (item.entity_type === "mapping") {
    const splitRows = form.splits
      .filter((split) => split.cellCode.trim())
      .map((split) => ({
        cell_code: split.cellCode,
        allocation_fraction: Number(split.fraction.toFixed(4)),
      }));
    return {
      cell_code: form.selectedCellCode || splitRows[0]?.cell_code || "",
      splits: splitRows,
    };
  }
  if (item.entity_type === "flag") {
    return {
      severity: form.severity,
      headline: form.headline,
      detail: form.detail,
      include_in_report: true,
    };
  }
  return { doc_type: form.docType };
}

function entityTitle(item: TenderQaItem): string {
  const payload = item.payload;
  return (
    readString(payload.headline) ??
    readString(payload.description_raw) ??
    readString(payload.filename) ??
    (readString(payload.cell_code) ? `Cell ${readString(payload.cell_code)}` : null) ??
    formatTenderStage(item.entity_type)
  );
}

function localTaxonomyMatches(
  taxonomy: TenderTaxonomyCell[],
  query: string,
): TenderTaxonomyCell[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];
  return taxonomy.filter((cell) =>
    `${cell.code} ${cell.name} ${cell.group}`.toLowerCase().includes(normalized),
  );
}

function findTaxonomyCell(
  taxonomy: TenderTaxonomyCell[],
  code: string | null,
): TenderTaxonomyCell | null {
  if (!code) return null;
  return taxonomy.find((cell) => cell.code === code) ?? null;
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function centsToDollarInput(cents: number | null): string {
  if (cents === null) return "";
  return String(cents / 100);
}

function dollarsToCents(value: string): number | null {
  const normalized = value.replace(/[$,]/g, "").trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? Math.round(parsed * 100) : null;
}
