import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const tenderKeys = {
  report: (comparisonId: string, revision?: number) =>
    ["tender", "comparison", comparisonId, "report", revision ?? "latest"] as const,
};

export function useTenderReport(comparisonId: string, revision?: number) {
  return useQuery({
    queryKey: tenderKeys.report(comparisonId, revision),
    queryFn: () => api.getTenderReport(comparisonId, revision),
    staleTime: 30_000,
  });
}
