import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ChatActivityProvider, useChatActivity } from "@/components/chat/chat-activity";
import { ChatRail } from "@/components/chat/ChatRail";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

vi.mock("@/components/chat/ChatPanel", () => ({
  ChatPanel: ({ threadId }: { threadId: string }) => (
    <div data-testid={`chat-panel-${threadId}`} />
  ),
}));

const threadA: ChatThread = {
  id: "thread-a",
  project_id: "project-1",
  title: "Architectural engagement",
  created_at: "2026-08-15T00:00:00Z",
  updated_at: "2026-08-15T00:00:00Z",
};

const threadB: ChatThread = {
  ...threadA,
  id: "thread-b",
  title: "Fee comparison",
};

const emptyMessages: ChatMessage[] = [];

describe("ChatRail failure boundary", () => {
  it("shows chat bootstrap errors locally and offers retry", async () => {
    const retry = vi.fn();
    render(
      <ChatRail
        thread={null}
        messages={[]}
        chatRevision={0}
        chatLoading={false}
        chatError="Could not open project chat."
        onRetry={retry}
        selectedCitationId={null}
        onConversationUpdate={vi.fn()}
        onSelectCitation={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not open project chat.",
    );
    expect(screen.queryByTestId(/chat-panel-/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry chat" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("keeps the workbench left gutter and sits closer to the repository", () => {
    const { container } = render(
      <ChatRail
        layout="main"
        thread={null}
        messages={[]}
        chatRevision={0}
        chatLoading={false}
        chatError="Could not open project chat."
        selectedCitationId={null}
        onConversationUpdate={vi.fn()}
        onSelectCitation={vi.fn()}
      />,
    );

    const frame = container.querySelector(".pl-4.lg\\:pl-6");
    expect(frame).toHaveClass("w-full", "min-w-0", "pl-4", "pr-2", "lg:pl-6", "lg:pr-2");
    expect(frame).not.toHaveClass("max-w-6xl");
  });
});

describe("ChatRail live session parking", () => {
  it("keeps the active session in the flex height chain so the transcript can scroll", () => {
    render(
      <ChatActivityProvider>
        <ChatRail
          layout="main"
          thread={threadA}
          messages={emptyMessages}
          chatRevision={0}
          chatLoading={false}
          selectedCitationId={null}
          onConversationUpdate={vi.fn()}
          onSelectCitation={vi.fn()}
        />
      </ChatActivityProvider>,
    );

    expect(screen.getByTestId("chat-panel-thread-a").parentElement).toHaveClass(
      "flex",
      "min-h-0",
      "flex-1",
      "flex-col",
    );
  });

  it("keeps a live chat mounted while another session is opened", async () => {
    function Harness() {
      const { setThreadBusy } = useChatActivity();
      const [thread, setThread] = useState<ChatThread | null>(threadA);
      const [chatLoading, setChatLoading] = useState(false);
      const [chatRevision, setChatRevision] = useState(0);

      return (
        <>
          <button type="button" onClick={() => setThreadBusy("thread-a", true)}>
            mark-a-live
          </button>
          <button
            type="button"
            onClick={() => {
              setChatLoading(true);
              setChatRevision((current) => current + 1);
            }}
          >
            start-switch
          </button>
          <button
            type="button"
            onClick={() => {
              setThread(threadB);
              setChatLoading(false);
              setChatRevision((current) => current + 1);
            }}
          >
            finish-switch
          </button>
          <ChatRail
            thread={thread}
            messages={emptyMessages}
            chatRevision={chatRevision}
            chatLoading={chatLoading}
            selectedCitationId={null}
            onConversationUpdate={vi.fn()}
            onSelectCitation={vi.fn()}
          />
        </>
      );
    }

    render(
      <ChatActivityProvider>
        <Harness />
      </ChatActivityProvider>,
    );

    expect(screen.getByTestId("chat-panel-thread-a")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "mark-a-live" }));
    await userEvent.click(screen.getByRole("button", { name: "start-switch" }));
    expect(screen.getByTestId("chat-panel-thread-a")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "finish-switch" }));
    expect(screen.getByTestId("chat-panel-thread-a")).toBeInTheDocument();
    expect(screen.getByTestId("chat-panel-thread-b")).toBeInTheDocument();
  });
});
