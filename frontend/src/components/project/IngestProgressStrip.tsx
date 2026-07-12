import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { formatEtaSeconds, type IngestBatchSnapshot } from "@/lib/ingest-progress";

export type IngestUploadStage = "uploading" | "ingesting";

export type IngestUploadProgress = {
  total: number;
  completed: number;
  currentFilename: string | null;
  stage: IngestUploadStage | null;
  failedCount: number;
};

const SNAPSHOT_TICK_MS = 500;

function stageMessage(progress: IngestUploadProgress): string {
  const { total, completed, currentFilename, stage, failedCount } = progress;

  if (completed >= total) {
    const failedSuffix = failedCount > 0 ? ` · ${failedCount} failed` : "";
    return `Finished ingesting ${total} document${total === 1 ? "" : "s"}${failedSuffix}.`;
  }
  if (!currentFilename) {
    return `Preparing ${total} document${total === 1 ? "" : "s"}…`;
  }
  return stage === "ingesting"
    ? `Ingesting ${currentFilename}`
    : `Uploading ${currentFilename}`;
}

export function IngestProgressStrip({
  progress,
  getSnapshot,
}: {
  progress: IngestUploadProgress;
  getSnapshot?: () => IngestBatchSnapshot;
}) {
  const isActive = progress.completed < progress.total;
  // The estimator lives outside React; a timer bumps this counter so the
  // snapshot below is re-read while the batch is active.
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!getSnapshot || !isActive) return;
    const timer = window.setInterval(() => {
      setTick((current) => current + 1);
    }, SNAPSHOT_TICK_MS);
    return () => window.clearInterval(timer);
  }, [getSnapshot, isActive]);

  const snapshot: IngestBatchSnapshot | null = getSnapshot ? getSnapshot() : null;

  const percent = isActive
    ? Math.round((snapshot?.fraction ?? 0) * 100)
    : 100;
  const eta = isActive ? formatEtaSeconds(snapshot?.etaSeconds ?? null) : null;

  return (
    <div
      className="mx-3 mt-3 rounded-md border border-primary/15 bg-primary/5 px-3 py-2 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center gap-2">
        {isActive ? (
          <Loader2
            className="size-3 shrink-0 animate-spin text-primary/70 motion-reduce:animate-none"
            aria-hidden
          />
        ) : null}
        <span className="min-w-0 flex-1 truncate">{stageMessage(progress)}</span>
        {isActive ? (
          <span className="shrink-0 tabular-nums text-[0.65rem] text-muted-foreground/80">
            {progress.completed + 1} of {progress.total}
            {eta ? ` · ${eta}` : ""}
          </span>
        ) : null}
      </div>
      {getSnapshot || !isActive ? (
        <div
          className="mt-2 h-0.5 overflow-hidden rounded-full bg-primary/15"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label="Batch ingest progress"
        >
          <div
            className="h-full rounded-full bg-primary/70 transition-[width] duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}
