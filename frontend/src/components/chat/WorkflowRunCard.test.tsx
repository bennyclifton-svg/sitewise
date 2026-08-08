import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkflowRunCard } from "@/components/chat/WorkflowRunCard";
import { api } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getWorkflowRun: vi.fn(),
    getProjectDraft: vi.fn(),
  },
}));

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function run(overrides: Partial<WorkflowRun> = {}): WorkflowRun {
  return {
    id: "run-1",
    project_id: "project-1",
    requested_by_user_id: "user-1",
    requested_by_thread_id: null,
    requested_by_turn_id: null,
    workflow_type: "consultant_procurement",
    idempotency_key: "key-1",
    schema_version: 1,
    frozen_profile_revision: 1,
    frozen_snapshot_fingerprint: "fp",
    frozen_evidence_fingerprint: "ev",
    frozen_decision_set_revision: 1,
    frozen_selection_revision: null,
    frozen_artefact_version: null,
    state: "queued",
    attempt: 1,
    max_attempts: 3,
    cancel_requested: false,
    progress: { percent: 0 },
    stage_durations_ms: {},
    result_artefact_id: null,
    result_reference: null,
    error_class: null,
    error_message: null,
    created_at: "2026-07-21T00:00:00Z",
    started_at: null,
    completed_at: null,
    updated_at: "2026-07-21T00:00:00Z",
    ...overrides,
  };
}

describe("WorkflowRunCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows progress while the consultant tender run is queued", async () => {
    vi.mocked(api.getWorkflowRun).mockResolvedValue(run());

    render(
      <WorkflowRunCard
        projectId="project-1"
        runRef={{
          kind: "workflow_run",
          projectId: "project-1",
          runId: "run-1",
          workflowType: "consultant_procurement",
          action: "queued",
        }}
      />,
      { wrapper: wrapper() },
    );

    expect(
      await screen.findByText(/Queued Request for Tender/i),
    ).toBeInTheDocument();
  });

  it("renders an openable artefact card when the run completes", async () => {
    vi.mocked(api.getWorkflowRun).mockResolvedValue(
      run({
        state: "complete",
        progress: { percent: 100 },
        result_artefact_id: "draft-1",
      }),
    );
    vi.mocked(api.getProjectDraft).mockResolvedValue({
      id: "draft-1",
      project_id: "project-1",
      workflow_type: "consultant_procurement_mechanical_engineer",
      version: 1,
      status: "draft",
      title: "Request for Tender - Mechanical engineer",
      workspace_path: "02-consultant/consultant_procurement_mechanical_engineer_v01.draft.md",
      author_user_id: "user-1",
      model: null,
      runtime: "clerk-consultant-procurement",
      created_at: "2026-07-21T00:00:00Z",
      updated_at: "2026-07-21T00:00:00Z",
      content_markdown: "# Request for Tender",
      provenance_metadata: null,
    });

    render(
      <WorkflowRunCard
        projectId="project-1"
        runRef={{
          kind: "workflow_run",
          projectId: "project-1",
          runId: "run-1",
          workflowType: "consultant_procurement",
          action: "queued",
        }}
      />,
      { wrapper: wrapper() },
    );

    expect(
      await screen.findByText("Request for Tender - Mechanical engineer"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute(
        "href",
        "/projects/project-1?artefact=draft-1&workflow=consultant_procurement_mechanical_engineer&revision=1",
      );
    });
  });
});
