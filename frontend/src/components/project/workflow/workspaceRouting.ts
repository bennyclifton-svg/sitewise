import type { DraftArtifactSummary } from "@/lib/types/project";

/** True when the explorer path points at a PMP draft workspace file. */
export function isPmpWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/00-brief-pmp\/PMP(\.md|-draft-v\d+\.md)$/i.test(normalised);
}

/** True when the explorer path points at a Cost Plan revision export. */
export function isCostPlanWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/01-cost\/(?:cost_plan_v\d+\.md|Cost_Plan_v\d+\.draft\.xlsx)$/i.test(normalised);
}

/** True when the explorer path points at a consultant procurement RFP draft. */
export function isConsultantProcurementWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/02-consultant\/consultant_procurement_.+_v\d+\.draft\.md$/i.test(normalised);
}

/** True when the explorer path points at a contractor EOI draft. */
export function isContractorEoiWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/02-procurement\/contractor_eoi_.+_v\d+\.draft\.md$/i.test(normalised);
}

/** True when the explorer path points at a trade RFT or RFQ draft. */
export function isTradeProcurementWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/05-procurement\/[^/]+\/02-tender-pack\/[^/]+_(?:rft|rfq)_v\d+\.draft\.md$/i.test(
    normalised,
  );
}

/** True when a workspace file is backed by a generated draft artefact. */
export function isDraftArtifactWorkspaceFile(path: string): boolean {
  return (
    isPmpWorkspaceFile(path) ||
    isCostPlanWorkspaceFile(path) ||
    isConsultantProcurementWorkspaceFile(path) ||
    isContractorEoiWorkspaceFile(path) ||
    isTradeProcurementWorkspaceFile(path)
  );
}

export function findDraftByWorkspacePath(
  drafts: Record<string, DraftArtifactSummary | null>,
  path: string,
): DraftArtifactSummary | null {
  const normalised = path.replaceAll("\\", "/");
  for (const draft of Object.values(drafts)) {
    if (!draft) continue;
    if (draft.workspace_path.replaceAll("\\", "/") === normalised) {
      return draft;
    }
    const costPlanWorkbook = normalised.match(
      /^(.*\/01-cost)\/Cost_Plan_v(\d+)\.draft\.xlsx$/i,
    );
    if (
      costPlanWorkbook &&
      draft.workflow_type === "create_cost_plan" &&
      draft.version === Number(costPlanWorkbook[2]) &&
      draft.workspace_path.replaceAll("\\", "/").startsWith(`${costPlanWorkbook[1]}/`)
    ) {
      return draft;
    }
  }
  return null;
}

export const EXPLORER_EXPANDED_PATHS_KEY_PREFIX = "clerk.workspace-explorer.expanded";

export function explorerExpandedPathsKey(projectId: string): string {
  return `${EXPLORER_EXPANDED_PATHS_KEY_PREFIX}:${projectId}`;
}

/** Restore the folders the user left open. Missing or invalid storage is collapsed. */
export function readExplorerExpandedPaths(projectId: string): Set<string> {
  try {
    const raw = localStorage.getItem(explorerExpandedPathsKey(projectId));
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((item): item is string => typeof item === "string"));
  } catch {
    return new Set();
  }
}

export function writeExplorerExpandedPaths(projectId: string, paths: Set<string>): void {
  try {
    const key = explorerExpandedPathsKey(projectId);
    if (paths.size === 0) {
      localStorage.removeItem(key);
      return;
    }
    localStorage.setItem(key, JSON.stringify([...paths]));
  } catch {
    // Ignore quota or private-mode storage failures.
  }
}
