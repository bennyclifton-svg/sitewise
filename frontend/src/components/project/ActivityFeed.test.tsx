import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ActivityFeed } from "@/components/project/ActivityFeed";
import {
  useDeleteProjectActivityRuns,
  useProjectActivity,
} from "@/lib/queries/project-activity";

vi.mock("@/lib/queries/project-activity", () => ({
  useDeleteProjectActivityRuns: vi.fn(),
  useProjectActivity: vi.fn(),
}));

const PROJECT_ID = "project-1";

describe("ActivityFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useDeleteProjectActivityRuns).mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue(0),
    } as unknown as ReturnType<typeof useDeleteProjectActivityRuns>);
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
            references: {
              seed_consulted: ["seed/setup-and-commission-guide.md"],
              evidence_refs: ["project_evidence:demo/brief.pdf#chunk=1"],
              context_refs: ["doctrine:docs/clerk-brief.md"],
            },
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
    } as unknown as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(<ActivityFeed projectId={PROJECT_ID} />);

    expect(screen.getByText(/Doc ingest quote\.pdf/)).toBeInTheDocument();

    await user.click(screen.getByTitle(/Doc ingest quote\.pdf/i));

    expect(screen.getByText("Stored file in the project workspace.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /references/i }));

    expect(screen.getByText("Seeds")).toBeInTheDocument();
    expect(screen.getByText("seed/setup-and-commission-guide.md")).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
    expect(screen.getByText("project_evidence:demo/brief.pdf#chunk=1")).toBeInTheDocument();
    expect(screen.getByText("Context")).toBeInTheDocument();
    expect(screen.getByText("doctrine:docs/clerk-brief.md")).toBeInTheDocument();
  });

  it("labels PMP update activity", () => {
    vi.mocked(useProjectActivity).mockReturnValue({
      data: {
        newest_created_at: "2026-07-04T02:00:00.000Z",
        runs: [
          {
            run_id: "run-1",
            source: "update_pmp",
            reference_type: "draft_artifact",
            reference_id: "draft-1",
            status: "complete",
            created_at: "2026-07-04T01:59:00.000Z",
            updated_at: "2026-07-04T02:00:00.000Z",
            references: null,
            events: [
              {
                id: "event-1",
                step: "draft_save",
                status: "complete",
                message: "Saved Update PMP as a new versioned draft artefact.",
                metadata: {},
                created_at: "2026-07-04T02:00:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useProjectActivity>);

    render(<ActivityFeed projectId={PROJECT_ID} />);

    expect(screen.getByText(/PMP update/)).toBeInTheDocument();
  });

  it("does not expand or collapse rows during modifier selection", async () => {
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
                message: "Stored the first file.",
                metadata: {
                  filename: "quote.pdf",
                  workspace_path: "04-projects/demo/_inbox/quote.pdf",
                },
                created_at: "2026-07-04T01:59:00.000Z",
              },
            ],
          },
          {
            run_id: "run-2",
            source: "document_ingest",
            reference_type: "workspace_file",
            reference_id: "file-2",
            status: "complete",
            created_at: "2026-07-04T01:58:00.000Z",
            updated_at: "2026-07-04T01:58:00.000Z",
            events: [
              {
                id: "event-2",
                step: "store",
                status: "complete",
                message: "Stored the second file.",
                metadata: {
                  filename: "quote-2.pdf",
                  workspace_path: "04-projects/demo/_inbox/quote-2.pdf",
                },
                created_at: "2026-07-04T01:58:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(<ActivityFeed projectId={PROJECT_ID} />);

    await user.click(screen.getByTitle(/Doc ingest quote\.pdf/i));
    expect(screen.getByText("Stored the first file.")).toBeInTheDocument();

    await user.keyboard("{Control>}");
    await user.click(screen.getByTitle(/Doc ingest quote\.pdf/i));
    await user.keyboard("{/Control}");
    expect(screen.getByText("Stored the first file.")).toBeInTheDocument();

    await user.keyboard("{Shift>}");
    await user.click(screen.getByTitle(/Doc ingest quote-2\.pdf/i));
    await user.keyboard("{/Shift}");
    expect(screen.queryByText("Stored the second file.")).not.toBeInTheDocument();
  });

  it("deletes a single activity run from the row action", async () => {
    const deleteRuns = vi.fn().mockResolvedValue(1);
    vi.mocked(useDeleteProjectActivityRuns).mockReturnValue({
      isPending: false,
      mutateAsync: deleteRuns,
    } as unknown as ReturnType<typeof useDeleteProjectActivityRuns>);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
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
                metadata: { filename: "quote.pdf" },
                created_at: "2026-07-04T01:59:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(<ActivityFeed projectId={PROJECT_ID} />);

    await user.click(
      screen.getByRole("button", { name: /delete doc ingest quote\.pdf/i }),
    );

    expect(confirm).toHaveBeenCalled();
    expect(deleteRuns).toHaveBeenCalledWith(["run-1"]);
    confirm.mockRestore();
  });

  it("deletes selected activity runs from the header action", async () => {
    const deleteRuns = vi.fn().mockResolvedValue(2);
    vi.mocked(useDeleteProjectActivityRuns).mockReturnValue({
      isPending: false,
      mutateAsync: deleteRuns,
    } as unknown as ReturnType<typeof useDeleteProjectActivityRuns>);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
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
                metadata: { filename: "quote-a.pdf" },
                created_at: "2026-07-04T01:59:00.000Z",
              },
            ],
          },
          {
            run_id: "run-2",
            source: "document_ingest",
            reference_type: "workspace_file",
            reference_id: "file-2",
            status: "complete",
            created_at: "2026-07-04T01:58:00.000Z",
            updated_at: "2026-07-04T01:58:00.000Z",
            events: [
              {
                id: "event-2",
                step: "store",
                status: "complete",
                message: "Stored file in the project workspace.",
                metadata: { filename: "quote-b.pdf" },
                created_at: "2026-07-04T01:58:00.000Z",
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useProjectActivity>);
    const user = userEvent.setup();

    render(<ActivityFeed projectId={PROJECT_ID} />);

    await user.click(screen.getByTitle(/Doc ingest quote-a\.pdf/i));
    await user.keyboard("{Shift>}");
    await user.click(screen.getByTitle(/Doc ingest quote-b\.pdf/i));
    await user.keyboard("{/Shift}");
    await user.click(
      screen.getByRole("button", {
        name: /delete 2 selected activity items/i,
      }),
    );

    expect(confirm).toHaveBeenCalled();
    expect(deleteRuns).toHaveBeenCalledWith(["run-1", "run-2"]);
    confirm.mockRestore();
  });
});
