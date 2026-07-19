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

function event(): ProjectEvent {
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
  };
}
