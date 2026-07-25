/**
 * Frontend time-budget progress for long-running workflow runs (PMP / cost plan).
 *
 * Backend progress is coarse (queued → starting → executing → terminal), so the
 * bar and stage copy are driven here: monotonic creep against a seeded budget,
 * real backend stage when available, and rotating sub-lines while a stage is
 * long-lived. Never reports 100% until the run is marked complete.
 */

import { formatEtaSeconds } from "@/lib/ingest-progress";

export { formatEtaSeconds };

/** Seeded from Petersham-scale Create/Update PMP runs (~3–5 min). */
export const WORKFLOW_BUDGET_SECONDS_DEFAULT = 4 * 60;
const ACTIVE_FRACTION_CAP = 0.98;
const SUBLINE_ROTATE_MS = 5_000;

export type WorkflowProgressMode = "create" | "update";

export type WorkflowProgressKind = "project_plan" | "cost_plan";

export type WorkflowProgressSnapshot = {
  /** Overall progress in [0, 1]; monotonic non-decreasing while active. */
  fraction: number;
  /** Estimated seconds remaining; null when idle. */
  etaSeconds: number | null;
};

export type WorkflowDisplayStage = {
  id: string;
  message: string;
};

type PhaseDef = {
  id: string;
  message: string;
  /** Relative weight within the executing window. */
  weight: number;
  sublines?: string[];
};

const PROJECT_PLAN_EXECUTING: PhaseDef[] = [
  { id: "evidence", message: "Reviewing project evidence…", weight: 0.15 },
  { id: "platform", message: "Checking SiteWise guidance…", weight: 0.1 },
  {
    id: "drafting",
    message: "Writing the project plan…",
    weight: 0.45,
    sublines: [
      "Building Project Summary…",
      "Filling Brief and Consultants…",
      "Setting programme and risk register…",
    ],
  },
  { id: "validating", message: "Checking citations and structure…", weight: 0.15 },
  { id: "saving", message: "Saving draft…", weight: 0.15 },
];

const COST_PLAN_EXECUTING: PhaseDef[] = [
  { id: "evidence", message: "Reviewing project evidence…", weight: 0.15 },
  { id: "platform", message: "Checking SiteWise guidance…", weight: 0.1 },
  {
    id: "drafting",
    message: "Writing the cost plan…",
    weight: 0.45,
    sublines: [
      "Building cost summary…",
      "Mapping elemental allowances…",
      "Checking rates and contingencies…",
    ],
  },
  { id: "validating", message: "Checking citations and structure…", weight: 0.15 },
  { id: "saving", message: "Saving draft…", weight: 0.15 },
];

export class WorkflowRunEstimator {
  private readonly budgetSeconds: number;
  private readonly startedAtMs: number;
  private readonly now: () => number;
  private maxReportedFraction = 0;
  private complete = false;

  constructor(
    options: {
      budgetSeconds?: number;
      startedAtMs?: number;
      now?: () => number;
    } = {},
  ) {
    this.now = options.now ?? (() => Date.now());
    this.budgetSeconds = options.budgetSeconds ?? WORKFLOW_BUDGET_SECONDS_DEFAULT;
    this.startedAtMs = options.startedAtMs ?? this.now();
  }

  markComplete(): void {
    this.complete = true;
    this.maxReportedFraction = 1;
  }

  elapsedSeconds(): number {
    return Math.max((this.now() - this.startedAtMs) / 1000, 0);
  }

  snapshot(): WorkflowProgressSnapshot {
    if (this.complete) {
      return { fraction: 1, etaSeconds: 0 };
    }

    const elapsed = this.elapsedSeconds();
    const raw = elapsed / this.budgetSeconds;
    const fraction = Math.max(
      Math.min(raw, ACTIVE_FRACTION_CAP),
      this.maxReportedFraction,
    );
    this.maxReportedFraction = fraction;

    // Past the budget: keep a small positive ETA so the label stays honest
    // ("a few seconds left") without claiming the bar is finished.
    const etaSeconds =
      elapsed < this.budgetSeconds
        ? this.budgetSeconds - elapsed
        : Math.max(5, (1 - fraction) * 20);

    return { fraction, etaSeconds };
  }
}

export function workflowProgressTitle(
  kind: WorkflowProgressKind,
  mode: WorkflowProgressMode,
): string {
  if (kind === "cost_plan") {
    return mode === "update" ? "Refreshing Cost Plan" : "Creating Cost Plan";
  }
  return mode === "update" ? "Updating Project Plan" : "Creating Project Plan";
}

/**
 * Map coarse backend stage + elapsed time onto user-facing copy.
 * Never invents a "complete" stage — caller stops rendering once terminal.
 */
export function resolveWorkflowDisplayStage(options: {
  kind: WorkflowProgressKind;
  backendStage: string | null | undefined;
  runState: string | null | undefined;
  elapsedSeconds: number;
  budgetSeconds?: number;
  nowMs?: number;
}): WorkflowDisplayStage {
  const stage = (options.backendStage ?? "").toLowerCase();
  const runState = (options.runState ?? "").toLowerCase();
  const budget = options.budgetSeconds ?? WORKFLOW_BUDGET_SECONDS_DEFAULT;
  const nowMs = options.nowMs ?? Date.now();

  if (stage === "queued" || runState === "queued") {
    return { id: "queued", message: "Waiting for a worker…" };
  }

  if (stage === "cancelling") {
    return { id: "cancelling", message: "Cancelling…" };
  }

  if (stage === "starting") {
    return { id: "preparing", message: "Loading project profile…" };
  }

  // executing / running / unknown-while-active → timed phases
  const phases =
    options.kind === "cost_plan" ? COST_PLAN_EXECUTING : PROJECT_PLAN_EXECUTING;
  const phase = pickExecutingPhase(phases, options.elapsedSeconds, budget);
  return withRotatedSubline(phase, nowMs);
}

function pickExecutingPhase(
  phases: PhaseDef[],
  elapsedSeconds: number,
  budgetSeconds: number,
): PhaseDef {
  const totalWeight = phases.reduce((sum, phase) => sum + phase.weight, 0);
  // Spend early budget on queued/starting outside this picker; map elapsed
  // across the full budget so late phases still appear before the cap.
  const t = Math.min(Math.max(elapsedSeconds / budgetSeconds, 0), 0.999);
  let cursor = 0;
  for (const phase of phases) {
    cursor += phase.weight / totalWeight;
    if (t < cursor) return phase;
  }
  return phases[phases.length - 1]!;
}

function withRotatedSubline(phase: PhaseDef, nowMs: number): WorkflowDisplayStage {
  if (!phase.sublines?.length) {
    return { id: phase.id, message: phase.message };
  }
  const index = Math.floor(nowMs / SUBLINE_ROTATE_MS) % phase.sublines.length;
  return { id: phase.id, message: phase.sublines[index]! };
}

/** Read `progress.stage` from a workflow run payload without assuming shape. */
export function workflowProgressStage(
  progress: Record<string, unknown> | null | undefined,
): string | null {
  if (!progress) return null;
  const stage = progress.stage;
  return typeof stage === "string" && stage.trim() ? stage : null;
}
