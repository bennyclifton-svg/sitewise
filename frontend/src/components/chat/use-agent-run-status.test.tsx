import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAgentRunStatus } from "@/components/chat/use-agent-run-status";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({ api: { getAgentTurnStatus: vi.fn() } }));

describe("server run recovery", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.resetAllMocks(); });
  afterEach(() => { vi.useRealTimers(); });

  it("finds a disconnected run and reloads once it completes", async () => {
    vi.mocked(api.getAgentTurnStatus)
      .mockResolvedValueOnce({ turn_id: "turn", active: true, status: "running" })
      .mockResolvedValue({ turn_id: "turn", active: false, status: "completed" });
    const settled = vi.fn();
    const { result } = renderHook(() => useAgentRunStatus("chat", true, false, settled));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(result.current.run?.active).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(result.current.run?.status).toBe("completed");
    expect(settled).toHaveBeenCalledTimes(1);
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(settled).toHaveBeenCalledTimes(1);
  });

  it("reports an unavailable status without claiming the request stopped", async () => {
    vi.mocked(api.getAgentTurnStatus)
      .mockResolvedValueOnce({ turn_id: "turn", active: true, status: "running" })
      .mockRejectedValue(new Error("offline"));
    const settled = vi.fn();
    const { result } = renderHook(() => useAgentRunStatus("chat", true, false, settled));
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(result.current.unavailable).toBe(true);
    expect(result.current.run?.active).toBe(true);
    expect(settled).not.toHaveBeenCalled();
  });

  it("reloads a result that finished before the chat reopened", async () => {
    vi.mocked(api.getAgentTurnStatus).mockResolvedValue({ turn_id: "turn", active: false, status: "completed" });
    const settled = vi.fn();
    renderHook(() => useAgentRunStatus("chat", true, false, settled));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(settled).toHaveBeenCalledTimes(1);
  });
});
