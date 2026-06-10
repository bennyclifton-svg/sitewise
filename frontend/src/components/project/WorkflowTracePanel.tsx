import { Check, CheckCircle2, CircleDashed, LoaderCircle, ShieldAlert } from "lucide-react";

import type { WorkflowTraceEvent } from "@/lib/types/project";

export function WorkflowTracePanel({
  trace,
  isRunning = false,
  emptyMessage = "Workflow trace will appear here after a run.",
}: {
  trace: WorkflowTraceEvent[];
  isRunning?: boolean;
  emptyMessage?: string;
}) {
  if (!trace.length && !isRunning) {
    return (
      <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  const complete = !isRunning && trace.length > 0 && trace.every(isSuccessStatus);
  const failed = trace.some((event) => event.status === "failed" || event.status === "blocked");

  return (
    <section
      className="cockpit-signature-card rounded-lg border bg-card p-4 shadow-sm"
      aria-label="Workflow activity"
      aria-live="polite"
    >
      <header className="mb-3 flex items-center gap-2 border-b pb-3">
        {isRunning ? (
          <LoaderCircle className="size-3.5 shrink-0 animate-spin text-[var(--wf-info-text)]" aria-hidden />
        ) : complete ? (
          <Check className="size-3.5 shrink-0 text-[var(--wf-ok-text)]" strokeWidth={3} aria-hidden />
        ) : failed ? (
          <ShieldAlert className="size-3.5 shrink-0 text-destructive" aria-hidden />
        ) : (
          <CircleDashed className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        )}
        <span className="text-sm font-semibold">
          {isRunning ? "Clerk is working…" : complete ? "Run complete" : "Workflow trace"}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">
          {trace.length} {trace.length === 1 ? "step" : "steps"}
        </span>
      </header>

      <ol className="flex flex-col gap-1.5">
        {trace.map((event, index) => (
          <li key={`${event.step}-${index}`} className="flex items-start gap-2 text-xs">
            <TraceRowIcon status={event.status} />
            <code className="cockpit-trace-tool shrink-0">{event.step}</code>
            <span className="min-w-0 text-muted-foreground">{event.message}</span>
            {Object.keys(event.metadata).length ? (
              <span className="ml-auto hidden shrink-0 text-[0.65rem] text-muted-foreground sm:inline">
                {formatMetadataSummary(event.metadata)}
              </span>
            ) : null}
          </li>
        ))}
        {isRunning ? (
          <li className="flex items-center gap-2 text-xs text-foreground">
            <LoaderCircle className="size-3 shrink-0 animate-spin text-[var(--wf-info-text)]" aria-hidden />
            <span>working…</span>
          </li>
        ) : complete ? (
          <li className="flex items-center gap-2 text-xs font-medium text-[var(--wf-ok-text)]">
            <Check className="size-3 shrink-0" strokeWidth={3} aria-hidden />
            <span>Draft ready for review</span>
          </li>
        ) : null}
      </ol>
    </section>
  );
}

function TraceRowIcon({ status }: { status: string }) {
  if (status === "failed" || status === "blocked") {
    return <ShieldAlert className="mt-0.5 size-3 shrink-0 text-destructive" aria-hidden />;
  }
  if (isSuccessStatus({ status } as WorkflowTraceEvent)) {
    return (
      <Check className="mt-0.5 size-3 shrink-0 text-[var(--wf-ok-text)]" strokeWidth={3} aria-hidden />
    );
  }
  if (status === "running" || status === "started") {
    return (
      <LoaderCircle
        className="mt-0.5 size-3 shrink-0 animate-spin text-[var(--wf-info-text)]"
        aria-hidden
      />
    );
  }
  return <CheckCircle2 className="mt-0.5 size-3 shrink-0 text-muted-foreground" aria-hidden />;
}

function isSuccessStatus(event: WorkflowTraceEvent): boolean {
  return (
    event.status === "complete" ||
    event.status === "completed" ||
    event.status === "passed"
  );
}

function formatMetadataSummary(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata).slice(0, 2);
  return entries.map(([key, value]) => `${key}: ${formatValue(value)}`).join(" · ");
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (value === null) return "null";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
