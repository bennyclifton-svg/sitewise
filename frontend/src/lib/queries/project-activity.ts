import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

export function useDeleteProjectActivityRuns(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runIds: string[]) =>
      api.deleteProjectActivityRuns(projectId, runIds),
    onMutate: async (runIds) => {
      await queryClient.cancelQueries({
        queryKey: projectActivityKeys.root(projectId),
      });
      const previous = queryClient.getQueryData<ProjectActivityResponse>(
        projectActivityKeys.root(projectId),
      );
      const runIdSet = new Set(runIds);
      queryClient.setQueryData<ProjectActivityResponse>(
        projectActivityKeys.root(projectId),
        (current) => {
          if (!current) return current;
          const runs = current.runs.filter((run) => !runIdSet.has(run.run_id));
          return {
            ...current,
            runs,
            newest_created_at: runs[0]?.updated_at ?? null,
          };
        },
      );
      return { previous };
    },
    onError: (_error, _runIds, context) => {
      if (context?.previous) {
        queryClient.setQueryData<ProjectActivityResponse>(
          projectActivityKeys.root(projectId),
          context.previous,
        );
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: projectActivityKeys.root(projectId),
      });
    },
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
