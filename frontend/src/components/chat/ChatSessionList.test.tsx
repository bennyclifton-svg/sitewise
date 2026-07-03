import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatSessionList } from "@/components/chat/ChatSessionList";
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

function renderList() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChatSessionList activeThreadId="thread-1" projectId="project-1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChatSessionList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listThreads).mockResolvedValue([thread]);
    vi.mocked(api.updateThreadTitle).mockResolvedValue({
      ...thread,
      title: "Renamed tender review",
    });
    vi.mocked(api.deleteThread).mockResolvedValue(undefined);
    vi.mocked(api.createThread).mockResolvedValue({
      ...thread,
      id: "thread-2",
      title: "New session",
    });
  });

  it("renders a resume link", async () => {
    renderList();

    expect(await screen.findByRole("link", { name: "Tender review" })).toHaveAttribute(
      "href",
      "/chat/thread-1",
    );
  });

  it("renames a thread", async () => {
    renderList();

    await userEvent.click(await screen.findByRole("button", { name: /rename/i }));
    await userEvent.clear(screen.getByLabelText("Thread title"));
    await userEvent.type(screen.getByLabelText("Thread title"), "Renamed tender review");
    await userEvent.click(screen.getByRole("button", { name: "Save title" }));

    await waitFor(() =>
      expect(api.updateThreadTitle).toHaveBeenCalledWith(
        "thread-1",
        "Renamed tender review",
      ),
    );
    expect(await screen.findByRole("link", { name: "Renamed tender review" })).toBeInTheDocument();
  });

  it("deletes a thread", async () => {
    renderList();

    await userEvent.click(await screen.findByRole("button", { name: /delete/i }));
    await userEvent.click(
      screen.getByRole("button", { name: /confirm delete tender review/i }),
    );

    await waitFor(() => expect(api.deleteThread).toHaveBeenCalledWith("thread-1"));
    expect(screen.queryByRole("link", { name: "Tender review" })).not.toBeInTheDocument();
  });

  it("creates a new project session", async () => {
    renderList();

    await userEvent.click(await screen.findByRole("button", { name: /new session/i }));

    await waitFor(() =>
      expect(api.createThread).toHaveBeenCalledWith(undefined, "project-1"),
    );
    expect(await screen.findByRole("link", { name: "New session" })).toBeInTheDocument();
  });
});
