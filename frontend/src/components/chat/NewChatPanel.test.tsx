import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NewChatPanel } from "@/components/chat/NewChatPanel";
import { api } from "@/lib/api";
import type { ChatThread } from "@/lib/types/chat";

vi.mock("@/lib/api", () => ({ api: { createThread: vi.fn() } }));
vi.mock("@/lib/queries/agent-configuration", () => ({
  useAgentConfiguration: () => ({ data: undefined, isPending: false }),
}));

const thread: ChatThread = {
  id: "new-thread", project_id: "project-1", title: null,
  created_at: "2026-09-16T00:00:00Z", updated_at: "2026-09-16T00:00:00Z",
};

function setup() {
  const onCreated = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <NewChatPanel projectId="project-1" onCreated={onCreated} />
    </QueryClientProvider>,
  );
  return { ...view, onCreated, client };
}

describe("NewChatPanel", () => {
  beforeEach(() => vi.resetAllMocks());

  it("accepts typing immediately and submits the draft once creation finishes", async () => {
    let resolve!: (thread: ChatThread) => void;
    vi.mocked(api.createThread).mockReturnValue(new Promise((done) => { resolve = done; }));
    const { onCreated } = setup();
    await userEvent.type(screen.getByRole("textbox", { name: "Message" }), "Compare tenders");
    expect(api.createThread).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Ask SiteWise" }));
    expect(screen.getByRole("status")).toHaveTextContent("Starting chat");
    expect(onCreated).not.toHaveBeenCalled();
    await act(async () => resolve(thread));
    expect(api.createThread).toHaveBeenCalledExactlyOnceWith(undefined, "project-1");
    expect(onCreated).toHaveBeenCalledExactlyOnceWith(thread, "Compare tenders");
  });

  it("preserves the message after a creation failure so sending can be retried", async () => {
    vi.mocked(api.createThread).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(thread);
    const { onCreated } = setup();
    await userEvent.type(screen.getByRole("textbox", { name: "Message" }), "Review fees");
    await userEvent.click(screen.getByRole("button", { name: "Ask SiteWise" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try sending again");
    expect(screen.getByRole("textbox", { name: "Message" })).toHaveValue("Review fees");
    await userEvent.click(screen.getByRole("button", { name: "Ask SiteWise" }));
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(thread, "Review fees"));
  });

  it("does not reopen or send a chat after navigating away during creation", async () => {
    let resolve!: (thread: ChatThread) => void;
    vi.mocked(api.createThread).mockReturnValue(new Promise((done) => { resolve = done; }));
    const { onCreated, unmount, client } = setup();
    await userEvent.type(screen.getByRole("textbox", { name: "Message" }), "Draft text");
    await userEvent.click(screen.getByRole("button", { name: "Ask SiteWise" }));
    unmount();
    await act(async () => resolve(thread));
    expect(onCreated).not.toHaveBeenCalled();
    expect(client.getQueryData(["chat", "threads"])).toEqual([thread]);
  });
});
