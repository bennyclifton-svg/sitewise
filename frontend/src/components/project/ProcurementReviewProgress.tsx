import { Check, Circle, TriangleAlert } from "lucide-react";

import { CubeTumbleMark } from "@/components/chat/StreamingIndicator";
import { Button } from "@/components/ui/button";
import type { ProcurementReviewRun } from "@/lib/types/procurement-review";
import { cn } from "@/lib/utils";

type Props = {
  run?: ProcurementReviewRun;
  connectionIssue: boolean;
  unavailable: boolean;
  checking: boolean;
  lastUpdated: number;
  retrying: boolean;
  retryError: string | null;
  onCheck: () => void;
  onRetry: () => void;
};

const documentStates = {
  queued: "Waiting",
  opening: "Opening file",
  reading: "Reading",
  retrying: "Retry scheduled",
  waiting: "Waiting to resume",
  complete: "Read",
  failed: "Needs attention",
};

function titleFor(run: ProcurementReviewRun | undefined, connectionIssue: boolean, unavailable: boolean) {
  if (unavailable) return "Comparison unavailable";
  if (!run) return connectionIssue ? "Waiting for a status update" : "Connecting to comparison";
  if (run.phase === "failed") return "Review needs attention";
  if (connectionIssue) return "Waiting for a status update";
  if (run.phase === "complete") return "Opening recommendation";
  if (run.activity === "retrying") return "Retrying from saved progress";
  if (run.activity === "queued") return run.documents.some((doc) => doc.pages_read > 0) ? "Waiting to continue" : "Waiting to start";
  if (run.activity === "waiting") return "Waiting for processing to resume";
  if (run.phase === "preparing") return "Preparing recommendation";
  return run.documents.some((doc) => doc.state === "opening") && !run.documents.some((doc) => doc.state === "reading") ? "Opening submissions" : "Reading submissions";
}

export function ProcurementReviewProgress({
  run, connectionIssue, unavailable, checking, lastUpdated, retrying, retryError, onCheck, onRetry,
}: Props) {
  const documents = run?.documents ?? [];
  const allRead = documents.length > 0 && documents.every((doc) => doc.complete);
  const totalKnown = documents.length > 0 && documents.every((doc) => doc.pages !== null && doc.pages > 0);
  const totalPages = documents.reduce((sum, doc) => sum + (doc.pages ?? 0), 0);
  const readPages = documents.reduce((sum, doc) => sum + doc.pages_read, 0);
  const finished = documents.filter((doc) => doc.complete).length;
  const failed = run?.phase === "failed";
  const stages = [
    { label: "Read submissions", done: allRead, current: Boolean(run) && !allRead },
    { label: "Prepare recommendation", done: run?.phase === "complete", current: allRead && run?.phase !== "complete" },
    { label: "Report ready", done: run?.phase === "complete", current: false },
  ];
  const updatedTime = lastUpdated ? new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(lastUpdated) : null;

  return <div className="max-w-2xl space-y-6 py-6">
    <div className="flex items-start gap-4">
      {failed || unavailable ? <TriangleAlert className="mt-1 size-6 shrink-0 text-muted-foreground" aria-hidden /> : <CubeTumbleMark />}
      <div className="min-w-0 space-y-2">
        <h2 className="text-lg font-medium" aria-live="polite" aria-atomic="true">{titleFor(run, connectionIssue, unavailable)}</h2>
        {run && <p className="text-sm text-muted-foreground break-words">{run.package_name}</p>}
        <p className="max-w-prose text-sm text-muted-foreground">
          {unavailable ? "This comparison could not be accessed. Return to Procurement to reopen it."
            : failed ? run.error
            : !run ? "Checking the saved comparison status."
            : connectionIssue ? "Waiting to reconnect to the saved comparison."
            : run.activity === "queued" ? "The next stage is queued. Saved progress will update when processing continues."
            : run.activity === "waiting" ? "No recent processing activity has been confirmed. Saved progress is shown below."
            : run.activity === "retrying" ? "The review will retry using its saved progress."
            : run.phase === "preparing" ? "Comparing prices and scope, checking the figures and preparing your report."
            : "Reading each file and checking prices against the source pages. Large submissions can take several minutes."}
        </p>
      </div>
    </div>

    {connectionIssue && !unavailable && <div className="border-y py-3 text-sm" role="status">
      <p>{run ? "Showing the last saved progress. Live updates are temporarily unavailable." : "Status updates are temporarily unavailable. This does not confirm that the comparison has stopped."}</p>
      {updatedTime && <p className="mt-1 text-xs text-muted-foreground">Last update received at {updatedTime}.</p>}
      <Button variant="link" className="mt-1 h-auto px-0" disabled={checking} onClick={onCheck}>{checking ? "Checking…" : "Check again"}</Button>
    </div>}

    {run && <>
      <ol aria-label="Comparison stages" className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3 sm:gap-5">
        {stages.map((stage) => <li key={stage.label} aria-current={stage.current ? "step" : undefined} className={cn("flex items-center gap-2 border-t pt-3", stage.current ? "font-medium" : "text-muted-foreground")}>
          {stage.done ? <Check className="size-4 shrink-0" aria-hidden /> : <Circle className={cn("size-3 shrink-0", stage.current && "fill-current text-primary")} aria-hidden />}
          <span>{stage.label}<span className="sr-only"> — {stage.done ? "complete" : stage.current ? "current stage" : "up next"}</span></span>
        </li>)}
      </ol>

      {documents.length > 0 && <div className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm" role="status" aria-live="polite" aria-atomic="true">
          <span className="font-medium">{finished} of {documents.length} {documents.length === 1 ? "file" : "files"} read</span>
          <span className="text-muted-foreground tabular-nums">{totalKnown ? `${readPages} of ${totalPages} pages read` : "Page count available as files open"}</span>
        </div>
        {totalKnown && <div role="progressbar" aria-label="Submission pages read" aria-valuemin={0} aria-valuemax={totalPages} aria-valuenow={readPages} aria-valuetext={`${readPages} of ${totalPages} pages read; recommendation follows`} className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary" style={{ width: `${Math.min(100, readPages / totalPages * 100)}%` }} />
        </div>}
        <ul className="divide-y">
          {documents.map((doc) => <li key={doc.id} className="flex flex-col gap-2 py-3 text-sm sm:flex-row sm:items-start sm:justify-between sm:gap-6">
            <div className="min-w-0">
              <p className="font-medium break-words">{doc.firm_name}</p>
              <p className="mt-0.5 text-muted-foreground [overflow-wrap:anywhere]">{doc.filename}</p>
            </div>
            <div className="shrink-0 text-muted-foreground sm:text-right">
              <p className="flex items-center gap-1.5 sm:justify-end">{doc.complete && <Check className="size-3.5" aria-hidden />}{documentStates[doc.state]}</p>
              {doc.pages !== null && doc.pages > 0 && <p className="mt-0.5 text-xs tabular-nums">{doc.pages_read} of {doc.pages} pages read</p>}
            </div>
          </li>)}
        </ul>
      </div>}

      {failed ? run.can_retry && <Button onClick={onRetry} disabled={retrying}>{retrying ? "Restarting…" : "Retry review"}</Button>
        : <p className="text-sm text-muted-foreground">You can leave this view. Return through Procurement to check progress or open the report.</p>}
    </>}
    {retryError && <p role="alert" className="text-sm text-destructive">{retryError}</p>}
  </div>;
}
