import {
  ArrowDownToLine,
  ArrowUpToLine,
  Download,
  FileText,
  GitCompareArrows,
  LoaderCircle,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Shield,
  ShieldOff,
  Trash,
} from "lucide-react";
import { useMemo, useState } from "react";

import { SitewiseMark } from "@/components/SitewiseMark";
import {
  ExcelFileIcon,
  WordFileIcon,
} from "@/components/icons/OfficeFileIcons";
import { CopyContentButton } from "@/components/project/CopyContentButton";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { MenuSelect } from "@/components/ui/menu-select";
import { cn } from "@/lib/utils";
import type {
  ProcurementRequest,
  ProcurementStrategy,
  ProcurementStrategyOperation,
  ProcurementStrategyRow,
  ProcurementStrategyStatus,
  ProjectDiscipline,
} from "@/lib/types/project";

const STATUS_MILESTONES: Array<{
  value: ProcurementStrategyStatus;
  label: string;
  shortLabel: string;
}> = [
  { value: "issued", label: "Issued", shortLabel: "Issued" },
  { value: "responses_received", label: "Submitted", shortLabel: "Submitted" },
  { value: "evaluating", label: "Recommendation", shortLabel: "Rec." },
  { value: "awarded", label: "Contract", shortLabel: "Contract" },
];

type InsertTarget = {
  anchorId: string | null;
  placement: "before" | "after";
};

const byStrategyRowName = (
  left: ProcurementStrategyRow,
  right: ProcurementStrategyRow,
) =>
  left.discipline_label.localeCompare(right.discipline_label, undefined, {
    sensitivity: "base",
    numeric: true,
  });

export function ProcurementStrategyGrid({
  strategy,
  disciplines,
  saving,
  refreshing = false,
  requestsByRowId = {},
  onApply,
  onRefresh,
  onCreateRequest,
  onOpenRequest,
  onCompare,
  onEditWithAi,
}: {
  strategy: ProcurementStrategy;
  disciplines: ProjectDiscipline[];
  saving: boolean;
  refreshing?: boolean;
  requestsByRowId?: Record<string, ProcurementRequest | undefined>;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
  onRefresh: () => Promise<void>;
  onCreateRequest?: (row: ProcurementStrategyRow) => void;
  onOpenRequest?: (request: ProcurementRequest) => void;
  onCompare?: (row: ProcurementStrategyRow) => void;
  onEditWithAi?: (row: ProcurementStrategyRow) => void;
}) {
  const [insertTarget, setInsertTarget] = useState<InsertTarget | null>(null);
  const [insertCode, setInsertCode] = useState("");
  const [exportAction, setExportAction] = useState<"csv" | "docx" | "xlsx" | null>(
    null,
  );
  const [exportError, setExportError] = useState<string | null>(null);
  const usedCodes = useMemo(
    () => new Set(strategy.rows.flatMap((row) => (row.discipline_code ? [row.discipline_code] : []))),
    [strategy.rows],
  );
  const availableDisciplines = disciplines.filter(
    (discipline) => !usedCodes.has(discipline.code),
  );

  async function addSelectedDiscipline() {
    if (!insertTarget || !insertCode) return;
    const operation: ProcurementStrategyOperation = {
      operation: "ADD_ROW",
      discipline_code: insertCode,
      ...(insertTarget.anchorId
        ? insertTarget.placement === "before"
          ? { before_row_id: insertTarget.anchorId }
          : { after_row_id: insertTarget.anchorId }
        : {}),
    };
    setInsertTarget(null);
    setInsertCode("");
    await onApply([operation]);
  }

  function requestInsert(anchorId: string | null, placement: "before" | "after") {
    setInsertTarget({ anchorId, placement });
    setInsertCode(availableDisciplines[0]?.code ?? "");
  }

  const tableRows: Array<
    | { type: "data"; row: ProcurementStrategyRow }
    | { type: "insert"; key: string }
    | { type: "group"; key: string; label: "Consultants" | "Trades" }
  > = [];
  const groupedRows = [
    {
      key: "consultants",
      label: "Consultants" as const,
      rows: strategy.rows
        .filter((row) => row.participant_type === "consultant")
        .sort(byStrategyRowName),
    },
    {
      key: "trades",
      label: "Trades" as const,
      rows: strategy.rows
        .filter((row) => row.participant_type !== "consultant")
        .sort(byStrategyRowName),
    },
  ];
  for (const group of groupedRows) {
    if (group.rows.length === 0) continue;
    tableRows.push({ type: "group", key: group.key, label: group.label });
    for (const row of group.rows) {
      if (insertTarget?.anchorId === row.id && insertTarget.placement === "before") {
        tableRows.push({ type: "insert", key: `before-${row.id}` });
      }
      tableRows.push({ type: "data", row });
      if (insertTarget?.anchorId === row.id && insertTarget.placement === "after") {
        tableRows.push({ type: "insert", key: `after-${row.id}` });
      }
    }
  }

  async function downloadStrategyExport(format: "csv" | "docx" | "xlsx") {
    setExportAction(format);
    setExportError(null);
    try {
      const blob = await api.downloadProcurementStrategy(strategy.project_id, format);
      downloadBlob(
        blob,
        `Procurement_Strategy_v${String(strategy.revision).padStart(2, "0")}.${format}`,
      );
    } catch (error) {
      setExportError(
        error instanceof ApiError
          ? error.message
          : `Could not export ${format.toUpperCase()}.`,
      );
    } finally {
      setExportAction(null);
    }
  }
  if (insertTarget?.anchorId === null) {
    tableRows.push({ type: "insert", key: "end" });
  }

  const exportContent = procurementStrategyExport(strategy, "\t");

  return (
    <section aria-label="Procurement Strategy" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            size="sm"
            disabled={saving || availableDisciplines.length === 0}
            onClick={() => requestInsert(null, "after")}
          >
            <Plus className="size-3.5" aria-hidden />
            Add discipline
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={saving || refreshing}
            onClick={() => void onRefresh()}
          >
            {refreshing ? (
              <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-3.5" aria-hidden />
            )}
            Sync
          </Button>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          {exportError ? (
            <span className="self-center text-xs text-destructive" role="alert">
              {exportError}
            </span>
          ) : null}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-9 text-muted-foreground hover:text-foreground"
                aria-label="Download procurement strategy"
                title="Download"
                disabled={exportAction !== null}
              >
                <Download
                  className={cn("size-5", exportAction !== null && "animate-pulse")}
                  aria-hidden
                />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[11rem]">
              <DropdownMenuItem
                className="gap-2.5 py-2"
                disabled={exportAction !== null}
                onSelect={() => void downloadStrategyExport("xlsx")}
              >
                <ExcelFileIcon className="size-6" />
                <span>Excel</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2.5 py-2"
                disabled={exportAction !== null}
                onSelect={() => void downloadStrategyExport("csv")}
              >
                <FileText className="size-5 text-[var(--sw-positive)]" aria-hidden />
                <span>CSV</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2.5 py-2"
                disabled={exportAction !== null}
                onSelect={() => void downloadStrategyExport("docx")}
              >
                <WordFileIcon className="size-6" />
                <span>Word</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <CopyContentButton
            content={exportContent}
            label="Copy procurement strategy"
            size="icon"
            className="size-9"
          />
        </div>
      </div>

      <div className="overflow-hidden border border-border bg-[var(--sw-panel)]">
        <table className="w-full table-fixed border-collapse text-sm">
          <colgroup>
            <col style={{ width: "16%" }} />
            {Array.from({ length: strategy.tenderer_column_count }, (_, index) => (
              <col
                key={index}
                style={{
                  width: strategy.tenderer_column_count === 3 ? "15%" : "12%",
                }}
              />
            ))}
            <col
              style={{
                width: strategy.tenderer_column_count === 3 ? "35%" : "32%",
              }}
            />
            <col style={{ width: "4%" }} />
          </colgroup>
          <thead>
            <tr className="border-b border-border bg-muted/35 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <th className="border-r border-border bg-muted px-2.5 py-2.5 normal-case tracking-normal text-foreground">
                Discipline
              </th>
              {Array.from({ length: strategy.tenderer_column_count }, (_, index) => (
                <th key={index} className="px-1.5 py-2.5 normal-case tracking-normal">
                  <div className="flex items-center justify-between gap-1">
                    <span className="truncate">Firm {index + 1}</span>
                    {strategy.tenderer_column_count === 3 && index === 2 ? (
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        className="shrink-0 text-muted-foreground"
                        aria-label="Add firm column"
                        title="Add firm column"
                        disabled={saving}
                        onClick={() =>
                          void onApply([
                            {
                              operation: "SET_TENDERER_COLUMN_COUNT",
                              tenderer_column_count: 4,
                            },
                          ])
                        }
                      >
                        <Plus className="size-3.5" aria-hidden />
                      </Button>
                    ) : null}
                  </div>
                </th>
              ))}
              <th className="px-1.5 py-2.5 normal-case tracking-normal">Status</th>
              <th className="px-1 py-2.5"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((item) =>
              item.type === "group" ? (
                <tr key={item.key} className="border-y border-border bg-muted/50">
                  <th
                    scope="rowgroup"
                    colSpan={strategy.tenderer_column_count + 3}
                    className="px-2.5 py-2 text-left text-xs font-semibold uppercase tracking-wide text-foreground"
                  >
                    {item.label}
                  </th>
                </tr>
              ) : item.type === "insert" ? (
                <InsertRow
                  key={item.key}
                  columnCount={strategy.tenderer_column_count}
                  options={availableDisciplines}
                  value={insertCode}
                  saving={saving}
                  onChange={setInsertCode}
                  onCancel={() => {
                    setInsertTarget(null);
                    setInsertCode("");
                  }}
                  onAdd={() => void addSelectedDiscipline()}
                />
              ) : (
                <StrategyRow
                  key={item.row.id}
                  row={item.row}
                  columnCount={strategy.tenderer_column_count}
                  saving={saving}
                  request={requestsByRowId[item.row.id]}
                  onApply={onApply}
                  onInsert={requestInsert}
                  onCreateRequest={onCreateRequest}
                  onOpenRequest={onOpenRequest}
                  onCompare={onCompare}
                  onEditWithAi={onEditWithAi}
                />
              ),
            )}
          </tbody>
        </table>
        {strategy.rows.length === 0 && !insertTarget ? (
          <div className="px-4 py-10 text-center text-sm text-muted-foreground">
            No disciplines yet. Add the first discipline to build the procurement roster.
          </div>
        ) : null}
      </div>
    </section>
  );
}

function procurementStrategyExport(
  strategy: ProcurementStrategy,
  delimiter: "," | "\t",
): string {
  return procurementStrategyRows(strategy)
    .map((row) => row.map((value) => escapeExportCell(value, delimiter)).join(delimiter))
    .join("\n");
}

function procurementStrategyRows(strategy: ProcurementStrategy): string[][] {
  return [[
    "Discipline",
    ...Array.from(
      { length: strategy.tenderer_column_count },
      (_, index) => `Firm ${index + 1}`,
    ),
    "Status",
  ], ...strategy.rows.map((row) => [
    row.discipline_label,
    ...Array.from(
      { length: strategy.tenderer_column_count },
      (_, index) =>
        row.candidates.find((candidate) => candidate.slot === index + 1)
          ?.company_name ?? "",
    ),
    row.status,
  ])];
}

function escapeExportCell(value: string, delimiter: "," | "\t"): string {
  if (!value.includes('"') && !value.includes("\n") && !value.includes(delimiter)) {
    return value;
  }
  return `"${value.replaceAll('"', '""')}"`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function StrategyRow({
  row,
  columnCount,
  saving,
  request,
  onApply,
  onInsert,
  onCreateRequest,
  onOpenRequest,
  onCompare,
  onEditWithAi,
}: {
  row: ProcurementStrategyRow;
  columnCount: 3 | 4;
  saving: boolean;
  request?: ProcurementRequest;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
  onInsert: (anchorId: string, placement: "before" | "after") => void;
  onCreateRequest?: (row: ProcurementStrategyRow) => void;
  onOpenRequest?: (request: ProcurementRequest) => void;
  onCompare?: (row: ProcurementStrategyRow) => void;
  onEditWithAi?: (row: ProcurementStrategyRow) => void;
}) {
  const protectedCell = row.locked || saving;
  const requestLabel = requestTypeLabel(row.request_kind);
  const comparableFirmCount = row.candidates.filter(
    (candidate) => candidate.company_name.trim().length > 0,
  ).length;
  return (
    <tr
      className={cn(
        "border-b border-border/70 last:border-b-0 hover:bg-muted/20",
        row.no_longer_required && "text-muted-foreground",
      )}
    >
      <th
        scope="row"
        className="border-r border-border bg-[var(--sw-panel)] px-2.5 py-2 text-left font-medium"
      >
        <div className="flex items-center gap-2">
          {row.locked ? <Shield className="size-3.5 shrink-0 text-muted-foreground" aria-label="Locked" /> : null}
          <span className="min-w-0 truncate" title={row.discipline_label}>
            {row.discipline_label}
          </span>
        </div>
        {row.no_longer_required ? (
          <span className="mt-1 block text-[11px] font-normal text-muted-foreground">
            No longer required by profile
          </span>
        ) : null}
      </th>
      {Array.from({ length: columnCount }, (_, index) => {
        const slot = index + 1;
        const candidate = row.candidates.find((item) => item.slot === slot);
        return (
          <td key={slot} className="px-1.5 py-1.5 align-top">
            <EditableCell
              key={candidate?.company_name ?? "empty"}
              ariaLabel={`${row.discipline_label}, Firm ${slot}`}
              value={candidate?.company_name ?? ""}
              placeholder="Add firm"
              disabled={protectedCell}
              onCommit={(companyName) =>
                onApply([
                  companyName
                    ? {
                        operation: "UPSERT_CANDIDATE",
                        row_id: row.id,
                        slot,
                        company_name: companyName,
                      }
                    : { operation: "CLEAR_CANDIDATE", row_id: row.id, slot },
                ])
              }
            />
          </td>
        );
      })}
      <td className="px-1.5 py-1.5 align-top">
        <div className="flex items-center gap-1">
          <StatusMilestones
            row={row}
            disabled={protectedCell}
            onApply={onApply}
          />
          {request?.current_draft ? (
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="shrink-0 rounded-sm text-[var(--sw-beam-hex)]"
              aria-label={`Open ${row.discipline_label} ${requestLabel}`}
              title={`${requestLabel} v${request.current_draft.version} · ${requestStatusLabel(request)}`}
              onClick={() => onOpenRequest?.(request)}
            >
              <FileText className="size-3.5" aria-hidden />
            </Button>
          ) : request ? (
            <span
              className="inline-flex size-6 shrink-0 items-center justify-center text-muted-foreground"
              aria-label={`Preparing ${row.discipline_label} ${requestLabel}`}
              title={`Preparing ${requestLabel}`}
            >
              <LoaderCircle className="size-3 animate-spin" aria-hidden />
            </span>
          ) : null}
        </div>
      </td>
      <td className="px-1 py-1.5 align-top text-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              size="icon-xs"
              variant="outline"
              className="border-transparent bg-transparent text-muted-foreground shadow-none"
              aria-label={`Actions for ${row.discipline_label}`}
              title="Actions"
              disabled={saving}
            >
              <MoreHorizontal className="size-3.5" aria-hidden />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-48">
            {request?.current_draft ? (
              <DropdownMenuItem onSelect={() => onOpenRequest?.(request)}>
                <FileText className="size-3.5" aria-hidden />
                Open {requestLabel}
              </DropdownMenuItem>
            ) : !request ? (
              <DropdownMenuItem
                disabled={!onCreateRequest}
                onSelect={() => onCreateRequest?.(row)}
              >
                <FileText className="size-3.5" aria-hidden />
                Create {requestLabel}
              </DropdownMenuItem>
            ) : null}
            <DropdownMenuItem
              disabled={!onCompare || comparableFirmCount < 2}
              title={
                comparableFirmCount < 2
                  ? "Add at least two firms before comparing"
                  : "Compare firms"
              }
              onSelect={() => onCompare?.(row)}
            >
              <GitCompareArrows className="size-3.5" aria-hidden />
              Compare firms
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label={`Edit ${row.discipline_label} with AI`}
              title={`Edit ${row.discipline_label} with AI`}
              disabled={!onEditWithAi}
              onSelect={() => onEditWithAi?.(row)}
            >
              <SitewiseMark size={14} variant="solid" className="p-0" title="" />
              Edit with AI
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label="Add row above"
              title="Add row above"
              onSelect={() => onInsert(row.id, "before")}
            >
              <ArrowUpToLine className="size-3.5 shrink-0" aria-hidden />
              Add discipline above
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label="Add row below"
              title="Add row below"
              onSelect={() => onInsert(row.id, "after")}
            >
              <ArrowDownToLine className="size-3.5 shrink-0" aria-hidden />
              Add discipline below
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label={row.locked ? `Unlock ${row.discipline_label}` : `Lock ${row.discipline_label}`}
              title={row.locked ? `Unlock ${row.discipline_label}` : `Lock ${row.discipline_label}`}
              onSelect={() =>
                void onApply([
                  { operation: row.locked ? "UNLOCK_ROW" : "LOCK_ROW", row_id: row.id },
                ])
              }
            >
              {row.locked ? (
                <ShieldOff className="size-3.5 shrink-0" aria-hidden />
              ) : (
                <Shield className="size-3.5 shrink-0" aria-hidden />
              )}
              {row.locked ? "Unlock row" : "Lock row"}
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label={`Delete ${row.discipline_label}`}
              title={`Delete ${row.discipline_label}`}
              variant="destructive"
              disabled={row.locked}
              onSelect={() => {
                const needsConfirmation =
                  row.candidates.length > 0 || row.linked_request_ids.length > 0;
                if (
                  needsConfirmation &&
                  !window.confirm(
                    `Delete ${row.discipline_label} and its firm information?`,
                  )
                ) {
                  return;
                }
                void onApply([{ operation: "DELETE_ROW", row_id: row.id }]);
              }}
            >
              <Trash className="size-3.5 shrink-0" aria-hidden />
              Delete row
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function StatusMilestones({
  row,
  disabled,
  onApply,
}: {
  row: ProcurementStrategyRow;
  disabled: boolean;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
}) {
  const currentIndex = STATUS_MILESTONES.findIndex(
    (milestone) => milestone.value === row.status,
  );

  return (
    <div
      role="group"
      aria-label={`${row.discipline_label} status`}
      className="grid min-w-0 flex-1 grid-cols-4 overflow-hidden rounded-sm border border-border"
    >
      {STATUS_MILESTONES.map((milestone, index) => {
        const fulfilled = currentIndex >= index;
        return (
          <button
            key={milestone.value}
            type="button"
            aria-label={`${row.discipline_label}: ${milestone.label}`}
            aria-pressed={fulfilled}
            title={milestone.label}
            disabled={disabled}
            className={cn(
              "h-7 min-w-0 border-r border-border px-1 text-[10px] font-medium text-muted-foreground outline-none transition-colors last:border-r-0 hover:bg-muted hover:text-foreground focus-visible:relative focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
              fulfilled &&
                "bg-[color-mix(in_oklch,var(--sw-beam)_14%,transparent)] text-foreground",
            )}
            onClick={() => {
              const status =
                currentIndex === index
                  ? index === 0
                    ? "not_started"
                    : STATUS_MILESTONES[index - 1].value
                  : milestone.value;
              void onApply([
                {
                  operation: "UPDATE_ROW",
                  row_id: row.id,
                  status,
                },
              ]);
            }}
          >
            <span className="block truncate">{milestone.shortLabel}</span>
          </button>
        );
      })}
    </div>
  );
}

function requestTypeLabel(kind: ProcurementRequest["kind"]): "RFP" | "RFT" | "RFQ" {
  if (kind === "consultant_rfp") return "RFP";
  if (kind === "trade_rfq") return "RFQ";
  return "RFT";
}

function requestStatusLabel(request: ProcurementRequest): string {
  if (request.status === "issued") return "Issued";
  if (request.status === "closed") return "Closed";
  if (request.status === "cancelled") return "Cancelled";
  return "Draft";
}

function EditableCell({
  value,
  placeholder,
  ariaLabel,
  disabled,
  onCommit,
}: {
  value: string;
  placeholder: string;
  ariaLabel: string;
  disabled: boolean;
  onCommit: (value: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState(value);
  function commit() {
    const next = draft.trim();
    if (next === value) return;
    void onCommit(next);
  }
  return (
    <Input
      value={draft}
      disabled={disabled}
      aria-label={ariaLabel}
      placeholder={placeholder}
      className="h-8 min-w-0 border-transparent bg-transparent px-1.5 hover:border-input focus-visible:bg-background"
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
        if (event.key === "Escape") {
          setDraft(value);
          event.currentTarget.blur();
        }
      }}
    />
  );
}

function InsertRow({
  columnCount,
  options,
  value,
  saving,
  onChange,
  onCancel,
  onAdd,
}: {
  columnCount: 3 | 4;
  options: ProjectDiscipline[];
  value: string;
  saving: boolean;
  onChange: (value: string) => void;
  onCancel: () => void;
  onAdd: () => void;
}) {
  return (
    <tr className="border-b border-border bg-primary/5">
      <td className="border-r border-border bg-[var(--sw-panel)] px-2 py-2">
        <MenuSelect
          value={value}
          options={options.map((item) => ({ value: item.code, label: item.label }))}
          onChange={onChange}
          placeholder="Choose discipline"
          aria-label="Discipline to add"
          className="rounded-none"
        />
      </td>
      <td colSpan={columnCount + 2} className="px-2 py-2">
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" disabled={!value || saving} onClick={onAdd}>
            Add row
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </td>
    </tr>
  );
}
