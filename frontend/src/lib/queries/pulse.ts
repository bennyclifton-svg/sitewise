import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PulseFeed } from "@/lib/types/pulse";

export const pulseKeys = {
  feed: (projectId: string, since?: string) =>
    ["project", projectId, "pulse", since ?? "7d"] as const,
};

const PULSE_POLL_MS = 15_000;

export function invalidatePulse(queryClient: QueryClient, projectId: string) {
  void queryClient.invalidateQueries({ queryKey: ["project", projectId, "pulse"] });
}

export function usePulseFeed(
  projectId: string,
  options?: { enabled?: boolean; since?: string },
) {
  const since = options?.since;
  return useQuery({
    queryKey: pulseKeys.feed(projectId, since),
    queryFn: () => api.getProjectPulse(projectId, since),
    enabled: options?.enabled ?? Boolean(projectId),
    refetchInterval: PULSE_POLL_MS,
    staleTime: 5_000,
  });
}

export function useDismissPulse(projectId: string, since?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subjectKey: string) =>
      api.dismissProjectPulse(projectId, subjectKey, since),
    onSuccess: (feed: PulseFeed) => {
      queryClient.setQueryData(pulseKeys.feed(projectId, since), feed);
    },
    onSettled: () => {
      invalidatePulse(queryClient, projectId);
    },
  });
}
