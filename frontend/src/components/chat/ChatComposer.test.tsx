import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/components/chat/ChatComposer";

vi.mock("@/lib/queries/agent-configuration", () => ({
  useAgentConfiguration: () => ({
    data: {
      agent: {
        agent_runtime_enabled: true,
        default_model: "openai:gpt-5.6-luna",
        models: [
          { id: "openai:gpt-5.6-luna", label: "Fast", is_default: true },
          { id: "xai:grok-4.6", label: "Thorough", is_default: false },
        ],
      },
      legacy: { default_model: "gpt-5.6-luna", models: [] },
    },
    isPending: false,
    error: null,
  }),
}));

type RecognitionHandler = ((event: unknown) => void) | null;

class MockSpeechRecognition {
  continuous = false;
  interimResults = false;
  lang = "";
  onresult: RecognitionHandler = null;
  onerror: RecognitionHandler = null;
  onend: (() => void) | null = null;
  start = vi.fn(() => {
    MockSpeechRecognition.instances.push(this);
  });
  stop = vi.fn(() => {
    this.onend?.();
  });
  abort = vi.fn(() => {
    this.onend?.();
  });

  static instances: MockSpeechRecognition[] = [];

  static reset() {
    MockSpeechRecognition.instances = [];
  }

  emitResult(transcript: string, isFinal = true) {
    this.onresult?.({
      results: [
        {
          0: { transcript },
          isFinal,
          length: 1,
        },
      ],
      resultIndex: 0,
    });
  }

  emitError(error: string) {
    this.onerror?.({ error });
  }
}

function renderComposer(overrides: {
  value?: string;
  onChange?: (value: string) => void;
  isBusy?: boolean;
} = {}) {
  const onChange = overrides.onChange ?? vi.fn();
  const onSubmit = vi.fn();
  render(
    <ChatComposer
      value={overrides.value ?? ""}
      onChange={onChange}
      onSubmit={onSubmit}
      isBusy={overrides.isBusy ?? false}
    />,
  );
  return { onChange, onSubmit };
}

describe("ChatComposer voice input", () => {
  beforeEach(() => {
    MockSpeechRecognition.reset();
    vi.stubGlobal("SpeechRecognition", MockSpeechRecognition);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("disables the mic when speech recognition is unavailable", () => {
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
    renderComposer();

    const mic = screen.getByRole("button", { name: /voice input/i });
    expect(mic).toBeDisabled();
    expect(mic).toHaveAttribute(
      "title",
      expect.stringMatching(/not supported/i),
    );
  });

  it("enables the mic when speech recognition is available", () => {
    renderComposer();

    const mic = screen.getByRole("button", {
      name: "Click or hold to record",
    });
    expect(mic).toBeEnabled();
    expect(mic).toHaveAttribute("title", "Click or hold to record");
  });

  it("starts recognition and appends the final transcript", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderComposer({ value: "Check ", onChange });

    await user.click(
      screen.getByRole("button", { name: "Click or hold to record" }),
    );

    expect(MockSpeechRecognition.instances).toHaveLength(1);
    const recognition = MockSpeechRecognition.instances[0]!;
    expect(recognition.start).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("button", { name: "Stop recording" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("voice-cube-meter")).toBeInTheDocument();

    recognition.emitResult("bearing capacity");
    expect(onChange).toHaveBeenCalledWith("Check bearing capacity");
  });

  it("stops recognition when the mic is clicked while listening", async () => {
    const user = userEvent.setup();
    renderComposer();

    await user.click(
      screen.getByRole("button", { name: "Click or hold to record" }),
    );
    const recognition = MockSpeechRecognition.instances[0]!;

    await user.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(recognition.stop).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("button", { name: "Click or hold to record" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("voice-cube-meter")).not.toBeInTheDocument();
  });

  it("stops on a second pointer down while listening", () => {
    renderComposer();

    const mic = screen.getByRole("button", {
      name: "Click or hold to record",
    });
    fireEvent.pointerDown(mic);
    expect(
      screen.getByRole("button", { name: "Stop recording" }),
    ).toBeInTheDocument();

    const recognition = MockSpeechRecognition.instances[0]!;
    fireEvent.pointerDown(mic);

    expect(recognition.stop).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("button", { name: "Click or hold to record" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("voice-cube-meter")).not.toBeInTheDocument();
  });

  it("clears the listening UI even when recognition stop does not fire onend", () => {
    renderComposer();

    const mic = screen.getByRole("button", {
      name: "Click or hold to record",
    });
    fireEvent.pointerDown(mic);
    const recognition = MockSpeechRecognition.instances[0]!;
    recognition.stop = vi.fn();

    fireEvent.pointerDown(mic);

    expect(recognition.stop).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("button", { name: "Click or hold to record" }),
    ).toBeInTheDocument();
  });

  it("starts on press and stops on release when held", () => {
    vi.useFakeTimers();
    renderComposer();

    const mic = screen.getByRole("button", {
      name: "Click or hold to record",
    });
    fireEvent.pointerDown(mic);
    expect(MockSpeechRecognition.instances).toHaveLength(1);

    vi.advanceTimersByTime(220);
    fireEvent.pointerUp(mic);

    const recognition = MockSpeechRecognition.instances[0]!;
    expect(recognition.stop).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("disables the mic while the chat is busy", () => {
    renderComposer({ isBusy: true });

    expect(
      screen.getByRole("button", { name: /click or hold to record|voice input/i }),
    ).toBeDisabled();
  });
});
