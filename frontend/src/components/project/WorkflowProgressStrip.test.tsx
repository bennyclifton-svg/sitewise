import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkflowProgressStrip } from "@/components/project/WorkflowProgressStrip";

describe("WorkflowProgressStrip", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the title, stage message, progress bar, and cancel action", () => {
    vi.useFakeTimers();
    let nowMs = 0;
    const onCancel = vi.fn();
    render(
      <WorkflowProgressStrip
        title="Updating Project Plan"
        kind="project_plan"
        runId="run-1"
        runState="running"
        progressStage="executing"
        onCancel={onCancel}
        now={() => nowMs}
        budgetSeconds={240}
      />,
    );

    nowMs = 90_000;
    act(() => {
      vi.advanceTimersByTime(500);
    });

    const status = screen.getByTestId("workflow-progress-strip");
    expect(status).toHaveTextContent("Updating Project Plan");
    expect(status).toHaveTextContent(/…/);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "38");
    expect(status).toHaveTextContent("%");
    expect(status).toHaveTextContent(/left/);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("uses create vs update titles supplied by the parent", () => {
    const { rerender } = render(
      <WorkflowProgressStrip
        title="Creating Project Plan"
        kind="project_plan"
        runId="run-create"
        runState="queued"
        progressStage="queued"
      />,
    );
    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Creating Project Plan",
    );

    rerender(
      <WorkflowProgressStrip
        title="Updating Project Plan"
        kind="project_plan"
        runId="run-update"
        runState="queued"
        progressStage="queued"
      />,
    );
    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Updating Project Plan",
    );
  });

  it("shows waiting copy while queued", () => {
    render(
      <WorkflowProgressStrip
        title="Creating Project Plan"
        kind="project_plan"
        runId="run-1"
        runState="queued"
        progressStage="queued"
      />,
    );
    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Waiting for a worker…",
    );
  });
});
