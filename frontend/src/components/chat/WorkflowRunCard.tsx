import { useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";

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
    return "Request for Tender";
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

function progressPercent(progress: Record<string, unknown> | undefined): number | null {
  const percent = progress?.percent;
  return typeof percent === "number" ? Math.max(0, Math.min(100, percent)) : null;
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

  if (!run || !isTerminalWorkflowRun(run)) {
    const percent = progressPercent(run?.progress);
    const stage =
      run?.state === "running"
        ? "Generating"
        : run?.state === "queued"
          ? "Queued"
          : "Preparing";
    return (
      <div
        className="mt-3 flex items-center gap-3 rounded-md border bg-muted/30 p-3"
        role="status"
        aria-live="polite"
      >
        <LoaderCircle
          className="size-4 shrink-0 animate-spin text-muted-foreground"
          aria-hidden
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            {stage} {label}
            {percent !== null ? ` (${Math.round(percent)}%)` : "…"}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            Draft will open here when ready.
          </p>
        </div>
      </div>
    );
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
