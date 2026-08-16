import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import type { ProjectSummary } from "@/lib/types/project";

const activeProject: ProjectSummary = {
  id: "project-1",
  slug: "newtown-heritage-extension",
  title: "Newtown Heritage Extension",
  workspace_path: "04-projects/newtown-heritage-extension",
  phase: "brief-planning",
  archetype: null,
  building_class: "residential",
  work_type: "extend",
  state: "NSW",
  profile_revision: 1,
  status: "active",
  overlay_status: { ready: true, missing: [], invalid: [] },
  updated_at: "2026-08-15T00:00:00Z",
};

function renderSwitcher(onRename?: (title: string) => Promise<void>) {
  return render(
    <MemoryRouter>
      <ProjectSwitcher
        projects={[activeProject]}
        activeProject={activeProject}
        onRename={onRename}
      />
    </MemoryRouter>,
  );
}

describe("ProjectSwitcher", () => {
  it("shows the full project name without a nav-row spacer", () => {
    renderSwitcher();

    expect(screen.getByText("PROJECT")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Project: Newtown Heritage Extension" }),
    ).toHaveTextContent("Newtown Heritage Extension");
  });

  it("renames the active project from the switcher menu", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn().mockResolvedValue(undefined);
    renderSwitcher(onRename);

    await user.click(
      screen.getByRole("button", { name: "Project: Newtown Heritage Extension" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Rename project" }));

    const input = screen.getByLabelText("Project name");
    await user.clear(input);
    await user.type(input, "41 George Street{enter}");

    expect(onRename).toHaveBeenCalledWith("41 George Street");
  });
});
