export { COST_PLAN_VIRTUALIZE_THRESHOLD } from "@/lib/interaction-budgets";

export type CostPlanItem = {
  item_key: string;
  cost_code: string;
  category: string;
  item: string;
  display_order: number;
  budget: string | null;
  committed: string;
  forecast: string;
  paid: string;
  allowance_type: "none" | "pc" | "ps" | "contingency";
  basis: string;
  source_refs: Array<Record<string, unknown>>;
  status: "proposed" | "confirmed" | "manual";
  locked: boolean;
};

export type CostPlanTotals = {
  budget: string;
  committed: string;
  forecast: string;
  paid: string;
  variance: string;
  total_excluding_gst: string;
  total_including_gst: string;
};

export type CostPlanItemVariations = {
  forecast_variations: string;
  approved_variations: string;
};

export type CostPlanState = {
  version: number;
  items: CostPlanItem[];
  totals: CostPlanTotals;
  categories?: string[];
  contingency_percent?: string;
  escalation_percent?: string;
  gst_treatment?: "exclusive" | "inclusive" | "not_applicable";
  narrative?: {
    categories?: string[];
    item_variations?: Record<string, Partial<CostPlanItemVariations>>;
  };
};

export type CostPlanOperation = {
  operation: "ADD" | "UPDATE" | "DELETE" | "MOVE" | "DUPLICATE";
  target_type: "cost_item" | "cost_category";
  target_id?: string;
  values?: Record<string, unknown>;
  reference_id?: string;
  placement?: "before" | "after";
};

export type CostPlanDelta = {
  version: number;
  changed_items: CostPlanItem[];
  deleted_item_keys: string[];
  totals: CostPlanTotals;
  workbook_status: "pending" | "ready";
};

export type CostPlanDeletionBlocker = {
  kind: "invoice" | "commitment" | "variation" | "forecast" | "procurement";
  id: string | null;
  label: string;
  reference_id?: string | null;
};

export type CostPlanSortKey = "cost_code" | "item" | "category";
export type CostPlanSortDirection = "asc" | "desc";

export type CostPlanSort = {
  key: CostPlanSortKey;
  direction: CostPlanSortDirection;
};

export type CostPlanLineRollup = {
  budget: number;
  approvedContract: number;
  forecastVariations: number;
  approvedVariations: number;
  forecastFinalCost: number;
  budgetVariance: number;
  claimedToDate: number;
  thisMonth: number;
  remaining: number;
};

export type CostPlanClaimedAmounts = {
  claimedToDate: number;
  thisMonth: number;
};

export type InvoiceClaimSource = {
  cost_item_key: string | null;
  cost_item_label: string;
  amount_ex_gst: string;
  billing_month: string;
};

/** Canonical default category order for the Cost Plan grid. */
export const DEFAULT_COST_PLAN_CATEGORIES = [
  "Fees and Charges",
  "Consultants",
  "Construction",
  "Contingency",
] as const;

const CATEGORY_CANONICAL = new Map<string, string>([
  ["fees and charges", "Fees and Charges"],
  ["fees and charge", "Fees and Charges"],
  ["consultants", "Consultants"],
  ["construction", "Construction"],
  ["contingency", "Contingency"],
  ["contingency / allowances", "Contingency"],
  ["contingency/allowances", "Contingency"],
]);

function money(value: number): string {
  return value.toFixed(2);
}

export function amount(value: string | null | undefined): number {
  if (value == null || value === "") return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatCostPlanMoney(value: number): string {
  return value.toLocaleString("en-AU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Assign sequential cost codes 1..N from current display order. */
export function renumberCostPlanItems(items: CostPlanItem[]): CostPlanItem[] {
  return [...items]
    .sort((left, right) => left.display_order - right.display_order)
    .map((item, index) => ({
      ...item,
      display_order: index + 1,
      cost_code: String(index + 1),
    }));
}

export function currentBillingMonthValue(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

export function billingMonthStart(monthValue: string): string {
  const trimmed = monthValue.trim();
  if (/^\d{4}-\d{2}$/.test(trimmed)) return `${trimmed}-01`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return `${trimmed.slice(0, 7)}-01`;
  return `${currentBillingMonthValue()}-01`;
}

export function canonicalCostPlanCategory(category: string): string {
  const trimmed = category.trim();
  if (!trimmed) return trimmed;
  return CATEGORY_CANONICAL.get(trimmed.toLowerCase()) ?? trimmed;
}

export function categorySortIndex(category: string): number {
  const canonical = canonicalCostPlanCategory(category);
  const index = DEFAULT_COST_PLAN_CATEGORIES.findIndex(
    (value) => value.toLowerCase() === canonical.toLowerCase(),
  );
  return index >= 0 ? index : DEFAULT_COST_PLAN_CATEGORIES.length;
}

export function calculateCostPlanTotals(
  items: CostPlanItem[],
  options: {
    contingencyPercent?: number;
    escalationPercent?: number;
    gstTreatment?: CostPlanState["gst_treatment"];
  } = {},
): CostPlanTotals {
  const contingencyPercent = options.contingencyPercent ?? 0;
  const escalationPercent = options.escalationPercent ?? 0;
  const gstTreatment = options.gstTreatment ?? "exclusive";
  const budget = items.reduce((sum, item) => sum + amount(item.budget), 0);
  const committed = items.reduce((sum, item) => sum + amount(item.committed), 0);
  const forecast = items.reduce((sum, item) => sum + amount(item.forecast), 0);
  const paid = items.reduce((sum, item) => sum + amount(item.paid), 0);
  const contingency = (budget * contingencyPercent) / 100;
  const escalation = ((budget + contingency) * escalationPercent) / 100;
  const subtotal = budget + contingency + escalation;
  let excluding = subtotal;
  let including = subtotal;
  if (gstTreatment === "exclusive") {
    including = subtotal * 1.1;
  } else if (gstTreatment === "inclusive") {
    excluding = subtotal / 1.1;
    including = subtotal;
  }
  return {
    budget: money(budget),
    committed: money(committed),
    forecast: money(forecast),
    paid: money(paid),
    variance: money(budget - forecast),
    total_excluding_gst: money(excluding),
    total_including_gst: money(including),
  };
}

export function costPlanCategories(state: CostPlanState): string[] {
  const fromState = (state.categories ?? state.narrative?.categories ?? [])
    .map((value) => value.trim())
    .filter(Boolean);
  const fromItems = state.items
    .map((item) => item.category.trim())
    .filter(Boolean);
  const present = [...fromState, ...fromItems];

  // Brand-new plans get the four default category chips; once categories exist
  // (or items define them), only show what is actually present.
  if (!present.length) {
    return [...DEFAULT_COST_PLAN_CATEGORIES];
  }

  const seen = new Set<string>();
  const ordered: string[] = [];

  for (const defaultCategory of DEFAULT_COST_PLAN_CATEGORIES) {
    const match = present.find(
      (value) =>
        canonicalCostPlanCategory(value).toLowerCase() ===
        defaultCategory.toLowerCase(),
    );
    if (!match) continue;
    const key = canonicalCostPlanCategory(match).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    ordered.push(match);
  }

  for (const value of present) {
    const key = canonicalCostPlanCategory(value).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    ordered.push(value);
  }

  return ordered;
}

export function itemVariations(
  state: CostPlanState,
  itemKey: string,
): CostPlanItemVariations {
  const entry = state.narrative?.item_variations?.[itemKey];
  return {
    forecast_variations: entry?.forecast_variations ?? "0",
    approved_variations: entry?.approved_variations ?? "0",
  };
}

export function withItemVariations(
  state: CostPlanState,
  itemKey: string,
  variations: Partial<CostPlanItemVariations>,
): CostPlanState {
  const current = itemVariations(state, itemKey);
  return {
    ...state,
    narrative: {
      ...state.narrative,
      categories: state.narrative?.categories ?? state.categories,
      item_variations: {
        ...state.narrative?.item_variations,
        [itemKey]: {
          forecast_variations:
            variations.forecast_variations ?? current.forecast_variations,
          approved_variations:
            variations.approved_variations ?? current.approved_variations,
        },
      },
    },
  };
}

export function lineRollup(
  item: CostPlanItem,
  variations: CostPlanItemVariations,
  claimed: CostPlanClaimedAmounts = { claimedToDate: 0, thisMonth: 0 },
): CostPlanLineRollup {
  const budget = amount(item.budget);
  const approvedContract = amount(item.committed);
  const forecastVariations = amount(variations.forecast_variations);
  const approvedVariations = amount(variations.approved_variations);
  const forecastFinalCost =
    approvedContract + forecastVariations + approvedVariations;
  return {
    budget,
    approvedContract,
    forecastVariations,
    approvedVariations,
    forecastFinalCost,
    budgetVariance: budget - forecastFinalCost,
    claimedToDate: claimed.claimedToDate,
    thisMonth: claimed.thisMonth,
    remaining: budget - claimed.claimedToDate,
  };
}

export function sumLineRollups(rows: CostPlanLineRollup[]): CostPlanLineRollup {
  return rows.reduce(
    (total, row) => ({
      budget: total.budget + row.budget,
      approvedContract: total.approvedContract + row.approvedContract,
      forecastVariations: total.forecastVariations + row.forecastVariations,
      approvedVariations: total.approvedVariations + row.approvedVariations,
      forecastFinalCost: total.forecastFinalCost + row.forecastFinalCost,
      budgetVariance: total.budgetVariance + row.budgetVariance,
      claimedToDate: total.claimedToDate + row.claimedToDate,
      thisMonth: total.thisMonth + row.thisMonth,
      remaining: total.remaining + row.remaining,
    }),
    {
      budget: 0,
      approvedContract: 0,
      forecastVariations: 0,
      approvedVariations: 0,
      forecastFinalCost: 0,
      budgetVariance: 0,
      claimedToDate: 0,
      thisMonth: 0,
      remaining: 0,
    },
  );
}

export function claimedAmountsByItem(
  rows: InvoiceClaimSource[],
  selectedMonth: string,
): Map<string, CostPlanClaimedAmounts> {
  const selected = billingMonthStart(selectedMonth);
  const byKey = new Map<string, CostPlanClaimedAmounts>();

  function bump(key: string, amountValue: number, month: string) {
    const current = byKey.get(key) ?? { claimedToDate: 0, thisMonth: 0 };
    if (month <= selected) current.claimedToDate += amountValue;
    if (month === selected) current.thisMonth += amountValue;
    byKey.set(key, current);
  }

  for (const row of rows) {
    const month = billingMonthStart(row.billing_month);
    const value = amount(row.amount_ex_gst);
    if (row.cost_item_key) bump(row.cost_item_key, value, month);
    const label = row.cost_item_label.trim().toLowerCase();
    if (label) bump(`label:${label}`, value, month);
  }
  return byKey;
}

export function claimedForItem(
  item: CostPlanItem,
  claimedByItem: Map<string, CostPlanClaimedAmounts>,
): CostPlanClaimedAmounts {
  const byKey = claimedByItem.get(item.item_key);
  if (byKey) return byKey;
  return (
    claimedByItem.get(`label:${item.item.trim().toLowerCase()}`) ?? {
      claimedToDate: 0,
      thisMonth: 0,
    }
  );
}

function compareText(left: string, right: string): number {
  return left.localeCompare(right, undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

export function sortCostPlanItems(
  items: CostPlanItem[],
  sort: CostPlanSort | null,
): CostPlanItem[] {
  if (!sort) {
    return [...items].sort((left, right) => left.display_order - right.display_order);
  }
  const direction = sort.direction === "asc" ? 1 : -1;
  return [...items].sort((left, right) => {
    let result = 0;
    if (sort.key === "cost_code") {
      result = compareText(left.cost_code, right.cost_code);
    } else if (sort.key === "item") {
      result = compareText(left.item, right.item);
    } else {
      result =
        categorySortIndex(left.category) - categorySortIndex(right.category) ||
        compareText(
          canonicalCostPlanCategory(left.category),
          canonicalCostPlanCategory(right.category),
        );
    }
    if (result !== 0) return result * direction;
    return left.display_order - right.display_order;
  });
}

export function nextCostPlanSort(
  current: CostPlanSort | null,
  key: CostPlanSortKey,
): CostPlanSort | null {
  if (!current || current.key !== key) return { key, direction: "asc" };
  if (current.direction === "asc") return { key, direction: "desc" };
  return null;
}

export type CostPlanViewRow =
  | {
      kind: "item";
      key: string;
      item: CostPlanItem;
      manualIndex: number;
      rollup: CostPlanLineRollup;
    }
  | {
      kind: "subtotal";
      key: string;
      category: string;
      rollup: CostPlanLineRollup;
    }
  | {
      kind: "grandtotal";
      key: string;
      rollup: CostPlanLineRollup;
    };

export function buildCostPlanViewRows(
  state: CostPlanState,
  options: {
    sort: CostPlanSort | null;
    claimedByItem: Map<string, CostPlanClaimedAmounts>;
  },
): CostPlanViewRow[] {
  const categories = costPlanCategories(state);
  const manualIndex = new Map(
    [...state.items]
      .sort((left, right) => left.display_order - right.display_order)
      .map((item, index) => [item.item_key, index]),
  );

  const grouped = new Map<string, CostPlanItem[]>();
  for (const category of categories) {
    grouped.set(canonicalCostPlanCategory(category).toLowerCase(), []);
  }
  for (const item of state.items) {
    const key = canonicalCostPlanCategory(item.category).toLowerCase();
    const bucket = grouped.get(key);
    if (bucket) bucket.push(item);
    else grouped.set(key, [item]);
  }

  let categoryOrder = categories;
  if (options.sort?.key === "category") {
    categoryOrder = [...categories].sort((left, right) => {
      const result = compareText(
        canonicalCostPlanCategory(left),
        canonicalCostPlanCategory(right),
      );
      return options.sort?.direction === "desc" ? -result : result;
    });
  }

  const rows: CostPlanViewRow[] = [];
  const grandTotals: CostPlanLineRollup[] = [];

  for (const category of categoryOrder) {
    const key = canonicalCostPlanCategory(category).toLowerCase();
    const items = grouped.get(key) ?? [];
    if (!items.length) continue;
    const withinCategorySort =
      options.sort && options.sort.key !== "category"
        ? options.sort
        : null;
    const orderedItems = sortCostPlanItems(items, withinCategorySort);
    const rollups: CostPlanLineRollup[] = [];
    for (const item of orderedItems) {
      const rollup = lineRollup(
        item,
        itemVariations(state, item.item_key),
        claimedForItem(item, options.claimedByItem),
      );
      rollups.push(rollup);
      rows.push({
        kind: "item",
        key: item.item_key,
        item,
        manualIndex: manualIndex.get(item.item_key) ?? 0,
        rollup,
      });
    }
    const subtotal = sumLineRollups(rollups);
    grandTotals.push(subtotal);
    rows.push({
      kind: "subtotal",
      key: `subtotal:${key}`,
      category,
      rollup: subtotal,
    });
  }

  rows.push({
    kind: "grandtotal",
    key: "grandtotal",
    rollup: sumLineRollups(grandTotals),
  });
  return rows;
}

function reorder(items: CostPlanItem[]): CostPlanItem[] {
  return items.map((item, index) => ({ ...item, display_order: index + 1 }));
}

export function withOptimisticTotals(state: CostPlanState): CostPlanState {
  return {
    ...state,
    totals: calculateCostPlanTotals(state.items, {
      contingencyPercent: amount(state.contingency_percent),
      escalationPercent: amount(state.escalation_percent),
      gstTreatment: state.gst_treatment,
    }),
  };
}

export function forecastFromContractAndVariations(
  committed: string,
  variations: CostPlanItemVariations,
): string {
  return money(
    amount(committed) +
      amount(variations.forecast_variations) +
      amount(variations.approved_variations),
  );
}

export function duplicateCostItemOptimistically(
  state: CostPlanState,
  targetId: string,
  values: { item_key: string; cost_code: string },
): CostPlanState {
  const index = state.items.findIndex((item) => item.item_key === targetId);
  if (index < 0) return state;
  const source = state.items[index];
  const duplicate: CostPlanItem = {
    ...source,
    item_key: values.item_key,
    cost_code: values.cost_code,
    status: "manual",
    locked: false,
  };
  const items = [...state.items];
  items.splice(index + 1, 0, duplicate);
  const withItems = withOptimisticTotals({
    ...state,
    items: reorder(items),
  });
  const sourceVariations = itemVariations(state, targetId);
  return withItemVariations(withItems, values.item_key, sourceVariations);
}

export function moveCostItemOptimistically(
  state: CostPlanState,
  targetId: string,
  referenceId: string,
  placement: "before" | "after",
): CostPlanState {
  const items = [...state.items];
  const from = items.findIndex((item) => item.item_key === targetId);
  if (from < 0) return state;
  const [moving] = items.splice(from, 1);
  const referenceIndex = items.findIndex((item) => item.item_key === referenceId);
  if (referenceIndex < 0) return state;
  const destination = referenceIndex + (placement === "after" ? 1 : 0);
  items.splice(destination, 0, moving);
  return withOptimisticTotals({
    ...state,
    items: reorder(items),
  });
}

export function applyCostPlanDelta(
  state: CostPlanState,
  delta: CostPlanDelta,
): CostPlanState {
  const changed = new Map(delta.changed_items.map((item) => [item.item_key, item]));
  const deleted = new Set(delta.deleted_item_keys);
  const items = state.items
    .filter((item) => !deleted.has(item.item_key))
    .map((item) => changed.get(item.item_key) ?? item);
  for (const item of changed.values()) {
    if (!items.some((existing) => existing.item_key === item.item_key)) items.push(item);
  }
  items.sort((left, right) => left.display_order - right.display_order);
  const itemVariationsMap = { ...state.narrative?.item_variations };
  for (const key of deleted) {
    delete itemVariationsMap[key];
  }
  return {
    ...state,
    version: delta.version,
    items,
    totals: delta.totals,
    narrative: {
      ...state.narrative,
      item_variations: itemVariationsMap,
    },
  };
}

export function formatCostPlanDeletionError(body: unknown): string | null {
  if (typeof body !== "object" || body === null || !("detail" in body)) return null;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail !== "object" || detail === null) return null;
  const structured = detail as {
    code?: unknown;
    message?: unknown;
    blockers?: unknown;
  };
  if (structured.code !== "cost_plan_deletion_blocked") return null;
  if (typeof structured.message === "string" && structured.message.trim()) {
    return structured.message;
  }
  const blockers = Array.isArray(structured.blockers)
    ? structured.blockers.filter(
        (blocker): blocker is CostPlanDeletionBlocker =>
          typeof blocker === "object" &&
          blocker !== null &&
          typeof (blocker as CostPlanDeletionBlocker).label === "string",
      )
    : [];
  if (!blockers.length) return null;
  return `Cannot delete cost item; referenced by ${blockers
    .map((blocker) => blocker.label)
    .join(", ")}`;
}
