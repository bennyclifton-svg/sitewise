import { useQuery, type QueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const emailKeys = {
  register: (projectId: string) => ["project", projectId, "emails"] as const,
};

const EMAIL_POLL_MS = 15_000;

export function invalidateProjectEmails(
  queryClient: QueryClient,
  projectId: string,
) {
  void queryClient.invalidateQueries({ queryKey: emailKeys.register(projectId) });
}

export function useProjectEmails(
  projectId: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: emailKeys.register(projectId),
    queryFn: () => api.listProjectEmails(projectId),
    enabled: options?.enabled ?? Boolean(projectId),
    refetchInterval: EMAIL_POLL_MS,
    staleTime: 5_000,
  });
}
