import type { QueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

/**
 * Cache keys for the workbench panels. Prefetch after cockpit bootstrap
 * writes here; the panels read with `fetchQuery` so the click path does not
 * start a second round-trip.
 */
export const workbenchKeys = {
  root: (projectId: string) => ["project", projectId, "workbench"] as const,
  draft: (projectId: string, draftId: string, version?: number) =>
    version == null
      ? (["project", projectId, "workbench", "draft", draftId] as const)
      : (["project", projectId, "workbench", "draft", draftId, version] as const),
  costPlan: (projectId: string) =>
    ["project", projectId, "workbench", "cost-plan"] as const,
  invoiceLedger: (projectId: string) =>
    ["project", projectId, "workbench", "invoice-ledger"] as const,
  decisions: (projectId: string) =>
    ["project", projectId, "workbench", "decisions"] as const,
  programme: (projectId: string) =>
    ["project", projectId, "workbench", "programme"] as const,
  procurementRequests: (projectId: string) =>
    ["project", projectId, "workbench", "procurement-requests"] as const,
};

export function prefetchWorkbench(
  queryClient: QueryClient,
  args: {
    projectId: string;
    pmpDraftId?: string | null;
    pmpDraftVersion?: number | null;
    costPlanDraftId?: string | null;
  },
): Promise<void> {
  void import("@/components/project/DraftReviewPanel");
  const tasks: Promise<unknown>[] = [];
  tasks.push(
    queryClient.prefetchQuery({
      queryKey: workbenchKeys.programme(args.projectId),
      queryFn: () => api.ensureProgramme(args.projectId),
    }),
  );
  tasks.push(
    queryClient.prefetchQuery({
      queryKey: workbenchKeys.procurementRequests(args.projectId),
      queryFn: () => api.listProcurementRequests(args.projectId),
    }),
  );
  if (args.pmpDraftId) {
    tasks.push(
      queryClient.prefetchQuery({
        queryKey: workbenchKeys.draft(
          args.projectId,
          args.pmpDraftId,
          args.pmpDraftVersion ?? undefined,
        ),
        queryFn: () => api.getProjectDraft(args.projectId, args.pmpDraftId!),
      }),
    );
    tasks.push(
      queryClient.prefetchQuery({
        queryKey: workbenchKeys.decisions(args.projectId),
        queryFn: () => api.listDecisions(args.projectId),
      }),
    );
  }
  if (args.costPlanDraftId) {
    tasks.push(
      queryClient.prefetchQuery({
        queryKey: workbenchKeys.costPlan(args.projectId),
        queryFn: () => api.getCostPlanState(args.projectId),
      }),
    );
    tasks.push(
      queryClient.prefetchQuery({
        queryKey: workbenchKeys.invoiceLedger(args.projectId),
        queryFn: () => api.getInvoiceLedger(args.projectId),
      }),
    );
  }
  return Promise.all(tasks).then(() => undefined);
}
