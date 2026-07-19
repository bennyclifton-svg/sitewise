import { useQuery, type QueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types/project";

export const workflowRunKeys = {
  run: (projectId: string, runId: string) =>
    ["project", projectId, "workflow-run", runId] as const,
};

export function isTerminalWorkflowRun(run: WorkflowRun) {
  return ["needs_input", "complete", "failed", "cancelled"].includes(
    run.state,
  );
}

export function useWorkflowRun(
  projectId: string,
  runId: string | null,
) {
  return useQuery({
    queryKey: workflowRunKeys.run(projectId, runId ?? "pending"),
    queryFn: () => api.getWorkflowRun(projectId, runId as string),
    enabled: Boolean(projectId && runId),
    staleTime: 250,
    refetchInterval: (query) => {
      const run = query.state.data;
      if (!run || isTerminalWorkflowRun(run)) return false;
      return run.state === "queued" ? 250 : 1_000;
    },
  });
}

export async function waitForWorkflowRun(
  queryClient: QueryClient,
  projectId: string,
  initial: WorkflowRun,
): Promise<WorkflowRun> {
  let run = initial;
  queryClient.setQueryData(workflowRunKeys.run(projectId, run.id), run);
  while (!isTerminalWorkflowRun(run)) {
    await new Promise((resolve) =>
      window.setTimeout(resolve, run.state === "queued" ? 250 : 1_000),
    );
    run = await api.getWorkflowRun(projectId, run.id);
    queryClient.setQueryData(workflowRunKeys.run(projectId, run.id), run);
  }
  return run;
}
