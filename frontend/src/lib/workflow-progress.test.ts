import { describe, expect, it } from "vitest";

import {
  formatEtaSeconds,
  resolveWorkflowDisplayStage,
  WorkflowRunEstimator,
  workflowProgressStage,
  workflowProgressTitle,
  workflowRunPreview,
  WORKFLOW_BUDGET_SECONDS_DEFAULT,
} from "@/lib/workflow-progress";

function makeEstimator(budgetSeconds = 240): {
  estimator: WorkflowRunEstimator;
  advance: (seconds: number) => void;
} {
  let nowMs = 0;
  const estimator = new WorkflowRunEstimator({
    budgetSeconds,
    now: () => nowMs,
    startedAtMs: 0,
  });
  return {
    estimator,
    advance: (seconds: number) => {
      nowMs += seconds * 1000;
    },
  };
}

describe("WorkflowRunEstimator", () => {
  it("starts near zero with a positive ETA", () => {
    const { estimator } = makeEstimator();
    const snapshot = estimator.snapshot();
    expect(snapshot.fraction).toBe(0);
    expect(snapshot.etaSeconds).toBe(WORKFLOW_BUDGET_SECONDS_DEFAULT);
  });

  it("advances monotonically and never reaches 100% while active", () => {
    const { estimator, advance } = makeEstimator(100);
    const fractions: number[] = [];
    for (let i = 0; i < 10; i += 1) {
      advance(15);
      fractions.push(estimator.snapshot().fraction);
    }
    for (let i = 1; i < fractions.length; i += 1) {
      expect(fractions[i]!).toBeGreaterThanOrEqual(fractions[i - 1]!);
    }
    expect(fractions.at(-1)!).toBeLessThan(1);
    expect(fractions.at(-1)!).toBeLessThanOrEqual(0.98);
  });

  it("snaps to complete only after markComplete", () => {
    const { estimator, advance } = makeEstimator(60);
    advance(60);
    expect(estimator.snapshot().fraction).toBeLessThan(1);
    estimator.markComplete();
    expect(estimator.snapshot()).toEqual({ fraction: 1, etaSeconds: 0 });
  });
});

describe("resolveWorkflowDisplayStage", () => {
  it("maps queued and starting to fixed copy", () => {
    expect(
      resolveWorkflowDisplayStage({
        kind: "project_plan",
        backendStage: "queued",
        runState: "queued",
        elapsedSeconds: 1,
      }).message,
    ).toBe("Waiting for a worker…");

    expect(
      resolveWorkflowDisplayStage({
        kind: "project_plan",
        backendStage: "starting",
        runState: "running",
        elapsedSeconds: 2,
      }).message,
    ).toBe("Loading project profile…");
  });

  it("rotates drafting sublines over time while executing", () => {
    const first = resolveWorkflowDisplayStage({
      kind: "project_plan",
      backendStage: "executing",
      runState: "running",
      elapsedSeconds: 120,
      budgetSeconds: 240,
      nowMs: 0,
    });
    const second = resolveWorkflowDisplayStage({
      kind: "project_plan",
      backendStage: "executing",
      runState: "running",
      elapsedSeconds: 120,
      budgetSeconds: 240,
      nowMs: 5_000,
    });
    expect(first.id).toBe("drafting");
    expect(second.id).toBe("drafting");
    expect(first.message).not.toBe(second.message);
  });
});

describe("workflowProgressTitle", () => {
  it("distinguishes create vs update for project and cost plans", () => {
    expect(workflowProgressTitle("project_plan", "create")).toBe(
      "Creating Project Plan",
    );
    expect(workflowProgressTitle("project_plan", "update")).toBe(
      "Updating Project Plan",
    );
    expect(workflowProgressTitle("cost_plan", "create")).toBe("Creating Cost Plan");
    expect(workflowProgressTitle("cost_plan", "update")).toBe("Refreshing Cost Plan");
    expect(workflowProgressTitle("procurement", "create")).toBe(
      "Preparing Procurement Request",
    );
  });
});

describe("workflowProgressStage", () => {
  it("reads stage strings from progress payloads", () => {
    expect(workflowProgressStage({ stage: "executing", percent: 50 })).toBe(
      "executing",
    );
    expect(workflowProgressStage({ percent: 50 })).toBeNull();
    expect(workflowProgressStage(null)).toBeNull();
  });
});

describe("formatEtaSeconds (shared)", () => {
  it("formats short and long remaining times", () => {
    expect(formatEtaSeconds(3)).toBe("a few seconds left");
    expect(formatEtaSeconds(130)).toBe("~2 min left");
  });
});

describe("workflowRunPreview", () => {
  it("returns the in-progress draft a run has published", () => {
    expect(
      workflowRunPreview({
        stage: "executing",
        percent: 50,
        preview: { stage: "scaffold", markdown: "# Project Management Plan" },
      }),
    ).toEqual({ stage: "scaffold", markdown: "# Project Management Plan" });
  });

  it("returns null before a run has published anything", () => {
    expect(workflowRunPreview({ stage: "queued", percent: 0 })).toBeNull();
    expect(workflowRunPreview(null)).toBeNull();
    expect(workflowRunPreview(undefined)).toBeNull();
  });

  it("returns null for a preview with no usable markdown", () => {
    expect(workflowRunPreview({ preview: { stage: "scaffold" } })).toBeNull();
    expect(
      workflowRunPreview({ preview: { stage: "scaffold", markdown: "   " } }),
    ).toBeNull();
    expect(workflowRunPreview({ preview: "not-an-object" })).toBeNull();
  });

  it("falls back to a generic stage when the publisher omitted one", () => {
    expect(workflowRunPreview({ preview: { markdown: "# Draft" } })).toEqual({
      stage: "drafting",
      markdown: "# Draft",
    });
  });
});
