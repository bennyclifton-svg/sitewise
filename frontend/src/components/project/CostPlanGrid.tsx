import { Copy, Loader2, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import {
  applyCostPlanDelta,
  type CostPlanItem,
  type CostPlanOperation,
  type CostPlanState,
} from "@/lib/cost-plan";
import { ApiError } from "@/lib/http";
import { runOptimisticMutation } from "@/lib/optimistic-mutation";
import { measureLocalMutation } from "@/lib/performance";

export function CostPlanGrid({ projectId }: { projectId: string }) {
  const [state, setState] = useState<CostPlanState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void api.getCostPlanState(projectId).then(
      (value) => {
        if (!cancelled) setState(value);
      },
      (loadError) => {
        if (!cancelled) {
          setError(loadError instanceof ApiError ? loadError.message : "Cost Plan could not load.");
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function mutate(operation: CostPlanOperation, optimistic: CostPlanState) {
    if (!state || saving) return;
    const snapshot = state;
    const startedAt = performance.now();
    setSaving(true);
    setError(null);
    try {
      await runOptimisticMutation({
        snapshot,
        optimistic,
        apply: setState,
        commit: () =>
          api.applyCostPlanOperations(projectId, snapshot.version, [operation]),
        confirmed: (delta) => applyCostPlanDelta(optimistic, delta),
        onConflict: () => api.getCostPlanState(projectId),
      });
      measureLocalMutation("cost-plan", startedAt);
    } catch (mutationError) {
      setError(
        mutationError instanceof ApiError
          ? mutationError.message
          : "Cost Plan change could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!state) {
    return (
      <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
        {error ?? "Loading Cost Plan…"}
      </div>
    );
  }

  return (
    <section className="border bg-background" aria-label="Canonical Cost Plan">
      <header className="flex items-center justify-between border-b px-3 py-2">
        <div>
          <p className="text-sm font-medium">Cost Plan</p>
          <p className="text-xs text-muted-foreground">Version {state.version}</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
          <Plus aria-hidden /> Add item
        </Button>
      </header>
      {adding ? (
        <AddCostItemForm
          onCancel={() => setAdding(false)}
          onAdd={(item) => {
            setAdding(false);
            void mutate(
              { operation: "ADD", target_type: "cost_item", values: item },
              { ...state, items: [...state.items, item] },
            );
          }}
        />
      ) : null}
      {error ? <p className="border-b p-3 text-xs text-destructive">{error}</p> : null}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[44rem] text-sm">
          <thead className="bg-muted/50 text-left">
            <tr>
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Item</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2 text-right">Budget</th>
              <th className="w-24 px-3 py-2"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {state.items.map((item) => (
              <tr key={item.item_key} className="border-t even:bg-muted/20">
                <td className="px-3 py-2 font-mono text-xs">{item.cost_code}</td>
                <td className="px-3 py-2">{item.item}</td>
                <td className="px-3 py-2 text-muted-foreground">{item.category}</td>
                <td className="px-3 py-1.5 text-right">
                  <Input
                    className="ml-auto h-8 w-32 text-right tabular-nums"
                    defaultValue={item.budget ?? ""}
                    aria-label={`${item.item} budget`}
                    onBlur={(event) => {
                      const budget = event.target.value.trim();
                      if (budget === (item.budget ?? "")) return;
                      const updated = { ...item, budget, forecast: budget };
                      void mutate(
                        {
                          operation: "UPDATE",
                          target_type: "cost_item",
                          target_id: item.item_key,
                          values: { budget, forecast: budget },
                        },
                        replaceItem(state, updated),
                      );
                    }}
                  />
                </td>
                <td className="px-3 py-1.5">
                  <div className="flex justify-end gap-1">
                    <Button
                      size="icon-xs"
                      variant="ghost"
                      aria-label={`Duplicate ${item.item}`}
                      onClick={() =>
                        void mutate(
                          {
                            operation: "DUPLICATE",
                            target_type: "cost_item",
                            target_id: item.item_key,
                            values: {
                              item_key: `${item.item_key}-copy`,
                              cost_code: `${item.cost_code}-COPY`,
                            },
                          },
                          state,
                        )
                      }
                    >
                      <Copy aria-hidden />
                    </Button>
                    <Button
                      size="icon-xs"
                      variant="ghost"
                      aria-label={`Delete ${item.item}`}
                      onClick={() =>
                        void mutate(
                          {
                            operation: "DELETE",
                            target_type: "cost_item",
                            target_id: item.item_key,
                          },
                          { ...state, items: state.items.filter((row) => row.item_key !== item.item_key) },
                        )
                      }
                    >
                      <Trash2 aria-hidden />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t font-medium">
            <tr>
              <td colSpan={3} className="px-3 py-2">Total excluding GST</td>
              <td className="px-3 py-2 text-right tabular-nums">
                ${Number(state.totals.total_excluding_gst).toLocaleString()}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
      {saving ? (
        <p className="flex items-center gap-1 border-t px-3 py-2 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" aria-hidden /> Saving in background
        </p>
      ) : null}
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

function AddCostItemForm({
  onAdd,
  onCancel,
}: {
  onAdd: (item: CostPlanItem) => void;
  onCancel: () => void;
}) {
  return (
    <form
      className="grid gap-2 border-b p-3 sm:grid-cols-4"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const label = String(data.get("item") ?? "").trim();
        const code = String(data.get("code") ?? "").trim();
        const category = String(data.get("category") ?? "").trim();
        const budget = String(data.get("budget") ?? "0").trim();
        if (!label || !code || !category) return;
        onAdd({
          item_key: `${code.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
          cost_code: code,
          category,
          item: label,
          display_order: 999999,
          budget,
          committed: "0",
          forecast: budget,
          paid: "0",
          allowance_type: "none",
          basis: "User-added allowance",
          source_refs: [{ kind: "user" }],
          status: "manual",
          locked: false,
        });
      }}
    >
      <Input name="code" placeholder="Code" required />
      <Input name="item" placeholder="Item" required />
      <Input name="category" placeholder="Category" required />
      <Input name="budget" inputMode="decimal" placeholder="Budget" required />
      <div className="flex gap-2 sm:col-span-4 sm:justify-end">
        <Button type="button" size="sm" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" size="sm">Add</Button>
      </div>
    </form>
  );
}
