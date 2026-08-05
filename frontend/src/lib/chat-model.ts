// Key bumped for the GPT-5.6 migration: stored selections named models that are
// no longer allowlisted, and the backend rejects an unknown chat_model outright.
const STORAGE_KEY = "clerk.chatModel.v2";
const CHANGE_EVENT = "clerk:chat-model-change";

export type ChatModelOption = {
  id: string;
  label: string;
  is_default: boolean;
};

export type ChatModelsResponse = {
  default_model: string;
  models: ChatModelOption[];
};

export const FALLBACK_CHAT_MODELS: ChatModelOption[] = [
  { id: "gpt-5.6-luna", label: "Fast", is_default: true },
  { id: "gpt-5.6-terra", label: "Balanced", is_default: false },
  { id: "gpt-5.6-sol", label: "Complex", is_default: false },
];

export const FALLBACK_DEFAULT_MODEL = "gpt-5.6-luna";

export function getSelectedChatModel(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setSelectedChatModel(modelId: string | null): void {
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

export function subscribeSelectedChatModel(onStoreChange: () => void): () => void {
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

export function workflowChatModelPayload(): { chat_model?: string } {
  const selected = getSelectedChatModel();
  return selected ? { chat_model: selected } : {};
}
