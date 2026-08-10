import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { projectKeys } from "@/lib/queries/project-data";
import { ProjectCockpitPage } from "@/pages/ProjectCockpitPage";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  ProcessInvoicesResult,
  ProjectDetail,
} from "@/lib/types/project";

const mocks = vi.hoisted(() => ({
  api: {
    createProjectThread: vi.fn(),
    getLatestDraft: vi.fn(),
    getProject: vi.fn(),
    getProjectChatBootstrap: vi.fn(),
    getProjectCockpitBootstrap: vi.fn(),
    getProjectDraft: vi.fn(),
    getThreadMessages: vi.fn(),
    listThreads: vi.fn(),
    startWorkflowRun: vi.fn(),
    getWorkflowResult: vi.fn(),
    cancelWorkflowRun: vi.fn(),
    createProcurementRequest: vi.fn(),
  },
  reloadProjectWorkspaceTree: vi.fn(),
  seedProjectData: vi.fn(),
  setProjectDetail: vi.fn(),
  waitForWorkflowRun: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: mocks.api,
}));

vi.mock("@/lib/queries/workflow-runs", () => ({
  useWorkflowRun: () => ({ data: null }),
  waitForWorkflowRun: mocks.waitForWorkflowRun,
}));

vi.mock("@/lib/queries/project-data", async () => {
  const actual = await vi.importActual<typeof import("@/lib/queries/project-data")>(
    "@/lib/queries/project-data",
  );
  return {
    ...actual,
    reloadProjectWorkspaceTree: mocks.reloadProjectWorkspaceTree,
    seedProjectData: mocks.seedProjectData,
    setProjectDetail: mocks.setProjectDetail,
    useProjectDetail: () => ({ data: project }),
    useProjectEventCursor: () => ({ applyResource: vi.fn(), pollNow: vi.fn() }),
    useProjectEvidence: () => ({ data: [] }),
    useProjectWorkspaceTree: () => ({ data: [] }),
  };
});

vi.mock("@/components/project/DocumentRepositoryPanel", () => ({
  DocumentRepositoryPanel: ({
    usageHighlightArtefactId,
  }: {
    usageHighlightArtefactId?: string | null;
  }) => (
    <div data-testid="repository">
      {usageHighlightArtefactId ?? "no-usage-highlight"}
    </div>
  ),
}));

vi.mock("@/components/project/DraftReviewPanel", () => ({
  DraftReviewPanel: ({ draft }: { draft: DraftArtifactSummary | null }) => (
    <div data-testid="draft-review">{draft ? `draft-v${draft.version}` : "no-draft"}</div>
  ),
}));

vi.mock("@/components/project/WorkspaceFilePanel", () => ({
  WorkspaceFilePanel: () => <div data-testid="workspace-file" />,
}));

vi.mock("@/components/project/WorkspaceFolderPanel", () => ({
  WorkspaceFolderPanel: () => <div data-testid="workspace-folder" />,
}));

vi.mock("@/components/chat/ChatRail", () => ({
  ChatRail: ({ chatError }: { chatError?: string | null }) => (
    <div data-testid="chat-rail">
      {chatError ? <div role="alert">{chatError}</div> : null}
    </div>
  ),
}));

vi.mock("@/components/project/ProjectShell", () => ({
  ProjectShell: ({
    leftNav,
    children,
    repository,
    chatPanel,
  }: {
    leftNav: ReactNode;
    children: ReactNode;
    repository: ReactNode;
    chatPanel: ReactNode;
  }) => (
    <div>
      {leftNav}
      {chatPanel}
      {children}
      {repository}
    </div>
  ),
}));

vi.mock("@/components/project/ProjectLeftNav", () => ({
  ProjectLeftNav: ({
    workflows,
  }: {
    workflows?: {
      tiles: Array<{ id: string; status: string; statusLabel: string }>;
    };
  }) => {
    const costPlan = workflows?.tiles.find((tile) => tile.id === "cost-plan");
    return (
      <div data-testid="cost-plan-nav-status">
        {costPlan ? `${costPlan.status}:${costPlan.statusLabel}` : "missing"}
      </div>
    );
  },
}));

vi.mock("@/components/project/ProjectControlBoard", () => ({
  ProjectControlBoard: ({
    isRunningCostPlan,
    onRunCreateCostPlan,
    onRunRefreshCostPlan,
    onRunProcessInvoices,
    costPlanWorkflowError,
    onCancelCostPlan,
    latestCostPlanDraft,
    invoiceProcessResult,
    isRunningProcurement,
    onRunProcurement,
    onSelectWorkflow,
    onDraftSelected,
  }: {
    isRunningCostPlan: boolean;
    onRunCreateCostPlan: () => void;
    onRunRefreshCostPlan?: () => void;
    onRunProcessInvoices?: () => void;
    costPlanWorkflowError: string | null;
    onCancelCostPlan?: () => void;
    latestCostPlanDraft: DraftArtifactSummary | null;
    invoiceProcessResult?: ProcessInvoicesResult | null;
    isRunningProcurement: boolean;
    onRunProcurement?: (kind: string, targetName: string) => void;
    onSelectWorkflow?: (workflowId: string) => void;
    onDraftSelected?: (draft: DraftArtifactSummary) => void;
  }) => (
    <div>
      <div data-testid="control-cost-plan-state">
        {isRunningCostPlan ? "running" : "idle"}
      </div>
      <button type="button" onClick={onRunCreateCostPlan}>
        Create cost plan
      </button>
      {onSelectWorkflow ? (
        <>
          <button type="button" onClick={() => onSelectWorkflow("cost-plan")}>
            Open Cost Plan panel
          </button>
          <button
            type="button"
            onClick={() => onSelectWorkflow("procurement-requests")}
          >
            Open Procurement panel
          </button>
        </>
      ) : null}
      {onDraftSelected ? (
        <button
          type="button"
          onClick={() =>
            onDraftSelected({
              ...costPlanSummary,
              id: "main-works-rft-v2",
              workflow_type: "trade_rft_main_works",
              title: "Request for Tender - Main Works",
            })
          }
        >
          Select Main Works RFT
        </button>
      ) : null}
      {onRunRefreshCostPlan ? (
        <button type="button" onClick={onRunRefreshCostPlan}>
          Refresh cost plan
        </button>
      ) : null}
      {onRunProcessInvoices ? (
        <button type="button" onClick={onRunProcessInvoices}>
          Process invoices
        </button>
      ) : null}
      {isRunningCostPlan && onCancelCostPlan ? (
        <button type="button" onClick={onCancelCostPlan}>
          Cancel cost plan
        </button>
      ) : null}
      {costPlanWorkflowError ? <div>{costPlanWorkflowError}</div> : null}
      <div data-testid="inline-cost-workbook">
        {latestCostPlanDraft ? `draft-v${latestCostPlanDraft.version}` : "no-draft"}
      </div>
      {invoiceProcessResult ? (
        <div data-testid="invoice-process-result">
          {JSON.stringify(invoiceProcessResult)}
        </div>
      ) : null}
      <div data-testid="control-procurement-state">
        {isRunningProcurement ? "running" : "idle"}
      </div>
      {onRunProcurement ? (
        <button type="button" onClick={() => onRunProcurement("trade_rft", "Electrical")}>
          Create electrical RFT
        </button>
      ) : null}
    </div>
  ),
}));

describe("ProjectCockpitPage cost plan workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.api.getProjectCockpitBootstrap.mockResolvedValue({
      project,
      projects: [project],
      evidence: [],
      workspace_tree: {
        project_id: project.id,
        root_path: project.workspace_path,
        tree: [],
      },
      platform_knowledge: { available: true, buckets: [] },
      latest_drafts: {
        create_pmp: null,
        create_cost_plan: null,
        sort_files: null,
      },
      timings_ms: {},
    });
    mocks.api.getProjectChatBootstrap.mockResolvedValue({ thread, messages: [] });
    mocks.api.listThreads.mockResolvedValue([thread]);
    mocks.api.getThreadMessages.mockResolvedValue([]);
    mocks.api.getLatestDraft.mockResolvedValue(costPlanSummary);
    mocks.api.getProjectDraft.mockResolvedValue(costPlanDraft);
    mocks.api.getProject.mockResolvedValue(project);
    mocks.api.startWorkflowRun.mockResolvedValue({
      id: "run-1",
      project_id: project.id,
      state: "queued",
    });
    mocks.api.getWorkflowResult.mockResolvedValue({
      run: { id: "run-1", project_id: project.id, state: "complete" },
      result: {
        status: "complete",
        gate: project.overlay_status,
        trace: [
          {
            step: "draft_save",
            status: "complete",
            message: "Saved Create Cost Plan as a versioned draft artefact.",
            metadata: {},
          },
        ],
        draft: costPlanDraft,
        message: null,
      },
    });
    mocks.api.cancelWorkflowRun.mockResolvedValue({
      id: "run-1",
      project_id: project.id,
      state: "running",
      cancel_requested: true,
    });
    mocks.api.createProcurementRequest.mockResolvedValue({ id: "request-1" });
    mocks.waitForWorkflowRun.mockImplementation(
      async (_client, _projectId, run) => ({ ...run, state: "complete" }),
    );
  });

  it("stops showing Cost Plan as running once the draft is returned", async () => {
    const user = userEvent.setup();
    let resolveWorkspaceRefresh: (() => void) | undefined;
    mocks.reloadProjectWorkspaceTree.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveWorkspaceRefresh = resolve;
        }),
    );

    renderProjectCockpit();

    await user.click(await screen.findByRole("button", { name: "Create cost plan" }));

    await waitFor(() => {
      expect(screen.getByTestId("cost-plan-nav-status")).toHaveTextContent(
        "draft:Draft v2",
      );
    });
    expect(screen.getByTestId("inline-cost-workbook")).toHaveTextContent("draft-v2");
    expect(screen.queryByTestId("draft-review")).not.toBeInTheDocument();
    expect(mocks.api.startWorkflowRun).toHaveBeenCalledWith(
      project.id,
      "cost-plan",
      expect.objectContaining({
        expected_snapshot_fingerprint: "a".repeat(64),
        expected_profile_revision: 1,
        expected_decision_set_revision: 1,
      }),
    );

    resolveWorkspaceRefresh?.();
  });

  it("highlights documents used by the open Cost Plan", async () => {
    const user = userEvent.setup();
    mocks.api.getProjectCockpitBootstrap.mockResolvedValueOnce({
      project,
      projects: [project],
      evidence: [],
      workspace_tree: {
        project_id: project.id,
        root_path: project.workspace_path,
        tree: [],
      },
      platform_knowledge: { available: true, buckets: [] },
      latest_drafts: {
        create_pmp: null,
        create_cost_plan: costPlanSummary,
        sort_files: null,
      },
      timings_ms: {},
    });

    renderProjectCockpit();
    await user.click(await screen.findByRole("button", { name: "Open Cost Plan panel" }));

    expect(screen.getByTestId("repository")).toHaveTextContent(costPlanSummary.id);
  });

  it("highlights documents used by an open trade RFT", async () => {
    const rftDraft: DraftArtifact = {
      ...costPlanDraft,
      id: "rft-draft-1",
      workflow_type: "trade_rft_mechanical_services_contractor",
      title: "Request for Tender - Mechanical Services Contractor",
      workspace_path:
        "04-projects/walsh-reno/05-procurement/mechanical/02-tender-pack/rft-v01.md",
      content_markdown: "# Request for Tender",
    };
    mocks.api.getProjectDraft.mockResolvedValueOnce(rftDraft);

    renderProjectCockpit({
      initialEntry: `/projects/project-1?artefact=${rftDraft.id}&revision=2`,
    });

    expect(await screen.findByTestId("draft-review")).toHaveTextContent("draft-v2");
    expect(screen.getByTestId("repository")).toHaveTextContent(rftDraft.id);
  });

  it("highlights documents for the RFT selected in the procurement workbench", async () => {
    const user = userEvent.setup();
    renderProjectCockpit();

    await user.click(
      await screen.findByRole("button", { name: "Open Procurement panel" }),
    );
    await user.click(screen.getByRole("button", { name: "Select Main Works RFT" }));

    expect(screen.getByTestId("repository")).toHaveTextContent("main-works-rft-v2");
  });

  it("shows the workbook draft returned by a Cost Plan refresh", async () => {
    const user = userEvent.setup();
    const baseDraft = { ...costPlanSummary, version: 1 };
    mocks.api.getProjectCockpitBootstrap.mockResolvedValueOnce({
      project,
      projects: [project],
      evidence: [],
      workspace_tree: {
        project_id: project.id,
        root_path: project.workspace_path,
        tree: [],
      },
      platform_knowledge: { available: true, buckets: [] },
      latest_drafts: {
        create_pmp: null,
        create_cost_plan: baseDraft,
        sort_files: null,
      },
      timings_ms: {},
    });
    mocks.api.getLatestDraft.mockRejectedValueOnce(new Error("not available"));
    mocks.api.getWorkflowResult.mockResolvedValueOnce({
      run: { id: "run-1", project_id: project.id, state: "complete" },
      result: {
        status: "complete",
        draft: costPlanDraft,
      },
    });

    renderProjectCockpit();

    await user.click(await screen.findByRole("button", { name: "Refresh cost plan" }));

    await waitFor(() => {
      expect(screen.getByTestId("inline-cost-workbook")).toHaveTextContent("draft-v2");
    });
    expect(mocks.api.startWorkflowRun).toHaveBeenCalledWith(
      project.id,
      "cost-plan/refresh",
      expect.objectContaining({
        expected_artefact_version: 1,
        parameters: { proposed_items: [] },
      }),
    );
  });

  it("processes all ingested invoices against the current Cost Plan", async () => {
    const user = userEvent.setup();
    const baseDraft = { ...costPlanSummary, version: 5 };
    mocks.api.getProjectCockpitBootstrap.mockResolvedValueOnce({
      project,
      projects: [project],
      evidence: [],
      workspace_tree: {
        project_id: project.id,
        root_path: project.workspace_path,
        tree: [],
      },
      platform_knowledge: { available: true, buckets: [] },
      latest_drafts: {
        create_pmp: null,
        create_cost_plan: baseDraft,
        sort_files: null,
      },
      timings_ms: {},
    });
    mocks.api.getWorkflowResult.mockResolvedValueOnce({
      run: { id: "run-1", project_id: project.id, state: "complete" },
      result: {
        candidate_count: 4,
        pending_ingest_count: 1,
        booked_invoice_count: 1,
        register_row_count: 1,
        duplicate_count: 0,
        conflict_count: 1,
        review_count: 1,
        extraction_error_count: 1,
        conflicts: ["Duplicate financial facts conflict"],
        review_items: ["INV-2: Unidentified line"],
        extraction_errors: ["INV-3 could not be extracted"],
        cost_plan_version: 6,
        workbook_path: "projects/kavanagh/01-cost/Cost_Plan_v06.draft.xlsx",
        draft_id: costPlanDraft.id,
        draft: { ...costPlanDraft, version: 6 },
      },
    });

    renderProjectCockpit();
    await user.click(await screen.findByRole("button", { name: "Process invoices" }));

    await waitFor(() => {
      expect(mocks.api.startWorkflowRun).toHaveBeenCalledWith(
        project.id,
        "cost-plan/invoices",
        expect.objectContaining({
          expected_artefact_version: 5,
          parameters: { source_document_ids: null },
        }),
      );
    });
    expect(screen.getByTestId("inline-cost-workbook")).toHaveTextContent("draft-v6");
    expect(screen.getByTestId("invoice-process-result")).toHaveTextContent(
      '"conflict_count":1',
    );
    expect(screen.getByTestId("invoice-process-result")).toHaveTextContent(
      '"review_count":1',
    );
    expect(screen.getByTestId("invoice-process-result")).toHaveTextContent(
      '"extraction_error_count":1',
    );
    expect(screen.getByTestId("invoice-process-result")).toHaveTextContent(
      '"pending_ingest_count":1',
    );
  });

  it("queues a trade RFT for worker-side request attachment", async () => {
    const user = userEvent.setup();
    renderProjectCockpit();

    await user.click(
      await screen.findByRole("button", { name: "Create electrical RFT" }),
    );

    await waitFor(() => expect(mocks.api.startWorkflowRun).toHaveBeenCalledOnce());
    expect(mocks.api.createProcurementRequest).not.toHaveBeenCalled();
    expect(mocks.api.startWorkflowRun).toHaveBeenCalledWith(
      project.id,
      "trade-procurement",
      expect.objectContaining({
        expected_snapshot_fingerprint: "a".repeat(64),
        expected_profile_revision: 1,
        expected_decision_set_revision: 1,
        idempotency_key: expect.any(String),
        parameters: {
          package: "Electrical",
          kind: "rft",
          max_pages: 3,
        },
      }),
    );
  });

  it("keeps project controls usable when chat bootstrap fails", async () => {
    const user = userEvent.setup();
    mocks.api.getProjectChatBootstrap.mockRejectedValueOnce(new Error("chat offline"));

    renderProjectCockpit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not open project chat.",
    );
    expect(screen.getByTestId("repository")).toBeInTheDocument();
    expect(screen.getByTestId("cost-plan-nav-status")).toBeInTheDocument();
    const createCostPlan = screen.getByRole("button", { name: "Create cost plan" });
    expect(createCostPlan).toBeEnabled();
    await user.click(createCostPlan);
    await waitFor(() => expect(mocks.api.startWorkflowRun).toHaveBeenCalledOnce());
  });

  it("shows a readable retry path when a durable run fails", async () => {
    const user = userEvent.setup();
    mocks.waitForWorkflowRun.mockImplementationOnce(
      async (_client, _projectId, run) => ({
        ...run,
        state: "failed",
        error_message: "Workbook export failed; retry the Cost Plan.",
      }),
    );

    renderProjectCockpit();
    const button = await screen.findByRole("button", { name: "Create cost plan" });
    await user.click(button);

    expect(
      await screen.findByText("Workbook export failed; retry the Cost Plan."),
    ).toBeInTheDocument();
    expect(button).toBeEnabled();
  });

  /**
   * A workflow launch must read the project itself rather than share the
   * cockpit's cached copy. The cache entry is owned by the project-event
   * poller, which invalidates it on every durable event; sharing it makes the
   * launch inherit both the global `staleTime` (a stale OCC fingerprint) and
   * `invalidateQueries`' `cancelRefetch`, which rejects an in-flight read with
   * a `CancelledError` and aborts the launch before any request is sent.
   */
  it("starts the run with a freshly read fingerprint, not the cached one", async () => {
    const user = userEvent.setup();
    const queryClient = renderProjectCockpit({ staleTime: 30_000 });

    await screen.findByRole("button", { name: "Create cost plan" });
    queryClient.setQueryData(projectKeys.detail(project.id), {
      ...project,
      workflow_capabilities: {
        ...project.workflow_capabilities,
        snapshot_content_fingerprint: "b".repeat(64),
      },
    });

    await user.click(screen.getByRole("button", { name: "Create cost plan" }));

    await waitFor(() => expect(mocks.api.startWorkflowRun).toHaveBeenCalledOnce());
    expect(mocks.api.startWorkflowRun).toHaveBeenCalledWith(
      project.id,
      "cost-plan",
      expect.objectContaining({
        expected_snapshot_fingerprint: "a".repeat(64),
      }),
    );
  });

  it("surfaces the underlying failure when a launch throws an unrecognised error", async () => {
    const user = userEvent.setup();
    mocks.api.getProject.mockRejectedValueOnce(new Error("CancelledError"));

    renderProjectCockpit();
    await user.click(await screen.findByRole("button", { name: "Create cost plan" }));

    expect(
      await screen.findByText(/Create Cost Plan could not run\..*CancelledError/),
    ).toBeInTheDocument();
    expect(mocks.api.startWorkflowRun).not.toHaveBeenCalled();
  });

  it("cancels the exact durable run from the UI", async () => {
    const user = userEvent.setup();
    let finishRun: ((run: Record<string, unknown>) => void) | undefined;
    mocks.waitForWorkflowRun.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finishRun = resolve;
        }),
    );

    renderProjectCockpit();
    await user.click(
      await screen.findByRole("button", { name: "Create cost plan" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Cancel cost plan" }),
    );

    expect(mocks.api.cancelWorkflowRun).toHaveBeenCalledWith(project.id, "run-1");
    finishRun?.({ id: "run-1", state: "cancelled", error_message: null });
  });
});

function renderProjectCockpit(options?: {
  staleTime?: number;
  initialEntry?: string;
}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: options?.staleTime },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options?.initialEntry ?? "/projects/project-1"]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectCockpitPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

const project: ProjectDetail = {
  id: "project-1",
  slug: "walsh-reno",
  title: "Walsh Reno",
  workspace_path: "04-projects/walsh-reno",
  phase: "brief-planning",
  archetype: null,
  building_class: "residential",
  work_type: "refurb",
  state: "NSW",
  status: "active",
  overlay_status: {
    ready: true,
    missing: [],
    invalid: [],
  },
  updated_at: "2026-07-06T10:00:00.000Z",
  metadata: {},
  evidence_preview: null,
  risk_flags: [],
  profile_revision: 1,
  decision_set_revision: 1,
  workflow_capabilities: {
    schema_version: 1,
    snapshot_schema_version: 1,
    snapshot_content_fingerprint: "a".repeat(64),
    capabilities: {
      create_cost_plan: {
        status: "supported",
        reasons: [],
        required_fields: [],
      },
    },
  },
};

const thread = {
  id: "thread-1",
  project_id: project.id,
  title: "Walsh Reno",
  created_at: "2026-07-06T10:00:00.000Z",
  updated_at: "2026-07-06T10:00:00.000Z",
};

const costPlanSummary: DraftArtifactSummary = {
  id: "draft-2",
  project_id: project.id,
  workflow_type: "create_cost_plan",
  version: 2,
  status: "draft",
  title: "Project Cost Plan",
  workspace_path: "04-projects/walsh-reno/01-cost/cost_plan_v02.md",
  author_user_id: "user-1",
  model: "gpt-5.6-terra",
  runtime: "clerk-sitewise-create-cost-plan-hybrid",
  created_at: "2026-07-06T10:08:44.000Z",
  updated_at: "2026-07-06T10:08:44.000Z",
};

const costPlanDraft: DraftArtifact = {
  ...costPlanSummary,
  content_markdown: "# Project Cost Plan",
  provenance_metadata: null,
};
