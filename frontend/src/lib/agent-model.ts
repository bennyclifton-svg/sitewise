import type { AgentRuntimeOption } from "@/lib/agent-runtime";
import { PI_RUNTIME_ID } from "@/lib/agent-runtime";

// Hermes key bumped for the GPT-5.6 migration: stored ids such as
// "openai-codex:gpt-5.5" are no longer in HERMES_MODEL_OPTIONS and the backend
// rejects an unknown agent_model. Pi ids were already 5.6, so that key stands.
const HERMES_STORAGE_KEY = "clerk.agentModel.v2";
const PI_STORAGE_KEY = "clerk.agentModel.pi";
const CHANGE_EVENT = "clerk:agent-model-change";

export const HERMES_DEFAULT_MODEL_ID = "__hermes_config__";

export type AgentModelOption = {
  id: string;
  label: string;
  is_default: boolean;
  provider: string | null;
  model: string | null;
};

export type AgentModelsResponse = {
  default_model: string;
  default_runtime: string;
  agent_runtime_enabled: boolean;
  models: AgentModelOption[];
  runtimes: AgentRuntimeOption[];
};

export type AgentConfigurationResponse = {
  agent: AgentModelsResponse;
  legacy: import("@/lib/chat-model").ChatModelsResponse;
};

function storageKeyForRuntime(runtimeId?: string | null): string {
  return runtimeId === PI_RUNTIME_ID ? PI_STORAGE_KEY : HERMES_STORAGE_KEY;
}

export function getSelectedAgentModel(runtimeId?: string | null): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(storageKeyForRuntime(runtimeId));
}

export function setSelectedAgentModel(
  modelId: string | null,
  runtimeId?: string | null,
): void {
  if (typeof window === "undefined") {
    return;
  }
  const storageKey = storageKeyForRuntime(runtimeId);
  if (modelId && (runtimeId === PI_RUNTIME_ID || modelId !== HERMES_DEFAULT_MODEL_ID)) {
    window.localStorage.setItem(storageKey, modelId);
  } else {
    window.localStorage.removeItem(storageKey);
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeSelectedAgentModel(
  onStoreChange: () => void,
): () => void {
  const onStorage = (event: StorageEvent) => {
    if (
      event.key === HERMES_STORAGE_KEY
      || event.key === PI_STORAGE_KEY
      || event.key === null
    ) {
      onStoreChange();
    }
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(CHANGE_EVENT, onStoreChange);
  };
}

export function agentModelPayload(): { agent_model?: string } {
  const selected = getSelectedAgentModel();
  return selected ? { agent_model: selected } : {};
}
