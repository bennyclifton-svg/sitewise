import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
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

export function LlmModelSelector({ className }: { className?: string }) {
  const [models, setModels] = useState<ChatModelOption[]>(FALLBACK_CHAT_MODELS);
  const [defaultModel, setDefaultModel] = useState(FALLBACK_DEFAULT_MODEL);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const selectedModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectionSnapshot,
    getSelectionServerSnapshot,
  );

  useEffect(() => {
    let cancelled = false;
    void api
      .getLlmModels()
      .then((response) => {
        if (cancelled) return;
        if (response.models.length > 0) {
          setModels(response.models);
          setDefaultModel(response.default_model);
        }
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setModels(FALLBACK_CHAT_MODELS);
        setDefaultModel(FALLBACK_DEFAULT_MODEL);
        setLoadError(
          error instanceof Error
            ? error.message
            : "Could not load model list from backend.",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const effectiveValue = selectedModel ?? defaultModel;
  const title = loadError
    ? `${loadError} Using fallback model list.`
    : loading
      ? "Loading LLM models..."
      : "LLM model for chat and workflows";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <label className="sr-only" htmlFor="clerk-llm-model">
        LLM model
      </label>
      <select
        id="clerk-llm-model"
        className="h-8 min-w-[9rem] max-w-[12rem] truncate rounded-md border border-input bg-background px-2 text-xs text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-wait disabled:opacity-70"
        value={effectiveValue}
        disabled={loading}
        aria-label="LLM model"
        title={title}
        onChange={(event) => {
          const next = event.target.value;
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
