import {
  ChevronRight,
  Loader2,
  Trash,
} from "lucide-react";
import {
  type KeyboardEvent,
  type MouseEvent,
  useMemo,
  useState,
} from "react";

import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { ApiError } from "@/lib/http";
import {
  useDeleteProjectActivityRuns,
  useProjectActivity,
} from "@/lib/queries/project-activity";
import type {
  ProjectActivityReferences,
  ProjectActivityRun,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

const STALLED_AFTER_MS = 5 * 60 * 1000;
const EMPTY_RUNS: ProjectActivityRun[] = [];

export function ActivityFeed({
  projectId,
}: {
  projectId: string;
}) {
  const { data, isLoading, error } = useProjectActivity(projectId);
  const deleteActivity = useDeleteProjectActivityRuns(projectId);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [selectedRunIds, setSelectedRunIds] = useState<Set<string>>(
    () => new Set<string>(),
  );
  const [selectionAnchorRunId, setSelectionAnchorRunId] = useState<string | null>(
    null,
  );
  const [expandedReferenceRunIds, setExpandedReferenceRunIds] = useState<
    Set<string>
  >(() => new Set<string>());
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const runs = data?.runs ?? EMPTY_RUNS;
  const runIdSet = useMemo(
    () => new Set(runs.map((run) => run.run_id)),
    [runs],
  );
  const selectedRuns = useMemo(
    () => runs.filter((run) => selectedRunIds.has(run.run_id)),
    [runs, selectedRunIds],
  );
  const isDeletingSelection = deleteActivity.isPending;

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "a") {
      return;
    }
    event.preventDefault();
    setSelectedRunIds(new Set(runs.map((run) => run.run_id)));
    setSelectionAnchorRunId(runs[0]?.run_id ?? null);
  }

  function handleRunClick(
    event: MouseEvent<HTMLButtonElement>,
    run: ProjectActivityRun,
  ) {
    setDeleteError(null);
    const additive = event.ctrlKey || event.metaKey;

    if (event.shiftKey) {
      const anchorId =
        selectionAnchorRunId && runIdSet.has(selectionAnchorRunId)
          ? selectionAnchorRunId
          : expandedRunId && runIdSet.has(expandedRunId)
            ? expandedRunId
            : run.run_id;
      const anchorIndex = runs.findIndex((item) => item.run_id === anchorId);
      const runIndex = runs.findIndex((item) => item.run_id === run.run_id);
      if (anchorIndex >= 0 && runIndex >= 0) {
        const start = Math.min(anchorIndex, runIndex);
        const end = Math.max(anchorIndex, runIndex);
        const rangeIds = runs.slice(start, end + 1).map((item) => item.run_id);
        setSelectedRunIds((current) => {
          const next = additive
            ? new Set([...current].filter((id) => runIdSet.has(id)))
            : new Set<string>();
          for (const id of rangeIds) next.add(id);
          return next;
        });
        setSelectionAnchorRunId(anchorId);
        return;
      }
    }

    if (additive) {
      setSelectedRunIds((current) => {
        const next = new Set([...current].filter((id) => runIdSet.has(id)));
        if (next.has(run.run_id)) {
          next.delete(run.run_id);
        } else {
          next.add(run.run_id);
        }
        return next;
      });
    } else {
      setSelectedRunIds(new Set([run.run_id]));
      setExpandedRunId((current) => (current === run.run_id ? null : run.run_id));
    }
    setSelectionAnchorRunId(run.run_id);
  }

  async function handleDeleteRun(run: ProjectActivityRun) {
    if (deleteActivity.isPending) return;

    const confirmed = window.confirm(
      `Delete "${runTitle(run)}"? This removes it from project activity and cannot be undone.`,
    );
    if (!confirmed) return;

    setDeleteError(null);
    try {
      await deleteActivity.mutateAsync([run.run_id]);
      setSelectedRunIds((current) => {
        if (!current.has(run.run_id)) return current;
        const next = new Set(current);
        next.delete(run.run_id);
        return next;
      });
      setSelectionAnchorRunId((current) =>
        current === run.run_id ? null : current,
      );
      setExpandedReferenceRunIds((current) => {
        if (!current.has(run.run_id)) return current;
        const next = new Set(current);
        next.delete(run.run_id);
        return next;
      });
      setExpandedRunId((current) => (current === run.run_id ? null : current));
    } catch (deleteFailure) {
      const detail =
        deleteFailure instanceof ApiError
          ? deleteFailure.message
          : "Please try again.";
      setDeleteError(`Could not delete activity: ${detail}`);
    }
  }

  async function handleDeleteSelected() {
    if (!selectedRuns.length || isDeletingSelection) return;

    const count = selectedRuns.length;
    const confirmed = window.confirm(
      `Delete ${count} selected ${count === 1 ? "activity item" : "activity items"}? This removes ${count === 1 ? "it" : "them"} from project activity and cannot be undone.`,
    );
    if (!confirmed) return;

    const runIds = selectedRuns.map((run) => run.run_id);
    setDeleteError(null);

    try {
      await deleteActivity.mutateAsync(runIds);
      setSelectedRunIds(new Set<string>());
      setSelectionAnchorRunId(null);
      setExpandedReferenceRunIds((current) => {
        const next = new Set(current);
        for (const runId of runIds) next.delete(runId);
        return next;
      });
      setExpandedRunId((current) =>
        current && runIds.includes(current) ? null : current,
      );
    } catch (deleteFailure) {
      const detail =
        deleteFailure instanceof ApiError
          ? deleteFailure.message
          : "Please try again.";
      setDeleteError(`Could not delete selected activity: ${detail}`);
    }
  }

  function toggleReferences(runId: string) {
    setExpandedReferenceRunIds((current) => {
      const next = new Set(current);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  }

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
    <div
      className="relative -mt-0.5 flex flex-col pl-[14px]"
      onKeyDown={handleKeyDown}
    >
      <div className="pointer-events-none absolute -top-[24px] right-0.5 flex h-[22px] items-center justify-end gap-1">
        {selectedRuns.length ? (
          <span className="min-w-0 truncate text-[0.65rem] text-muted-foreground">
            {selectedRuns.length} selected
          </span>
        ) : null}
        <button
          type="button"
          disabled={!selectedRuns.length || isDeletingSelection}
          className="pointer-events-auto inline-flex size-[22px] items-center justify-center rounded-sm text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-35"
          aria-label={
            selectedRuns.length
              ? `Delete ${selectedRuns.length} selected activity ${selectedRuns.length === 1 ? "item" : "items"}`
              : "Delete selected activity"
          }
          title={
            selectedRuns.length
              ? `Delete ${selectedRuns.length} selected`
              : "Select activity to delete"
          }
          onClick={() => void handleDeleteSelected()}
        >
          {isDeletingSelection ? (
            <Loader2 className="size-3.5 animate-spin" aria-hidden />
          ) : (
            <Trash className="size-3.5" aria-hidden />
          )}
        </button>
      </div>
      {deleteError ? (
        <div className="px-1 pb-1 text-[0.65rem] text-destructive">
          {deleteError}
        </div>
      ) : null}
      {runs.map((run) => {
        const expanded = expandedRunId === run.run_id;
        const selected = selectedRunIds.has(run.run_id);
        const displayStatus = displayRunStatus(run);
        const label = activityLine(run, displayStatus);
        const references = activityReferences(run);
        const referencesExpanded = expandedReferenceRunIds.has(run.run_id);
        return (
          <div
            key={run.run_id}
            className={cn(
              "overflow-hidden rounded-sm transition-colors",
              selected || expanded
                ? "bg-primary/10 text-foreground"
                : "text-muted-foreground hover:bg-muted/60",
            )}
          >
            <div className="flex min-w-0 items-center">
              <button
                type="button"
                className={cn(
                  "flex h-[22px] min-w-0 flex-1 select-none items-center gap-1 rounded-none bg-transparent px-1 text-left text-xs transition-colors focus:outline-none focus-visible:outline-none focus-visible:ring-0",
                  selected || expanded ? "text-foreground" : "text-muted-foreground",
                )}
                aria-expanded={expanded}
                aria-pressed={selected}
                title={label}
                onClick={(event) => handleRunClick(event, run)}
              >
                <ChevronRight
                  className={cn(
                    "size-3 shrink-0 text-muted-foreground transition-transform",
                    expanded && "rotate-90",
                  )}
                  aria-hidden
                />
                <span className="min-w-0 flex-1 truncate">
                  <span className="font-medium">{runTitle(run)}</span>
                  <span
                    className={cn(
                      "text-muted-foreground",
                      (selected || expanded) && "text-foreground/70",
                    )}
                  >
                    {" "}
                    - {activitySuffix(displayStatus, run.updated_at)}
                  </span>
                </span>
              </button>
              <button
                type="button"
                disabled={deleteActivity.isPending}
                className="inline-flex size-[22px] shrink-0 items-center justify-center rounded-none text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-35"
                aria-label={`Delete ${runTitle(run)}`}
                title="Delete activity"
                onClick={(event) => {
                  event.stopPropagation();
                  void handleDeleteRun(run);
                }}
              >
                {deleteActivity.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  <Trash className="size-3.5" aria-hidden />
                )}
              </button>
            </div>
            {expanded ? (
              <div className="pl-[18px] pr-[22px]">
                <WorkflowTracePanel
                  embedded
                  trace={run.events.map(traceEvent)}
                  isRunning={displayStatus === "running"}
                />
                {references ? (
                  <ActivityReferenceDisclosure
                    references={references}
                    expanded={referencesExpanded}
                    onToggle={() => toggleReferences(run.run_id)}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function ActivityReferenceDisclosure({
  references,
  expanded,
  onToggle,
}: {
  references: ProjectActivityReferences;
  expanded: boolean;
  onToggle: () => void;
}) {
  const count =
    references.seed_consulted.length +
    references.evidence_refs.length +
    references.context_refs.length;

  return (
    <div className="text-xs">
      <button
        type="button"
        className="flex h-[22px] w-full items-center gap-1 rounded-none px-1 text-left text-muted-foreground transition-colors hover:bg-primary/10 focus:outline-none focus-visible:outline-none focus-visible:ring-0"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        <ChevronRight
          className={cn(
            "size-3 shrink-0 transition-transform",
            expanded && "rotate-90",
          )}
          aria-hidden
        />
        <span className="min-w-0 flex-1 truncate font-medium">References</span>
        <span className="shrink-0 text-[0.65rem] text-muted-foreground">
          {count} {count === 1 ? "ref" : "refs"}
        </span>
      </button>
      {expanded ? (
        <div className="pl-4">
          <ReferenceGroup label="Seeds" items={references.seed_consulted} />
          <ReferenceGroup label="Evidence" items={references.evidence_refs} />
          <ReferenceGroup label="Context" items={references.context_refs} />
        </div>
      ) : null}
    </div>
  );
}

function ReferenceGroup({
  label,
  items,
}: {
  label: string;
  items: string[];
}) {
  return (
    <div className="grid min-h-[22px] grid-cols-[3.75rem_minmax(0,1fr)] gap-2 px-1 py-0.5 text-xs leading-tight">
      <span className="font-medium text-foreground/80">{label}</span>
      <span className="min-w-0 whitespace-normal break-words text-muted-foreground">
        {items.length ? items.join(", ") : "None"}
      </span>
    </div>
  );
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

function activityLine(run: ProjectActivityRun, status: string): string {
  return `${runTitle(run)} - ${activitySuffix(status, run.updated_at)}`;
}

function activitySuffix(status: string, updatedAt: string): string {
  const time = relativeTime(updatedAt);
  if (isCompleteStatus(status)) return time;
  return `${statusLabel(status).toLowerCase()} - ${time}`;
}

function isCompleteStatus(status: string): boolean {
  return status === "complete" || status === "completed" || status === "done";
}

function runTitle(run: ProjectActivityRun): string {
  const filename = metadataText(run, "filename");
  const title = metadataText(run, "title");
  const sourceLabel = sourceTitle(run.source);
  if (filename) return `${sourceLabel} ${filename}`;
  if (title) return `${sourceLabel} ${title}`;
  return sourceLabel;
}

function sourceTitle(source: string): string {
  const labels: Record<string, string> = {
    create_cost_plan: "Cost plan",
    create_pmp: "PMP",
    document_ingest: "Doc ingest",
    sort_files: "Sort",
    tender: "Tender",
    update_pmp: "PMP update",
  };
  return labels[source] ?? source.replaceAll("_", " ");
}

function activityReferences(
  run: ProjectActivityRun,
): ProjectActivityReferences | null {
  const fromRun = normalizeReferences(run.references);
  if (fromRun) return fromRun;

  for (const event of [...run.events].reverse()) {
    const fromMetadata = normalizeReferences({
      seed_consulted: event.metadata.seed_consulted,
      evidence_refs: event.metadata.evidence_refs,
      context_refs: event.metadata.context_refs,
    });
    if (fromMetadata) return fromMetadata;
  }
  return null;
}

function normalizeReferences(value: unknown): ProjectActivityReferences | null {
  if (!value || typeof value !== "object") return null;
  const references = value as Partial<Record<keyof ProjectActivityReferences, unknown>>;
  const normalized = {
    seed_consulted: stringList(references.seed_consulted),
    evidence_refs: stringList(references.evidence_refs),
    context_refs: stringList(references.context_refs),
  };
  if (
    !normalized.seed_consulted.length &&
    !normalized.evidence_refs.length &&
    !normalized.context_refs.length
  ) {
    return null;
  }
  return normalized;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.reduce<string[]>((items, item) => {
    if (typeof item !== "string") return items;
    const trimmed = item.trim();
    if (trimmed) items.push(trimmed);
    return items;
  }, []);
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

function relativeTime(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "";
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
