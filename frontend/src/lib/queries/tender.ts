import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const tenderKeys = {
  report: (comparisonId: string) => ["tender", "comparison", comparisonId, "report"] as const,
};

export function useTenderReport(comparisonId: string) {
  return useQuery({
    queryKey: tenderKeys.report(comparisonId),
    queryFn: () => api.getTenderReport(comparisonId),
    staleTime: 30_000,
  });
}
