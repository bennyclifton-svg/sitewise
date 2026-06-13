import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { EvidencePreview, WorkspaceTreeNode } from "@/lib/types/project";

/**
 * Centralised query keys for project-scoped data. Keeping them in one place
 * means a mutation and the query it should refresh can never drift apart.
 */
export const projectKeys = {
  root: (projectId: string) => ["project", projectId] as const,
  evidence: (projectId: string) => ["project", projectId, "evidence"] as const,
  workspaceTree: (projectId: string) =>
    ["project", projectId, "workspace-tree"] as const,
};

const PROJECT_DATA_STALE_MS = 60_000;

type QueryToggle = { enabled?: boolean };

export function useProjectEvidence(projectId: string, options?: QueryToggle) {
  return useQuery({
    queryKey: projectKeys.evidence(projectId),
    queryFn: () => api.getProjectEvidence(projectId),
    staleTime: PROJECT_DATA_STALE_MS,
    enabled: options?.enabled ?? true,
  });
}

export function useProjectWorkspaceTree(
  projectId: string,
  options?: QueryToggle,
) {
  return useQuery({
    queryKey: projectKeys.workspaceTree(projectId),
    queryFn: async () =>
      (await api.getProjectWorkspaceTree(projectId)).tree,
    staleTime: PROJECT_DATA_STALE_MS,
    enabled: options?.enabled ?? true,
  });
}

/**
 * Delete an evidence document with an optimistic cache update: the row
 * disappears from the repository the instant the user confirms, the network
 * call runs in the background, and the row is restored only if the server
 * rejects. The workspace tree is refreshed once the delete settles since the
 * backing file leaves the folder view too.
 */
export function useDeleteEvidence(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (evidenceId: string) =>
      api.deleteProjectEvidence(projectId, evidenceId),
    onMutate: async (evidenceId: string) => {
      await queryClient.cancelQueries({
        queryKey: projectKeys.evidence(projectId),
      });
      const previous = queryClient.getQueryData<EvidencePreview[]>(
        projectKeys.evidence(projectId),
      );
      queryClient.setQueryData<EvidencePreview[]>(
        projectKeys.evidence(projectId),
        (current) => (current ?? []).filter((item) => item.id !== evidenceId),
      );
      return { previous };
    },
    onError: (_error, _evidenceId, context) => {
      if (context?.previous) {
        queryClient.setQueryData<EvidencePreview[]>(
          projectKeys.evidence(projectId),
          context.previous,
        );
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: projectKeys.evidence(projectId),
      });
      void queryClient.invalidateQueries({
        queryKey: projectKeys.workspaceTree(projectId),
      });
    },
  });
}

/** Fetch the latest workspace tree and write it into the query cache. */
export async function reloadProjectWorkspaceTree(
  queryClient: QueryClient,
  projectId: string,
) {
  const tree = (await api.getProjectWorkspaceTree(projectId)).tree;
  queryClient.setQueryData(projectKeys.workspaceTree(projectId), tree);
  return tree;
}

/** Seed the project-data caches from a cockpit bootstrap response so the
 * dedicated queries render instantly without a second round-trip. */
export function seedProjectData(
  queryClient: QueryClient,
  projectId: string,
  data: { evidence: EvidencePreview[]; workspaceTree: WorkspaceTreeNode[] },
) {
  queryClient.setQueryData(projectKeys.evidence(projectId), data.evidence);
  queryClient.setQueryData(
    projectKeys.workspaceTree(projectId),
    data.workspaceTree,
  );
}
