import { ApiError } from "@/lib/http";
import type {
  DeleteDraftResponse,
  DraftArtifactSummary,
} from "@/lib/types/project";

const PMP_WORKFLOW_TYPES = new Set(["create_pmp", "update_pmp"]);

export function isPmpWorkflowType(workflowType: string): boolean {
  return PMP_WORKFLOW_TYPES.has(workflowType);
}

export function repositoryArtefactDrafts(
  drafts: Array<DraftArtifactSummary | null | undefined>,
): DraftArtifactSummary[] {
  const byId = new Map<string, DraftArtifactSummary>();
  let pmp: DraftArtifactSummary | null = null;
  for (const draft of drafts) {
    if (!draft || draft.workflow_type === "sort_files") continue;
    if (isPmpWorkflowType(draft.workflow_type)) {
      pmp = preferPmpDraft(pmp, draft);
      continue;
    }
    if (!byId.has(draft.id)) byId.set(draft.id, draft);
  }
  const rows = [...byId.values()];
  if (pmp) rows.push(pmp);
  return rows;
}

export function artefactMapKey(workflowType: string): string {
  return isPmpWorkflowType(workflowType) ? "create_pmp" : workflowType;
}

export function applyArtefactDeleted(
  current: Record<string, DraftArtifactSummary | null>,
  result: DeleteDraftResponse,
): Record<string, DraftArtifactSummary | null> {
  const isPmp = isPmpWorkflowType(result.workflow_type);
  const next: Record<string, DraftArtifactSummary | null> = {};
  for (const [key, draft] of Object.entries(current)) {
    if (draft?.id === result.deleted_id) continue;
    if (isPmp && (key === "create_pmp" || key === "update_pmp")) continue;
    next[key] = draft;
  }
  if (result.latest_draft) {
    const key = artefactMapKey(result.latest_draft.workflow_type);
    next[key] = result.latest_draft;
  }
  return next;
}

export function missingDraftDeleteResult(
  draft: Pick<DraftArtifactSummary, "id" | "workflow_type">,
): DeleteDraftResponse {
  return {
    deleted_id: draft.id,
    workflow_type: draft.workflow_type,
    latest_draft: null,
  };
}

export function isDraftNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

function preferPmpDraft(
  current: DraftArtifactSummary | null,
  incoming: DraftArtifactSummary,
): DraftArtifactSummary {
  if (!current) return incoming;
  if (incoming.version !== current.version) {
    return incoming.version > current.version ? incoming : current;
  }
  if (incoming.updated_at !== current.updated_at) {
    return incoming.updated_at > current.updated_at ? incoming : current;
  }
  return incoming.id === current.id ? current : incoming;
}
