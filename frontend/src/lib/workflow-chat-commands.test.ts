import { describe, expect, it } from "vitest";

import {
  procurementChatCommand,
  workflowChatCommand,
} from "@/lib/workflow-chat-commands";

describe("workflowChatCommand", () => {
  it("returns the button-equivalent instruction text", () => {
    expect(workflowChatCommand("create_pmp")).toBe("Create PMP");
    expect(workflowChatCommand("update_pmp")).toBe("Update PMP");
    expect(workflowChatCommand("create_cost_plan")).toBe("Create cost plan");
    expect(workflowChatCommand("refresh_cost_plan")).toBe("Refresh cost plan");
    expect(workflowChatCommand("process_invoices")).toBe("Process invoices");
    expect(workflowChatCommand("create_programme")).toBe("Create a program");
  });
});

describe("procurementChatCommand", () => {
  it("names the package in a natural instruction", () => {
    expect(procurementChatCommand("consultant_rfp", "Architect")).toBe(
      "Create a consultant request for Architect",
    );
    expect(procurementChatCommand("trade_rft", "Electrical services")).toBe(
      "Create a trade package for Electrical services",
    );
    expect(procurementChatCommand("trade_rfq", "Electrical supplier")).toBe(
      "Create a supplier quote for Electrical supplier",
    );
  });
});
