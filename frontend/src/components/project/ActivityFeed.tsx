import {
  AlertTriangle,
  Check,
  CircleDashed,
  ExternalLink,
  FileText,
  FolderOpen,
  LoaderCircle,
  Upload,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { useProjectActivity } from "@/lib/queries/project-activity";
import type {
  ProjectActivityRun,
  WorkflowTraceEvent,
} from "@/lib/types/project";

const STALLED_AFTER_MS = 5 * 60 * 1000;

export function ActivityFeed({
  projectId,
  onSelectWorkspacePath,
  onOpenWorkflow,
}: {
  projectId: string;
  onSelectWorkspacePath: (path: string) => void;
  onOpenWorkflow: (workflowId: string) => void;
}) {
  const { data, isLoading, error } = useProjectActivity(projectId);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const runs = data?.runs ?? [];

  if (isLoading) {
    return (
      <div className="px-1.5 py-2 text-xs text-muted-foreground">
        Loading activity
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-1.5 py-2 text-xs text-destructive">
        Activity unavailable
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div className="px-1.5 py-2 text-xs text-muted-foreground">
        No activity yet
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 px-0.5 py-1">
      {runs.map((run) => {
        const expanded = expandedRunId === run.run_id;
        const displayStatus = displayRunStatus(run);
        return (
          <div key={run.run_id} className="border-b border-border/70 pb-1 last:border-b-0">
            <div className="flex min-w-0 items-center gap-1.5">
              <button
                type="button"
                className="flex min-h-8 min-w-0 flex-1 items-center gap-1.5 rounded-sm px-1.5 py-1 text-left transition-colors hover:bg-muted/70"
                aria-expanded={expanded}
                onClick={() =>
                  setExpandedRunId((current) =>
                    current === run.run_id ? null : run.run_id,
                  )
                }
              >
                <RunIcon source={run.source} status={displayStatus} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium">
                    {runTitle(run)}
                  </span>
                  <span className="block truncate text-[0.65rem] text-muted-foreground">
                    {statusLabel(displayStatus)} - {relativeTime(run.updated_at)}
                  </span>
                </span>
              </button>
              {runTarget(run) ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Open activity target"
                  title="Open target"
                  onClick={() => openRunTarget(run, onSelectWorkspacePath, onOpenWorkflow)}
                >
                  <ExternalLink className="size-3" aria-hidden />
                </Button>
              ) : null}
            </div>
            {expanded ? (
              <div className="mt-1 px-1">
                <WorkflowTracePanel
                  trace={run.events.map(traceEvent)}
                  isRunning={displayStatus === "running"}
                  emptyMessage="No steps recorded."
                />
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function RunIcon({
  source,
  status,
}: {
  source: string;
  status: string;
}) {
  if (status === "running") {
    return <LoaderCircle className="size-3.5 shrink-0 animate-spin text-[var(--wf-info-text)]" aria-hidden />;
  }
  if (status === "failed" || status === "blocked" || status === "stalled") {
    return <AlertTriangle className="size-3.5 shrink-0 text-destructive" aria-hidden />;
  }
  if (status === "complete" || status === "completed" || status === "done") {
    return <Check className="size-3.5 shrink-0 text-[var(--wf-ok-text)]" aria-hidden />;
  }
  if (source === "document_ingest") {
    return <Upload className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />;
  }
  if (source === "sort_files") {
    return <FolderOpen className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />;
  }
  if (source === "create_pmp" || source === "create_cost_plan") {
    return <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />;
  }
  return <CircleDashed className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />;
}

function displayRunStatus(run: ProjectActivityRun): string {
  if (isTerminalStatus(run.status)) return run.status;
  const updated = Date.parse(run.updated_at);
  if (Number.isFinite(updated) && Date.now() - updated > STALLED_AFTER_MS) {
    return "stalled";
  }
  return "running";
}

function isTerminalStatus(status: string): boolean {
  return [
    "blocked",
    "cancelled",
    "canceled",
    "complete",
    "completed",
    "done",
    "failed",
    "refused",
    "skipped",
  ].includes(status);
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    blocked: "Blocked",
    cancelled: "Cancelled",
    canceled: "Cancelled",
    complete: "Complete",
    completed: "Complete",
    done: "Complete",
    failed: "Failed",
    refused: "Refused",
    running: "Running",
    skipped: "Skipped",
    stalled: "Stalled",
  };
  return labels[status] ?? status;
}

function runTitle(run: ProjectActivityRun): string {
  const filename = metadataText(run, "filename");
  const title = metadataText(run, "title");
  const sourceLabel = sourceTitle(run.source);
  if (filename) return `${sourceLabel}: ${filename}`;
  if (title) return `${sourceLabel}: ${title}`;
  return sourceLabel;
}

function sourceTitle(source: string): string {
  const labels: Record<string, string> = {
    create_cost_plan: "Create Cost Plan",
    create_pmp: "Create PMP",
    document_ingest: "Document Ingest",
    sort_files: "Sort Files",
    tender: "Tender",
  };
  return labels[source] ?? source.replaceAll("_", " ");
}

function metadataText(run: ProjectActivityRun, key: string): string | null {
  for (const event of [...run.events].reverse()) {
    const value = event.metadata[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

function traceEvent(event: {
  step: string;
  status: string;
  message: string;
  metadata: Record<string, unknown>;
}): WorkflowTraceEvent {
  return {
    step: event.step,
    status: event.status,
    message: event.message,
    metadata: event.metadata,
  };
}

function runTarget(run: ProjectActivityRun): string | null {
  return metadataText(run, "workspace_path") ?? workflowTarget(run.source);
}

function workflowTarget(source: string): string | null {
  if (source === "create_pmp") return "create-pmp";
  if (source === "create_cost_plan") return "cost-plan";
  if (source === "sort_files" || source === "document_ingest") return "document-intake";
  if (source === "tender") return "procurement";
  return null;
}

function openRunTarget(
  run: ProjectActivityRun,
  onSelectWorkspacePath: (path: string) => void,
  onOpenWorkflow: (workflowId: string) => void,
) {
  const workspacePath = metadataText(run, "workspace_path");
  if (workspacePath) {
    onSelectWorkspacePath(workspacePath);
    return;
  }
  const workflowId = workflowTarget(run.source);
  if (workflowId) onOpenWorkflow(workflowId);
}

function relativeTime(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "";
  const seconds = Math.round((timestamp - Date.now()) / 1000);
  const absolute = Math.abs(seconds);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (absolute < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}
