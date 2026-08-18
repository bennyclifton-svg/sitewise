import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import type { SortFileRow, SortFilesSummary } from "@/lib/types/project";

const emptySummary: SortFilesSummary = {
  inspected: 0,
  moved: 0,
  unresolved: 0,
  refused: 0,
  already_filed: 0,
  skipped: 0,
  waiting: 0,
  needs_review: 0,
  failed: 0,
};

function row(overrides: Partial<SortFileRow>): SortFileRow {
  return {
    source_path: "04-projects/demo/_inbox/file.pdf",
    filename: "file.pdf",
    outcome: "moved",
    destination_path: null,
    destination_filename: null,
    reason: null,
    document_number: null,
    title: null,
    revision: null,
    category: null,
    ...overrides,
  };
}

describe("SortFilesResultPanel", () => {
  it("shows the complete document-control identity for each result", () => {
    render(
      <SortFilesResultPanel
        summary={{ ...emptySummary, inspected: 1, moved: 1 }}
        rows={[
          row({
            source_path: "04-projects/demo/_inbox/HY-SK~1.PDF",
            filename: "HY-SK~1.PDF",
            destination_path:
              "04-projects/demo/03-design/hydraulic/HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF",
            destination_filename: "HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF",
            reason: "Classified and filed",
            document_number: "HY-SK-06",
            title: "ROOF DRAINAGE PLAN",
            revision: "P1",
            category: "Hydraulic",
          }),
        ]}
      />,
    );

    expect(screen.getByText("ROOF DRAINAGE PLAN")).toBeInTheDocument();
    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("Sorted 1 file")).toBeInTheDocument();
  });

  it("explains waiting files instead of a bare zero-moved result", () => {
    render(
      <SortFilesResultPanel
        summary={{ ...emptySummary, waiting: 3 }}
        rows={[
          row({
            filename: "a.pdf",
            source_path: "04-projects/demo/_inbox/a.pdf",
            outcome: "waiting",
            reason: "Ingestion is still in progress",
          }),
        ]}
      />,
    );

    expect(
      screen.getByText(
        "3 files are still being processed. They will be filed automatically when classification completes.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("0 moved")).not.toBeInTheDocument();
    expect(screen.getByText(/Waiting for ingestion/)).toBeInTheDocument();
  });

  it("lets a needs-review row open classification", () => {
    const onReviewFile = vi.fn();
    render(
      <SortFilesResultPanel
        summary={{ ...emptySummary, needs_review: 1 }}
        rows={[
          row({
            filename: "scan.pdf",
            source_path: "04-projects/demo/_inbox/scan.pdf",
            outcome: "needs-review",
            reason: "Low confidence; tap to classify",
          }),
        ]}
        onReviewFile={onReviewFile}
      />,
    );

    screen.getByRole("button", { name: "Classify" }).click();
    expect(onReviewFile).toHaveBeenCalledWith("04-projects/demo/_inbox/scan.pdf");
  });

  it("offers retry on failed rows", () => {
    const onRetryFailed = vi.fn();
    render(
      <SortFilesResultPanel
        summary={{ ...emptySummary, failed: 1 }}
        rows={[
          row({
            filename: "broken.pdf",
            source_path: "04-projects/demo/_inbox/broken.pdf",
            outcome: "failed",
            reason: "Ingestion failed; retry the upload before sorting",
          }),
        ]}
        onRetryFailed={onRetryFailed}
      />,
    );

    screen.getByRole("button", { name: "Retry" }).click();
    expect(onRetryFailed).toHaveBeenCalledWith("04-projects/demo/_inbox/broken.pdf");
  });
});
