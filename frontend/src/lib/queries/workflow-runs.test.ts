import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { waitForWorkflowRun } from "@/lib/queries/workflow-runs";
import type { WorkflowRun } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getWorkflowRun: vi.fn(),
  },
}));

describe("waitForWorkflowRun", () => {
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
