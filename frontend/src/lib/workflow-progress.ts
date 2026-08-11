export type WorkflowProgressMode = "create" | "update" | "invoices";

export type WorkflowProgressKind = "project_plan" | "cost_plan" | "procurement";

export type WorkflowDisplayStage = {
  id: string;
  message: string;
};

export type WorkflowRunPreview = {
  stage: string;
  markdown: string;
};

export type WorkflowSection = {
  id: string;
  label: string;
  status: "queued" | "generating" | "complete" | "failed";
};

export type WorkflowSectionProgress = {
  completed: number;
  total: number;
  sections: WorkflowSection[];
};

const STAGE_MESSAGES: Record<string, string> = {
  queued: "Waiting for a worker…",
  starting: "Loading project profile…",
  context_ready: "Project context ready.",
  retrieval_complete: "Project evidence and guidance ready.",
  scaffold: "Document structure ready.",
  scaffold_ready: "Document structure ready.",
  section_started: "Writing document sections…",
  section_completed: "Writing document sections…",
  section_failed: "A document section failed.",
  validation_started: "Checking structure, evidence, and citations…",
  saving: "Saving draft…",
  artefact_ready: "Draft ready.",
  cancelling: "Cancelling…",
  discovering_invoices: "Finding ingested invoices…",
  extracting_and_mapping: "Extracting and mapping invoices…",
  publishing_cost_plan: "Publishing the updated Cost Plan…",
  verifying_workbook: "Checking invoice register and totals…",
};

export function workflowProgressTitle(
  kind: WorkflowProgressKind,
  mode: WorkflowProgressMode,
): string {
  if (kind === "cost_plan") {
    if (mode === "invoices") return "Processing Invoices";
    return mode === "update" ? "Refreshing Cost Plan" : "Creating Cost Plan";
  }
  if (kind === "procurement") {
    return mode === "update"
      ? "Refreshing Procurement Request"
      : "Preparing Procurement Request";
  }
  return mode === "update" ? "Updating Project Plan" : "Creating Project Plan";
}

export function resolveWorkflowDisplayStage(options: {
  kind: WorkflowProgressKind;
  backendStage: string | null | undefined;
  runState: string | null | undefined;
  progress?: Record<string, unknown> | null;
}): WorkflowDisplayStage {
  const stage = (options.backendStage ?? "").toLowerCase();
  const runState = (options.runState ?? "").toLowerCase();
  const sectionProgress = workflowSectionProgress(options.progress);
  if ((stage === "section_started" || stage === "section_completed") && sectionProgress) {
    const activeId = options.progress?.active_section;
    const active = sectionProgress.sections.find((section) => section.id === activeId);
    return {
      id: stage,
      message:
        active?.status === "generating"
          ? `Writing ${active.label}…`
          : `${sectionProgress.completed} of ${sectionProgress.total} sections complete.`,
    };
  }
  if (STAGE_MESSAGES[stage]) {
    return { id: stage, message: STAGE_MESSAGES[stage]! };
  }
  if (runState === "queued") {
    return { id: "queued", message: STAGE_MESSAGES.queued! };
  }
  return { id: stage || "running", message: "Workflow running…" };
}

export function workflowSectionProgress(
  progress: Record<string, unknown> | null | undefined,
): WorkflowSectionProgress | null {
  if (!progress || !Array.isArray(progress.sections)) return null;
  const sections = progress.sections.flatMap((value): WorkflowSection[] => {
    if (!value || typeof value !== "object") return [];
    const raw = value as Record<string, unknown>;
    if (
      typeof raw.id !== "string" ||
      typeof raw.label !== "string" ||
      !["queued", "generating", "complete", "failed"].includes(String(raw.status))
    ) {
      return [];
    }
    return [
      {
        id: raw.id,
        label: raw.label,
        status: raw.status as WorkflowSection["status"],
      },
    ];
  });
  if (!sections.length) return null;
  const derivedCompleted = sections.filter(
    (section) => section.status === "complete",
  ).length;
  const backendCompleted = progress.completed_sections;
  const backendTotal = progress.total_sections;
  const completed =
    typeof backendCompleted === "number" &&
    Number.isFinite(backendCompleted) &&
    backendCompleted === derivedCompleted
      ? backendCompleted
      : derivedCompleted;
  const total =
    typeof backendTotal === "number" &&
    Number.isFinite(backendTotal) &&
    backendTotal === sections.length
      ? backendTotal
      : sections.length;
  return { completed, total, sections };
}

export function workflowRunPercent(
  progress: Record<string, unknown> | null | undefined,
): number | null {
  // Only completed/total section counts are truthful measurable progress.
  // Lifecycle placeholders such as percent: 0/1/100 must not surface in the UI.
  const sections = workflowSectionProgress(progress);
  if (!sections || sections.total <= 0) return null;
  return Math.round((sections.completed / sections.total) * 100);
}

export function workflowRunPreview(
  progress: Record<string, unknown> | null | undefined,
): WorkflowRunPreview | null {
  const preview = progress?.preview;
  if (!preview || typeof preview !== "object") return null;
  const { stage, markdown } = preview as Record<string, unknown>;
  if (typeof markdown !== "string" || !markdown.trim()) return null;
  return {
    stage: typeof stage === "string" && stage.trim() ? stage : "drafting",
    markdown,
  };
}

export function workflowProgressStage(
  progress: Record<string, unknown> | null | undefined,
): string | null {
  if (!progress) return null;
  const stage = progress.stage;
  return typeof stage === "string" && stage.trim() ? stage : null;
}
