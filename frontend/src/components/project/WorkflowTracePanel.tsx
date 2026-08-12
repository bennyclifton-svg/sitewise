import { Check, CheckCircle2, CircleDashed, LoaderCircle, ShieldAlert } from "lucide-react";

import type { WorkflowTraceEvent } from "@/lib/types/project";

export function WorkflowTracePanel({
  trace,
  isRunning = false,
  embedded = false,
}: {
  trace: WorkflowTraceEvent[];
  isRunning?: boolean;
  embedded?: boolean;
}) {
  if (!trace.length && !isRunning) {
    return null;
  }

  const complete = !isRunning && trace.length > 0 && trace.every(isSuccessStatus);
  const failed = trace.some((event) => event.status === "failed" || event.status === "blocked");

  return (
    <section
      className={
        embedded
          ? "bg-transparent py-0"
          : "cockpit-signature-card p-4"
      }
      aria-label="Workflow activity"
      aria-live="polite"
    >
      <header
        className={
          embedded
            ? "flex min-h-[22px] items-center gap-2 px-1 text-xs"
            : "mb-3 flex items-center gap-2 border-b pb-3"
        }
      >
        {isRunning ? (
          <LoaderCircle className="size-3.5 shrink-0 animate-spin text-[var(--wf-info-text)]" aria-hidden />
        ) : complete ? (
          <Check className="size-3.5 shrink-0 text-[var(--wf-ok-text)]" strokeWidth={3} aria-hidden />
        ) : failed ? (
          <ShieldAlert className="size-3.5 shrink-0 text-destructive" aria-hidden />
        ) : (
          <CircleDashed className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        )}
        <span className={embedded ? "font-medium" : "text-sm font-semibold"}>
          {isRunning ? "Pi is working…" : complete ? "Run complete" : "Workflow trace"}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">
          {trace.length} {trace.length === 1 ? "step" : "steps"}
        </span>
      </header>

      <ol className={embedded ? "flex flex-col gap-0" : "flex flex-col gap-1.5"}>
        {trace.map((event, index) => {
          const metadataSummary = Object.keys(event.metadata).length
            ? formatMetadataSummary(event.metadata)
            : "";
          return (
            <li
              key={`${event.step}-${index}`}
              className={
                embedded
                  ? "grid min-h-[22px] grid-cols-[0.75rem_auto_minmax(0,1fr)] items-start gap-x-2 px-1 py-0.5 text-xs leading-tight"
                  : metadataSummary
                    ? "grid grid-cols-[auto_auto_minmax(0,1fr)_auto] items-start gap-2 text-xs"
                    : "grid grid-cols-[auto_auto_minmax(0,1fr)] items-start gap-2 text-xs"
              }
              title={metadataSummary || undefined}
            >
              <TraceRowIcon status={event.status} />
              <code
                className={
                  embedded
                    ? "shrink-0 font-mono text-[0.65rem] text-[var(--wf-info-text)]"
                    : "cockpit-trace-tool shrink-0"
                }
              >
                {event.step}
              </code>
              <span
                className={
                  embedded
                    ? "min-w-0 whitespace-normal break-words text-muted-foreground"
                    : "min-w-0 break-words text-muted-foreground"
                }
              >
                {event.message}
              </span>
              {metadataSummary ? (
                <span
                  className={
                    embedded
                      ? "hidden"
                      : "hidden max-w-[14rem] truncate text-right text-[0.65rem] text-muted-foreground sm:block"
                  }
                >
                  {metadataSummary}
                </span>
              ) : null}
            </li>
          );
        })}
        {isRunning ? (
          <li
            className={
              embedded
                ? "flex min-h-[22px] items-center gap-2 px-1 text-xs text-foreground"
                : "flex items-center gap-2 text-xs text-foreground"
            }
          >
            <LoaderCircle className="size-3 shrink-0 animate-spin text-[var(--wf-info-text)]" aria-hidden />
            <span>working…</span>
          </li>
        ) : complete ? (
          <li
            className={
              embedded
                ? "flex min-h-[22px] items-center gap-2 px-1 text-xs font-medium text-[var(--wf-ok-text)]"
                : "flex items-center gap-2 text-xs font-medium text-[var(--wf-ok-text)]"
            }
          >
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

/** Compact inline summary — arrays become counts so chunk refs never blow the row. */
export function formatMetadataSummary(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata);
  const scalars = entries.filter(([, value]) => isScalarMetadata(value));
  const rest = entries.filter(([, value]) => !isScalarMetadata(value));
  return [...scalars, ...rest]
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${formatValue(value)}`)
    .join(" · ");
}

function isScalarMetadata(value: unknown): boolean {
  return value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean";
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return String(value.length);
  if (value === null) return "null";
  if (typeof value === "object") return "object";
  const text = String(value);
  if (text.length > 48) return `${text.slice(0, 45)}…`;
  return text;
}
