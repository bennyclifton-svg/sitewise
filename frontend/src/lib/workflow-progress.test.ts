import { describe, expect, it } from "vitest";

import {
  resolveWorkflowDisplayStage,
  workflowProgressStage,
  workflowProgressTitle,
  workflowRunPercent,
  workflowRunPreview,
  workflowSectionProgress,
} from "@/lib/workflow-progress";

const sectionProgress = {
  stage: "section_started",
  active_section: "scope",
  completed_sections: 1,
  total_sections: 3,
  sections: [
    { id: "background", label: "Background", status: "complete" },
    { id: "scope", label: "Scope", status: "generating" },
    { id: "programme", label: "Programme", status: "queued" },
  ],
};

describe("resolveWorkflowDisplayStage", () => {
  it("maps real lifecycle events to fixed copy", () => {
    expect(
      resolveWorkflowDisplayStage({
        kind: "project_plan",
        backendStage: "context_ready",
        runState: "running",
      }).message,
    ).toBe("Project context ready.");
    expect(
      resolveWorkflowDisplayStage({
        kind: "project_plan",
        backendStage: "retrieval_complete",
        runState: "running",
      }).message,
    ).toBe("Project evidence and guidance ready.");
  });

  it("names the section that is actually generating", () => {
    expect(
      resolveWorkflowDisplayStage({
        kind: "procurement",
        backendStage: "section_started",
        runState: "running",
        progress: sectionProgress,
      }),
    ).toEqual({ id: "section_started", message: "Writing Scope…" });
  });

  it("shows deterministic invoice processing stages", () => {
    expect(
      resolveWorkflowDisplayStage({
        kind: "cost_plan",
        backendStage: "extracting_and_mapping",
        runState: "running",
      }),
    ).toEqual({
      id: "extracting_and_mapping",
      message: "Extracting and mapping invoices…",
    });
  });
});

describe("truthful progress", () => {
  it("derives progress only from completed section events", () => {
    expect(workflowSectionProgress(sectionProgress)).toEqual({
      completed: 1,
      total: 3,
      sections: sectionProgress.sections,
    });
    expect(workflowRunPercent(sectionProgress)).toBe(33);
  });

  it("uses explicit backend percentages and otherwise returns no percentage", () => {
    expect(workflowRunPercent({ stage: "verifying_workbook", percent: 80 })).toBe(80);
    expect(workflowRunPercent({ stage: "retrieval_complete" })).toBeNull();
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
    expect(workflowProgressTitle("cost_plan", "invoices")).toBe("Processing Invoices");
    expect(workflowProgressTitle("procurement", "create")).toBe(
      "Preparing Procurement Request",
    );
  });
});

describe("workflow payload helpers", () => {
  it("reads stage strings from progress payloads", () => {
    expect(workflowProgressStage({ stage: "saving" })).toBe("saving");
    expect(workflowProgressStage({ percent: 50 })).toBeNull();
  });

  it("returns the in-progress draft a run has published", () => {
    expect(
      workflowRunPreview({
        stage: "scaffold_ready",
        preview: { stage: "scaffold_ready", markdown: "# Project Management Plan" },
      }),
    ).toEqual({
      stage: "scaffold_ready",
      markdown: "# Project Management Plan",
    });
  });

  it("rejects missing preview content and defaults a missing preview stage", () => {
    expect(workflowRunPreview({ stage: "queued" })).toBeNull();
    expect(workflowRunPreview({ preview: { markdown: "   " } })).toBeNull();
    expect(workflowRunPreview({ preview: { markdown: "# Draft" } })).toEqual({
      stage: "drafting",
      markdown: "# Draft",
    });
  });
});
