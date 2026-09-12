import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { useWorkflowRun, waitForWorkflowRun, workflowRunKeys } from "@/lib/queries/workflow-runs";
import type { WorkflowRun } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getWorkflowRun: vi.fn(),
  },
}));

describe("waitForWorkflowRun", () => {
  it("reuses status fetched by a mounted workflow card", async () => {
    vi.useFakeTimers();
    const initial = { id: "run-1", project_id: "project-1", state: "running" } as WorkflowRun;
    vi.mocked(api.getWorkflowRun).mockResolvedValueOnce(initial).mockResolvedValue({ ...initial, state: "complete" });
    const client = new QueryClient();
    const result = waitForWorkflowRun(client, "project-1", initial);
    await vi.advanceTimersByTimeAsync(500);
    const hook = renderHook(() => useWorkflowRun("project-1", initial.id), {
      wrapper: ({ children }: { children: ReactNode }) => createElement(QueryClientProvider, { client }, children),
    });
    await act(async () => { await vi.advanceTimersByTimeAsync(1_500); });
    await expect(result).resolves.toMatchObject({ state: "complete" });
    expect(api.getWorkflowRun).toHaveBeenCalledTimes(2);
    hook.unmount();
    client.clear();
  });
  it("shares a status request between concurrent waiters", async () => {
    vi.useFakeTimers();
    const initial = { id: "run-1", project_id: "project-1", state: "running" } as WorkflowRun;
    vi.mocked(api.getWorkflowRun).mockResolvedValue({ ...initial, state: "complete" });
    const client = new QueryClient();
    const first = waitForWorkflowRun(client, "project-1", initial);
    const second = waitForWorkflowRun(client, "project-1", initial);
    await vi.advanceTimersByTimeAsync(1_000);
    await expect(first).resolves.toMatchObject({ state: "complete" });
    await expect(second).resolves.toMatchObject({ state: "complete" });
    expect(api.getWorkflowRun).toHaveBeenCalledTimes(1);
    client.clear();
  });

  it("does not overwrite a completed cached run with an older initial response", async () => {
    const initial = { id: "run-1", project_id: "project-1", state: "running" } as WorkflowRun;
    const client = new QueryClient();
    client.setQueryData(workflowRunKeys.run("project-1", initial.id), { ...initial, state: "complete" });
    await expect(waitForWorkflowRun(client, "project-1", initial)).resolves.toMatchObject({ state: "complete" });
    expect(api.getWorkflowRun).not.toHaveBeenCalled();
    client.clear();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("keeps polling when a durable run status request times out", async () => {
    vi.useFakeTimers();
    vi.mocked(api.getWorkflowRun)
      .mockRejectedValueOnce(
        new ApiError("Request timed out.", { kind: "timeout" }),
      )
      .mockResolvedValueOnce({
        id: "run-1",
        project_id: "project-1",
        state: "complete",
      } as WorkflowRun);
    const queryClient = new QueryClient();

    const result = waitForWorkflowRun(queryClient, "project-1", {
      id: "run-1",
      project_id: "project-1",
      state: "running",
    } as WorkflowRun);

    await vi.advanceTimersByTimeAsync(3_000);

    await expect(result).resolves.toMatchObject({ state: "complete" });
    expect(api.getWorkflowRun).toHaveBeenCalledTimes(2);
  });
});
