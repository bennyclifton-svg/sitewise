import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkflowProgressStrip } from "@/components/project/WorkflowProgressStrip";

describe("WorkflowProgressStrip", () => {
  it("shows real section progress and a cancel action", () => {
    const onCancel = vi.fn();
    render(
      <WorkflowProgressStrip
        title="Updating Project Plan"
        kind="project_plan"
        runId="run-1"
        runState="running"
        progressStage="section_started"
        progress={{
          stage: "section_started",
          active_section: "actions",
          sections: [
            { id: "assessment", label: "Assessment", status: "complete" },
            { id: "actions", label: "Actions", status: "generating" },
            { id: "risks", label: "Risks", status: "queued" },
          ],
        }}
        onCancel={onCancel}
      />,
    );

    const status = screen.getByTestId("workflow-progress-strip");
    expect(status).toHaveTextContent("Writing Actions…");
    expect(status).toHaveTextContent("1/3 sections");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "33");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("uses an indeterminate bar when the backend has no measurable progress", () => {
    render(
      <WorkflowProgressStrip
        title="Creating Project Plan"
        kind="project_plan"
        runId="run-create"
        runState="running"
        progressStage="retrieval_complete"
        progress={{ stage: "retrieval_complete" }}
      />,
    );
    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Project evidence and guidance ready.",
    );
    expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
    expect(screen.getByTestId("workflow-progress-strip")).not.toHaveTextContent("%")
  });

  it("shows waiting copy while queued", () => {
    render(
      <WorkflowProgressStrip
        title="Creating Project Plan"
        kind="project_plan"
        runId="run-queued"
        runState="queued"
        progressStage="queued"
      />,
    );
    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Waiting for a worker…",
    );
  });
});
