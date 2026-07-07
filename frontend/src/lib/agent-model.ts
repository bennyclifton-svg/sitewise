const STORAGE_KEY = "clerk.agentModel";
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

export type AgentRuntimeOption = {
  id: string;
  label: string;
  enabled: boolean;
  description?: string | null;
  provider?: string | null;
  model?: string | null;
  model_label?: string | null;
};

export function getSelectedAgentModel(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setSelectedAgentModel(modelId: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (modelId && modelId !== HERMES_DEFAULT_MODEL_ID) {
    window.localStorage.setItem(STORAGE_KEY, modelId);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeSelectedAgentModel(
  onStoreChange: () => void,
): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY || event.key === null) {
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
