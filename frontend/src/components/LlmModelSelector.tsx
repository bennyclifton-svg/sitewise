import { useSyncExternalStore } from "react";

import { MenuSelect } from "@/components/ui/menu-select";
import {
  getSelectedAgentModel,
  setSelectedAgentModel,
  subscribeSelectedAgentModel,
  type AgentModelOption,
} from "@/lib/agent-model";
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
    ? agent?.default_model ?? ""
    : legacy?.default_model ?? FALLBACK_DEFAULT_MODEL;
  const loadError = configuration.error instanceof Error
    ? configuration.error.message
    : null;
  const loading = configuration.isPending;
  const selectedLegacyModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectionSnapshot,
    getSelectionServerSnapshot,
  );
  const selectedAgentModel = useSyncExternalStore(
    subscribeSelectedAgentModel,
    getSelectedAgentModel,
    getSelectionServerSnapshot,
  );
  const selectedModel = mode === "agent" ? selectedAgentModel : selectedLegacyModel;
  const effectiveValue = selectedModel ?? defaultModel;
  const title = loadError
    ? `${loadError} Using fallback model list.`
    : loading
      ? "Loading LLM models..."
      : mode === "agent"
        ? "Choose the model tier Pi uses for this chat turn"
        : "Choose the model tier for legacy chat and workflows";
  const label = "Model tier";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)} title={title}>
      <label className="sr-only" htmlFor="clerk-llm-model">
        {label}
      </label>
      <MenuSelect
        id="clerk-llm-model"
        value={effectiveValue}
        disabled={loading || (mode === "agent" && models.length === 0)}
        aria-label={label}
        className={
          compact
            ? "h-7 w-auto max-w-[7rem] border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-2 focus-visible:ring-ring/30"
            : "h-8 min-w-[9rem] max-w-[12rem] px-2 text-xs"
        }
        options={models.map((model) => ({
          value: model.id,
          label: model.label,
        }))}
        onChange={(next) => {
          if (mode === "agent") {
            setSelectedAgentModel(next === defaultModel ? null : next);
            return;
          }
          if (next === defaultModel) {
            setSelectedChatModel(null);
            return;
          }
          setSelectedChatModel(next);
        }}
      />
    </div>
  );
}
