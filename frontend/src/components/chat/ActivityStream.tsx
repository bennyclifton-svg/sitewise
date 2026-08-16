import { useEffect, useMemo, useRef, useState } from "react";

import { CubeTumbleMark } from "@/components/chat/StreamingIndicator";
import {
  buildActivityLines,
  workflowActivityLine,
  type ActivityLine,
} from "@/lib/activity-stream";
import type { ToolStatusEvent, WorkflowRunRef } from "@/lib/chat-events";
import {
  isTerminalWorkflowRun,
  useWorkflowRun,
} from "@/lib/queries/workflow-runs";
import { cn } from "@/lib/utils";

type ActivityStreamProps = {
  statusMessage?: string | null;
  toolEvents?: ToolStatusEvent[];
  workflowRuns?: WorkflowRunRef[];
  projectId?: string | null;
  /** Parent turn is still streaming/submitted. */
  busy?: boolean;
  /** Reports whether the stream still has visible in-flight work. */
  onPresenceChange?: (active: boolean) => void;
  className?: string;
};

const VISIBLE_LINES = 3;

function WorkflowProgressSubscription({
  runRef,
  projectId,
  onLine,
}: {
  runRef: WorkflowRunRef;
  projectId?: string | null;
  onLine: (runId: string, line: ActivityLine | null, known: boolean) => void;
}) {
  const resolvedProjectId = projectId ?? runRef.projectId;
  const { data: run, isFetched, isError } = useWorkflowRun(
    resolvedProjectId,
    runRef.runId,
  );

  useEffect(() => {
    if (isError) {
      onLine(runRef.runId, null, true);
      return;
    }
    if (!isFetched) {
      onLine(runRef.runId, null, false);
      return;
    }
    if (!run || isTerminalWorkflowRun(run)) {
      onLine(runRef.runId, null, true);
      return;
    }
    onLine(runRef.runId, workflowActivityLine(run, runRef), true);
  }, [isError, isFetched, onLine, run, runRef]);

  return null;
}

export function ActivityStream({
  statusMessage = null,
  toolEvents = [],
  workflowRuns = [],
  projectId = null,
  busy = false,
  onPresenceChange,
  className,
}: ActivityStreamProps) {
  const [workflowLinesById, setWorkflowLinesById] = useState<
    Record<string, ActivityLine>
  >({});
  const [knownRunIds, setKnownRunIds] = useState<Record<string, boolean>>({});
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  const onWorkflowLine = useMemo(() => {
    return (runId: string, line: ActivityLine | null, known: boolean) => {
      setKnownRunIds((current) => {
        if (current[runId] === known) return current;
        return { ...current, [runId]: known };
      });
      setWorkflowLinesById((current) => {
        if (line === null) {
          if (!(runId in current)) return current;
          const next = { ...current };
          delete next[runId];
          return next;
        }
        const existing = current[runId];
        if (
          existing &&
          existing.label === line.label &&
          existing.state === line.state
        ) {
          return current;
        }
        return { ...current, [runId]: line };
      });
    };
  }, []);

  const workflowLines = useMemo(
    () =>
      workflowRuns
        .map((run) => workflowLinesById[run.runId])
        .filter((line): line is ActivityLine => Boolean(line)),
    [workflowLinesById, workflowRuns],
  );

  const lines = useMemo(
    () =>
      buildActivityLines({
        // Clerk status is turn-scoped; tool + workflow lines can outlive the model turn.
        statusMessage: busy ? statusMessage : null,
        toolEvents,
        workflowLines,
        busy,
      }),
    [busy, statusMessage, toolEvents, workflowLines],
  );

  const workflowsPending = workflowRuns.some(
    (run) => knownRunIds[run.runId] !== true,
  );
  const hasInFlightWorkflow = workflowLines.length > 0 || workflowsPending;
  const present = busy || hasInFlightWorkflow;

  useEffect(() => {
    onPresenceChange?.(present);
  }, [onPresenceChange, present]);

  const visible = lines.slice(-VISIBLE_LINES);
  const latestLabel = visible[visible.length - 1]?.label ?? "Working";
  const showUi = busy || workflowLines.length > 0 || workflowsPending;

  useEffect(() => {
    const node = scrollerRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [lines.length, latestLabel]);

  if (!showUi) {
    return (
      <>
        {workflowRuns.map((runRef) => (
          <WorkflowProgressSubscription
            key={runRef.runId}
            runRef={runRef}
            projectId={projectId}
            onLine={onWorkflowLine}
          />
        ))}
      </>
    );
  }

  return (
    <>
      {workflowRuns.map((runRef) => (
        <WorkflowProgressSubscription
          key={runRef.runId}
          runRef={runRef}
          projectId={projectId}
          onLine={onWorkflowLine}
        />
      ))}
      <div
        className={cn(
          "mr-8 flex max-w-[92%] items-end gap-3 self-start text-sm",
          className,
        )}
        role="status"
        aria-live="polite"
        aria-label={latestLabel}
        aria-busy={present}
        data-testid="activity-stream"
      >
        <CubeTumbleMark />
        {visible.length > 0 ? (
          <div
            ref={scrollerRef}
            className={cn(
              "streaming-status-copy relative min-w-0 flex-1 overflow-hidden",
              visible.length > 1 ? "max-h-[4.875rem]" : null,
              visible.length >= VISIBLE_LINES
                ? "[mask-image:linear-gradient(to_bottom,transparent,black_28%,black)]"
                : null,
            )}
          >
            <ul className="flex flex-col justify-end gap-0.5">
              {visible.map((line, index) => {
                const depth = visible.length - 1 - index;
                const isLive = depth === 0;
                return (
                  <li
                    key={line.id}
                    className={cn(
                      "min-w-0 leading-none transition-opacity duration-300 ease-out",
                      isLive && "flex h-[34px] items-center",
                      !isLive && depth === 1 && "leading-5 opacity-45",
                      !isLive && depth >= 2 && "leading-5 opacity-25",
                    )}
                    title={line.label}
                  >
                    <span
                      className={cn(
                        "block w-full min-w-0 truncate",
                        isLive && "streaming-status-live",
                        line.state === "error" && "streaming-status-error",
                      )}
                    >
                      {line.label}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
      </div>
    </>
  );
}
