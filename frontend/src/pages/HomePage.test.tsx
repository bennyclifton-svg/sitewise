import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProjectSummary } from "@/lib/types/project";
import { HomePage } from "@/pages/HomePage";

vi.mock("@/lib/api", () => ({
  api: {
    listProjects: vi.fn(),
    deleteProject: vi.fn(),
    updateProject: vi.fn(),
    getTaxonomy: vi.fn(),
    createProject: vi.fn(),
  },
}));

const project: ProjectSummary = {
  id: "project-1",
  slug: "new-town-extension",
  title: "New Town Extension",
  workspace_path: "04-projects/new-town-extension",
  phase: "brief-planning",
  archetype: null,
  building_class: "residential",
  work_type: "extend",
  state: "NSW",
  status: "active",
  overlay_status: { ready: true, missing: [], invalid: [] },
  updated_at: "2026-08-15T00:00:00Z",
};

function renderHome() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listProjects).mockResolvedValue([project]);
    vi.mocked(api.getTaxonomy).mockResolvedValue({
      building_classes: [],
      work_types: [],
      work_scopes: {},
      complexity: {},
      emphasis_profiles: { sections: [], weights: {}, applicability: {} },
    } as never);
    vi.mocked(api.deleteProject).mockResolvedValue(undefined);
    vi.mocked(api.updateProject).mockResolvedValue({
      profile: {
        project_id: project.id,
        profile_revision: 2,
        title: "Newtown Heritage Extension",
        building_class: project.building_class,
        work_type: project.work_type,
        subclasses: [],
        scale: {},
        complexity: {},
        work_scope: [],
        state: project.state,
        site_address: null,
        client: null,
      },
      previous_revision: 1,
      new_revision: 2,
      changed_fields: ["title"],
      cleared_fields: [],
      overlay_status: project.overlay_status,
      risk_flags: [],
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("deletes a project from the catalog tile menu", async () => {
    const user = userEvent.setup();
    renderHome();

    expect(await screen.findByText("New Town Extension")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Actions for New Town Extension" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() => {
      expect(api.deleteProject).toHaveBeenCalledWith("project-1");
    });
    expect(screen.queryByText("New Town Extension")).not.toBeInTheDocument();
  });

  it("renames a project from the catalog tile menu", async () => {
    const user = userEvent.setup();
    renderHome();

    expect(await screen.findByText("New Town Extension")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Actions for New Town Extension" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Rename" }));

    const input = await screen.findByLabelText("Rename New Town Extension");
    await user.clear(input);
    await user.type(input, "Newtown Heritage Extension{enter}");

    await waitFor(() => {
      expect(api.updateProject).toHaveBeenCalledWith("project-1", {
        expected_revision: 1,
        title: "Newtown Heritage Extension",
      });
    });
    expect(await screen.findByText("Newtown Heritage Extension")).toBeInTheDocument();
  });

  it("keeps the project when delete is cancelled", async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    const user = userEvent.setup();
    renderHome();

    expect(await screen.findByText("New Town Extension")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Actions for New Town Extension" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(api.deleteProject).not.toHaveBeenCalled();
    expect(screen.getByText("New Town Extension")).toBeInTheDocument();
  });

  it("shows a delete constraint error without claiming the catalog is offline", async () => {
    vi.mocked(api.deleteProject).mockRejectedValue(
      new ApiError("Database constraint conflict while saving. Retry the workflow.", {
        kind: "http",
        status: 409,
      }),
    );
    const user = userEvent.setup();
    renderHome();

    expect(await screen.findByText("New Town Extension")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Actions for New Town Extension" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Database constraint conflict while saving. Retry the workflow.",
    );
    expect(
      screen.queryByText("Project catalog API is not reachable."),
    ).not.toBeInTheDocument();
    expect(screen.getByText("New Town Extension")).toBeInTheDocument();
  });
});
