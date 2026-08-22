import {
  ArrowDownToLine,
  ArrowUpToLine,
  ExternalLink,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Shield,
  ShieldOff,
  Trash,
} from "lucide-react";
import { useMemo, useState } from "react";

import { SitewiseMark } from "@/components/SitewiseMark";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { MenuSelect } from "@/components/ui/menu-select";
import { cn } from "@/lib/utils";
import type {
  ProcurementStrategy,
  ProcurementStrategyOperation,
  ProcurementStrategyRow,
  ProcurementStrategyStatus,
  ProjectDiscipline,
} from "@/lib/types/project";

const STATUS_OPTIONS: Array<{
  value: ProcurementStrategyStatus;
  label: string;
}> = [
  { value: "issued", label: "RFP issued" },
  { value: "responses_received", label: "Received" },
  { value: "evaluating", label: "Recommendation" },
  { value: "awarded", label: "Awarded" },
];

const VISIBLE_STATUSES = new Set<ProcurementStrategyStatus>(
  STATUS_OPTIONS.map((option) => option.value),
);

type InsertTarget = {
  anchorId: string | null;
  placement: "before" | "after";
};

export function ProcurementStrategyGrid({
  strategy,
  disciplines,
  saving,
  onApply,
  onRefresh,
  onEditWithAi,
}: {
  strategy: ProcurementStrategy;
  disciplines: ProjectDiscipline[];
  saving: boolean;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
  onRefresh: () => Promise<void>;
  onEditWithAi?: (row: ProcurementStrategyRow) => void;
}) {
  const [insertTarget, setInsertTarget] = useState<InsertTarget | null>(null);
  const [insertCode, setInsertCode] = useState("");
  const usedCodes = useMemo(
    () => new Set(strategy.rows.flatMap((row) => (row.discipline_code ? [row.discipline_code] : []))),
    [strategy.rows],
  );
  const availableDisciplines = disciplines.filter(
    (discipline) => !usedCodes.has(discipline.code),
  );

  async function addSelectedDiscipline() {
    if (!insertTarget || !insertCode) return;
    await onApply([
      {
        operation: "ADD_ROW",
        discipline_code: insertCode,
        ...(insertTarget.anchorId
          ? insertTarget.placement === "before"
            ? { before_row_id: insertTarget.anchorId }
            : { after_row_id: insertTarget.anchorId }
          : {}),
      },
    ]);
    setInsertTarget(null);
    setInsertCode("");
  }

  function requestInsert(anchorId: string | null, placement: "before" | "after") {
    setInsertTarget({ anchorId, placement });
    setInsertCode(availableDisciplines[0]?.code ?? "");
  }

  const tableRows: Array<
    | { type: "data"; row: ProcurementStrategyRow }
    | { type: "insert"; key: string }
  > = [];
  for (const row of strategy.rows) {
    if (insertTarget?.anchorId === row.id && insertTarget.placement === "before") {
      tableRows.push({ type: "insert", key: `before-${row.id}` });
    }
    tableRows.push({ type: "data", row });
    if (insertTarget?.anchorId === row.id && insertTarget.placement === "after") {
      tableRows.push({ type: "insert", key: `after-${row.id}` });
    }
  }
  if (insertTarget?.anchorId === null) {
    tableRows.push({ type: "insert", key: "end" });
  }

  return (
    <section aria-label="Procurement Strategy" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm text-muted-foreground">
          {strategy.rows.length} {strategy.rows.length === 1 ? "discipline" : "disciplines"}
          <span aria-hidden> · </span>
          Revision {strategy.revision}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={saving}
            onClick={() => void onRefresh()}
          >
            <RefreshCw className={cn("size-3.5", saving && "animate-spin")} aria-hidden />
            Refresh roster
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={saving || availableDisciplines.length === 0}
            onClick={() => requestInsert(null, "after")}
          >
            <Plus className="size-3.5" aria-hidden />
            Add discipline
          </Button>
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
            <col style={{ width: "13%" }} />
            <col
              style={{
                width: strategy.tenderer_column_count === 3 ? "22%" : "19%",
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
                    <span className="truncate">Tenderer {index + 1}</span>
                    {strategy.tenderer_column_count === 3 && index === 2 ? (
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        className="shrink-0 text-muted-foreground"
                        aria-label="Add tenderer column"
                        title="Add tenderer column"
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
              <th className="px-1.5 py-2.5 normal-case tracking-normal">Notes</th>
              <th className="px-1 py-2.5"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((item) =>
              item.type === "insert" ? (
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
                  onApply={onApply}
                  onInsert={requestInsert}
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

function StrategyRow({
  row,
  columnCount,
  saving,
  onApply,
  onInsert,
  onEditWithAi,
}: {
  row: ProcurementStrategyRow;
  columnCount: 3 | 4;
  saving: boolean;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
  onInsert: (anchorId: string, placement: "before" | "after") => void;
  onEditWithAi?: (row: ProcurementStrategyRow) => void;
}) {
  const protectedCell = row.locked || saving;
  return (
    <tr
      className={cn(
        "border-b border-border/70 last:border-b-0 hover:bg-muted/20",
        row.no_longer_required && "text-muted-foreground",
      )}
    >
      <th className="border-r border-border bg-[var(--sw-panel)] px-2.5 py-2 text-left font-medium">
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
              ariaLabel={`${row.discipline_label}, Tenderer ${slot}`}
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
            {candidate?.source_url ? (
              <a
                href={candidate.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                Source <ExternalLink className="size-3" aria-hidden />
              </a>
            ) : null}
          </td>
        );
      })}
      <td className="px-1.5 py-1.5 align-top">
        <MenuSelect
          value={VISIBLE_STATUSES.has(row.status) ? row.status : ""}
          options={STATUS_OPTIONS}
          placeholder="—"
          disabled={protectedCell}
          aria-label={`${row.discipline_label} status`}
          className="h-8 min-w-0 rounded-none border-transparent bg-transparent px-1.5 text-xs hover:border-input"
          onChange={(value) =>
            void onApply([
              {
                operation: "UPDATE_ROW",
                row_id: row.id,
                status: value as ProcurementStrategyStatus,
              },
            ])
          }
        />
      </td>
      <td className="px-1.5 py-1.5 align-top">
        <EditableCell
          key={row.notes}
          ariaLabel={`${row.discipline_label} notes`}
          value={row.notes}
          placeholder="Add note"
          disabled={protectedCell}
          onCommit={(notes) =>
            onApply([{ operation: "UPDATE_ROW", row_id: row.id, notes }])
          }
        />
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
          <DropdownMenuContent align="end" className="min-w-0 w-auto">
            <DropdownMenuItem
              aria-label={`Edit ${row.discipline_label} with AI`}
              title={`Edit ${row.discipline_label} with AI`}
              className="justify-center px-2 py-2"
              disabled={!onEditWithAi}
              onSelect={() => onEditWithAi?.(row)}
            >
              <SitewiseMark size={14} variant="solid" className="p-0" title="" />
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label="Add row above"
              title="Add row above"
              className="justify-center px-2 py-2"
              onSelect={() => onInsert(row.id, "before")}
            >
              <ArrowUpToLine className="size-3.5 shrink-0" aria-hidden />
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label="Add row below"
              title="Add row below"
              className="justify-center px-2 py-2"
              onSelect={() => onInsert(row.id, "after")}
            >
              <ArrowDownToLine className="size-3.5 shrink-0" aria-hidden />
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label={row.locked ? `Unlock ${row.discipline_label}` : `Lock ${row.discipline_label}`}
              title={row.locked ? `Unlock ${row.discipline_label}` : `Lock ${row.discipline_label}`}
              className="justify-center px-2 py-2"
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
            </DropdownMenuItem>
            <DropdownMenuItem
              aria-label={`Delete ${row.discipline_label}`}
              title={`Delete ${row.discipline_label}`}
              className="justify-center px-2 py-2"
              variant="destructive"
              disabled={row.locked}
              onSelect={() => {
                const needsConfirmation =
                  row.candidates.length > 0 || row.linked_request_ids.length > 0;
                if (
                  needsConfirmation &&
                  !window.confirm(
                    `Delete ${row.discipline_label} and its tenderer information?`,
                  )
                ) {
                  return;
                }
                void onApply([{ operation: "DELETE_ROW", row_id: row.id }]);
              }}
            >
              <Trash className="size-3.5 shrink-0" aria-hidden />
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
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
      <td colSpan={columnCount + 3} className="px-2 py-2">
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
