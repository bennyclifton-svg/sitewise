import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { api } from "@/lib/api";

const { useChatMock, stopMock } = vi.hoisted(() => ({
  useChatMock: vi.fn(),
  stopMock: vi.fn(),
}));

vi.mock("@ai-sdk/react", () => ({
  useChat: useChatMock,
}));

vi.mock("ai", () => ({
  DefaultChatTransport: vi.fn(function DefaultChatTransport(config: unknown) {
    return config;
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    cancelAgentTurn: vi.fn(),
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

describe("ChatPanel stop control", () => {
  beforeEach(() => {
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
