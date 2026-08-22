import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import { prefetchWorkbench, workbenchKeys } from "@/lib/queries/workbench";

vi.mock("@/lib/api", () => ({
  api: {
    getProjectDraft: vi.fn(),
    listDecisions: vi.fn(),
    getCostPlanState: vi.fn(),
    getInvoiceLedger: vi.fn(),
    ensureProgramme: vi.fn(),
    listProcurementRequests: vi.fn(),
  },
}));

describe("prefetchWorkbench", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProjectDraft).mockResolvedValue({ id: "pmp-1" } as never);
    vi.mocked(api.listDecisions).mockResolvedValue({
      decisions: [],
      set_revision: 0,
    });
    vi.mocked(api.getCostPlanState).mockResolvedValue({
      version: 1,
      items: [],
    } as never);
    vi.mocked(api.getInvoiceLedger).mockResolvedValue({
      cost_plan_version: 1,
      workbook_path: "cost-plan.xlsx",
      rows: [],
      cost_items: [],
    });
    vi.mocked(api.ensureProgramme).mockResolvedValue({
      id: "prog-1",
      project_id: "project-1",
      version: 1,
    } as never);
    vi.mocked(api.listProcurementRequests).mockResolvedValue([]);
  });

  it("does not fetch PMP or Cost Plan drafts when they are absent", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 30_000 } },
    });

    await prefetchWorkbench(queryClient, { projectId: "project-1" });

    expect(api.getProjectDraft).not.toHaveBeenCalled();
    expect(api.listDecisions).not.toHaveBeenCalled();
    expect(api.getCostPlanState).not.toHaveBeenCalled();
    expect(api.getInvoiceLedger).not.toHaveBeenCalled();
    expect(api.ensureProgramme).toHaveBeenCalledWith("project-1");
    expect(api.listProcurementRequests).toHaveBeenCalledWith("project-1");
  });

  it("prefetches PMP markdown, decisions, and Cost Plan state when drafts exist", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 30_000 } },
    });

    await prefetchWorkbench(queryClient, {
      projectId: "project-1",
      pmpDraftId: "pmp-1",
      pmpDraftVersion: 3,
      costPlanDraftId: "cost-1",
    });

    expect(api.getProjectDraft).toHaveBeenCalledTimes(1);
    expect(api.getProjectDraft).toHaveBeenCalledWith("project-1", "pmp-1");
    expect(api.listDecisions).toHaveBeenCalledWith("project-1");
    expect(api.getCostPlanState).toHaveBeenCalledTimes(1);
    expect(api.getInvoiceLedger).toHaveBeenCalledWith("project-1");
    expect(api.ensureProgramme).toHaveBeenCalledWith("project-1");
    expect(api.listProcurementRequests).toHaveBeenCalledWith("project-1");

    await queryClient.fetchQuery({
      queryKey: workbenchKeys.draft("project-1", "pmp-1", 3),
      queryFn: () => api.getProjectDraft("project-1", "pmp-1"),
    });
    await queryClient.fetchQuery({
      queryKey: workbenchKeys.costPlan("project-1"),
      queryFn: () => api.getCostPlanState("project-1"),
    });
    expect(api.getProjectDraft).toHaveBeenCalledTimes(1);
    expect(api.getCostPlanState).toHaveBeenCalledTimes(1);
  });
});
