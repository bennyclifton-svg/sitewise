import type { ToolStatusEvent, WorkflowRunRef } from "@/lib/chat-events";
import { toolActivityLines } from "@/lib/tool-activity";
import type { WorkflowRun } from "@/lib/types/project";
import {
  resolveWorkflowDisplayStage,
  workflowProgressStage,
  workflowProgressTitle,
  type WorkflowProgressKind,
  type WorkflowProgressMode,
} from "@/lib/workflow-progress";

export type ActivityLineState = "running" | "done" | "error" | "info";

export type ActivityLine = {
  id: string;
  label: string;
  state: ActivityLineState;
};

const GENERIC_STATUS = new Set([
  "workflow queued",
  "workflow running",
  "working",
  "thinking",
]);

function normalizeLabel(label: string): string {
  return label.trim().replace(/\s+/g, " ").toLowerCase();
}

function workflowKind(workflowType: string | undefined): WorkflowProgressKind {
  const type = (workflowType ?? "").toLowerCase();
  if (type.includes("cost_plan") || type.includes("invoice")) return "cost_plan";
  if (type.includes("procurement") || type.includes("consultant")) {
    return "procurement";
  }
  return "project_plan";
}

function workflowMode(workflowType: string | undefined): WorkflowProgressMode {
  const type = (workflowType ?? "").toLowerCase();
  if (type.includes("invoice")) return "invoices";
  if (type.startsWith("refresh_") || type.startsWith("update_")) return "update";
  return "create";
}

function shortWorkflowLabel(workflowType: string | undefined): string {
  const kind = workflowKind(workflowType);
  if (kind === "cost_plan") {
    return workflowMode(workflowType) === "invoices" ? "Invoices" : "Cost Plan";
  }
  if (kind === "procurement") return "Request for Proposal";
  return "Project Plan";
}

/** Human status line for an in-flight workflow run. */
export function formatWorkflowActivityLabel(
  run: Pick<WorkflowRun, "workflow_type" | "state" | "progress">,
  fallbackType?: string,
): string {
  const workflowType = run.workflow_type || fallbackType;
  const kind = workflowKind(workflowType);
  const mode = workflowMode(workflowType);
  const title = workflowProgressTitle(kind, mode);
  const stage = resolveWorkflowDisplayStage({
    kind,
    backendStage: workflowProgressStage(run.progress),
    runState: run.state,
    progress: run.progress,
  });

  if (run.state === "queued") {
    return `Queued ${shortWorkflowLabel(workflowType)}…`;
  }

  if (
    stage.id === "section_started" ||
    stage.id === "section_completed" ||
    stage.message.startsWith("Writing ")
  ) {
    return stage.message;
  }

  if (stage.id && stage.id !== "running" && STAGE_IS_SPECIFIC.has(stage.id)) {
    return stage.message;
  }

  if (run.state === "running") {
    return `${title}…`;
  }

  return stage.message || `${title}…`;
}

const STAGE_IS_SPECIFIC = new Set([
  "starting",
  "context_ready",
  "retrieval_complete",
  "scaffold",
  "scaffold_ready",
  "typed_rows_ready",
  "validation_started",
  "saving",
  "artefact_ready",
  "cancelling",
  "discovering_invoices",
  "extracting_and_mapping",
  "publishing_cost_plan",
  "verifying_workbook",
]);

export function workflowActivityLine(
  run: Pick<WorkflowRun, "id" | "workflow_type" | "state" | "progress">,
  runRef?: WorkflowRunRef,
): ActivityLine {
  return {
    id: `workflow-${run.id}`,
    label: formatWorkflowActivityLabel(run, runRef?.workflowType),
    state: "running",
  };
}

/**
 * Merge live clerk status, tool steps, and workflow progress into one
 * chronological activity feed. Drops generic status noise when richer lines exist.
 */
export function buildActivityLines(options: {
  statusMessage?: string | null;
  toolEvents?: ToolStatusEvent[];
  workflowLines?: ActivityLine[];
}): ActivityLine[] {
  const lines: ActivityLine[] = [];
  const toolLines = toolActivityLines(options.toolEvents ?? []);
  for (const line of toolLines) {
    lines.push({
      id: line.id,
      label: line.label,
      state: line.state,
    });
  }

  for (const line of options.workflowLines ?? []) {
    if (!line.label.trim()) continue;
    const last = lines[lines.length - 1];
    if (last && normalizeLabel(last.label) === normalizeLabel(line.label)) {
      last.label = line.label;
      last.state = line.state;
      continue;
    }
    lines.push(line);
  }

  const status = options.statusMessage?.trim() ?? "";
  if (status) {
    const normalized = normalizeLabel(status);
    const hasRicher =
      lines.length > 0 &&
      (GENERIC_STATUS.has(normalized) ||
        lines.some((line) => normalizeLabel(line.label) === normalized));
    if (!hasRicher) {
      const last = lines[lines.length - 1];
      if (last && normalizeLabel(last.label) === normalized) {
        last.label = status;
      } else {
        lines.push({
          id: `status-${normalized}`,
          label: status,
          state: "info",
        });
      }
    }
  }

  return lines;
}
