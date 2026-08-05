const STORAGE_KEY = "clerk.agentModel.pi";
const CHANGE_EVENT = "clerk:agent-model-change";

export type AgentModelOption = {
  id: string;
  label: string;
  is_default: boolean;
  provider: string;
  model: string;
};

export type AgentModelsResponse = {
  default_model: string;
  agent_runtime_enabled: boolean;
  models: AgentModelOption[];
};

export type AgentConfigurationResponse = {
  agent: AgentModelsResponse;
  legacy: import("@/lib/chat-model").ChatModelsResponse;
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
  if (modelId) {
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
    if (
      event.key === STORAGE_KEY || event.key === null
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
