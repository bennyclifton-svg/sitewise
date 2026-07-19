import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";

import { api } from "@/lib/api";
import { projectActivityKeys } from "@/lib/queries/project-activity";
import type { ResourceEvent } from "@/lib/chat-events";
import type {
  EvidencePreview,
  ProjectDetail,
  ProjectEvent,
  WorkspaceTreeNode,
} from "@/lib/types/project";

/**
 * Centralised query keys for project-scoped data. Keeping them in one place
 * means a mutation and the query it should refresh can never drift apart.
 */
export const projectKeys = {
  root: (projectId: string) => ["project", projectId] as const,
  detail: (projectId: string) => ["project", projectId, "detail"] as const,
  evidence: (projectId: string) => ["project", projectId, "evidence"] as const,
  workspaceTree: (projectId: string) =>
    ["project", projectId, "workspace-tree"] as const,
};

const PROJECT_DATA_STALE_MS = 60_000;

type QueryToggle = { enabled?: boolean };

export function useProjectDetail(projectId: string, options?: QueryToggle) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => api.getProject(projectId),
    staleTime: PROJECT_DATA_STALE_MS,
    enabled: options?.enabled ?? true,
  });
}

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
  data: {
    project: ProjectDetail;
    evidence: EvidencePreview[];
    workspaceTree: WorkspaceTreeNode[];
  },
) {
  queryClient.setQueryData(projectKeys.detail(projectId), data.project);
  queryClient.setQueryData(projectKeys.evidence(projectId), data.evidence);
  queryClient.setQueryData(
    projectKeys.workspaceTree(projectId),
    data.workspaceTree,
  );
}

export function setProjectDetail(
  queryClient: QueryClient,
  project: ProjectDetail,
) {
  queryClient.setQueryData(projectKeys.detail(project.id), project);
}

type ProjectResourceSignal = Pick<ResourceEvent, "projectId" | "resourceType">;

export function applyProjectResourceSignal(
  queryClient: QueryClient,
  signal: ProjectResourceSignal,
) {
  const keys = invalidationKeys(signal.projectId, signal.resourceType);
  for (const queryKey of keys) {
    void queryClient.invalidateQueries({ queryKey, exact: true });
  }
}

export function useProjectEventCursor({
  projectId,
  enabled,
  active,
}: {
  projectId: string;
  enabled: boolean;
  active: boolean;
}) {
  const queryClient = useQueryClient();
  const cursorRef = useRef(0);
  const seenIdsRef = useRef(new Set<string>());
  const pollRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    cursorRef.current = 0;
    seenIdsRef.current.clear();
  }, [projectId]);

  const applyResource = useCallback(
    (resource: ResourceEvent) => {
      if (resource.projectId !== projectId) return;
      applyProjectResourceSignal(queryClient, resource);
    },
    [projectId, queryClient],
  );

  useEffect(() => {
    if (!enabled || !projectId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let inFlight = false;

    const schedule = (delay: number) => {
      if (cancelled || document.visibilityState === "hidden") return;
      timer = setTimeout(poll, delay);
    };
    const poll = async () => {
      if (cancelled || inFlight || document.visibilityState === "hidden") return;
      inFlight = true;
      try {
        const response = await api.getProjectEvents(projectId, cursorRef.current);
        for (const event of response.events) {
          if (
            event.sequence <= cursorRef.current ||
            seenIdsRef.current.has(event.id)
          ) {
            continue;
          }
          seenIdsRef.current.add(event.id);
          applyDurableProjectEvent(queryClient, event);
        }
        cursorRef.current = Math.max(cursorRef.current, response.next_after);
        schedule(response.events.length >= 100 ? 0 : active ? 250 : 1_500);
      } catch {
        schedule(active ? 500 : 1_500);
      } finally {
        inFlight = false;
      }
    };
    pollRef.current = () => void poll();
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
      else if (timer) clearTimeout(timer);
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    void poll();
    return () => {
      cancelled = true;
      pollRef.current = null;
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [active, enabled, projectId, queryClient]);

  return {
    applyResource,
    pollNow: () => pollRef.current?.(),
  };
}

export function applyDurableProjectEvent(
  queryClient: QueryClient,
  event: ProjectEvent,
) {
  applyProjectResourceSignal(queryClient, {
    projectId: event.project_id,
    resourceType: event.resource_type,
  });
  const changedResources =
    event.payload.changedResources ?? event.payload.changed_resources;
  if (Array.isArray(changedResources)) {
    for (const resourceType of changedResources) {
      if (typeof resourceType === "string") {
        applyProjectResourceSignal(queryClient, {
          projectId: event.project_id,
          resourceType,
        });
      }
    }
  }
}

function invalidationKeys(projectId: string, resourceType: string) {
  switch (resourceType) {
    case "project_profile":
    case "project_profile_proposal":
    case "project_decision":
      return [projectKeys.detail(projectId)];
    case "source_document":
    case "project_evidence":
      return [projectKeys.evidence(projectId), projectKeys.workspaceTree(projectId)];
    case "workspace_file":
    case "draft_artifact":
      return [projectKeys.workspaceTree(projectId), projectActivityKeys.root(projectId)];
    case "workflow_run":
    case "tender_job":
      return [projectActivityKeys.root(projectId)];
    default:
      return [];
  }
}
