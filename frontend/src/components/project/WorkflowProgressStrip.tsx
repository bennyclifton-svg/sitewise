import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  formatEtaSeconds,
  resolveWorkflowDisplayStage,
  WorkflowRunEstimator,
  type WorkflowProgressKind,
  WORKFLOW_BUDGET_SECONDS_DEFAULT,
} from "@/lib/workflow-progress";

const SNAPSHOT_TICK_MS = 500;

export type WorkflowProgressStripProps = {
  title: string;
  kind: WorkflowProgressKind;
  /** Stable id for the active run; estimator resets when it changes. */
  runId: string;
  runState?: string | null;
  progressStage?: string | null;
  onCancel?: () => void;
  /** Optional clock injection for tests. */
  now?: () => number;
  budgetSeconds?: number;
};

export function WorkflowProgressStrip({
  runId,
  ...props
}: WorkflowProgressStripProps) {
  return <WorkflowProgressStripRun key={runId} runId={runId} {...props} />;
}

function WorkflowProgressStripRun({
  title,
  kind,
  runId,
  runState = null,
  progressStage = null,
  onCancel,
  now,
  budgetSeconds = WORKFLOW_BUDGET_SECONDS_DEFAULT,
}: WorkflowProgressStripProps) {
  const [estimator] = useState(
    () =>
      new WorkflowRunEstimator({
        budgetSeconds,
        now,
        startedAtMs: now?.(),
      }),
  );
  const [nowMs, setNowMs] = useState(() => now?.() ?? Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowMs(now?.() ?? Date.now());
    }, SNAPSHOT_TICK_MS);
    return () => window.clearInterval(timer);
  }, [now, runId]);

  const snapshot = estimator.snapshot();
  const percent = Math.round(snapshot.fraction * 100);
  const eta = formatEtaSeconds(snapshot.etaSeconds);
  const stage = resolveWorkflowDisplayStage({
    kind,
    backendStage: progressStage,
    runState,
    elapsedSeconds: estimator.elapsedSeconds(),
    budgetSeconds,
    nowMs,
  });

  return (
    <div
      className="rounded-md border border-primary/15 bg-primary/5 px-3 py-2 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
      aria-atomic="true"
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
      <div className="mt-2 flex items-center gap-2">
        <div
          className="h-0.5 min-w-0 flex-1 overflow-hidden rounded-full bg-primary/15"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={`${title} progress`}
        >
          <div
            className="h-full rounded-full bg-primary/70 transition-[width] duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
        <span className="shrink-0 tabular-nums text-[0.65rem] text-muted-foreground/80">
          {percent}%
          {eta ? ` · ${eta}` : ""}
        </span>
      </div>
    </div>
  );
}
