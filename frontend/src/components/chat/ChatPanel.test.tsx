import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { api } from "@/lib/api";

const { useChatMock, stopMock, transportMock } = vi.hoisted(() => ({
  useChatMock: vi.fn(),
  stopMock: vi.fn(),
  transportMock: vi.fn(),
}));

vi.mock("@ai-sdk/react", () => ({
  useChat: useChatMock,
}));

vi.mock("ai", () => ({
  DefaultChatTransport: vi.fn(function DefaultChatTransport(config: unknown) {
    transportMock(config);
    return config;
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    cancelAgentTurn: vi.fn(),
    getAgentModels: vi.fn().mockResolvedValue({
      agent_runtime_enabled: true,
      default_model: "__hermes_config__",
      default_runtime: "hermes",
      runtimes: [{ id: "hermes", label: "Hermes", enabled: true }],
      models: [{ id: "__hermes_config__", label: "Hermes default", is_default: true }],
    }),
    getLlmModels: vi.fn().mockResolvedValue({
      default_model: "gpt-4.1-mini",
      models: [{ id: "gpt-4.1-mini", label: "gpt-4.1-mini", is_default: true }],
    }),
  },
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: vi.fn(),
}));

function renderPanel(status: "ready" | "submitted" | "streaming" = "ready") {
  useChatMock.mockReturnValue({
    messages: [],
    sendMessage: vi.fn(),
    status,
    error: null,
    stop: stopMock,
  });

  return render(
    <ChatPanel
      threadId="thread-1"
      initialMessages={[]}
      agentMode
      projectId="project-1"
    />,
  );
}

function mockUseChat({
  messages = [],
  status = "ready",
}: {
  messages?: unknown[];
  status?: "ready" | "submitted" | "streaming";
} = {}) {
  useChatMock.mockReturnValue({
    messages,
    sendMessage: vi.fn(),
    status,
    error: null,
    stop: stopMock,
  });
}

describe("ChatPanel stop control", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(api.cancelAgentTurn).mockResolvedValue(true);
  });

  it("appears only while busy", () => {
    const { rerender } = renderPanel("ready");

    expect(screen.queryByRole("button", { name: /stop/i })).not.toBeInTheDocument();

    useChatMock.mockReturnValue({
      messages: [],
      sendMessage: vi.fn(),
      status: "streaming",
      error: null,
      stop: stopMock,
    });
    rerender(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
      />,
    );

    expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument();
  });

  it("calls client stop and backend cancel", async () => {
    renderPanel("streaming");

    await userEvent.click(screen.getByRole("button", { name: /stop/i }));

    expect(stopMock).toHaveBeenCalledOnce();
    await waitFor(() =>
      expect(api.cancelAgentTurn).toHaveBeenCalledWith("thread-1"),
    );
  });
});

describe("ChatPanel agent model selection", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(api.cancelAgentTurn).mockResolvedValue(true);
  });

  it("sends the selected Hermes model with agent chat requests", () => {
    window.localStorage.setItem("clerk.agentModel", "openai-codex:gpt-5.5");
    renderPanel("ready");

    const config = transportMock.mock.calls[0][0] as {
      prepareSendMessagesRequest: (input: {
        id: string;
        messages: unknown[];
        body: Record<string, unknown>;
      }) => { body: Record<string, unknown> };
    };

    const request = config.prepareSendMessagesRequest({
      id: "thread-1",
      messages: [],
      body: {},
    });

    expect(request.body).toMatchObject({
      thread_id: "thread-1",
      agent_model: "openai-codex:gpt-5.5",
    });
  });
});

describe("ChatPanel long history", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(api.cancelAgentTurn).mockResolvedValue(true);
  });

  it("keeps the input reachable by scrolling message history inside the panel", async () => {
    const messages = Array.from({ length: 24 }, (_, index) => ({
      id: `assistant-${index}`,
      role: "assistant",
      parts: [{ type: "text", text: `History item ${index}` }],
    }));
    mockUseChat({ messages });

    render(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
        compact
        layout="rail"
      />,
    );

    const history = screen.getByRole("log", {
      name: /conversation history/i,
    });
    expect(history).toHaveClass("overflow-y-auto");
    expect(screen.getByRole("textbox", { name: /message/i })).toBeInTheDocument();

    Object.defineProperty(history, "clientHeight", {
      configurable: true,
      value: 120,
    });
    Object.defineProperty(history, "scrollHeight", {
      configurable: true,
      value: 1200,
    });
    Object.defineProperty(history, "scrollTop", {
      configurable: true,
      value: 0,
      writable: true,
    });

    fireEvent.scroll(history);

    const scrollButton = await screen.findByRole("button", {
      name: /scroll to latest message/i,
    });
    await userEvent.click(scrollButton);

    expect(history.scrollTop).toBe(1200);
  });
});
