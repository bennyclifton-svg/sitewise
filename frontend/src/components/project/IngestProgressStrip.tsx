import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

export type IngestUploadProgress = {
  total: number;
  completed: number;
  currentFilename: string | null;
  failedCount: number;
};

const PHASE_BUILDERS = [
  (filename: string) => `Uploading ${filename}`,
  (filename: string) => `Extracting content from ${filename}`,
  (filename: string) => `Indexing ${filename}`,
] as const;

const PHASE_CYCLE_MS = 2_200;

type PhaseState = {
  filename: string | null;
  index: number;
};

function progressMessage(progress: IngestUploadProgress, phaseIndex: number): string {
  const { total, completed, currentFilename, failedCount } = progress;

  if (completed >= total) {
    const failedSuffix =
      failedCount > 0
        ? ` · ${failedCount} failed`
        : "";
    return `Finished ingesting ${total} document${total === 1 ? "" : "s"}${failedSuffix}.`;
  }

  if (!currentFilename) {
    return `Preparing ${total} document${total === 1 ? "" : "s"}…`;
  }

  const currentNumber = completed + 1;
  const phase = PHASE_BUILDERS[phaseIndex % PHASE_BUILDERS.length](currentFilename);
  return `${phase} (${currentNumber} of ${total})…`;
}

export function IngestProgressStrip({ progress }: { progress: IngestUploadProgress }) {
  const [phaseState, setPhaseState] = useState<PhaseState>({
    filename: null,
    index: 0,
  });
  const isActive = progress.completed < progress.total;
  const phaseIndex =
    phaseState.filename === progress.currentFilename ? phaseState.index : 0;

  useEffect(() => {
    if (!isActive || !progress.currentFilename) return;
    const timer = window.setInterval(() => {
      setPhaseState((current) => {
        if (current.filename !== progress.currentFilename) {
          return { filename: progress.currentFilename, index: 1 };
        }
        return {
          filename: current.filename,
          index: (current.index + 1) % PHASE_BUILDERS.length,
        };
      });
    }, PHASE_CYCLE_MS);
    return () => window.clearInterval(timer);
  }, [isActive, progress.currentFilename]);

  return (
    <div
      className="mx-3 mt-3 flex items-center gap-2 rounded-md border border-primary/15 bg-primary/5 px-3 py-2 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {isActive ? (
        <Loader2 className="size-3 shrink-0 animate-spin text-primary/70" aria-hidden />
      ) : null}
      <span className="min-w-0 truncate">{progressMessage(progress, phaseIndex)}</span>
    </div>
  );
}
