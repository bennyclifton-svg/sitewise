import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import { api } from "@/lib/api";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import type { ProjectDetail, TaxonomyCatalog } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    updateProject: vi.fn(),
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

  it("renders risk chips and saves taxonomy edits", async () => {
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
        user_role: project.user_role,
        state: project.state,
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
        },
      },
    };
    vi.mocked(api.updateProject).mockResolvedValue(updatedChange);

    render(
      <ProjectControlBoard
        project={project}
        evidence={[]}
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
        onOpenDraft={vi.fn()}
        onOpenTenderComparison={vi.fn()}
        inboxCount={0}
        sortFilesResult={null}
        sortFilesDraft={null}
        sortFilesError={null}
        isRunningSortFiles={false}
        onProjectUpdated={onProjectUpdated}
      />,
    );

    expect(screen.getByText("Live Operational Environment")).toHaveAttribute(
      "title",
      "Works in live environments require careful staging.",
    );
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
        user_role: "architect-pm",
        state: "NSW",
      }),
    );
    expect(onProjectUpdated).toHaveBeenCalledWith(updatedProject);
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
      user_role: "owner-builder",
    };
    view.rerender(profileBoard(newerProject, onProjectUpdated));

    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(screen.getByLabelText("State")).toHaveValue("QLD");
    expect(screen.getByLabelText("Your role")).toHaveValue("owner-builder");

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
        user_role: "owner-builder",
        state: "QLD",
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
        user_role: "owner-builder",
        state: "QLD",
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
        evidence={[]}
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
        onOpenDraft={vi.fn()}
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
  user_role: "architect-pm",
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

function profileBoard(
  projectValue: ProjectDetail,
  onProjectUpdated = vi.fn(),
) {
  return (
    <ProjectControlBoard
      project={projectValue}
      evidence={[]}
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
      onOpenDraft={vi.fn()}
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
