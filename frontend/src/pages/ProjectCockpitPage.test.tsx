import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/http";
import { ProjectCockpitPage } from "@/pages/ProjectCockpitPage";
import type {
  DraftArtifact,
  DraftArtifactSummary,
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
    getThread: vi.fn(),
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
  ChatRail: ({
    chatError,
    pendingInstruction,
    onConversationUpdate,
  }: {
    chatError?: string | null;
    pendingInstruction?: { id: number; text: string } | null;
    onConversationUpdate?: () => void;
  }) => (
    <div data-testid="chat-rail">
      {chatError ? <div role="alert">{chatError}</div> : null}
      {pendingInstruction ? (
        <div data-testid="pending-chat-instruction">{pendingInstruction.text}</div>
      ) : null}
      <button type="button" onClick={() => onConversationUpdate?.()}>
        Finish conversation
      </button>
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
      <div data-instruction-tray-host />
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
    onRunCreateCostPlan,
    onRunRefreshCostPlan,
    onRunProcessInvoices,
    latestCostPlanDraft,
    onRunProcurement,
    onSelectWorkflow,
    onDraftSelected,
  }: {
    onRunCreateCostPlan: () => void;
    onRunRefreshCostPlan?: () => void;
    onRunProcessInvoices?: () => void;
    latestCostPlanDraft: DraftArtifactSummary | null;
    onRunProcurement?: (kind: string, targetName: string) => void;
    onSelectWorkflow?: (workflowId: string) => void;
    onDraftSelected?: (draft: DraftArtifactSummary) => void;
  }) => (
    <div>
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
      <div data-testid="inline-cost-workbook">
        {latestCostPlanDraft ? `draft-v${latestCostPlanDraft.version}` : "no-draft"}
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
    mocks.api.getThread.mockResolvedValue(thread);
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

  it("sends Create cost plan as a chat instruction instead of starting a durable run", async () => {
    const user = userEvent.setup();
    renderProjectCockpit();

    await user.click(await screen.findByRole("button", { name: "Create cost plan" }));

    expect(await screen.findByTestId("pending-chat-instruction")).toHaveTextContent(
      "Create cost plan",
    );
    expect(mocks.api.startWorkflowRun).not.toHaveBeenCalled();
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

    await waitFor(() => {
      expect(screen.getByTestId("repository")).toHaveTextContent(rftDraft.id);
    });
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

  it("sends Refresh cost plan and Process invoices as chat instructions", async () => {
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

    await user.click(await screen.findByRole("button", { name: "Refresh cost plan" }));
    expect(await screen.findByTestId("pending-chat-instruction")).toHaveTextContent(
      "Refresh cost plan",
    );

    await user.click(screen.getByRole("button", { name: "Process invoices" }));
    expect(await screen.findByTestId("pending-chat-instruction")).toHaveTextContent(
      "Process invoices",
    );
    expect(mocks.api.startWorkflowRun).not.toHaveBeenCalled();
  });

  it("sends procurement create as a chat instruction", async () => {
    const user = userEvent.setup();
    renderProjectCockpit();

    await user.click(
      await screen.findByRole("button", { name: "Create electrical RFT" }),
    );

    expect(await screen.findByTestId("pending-chat-instruction")).toHaveTextContent(
      "Create a trade package for Electrical",
    );
    expect(mocks.api.startWorkflowRun).not.toHaveBeenCalled();
    expect(mocks.api.createProcurementRequest).not.toHaveBeenCalled();
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
    expect(await screen.findByTestId("pending-chat-instruction")).toHaveTextContent(
      "Create cost plan",
    );
    expect(mocks.api.startWorkflowRun).not.toHaveBeenCalled();
  });

  it("keeps chat mounted when a post-turn message refresh times out", async () => {
    const user = userEvent.setup();
    mocks.api.getThreadMessages.mockRejectedValueOnce(
      new ApiError("Request timed out.", { kind: "timeout" }),
    );

    renderProjectCockpit();

    await screen.findByTestId("chat-rail");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Finish conversation" }));
    await waitFor(() => expect(mocks.api.getThreadMessages).toHaveBeenCalled());

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-rail")).toBeInTheDocument();
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
