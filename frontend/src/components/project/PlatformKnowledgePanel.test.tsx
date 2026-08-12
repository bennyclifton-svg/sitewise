import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PlatformKnowledgePanel } from "@/components/project/PlatformKnowledgePanel";
import type { PlatformKnowledgeStatus } from "@/lib/types/project";

const platformStatus: PlatformKnowledgeStatus = {
  available: true,
  buckets: [
    {
      kind: "doctrine",
      document_count: 1,
      documents: [{ filename: "clerk-brief.md", relative_path: "docs/clerk-brief.md" }],
    },
    {
      kind: "seed",
      document_count: 2,
      documents: [
        {
          filename: "new-dwelling-guide.md",
          relative_path: "seed/new-dwelling-guide.md",
        },
        {
          filename: "setup-and-commission-guide.md",
          relative_path: "seed/setup-and-commission-guide.md",
        },
      ],
    },
  ],
};

describe("PlatformKnowledgePanel", () => {
  it("lists seed documents under an expanded seed folder", () => {
    render(<PlatformKnowledgePanel platformStatus={platformStatus} mode="knowledge" />);

    expect(screen.getByText("new-dwelling-guide.md")).toBeInTheDocument();
    expect(screen.getByText("setup-and-commission-guide.md")).toBeInTheDocument();
    expect(screen.queryByText("clerk-brief.md")).not.toBeInTheDocument();
  });

  it("expands doctrine on demand", () => {
    render(<PlatformKnowledgePanel platformStatus={platformStatus} mode="knowledge" />);

    fireEvent.click(screen.getByRole("button", { name: /expand doctrine/i }));

    expect(screen.getByText("clerk-brief.md")).toBeInTheDocument();
  });

  it("notifies when a seed document is selected", () => {
    const onSelectDocument = vi.fn();
    render(
      <PlatformKnowledgePanel
        platformStatus={platformStatus}
        mode="knowledge"
        onSelectDocument={onSelectDocument}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "new-dwelling-guide.md" }));

    expect(onSelectDocument).toHaveBeenCalledWith({
      filename: "new-dwelling-guide.md",
      relative_path: "seed/new-dwelling-guide.md",
    });
  });
});
