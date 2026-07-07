import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    getProjectCockpitBootstrap: vi.fn(),
    getThreadMessages: vi.fn(),
    listThreads: vi.fn(),
    runCreateCostPlan: vi.fn(),
  },
  reloadProjectWorkspaceTree: vi.fn(),
  seedProjectData: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: mocks.api,
}));

vi.mock("@/lib/queries/project-data", () => ({
  projectKeys: {
    evidence: (projectId: string) => ["project", projectId, "evidence"],
  },
  reloadProjectWorkspaceTree: mocks.reloadProjectWorkspaceTree,
  seedProjectData: mocks.seedProjectData,
  useProjectEvidence: () => ({ data: [] }),
  useProjectWorkspaceTree: () => ({ data: [] }),
}));

vi.mock("@/components/project/DocumentRepositoryPanel", () => ({
  DocumentRepositoryPanel: () => <div data-testid="repository" />,
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
  ChatRail: () => <div data-testid="chat-rail" />,
}));

vi.mock("@/components/project/ProjectShell", () => ({
  ProjectShell: ({
    leftNav,
    children,
    repository,
  }: {
    leftNav: ReactNode;
    children: ReactNode;
    repository: ReactNode;
  }) => (
    <div>
      {leftNav}
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
  }: {
    isRunningCostPlan: boolean;
    onRunCreateCostPlan: () => void;
  }) => (
    <div>
      <div data-testid="control-cost-plan-state">
        {isRunningCostPlan ? "running" : "idle"}
      </div>
      <button type="button" onClick={onRunCreateCostPlan}>
        Create cost plan
      </button>
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
    mocks.api.listThreads.mockResolvedValue([thread]);
    mocks.api.getThreadMessages.mockResolvedValue([]);
    mocks.api.getLatestDraft.mockResolvedValue(costPlanSummary);
    mocks.api.runCreateCostPlan.mockResolvedValue({
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
    });
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
    expect(screen.getByTestId("draft-review")).toHaveTextContent("draft-v2");

    resolveWorkspaceRefresh?.();
  });
});

function renderProjectCockpit() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/projects/project-1"]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectCockpitPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
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
  user_role: "architect-pm",
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
  model: "gpt-4o-mini",
  runtime: "clerk-sitewise-create-cost-plan-hybrid",
  created_at: "2026-07-06T10:08:44.000Z",
  updated_at: "2026-07-06T10:08:44.000Z",
};

const costPlanDraft: DraftArtifact = {
  ...costPlanSummary,
  content_markdown: "# Project Cost Plan",
  provenance_metadata: null,
};
