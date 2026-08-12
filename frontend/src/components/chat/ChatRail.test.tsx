import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatRail } from "@/components/chat/ChatRail";

vi.mock("@/components/chat/ChatPanel", () => ({
  ChatPanel: () => <div data-testid="chat-panel" />,
}));

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
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry chat" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("matches workbench gutters in the main layout", () => {
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

    const frame = container.querySelector(".px-4.lg\\:px-6");
    expect(frame).toHaveClass("w-full", "min-w-0", "px-4", "lg:px-6");
    expect(frame).not.toHaveClass("max-w-6xl");
  });
});
