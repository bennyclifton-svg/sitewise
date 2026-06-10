const STORAGE_KEY = "clerk.chatModel";
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
  { id: "gpt-4.1-nano", label: "GPT-4.1 nano (fastest)", is_default: false },
  { id: "gpt-4o-mini", label: "GPT-4o mini (fast, default)", is_default: true },
  { id: "gpt-4.1-mini", label: "GPT-4.1 mini (fast)", is_default: false },
  { id: "gpt-4.1", label: "GPT-4.1 (capable)", is_default: false },
  { id: "gpt-4o", label: "GPT-4o (capable)", is_default: false },
  { id: "o4-mini", label: "o4-mini (reasoning, fast)", is_default: false },
  { id: "o3-mini", label: "o3-mini (reasoning)", is_default: false },
];

export const FALLBACK_DEFAULT_MODEL = "gpt-4o-mini";

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
