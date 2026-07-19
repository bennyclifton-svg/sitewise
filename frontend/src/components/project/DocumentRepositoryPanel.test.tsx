import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DocumentRepositoryPanel } from "@/components/project/DocumentRepositoryPanel";
import { api } from "@/lib/api";
import type { InboxUploadResult, PdfAnalyzeResult } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    analyzePdf: vi.fn(),
    commitStagedPdf: vi.fn(),
    uploadInboxFiles: vi.fn(),
  },
}));

vi.mock("@/lib/queries/project-data", () => ({
  useDeleteEvidence: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
  }),
  useBatchDeleteEvidence: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
  }),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function uploadResult(overrides: Partial<InboxUploadResult> = {}): InboxUploadResult {
  return {
    id: "wf-1",
    filename: "notes.md",
    workspace_path: "04-projects/demo/_inbox/notes.md",
    content_hash: "hash",
    size_bytes: 12,
    ingest_status: "ingested",
    message: null,
    ...overrides,
  };
}

function analyzeResult(overrides: Partial<PdfAnalyzeResult> = {}): PdfAnalyzeResult {
  return {
    staging_id: "stg-1",
    is_drawing_set: false,
    confidence: 0.1,
    page_count: 3,
    scores: {},
    pages: [],
    ...overrides,
  };
}

function renderPanel(onUploadComplete = vi.fn().mockResolvedValue(undefined)) {
  const view = render(
    <DocumentRepositoryPanel
      projectId="project-1"
      evidence={[]}
      selectedEvidenceId={null}
      workspaceTree={[]}
      selectedWorkspacePath={null}
      onSelectEvidence={vi.fn()}
      onSelectWorkspacePath={vi.fn()}
      onOpenWorkflow={vi.fn()}
      onViewWorkbench={vi.fn()}
      onViewFolder={vi.fn()}
      onUploadComplete={onUploadComplete}
    />,
  );
  return { ...view, onUploadComplete };
}

function dropFile(container: HTMLElement, file: File) {
  const input = container.querySelector<HTMLInputElement>("input[type=file]");
  if (!input) throw new Error("file input not found");
  fireEvent.change(input, { target: { files: [file] } });
}

describe("DocumentRepositoryPanel pending uploads", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("acknowledges a dropped file instantly with a placeholder row", async () => {
    const upload = deferred<InboxUploadResult[]>();
    vi.mocked(api.uploadInboxFiles).mockReturnValue(upload.promise);
    const { container, onUploadComplete } = renderPanel();

    dropFile(container, new File(["# notes"], "notes.md", { type: "text/markdown" }));

    // The register table appears immediately with the placeholder row, even
    // though the project has no ingested evidence yet.
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(screen.getByText("notes.md")).toBeInTheDocument();
    expect(screen.getByText("Uploading…")).toBeInTheDocument();
    expect(container.querySelector(".cockpit-skeleton")).not.toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("Uploading notes.md");

    upload.resolve([uploadResult()]);
    await waitFor(() => expect(onUploadComplete).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByText("notes.md")).not.toBeInTheDocument());
  });

  it("ingests an analyzed PDF from staging instead of uploading it twice", async () => {
    const analyze = deferred<PdfAnalyzeResult>();
    const commit = deferred<InboxUploadResult[]>();
    vi.mocked(api.analyzePdf).mockReturnValue(analyze.promise);
    vi.mocked(api.commitStagedPdf).mockReturnValue(commit.promise);
    const { container, onUploadComplete } = renderPanel();

    dropFile(container, new File(["%PDF-1.7"], "site-plan.pdf", { type: "application/pdf" }));

    expect(await screen.findByText("site-plan.pdf")).toBeInTheDocument();
    expect(screen.getByText("Uploading…")).toBeInTheDocument();

    analyze.resolve(analyzeResult());
    expect(await screen.findByText("Ingesting…")).toBeInTheDocument();
    expect(api.commitStagedPdf).toHaveBeenCalledWith("project-1", "stg-1", "site-plan.pdf");
    expect(api.uploadInboxFiles).not.toHaveBeenCalled();

    commit.resolve([uploadResult({ filename: "site-plan.pdf" })]);
    await waitFor(() => expect(onUploadComplete).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByText("site-plan.pdf")).not.toBeInTheDocument(),
    );
  });

  it("swaps a drawing-set placeholder for the split proposal", async () => {
    vi.mocked(api.analyzePdf).mockResolvedValue(
      analyzeResult({
        is_drawing_set: true,
        confidence: 0.9,
        page_count: 2,
        pages: [
          { index: 1, proposed_title: "A-100 Site Plan", filename: "a-100.pdf", has_text: true },
          { index: 2, proposed_title: "A-200 Floor Plan", filename: "a-200.pdf", has_text: true },
        ],
      }),
    );
    const { container } = renderPanel();

    dropFile(container, new File(["%PDF-1.7"], "plans.pdf", { type: "application/pdf" }));

    expect(await screen.findByText(/looks like a drawing set/)).toBeInTheDocument();
    // The placeholder row is gone: the proposal card owns the file now.
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(api.commitStagedPdf).not.toHaveBeenCalled();
    expect(api.uploadInboxFiles).not.toHaveBeenCalled();
  });
});
