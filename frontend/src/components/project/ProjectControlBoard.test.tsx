import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import { api } from "@/lib/api";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import type {
  DraftArtifactSummary,
  ProcessInvoicesResult,
  ProjectDetail,
  TaxonomyCatalog,
  WorkflowCapability,
  WorkflowRun,
} from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    updateProject: vi.fn(),
    listProcurementRequests: vi.fn(),
  },
}));

vi.mock("@/lib/queries/taxonomy", () => ({
  useTaxonomy: vi.fn(),
}));

const catalog: TaxonomyCatalog = {
  work_types: [
    { value: "new", label: "New build" },
    { value: "refurb", label: "Refurbishment" },
  ],
  building_classes: [
    {
      value: "commercial",
      label: "Commercial",
      multi_subclass: false,
      work_types: ["new", "refurb"],
      subclasses: [
        {
          value: "office",
          label: "Office (Class 5)",
          ncc_class: "5",
          scale_fields: [],
        },
        { value: "other", label: "Other", ncc_class: "varies", scale_fields: [] },
      ],
    },
  ],
  complexity_dimensions: {
    commercial: [
      {
        key: "operational_constraints",
        label: "Operational constraints",
        options: [
          { value: "vacant", label: "Vacant/Unoccupied" },
          { value: "live_environment", label: "Live Environment (+10-20%)" },
        ],
      },
    ],
  },
  risk_flags: {},
  work_scopes: {},
  emphasis_profiles: { sections: [], base_weights: {}, modifiers: [] },
};

describe("ProjectControlBoard project profile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTaxonomy).mockReturnValue({
      data: catalog,
      error: null,
    } as unknown as ReturnType<typeof useTaxonomy>);
  });

  it("saves taxonomy edits from the project profile panel", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    const updatedChange = {
      profile: {
        project_id: project.id,
        profile_revision: 2,
        building_class: project.building_class,
        work_type: project.work_type,
        subclasses: [{ value: "other", label: "Laboratory office" }],
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: project.state,
        site_address: null,
        client: null,
      },
      previous_revision: 1,
      new_revision: 2,
      changed_fields: ["subclasses" as const],
      cleared_fields: [],
      overlay_status: project.overlay_status,
      risk_flags: project.risk_flags,
    };
    const updatedProject = {
      ...project,
      profile_revision: 2,
      metadata: {
        ...project.metadata,
        taxonomy: {
          ...project.metadata?.taxonomy,
          subclasses: [{ value: "other", label: "Laboratory office" }],
          scale: {},
          complexity: { operational_constraints: "live_environment" },
          work_scope: [],
          site_address: null,
          client: null,
        },
      },
    };
    vi.mocked(api.updateProject).mockResolvedValue(updatedChange);

    render(
      <ProjectControlBoard
        project={project}
        latestDraft={null}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan={false}
        selectedWorkflowId="project-profile"
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={vi.fn()}
        onRunSortFiles={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
        onProjectUpdated={onProjectUpdated}
      />,
    );

    expect(screen.queryByText("Live Operational Environment")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/archetype/i)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Other"));
    await user.type(screen.getByLabelText("Other subclass"), "Laboratory office");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        expected_revision: 1,
        building_class: "commercial",
        work_type: "refurb",
        subclasses: [{ value: "other", label: "Laboratory office" }],
        complexity: { operational_constraints: "live_environment" },
        state: "NSW",
        site_address: null,
        client: null,
      }),
    );
    expect(onProjectUpdated).toHaveBeenCalledWith(updatedProject);
  });

  it("creates a trade RFQ from the RFP / RFT panel", async () => {
    const user = userEvent.setup();
    const onRunProcurement = vi.fn();
    vi.mocked(api.listProcurementRequests).mockResolvedValue([]);

    render(
      <ProjectControlBoard
        project={project}
        latestDraft={null}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan={false}
        selectedWorkflowId="procurement-requests"
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={vi.fn()}
        onRunSortFiles={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
        onRunProcurement={onRunProcurement}
      />,
    );

    await screen.findByText("No procurement requests yet.");
    await user.selectOptions(screen.getByLabelText("Request"), "trade_rfq");
    await user.type(screen.getByLabelText("Target"), "Electrical services");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(onRunProcurement).toHaveBeenCalledWith(
      "trade_rfq",
      "Electrical services",
    );
  });

  it("updates clean controls when a newer server revision arrives", () => {
    const view = render(profileBoard(project));

    expect(screen.getByLabelText("State")).toHaveValue("NSW");
    view.rerender(
      profileBoard({ ...project, profile_revision: 2, state: "VIC" }),
    );

    expect(screen.getByLabelText("State")).toHaveValue("VIC");
    expect(
      screen.queryByText("Project profile changed elsewhere."),
    ).not.toBeInTheDocument();
  });

  it("preserves dirty controls until the user reloads the newer revision", async () => {
    const user = userEvent.setup();
    const view = render(profileBoard(project));
    await user.selectOptions(screen.getByLabelText("State"), "QLD");

    view.rerender(
      profileBoard({ ...project, profile_revision: 2, state: "VIC" }),
    );

    expect(screen.getByLabelText("State")).toHaveValue("QLD");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Revision 2 arrived while you had unsaved edits.",
    );
    expect(screen.getByRole("button", { name: "Save profile" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Reload latest" }));
    expect(screen.getByLabelText("State")).toHaveValue("VIC");
    expect(
      screen.queryByText("Project profile changed elsewhere."),
    ).not.toBeInTheDocument();
  });

  it("rebases only edited fields when the user keeps editing", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    const view = render(profileBoard(project, onProjectUpdated));
    await user.selectOptions(screen.getByLabelText("State"), "QLD");
    const newerProject = {
      ...project,
      profile_revision: 2,
      state: "VIC",
    };
    view.rerender(profileBoard(newerProject, onProjectUpdated));

    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(screen.getByLabelText("State")).toHaveValue("QLD");

    vi.mocked(api.updateProject).mockResolvedValue({
      profile: {
        project_id: project.id,
        profile_revision: 3,
        building_class: project.building_class,
        work_type: project.work_type,
        subclasses: ["office"],
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: "QLD",
        site_address: null,
        client: null,
      },
      previous_revision: 2,
      new_revision: 3,
      changed_fields: ["state"],
      cleared_fields: [],
      overlay_status: project.overlay_status,
      risk_flags: project.risk_flags,
    });
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        expected_revision: 2,
        building_class: "commercial",
        work_type: "refurb",
        subclasses: ["office"],
        complexity: { operational_constraints: "live_environment" },
        state: "QLD",
        site_address: null,
        client: null,
      }),
    );
  });

  it("blocks Create Cost Plan until project profile overlays are set", async () => {
    const user = userEvent.setup();
    const onRunCreateCostPlan = vi.fn();
    const onSelectWorkflow = vi.fn();

    render(
      <ProjectControlBoard
        project={blockedProject}
        latestDraft={null}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan={false}
        selectedWorkflowId="cost-plan"
        onSelectWorkflow={onSelectWorkflow}
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={onRunCreateCostPlan}
        onRunSortFiles={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
      />,
    );

    expect(
      screen.getByText("Create Cost Plan is blocked by missing overlays."),
    ).toBeInTheDocument();
    expect(screen.getByText("building_class: missing")).toBeInTheDocument();
    expect(screen.getByText("work_type: missing")).toBeInTheDocument();

    const runButton = screen.getByRole("button", { name: /create cost plan/i });
    expect(runButton).toBeDisabled();
    await user.click(runButton);
    expect(onRunCreateCostPlan).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /set project profile/i }));
    expect(onSelectWorkflow).toHaveBeenCalledWith("project-profile");
  });

  it("disables Create/Refresh Cost Plan when the capability is unsupported even though overlays are ready", async () => {
    const user = userEvent.setup();
    const onRunCreateCostPlan = vi.fn();

    render(costPlanBoard(costPlanUnsupportedProject, { onRunCreateCostPlan }));

    expect(project.overlay_status.ready).toBe(true);
    expect(costPlanUnsupportedProject.overlay_status.ready).toBe(true);
    expect(
      screen.getByText(
        "Cost Plan reference-data coverage is currently residential only.",
      ),
    ).toBeInTheDocument();

    const createButton = screen.getByRole("button", { name: /create cost plan/i });
    expect(createButton).toBeDisabled();
    await user.click(createButton);
    expect(onRunCreateCostPlan).not.toHaveBeenCalled();

    expect(screen.getByRole("button", { name: /refresh cost plan/i })).toBeDisabled();
  });

  it("keeps Create Cost Plan enabled when the capability is supported", () => {
    render(costPlanBoard(costPlanSupportedProject));

    expect(screen.getByRole("button", { name: /create cost plan/i })).toBeEnabled();
  });

  it("keeps Create Cost Plan enabled when the project has no capability matrix at all", () => {
    render(costPlanBoard({ ...project, workflow_capabilities: null }));

    expect(screen.getByRole("button", { name: /create cost plan/i })).toBeEnabled();
  });

  it("shows one progress strip while Project Plan runs and hides Pi is working copy", async () => {
    render(
      <ProjectControlBoard
        project={project}
        latestDraft={draftSummary}
        latestCostPlanDraft={null}
        trace={[{ step: "plan", status: "running", message: "working", metadata: {} }]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow
        isRunningCostPlan={false}
        pmpRunMode="update"
        pmpProgressKey="pmp-session-1"
        activeWorkflowRun={runningWorkflowRun}
        selectedWorkflowId="create-pmp"
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={vi.fn()}
        onRunSortFiles={vi.fn()}
        onCancelWorkflow={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
      />,
    );

    expect(screen.getByTestId("workflow-progress-strip")).toHaveTextContent(
      "Updating Project Plan",
    );
    expect(screen.queryByText("Pi is working…")).not.toBeInTheDocument();
    expect(screen.queryByText("working…")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create pmp/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /update pmp/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /create pmp/i })).toHaveTextContent(
      "Create PMP",
    );
    expect(screen.getByRole("button", { name: /create pmp/i })).not.toHaveTextContent(
      "Running",
    );
    expect(screen.queryByRole("button", { name: /review draft/i })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /accept pmp/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  function runningPmpBoard(run: WorkflowRun) {
    return (
      <ProjectControlBoard
        project={project}
        latestDraft={draftSummary}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow
        isRunningCostPlan={false}
        pmpRunMode="create"
        pmpProgressKey="pmp-session-1"
        activeWorkflowRun={run}
        selectedWorkflowId="create-pmp"
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={vi.fn()}
        onRunSortFiles={vi.fn()}
        onCancelWorkflow={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
      />
    );
  }

  it("shows the document taking shape once the run publishes a scaffold", async () => {
    render(
      runningPmpBoard({
        ...runningWorkflowRun,
        progress: {
          stage: "executing",
          percent: 50,
          preview: {
            stage: "scaffold",
            markdown: "## 1. Project Summary\n\nScaffolded content.",
          },
        },
      }),
    );

    const preview = await screen.findByTestId("workflow-draft-preview");
    expect(preview).toHaveTextContent("1. Project Summary");
    expect(preview).toHaveTextContent("Drafting");
  });

  it("keeps the progress strip alongside the building draft", () => {
    render(
      runningPmpBoard({
        ...runningWorkflowRun,
        progress: {
          stage: "executing",
          percent: 50,
          preview: { stage: "scaffold", markdown: "## 1. Project Summary" },
        },
      }),
    );

    expect(screen.getByTestId("workflow-progress-strip")).toBeInTheDocument();
  });

  it("shows the existing draft until the run publishes its first preview", async () => {
    render(runningPmpBoard(runningWorkflowRun));

    expect(screen.queryByTestId("workflow-draft-preview")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /accept pmp/i })).toBeInTheDocument();
  });

  it("shows the cost plan taking shape once its run publishes a scaffold", async () => {
    render(
      <ProjectControlBoard
        project={costPlanSupportedProject}
        latestDraft={null}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan
        costPlanRunMode="create"
        costPlanProgressKey="cost-session-1"
        activeCostPlanRun={{
          ...runningWorkflowRun,
          workflow_type: "create_cost_plan",
          progress: {
            stage: "executing",
            percent: 50,
            preview: { stage: "scaffold", markdown: "## 1. Cost Summary" },
          },
        }}
        selectedWorkflowId="cost-plan"
        onRunCreatePmp={vi.fn()}
        onRunUpdatePmp={vi.fn()}
        onRunCreateCostPlan={vi.fn()}
        onRunRefreshCostPlan={vi.fn()}
        onRunSortFiles={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
      />,
    );

    expect(await screen.findByTestId("workflow-draft-preview")).toHaveTextContent(
      "1. Cost Summary",
    );
  });

  it("shows the cost workbook directly under Cost Plan actions", async () => {
    render(costPlanBoard(costPlanSupportedProject));

    expect(screen.queryByRole("button", { name: /review draft/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cost workbook" })).toBeInTheDocument();
    expect(
      await screen.findByText("Create cost plan to generate the workbook."),
    ).toBeInTheDocument();
  });

  it("surfaces invoice conflicts, review items, and extraction errors", async () => {
    render(
      costPlanBoard(costPlanSupportedProject, {
        latestCostPlanDraft: {
          ...draftSummary,
          workflow_type: "create_cost_plan",
          title: "Cost Plan",
        },
        invoiceProcessResult: {
          candidate_count: 4,
          pending_ingest_count: 1,
          booked_invoice_count: 1,
          register_row_count: 1,
          duplicate_count: 0,
          conflict_count: 1,
          review_count: 1,
          extraction_error_count: 1,
          conflicts: ["conflict"],
          review_items: ["review"],
          extraction_errors: ["extraction"],
          cost_plan_version: 6,
          workbook_path: null,
          draft_id: null,
        },
      }),
    );

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("1 conflict requires review");
    expect(status).toHaveTextContent("1 allocation needs review");
    expect(status).toHaveTextContent("1 invoice could not be extracted");
    expect(status).toHaveTextContent(
      "1 invoice upload is still ingesting; run Process invoices again when ready",
    );
  });
});

const project: ProjectDetail = {
  id: "project-1",
  slug: "demo",
  title: "Demo Project",
  workspace_path: "04-projects/demo",
  phase: "brief-planning",
  archetype: "small-commercial",
  building_class: "commercial",
  work_type: "refurb",
  state: "NSW",
  profile_revision: 1,
  status: "active",
  overlay_status: {
    ready: true,
    missing: [],
    invalid: [],
  },
  updated_at: "2026-07-05T00:00:00.000Z",
  metadata: {
    taxonomy: {
      subclasses: ["office"],
      complexity: { operational_constraints: "live_environment" },
    },
  },
  evidence_preview: null,
  risk_flags: [
    {
      value: "live_operations",
      severity: "info",
      title: "Live Operational Environment",
      description: "Works in live environments require careful staging.",
    },
  ],
};

const blockedProject: ProjectDetail = {
  ...project,
  archetype: null,
  building_class: null,
  work_type: null,
  overlay_status: {
    ready: false,
    missing: [
      { field: "building_class", value: null, reason: "missing" },
      { field: "work_type", value: null, reason: "missing" },
    ],
    invalid: [],
  },
  metadata: {},
  risk_flags: [],
};

const unsupportedCostPlanCapability: WorkflowCapability = {
  status: "unsupported",
  reasons: ["Cost Plan reference-data coverage is currently residential only."],
  required_fields: [],
};

const costPlanUnsupportedProject: ProjectDetail = {
  ...project,
  building_class: "industrial",
  work_type: "new-build",
  workflow_capabilities: {
    schema_version: 1,
    snapshot_schema_version: 1,
    snapshot_content_fingerprint: "a".repeat(64),
    capabilities: { create_cost_plan: unsupportedCostPlanCapability },
  },
};

const costPlanSupportedProject: ProjectDetail = {
  ...project,
  workflow_capabilities: {
    schema_version: 1,
    snapshot_schema_version: 1,
    snapshot_content_fingerprint: "a".repeat(64),
    capabilities: {
      create_cost_plan: { status: "supported", reasons: [], required_fields: [] },
    },
  },
};

const draftSummary = {
  id: "draft-1",
  project_id: project.id,
  workflow_type: "create_pmp",
  version: 1,
  status: "draft",
  title: "Project Plan",
  workspace_path: "04-projects/demo/project-plan.md",
  author_user_id: "user-1",
  model: null,
  runtime: "workflow",
  created_at: "2026-07-05T00:00:00.000Z",
  updated_at: "2026-07-05T00:00:00.000Z",
};

const runningWorkflowRun: WorkflowRun = {
  id: "run-1",
  project_id: project.id,
  requested_by_user_id: "user-1",
  requested_by_thread_id: null,
  requested_by_turn_id: null,
  workflow_type: "create_pmp",
  idempotency_key: "key-1",
  schema_version: 1,
  frozen_profile_revision: 1,
  frozen_snapshot_fingerprint: "b".repeat(64),
  frozen_evidence_fingerprint: "c".repeat(64),
  frozen_decision_set_revision: 0,
  frozen_selection_revision: null,
  frozen_artefact_version: null,
  state: "running",
  attempt: 1,
  max_attempts: 1,
  cancel_requested: false,
  progress: { stage: "executing", percent: 50 },
  stage_durations_ms: {},
  result_artefact_id: null,
  result_reference: null,
  error_class: null,
  error_message: null,
  created_at: "2026-07-05T00:00:00.000Z",
  started_at: "2026-07-05T00:00:01.000Z",
  completed_at: null,
  updated_at: "2026-07-05T00:00:01.000Z",
};

function costPlanBoard(
  projectValue: ProjectDetail,
  overrides: {
    onRunCreateCostPlan?: () => void;
    latestCostPlanDraft?: DraftArtifactSummary | null;
    invoiceProcessResult?: ProcessInvoicesResult | null;
  } = {},
) {
  return (
    <ProjectControlBoard
      project={projectValue}
      latestDraft={null}
      latestCostPlanDraft={overrides.latestCostPlanDraft ?? null}
      trace={[]}
      costPlanTrace={[]}
      workflowError={null}
      costPlanWorkflowError={null}
      isRunningWorkflow={false}
      isRunningCostPlan={false}
      selectedWorkflowId="cost-plan"
      onRunCreatePmp={vi.fn()}
      onRunUpdatePmp={vi.fn()}
      onRunCreateCostPlan={overrides.onRunCreateCostPlan ?? vi.fn()}
      onRunRefreshCostPlan={vi.fn()}
      invoiceProcessResult={overrides.invoiceProcessResult}
      onRunSortFiles={vi.fn()}
      onOpenTenderComparison={vi.fn()}
      inboxCount={0}
      sortFilesResult={null}
      sortFilesDraft={null}
      sortFilesError={null}
      isRunningSortFiles={false}
    />
  );
}

function profileBoard(
  projectValue: ProjectDetail,
  onProjectUpdated = vi.fn(),
) {
  return (
    <ProjectControlBoard
      project={projectValue}
      latestDraft={null}
      latestCostPlanDraft={null}
      trace={[]}
      costPlanTrace={[]}
      workflowError={null}
      costPlanWorkflowError={null}
      isRunningWorkflow={false}
      isRunningCostPlan={false}
      selectedWorkflowId="project-profile"
      onRunCreatePmp={vi.fn()}
      onRunUpdatePmp={vi.fn()}
      onRunCreateCostPlan={vi.fn()}
      onRunSortFiles={vi.fn()}
      onOpenTenderComparison={vi.fn()}
      inboxCount={0}
      sortFilesResult={null}
      sortFilesDraft={null}
      sortFilesError={null}
      isRunningSortFiles={false}
      onProjectUpdated={onProjectUpdated}
    />
  );
}
