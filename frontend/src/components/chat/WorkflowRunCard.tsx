import { useQuery } from "@tanstack/react-query";

import { ArtefactCard } from "@/components/chat/ArtefactCard";
import { api } from "@/lib/api";
import type { WorkflowRunRef } from "@/lib/chat-events";
import {
  isTerminalWorkflowRun,
  useWorkflowRun,
} from "@/lib/queries/workflow-runs";

type WorkflowRunCardProps = {
  runRef: WorkflowRunRef;
  projectId?: string | null;
};

function titleForWorkflowType(workflowType: string | undefined): string {
  if (!workflowType) return "Workflow";
  if (
    workflowType === "consultant_procurement" ||
    workflowType.startsWith("consultant_procurement_")
  ) {
    return "Request for Proposal";
  }
  if (workflowType === "create_project_plan" || workflowType === "create_pmp") {
    return "Project Plan";
  }
  if (workflowType === "refresh_project_plan") {
    return "Project Plan refresh";
  }
  if (workflowType === "create_cost_plan" || workflowType === "refresh_cost_plan") {
    return "Cost Plan";
  }
  if (workflowType === "sort_project_files" || workflowType === "sort_files") {
    return "File sort";
  }
  return workflowType.replaceAll("_", " ");
}

export function WorkflowRunCard({ runRef, projectId }: WorkflowRunCardProps) {
  const resolvedProjectId = projectId ?? runRef.projectId;
  const { data: run, isError, error } = useWorkflowRun(
    resolvedProjectId,
    runRef.runId,
  );

  const draftId = run?.result_artefact_id ?? null;
  const draftQuery = useQuery({
    queryKey: ["project", resolvedProjectId, "draft", draftId ?? "pending"],
    queryFn: () => api.getProjectDraft(resolvedProjectId, draftId as string),
    enabled: Boolean(
      resolvedProjectId && draftId && run && isTerminalWorkflowRun(run) && run.state === "complete",
    ),
  });

  const workflowType = run?.workflow_type ?? runRef.workflowType;
  const label = titleForWorkflowType(workflowType);

  if (isError) {
    return (
      <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
        Could not load workflow status
        {error instanceof Error && error.message ? `: ${error.message}` : "."}
      </div>
    );
  }

  // In-flight progress is owned by ActivityStream (one cube, one status stack).
  if (!run || !isTerminalWorkflowRun(run)) {
    return null;
  }

  if (run.state === "failed" || run.state === "cancelled") {
    return (
      <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
        {label} {run.state}
        {run.error_message ? `: ${run.error_message}` : "."}
      </div>
    );
  }

  if (run.state === "needs_input") {
    return (
      <div className="mt-3 rounded-md border bg-muted/30 p-3 text-sm">
        {label} needs more project details before it can finish.
      </div>
    );
  }

  if (!draftId) {
    return (
      <div className="mt-3 rounded-md border bg-muted/30 p-3 text-sm">
        {label} completed.
      </div>
    );
  }

  const draft = draftQuery.data;
  return (
    <ArtefactCard
      projectId={resolvedProjectId}
      artefact={{
        kind: "artefact",
        title: draft?.title ?? label,
        workflowType: draft?.workflow_type ?? workflowType,
        draftId,
        projectId: resolvedProjectId,
        version: draft?.version,
      }}
    />
  );
}
