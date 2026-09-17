import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import {
  applyDurableProjectEvent,
  projectKeys,
  setProjectDetail,
  useProjectEventCursor,
} from "@/lib/queries/project-data";
import { workbenchKeys } from "@/lib/queries/workbench";
import { pulseKeys } from "@/lib/queries/pulse";
import type { ProjectDetail, ProjectEvent } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getProjectEvents: vi.fn(),
  },
}));

describe("project event reconciliation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility("visible");
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("invalidates only keys named by the durable resource", () => {
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    applyDurableProjectEvent(queryClient, event());

    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.detail("project-1"),
      exact: true,
    });
  });

  it("invalidates project detail when evidence changes", () => {
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    applyDurableProjectEvent(
      queryClient,
      event({ resource_type: "project_evidence" }),
    );

    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.detail("project-1"),
      exact: true,
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.evidence("project-1"),
      exact: true,
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.workspaceTree("project-1"),
      exact: true,
    });
  });

  it("invalidates detail and document statuses when a workflow run changes", () => {
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    applyDurableProjectEvent(
      queryClient,
      event({ resource_type: "workflow_run" }),
    );

    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.detail("project-1"),
      exact: true,
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: projectKeys.evidence("project-1"),
      exact: true,
    });
  });

  it.each(["project_evidence", "workflow_run", "email"])(
    "invalidates all Pulse windows for %s without touching another project",
    (resourceType) => {
      const queryClient = client();
      const keys = [pulseKeys.feed("project-1"), pulseKeys.feed("project-1", "2026-09-01T00:00:00Z")];
      const otherKey = pulseKeys.feed("project-2");
      for (const key of [...keys, otherKey]) queryClient.setQueryData(key, {});
      applyDurableProjectEvent(queryClient, event({ resource_type: resourceType }));
      for (const key of keys) expect(queryClient.getQueryState(key)?.isInvalidated).toBe(true);
      expect(queryClient.getQueryState(otherKey)?.isInvalidated).toBe(false);
      queryClient.clear();
    },
  );

  it("invalidates the strategy grid after an agent table edit", () => {
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    applyDurableProjectEvent(
      queryClient,
      event({ resource_type: "procurement_strategy" }),
    );

    expect(invalidate).toHaveBeenCalledWith({
      queryKey: workbenchKeys.procurementStrategy("project-1"),
      exact: true,
    });
  });

  it("writes an HTTP project response to the exact detail key immediately", () => {
    const queryClient = client();
    const project = { id: "project-1", profile_revision: 4 } as ProjectDetail;

    setProjectDetail(queryClient, project);

    expect(queryClient.getQueryData(projectKeys.detail("project-1"))).toBe(project);
    expect(queryClient.getQueryData(projectKeys.root("project-1"))).toBeUndefined();
  });

  it("deduplicates cursor replay and uses the active 250ms interval", async () => {
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(api.getProjectEvents)
      .mockResolvedValueOnce({ events: [event()], next_after: 1 })
      .mockResolvedValue({ events: [event()], next_after: 1 });

    renderHook(
      () =>
        useProjectEventCursor({
          projectId: "project-1",
          enabled: true,
          active: true,
        }),
      { wrapper: wrapper(queryClient) },
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(api.getProjectEvents).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(249);
    });
    expect(api.getProjectEvents).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(api.getProjectEvents).toHaveBeenCalledTimes(2);
    expect(invalidate).toHaveBeenCalledTimes(1);
  });

  it("pauses while hidden and resumes immediately when visible", async () => {
    const queryClient = client();
    setVisibility("hidden");
    vi.mocked(api.getProjectEvents).mockResolvedValue({ events: [], next_after: 0 });

    renderHook(
      () =>
        useProjectEventCursor({
          projectId: "project-1",
          enabled: true,
          active: false,
        }),
      { wrapper: wrapper(queryClient) },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(api.getProjectEvents).not.toHaveBeenCalled();

    setVisibility("visible");
    document.dispatchEvent(new Event("visibilitychange"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(api.getProjectEvents).toHaveBeenCalledTimes(1);
  });

  it("keeps one polling timer after an immediate refresh", async () => {
    vi.mocked(api.getProjectEvents).mockResolvedValue({ events: [], next_after: 0 });
    const hook = renderHook(() => useProjectEventCursor({
      projectId: "project-1", enabled: true, active: true,
    }), { wrapper: wrapper(client()) });
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });
    await act(async () => { hook.result.current.pollNow(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    // Initial request, explicit request, then four periodic requests.
    expect(api.getProjectEvents).toHaveBeenCalledTimes(6);
    hook.unmount();
  });

  it("ignores an old project's response after navigation", async () => {
    let resolveOld!: (value: { events: ProjectEvent[]; next_after: number }) => void;
    vi.mocked(api.getProjectEvents)
      .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }))
      .mockResolvedValue({ events: [], next_after: 0 });
    const onEvent = vi.fn();
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const hook = renderHook(({ projectId }) => useProjectEventCursor({
      projectId, enabled: true, active: true, onEvent,
    }), { initialProps: { projectId: "project-1" }, wrapper: wrapper(queryClient) });
    hook.rerender({ projectId: "project-2" });
    await act(async () => { resolveOld({ events: [event()], next_after: 1 }); });
    expect(onEvent).not.toHaveBeenCalled();
    expect(invalidate).not.toHaveBeenCalled();
    hook.unmount();
  });

  it.each([1, 2, 4])("coalesces a page from %s simultaneous workflows", async (workflows) => {
    const events = Array.from({ length: workflows * 10 }, (_, index) => event({
      id: `event-${index}`, sequence: index + 1, resource_type: "workflow_run",
      payload: { changedResources: ["project_evidence", "workflow_run"] },
    }));
    vi.mocked(api.getProjectEvents).mockResolvedValue({ events, next_after: events.length });
    const queryClient = client();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const onEvent = vi.fn();
    const hook = renderHook(() => useProjectEventCursor({
      projectId: "project-1", enabled: true, active: true, onEvent,
    }), { wrapper: wrapper(queryClient) });
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    console.info(JSON.stringify({ workflows, events: events.length, invalidations: invalidate.mock.calls.length }));
    expect(onEvent).toHaveBeenCalledTimes(events.length);
    expect(invalidate).toHaveBeenCalledTimes(6);
    hook.unmount();
  });
});

function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function wrapper(queryClient: QueryClient) {
  return function QueryWrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

function setVisibility(value: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value,
  });
}

function event(
  overrides: Partial<ProjectEvent> = {},
): ProjectEvent {
  return {
    id: "event-1",
    sequence: 1,
    schema_version: 1,
    project_id: "project-1",
    actor_source: "agent",
    resource_type: "project_profile",
    resource_id: "project-1",
    resource_revision: 2,
    action: "updated",
    payload: { changed_fields: ["state"] },
    deduplication_key: null,
    created_at: "2026-07-19T00:00:00Z",
    ...overrides,
  };
}
