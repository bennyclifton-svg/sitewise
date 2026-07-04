import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import {
  HERMES_DEFAULT_MODEL_ID,
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
import { cn } from "@/lib/utils";

function getSelectionSnapshot(): string | null {
  return getSelectedChatModel();
}

function getSelectionServerSnapshot(): string | null {
  return null;
}

function getAgentSelectionSnapshot(): string | null {
  return getSelectedAgentModel();
}

type SelectorMode = "agent" | "legacy";
type ModelOption = ChatModelOption | AgentModelOption;

export function LlmModelSelector({ className }: { className?: string }) {
  const [mode, setMode] = useState<SelectorMode>("legacy");
  const [models, setModels] = useState<ModelOption[]>(FALLBACK_CHAT_MODELS);
  const [defaultModel, setDefaultModel] = useState(FALLBACK_DEFAULT_MODEL);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const selectedLegacyModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectionSnapshot,
    getSelectionServerSnapshot,
  );
  const selectedAgentModel = useSyncExternalStore(
    subscribeSelectedAgentModel,
    getAgentSelectionSnapshot,
    getSelectionServerSnapshot,
  );

  useEffect(() => {
    let cancelled = false;
    async function loadModels() {
      setLoading(true);
      try {
        const agentResponse = await api.getAgentModels();
        if (cancelled) return;
        if (agentResponse.agent_runtime_enabled) {
          setMode("agent");
          setModels(agentResponse.models);
          setDefaultModel(agentResponse.default_model);
          setLoadError(null);
          return;
        }

        const response = await api.getLlmModels();
        if (cancelled) return;
        setMode("legacy");
        if (response.models.length > 0) {
          setModels(response.models);
          setDefaultModel(response.default_model);
        }
        setLoadError(null);
      } catch (error: unknown) {
        if (cancelled) return;
        setMode("legacy");
        setModels(FALLBACK_CHAT_MODELS);
        setDefaultModel(FALLBACK_DEFAULT_MODEL);
        setLoadError(
          error instanceof Error
            ? error.message
            : "Could not load model list from backend.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedModel =
    mode === "agent" ? selectedAgentModel : selectedLegacyModel;
  const effectiveValue = selectedModel ?? defaultModel;
  const title = loadError
    ? `${loadError} Using fallback model list.`
    : loading
      ? "Loading LLM models..."
      : mode === "agent"
        ? "Hermes model for agent chat"
        : "LLM model for legacy chat and workflows";
  const label = mode === "agent" ? "Hermes model" : "LLM model";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <label className="sr-only" htmlFor="clerk-llm-model">
        {label}
      </label>
      <select
        id="clerk-llm-model"
        className="h-8 min-w-[9rem] max-w-[12rem] truncate rounded-md border border-input bg-background px-2 text-xs text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70"
        value={effectiveValue}
        disabled={loading}
        aria-label={label}
        title={title}
        onChange={(event) => {
          const next = event.target.value;
          if (mode === "agent") {
            setSelectedAgentModel(
              next === defaultModel || next === HERMES_DEFAULT_MODEL_ID ? null : next,
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
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label}
          </option>
        ))}
      </select>
    </div>
  );
}
