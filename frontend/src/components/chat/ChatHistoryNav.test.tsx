import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatHistoryNav } from "@/components/chat/ChatHistoryNav";
import { api } from "@/lib/api";
import type { ChatThread } from "@/lib/types/chat";

vi.mock("@/lib/api", () => ({
  api: {
    listThreads: vi.fn(),
    createThread: vi.fn(),
    updateThreadTitle: vi.fn(),
    deleteThread: vi.fn(),
  },
}));

const thread: ChatThread = {
  id: "thread-1",
  project_id: "project-1",
  title: "Tender review",
  created_at: "2026-07-03T00:00:00Z",
  updated_at: "2026-07-03T00:00:00Z",
};

function renderNav(onCreateSession = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChatHistoryNav
          projectId="project-1"
          activeThreadId="thread-1"
          onSelectThread={vi.fn()}
          onCreateSession={onCreateSession}
          onActiveThreadDeleted={vi.fn()}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return { onCreateSession };
}

describe("ChatHistoryNav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listThreads).mockResolvedValue([thread]);
    vi.mocked(api.createThread).mockResolvedValue({
      ...thread,
      id: "thread-2",
      title: "New chat",
    });
  });

  it("shows a new chat nav action above history and selects the created thread", async () => {
    const onCreateSession = vi.fn();
    renderNav(onCreateSession);

    const history = screen.getByRole("region", { name: "Chat history" });
    expect(within(history).queryByRole("button", { name: "New chat" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "New chat" }));

    await waitFor(() =>
      expect(api.createThread).toHaveBeenCalledWith(undefined, "project-1"),
    );
    await waitFor(() =>
      expect(onCreateSession).toHaveBeenCalledWith(
        expect.objectContaining({ id: "thread-2", project_id: "project-1" }),
      ),
    );
  });
});
