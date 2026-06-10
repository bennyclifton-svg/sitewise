/**
 * Shared workflow tile / spine status styling.
 * Uses --wf-* tokens derived from SiteWise semantics in index.css.
 */

export type WorkflowStatus =
  | "ready"
  | "blocked"
  | "running"
  | "draft"
  | "failed"
  | "unavailable";

/** Badge and pill classes for workflow tiles. */
export function workflowStatusBadgeClass(status: WorkflowStatus): string {
  switch (status) {
    case "blocked":
    case "failed":
      return "border-[var(--wf-danger-border)] bg-[var(--wf-danger-bg)] text-[var(--wf-danger-text)]";
    case "running":
      return "border-[var(--wf-info-border)] bg-[var(--wf-info-bg)] text-[var(--wf-info-text)]";
    case "draft":
      return "border-[var(--wf-ok-border)] bg-[var(--wf-ok-bg)] text-[var(--wf-ok-text)]";
    case "ready":
      return "border-[var(--wf-ready-border)] bg-[var(--wf-ready-bg)] text-[var(--wf-ready-text)]";
    case "unavailable":
      return "bg-muted text-muted-foreground";
  }
}

/** Lifecycle spine node ring classes. */
export function workflowSpineNodeClass(
  status: WorkflowStatus,
  selected: boolean,
): string {
  const base =
    "relative z-10 grid size-[1.375rem] shrink-0 place-items-center rounded-full border-2 bg-background transition-shadow";

  if (status === "unavailable") {
    return `${base} border-dashed border-muted-foreground/40 text-muted-foreground/50`;
  }
  if (status === "draft") {
    return `${base} border-[var(--wf-ok-text)] bg-[var(--wf-ok-text)] text-primary-foreground`;
  }
  if (status === "running") {
    return `${base} border-[var(--wf-info-text)] bg-[var(--wf-info-text)] text-primary-foreground animate-[wf-pulse_2.2s_ease-in-out_infinite]`;
  }
  if (status === "ready") {
    return `${base} border-[var(--wf-info-text)] text-[var(--wf-info-text)]${
      selected ? " shadow-[0_0_0_3px_var(--wf-info-bg)]" : ""
    }`;
  }
  if (status === "blocked" || status === "failed") {
    return `${base} border-[var(--wf-danger-text)] text-[var(--wf-danger-text)]`;
  }
  return `${base} border-border text-muted-foreground`;
}

/** Selected workflow tile border emphasis. */
export function workflowTileClass(selected: boolean, status: WorkflowStatus): string {
  return [
    "min-h-[5.5rem] rounded-lg border bg-background p-3 text-left transition-colors hover:bg-muted/60",
    selected ? "border-foreground bg-muted shadow-sm" : "border-border",
    status === "running" && selected ? "ring-2 ring-[var(--wf-info-bg)]" : "",
  ]
    .filter(Boolean)
    .join(" ");
}

/** Compact always-on tile variant. */
export function workflowDockTileClass(selected: boolean): string {
  return [
    "flex min-h-14 w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors hover:bg-muted/60",
    selected ? "border-foreground bg-muted font-medium" : "border-border bg-background",
  ].join(" ");
}
