import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

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
import {
  appendDictationTranscript,
  getSpeechRecognitionConstructor,
  isSpeechRecognitionSupported,
  type SpeechRecognitionLike,
} from "@/lib/speech-recognition";
import { cn } from "@/lib/utils";

const MIN_TEXTAREA_ROWS = 1;
const MAX_TEXTAREA_ROWS = 6;
const HOLD_TO_RECORD_MS = 180;

const DEPTH_LABELS = ["Fast", "Balanced", "Complex"] as const;

type ModelOption = ChatModelOption | AgentModelOption;

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  isBusy: boolean;
  crossProject?: boolean;
  onCrossProjectChange?: (value: boolean) => void;
  showScopeControls?: boolean;
  collapsed?: boolean;
  collapsible?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
};

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  isBusy,
  crossProject = false,
  onCrossProjectChange,
  showScopeControls = false,
  collapsed = false,
  collapsible = false,
  onCollapsedChange,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const holdTimerRef = useRef<number | null>(null);
  const holdModeRef = useRef(false);
  const suppressClickRef = useRef(false);
  const startedOnPointerRef = useRef(false);
  const [fieldFocused, setFieldFocused] = useState(false);
  const [listening, setListening] = useState(false);
  const voiceSupported = isSpeechRecognitionSupported();
  const micDisabled = !voiceSupported || isBusy;
  const { models, defaultModel, effectiveValue, selectModel, loading } =
    useComposerModelTier();

  useEffect(() => {
    valueRef.current = value;
    onChangeRef.current = onChange;
  }, [value, onChange]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const lineHeight = Number.parseInt(getComputedStyle(textarea).lineHeight, 10) || 20;
    const maxHeight = lineHeight * MAX_TEXTAREA_ROWS;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, [value]);

  useEffect(() => {
    return () => {
      if (holdTimerRef.current !== null) {
        window.clearTimeout(holdTimerRef.current);
      }
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (isBusy && recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, [isBusy]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isBusy && value.trim()) {
        onSubmit();
      }
    }
  }

  function clearHoldTimer() {
    if (holdTimerRef.current !== null) {
      window.clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
  }

  function stopVoiceInput() {
    clearHoldTimer();
    holdModeRef.current = false;
    recognitionRef.current?.stop();
  }

  function startVoiceInput() {
    if (!voiceSupported || isBusy || recognitionRef.current) return;

    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) return;

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang =
      typeof navigator !== "undefined" && navigator.language
        ? navigator.language
        : "en-AU";

    recognition.onresult = (event) => {
      let spoken = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result?.isFinal) {
          spoken += result[0]?.transcript ?? "";
        }
      }
      if (!spoken.trim()) return;
      onChangeRef.current(
        appendDictationTranscript(valueRef.current, spoken),
      );
    };

    recognition.onerror = (event) => {
      if (event.error === "aborted" || event.error === "no-speech") return;
      setListening(false);
      recognitionRef.current = null;
    };

    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
      holdModeRef.current = false;
      clearHoldTimer();
    };

    recognitionRef.current = recognition;
    setListening(true);
    try {
      recognition.start();
    } catch {
      setListening(false);
      recognitionRef.current = null;
    }
  }

  function handleMicPointerDown(event: React.PointerEvent<HTMLButtonElement>) {
    if (micDisabled || event.button !== 0) return;
    event.preventDefault();

    if (listening) return;

    holdModeRef.current = false;
    suppressClickRef.current = false;
    startedOnPointerRef.current = true;
    startVoiceInput();
    holdTimerRef.current = window.setTimeout(() => {
      holdModeRef.current = true;
      suppressClickRef.current = true;
      holdTimerRef.current = null;
    }, HOLD_TO_RECORD_MS);
  }

  function handleMicPointerUp() {
    clearHoldTimer();
    if (holdModeRef.current) {
      stopVoiceInput();
    }
  }

  function handleMicPointerLeave() {
    if (holdModeRef.current) {
      stopVoiceInput();
    } else {
      clearHoldTimer();
    }
  }

  function handleMicClick() {
    if (micDisabled) return;
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      startedOnPointerRef.current = false;
      return;
    }
    if (startedOnPointerRef.current) {
      // Short press already started listening on pointerdown; keep it running.
      startedOnPointerRef.current = false;
      return;
    }
    if (listening) {
      stopVoiceInput();
      return;
    }
    startVoiceInput();
  }

  const canSubmit = !isBusy && value.trim() !== "";
  // Decorative sky caret for the empty idle state; hide once the native caret takes over.
  const showCaret = value.trim() === "" && !isBusy && !fieldFocused;
  const micLabel = !voiceSupported
    ? "Voice input not supported in this browser"
    : listening
      ? "Stop recording"
      : "Click or hold to record";

  return (
    <form
      className="sw-composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubmit) onSubmit();
      }}
    >
      {collapsible ? (
        <button
          type="button"
          className="sw-collapse"
          aria-label={collapsed ? "Expand chat" : "Collapse chat"}
          title={collapsed ? "Expand chat" : "Collapse chat"}
          onClick={() => onCollapsedChange?.(!collapsed)}
        >
          <CollapseChevron collapsed={collapsed} />
          <span className="sw-collapse-grip" aria-hidden="true" />
          <CollapseChevron collapsed={collapsed} />
        </button>
      ) : null}

      <div className="sw-body">
        <div className="sw-main">
          <label className="sw-field">
            {showCaret ? <span className="sw-caret" aria-hidden="true" /> : null}
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onFocus={() => setFieldFocused(true)}
              onBlur={() => setFieldFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your project documents"
              disabled={isBusy}
              aria-label="Message"
              rows={MIN_TEXTAREA_ROWS}
            />
          </label>

          <div className="sw-controls">
            <div className="sw-depth" role="group" aria-label="Reasoning depth">
              {DEPTH_LABELS.flatMap((label, index, labels) => {
                const model = models.find((option) => option.label === label);
                if (!model) return [];
                const pressed = model.id === effectiveValue;
                const nodes: ReactNode[] = [
                  <button
                    key={model.id}
                    type="button"
                    aria-pressed={pressed}
                    disabled={loading || isBusy}
                    title={`Model tier: ${label}`}
                    onClick={() => selectModel(model.id, defaultModel)}
                  >
                    <DepthIcon label={label} active={pressed} />
                    {label}
                  </button>,
                ];
                const hasFollowing = labels
                  .slice(index + 1)
                  .some((next) => models.some((option) => option.label === next));
                if (hasFollowing) {
                  nodes.push(<hr key={`${model.id}-rule`} />);
                }
                return nodes;
              })}
            </div>

            {showScopeControls ? (
              <div
                className="sw-depth"
                role="group"
                aria-label="Search scope"
              >
                <button
                  type="button"
                  aria-pressed={!crossProject}
                  onClick={() => onCrossProjectChange?.(false)}
                >
                  Project
                </button>
                <button
                  type="button"
                  aria-pressed={crossProject}
                  onClick={() => onCrossProjectChange?.(true)}
                >
                  Cross-project
                </button>
              </div>
            ) : null}

            <div className="sw-spacer" />
          </div>
        </div>

        <div className={cn("sw-voice", listening && "is-listening")}>
          {listening ? (
            <div
              className="sw-voice-meter"
              data-testid="voice-cube-meter"
              aria-hidden="true"
            >
              <span className="sw-voice-bar" />
              <span className="sw-voice-bar" />
              <span className="sw-voice-bar" />
            </div>
          ) : null}
          <button
            type="button"
            className={cn("sw-icon", "sw-mic", listening && "is-listening")}
            disabled={micDisabled}
            aria-label={micLabel}
            aria-pressed={listening}
            title={micLabel}
            onClick={handleMicClick}
            onPointerDown={handleMicPointerDown}
            onPointerUp={handleMicPointerUp}
            onPointerCancel={handleMicPointerUp}
            onPointerLeave={handleMicPointerLeave}
          >
            <SolidMicIcon />
          </button>
        </div>

        {isBusy ? (
          <button
            type="button"
            className="sw-send"
            aria-label="Stop"
            title="Stop"
            onClick={() => onStop?.()}
          >
            <StopMark />
          </button>
        ) : (
          <button
            type="submit"
            className="sw-send"
            aria-label="Ask SiteWise"
            title="Ask SiteWise"
            disabled={!canSubmit}
          >
            <SendMark />
          </button>
        )}
      </div>
    </form>
  );
}

function useComposerModelTier() {
  const configuration = useAgentConfiguration();
  const agent = configuration.data?.agent;
  const legacy = configuration.data?.legacy;
  const mode = agent?.agent_runtime_enabled ? "agent" : "legacy";
  const configuredModels: ModelOption[] =
    mode === "agent" ? agent?.models ?? [] : legacy?.models ?? [];
  const models =
    configuredModels.length > 0 ? configuredModels : FALLBACK_CHAT_MODELS;
  const defaultModel =
    mode === "agent"
      ? agent?.default_model || FALLBACK_DEFAULT_MODEL
      : legacy?.default_model ?? FALLBACK_DEFAULT_MODEL;

  const selectedLegacyModel = useSyncExternalStore(
    subscribeSelectedChatModel,
    getSelectedChatModel,
    () => null,
  );
  const selectedAgentModel = useSyncExternalStore(
    subscribeSelectedAgentModel,
    getSelectedAgentModel,
    () => null,
  );
  const selectedModel = mode === "agent" ? selectedAgentModel : selectedLegacyModel;
  const effectiveValue = selectedModel ?? defaultModel;

  function selectModel(modelId: string, fallbackDefault: string) {
    if (mode === "agent") {
      setSelectedAgentModel(modelId === fallbackDefault ? null : modelId);
      return;
    }
    setSelectedChatModel(modelId === fallbackDefault ? null : modelId);
  }

  return {
    models,
    defaultModel,
    effectiveValue,
    selectModel,
    loading: configuration.isPending,
  };
}

function CollapseChevron({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="12"
      height="8"
      viewBox="0 0 12 8"
      fill="none"
      aria-hidden="true"
      className={cn("sw-collapse-chevron", collapsed && "rotate-180")}
    >
      <path
        d="M1.2 1.4L6 6.2L10.8 1.4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SolidMicIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 14a3.5 3.5 0 0 0 3.5-3.5v-5a3.5 3.5 0 1 0-7 0v5A3.5 3.5 0 0 0 12 14Z"
      />
      <path
        fill="currentColor"
        d="M6.25 10.5a.75.75 0 0 0-1.5 0 7.25 7.25 0 0 0 6.5 7.21V20.5h-2a.75.75 0 0 0 0 1.5h5.5a.75.75 0 0 0 0-1.5h-2v-2.79a7.25 7.25 0 0 0 6.5-7.21.75.75 0 0 0-1.5 0 5.75 5.75 0 0 1-11.5 0Z"
      />
    </svg>
  );
}

function DepthIcon({
  label,
  active,
}: {
  label: (typeof DEPTH_LABELS)[number];
  active: boolean;
}) {
  if (label === "Fast") {
    return (
      <svg width="12" height="12" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <path
          d="M7.5 3.6L12.2 6.3L7.5 9L2.8 6.3Z"
          fill="currentColor"
          opacity=".85"
        />
      </svg>
    );
  }
  if (label === "Balanced") {
    return (
      <svg width="12" height="12" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <path
          d="M7.5 1.9L12.2 4.6L7.5 7.3L2.8 4.6Z"
          fill={active ? "#7FB0E4" : "currentColor"}
          opacity={active ? 1 : 0.85}
        />
        <path
          d="M7.5 6.1L12.2 8.8L7.5 11.5L2.8 8.8Z"
          fill={active ? "#2F72C4" : "currentColor"}
          opacity={active ? 1 : 0.55}
        />
      </svg>
    );
  }
  return (
    <svg width="12" height="12" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path
        d="M7.5 0.9L12.2 3.6L7.5 6.3L2.8 3.6Z"
        fill="currentColor"
        opacity=".9"
      />
      <path
        d="M7.5 4.6L12.2 7.3L7.5 10L2.8 7.3Z"
        fill="currentColor"
        opacity=".6"
      />
      <path
        d="M7.5 8.3L12.2 11L7.5 13.7L2.8 11Z"
        fill="currentColor"
        opacity=".35"
      />
    </svg>
  );
}

function SendMark() {
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden="true">
      <path d="M22 5.5L37 14.1L22 22.7L7 14.1Z" fill="#2C3037" />
      <path d="M22 22.7L7 31.3L22 39.9Z" fill="#D6D6D0" />
      <path d="M22 22.7L37 14.1L37 31.3Z" fill="#123564" />
      <path d="M22 22.7L37 31.3L22 39.9Z" fill="#2F72C4" />
      <path
        d="M22 22.7L37 14.1"
        stroke="#A9C6E8"
        strokeWidth="1"
        opacity=".32"
      />
      <path
        d="M22 22.7L7 14.1"
        stroke="#8C95A2"
        strokeWidth="1"
        opacity=".26"
      />
    </svg>
  );
}

function StopMark() {
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden="true">
      <rect x="14" y="14" width="16" height="16" fill="currentColor" opacity=".85" />
    </svg>
  );
}
