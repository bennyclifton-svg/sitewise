import { useEffect, useRef } from "react";

/** Reattach to an existing turn; never resend the user's mutation request. */
export function useAgentStreamResume({
  turnId, streaming, paused, prepare, resume,
}: {
  turnId: string | null;
  streaming: boolean;
  paused: boolean;
  prepare: () => void;
  resume: () => Promise<void>;
}) {
  const callbacks = useRef({ prepare, resume });
  useEffect(() => { callbacks.current = { prepare, resume }; }, [prepare, resume]);
  useEffect(() => {
    if (!turnId || streaming || paused) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    async function reconnect() {
      if (disposed) return;
      callbacks.current.prepare();
      try {
        await callbacks.current.resume();
      } catch {
        // Status polling remains authoritative; a network error is not Stop.
      } finally {
        if (!disposed) timer = setTimeout(() => void reconnect(), 5000);
      }
    }
    timer = setTimeout(() => void reconnect(), 1000);
    return () => { disposed = true; clearTimeout(timer); };
  }, [turnId, streaming, paused]);
}
