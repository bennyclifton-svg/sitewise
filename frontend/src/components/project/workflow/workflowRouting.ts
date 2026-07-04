import type { WorkspaceTreeNode } from "@/lib/types/project";

/** Maps SiteWise template `related_workflows` slugs to cockpit control-board tile ids. */
const WORKFLOW_SLUG_TO_TILE: Record<string, string> = {
  create_pmp: "create-pmp",
  update_pmp: "create-pmp",
  create_cost_plan: "cost-plan",
  consultant_procurement: "design",
  design_review: "design",
  rft: "procurement",
  tender_evaluation: "procurement",
  tender_recommendation: "procurement",
  programme: "delivery",
  risk_register: "risk-register",
  rfi: "rfis",
  process_variations: "variations",
  payment_claims: "variations",
  sort_files: "document-intake",
};

const IMPLEMENTED_TILES = new Set(["create-pmp", "cost-plan", "document-intake"]);

const DRAFT_WORKFLOW_TILES = new Set(["create-pmp", "cost-plan"]);

export function resolveWorkflowTileId(relatedWorkflows: string[]): string | null {
  for (const slug of relatedWorkflows) {
    const tileId = WORKFLOW_SLUG_TO_TILE[slug];
    if (tileId && IMPLEMENTED_TILES.has(tileId)) {
      return tileId;
    }
  }
  for (const slug of relatedWorkflows) {
    const tileId = WORKFLOW_SLUG_TO_TILE[slug];
    if (tileId) return tileId;
  }
  return null;
}

export function handleWorkspaceNodeSelect(
  node: WorkspaceTreeNode,
  callbacks: {
    onSelectPath: (path: string) => void;
    onOpenWorkflow: (tileId: string) => void;
    onViewWorkbench: () => void;
    onViewFolder: () => void;
  },
): void {
  callbacks.onSelectPath(node.path);
  if (node.kind === "file") {
    return;
  }

  const tileId = resolveWorkflowTileId(node.related_workflows);
  if (tileId) {
    callbacks.onOpenWorkflow(tileId);
    if (!DRAFT_WORKFLOW_TILES.has(tileId)) {
      callbacks.onViewWorkbench();
    }
    return;
  }
  callbacks.onViewFolder();
}
