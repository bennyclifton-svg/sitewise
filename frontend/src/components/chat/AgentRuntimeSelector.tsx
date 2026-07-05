import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import {
  HERMES_RUNTIME_ID,
  getSelectedAgentRuntime,
  setSelectedAgentRuntime,
  subscribeSelectedAgentRuntime,
  type AgentRuntimeOption,
} from "@/lib/agent-runtime";

type AgentRuntimeSelectorProps = {
  className?: string;
  compact?: boolean;
};

export function AgentRuntimeSelector({ className, compact = false }: AgentRuntimeSelectorProps) {
  const [runtimes, setRuntimes] = useState<AgentRuntimeOption[]>([]);
  const [defaultRuntime, setDefaultRuntime] = useState(HERMES_RUNTIME_ID);
  const [loading, setLoading] = useState(true);
  const selectedRuntime = useSyncExternalStore(
    subscribeSelectedAgentRuntime,
    getSelectedAgentRuntime,
    () => null,
  );

  useEffect(() => {
    let cancelled = false;
    async function loadRuntimes() {
      setLoading(true);
      try {
        const response = await api.getAgentModels();
        if (cancelled) return;
        setRuntimes(response.runtimes ?? []);
        setDefaultRuntime(response.default_runtime ?? HERMES_RUNTIME_ID);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadRuntimes();
    return () => {
      cancelled = true;
    };
  }, []);

  const enabledRuntimes = runtimes.filter((runtime) => runtime.enabled);
  if (enabledRuntimes.length <= 1) {
    return null;
  }

  const effectiveValue = selectedRuntime ?? defaultRuntime;

  return (
    <div className={className}>
      <label className="sr-only" htmlFor="clerk-agent-runtime">
        Agent runtime
      </label>
      <select
        id="clerk-agent-runtime"
        className={
          compact
            ? "h-7 w-auto max-w-[5.5rem] truncate border-0 bg-transparent px-1 text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70"
            : "h-8 w-full rounded-md border border-input bg-background px-2 text-xs text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70"
        }
        value={effectiveValue}
        disabled={loading}
        aria-label="Agent runtime"
        title="Choose Hermes or Pi for project chat turns"
        onChange={(event) => {
          const next = event.target.value;
          setSelectedAgentRuntime(
            next === defaultRuntime ? null : next,
          );
        }}
      >
        {enabledRuntimes.map((runtime) => (
          <option key={runtime.id} value={runtime.id}>
            {runtime.label}
          </option>
        ))}
      </select>
    </div>
  );
}
