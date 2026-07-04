import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ProjectActivityResponse } from "@/lib/types/project";

export const projectActivityKeys = {
  root: (projectId: string) => ["project", projectId, "activity"] as const,
};

const ACTIVITY_POLL_MS = 2_500;

export function useProjectActivity(
  projectId: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: projectActivityKeys.root(projectId),
    queryFn: () => api.getProjectActivity(projectId),
    enabled: options?.enabled ?? true,
    refetchInterval: (query) =>
      hasRunningRun(query.state.data) ? ACTIVITY_POLL_MS : false,
    staleTime: 0,
  });
}

function hasRunningRun(data: ProjectActivityResponse | undefined): boolean {
  return (data?.runs ?? []).some((run) => !isTerminalStatus(run.status));
}

function isTerminalStatus(status: string): boolean {
  return [
    "blocked",
    "cancelled",
    "canceled",
    "complete",
    "completed",
    "done",
    "failed",
    "refused",
    "skipped",
  ].includes(status);
}
