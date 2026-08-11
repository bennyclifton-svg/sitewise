import { describe, expect, it } from "vitest";

import {
  applyCostPlanDelta,
  buildCostPlanViewRows,
  calculateCostPlanTotals,
  claimedAmountsByItem,
  costPlanCategories,
  DEFAULT_COST_PLAN_CATEGORIES,
  duplicateCostItemOptimistically,
  formatCostPlanMoney,
  lineRollup,
  moveCostItemOptimistically,
  renumberCostPlanItems,
  type CostPlanItem,
  type CostPlanState,
  withItemVariations,
  withOptimisticTotals,
} from "@/lib/cost-plan";

function item(
  key: string,
  overrides: Partial<CostPlanItem> = {},
): CostPlanItem {
  return {
    item_key: key,
    cost_code: key.toUpperCase(),
    category: "Construction",
    item: key,
    display_order: 1,
    budget: "100",
    committed: "0",
    forecast: "100",
    paid: "0",
    allowance_type: "none",
    basis: "Manual",
    source_refs: [],
    status: "manual",
    locked: false,
    ...overrides,
  };
}

function state(items: CostPlanItem[]): CostPlanState {
  return {
    version: 1,
    items,
    totals: calculateCostPlanTotals(items),
    categories: ["Construction", "Consultants"],
  };
}

describe("cost-plan optimistic helpers", () => {
  it("recalculates totals from local rows without waiting for XLSX", () => {
    const totals = calculateCostPlanTotals([
      item("a", { budget: "150", forecast: "150" }),
      item("b", { budget: "50", forecast: "50" }),
    ]);
    expect(totals.budget).toBe("200.00");
    expect(totals.total_excluding_gst).toBe("200.00");
    expect(totals.total_including_gst).toBe("220.00");
  });

  it("duplicates a row optimistically with refreshed order and totals", () => {
    const next = duplicateCostItemOptimistically(
      state([item("joinery", { display_order: 1 }), item("ffe", { display_order: 2 })]),
      "joinery",
      { item_key: "joinery-copy", cost_code: "JOINERY-COPY" },
    );
    expect(next.items.map((row) => row.item_key)).toEqual([
      "joinery",
      "joinery-copy",
      "ffe",
    ]);
    expect(next.items.map((row) => row.display_order)).toEqual([1, 2, 3]);
    expect(next.totals.budget).toBe("300.00");
  });

  it("moves a row before/after a reference and reorders locally", () => {
    const base = state([
      item("a", { display_order: 1 }),
      item("b", { display_order: 2 }),
      item("c", { display_order: 3 }),
    ]);
    const moved = moveCostItemOptimistically(base, "c", "a", "before");
    expect(moved.items.map((row) => row.item_key)).toEqual(["c", "a", "b"]);
    expect(moved.items.map((row) => row.display_order)).toEqual([1, 2, 3]);
  });

  it("tracks categories and keeps totals helpers stable", () => {
    const current = withOptimisticTotals({
      ...state([item("a")]),
      categories: ["Construction"],
    });
    expect(costPlanCategories(current)).toEqual(["Construction"]);
    expect(costPlanCategories({ ...current, items: [], categories: [] })).toEqual([
      ...DEFAULT_COST_PLAN_CATEGORIES,
    ]);
    const deltaApplied = applyCostPlanDelta(current, {
      version: 2,
      changed_items: [item("b", { display_order: 2, budget: "25", forecast: "25" })],
      deleted_item_keys: [],
      totals: calculateCostPlanTotals([item("a"), item("b", { budget: "25", forecast: "25" })]),
      workbook_status: "pending",
    });
    expect(deltaApplied.version).toBe(2);
    expect(deltaApplied.items).toHaveLength(2);
  });

  it("builds category subtotals and workbook-style rollups", () => {
    const current = withItemVariations(
      state([
        item("fee", {
          category: "Fees and Charges",
          display_order: 1,
          budget: "40",
          committed: "30",
        }),
        item("build", {
          category: "Construction",
          display_order: 2,
          budget: "100",
          committed: "80",
        }),
      ]),
      "build",
      { forecast_variations: "10", approved_variations: "5" },
    );
    const claimed = claimedAmountsByItem(
      [
        {
          cost_item_key: "build",
          cost_item_label: "build",
          amount_ex_gst: "20",
          billing_month: "2026-08-01",
        },
      ],
      "2026-08",
    );
    const rollup = lineRollup(
      current.items[1]!,
      { forecast_variations: "10", approved_variations: "5" },
      claimed.get("build"),
    );
    expect(rollup.forecastFinalCost).toBe(95);
    expect(rollup.budgetVariance).toBe(5);
    expect(rollup.claimedToDate).toBe(20);
    expect(rollup.thisMonth).toBe(20);
    expect(rollup.remaining).toBe(80);

    const rows = buildCostPlanViewRows(current, {
      sort: null,
      claimedByItem: claimed,
    });
    expect(rows.map((row) => row.kind)).toEqual([
      "item",
      "subtotal",
      "item",
      "subtotal",
      "grandtotal",
    ]);
    expect(rows[1]).toMatchObject({ kind: "subtotal", category: "Fees and Charges" });
    expect(rows[3]).toMatchObject({ kind: "subtotal", category: "Construction" });
  });

  it("formats money with Australian thousands separators and no dollar sign", () => {
    expect(formatCostPlanMoney(30000)).toBe("30,000.00");
    expect(formatCostPlanMoney(100)).toBe("100.00");
  });

  it("renumbers cost codes sequentially from display order", () => {
    const renumbered = renumberCostPlanItems([
      item("b", { display_order: 2, cost_code: "C-02" }),
      item("a", { display_order: 1, cost_code: "C-01" }),
    ]);
    expect(renumbered.map((row) => row.cost_code)).toEqual(["1", "2"]);
    expect(renumbered.map((row) => row.item_key)).toEqual(["a", "b"]);
  });
});
