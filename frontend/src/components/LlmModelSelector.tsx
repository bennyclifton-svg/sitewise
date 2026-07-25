import { useSyncExternalStore } from "react";

import {
  HERMES_DEFAULT_MODEL_ID,
  getSelectedAgentModel,
  setSelectedAgentModel,
  subscribeSelectedAgentModel,
  type AgentModelOption,
} from "@/lib/agent-model";
import {
  HERMES_RUNTIME_ID,
  PI_RUNTIME_ID,
  getSelectedAgentRuntime,
  subscribeSelectedAgentRuntime,
} from "@/lib/agent-runtime";
import {
  FALLBACK_CHAT_MODELS,
  FALLBACK_DEFAULT_MODEL,
  getSelectedChatModel,
  setSelectedChatModel,
  subscribeSelectedChatModel,
  type ChatModelOption,
} from "@/lib/chat-model";
import { useAgentConfiguration } from "@/lib/queries/agent-configuration";
import { cn } from "@/lib/utils";

function getSelectionSnapshot(): string | null {
  return getSelectedChatModel();
}

function getSelectionServerSnapshot(): string | null {
  return null;
}

function getAgentRuntimeSnapshot(): string | null {
  return getSelectedAgentRuntime();
}

type SelectorMode = "agent" | "legacy";
type ModelOption = ChatModelOption | AgentModelOption;

export function LlmModelSelector({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const configuration = useAgentConfiguration();
  const agent = configuration.data?.agent;
  const legacy = configuration.data?.legacy;
  const mode: SelectorMode = agent?.agent_runtime_enabled ? "agent" : "legacy";
  const models: ModelOption[] = mode === "agent"
    ? agent?.models ?? []
    : legacy?.models ?? FALLBACK_CHAT_MODELS;
  const defaultModel = mode === "agent"
    ? agent?.default_model ?? HERMES_DEFAULT_MODEL_ID
    : legacy?.default_model ?? FALLBACK_DEFAULT_MODEL;
  const defaultRuntime = agent?.default_runtime ?? HERMES_RUNTIME_ID;
  const runtimes = agent?.runtimes ?? [];
  const loadError = configuration.error instanceof Error
    ? configuration.error.message
    : null;
  const loading = configuration.isPending;
  const selectedLegacyModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectionSnapshot,
    getSelectionServerSnapshot,
  );
  const selectedAgentRuntime = useSyncExternalStore(
    subscribeSelectedAgentRuntime,
    getAgentRuntimeSnapshot,
    getSelectionServerSnapshot,
  );

  const effectiveAgentRuntime = selectedAgentRuntime ?? defaultRuntime;
  const selectedAgentModel = useSyncExternalStore(
    subscribeSelectedAgentModel,
    () => getSelectedAgentModel(effectiveAgentRuntime),
    getSelectionServerSnapshot,
  );
  const piRuntime = runtimes.find((runtime) => runtime.id === PI_RUNTIME_ID);
  const isPiMode = mode === "agent" && effectiveAgentRuntime === PI_RUNTIME_ID;
  const piModels = piRuntime?.model_options ?? [];
  const piDefaultModel = piRuntime?.default_model
    ?? piModels.find((model) => model.is_default)?.id
    ?? null;
  const selectedModel = mode === "agent" ? selectedAgentModel : selectedLegacyModel;
  const selectedPiModel = piModels.some((model) => model.id === selectedAgentModel)
    ? selectedAgentModel
    : null;
  const displayModels = isPiMode ? piModels : models;
  const effectiveValue = isPiMode
    ? selectedPiModel ?? piDefaultModel ?? ""
    : selectedModel ?? defaultModel;
  const title = loadError
    ? `${loadError} Using fallback model list.`
    : loading
      ? "Loading LLM models..."
      : isPiMode
        ? "Choose the Pi model for this chat turn"
        : mode === "agent"
        ? "Hermes model for agent chat"
        : "LLM model for legacy chat and workflows";
  const label = isPiMode ? "Pi model" : mode === "agent" ? "Hermes model" : "LLM model";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <label className="sr-only" htmlFor="clerk-llm-model">
        {label}
      </label>
      <select
        id="clerk-llm-model"
        className={cn(
          compact
            ? "h-7 w-auto max-w-[7rem] truncate border-0 bg-transparent px-1 text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70"
            : "h-8 min-w-[9rem] max-w-[12rem] truncate rounded-md border border-input bg-background px-2 text-xs text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70",
          className,
        )}
        value={effectiveValue}
        disabled={loading || (isPiMode && displayModels.length === 0)}
        aria-label={label}
        title={title}
        onChange={(event) => {
          const next = event.target.value;
          if (isPiMode) {
            setSelectedAgentModel(
              next === piDefaultModel ? null : next,
              PI_RUNTIME_ID,
            );
            return;
          }
          if (mode === "agent") {
            setSelectedAgentModel(
              next === defaultModel || next === HERMES_DEFAULT_MODEL_ID ? null : next,
              effectiveAgentRuntime,
            );
            return;
          }
          if (next === defaultModel) {
            setSelectedChatModel(null);
            return;
          }
          setSelectedChatModel(next);
        }}
      >
        {displayModels.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label}
          </option>
        ))}
      </select>
    </div>
  );
}
