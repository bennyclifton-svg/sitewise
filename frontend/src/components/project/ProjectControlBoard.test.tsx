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
    const updatedProject = {
      ...project,
      metadata: {
        taxonomy: {
          subclasses: [{ value: "other", label: "Laboratory office" }],
          complexity: { operational_constraints: "live_environment" },
        },
      },
    };
    vi.mocked(api.updateProject).mockResolvedValue(updatedProject);

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
        onSelectWorkflow={vi.fn()}
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

    await user.click(screen.getByLabelText("Other"));
    await user.type(screen.getByLabelText("Other subclass"), "Laboratory office");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        building_class: "commercial",
        work_type: "refurb",
        subclasses: [{ value: "other", label: "Laboratory office" }],
        complexity: { operational_constraints: "live_environment" },
      }),
    );
    expect(onProjectUpdated).toHaveBeenCalledWith(updatedProject);
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
