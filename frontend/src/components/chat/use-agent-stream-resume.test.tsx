import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAgentStreamResume } from "@/components/chat/use-agent-stream-resume";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("reconnects an existing turn with backoff without submitting a new request", async () => {
  const prepare = vi.fn();
  const resume = vi.fn().mockRejectedValue(new Error("offline"));
  const { unmount } = renderHook(() => useAgentStreamResume({ turnId: "turn", streaming: false, paused: false, prepare, resume }));
  await act(() => vi.advanceTimersByTimeAsync(1000));
  expect(prepare).toHaveBeenCalledOnce();
  expect(resume).toHaveBeenCalledOnce();
  await act(() => vi.advanceTimersByTimeAsync(4999));
  expect(resume).toHaveBeenCalledOnce();
  await act(() => vi.advanceTimersByTimeAsync(1));
  expect(resume).toHaveBeenCalledTimes(2);
  unmount();
  await act(() => vi.advanceTimersByTimeAsync(10000));
  expect(resume).toHaveBeenCalledTimes(2);
});

it("does not reconnect after explicit Stop or while already streaming", async () => {
  const prepare = vi.fn();
  const resume = vi.fn().mockResolvedValue(undefined);
  const { rerender } = renderHook(({ paused, streaming }) => useAgentStreamResume({ turnId: "turn", paused, streaming, prepare, resume }), { initialProps: { paused: false, streaming: false } });
  rerender({ paused: true, streaming: false });
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(resume).not.toHaveBeenCalled();
  rerender({ paused: false, streaming: true });
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(resume).not.toHaveBeenCalled();
});
