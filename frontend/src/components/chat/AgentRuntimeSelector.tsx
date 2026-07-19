import { useSyncExternalStore } from "react";

import {
  HERMES_RUNTIME_ID,
  getSelectedAgentRuntime,
  setSelectedAgentRuntime,
  subscribeSelectedAgentRuntime,
} from "@/lib/agent-runtime";
import { useAgentConfiguration } from "@/lib/queries/agent-configuration";

type AgentRuntimeSelectorProps = {
  className?: string;
  compact?: boolean;
};

export function AgentRuntimeSelector({ className, compact = false }: AgentRuntimeSelectorProps) {
  const configuration = useAgentConfiguration();
  const runtimes = configuration.data?.agent.runtimes ?? [];
  const defaultRuntime = configuration.data?.agent.default_runtime ?? HERMES_RUNTIME_ID;
  const loading = configuration.isPending;
  const selectedRuntime = useSyncExternalStore(
    subscribeSelectedAgentRuntime,
    getSelectedAgentRuntime,
    () => null,
  );

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
