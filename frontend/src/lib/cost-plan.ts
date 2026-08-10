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

export type CostPlanState = {
  version: number;
  items: CostPlanItem[];
  totals: CostPlanTotals;
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
  return { version: delta.version, items, totals: delta.totals };
}
