import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ArrowUpDown,
  Copy,
  Loader2,
  MoreHorizontal,
  Plus,
  Trash,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
  type RefObject,
} from "react";

import { CostInvoiceRegister } from "@/components/project/CostInvoiceRegister";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
import {
  addCostItemOptimistically,
  amount,
  applyCostPlanDelta,
  buildCostPlanViewRows,
  claimedAmountsByItem,
  COST_PLAN_VIRTUALIZE_THRESHOLD,
  costPlanCategories,
  currentBillingMonthValue,
  readCostPlanTab,
  writeCostPlanTab,
  duplicateCostItemOptimistically,
  forecastFromContractAndVariations,
  formatCostPlanDeletionError,
  formatCostPlanMoney,
  itemVariations,
  nextCostPlanSort,
  parseCostPlanMoneyInput,
  renumberCostPlanItems,
  withItemVariations,
  withOptimisticTotals,
  type CostPlanItem,
  type CostPlanOperation,
  type CostPlanSort,
  type CostPlanSortKey,
  type CostPlanState,
  type CostPlanTab,
  type CostPlanViewRow,
} from "@/lib/cost-plan";
import { ApiError } from "@/lib/http";
import { runOptimisticMutation } from "@/lib/optimistic-mutation";
import { measureLocalMutation } from "@/lib/performance";
import type { InvoiceLedger } from "@/lib/types/project";
import { cn } from "@/lib/utils";

const COST_PLAN_ROW_PX = 26;
const TABLE_COL_COUNT = 13;

function readCachedCostPlan(projectId: string): CostPlanState | null {
  const cached = queryClient.getQueryData<CostPlanState>(
    workbenchKeys.costPlan(projectId),
  );
  if (!cached) return null;
  return {
    ...cached,
    categories: costPlanCategories(cached),
  };
}

function readCachedInvoiceLedger(projectId: string): InvoiceLedger | null {
  return (
    queryClient.getQueryData<InvoiceLedger>(
      workbenchKeys.invoiceLedger(projectId),
    ) ?? null
  );
}

function CostPlanTabPane({
  id,
  active,
  children,
}: {
  id: CostPlanTab;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div
      data-testid={`cost-plan-tab-pane-${id}`}
      hidden={!active}
      aria-hidden={!active}
      inert={!active}
      className={cn(!active && "hidden")}
    >
      {children}
    </div>
  );
}

export function CostPlanGrid({
  projectId,
  revision = null,
  reviewInvoiceId = null,
  active = true,
}: {
  projectId: string;
  /** When the published Cost Plan revision changes (e.g. agent edit), reload. */
  revision?: number | null;
  reviewInvoiceId?: string | null;
  /** False while the workbench is kept mounted but hidden. */
  active?: boolean;
}) {
  const [state, setState] = useState<CostPlanState | null>(() =>
    readCachedCostPlan(projectId),
  );
  const [ledger, setLedger] = useState<InvoiceLedger | null>(() =>
    readCachedInvoiceLedger(projectId),
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [addingCategory, setAddingCategory] = useState(false);
  const [tab, setTab] = useState<CostPlanTab>(() =>
    reviewInvoiceId ? "invoices" : readCostPlanTab(projectId),
  );
  const [tabProjectId, setTabProjectId] = useState(projectId);
  const [openedInvoiceId, setOpenedInvoiceId] = useState(reviewInvoiceId ?? null);
  const [sort, setSort] = useState<CostPlanSort | null>(null);
  const [selectedMonth, setSelectedMonth] = useState(currentBillingMonthValue);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [selectionAnchor, setSelectionAnchor] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const loadedRevisionRef = useRef(revision);

  if (projectId !== tabProjectId) {
    setTabProjectId(projectId);
    setOpenedInvoiceId(reviewInvoiceId ?? null);
    setTab(reviewInvoiceId ? "invoices" : readCostPlanTab(projectId));
  } else if (reviewInvoiceId && reviewInvoiceId !== openedInvoiceId) {
    setOpenedInvoiceId(reviewInvoiceId);
    setTab("invoices");
  }

  function selectTab(next: CostPlanTab) {
    setTab(next);
    writeCostPlanTab(projectId, next);
  }

  useEffect(() => {
    let cancelled = false;
    const fresh = loadedRevisionRef.current !== revision;
    loadedRevisionRef.current = revision;

    async function loadDetail() {
      setError(null);
      try {
        if (fresh) {
          await queryClient.invalidateQueries({
            queryKey: workbenchKeys.costPlan(projectId),
          });
        }
        const value = await queryClient.fetchQuery({
          queryKey: workbenchKeys.costPlan(projectId),
          queryFn: () => api.getCostPlanState(projectId),
        });
        if (!cancelled) {
          setState({
            ...value,
            categories: costPlanCategories(value),
          });
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Cost Plan could not load.",
          );
        }
      }
      try {
        if (fresh) {
          await queryClient.invalidateQueries({
            queryKey: workbenchKeys.invoiceLedger(projectId),
          });
        }
        const value = await queryClient.fetchQuery({
          queryKey: workbenchKeys.invoiceLedger(projectId),
          queryFn: () => api.getInvoiceLedger(projectId),
        });
        if (!cancelled) setLedger(value);
      } catch {
        if (!cancelled) setLedger(null);
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [projectId, revision]);

  async function mutate(
    operations: CostPlanOperation | CostPlanOperation[],
    optimistic: CostPlanState,
  ) {
    if (!state || saving) return;
    const batch = Array.isArray(operations) ? operations : [operations];
    if (!batch.length) return;
    const snapshot = state;
    // Mutation handler timing, not render output.
    const startedAt = performance.now();
    setSaving(true);
    setError(null);
    let unresolvedConflict = false;
    try {
      await runOptimisticMutation({
        snapshot,
        optimistic,
        apply: setState,
        commit: (base) =>
          api.applyCostPlanOperations(projectId, base.version, batch),
        confirmed: (delta) => {
          const next = applyCostPlanDelta(optimistic, delta);
          const resolved = {
            ...next,
            items: renumberCostPlanItems(next.items),
            categories: costPlanCategories(next),
            narrative: {
              ...next.narrative,
              ...optimistic.narrative,
              item_variations: {
                ...next.narrative?.item_variations,
                ...optimistic.narrative?.item_variations,
              },
            },
          };
          queryClient.setQueryData(workbenchKeys.costPlan(projectId), resolved);
          return resolved;
        },
        reload: async () => {
          await queryClient.invalidateQueries({
            queryKey: workbenchKeys.costPlan(projectId),
          });
          const latest = await queryClient.fetchQuery({
            queryKey: workbenchKeys.costPlan(projectId),
            queryFn: () => api.getCostPlanState(projectId),
          });
          return {
            ...latest,
            categories: costPlanCategories(latest),
          };
        },
        rebase: ({ pending, latest }) => {
          const missingTarget = batch.some(
            (operation) =>
              operation.target_type === "cost_item" &&
              operation.operation !== "ADD" &&
              operation.target_id &&
              !latest.items.some((item) => item.item_key === operation.target_id),
          );
          if (missingTarget) return { status: "unsafe" };
          return {
            status: "safe",
            state: {
              ...pending,
              version: latest.version,
              categories: costPlanCategories(latest),
              narrative: {
                ...latest.narrative,
                ...pending.narrative,
                item_variations: {
                  ...latest.narrative?.item_variations,
                  ...pending.narrative?.item_variations,
                },
              },
            },
          };
        },
        onUnresolvedConflict: ({ pending }) => {
          unresolvedConflict = true;
          setState(pending);
          setError(
            "Cost Plan changed elsewhere. Your edit was kept locally — resolve before saving again.",
          );
        },
      });
      measureLocalMutation("cost-plan", startedAt);
      void queryClient
        .invalidateQueries({ queryKey: workbenchKeys.invoiceLedger(projectId) })
        .then(() =>
          queryClient.fetchQuery({
            queryKey: workbenchKeys.invoiceLedger(projectId),
            queryFn: () => api.getInvoiceLedger(projectId),
          }),
        )
        .then(setLedger, () => undefined);
    } catch (mutationError) {
      if (!(mutationError instanceof ApiError && mutationError.status === 409) || !unresolvedConflict) {
        const deletionMessage =
          mutationError instanceof ApiError
            ? formatCostPlanDeletionError(mutationError.body)
            : null;
        setError(
          deletionMessage ??
            (mutationError instanceof ApiError
              ? mutationError.message
              : "Cost Plan change could not be saved."),
        );
      }
    } finally {
      setSaving(false);
    }
  }

  if (!state) {
    return (
      <div className="artifact-workbook cost-plan-surface flex min-h-32 items-center justify-center border text-sm text-muted-foreground">
        {error ?? "Loading Cost Plan…"}
      </div>
    );
  }

  const categories = costPlanCategories(state);

  return (
    <section
      className="artifact-workbook cost-plan-surface w-full min-w-0 border"
      aria-label="Canonical Cost Plan"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Cost plan sections">
          {(
            [
              ["cost-plan", `Cost Plan v${state.version}`],
              ["invoices", "Invoices"],
              ["variations", "Variations"],
            ] as const
          ).map(([id, label]) => (
            <Button
              key={id}
              size="sm"
              variant={tab === id ? "default" : "ghost"}
              role="tab"
              aria-selected={tab === id}
              onClick={() => selectTab(id)}
            >
              {label}
            </Button>
          ))}
        </div>
        {tab === "cost-plan" ? (
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="month"
              className="cost-plan-field h-8 w-36"
              value={selectedMonth}
              aria-label="Selected billing month"
              onChange={(event) => {
                if (event.target.value) setSelectedMonth(event.target.value);
              }}
            />
            <Button size="sm" variant="outline" onClick={() => setAddingCategory(true)}>
              <Plus aria-hidden /> Add category
            </Button>
          </div>
        ) : null}
      </div>

      <CostPlanTabPane id="invoices" active={tab === "invoices"}>
        <CostInvoiceRegister
          projectId={projectId}
          revision={state.version}
          reviewInvoiceId={reviewInvoiceId}
          ledger={ledger}
          onLedgerChange={setLedger}
        />
      </CostPlanTabPane>
      <CostPlanTabPane id="variations" active={tab === "variations"}>
        <div className="px-3 py-8 text-sm text-muted-foreground">
          Variation schedule coming soon. Forecast and approved variation amounts can be
          edited on each Cost Plan line until then.
        </div>
      </CostPlanTabPane>

      <CostPlanTabPane id="cost-plan" active={tab === "cost-plan"}>
          {addingCategory ? (
            <form
              className="flex flex-wrap items-end gap-2 border-b p-3"
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                const category = String(data.get("category") ?? "").trim();
                if (!category) return;
                setAddingCategory(false);
                void mutate(
                  {
                    operation: "ADD",
                    target_type: "cost_category",
                    values: { category },
                  },
                  {
                    ...state,
                    categories: Array.from(new Set([...categories, category])),
                    narrative: {
                      ...state.narrative,
                      categories: Array.from(new Set([...categories, category])),
                    },
                  },
                );
              }}
            >
              <div className="min-w-48 flex-1">
                <label className="mb-1 block text-xs text-muted-foreground" htmlFor="new-category">
                  New category
                </label>
                <Input id="new-category" name="category" required className="cost-plan-field" />
              </div>
              <Button type="button" size="sm" variant="outline" onClick={() => setAddingCategory(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm">
                Save category
              </Button>
            </form>
          ) : null}
          {error ? <p className="border-b p-3 text-xs text-destructive">{error}</p> : null}
          <datalist id="cost-plan-categories">
            {categories.map((category) => (
              <option key={category} value={category} />
            ))}
          </datalist>
          <CostPlanItemsTable
            state={state}
            saving={saving}
            sort={sort}
            selectedMonth={selectedMonth}
            ledger={ledger}
            selectedKeys={selectedKeys}
            selectionAnchor={selectionAnchor}
            scrollRef={scrollRef}
            active={active && tab === "cost-plan"}
            onSortChange={setSort}
            onSelectionChange={setSelectedKeys}
            onSelectionAnchorChange={setSelectionAnchor}
            onBulkDelete={() => {
              const keys = [...selectedKeys];
              if (!keys.length) return;
              const confirmed = window.confirm(
                `Delete ${keys.length} selected ${keys.length === 1 ? "item" : "items"}?`,
              );
              if (!confirmed) return;
              void mutate(
                keys.map((target_id) => ({
                  operation: "DELETE" as const,
                  target_type: "cost_item" as const,
                  target_id,
                })),
                withOptimisticTotals({
                  ...state,
                  items: renumberCostPlanItems(
                    state.items.filter((item) => !selectedKeys.has(item.item_key)),
                  ),
                }),
              );
              setSelectedKeys(new Set());
              setSelectionAnchor(null);
            }}
            onMutate={mutate}
          />
          {saving ? (
            <p className="flex items-center gap-1 border-t px-3 py-2 text-xs text-muted-foreground">
              <Loader2 className="size-3 animate-spin" aria-hidden /> Saving in background
            </p>
          ) : null}
      </CostPlanTabPane>
    </section>
  );
}

function replaceItem(state: CostPlanState, item: CostPlanItem): CostPlanState {
  return {
    ...state,
    items: state.items.map((current) =>
      current.item_key === item.item_key ? item : current,
    ),
  };
}

function CostPlanItemsTable({
  state,
  saving,
  sort,
  selectedMonth,
  ledger,
  selectedKeys,
  selectionAnchor,
  scrollRef,
  active,
  onSortChange,
  onSelectionChange,
  onSelectionAnchorChange,
  onBulkDelete,
  onMutate,
}: {
  state: CostPlanState;
  saving: boolean;
  sort: CostPlanSort | null;
  selectedMonth: string;
  ledger: InvoiceLedger | null;
  selectedKeys: Set<string>;
  selectionAnchor: string | null;
  scrollRef: RefObject<HTMLDivElement | null>;
  active: boolean;
  onSortChange: (sort: CostPlanSort | null) => void;
  onSelectionChange: (keys: Set<string>) => void;
  onSelectionAnchorChange: (key: string | null) => void;
  onBulkDelete: () => void;
  onMutate: (
    operations: CostPlanOperation | CostPlanOperation[],
    optimistic: CostPlanState,
  ) => Promise<void>;
}) {
  const claimedByItem = useMemo(
    () => claimedAmountsByItem(ledger?.rows ?? [], selectedMonth),
    [ledger, selectedMonth],
  );
  const viewRows = useMemo(
    () => buildCostPlanViewRows(state, { sort, claimedByItem }),
    [state, sort, claimedByItem],
  );
  const selectableKeys = useMemo(
    () =>
      viewRows
        .filter((row): row is Extract<CostPlanViewRow, { kind: "item" }> => row.kind === "item")
        .map((row) => row.item.item_key),
    [viewRows],
  );
  const virtualize = viewRows.length >= COST_PLAN_VIRTUALIZE_THRESHOLD;
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual returns unmemoizable functions by design.
  const virtualizer = useVirtualizer({
    count: viewRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => COST_PLAN_ROW_PX,
    overscan: 8,
    enabled: virtualize && active,
  });
  useEffect(() => {
    if (!active) return;
    virtualizer.measure?.();
  }, [active, virtualizer]);
  const rows = virtualize
    ? virtualizer.getVirtualItems().map((virtualRow) => ({
        row: viewRows[virtualRow.index]!,
        index: virtualRow.index,
      }))
    : viewRows.map((row, index) => ({ row, index }));
  const paddingTop = virtualize ? (virtualizer.getVirtualItems()[0]?.start ?? 0) : 0;
  const paddingBottom = virtualize
    ? Math.max(
        0,
        virtualizer.getTotalSize() -
          (virtualizer.getVirtualItems().at(-1)?.end ?? 0),
      )
    : 0;

  function handleRowClick(
    event: ReactMouseEvent<HTMLTableRowElement>,
    itemKey: string,
  ) {
    const target = event.target as HTMLElement;
    if (target.closest("input, button, a, [role='menuitem'], [data-radix-collection-item]")) {
      return;
    }
    const additive = event.ctrlKey || event.metaKey;
    if (event.shiftKey) {
      const anchor =
        selectionAnchor && selectableKeys.includes(selectionAnchor)
          ? selectionAnchor
          : itemKey;
      const anchorIndex = selectableKeys.indexOf(anchor);
      const rowIndex = selectableKeys.indexOf(itemKey);
      if (anchorIndex >= 0 && rowIndex >= 0) {
        const start = Math.min(anchorIndex, rowIndex);
        const end = Math.max(anchorIndex, rowIndex);
        const range = selectableKeys.slice(start, end + 1);
        const next = additive ? new Set(selectedKeys) : new Set<string>();
        for (const key of range) next.add(key);
        onSelectionChange(next);
        return;
      }
    }
    if (additive) {
      const next = new Set(selectedKeys);
      if (next.has(itemKey)) next.delete(itemKey);
      else next.add(itemKey);
      onSelectionChange(next);
    } else {
      onSelectionChange(new Set([itemKey]));
    }
    onSelectionAnchorChange(itemKey);
  }

  return (
    <div ref={scrollRef} className="w-full min-w-0 overflow-x-auto">
      <table className="cost-plan-grid-table">
        <colgroup>
          <col className="cost-plan-col-code" />
          <col className="cost-plan-col-category" />
          <col className="cost-plan-col-item" />
          {Array.from({ length: 9 }, (_, index) => (
            <col key={`money-${index}`} className="cost-plan-col-money" />
          ))}
          <col className="cost-plan-col-actions" />
        </colgroup>
        <thead className="sticky top-0 z-10">
          <tr>
            <SortableHeader
              label="Code"
              sortKey="cost_code"
              sort={sort}
              onSortChange={onSortChange}
              className="cost-plan-grid-cell--code whitespace-nowrap"
            />
            <SortableHeader
              label="Category"
              sortKey="category"
              sort={sort}
              onSortChange={onSortChange}
            />
            <SortableHeader
              label="Item"
              sortKey="item"
              sort={sort}
              onSortChange={onSortChange}
            />
            <th className="text-right">Budget</th>
            <th className="text-right">Approved Contract</th>
            <th className="text-right">Forecast Variations</th>
            <th className="text-right">Approved Variations</th>
            <th className="text-right">Forecast Final Cost</th>
            <th className="text-right">Budget Variance</th>
            <th className="text-right">Claimed to Date</th>
            <th className="text-right">This Month</th>
            <th className="text-right">Remaining</th>
            <th className="text-right">
              {selectedKeys.size > 0 ? (
                <button
                  type="button"
                  className="cost-plan-grid-action cost-plan-grid-action--danger cost-plan-grid-action--visible ml-auto"
                  aria-label={`Delete ${selectedKeys.size} selected items`}
                  title={`Delete ${selectedKeys.size} selected`}
                  disabled={saving}
                  onClick={(event) => {
                    event.stopPropagation();
                    onBulkDelete();
                  }}
                >
                  <Trash className="size-3.5" aria-hidden />
                </button>
              ) : (
                <span className="sr-only">Actions</span>
              )}
            </th>
          </tr>
        </thead>
        <tbody>
          {paddingTop > 0 ? (
            <tr aria-hidden>
              <td
                colSpan={TABLE_COL_COUNT}
                style={{ height: paddingTop, padding: 0, border: 0 }}
              />
            </tr>
          ) : null}
          {rows.map(({ row }) =>
            row.kind === "item" ? (
              <ItemRow
                key={row.key}
                row={row}
                state={state}
                saving={saving}
                selected={selectedKeys.has(row.item.item_key)}
                onRowClick={handleRowClick}
                onMutate={onMutate}
                onDeleted={(key) => {
                  onSelectionChange(
                    new Set([...selectedKeys].filter((value) => value !== key)),
                  );
                  if (selectionAnchor === key) onSelectionAnchorChange(null);
                }}
              />
            ) : (
              <SummaryRow key={row.key} row={row} />
            ),
          )}
          {paddingBottom > 0 ? (
            <tr aria-hidden>
              <td
                colSpan={TABLE_COL_COUNT}
                style={{ height: paddingBottom, padding: 0, border: 0 }}
              />
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  sort,
  onSortChange,
  className,
}: {
  label: string;
  sortKey: CostPlanSortKey;
  sort: CostPlanSort | null;
  onSortChange: (sort: CostPlanSort | null) => void;
  className?: string;
}) {
  const active = sort?.key === sortKey;
  const ariaSort = !active
    ? "none"
    : sort.direction === "asc"
      ? "ascending"
      : "descending";
  return (
    <th className={className} aria-sort={ariaSort}>
      <button
        type="button"
        className="inline-flex max-w-full items-center gap-0.5 text-left font-medium hover:underline"
        onClick={() => onSortChange(nextCostPlanSort(sort, sortKey))}
      >
        {label}
        <ArrowUpDown
          className={cn("size-3 shrink-0", active ? "text-foreground" : "text-muted-foreground")}
          aria-hidden
        />
        <span className="sr-only">
          {active ? `sorted ${sort.direction}` : "not sorted"}
        </span>
      </button>
    </th>
  );
}

function SummaryRow({ row }: { row: Extract<CostPlanViewRow, { kind: "subtotal" | "grandtotal" }> }) {
  const label =
    row.kind === "grandtotal" ? "Grand total" : `${row.category} subtotal`;
  return (
    <tr>
      {/* Keep Code blank so the label lines up under Category. */}
      <td className="cost-plan-grid-cell--summary" />
      <td className="cost-plan-grid-cell--summary" colSpan={2}>
        {label}
      </td>
      <MoneyCell value={row.rollup.budget} summary />
      <MoneyCell value={row.rollup.approvedContract} summary />
      <MoneyCell value={row.rollup.forecastVariations} summary />
      <MoneyCell value={row.rollup.approvedVariations} summary />
      <MoneyCell value={row.rollup.forecastFinalCost} summary />
      <MoneyCell value={row.rollup.budgetVariance} summary />
      <MoneyCell value={row.rollup.claimedToDate} summary />
      <MoneyCell value={row.rollup.thisMonth} summary />
      <MoneyCell value={row.rollup.remaining} summary />
      <td className="cost-plan-grid-cell--summary" />
    </tr>
  );
}

function MoneyCell({ value, summary = false }: { value: number; summary?: boolean }) {
  return (
    <td
      className={cn(
        "cost-plan-grid-cell--money cost-plan-grid-cell--readonly",
        summary && "cost-plan-grid-cell--summary",
      )}
    >
      {formatCostPlanMoney(value)}
    </td>
  );
}

function MoneyInput({
  value,
  ariaLabel,
  onCommit,
}: {
  value: string;
  ariaLabel: string;
  onCommit: (next: string) => void;
}) {
  const display = formatCostPlanMoney(amount(value));
  return (
    <input
      key={value}
      className="cost-plan-grid-input cost-plan-grid-input--money"
      defaultValue={display}
      aria-label={ariaLabel}
      onClick={(event) => event.stopPropagation()}
      onBlur={(event) => {
        const parsed = parseCostPlanMoneyInput(event.target.value);
        if (parsed === null) {
          event.target.value = display;
          return;
        }
        if (amount(parsed) === amount(value)) {
          event.target.value = display;
          return;
        }
        onCommit(parsed);
      }}
    />
  );
}

function ItemRow({
  row,
  state,
  saving,
  selected,
  onRowClick,
  onMutate,
  onDeleted,
}: {
  row: Extract<CostPlanViewRow, { kind: "item" }>;
  state: CostPlanState;
  saving: boolean;
  selected: boolean;
  onRowClick: (event: ReactMouseEvent<HTMLTableRowElement>, itemKey: string) => void;
  onMutate: (
    operations: CostPlanOperation | CostPlanOperation[],
    optimistic: CostPlanState,
  ) => Promise<void>;
  onDeleted: (itemKey: string) => void;
}) {
  const { item, rollup, manualIndex } = row;
  const variations = itemVariations(state, item.item_key);
  const code = String(manualIndex + 1);

  function updateItem(values: Record<string, unknown>, optimisticItem: CostPlanItem) {
    void onMutate(
      {
        operation: "UPDATE",
        target_type: "cost_item",
        target_id: item.item_key,
        values,
      },
      withOptimisticTotals(replaceItem(state, optimisticItem)),
    );
  }

  function updateVariations(next: {
    forecast_variations?: string;
    approved_variations?: string;
  }) {
    const merged = {
      forecast_variations: next.forecast_variations ?? variations.forecast_variations,
      approved_variations: next.approved_variations ?? variations.approved_variations,
    };
    const forecast = forecastFromContractAndVariations(item.committed, merged);
    void onMutate(
      {
        operation: "UPDATE",
        target_type: "cost_item",
        target_id: item.item_key,
        values: {
          forecast,
          forecast_variations: merged.forecast_variations,
          approved_variations: merged.approved_variations,
        },
      },
      withOptimisticTotals(
        withItemVariations(replaceItem(state, { ...item, forecast }), item.item_key, merged),
      ),
    );
  }

  function deleteItem() {
    const confirmed = window.confirm(`Delete "${item.item}"?`);
    if (!confirmed) return;
    void onMutate(
      {
        operation: "DELETE",
        target_type: "cost_item",
        target_id: item.item_key,
      },
      withOptimisticTotals({
        ...state,
        items: renumberCostPlanItems(
          state.items.filter((candidate) => candidate.item_key !== item.item_key),
        ),
      }),
    );
    onDeleted(item.item_key);
  }

  return (
    <tr
      className={cn("select-none", selected && "cost-plan-grid-row--selected")}
      onClick={(event) => onRowClick(event, item.item_key)}
    >
      <td className="cost-plan-grid-cell cost-plan-grid-cell--code cost-plan-grid-cell--readonly">
        {code}
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <input
          className="cost-plan-grid-input"
          defaultValue={item.category}
          list="cost-plan-categories"
          aria-label={`${item.item} category`}
          onClick={(event) => event.stopPropagation()}
          onBlur={(event) => {
            const category = event.target.value.trim();
            if (!category || category === item.category) return;
            updateItem({ category }, { ...item, category });
          }}
        />
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <input
          className="cost-plan-grid-input"
          defaultValue={item.item}
          aria-label={`${item.item} name`}
          onClick={(event) => event.stopPropagation()}
          onBlur={(event) => {
            const label = event.target.value.trim();
            if (!label || label === item.item) return;
            updateItem({ item: label }, { ...item, item: label });
          }}
        />
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <MoneyInput
          value={item.budget ?? ""}
          ariaLabel={`${item.item} budget`}
          onCommit={(budget) => updateItem({ budget }, { ...item, budget })}
        />
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <MoneyInput
          value={item.committed}
          ariaLabel={`${item.item} approved contract`}
          onCommit={(committed) => {
            const forecast = forecastFromContractAndVariations(committed, variations);
            updateItem({ committed, forecast }, { ...item, committed, forecast });
          }}
        />
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <MoneyInput
          value={variations.forecast_variations}
          ariaLabel={`${item.item} forecast variations`}
          onCommit={(forecast_variations) => updateVariations({ forecast_variations })}
        />
      </td>
      <td className="cost-plan-grid-cell cost-plan-grid-cell--editable">
        <MoneyInput
          value={variations.approved_variations}
          ariaLabel={`${item.item} approved variations`}
          onCommit={(approved_variations) => updateVariations({ approved_variations })}
        />
      </td>
      <MoneyCell value={rollup.forecastFinalCost} />
      <MoneyCell value={rollup.budgetVariance} />
      <MoneyCell value={rollup.claimedToDate} />
      <MoneyCell value={rollup.thisMonth} />
      <MoneyCell value={rollup.remaining} />
      <td className="cost-plan-grid-cell">
        <div className="cost-plan-grid-actions">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="cost-plan-grid-action"
                aria-label={`More actions for ${item.item}`}
                disabled={saving}
                onClick={(event) => event.stopPropagation()}
              >
                <MoreHorizontal className="size-3.5" aria-hidden />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="min-w-0 w-auto"
              onClick={(event) => event.stopPropagation()}
            >
              <DropdownMenuItem
                disabled={saving}
                aria-label="Copy"
                title="Copy"
                className="justify-center px-2 py-2"
                onSelect={() => {
                  const values = {
                    item_key: `${item.item_key}-copy`,
                    cost_code: `${Date.now()}`,
                  };
                  const duplicated = duplicateCostItemOptimistically(
                    state,
                    item.item_key,
                    values,
                  );
                  void onMutate(
                    {
                      operation: "DUPLICATE",
                      target_type: "cost_item",
                      target_id: item.item_key,
                      values,
                    },
                    withOptimisticTotals({
                      ...duplicated,
                      items: renumberCostPlanItems(duplicated.items),
                    }),
                  );
                }}
              >
                <Copy className="size-3.5" aria-hidden />
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={saving}
                aria-label="Add row below"
                title="Add row below"
                className="justify-center px-2 py-2"
                onSelect={() => {
                  const stamp = Date.now();
                  const newItem: CostPlanItem = {
                    item_key: `item-${stamp}`,
                    cost_code: String(stamp),
                    category: item.category,
                    item: "New item",
                    display_order: item.display_order + 1,
                    budget: "0",
                    committed: "0",
                    forecast: "0",
                    paid: "0",
                    allowance_type: "none",
                    basis: "User-added allowance",
                    source_refs: [{ kind: "user" }],
                    status: "manual",
                    locked: false,
                  };
                  const added = addCostItemOptimistically(
                    state,
                    newItem,
                    item.item_key,
                    "after",
                  );
                  void onMutate(
                    [
                      {
                        operation: "ADD",
                        target_type: "cost_item",
                        values: newItem,
                      },
                      {
                        operation: "MOVE",
                        target_type: "cost_item",
                        target_id: newItem.item_key,
                        reference_id: item.item_key,
                        placement: "after",
                      },
                    ],
                    withOptimisticTotals({
                      ...added,
                      items: renumberCostPlanItems(added.items),
                    }),
                  );
                }}
              >
                <Plus className="size-3.5" aria-hidden />
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <button
            type="button"
            className="cost-plan-grid-action cost-plan-grid-action--danger"
            aria-label={`Delete ${item.item}`}
            disabled={saving}
            onClick={(event) => {
              event.stopPropagation();
              deleteItem();
            }}
          >
            <Trash className="size-3.5" aria-hidden />
          </button>
        </div>
      </td>
    </tr>
  );
}
