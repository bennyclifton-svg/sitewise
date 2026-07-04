import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ActivityFeed } from "@/components/project/ActivityFeed";
import { useProjectActivity } from "@/lib/queries/project-activity";

vi.mock("@/lib/queries/project-activity", () => ({
  useProjectActivity: vi.fn(),
}));

const PROJECT_ID = "project-1";

describe("ActivityFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders collapsed activity and expands a trace", async () => {
    vi.mocked(useProjectActivity).mockReturnValue({
      data: {
        newest_created_at: "2026-07-04T02:00:00.000Z",
        runs: [
          {
            run_id: "run-1",
            source: "document_ingest",
            reference_type: "workspace_file",
            reference_id: "file-1",
            status: "complete",
            created_at: "2026-07-04T01:59:00.000Z",
            updated_at: "2026-07-04T02:00:00.000Z",
            events: [
              {
                id: "event-1",
                step: "store",
                status: "complete",
                message: "Stored file in the project workspace.",
                metadata: {
                  filename: "quote.pdf",
                  workspace_path: "04-projects/demo/_inbox/quote.pdf",
                },
                created_at: "2026-07-04T01:59:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(
      <ActivityFeed
        projectId={PROJECT_ID}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
      />,
    );

    expect(screen.getByText("Document Ingest: quote.pdf")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /document ingest/i }));

    expect(screen.getByText("Stored file in the project workspace.")).toBeInTheDocument();
  });

  it("opens the workspace path target", async () => {
    const onSelectWorkspacePath = vi.fn();
    vi.mocked(useProjectActivity).mockReturnValue({
      data: {
        newest_created_at: "2026-07-04T02:00:00.000Z",
        runs: [
          {
            run_id: "run-1",
            source: "document_ingest",
            reference_type: "workspace_file",
            reference_id: "file-1",
            status: "complete",
            created_at: "2026-07-04T01:59:00.000Z",
            updated_at: "2026-07-04T02:00:00.000Z",
            events: [
              {
                id: "event-1",
                step: "store",
                status: "complete",
                message: "Stored file in the project workspace.",
                metadata: {
                  filename: "quote.pdf",
                  workspace_path: "04-projects/demo/_inbox/quote.pdf",
                },
                created_at: "2026-07-04T01:59:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(
      <ActivityFeed
        projectId={PROJECT_ID}
        onSelectWorkspacePath={onSelectWorkspacePath}
        onOpenWorkflow={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /open activity target/i }));

    expect(onSelectWorkspacePath).toHaveBeenCalledWith(
      "04-projects/demo/_inbox/quote.pdf",
    );
  });
});
