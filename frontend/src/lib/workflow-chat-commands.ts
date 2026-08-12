import type { RunnableProcurementRequestKind } from "@/components/project/ProcurementRequestPanel";

/** User-facing chat text for workbench command buttons. */
export function workflowChatCommand(
  action:
    | "create_pmp"
    | "update_pmp"
    | "create_cost_plan"
    | "refresh_cost_plan"
    | "process_invoices",
): string {
  switch (action) {
    case "create_pmp":
      return "Create PMP";
    case "update_pmp":
      return "Update PMP";
    case "create_cost_plan":
      return "Create cost plan";
    case "refresh_cost_plan":
      return "Refresh cost plan";
    case "process_invoices":
      return "Process invoices";
  }
}

export function procurementChatCommand(
  kind: RunnableProcurementRequestKind,
  targetName: string,
): string {
  const target = targetName.trim();
  if (kind === "consultant_rfp") {
    return `Create a consultant request for ${target}`;
  }
  if (kind === "trade_rfq") {
    return `Create a supplier quote for ${target}`;
  }
  return `Create a trade package for ${target}`;
}
