const STORAGE_KEY = "clerk.agentRuntime";
const CHANGE_EVENT = "clerk:agent-runtime-change";

export const HERMES_RUNTIME_ID = "hermes";
export const PI_RUNTIME_ID = "pi";

export type AgentRuntimeOption = {
  id: string;
  label: string;
  enabled: boolean;
  description?: string | null;
};

export function getSelectedAgentRuntime(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setSelectedAgentRuntime(runtimeId: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (runtimeId && runtimeId !== HERMES_RUNTIME_ID) {
    window.localStorage.setItem(STORAGE_KEY, runtimeId);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeSelectedAgentRuntime(
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

export function agentRuntimePayload(
  defaultRuntime: string,
): { agent_runtime?: string } {
  const selected = getSelectedAgentRuntime();
  if (selected && selected !== defaultRuntime) {
    return { agent_runtime: selected };
  }
  return {};
}
