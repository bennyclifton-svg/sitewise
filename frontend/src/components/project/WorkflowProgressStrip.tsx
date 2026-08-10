import { Check, Circle, Loader2, TriangleAlert } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  resolveWorkflowDisplayStage,
  workflowRunPercent,
  workflowSectionProgress,
  type WorkflowProgressKind,
} from "@/lib/workflow-progress";
import { markWorkflowStage } from "@/lib/performance";

export type WorkflowProgressStripProps = {
  title: string;
  kind: WorkflowProgressKind;
  runId: string;
  runState?: string | null;
  progressStage?: string | null;
  progress?: Record<string, unknown> | null;
  onCancel?: () => void;
};

export function WorkflowProgressStrip({
  title,
  kind,
  runId,
  runState = null,
  progressStage = null,
  progress = null,
  onCancel,
}: WorkflowProgressStripProps) {
  const sections = workflowSectionProgress(progress);
  const percent = workflowRunPercent(progress);
  const stage = resolveWorkflowDisplayStage({
    kind,
    backendStage: progressStage,
    runState,
    progress,
  });
  useEffect(() => {
    markWorkflowStage(runId, progressStage ?? runState ?? "running");
  }, [progressStage, runId, runState]);

  return (
    <div
      className="rounded-md border border-primary/15 bg-primary/5 px-3 py-2 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-run-id={runId}
      data-testid="workflow-progress-strip"
    >
      <div className="flex items-start gap-2">
        <Loader2
          className="mt-0.5 size-3 shrink-0 animate-spin text-primary/70 motion-reduce:animate-none"
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-foreground">{title}</p>
          <p className="mt-0.5 truncate">{stage.message}</p>
        </div>
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 shrink-0 px-2 text-xs"
            onClick={onCancel}
          >
            Cancel
          </Button>
        ) : null}
      </div>

      {sections ? (
        <ul className="mt-2 grid gap-1 sm:grid-cols-3" aria-label="Document sections">
          {sections.sections.map((section) => (
            <li key={section.id} className="flex min-w-0 items-center gap-1">
              {section.status === "complete" ? (
                <Check className="size-3 shrink-0 text-primary" aria-hidden />
              ) : section.status === "failed" ? (
                <TriangleAlert className="size-3 shrink-0 text-destructive" aria-hidden />
              ) : section.status === "generating" ? (
                <Loader2 className="size-3 shrink-0 animate-spin text-primary" aria-hidden />
              ) : (
                <Circle className="size-2.5 shrink-0 text-muted-foreground/50" aria-hidden />
              )}
              <span className="truncate">{section.label}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-2 flex items-center gap-2">
        <div
          className="h-0.5 min-w-0 flex-1 overflow-hidden rounded-full bg-primary/15"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent ?? undefined}
          aria-label={`${title} progress`}
        >
          <div
            className={
              percent === null
                ? "h-full w-1/3 animate-pulse rounded-full bg-primary/70 motion-reduce:animate-none"
                : "h-full rounded-full bg-primary/70 transition-[width] duration-300 ease-out"
            }
            style={percent === null ? undefined : { width: `${percent}%` }}
          />
        </div>
        {percent !== null ? (
          <span className="shrink-0 tabular-nums text-[0.65rem] text-muted-foreground/80">
            {sections
              ? `${sections.completed}/${sections.total} sections`
              : `${percent}%`}
          </span>
        ) : null}
      </div>
    </div>
  );
}
