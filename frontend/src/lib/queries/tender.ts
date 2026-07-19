import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const tenderKeys = {
  root: ["tender"] as const,
  comparisons: (projectId: string) =>
    ["tender", "project", projectId, "comparisons"] as const,
  comparison: (comparisonId: string) =>
    ["tender", "comparison", comparisonId, "detail"] as const,
  progress: (comparisonId: string) =>
    ["tender", "comparison", comparisonId, "progress"] as const,
  matrix: (comparisonId: string) =>
    ["tender", "comparison", comparisonId, "matrix"] as const,
  qa: (comparisonId: string) =>
    ["tender", "comparison", comparisonId, "qa"] as const,
  report: (comparisonId: string, revision?: number) =>
    ["tender", "comparison", comparisonId, "report", revision ?? "latest"] as const,
};

export function useTenderComparisons(projectId: string) {
  return useQuery({
    queryKey: tenderKeys.comparisons(projectId),
    queryFn: () => api.listTenderComparisons(projectId),
  });
}

export function useTenderComparison(comparisonId: string) {
  return useQuery({
    queryKey: tenderKeys.comparison(comparisonId),
    queryFn: () => api.getTenderComparison(comparisonId),
  });
}

export function useTenderProgress(comparisonId: string) {
  return useQuery({
    queryKey: tenderKeys.progress(comparisonId),
    queryFn: () => api.getTenderComparisonProgress(comparisonId),
    refetchInterval: (query) => {
      if (document.visibilityState === "hidden") return false;
      return query.state.data?.is_processing ? 1_500 : false;
    },
    refetchIntervalInBackground: false,
    retry: 2,
    retryDelay: (attempt) => Math.min(1_000 * 2 ** attempt, 8_000),
  });
}

export function useTenderMatrix(comparisonId: string) {
  return useQuery({
    queryKey: tenderKeys.matrix(comparisonId),
    queryFn: () => api.getTenderMatrix(comparisonId),
  });
}

export function useTenderQa(comparisonId: string) {
  return useQuery({
    queryKey: tenderKeys.qa(comparisonId),
    queryFn: async () => (await api.getTenderQaQueue(comparisonId)).items,
  });
}

export function useTenderReport(comparisonId: string, revision?: number) {
  return useQuery({
    queryKey: tenderKeys.report(comparisonId, revision),
    queryFn: () => api.getTenderReport(comparisonId, revision),
    staleTime: 30_000,
  });
}
