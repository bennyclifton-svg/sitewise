import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ActivityStream } from "@/components/chat/ActivityStream";
import { api } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getWorkflowRun: vi.fn(),
  },
}));

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function run(overrides: Partial<WorkflowRun> = {}): WorkflowRun {
  return {
    id: "run-1",
    project_id: "project-1",
    requested_by_user_id: "user-1",
    requested_by_thread_id: null,
    requested_by_turn_id: null,
    workflow_type: "create_cost_plan",
    idempotency_key: "key-1",
    schema_version: 1,
    frozen_project_context_version: 1,
    frozen_profile_revision: 1,
    frozen_snapshot_fingerprint: "fp",
    frozen_evidence_fingerprint: "ev",
    frozen_decision_set_revision: 1,
    frozen_selection_revision: null,
    frozen_artefact_version: null,
    state: "running",
    attempt: 1,
    max_attempts: 3,
    cancel_requested: false,
    progress: { stage: "context_ready", percent: 0 },
    stage_durations_ms: {},
    result_artefact_id: null,
    result_reference: null,
    error_class: null,
    error_message: null,
    created_at: "2026-07-21T00:00:00Z",
    started_at: "2026-07-21T00:00:01Z",
    completed_at: null,
    updated_at: "2026-07-21T00:00:01Z",
    ...overrides,
  };
}

describe("ActivityStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows one cube and merged status lines", async () => {
    vi.mocked(api.getWorkflowRun).mockResolvedValue(run());

    const { container } = render(
      <ActivityStream
        busy
        statusMessage="Workflow queued"
        toolEvents={[
          {
            kind: "tool",
            tool: "search_documents",
            state: "done",
            message: "Searched · plant.pdf",
            documents: ["plant.pdf"],
          },
        ]}
        workflowRuns={[
          {
            kind: "workflow_run",
            projectId: "project-1",
            runId: "run-1",
            workflowType: "create_cost_plan",
          },
        ]}
        projectId="project-1"
      />,
      { wrapper: wrapper() },
    );

    const status = await screen.findByTestId("activity-stream");
    expect(status.querySelectorAll(".streaming-cube")).toHaveLength(1);
    expect(container.querySelectorAll(".streaming-cube")).toHaveLength(1);
    expect(status.querySelector(".streaming-status-live")).toBeTruthy();
    expect(status).toHaveTextContent("Searched · plant.pdf");
    await waitFor(() => {
      expect(status).toHaveTextContent("Project context ready.");
    });
    expect(status).not.toHaveTextContent("Workflow queued");
  });

  it("shows a starting line beside the cube while busy before the first status", () => {
    render(<ActivityStream busy />, { wrapper: wrapper() });

    const status = screen.getByTestId("activity-stream");
    expect(status).toHaveAttribute("aria-label", "Reading your request…");
    expect(status.querySelector(".streaming-cube")).toBeTruthy();
    expect(status.querySelector(".streaming-status-live")).toHaveTextContent(
      "Reading your request…",
    );
  });
});
