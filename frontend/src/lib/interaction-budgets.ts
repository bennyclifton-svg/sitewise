/** Deterministic F9 interaction and payload guardrails for CI. */

export const COST_PLAN_VIRTUALIZE_THRESHOLD = 40;

/** Advisory local-mutation p95 budgets in milliseconds (CI asserts constants exist). */
export const INTERACTION_P95_MS = {
  paragraphEdit: 120,
  tableRowAddDelete: 150,
  costPlanAmountEdit: 120,
  costPlanItemAdd: 180,
  profileSave: 200,
} as const;

/** Delta payloads must stay under this fraction of a comparable full-state payload. */
export const BLOCK_DELTA_MAX_FRACTION_OF_FULL = 1 / 3;

export const PERFORMANCE_BENCHMARK_ENV = {
  suite: "unified-context-f9",
  repeats: 20,
  recordedAt: "2026-08-11",
} as const;
