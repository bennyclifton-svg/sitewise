import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformKnowledgeViewer } from "@/components/project/PlatformKnowledgeViewer";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getPlatformKnowledgeDocument: vi.fn(),
  },
}));

vi.mock("@/components/project/MarkdownContent", () => ({
  MarkdownContent: ({ markdown }: { markdown: string }) => (
    <div data-testid="markdown">{markdown}</div>
  ),
}));

describe("PlatformKnowledgeViewer", () => {
  beforeEach(() => {
    vi.mocked(api.getPlatformKnowledgeDocument).mockReset();
  });

  it("loads and renders selected platform knowledge markdown", async () => {
    vi.mocked(api.getPlatformKnowledgeDocument).mockResolvedValue({
      filename: "new-dwelling-guide.md",
      relative_path: "seed/new-dwelling-guide.md",
      kind: "seed",
      content: "# New dwelling\n\nBody copy.",
    });

    render(
      <PlatformKnowledgeViewer
        document={{
          filename: "new-dwelling-guide.md",
          relative_path: "seed/new-dwelling-guide.md",
        }}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Loading document content");

    await waitFor(() => {
      expect(screen.getByTestId("markdown")).toHaveTextContent("New dwelling");
    });
    expect(api.getPlatformKnowledgeDocument).toHaveBeenCalledWith(
      "seed/new-dwelling-guide.md",
    );
    expect(screen.getByText("Platform knowledge")).toBeInTheDocument();
  });
});