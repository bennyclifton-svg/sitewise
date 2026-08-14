import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import { api } from "@/lib/api";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  ProcessInvoicesResult,
  ProjectDetail,
  TaxonomyCatalog,
  WorkflowCapability,
  WorkflowRun,
} from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    applyCostPlanOperations: vi.fn(),
    getCostPlanState: vi.fn(),
    getInvoiceLedger: vi.fn(),
    getProject: vi.fn(),
    updateProject: vi.fn(),
    listProcurementRequests: vi.fn(),
    getLatestDraft: vi.fn(),
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
  work_scopes: {
    refurb: {
      categories: [
        {
          value: "building_services",
          label: "Building Services",
          items: [
            {
              value: "vertical_transport",
              label: "Vertical Transport",
              consultants: ["Services Engineer"],
            },
          ],
        },
      ],
    },
  },
  emphasis_profiles: { sections: [], base_weights: {}, modifiers: [] },
};

describe("ProjectControlBoard project profile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCostPlanState).mockResolvedValue({
      version: 1,
      items: [],
      totals: {
        budget: "0.00",
        committed: "0.00",
        forecast: "0.00",
        paid: "0.00",
        variance: "0.00",
        total_excluding_gst: "0.00",
        total_including_gst: "0.00",
      },
    });
    vi.mocked(api.getInvoiceLedger).mockResolvedValue({
      cost_plan_version: 1,
      workbook_path: "cost-plan.xlsx",
      rows: [],
      cost_items: [],
    });
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
        budget: null,
        scope_narrative: [],
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
          budget: null,
          scope_narrative: [],
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
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: "NSW",
        site_address: null,
        client: null,
        budget: null,
        scope_narrative: [],
      }),
    );
    expect(onProjectUpdated).toHaveBeenCalledWith(updatedProject);
  });

  it("does not save when the profile has no unsaved changes", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    render(profileBoard(project, onProjectUpdated));

    const saveButton = screen.getByRole("button", { name: "Save profile" });
    expect(saveButton).toBeDisabled();
    expect(saveButton).toHaveAttribute("title", "No unsaved changes");
    await user.click(saveButton);
    expect(api.updateProject).not.toHaveBeenCalled();
    expect(onProjectUpdated).not.toHaveBeenCalled();
  });

  it("saves budget and scope notes from the project profile panel", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    vi.mocked(api.updateProject).mockResolvedValue({
      profile: {
        project_id: project.id,
        profile_revision: 2,
        building_class: project.building_class,
        work_type: project.work_type,
        subclasses: ["office"],
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: project.state,
        site_address: null,
        client: null,
        budget: "$120m",
        scope_narrative: [
          "New lifts",
          "Footbridge",
          "Accessible platforms and canopies",
          "Work in possessions",
        ],
      },
      previous_revision: 1,
      new_revision: 2,
      changed_fields: ["budget", "scope_narrative"],
      cleared_fields: [],
      overlay_status: project.overlay_status,
      risk_flags: project.risk_flags,
    });

    render(profileBoard(project, onProjectUpdated));

    await user.type(screen.getByLabelText("Budget"), "$120m");
    await user.type(
      screen.getByLabelText("Scope notes"),
      "New lifts{enter}Footbridge{enter}Accessible platforms and canopies{enter}Work in possessions",
    );
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        expected_revision: 1,
        building_class: "commercial",
        work_type: "refurb",
        subclasses: ["office"],
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: "NSW",
        site_address: null,
        client: null,
        budget: "$120m",
        scope_narrative: [
          "New lifts",
          "Footbridge",
          "Accessible platforms and canopies",
          "Work in possessions",
        ],
      }),
    );
  });

  it("keeps the overlay banner and hides Saved when work type is still missing", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    const overlay = {
      ready: false,
      missing: [{ field: "work_type", value: null, reason: "missing" }],
      invalid: [],
    };
    vi.mocked(api.updateProject).mockResolvedValue({
      profile: {
        project_id: blockedProject.id,
        profile_revision: 2,
        building_class: "commercial",
        work_type: null,
        subclasses: [],
        scale: {},
        complexity: {},
        work_scope: [],
        state: "NSW",
        site_address: null,
        client: null,
      },
      previous_revision: 1,
      new_revision: 2,
      changed_fields: ["building_class"],
      cleared_fields: [],
      overlay_status: overlay,
      risk_flags: [],
    });

    render(profileBoard(blockedProject, onProjectUpdated));

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith(
        "project-1",
        expect.objectContaining({
          building_class: "commercial",
          work_type: null,
        }),
      ),
    );
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
    expect(screen.getByText("Project overlays are incomplete.")).toBeInTheDocument();
    expect(screen.getByText("work type: missing")).toBeInTheDocument();
  });

  it("asks to save when class and work type are selected but not yet persisted", async () => {
    const user = userEvent.setup();
    render(profileBoard(blockedProject, vi.fn()));

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    await user.click(screen.getByRole("button", { name: "Refurbishment" }));

    expect(
      screen.getByText("Save profile to apply these overlays."),
    ).toBeInTheDocument();
    expect(screen.queryByText("work type: missing")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save profile" })).toBeEnabled();
  });

  it("persists explicit dependent-field clears when the building class changes", async () => {
    const user = userEvent.setup();
    const residentialCatalog: TaxonomyCatalog = {
      ...catalog,
      building_classes: [
        {
          value: "residential",
          label: "Residential",
          multi_subclass: false,
          work_types: ["new", "refurb"],
          subclasses: [
            {
              value: "apartments",
              label: "Apartments",
              ncc_class: "2",
              scale_fields: [],
            },
          ],
        },
        ...catalog.building_classes,
      ],
      complexity_dimensions: {
        ...catalog.complexity_dimensions,
        residential: [],
      },
    };
    vi.mocked(useTaxonomy).mockReturnValue({
      data: residentialCatalog,
      error: null,
    } as unknown as ReturnType<typeof useTaxonomy>);
    vi.mocked(api.updateProject).mockResolvedValue({
      profile: {
        project_id: project.id,
        profile_revision: 2,
        building_class: "residential",
        work_type: "refurb",
        subclasses: [],
        scale: {},
        complexity: {},
        work_scope: [],
        state: "NSW",
        site_address: null,
        client: null,
      },
      previous_revision: 1,
      new_revision: 2,
      changed_fields: ["building_class"],
      cleared_fields: ["subclasses", "complexity"],
      overlay_status: project.overlay_status,
      risk_flags: [],
    });

    render(profileBoard(project, vi.fn()));

    await user.click(screen.getByRole("button", { name: "Residential" }));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        expected_revision: 1,
        building_class: "residential",
        work_type: "refurb",
        subclasses: [],
        scale: {},
        complexity: {},
        work_scope: [],
        state: "NSW",
        site_address: null,
        client: null,
        budget: null,
        scope_narrative: [],
      }),
    );
  });

  it("creates a trade RFT from the consolidated tender panel", async () => {
    const user = userEvent.setup();
    const onRunProcurement = vi.fn();
    vi.mocked(api.listProcurementRequests).mockResolvedValue([]);
    vi.mocked(api.getLatestDraft).mockResolvedValue(null);

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

    await screen.findByText("No requests yet. Create the first one above.");
    await user.click(screen.getByLabelText("Request type"));
    await user.click(screen.getByRole("menuitem", { name: "Trade package" }));
    await user.type(screen.getByLabelText("Discipline"), "Electrical services");
    await user.click(
      screen.getByRole("button", { name: "Create Trade package" }),
    );

    expect(onRunProcurement).toHaveBeenCalledWith(
      "trade_rft",
      "Electrical services",
    );
  });

  it("updates clean controls when a newer server revision arrives", () => {
    const view = render(profileBoard(project));

    expect(screen.getByLabelText("State")).toHaveTextContent("NSW");
    view.rerender(
      profileBoard({ ...project, profile_revision: 2, state: "VIC" }),
    );

    expect(screen.getByLabelText("State")).toHaveTextContent("VIC");
    expect(
      screen.queryByText("Project profile changed elsewhere."),
    ).not.toBeInTheDocument();
  });

  it("preserves dirty controls until the user reloads the newer revision", async () => {
    const user = userEvent.setup();
    const view = render(profileBoard(project));
    await user.click(screen.getByLabelText("State"));
    await user.click(screen.getByRole("menuitem", { name: "QLD" }));

    view.rerender(
      profileBoard({ ...project, profile_revision: 2, state: "VIC" }),
    );

    expect(screen.getByLabelText("State")).toHaveTextContent("QLD");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Revision 2 arrived while you had unsaved edits.",
    );
    expect(screen.getByRole("button", { name: "Save profile" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Reload latest" }));
    expect(screen.getByLabelText("State")).toHaveTextContent("VIC");
    expect(
      screen.queryByText("Project profile changed elsewhere."),
    ).not.toBeInTheDocument();
  });

  it("rebases only edited fields when the user keeps editing", async () => {
    const user = userEvent.setup();
    const onProjectUpdated = vi.fn();
    const view = render(profileBoard(project, onProjectUpdated));
    await user.click(screen.getByLabelText("State"));
    await user.click(screen.getByRole("menuitem", { name: "QLD" }));
    const newerProject = {
      ...project,
      profile_revision: 2,
      state: "VIC",
    };
    view.rerender(profileBoard(newerProject, onProjectUpdated));

    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(screen.getByLabelText("State")).toHaveTextContent("QLD");

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
        scale: {},
        complexity: { operational_constraints: "live_environment" },
        work_scope: [],
        state: "QLD",
        site_address: null,
        client: null,
        budget: null,
        scope_narrative: [],
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

  it("keeps Project Plan and Cost Plan on the same workbench frame gutters", () => {
    const { unmount } = render(
      <ProjectControlBoard
        project={project}
        latestDraft={draftSummary}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan={false}
        selectedWorkflowId="create-pmp"
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
      />,
    );
    const projectPlanFrame = screen.getByTestId("workbench-frame");
    expect(projectPlanFrame).toHaveClass("w-full", "min-w-0", "p-4", "lg:p-6");
    expect(projectPlanFrame).not.toHaveClass("max-w-6xl");
    const projectPlanClasses = projectPlanFrame.className;
    unmount();

    render(costPlanBoard(project));
    const costPlanFrame = screen.getByTestId("workbench-frame");
    expect(costPlanFrame.className).toBe(projectPlanClasses);
    expect(costPlanFrame).not.toHaveClass("max-w-none");
  });

  it("keeps Create/Update PMP enabled without a top-of-panel progress strip", async () => {
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

    expect(screen.queryByTestId("workflow-progress-strip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workflow-draft-preview")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create pmp/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /update pmp/i })).toBeEnabled();
    expect(await screen.findByText("Trace & QA")).toBeInTheDocument();
  });

  function pmpBoard() {
    return (
      <ProjectControlBoard
        project={project}
        latestDraft={draftSummary}
        latestCostPlanDraft={null}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan={false}
        selectedWorkflowId="create-pmp"
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
      />
    );
  }

  it("copies the complete PMP from the top control without workflow metadata", async () => {
    const user = userEvent.setup();
    const documentMarkdown = [
      "# Project Management Plan",
      "",
      "## Citation key",
      "",
      "- [P1] Project brief",
    ].join("\n");
    const getProjectDraft = vi.fn().mockResolvedValue({
      ...draftSummary,
      content_markdown: documentMarkdown,
      provenance_metadata: {
        trace: [
          {
            step: "compose",
            status: "complete",
            message: "This workflow trace is not document content.",
            metadata: {},
          },
        ],
      },
    } as DraftArtifact);
    Object.assign(api, { getProjectDraft });

    try {
      render(pmpBoard());

      await user.click(
        screen.getByRole("button", { name: "Copy project management plan" }),
      );

      await waitFor(async () => {
        expect(await navigator.clipboard.readText()).toBe(documentMarkdown);
      });
      expect(await navigator.clipboard.readText()).not.toContain(
        "This workflow trace is not document content.",
      );
    } finally {
      Reflect.deleteProperty(api, "getProjectDraft");
    }
  });

  it("downloads Word and PDF from a single download callout beside copy", async () => {
    const user = userEvent.setup();
    const downloadDraftExport = vi.fn().mockResolvedValue(new Blob(["export"]));
    Object.assign(api, { downloadDraftExport });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });

    try {
      render(pmpBoard());

      expect(screen.queryByRole("button", { name: "Copy for Word" })).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", {
          name: "Download project management plan as Word",
        }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", {
          name: "Download project management plan as PDF",
        }),
      ).not.toBeInTheDocument();

      await user.click(
        screen.getByRole("button", { name: "Download project management plan" }),
      );
      await user.click(await screen.findByRole("menuitem", { name: "Word" }));
      await waitFor(() => {
        expect(downloadDraftExport).toHaveBeenCalledWith(
          "project-1",
          draftSummary.id,
          "docx",
        );
      });

      await user.click(
        screen.getByRole("button", { name: "Download project management plan" }),
      );
      await user.click(await screen.findByRole("menuitem", { name: "PDF" }));
      await waitFor(() => {
        expect(downloadDraftExport).toHaveBeenCalledWith(
          "project-1",
          draftSummary.id,
          "pdf",
        );
      });
      expect(
        screen.getByRole("button", { name: "Copy project management plan" }),
      ).toBeInTheDocument();
    } finally {
      Reflect.deleteProperty(api, "downloadDraftExport");
    }
  });

  it("keeps Cost Plan actions available without a top-of-panel progress strip", () => {
    render(
      <ProjectControlBoard
        project={costPlanSupportedProject}
        latestDraft={null}
        latestCostPlanDraft={{
          ...draftSummary,
          workflow_type: "create_cost_plan",
          title: "Prior Cost Plan",
        }}
        trace={[]}
        costPlanTrace={[]}
        workflowError={null}
        costPlanWorkflowError={null}
        isRunningWorkflow={false}
        isRunningCostPlan
        costPlanRunMode="update"
        costPlanProgressKey="cost-session-2"
        activeCostPlanRun={{
          ...runningWorkflowRun,
          workflow_type: "refresh_cost_plan",
          progress: { stage: "retrieval_complete" },
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

    expect(screen.queryByTestId("workflow-progress-strip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workflow-draft-preview")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cost-plan-running-placeholder")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create cost plan/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /refresh cost plan/i })).toBeEnabled();
  });

  it("shows the cost workbook directly under Cost Plan actions", async () => {
    render(costPlanBoard(costPlanSupportedProject));

    expect(screen.queryByRole("button", { name: /review draft/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Cost workbook" })).not.toBeInTheDocument();
    expect(
      await screen.findByText("Create cost plan to open the editable Cost Plan grid."),
    ).toBeInTheDocument();
  });

  it("downloads Excel from a single download callout beside copy", async () => {
    const user = userEvent.setup();
    const getProjectDraft = vi.fn().mockResolvedValue({
      ...draftSummary,
      workflow_type: "create_cost_plan",
      title: "Cost Plan",
      content_markdown: "# Cost Plan",
      provenance_metadata: {
        workbook: {
          file_name: "Cost_Plan_v02.draft.xlsx",
          workspace_path: "04-projects/demo/01-cost/Cost_Plan_v02.draft.xlsx",
        },
      },
    });
    const downloadWorkspaceFile = vi.fn().mockResolvedValue(new Blob(["xlsx"]));
    Object.assign(api, { getProjectDraft, downloadWorkspaceFile });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });

    try {
      render(
        costPlanBoard(costPlanSupportedProject, {
          latestCostPlanDraft: {
            ...draftSummary,
            workflow_type: "create_cost_plan",
            title: "Cost Plan",
          },
        }),
      );

      expect(screen.queryByRole("button", { name: "Download Excel" })).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Download cost plan as Excel" }),
      ).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Download cost plan" }));
      await user.click(await screen.findByRole("menuitem", { name: "Excel" }));
      await waitFor(() => {
        expect(getProjectDraft).toHaveBeenCalledWith("project-1", "draft-1");
        expect(downloadWorkspaceFile).toHaveBeenCalledWith(
          "project-1",
          "04-projects/demo/01-cost/Cost_Plan_v02.draft.xlsx",
        );
      });
      expect(screen.getByRole("button", { name: "Copy cost plan" })).toBeInTheDocument();
    } finally {
      Reflect.deleteProperty(api, "getProjectDraft");
      Reflect.deleteProperty(api, "downloadWorkspaceFile");
    }
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
  frozen_project_context_version: 1,
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
