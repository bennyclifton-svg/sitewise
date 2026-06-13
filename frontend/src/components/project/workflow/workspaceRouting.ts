import type { WorkspaceTreeNode } from "@/lib/types/project";

/** True when the explorer path points at a PMP draft workspace file. */
export function isPmpWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/00-brief-pmp\/PMP(\.md|-draft-v\d+\.md)$/i.test(normalised);
}

/** True when the explorer path points at a cost plan draft markdown file. */
export function isCostPlanWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/01-cost\/cost_plan_v\d+\.md$/i.test(normalised);
}

/** Expand folders that contain files and any ancestor of the selected path. */
export function collectExplorerExpandPaths(
  tree: WorkspaceTreeNode[],
  selectedPath: string | null,
): Set<string> {
  const expanded = new Set<string>();
  const normalisedSelected = selectedPath?.replaceAll("\\", "/") ?? null;

  function visit(nodes: WorkspaceTreeNode[]) {
    for (const node of nodes) {
      if (node.kind === "file") continue;

      const hasFileChildren = node.children.some((child) => child.kind === "file");
      const onSelectedBranch =
        normalisedSelected !== null &&
        (normalisedSelected === node.path ||
          normalisedSelected.startsWith(`${node.path}/`));

      if (hasFileChildren || onSelectedBranch || node.document_count > 0) {
        expanded.add(node.path);
      }
      visit(node.children);
    }
  }

  visit(tree);
  return expanded;
}
