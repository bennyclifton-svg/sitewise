import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PulseFeed } from "@/lib/types/pulse";

export const pulseKeys = {
  feed: (projectId: string) => ["project", projectId, "pulse"] as const,
};

const PULSE_POLL_MS = 15_000;

export function invalidatePulse(queryClient: QueryClient, projectId: string) {
  void queryClient.invalidateQueries({ queryKey: pulseKeys.feed(projectId) });
}

export function usePulseFeed(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: pulseKeys.feed(projectId),
    queryFn: () => api.getProjectPulse(projectId),
    enabled: options?.enabled ?? Boolean(projectId),
    refetchInterval: PULSE_POLL_MS,
    staleTime: 5_000,
  });
}

export function useDismissPulse(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subjectKey: string) => api.dismissProjectPulse(projectId, subjectKey),
    onSuccess: (feed: PulseFeed) => {
      queryClient.setQueryData(pulseKeys.feed(projectId), feed);
    },
    onSettled: () => {
      invalidatePulse(queryClient, projectId);
    },
  });
}
