import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  ChatActivityProvider,
  useChatActivity,
} from "@/components/chat/chat-activity";

function Probe() {
  const { busyThreadIds, setThreadBusy } = useChatActivity();
  return (
    <div>
      <p>{[...busyThreadIds].join(",") || "idle"}</p>
      <button type="button" onClick={() => setThreadBusy("thread-1", true)}>
        start
      </button>
      <button type="button" onClick={() => setThreadBusy("thread-1", false)}>
        stop
      </button>
    </div>
  );
}

describe("ChatActivityProvider", () => {
  it("tracks which threads are live", async () => {
    render(
      <ChatActivityProvider>
        <Probe />
      </ChatActivityProvider>,
    );

    expect(screen.getByText("idle")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "start" }));
    expect(screen.getByText("thread-1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "stop" }));
    expect(screen.getByText("idle")).toBeInTheDocument();
  });

  it("stays idle when no provider is mounted", () => {
    render(<Probe />);
    expect(screen.getByText("idle")).toBeInTheDocument();
  });
});
