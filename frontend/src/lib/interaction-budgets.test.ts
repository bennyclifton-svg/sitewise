import { describe, expect, it } from "vitest";

import {
  BLOCK_DELTA_MAX_FRACTION_OF_FULL,
  COST_PLAN_VIRTUALIZE_THRESHOLD,
  INTERACTION_P95_MS,
  PERFORMANCE_BENCHMARK_ENV,
} from "@/lib/interaction-budgets";

describe("F9 interaction budgets", () => {
  it("keeps Cost Plan virtualization above small-list threshold", () => {
    expect(COST_PLAN_VIRTUALIZE_THRESHOLD).toBeGreaterThanOrEqual(40);
  });

  it("records positive p95 budgets and benchmark metadata for CI", () => {
    for (const [name, budget] of Object.entries(INTERACTION_P95_MS)) {
      expect(budget, name).toBeGreaterThan(0);
      expect(budget, name).toBeLessThanOrEqual(500);
    }
    expect(PERFORMANCE_BENCHMARK_ENV.repeats).toBeGreaterThanOrEqual(10);
    expect(PERFORMANCE_BENCHMARK_ENV.suite).toContain("f9");
    expect(BLOCK_DELTA_MAX_FRACTION_OF_FULL).toBeLessThan(0.5);
  });
});
