const WORKBENCH_WORKFLOW_IDS = new Set([
  "project-profile",
  "create-pmp",
  "cost-plan",
  "program",
  "procurement-requests",
]);

export function readWorkbenchWorkflow(search: string): string | null {
  const value = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  ).get("workflow");
  if (!value || !WORKBENCH_WORKFLOW_IDS.has(value)) return null;
  return value;
}

export function workbenchSearchFor(
  workflowId: string,
  currentSearch = "",
): string {
  const params = new URLSearchParams(
    currentSearch.startsWith("?") ? currentSearch.slice(1) : currentSearch,
  );
  params.set("workflow", workflowId);
  // Deep-link artefact params belong to a specific revision view; leave them
  // behind when the user explicitly switches workbench tiles.
  params.delete("artefact");
  params.delete("revision");
  const next = params.toString();
  return next ? `?${next}` : "";
}
