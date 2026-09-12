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

    expect(screen.queryByText("PROJECT")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Project: Newtown Heritage Extension" }),
    ).toHaveTextContent("Newtown Heritage Extension");
  });

  it("puts create project first and keeps a long list scrollable", async () => {
    const user = userEvent.setup();
    const manyProjects = Array.from({ length: 24 }, (_, index) => ({
      ...activeProject,
      id: `project-${index + 1}`,
      slug: `project-${index + 1}`,
      title: index === 0 ? activeProject.title : `Project ${index + 1}`,
    }));

    render(
      <MemoryRouter>
        <ProjectSwitcher projects={manyProjects} activeProject={activeProject} />
      </MemoryRouter>,
    );

    await user.click(
      screen.getByRole("button", { name: "Project: Newtown Heritage Extension" }),
    );

    const items = screen.getAllByRole("menuitem").map((item) => item.textContent);
    expect(items[0]).toBe("Create project");
    expect(items[1]).toBe("All projects");
    expect(items.at(-1)).toBe("Project 24");

    const menu = screen.getByRole("menu");
    expect(menu.className).toMatch(/max-h-\[var\(--radix-dropdown-menu-content-available-height\)\]/);
    expect(menu.querySelector(".overflow-y-auto")).not.toBeNull();
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
