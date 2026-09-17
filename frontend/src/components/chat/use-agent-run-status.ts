import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

export function useAgentRunStatus(
  threadId: string,
  enabled: boolean,
  streaming: boolean,
  onSettled: () => void,
) {
  const [runState, setRun] = useState<{ threadId: string; value: Awaited<ReturnType<typeof api.getAgentTurnStatus>> } | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const settledRef = useRef(onSettled);
  useEffect(() => { settledRef.current = onSettled; }, [onSettled]);

  useEffect(() => {
    if (!enabled || streaming) return;
    let disposed = false;
    let wasActive = false;
    let settledTurnId: string | null = null;
    let timer: ReturnType<typeof setTimeout>;
    async function check() {
      try {
        const next = await api.getAgentTurnStatus(threadId);
        if (disposed) return;
        setRun({ threadId, value: next });
        setUnavailable(false);
        if (!next.active && next.turn_id !== settledTurnId && (wasActive || ["completed", "interrupted", "cancelled"].includes(next.status))) {
          settledTurnId = next.turn_id;
          settledRef.current();
        }
        wasActive = next.active;
      } catch {
        if (!disposed) setUnavailable(true);
      } finally {
        if (!disposed) timer = setTimeout(() => void check(), 3000);
      }
    }
    void check();
    return () => { disposed = true; clearTimeout(timer); };
  }, [enabled, streaming, threadId]);

  const current = enabled && !streaming && runState?.threadId === threadId;
  return { run: current ? runState.value : null, unavailable: enabled && !streaming && unavailable };
}
