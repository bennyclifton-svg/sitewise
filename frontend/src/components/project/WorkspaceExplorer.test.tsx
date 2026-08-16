import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceExplorer } from "@/components/project/WorkspaceExplorer";
import { explorerExpandedPathsKey } from "@/components/project/workflow/workspaceRouting";
import type { WorkspaceTreeNode } from "@/lib/types/project";

const PROJECT_ID = "project-1";

function directory(
  name: string,
  path: string,
  children: WorkspaceTreeNode[] = [],
  documentCount = children.filter((child) => child.kind === "file").length,
): WorkspaceTreeNode {
  return {
    name,
    path,
    kind: "directory",
    description: name,
    document_count: documentCount,
    related_workflows: [],
    children,
  };
}

function file(name: string, path: string): WorkspaceTreeNode {
  return {
    name,
    path,
    kind: "file",
    description: name,
    document_count: 1,
    related_workflows: [],
    children: [],
  };
}

const tree: WorkspaceTreeNode[] = [
  directory("00-brief-pmp", "04-projects/demo/00-brief-pmp", [
    file("PMP.md", "04-projects/demo/00-brief-pmp/PMP.md"),
  ]),
  directory("01-cost", "04-projects/demo/01-cost", [
    file("cost_plan_v01.md", "04-projects/demo/01-cost/cost_plan_v01.md"),
  ]),
];

function renderExplorer(projectId = PROJECT_ID) {
  return render(
    <WorkspaceExplorer
      projectId={projectId}
      tree={tree}
      selectedPath="04-projects/demo/00-brief-pmp/PMP.md"
      onSelectPath={vi.fn()}
      onOpenWorkflow={vi.fn()}
      onViewWorkbench={vi.fn()}
      onViewFolder={vi.fn()}
    />,
  );
}

describe("WorkspaceExplorer", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts with every folder collapsed", () => {
    renderExplorer();

    expect(screen.getByText("00-brief-pmp")).toBeInTheDocument();
    expect(screen.getByText("01-cost")).toBeInTheDocument();
    expect(screen.queryByText("PMP.md")).not.toBeInTheDocument();
    expect(screen.queryByText("cost_plan_v01.md")).not.toBeInTheDocument();
  });

  it("remembers an expanded folder after the tree remounts", async () => {
    const user = userEvent.setup();
    const view = renderExplorer();

    await user.click(screen.getByRole("button", { name: "Expand 00-brief-pmp" }));
    expect(screen.getByText("PMP.md")).toBeInTheDocument();
    expect(screen.queryByText("cost_plan_v01.md")).not.toBeInTheDocument();

    view.unmount();
    renderExplorer();

    expect(screen.getByText("PMP.md")).toBeInTheDocument();
    expect(screen.queryByText("cost_plan_v01.md")).not.toBeInTheDocument();
    expect(window.localStorage.getItem(explorerExpandedPathsKey(PROJECT_ID))).toBe(
      JSON.stringify(["04-projects/demo/00-brief-pmp"]),
    );
  });

  it("does not reuse another project's expanded folders", async () => {
    const user = userEvent.setup();
    const view = renderExplorer();

    await user.click(screen.getByRole("button", { name: "Expand 01-cost" }));
    view.unmount();
    renderExplorer("project-2");

    expect(screen.queryByText("cost_plan_v01.md")).not.toBeInTheDocument();
  });
});
