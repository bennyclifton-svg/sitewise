import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DocumentRepositoryPanel } from "@/components/project/DocumentRepositoryPanel";
import { api } from "@/lib/api";
import type {
  DocumentUsageMark,
  DraftArtifactSummary,
  EvidencePreview,
  InboxUploadResult,
  PdfAnalyzeResult,
} from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ version: 0, prompts: null }),
    put: vi.fn(),
    analyzePdf: vi.fn(),
    commitStagedPdf: vi.fn(),
    uploadInboxFiles: vi.fn(),
  },
}));

vi.mock("@/components/project/ActivityFeed", () => ({ ActivityFeed: () => null }));

const deleteDraftMutateAsync = vi.fn();
const batchClassificationMutateAsync = vi.fn();
let batchClassificationIsPending = false;

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
  useBatchSetDocumentClassification: () => ({
    mutateAsync: batchClassificationMutateAsync,
    isPending: batchClassificationIsPending,
  }),
  useDeleteDraft: () => ({
    mutateAsync: deleteDraftMutateAsync,
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

describe("DocumentRepositoryPanel navigation", () => {
  it("uses one button to switch document views", () => {
    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Switch to tree view" }));
    expect(screen.getByRole("button", { name: "Switch to document list" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Switch to document list" }));
    expect(screen.getByRole("button", { name: "Switch to tree view" })).toBeVisible();
  });

  it("keeps an unsaved prompt edit when visiting documents", async () => {
    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Prompts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit Cost plan" }));
    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "Keep my unsaved edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Show documents" }));
    expect(screen.queryByRole("region", { name: "Personal prompt library" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Prompts" }));
    expect(screen.getByLabelText("Prompt")).toHaveValue("Keep my unsaved edit");
  });
});

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

    const completed = uploadResult({ workflow_run_id: "run-1" });
    upload.resolve([completed]);
    await waitFor(() => expect(onUploadComplete).toHaveBeenCalledWith([completed]));
    await waitFor(() => expect(screen.queryByText("notes.md")).not.toBeInTheDocument());
  });

  it("accepts a dropped RTF file for inbox ingest", async () => {
    const upload = deferred<InboxUploadResult[]>();
    vi.mocked(api.uploadInboxFiles).mockReturnValue(upload.promise);
    const { container } = renderPanel();

    dropFile(
      container,
      new File(["{\\rtf1 Inner West LEP}"], "iwlep2022344.rtf", {
        type: "application/rtf",
      }),
    );

    expect(await screen.findByText("iwlep2022344.rtf")).toBeInTheDocument();
    expect(screen.queryByText(/Unsupported file type/)).not.toBeInTheDocument();
    await waitFor(() => expect(api.uploadInboxFiles).toHaveBeenCalledTimes(1));
    const uploaded = vi.mocked(api.uploadInboxFiles).mock.calls[0]?.[1] as File[];
    expect(uploaded[0]?.name).toBe("iwlep2022344.rtf");

    upload.resolve([uploadResult({ filename: "iwlep2022344.rtf" })]);
    await waitFor(() =>
      expect(screen.queryByText("iwlep2022344.rtf")).not.toBeInTheDocument(),
    );
  });

  it("queues a later drop while the current file is still ingesting", async () => {
    const firstUpload = deferred<InboxUploadResult[]>();
    const secondUpload = deferred<InboxUploadResult[]>();
    vi.mocked(api.uploadInboxFiles)
      .mockReturnValueOnce(firstUpload.promise)
      .mockReturnValueOnce(secondUpload.promise);
    const { container, onUploadComplete } = renderPanel();

    dropFile(container, new File(["# first"], "first.md", { type: "text/markdown" }));
    await waitFor(() => expect(api.uploadInboxFiles).toHaveBeenCalledTimes(1));

    fireEvent.drop(container.firstElementChild!, {
      dataTransfer: {
        files: [new File(["# second"], "second.md", { type: "text/markdown" })],
      },
    });

    expect(await screen.findByText("first.md")).toBeInTheDocument();
    expect(screen.getByText("second.md")).toBeInTheDocument();
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(api.uploadInboxFiles).toHaveBeenCalledTimes(1);

    firstUpload.resolve([uploadResult({ filename: "first.md" })]);
    await waitFor(() => expect(api.uploadInboxFiles).toHaveBeenCalledTimes(2));

    secondUpload.resolve([uploadResult({ filename: "second.md" })]);
    await waitFor(() => expect(onUploadComplete).toHaveBeenCalledTimes(2));
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
function evidenceRow(overrides: Partial<EvidencePreview> = {}): EvidencePreview {
  return {
    id: "doc-1",
    title: "Owner Brief",
    filename: "owner-brief.pdf",
    relative_path: "04-projects/demo/01-brief/owner-brief.pdf",
    source_type: "project_evidence",
    document_class: "project_evidence",
    excerpt: "Brief excerpt.",
    used_by: [],
    ...overrides,
  };
}

function artefactDraft(
  overrides: Partial<DraftArtifactSummary> = {},
): DraftArtifactSummary {
  return {
    id: "draft-1",
    project_id: "project-1",
    workflow_type: "trade_rft_electrical_services",
    version: 2,
    status: "draft",
    title: "Request for Tender - Electrical services",
    workspace_path:
      "04-projects/demo/05-procurement/electrical-services/02-tender-pack/electrical-services_rft_v02.draft.md",
    author_user_id: "user-1",
    model: null,
    runtime: "clerk-trade-procurement",
    created_at: "2026-08-02T00:00:00.000Z",
    updated_at: "2026-08-02T00:00:00.000Z",
    ...overrides,
  };
}

function usageMark(overrides: Partial<DocumentUsageMark> = {}): DocumentUsageMark {
  return {
    artefact_id: "artefact-1",
    workflow_type: "create_pmp",
    title: "Project Management Plan",
    version: 3,
    ...overrides,
  };
}

function renderWithEvidence(
  evidence: EvidencePreview[],
  options: { usageHighlightArtefactId?: string | null } = {},
) {
  return render(
    <DocumentRepositoryPanel
      projectId="project-1"
      evidence={evidence}
      selectedEvidenceId={null}
      workspaceTree={[]}
      selectedWorkspacePath={null}
      onSelectEvidence={vi.fn()}
      onSelectWorkspacePath={vi.fn()}
      onOpenWorkflow={vi.fn()}
      onViewWorkbench={vi.fn()}
      onViewFolder={vi.fn()}
      onUploadComplete={vi.fn().mockResolvedValue(undefined)}
      usageHighlightArtefactId={options.usageHighlightArtefactId}
    />,
  );
}

describe("DocumentRepositoryPanel usage marks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("hides usage marks until a matching artefact is open in the middle panel", () => {
    renderWithEvidence([evidenceRow({ used_by: [usageMark()] })]);

    expect(screen.queryByTitle(/^Used by /)).not.toBeInTheDocument();
  });

  it("marks a source document with a dot when its PMP is open", () => {
    renderWithEvidence([evidenceRow({ used_by: [usageMark()] })], {
      usageHighlightArtefactId: "artefact-1",
    });

    const mark = screen.getByTitle("Used by Project Management Plan v3");
    expect(mark).toBeInTheDocument();
    expect(mark).toHaveAttribute(
      "aria-label",
      "Used by Project Management Plan v3",
    );
    expect(mark).toBeEmptyDOMElement();
  });

  it("leaves an unused document unmarked", () => {
    renderWithEvidence([evidenceRow()], {
      usageHighlightArtefactId: "artefact-1",
    });

    expect(screen.getByText("Owner Brief")).toBeInTheDocument();
    expect(screen.queryByTitle(/^Used by /)).not.toBeInTheDocument();
  });

  it("only highlights the open artefact when a document feeds multiple drafts", () => {
    renderWithEvidence(
      [
        evidenceRow({
          used_by: [
            usageMark(),
            usageMark({
              artefact_id: "artefact-2",
              workflow_type: "create_cost_plan",
              title: "Cost Plan",
              version: 2,
            }),
          ],
        }),
      ],
      { usageHighlightArtefactId: "artefact-1" },
    );

    expect(screen.getByTitle("Used by Project Management Plan v3")).toBeInTheDocument();
    expect(screen.queryByTitle("Used by Cost Plan v2")).not.toBeInTheDocument();
  });

  it("tolerates evidence rows from an older API response with no used_by field", () => {
    const legacy = evidenceRow();
    delete (legacy as { used_by?: unknown }).used_by;

    renderWithEvidence([legacy], { usageHighlightArtefactId: "artefact-1" });

    expect(screen.getByText("Owner Brief")).toBeInTheDocument();
  });
});

describe("DocumentRepositoryPanel invoice status", () => {
  it.each([
    ["reading", "Reading"],
    ["ready_to_process", "Ready"],
    ["processing", "Processing"],
    ["booked", "Booked"],
    ["needs_review", "Review"],
    ["failed", "Failed"],
  ] as const)("shows %s with a text label as well as colour", (status, label) => {
    renderWithEvidence([
      evidenceRow({
        title: "Structural invoice",
        filename: "structural-invoice.pdf",
        invoice_status: status,
      }),
    ]);

    expect(screen.getByLabelText(`Invoice status: ${label}`)).toBeInTheDocument();
  });
});

describe("DocumentRepositoryPanel generated artefacts", () => {
  beforeEach(() => {
    deleteDraftMutateAsync.mockReset();
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("selects and opens an RFT artefact like a normal schedule row", () => {
    const onSelectEvidence = vi.fn();
    const onOpenDraft = vi.fn();
    const onSelectedEvidenceIdsChange = vi.fn();
    const draft = artefactDraft();
    render(
      <DocumentRepositoryPanel
        projectId="project-1"
        evidence={[evidenceRow()]}
        selectedEvidenceId={null}
        workspaceTree={[]}
        selectedWorkspacePath={null}
        onSelectEvidence={onSelectEvidence}
        onSelectedEvidenceIdsChange={onSelectedEvidenceIdsChange}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
        onViewWorkbench={vi.fn()}
        onViewFolder={vi.fn()}
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        artefactDrafts={[draft]}
        onOpenDraft={onOpenDraft}
      />,
    );

    expect(screen.getByText("RFT")).toBeInTheDocument();
    expect(screen.getByText("RFT - Electrical services")).toBeInTheDocument();
    fireEvent.click(screen.getByText("RFT - Electrical services"));

    expect(onOpenDraft).toHaveBeenCalledWith(draft);
    expect(onSelectEvidence).not.toHaveBeenCalled();
    expect(onSelectedEvidenceIdsChange).toHaveBeenCalledWith(new Set([draft.id]));
    expect(
      screen.getByRole("button", { name: "Delete RFT - Electrical services" }),
    ).toBeInTheDocument();
  });

  it("deletes a generated artefact from the bin action", async () => {
    const onArtefactDeleted = vi.fn();
    const draft = artefactDraft({
      title: "Request for Fee Proposal - Quantity surveyor",
      workflow_type: "consultant_procurement_quantity_surveyor",
    });
    deleteDraftMutateAsync.mockResolvedValue({
      deleted_id: draft.id,
      workflow_type: draft.workflow_type,
      latest_draft: null,
    });

    render(
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
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        artefactDrafts={[draft]}
        onOpenDraft={vi.fn()}
        onArtefactDeleted={onArtefactDeleted}
      />,
    );

    expect(screen.getByText("RFP - Quantity surveyor")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Delete RFP - Quantity surveyor" }),
    );

    await waitFor(() => {
      expect(deleteDraftMutateAsync).toHaveBeenCalledWith(draft.id);
      expect(onArtefactDeleted).toHaveBeenCalledWith({
        deleted_id: draft.id,
        workflow_type: draft.workflow_type,
        latest_draft: null,
      });
    });
  });

  it("lists one project management plan when create and update both appear as v1", () => {
    const created = artefactDraft({
      id: "pmp-create",
      title: "Project Management Plan",
      workflow_type: "create_pmp",
      version: 1,
    });
    const updated = artefactDraft({
      id: "pmp-update",
      title: "Project Management Plan",
      workflow_type: "update_pmp",
      version: 1,
      updated_at: "2026-08-02T08:24:52.000Z",
    });

    render(
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
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        artefactDrafts={[created, updated]}
        onOpenDraft={vi.fn()}
      />,
    );

    expect(screen.getAllByText("Project Management Plan")).toHaveLength(1);
    expect(screen.getAllByText("v1")).toHaveLength(1);
    expect(
      screen.getAllByRole("button", { name: "Delete Project Management Plan" }),
    ).toHaveLength(1);
  });

  it("treats a missing draft as already deleted", async () => {
    const { ApiError } = await import("@/lib/http");
    const onArtefactDeleted = vi.fn();
    const pmp = artefactDraft({
      title: "Project Management Plan",
      workflow_type: "create_pmp",
      version: 1,
    });
    deleteDraftMutateAsync.mockRejectedValue(
      new ApiError("Draft not found", { kind: "http", status: 404 }),
    );

    render(
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
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        artefactDrafts={[pmp]}
        onOpenDraft={vi.fn()}
        onArtefactDeleted={onArtefactDeleted}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Delete Project Management Plan" }),
    );

    await waitFor(() => {
      expect(onArtefactDeleted).toHaveBeenCalledWith({
        deleted_id: pmp.id,
        workflow_type: "create_pmp",
        latest_draft: null,
      });
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("DocumentRepositoryPanel schedule sorting", () => {
  function scheduleTitles(): string[] {
    return screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.querySelector("td:nth-child(2)")?.textContent?.trim() ?? "");
  }

  it("defaults to ascending document number order", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-b",
        title: "Structural",
        document_number: "A-200",
      }),
      evidenceRow({
        id: "doc-a",
        title: "Architectural",
        document_number: "A-100",
      }),
      evidenceRow({
        id: "doc-c",
        title: "Services",
        document_number: "A-300",
      }),
    ]);

    expect(scheduleTitles()).toEqual(["Architectural", "Structural", "Services"]);
    const documentNumberHeader = screen.getByRole("columnheader", {
      name: "Document number",
    });
    expect(documentNumberHeader).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    expect(documentNumberHeader).toHaveTextContent("#");
    expect(documentNumberHeader.closest("table")?.querySelector("col")).toHaveClass(
      "w-[4.5rem]",
    );
    expect(
      Array.from(documentNumberHeader.closest("thead")?.querySelectorAll("th") ?? []).map(
        (header) => header.textContent?.trim() ?? "",
      ),
    ).toEqual(["#", "Title", "Rev", "Cat", "Type", ""]);
    expect(screen.getByRole("columnheader", { name: "Rev" })).toHaveClass(
      "document-repository-col-revision",
    );
    expect(screen.getByRole("columnheader", { name: "Category" })).toHaveClass(
      "document-repository-col-category",
    );
    expect(screen.getByRole("columnheader", { name: "Document type" })).toHaveClass(
      "document-repository-col-type",
    );
    expect(screen.getByText("A-100").closest("td")).toHaveAttribute(
      "title",
      "A-100",
    );
  });

  it("strips markdown emphasis from drawing numbers in the register", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-a",
        title: "Cover Sheet",
        document_number: "**A-000**",
      }),
    ]);

    expect(screen.getByText("A-000")).toBeInTheDocument();
    expect(screen.queryByText("**A-000**")).not.toBeInTheDocument();
    expect(screen.getByText("A-000").closest("td")).toHaveAttribute(
      "title",
      "A-000",
    );
  });

  it("sorts by title when the Title header is clicked", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-b",
        title: "Structural",
        document_number: "A-100",
      }),
      evidenceRow({
        id: "doc-a",
        title: "Architectural",
        document_number: "A-200",
      }),
      evidenceRow({
        id: "doc-c",
        title: "Services",
        document_number: "A-300",
      }),
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Title" }));

    expect(scheduleTitles()).toEqual(["Architectural", "Services", "Structural"]);
    expect(screen.getByRole("columnheader", { name: "Title" })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
  });

  it("toggles descending order on a second click of the same header", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-b",
        title: "Structural",
        document_number: "A-100",
        category: "Structural",
      }),
      evidenceRow({
        id: "doc-a",
        title: "Architectural",
        document_number: "A-200",
        category: "Architectural",
      }),
      evidenceRow({
        id: "doc-c",
        title: "Services",
        document_number: "A-300",
        category: "Services",
      }),
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Category" }));
    fireEvent.click(screen.getByRole("button", { name: "Category" }));

    expect(scheduleTitles()).toEqual(["Structural", "Architectural", "Services"]);
    expect(screen.getByRole("columnheader", { name: "Category" })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("shows document category instead of Inbox for unfiled files", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-arch",
        title: "Site Plan",
        relative_path: "04-projects/newtown/_inbox/ARCHITECTURE/CC-A-010.pdf",
                    category: "Architectural",
        document_subject: "none",
      }),
      evidenceRow({
        id: "doc-his",
        title: "HIS",
        relative_path: "04-projects/newtown/_inbox/heritage-impact.pdf",
        document_subject: "heritage",
      }),
    ]);

    expect(screen.getByText("Architect")).toBeInTheDocument();
    expect(screen.getByText("Heritage")).toBeInTheDocument();
    expect(screen.queryByText("Inbox")).not.toBeInTheDocument();
  });

  it("sorts by revision when the Rev header is clicked", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-b",
        title: "Structural",
        document_number: "A-100",
        revision: "B",
      }),
      evidenceRow({
        id: "doc-a",
        title: "Architectural",
        document_number: "A-200",
        revision: "A",
      }),
      evidenceRow({
        id: "doc-c",
        title: "Services",
        document_number: "A-300",
        revision: "C",
      }),
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Rev" }));

    expect(scheduleTitles()).toEqual(["Architectural", "Structural", "Services"]);
    expect(screen.getByRole("columnheader", { name: "Rev" })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
  });

  it("shows and sorts the document type column", () => {
    renderWithEvidence([
      evidenceRow({
        id: "doc-report",
        title: "Site Report",
        document_number: "A-100",
        document_class: "report",
      }),
      evidenceRow({
        id: "doc-drawing",
        title: "Site Plan",
        document_number: "A-200",
        document_class: "drawing",
      }),
    ]);

    expect(screen.getByText("Report")).toBeInTheDocument();
    expect(screen.getByText("Drawing")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Document type" }));

    expect(scheduleTitles()).toEqual(["Site Plan", "Site Report"]);
    expect(screen.getByRole("columnheader", { name: "Document type" })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
  });
});

describe("DocumentRepositoryPanel schedule filters", () => {
  function visibleScheduleTitles(): string[] {
    return screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.querySelector("td:nth-child(2)")?.textContent?.trim() ?? "");
  }

  it("combines multi-select categories with document type filters", async () => {
    renderWithEvidence([
      evidenceRow({
        id: "architect-drawing",
        title: "Architectural drawing",
        document_subject: "architect",
        document_class: "drawing",
      }),
      evidenceRow({
        id: "structural-drawing",
        title: "Structural drawing",
        document_subject: "structural",
        document_class: "drawing",
      }),
      evidenceRow({
        id: "architect-report",
        title: "Architectural report",
        document_subject: "architect",
        document_class: "report",
      }),
    ]);

    fireEvent.pointerDown(screen.getByRole("button", { name: "Filter category" }), {
      button: 0,
      ctrlKey: false,
    });
    const selectAll = await screen.findByRole("menuitemcheckbox", { name: "Select all" });
    expect(selectAll).toHaveAttribute("aria-checked", "true");
    expect(
      screen.getByRole("menuitemcheckbox", { name: "Architect" }),
    ).toHaveAttribute("aria-checked", "true");

    fireEvent.click(selectAll);
    fireEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Architect" }));
    fireEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Structural" }));
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });

    expect(visibleScheduleTitles()).toEqual([
      "Architectural drawing",
      "Architectural report",
      "Structural drawing",
    ]);

    fireEvent.pointerDown(screen.getByRole("button", { name: "Filter document type" }), {
      button: 0,
      ctrlKey: false,
    });
    fireEvent.click(
      await screen.findByRole("menuitemcheckbox", { name: "Select all" }),
    );
    fireEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Drawing" }));
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });

    expect(visibleScheduleTitles()).toEqual([
      "Architectural drawing",
      "Structural drawing",
    ]);
  });

  it("keeps the transmittal action disabled until source documents are selected", () => {
    const onCreateTransmittal = vi.fn();
    const { rerender } = render(
      <DocumentRepositoryPanel
        projectId="project-1"
        evidence={[evidenceRow({ id: "doc-1" })]}
        selectedEvidenceId={null}
        selectedEvidenceIds={new Set()}
        workspaceTree={[]}
        selectedWorkspacePath={null}
        onSelectEvidence={vi.fn()}
        onSelectedEvidenceIdsChange={vi.fn()}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
        onViewWorkbench={vi.fn()}
        onViewFolder={vi.fn()}
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        onCreateTransmittal={onCreateTransmittal}
      />,
    );

    expect(screen.getByRole("button", { name: "Create transmittal" })).toBeDisabled();

    rerender(
      <DocumentRepositoryPanel
        projectId="project-1"
        evidence={[evidenceRow({ id: "doc-1" })]}
        selectedEvidenceId={null}
        selectedEvidenceIds={new Set(["doc-1"])}
        workspaceTree={[]}
        selectedWorkspacePath={null}
        onSelectEvidence={vi.fn()}
        onSelectedEvidenceIdsChange={vi.fn()}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
        onViewWorkbench={vi.fn()}
        onViewFolder={vi.fn()}
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        onCreateTransmittal={onCreateTransmittal}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create transmittal from 1 selected document",
      }),
    );
    expect(onCreateTransmittal).toHaveBeenCalledOnce();
  });
});

describe("DocumentRepositoryPanel bulk classification", () => {
  beforeEach(() => {
    batchClassificationMutateAsync.mockReset();
    batchClassificationMutateAsync.mockResolvedValue({ documents: [] });
    batchClassificationIsPending = false;
  });

  it("changes the category for the selected source documents from the context menu", async () => {
    render(
      <DocumentRepositoryPanel
        projectId="project-1"
        evidence={[
          evidenceRow({ id: "doc-1", title: "Ground Floor", document_class: "drawing" }),
          evidenceRow({ id: "doc-2", title: "First Floor", document_class: "drawing" }),
        ]}
        selectedEvidenceId="doc-1"
        selectedEvidenceIds={new Set(["doc-1", "doc-2"])}
        workspaceTree={[]}
        selectedWorkspacePath={null}
        onSelectEvidence={vi.fn()}
        onSelectedEvidenceIdsChange={vi.fn()}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
        onViewWorkbench={vi.fn()}
        onViewFolder={vi.fn()}
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.contextMenu(screen.getByText("Ground Floor"));
    const documentTypeMenu = await screen.findByRole("menuitem", {
      name: "Change document type",
    });
    const categoryMenu = await screen.findByRole("menuitem", {
      name: "Change category",
    });
    await waitFor(() => expect(documentTypeMenu).toHaveFocus());
    fireEvent.keyDown(documentTypeMenu, { key: "ArrowDown" });
    expect(categoryMenu).toHaveFocus();
    fireEvent.keyDown(categoryMenu, { key: "ArrowRight" });
    fireEvent.click(
      await screen.findByRole("menuitem", { name: /^Architect$/ }),
    );

    await waitFor(() => {
      expect(batchClassificationMutateAsync).toHaveBeenCalledOnce();
    });
    const change = batchClassificationMutateAsync.mock.calls[0]?.[0];
    expect(change?.documentSubject).toBe("architect");
    expect(new Set(change?.documentIds)).toEqual(new Set(["doc-1", "doc-2"]));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Category updated for 2 documents",
    );
  });

  it("allows a different selection to be classified while an earlier batch is pending", async () => {
    const firstBatch = deferred<{ documents: EvidencePreview[] }>();
    batchClassificationMutateAsync.mockImplementationOnce(() => firstBatch.promise);
    const evidence = [
      evidenceRow({ id: "doc-1", title: "Ground Floor", document_class: "drawing" }),
      evidenceRow({ id: "doc-2", title: "First Floor", document_class: "drawing" }),
      evidenceRow({ id: "doc-3", title: "Elevations", document_class: "drawing" }),
      evidenceRow({ id: "doc-4", title: "Sections", document_class: "drawing" }),
    ];
    const commonProps = {
      projectId: "project-1",
      evidence,
      selectedEvidenceId: "doc-1",
      workspaceTree: [],
      selectedWorkspacePath: null,
      onSelectEvidence: vi.fn(),
      onSelectedEvidenceIdsChange: vi.fn(),
      onSelectWorkspacePath: vi.fn(),
      onOpenWorkflow: vi.fn(),
      onViewWorkbench: vi.fn(),
      onViewFolder: vi.fn(),
      onUploadComplete: vi.fn().mockResolvedValue(undefined),
    };
    const view = render(
      <DocumentRepositoryPanel
        {...commonProps}
        selectedEvidenceIds={new Set(["doc-1", "doc-2"])}
      />,
    );

    fireEvent.contextMenu(screen.getByText("Ground Floor"));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Change category" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: /^Architect$/ }));
    await waitFor(() => expect(batchClassificationMutateAsync).toHaveBeenCalledOnce());

    batchClassificationIsPending = true;
    view.rerender(
      <DocumentRepositoryPanel
        {...commonProps}
        selectedEvidenceId="doc-3"
        selectedEvidenceIds={new Set(["doc-3", "doc-4"])}
      />,
    );
    fireEvent.contextMenu(screen.getByText("Elevations"));

    expect(
      await screen.findByRole("menuitem", { name: "Change category" }),
    ).toBeEnabled();
    firstBatch.resolve({ documents: [] });
  });
});

function renderScheduleSelection({
  selectedEvidenceId = null,
  selectedEvidenceIds,
}: {
  selectedEvidenceId?: string | null;
  selectedEvidenceIds: Set<string>;
}) {
  const onSelectedEvidenceIdsChange = vi.fn();
  render(
    <DocumentRepositoryPanel
      projectId="project-1"
      evidence={[
        evidenceRow({ id: "doc-1", title: "Brief" }),
        evidenceRow({ id: "doc-2", title: "Drawing" }),
        evidenceRow({ id: "doc-3", title: "Spec" }),
      ]}
      selectedEvidenceId={selectedEvidenceId}
      selectedEvidenceIds={selectedEvidenceIds}
      workspaceTree={[]}
      selectedWorkspacePath={null}
      onSelectEvidence={vi.fn()}
      onSelectedEvidenceIdsChange={onSelectedEvidenceIdsChange}
      onSelectWorkspacePath={vi.fn()}
      onOpenWorkflow={vi.fn()}
      onViewWorkbench={vi.fn()}
      onViewFolder={vi.fn()}
      onUploadComplete={vi.fn().mockResolvedValue(undefined)}
    />,
  );
  return { onSelectedEvidenceIdsChange };
}

describe("DocumentRepositoryPanel schedule selection", () => {
  it("replaces a loaded transmittal selection on a plain click", () => {
    const { onSelectedEvidenceIdsChange } = renderScheduleSelection({
      selectedEvidenceIds: new Set(["doc-1", "doc-2"]),
    });

    fireEvent.click(screen.getByText("Spec"));
    expect(onSelectedEvidenceIdsChange).toHaveBeenCalledWith(new Set(["doc-3"]));
  });

  it("appends with Ctrl after a loaded transmittal", () => {
    const { onSelectedEvidenceIdsChange } = renderScheduleSelection({
      selectedEvidenceIds: new Set(["doc-1", "doc-2"]),
    });

    fireEvent.click(screen.getByText("Spec"), { ctrlKey: true });
    expect(onSelectedEvidenceIdsChange).toHaveBeenCalledWith(
      new Set(["doc-1", "doc-2", "doc-3"]),
    );
  });

  it("ranges with Shift from the current document after a loaded transmittal", () => {
    const { onSelectedEvidenceIdsChange } = renderScheduleSelection({
      selectedEvidenceId: "doc-1",
      selectedEvidenceIds: new Set(["doc-1", "doc-2"]),
    });

    fireEvent.click(screen.getByText("Spec"), { shiftKey: true });
    expect(onSelectedEvidenceIdsChange).toHaveBeenCalledWith(
      new Set(["doc-1", "doc-2", "doc-3"]),
    );
  });
});

describe("DocumentRepositoryPanel project pulse", () => {
  const pulseFeed = {
    attention: [
      {
        id: "drawing_revision:source_document:doc-1",
        kind: "attention" as const,
        signal_type: "drawing_revision" as const,
        title: "S203 Rev C supersedes Rev B",
        body: "S203 Rev C supersedes Rev B",
        domain: "STRUCTURE",
        evidence: [
          {
            reference_type: "source_document",
            reference_id: "doc-1",
            label: "S203.pdf",
          },
        ],
        actions: ["view_evidence", "dismiss"],
        created_at: "2026-08-19T00:00:00Z",
      },
    ],
    other: [],
    attention_count: 1,
    generated_at: "2026-08-19T00:00:00Z",
    since: "2026-08-12T00:00:00Z",
  };

  function renderWithPulse() {
    return render(
      <DocumentRepositoryPanel
        projectId="project-1"
        evidence={[evidenceRow()]}
        selectedEvidenceId={null}
        workspaceTree={[]}
        selectedWorkspacePath={null}
        onSelectEvidence={vi.fn()}
        onSelectWorkspacePath={vi.fn()}
        onOpenWorkflow={vi.fn()}
        onViewWorkbench={vi.fn()}
        onViewFolder={vi.fn()}
        onUploadComplete={vi.fn().mockResolvedValue(undefined)}
        pulseFeed={pulseFeed}
      />,
    );
  }

  it("keeps pulse collapsed and document rows visible by default", () => {
    renderWithPulse();

    expect(screen.getByRole("button", { name: /correspondence/i })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.queryByTestId("project-pulse")).not.toBeInTheDocument();
    expect(screen.getByText("Owner Brief")).toBeInTheDocument();
  });

  it("shows attention items above the document list when pulse is opened", () => {
    renderWithPulse();

    fireEvent.click(screen.getByRole("button", { name: /correspondence/i }));

    const pulse = screen.getByTestId("project-pulse");
    const tables = screen.getAllByRole("table");
    const list = tables[tables.length - 1];
    expect(list).toBeDefined();
    expect(pulse.compareDocumentPosition(list!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("S203 Rev C supersedes Rev B")).toBeInTheDocument();
    expect(screen.getByText("Owner Brief")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /correspondence/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("hides pulse items again when the icon is toggled off", () => {
    renderWithPulse();
    const pulseButton = screen.getByRole("button", { name: /correspondence/i });

    fireEvent.click(pulseButton);
    fireEvent.click(pulseButton);

    expect(screen.queryByTestId("project-pulse")).not.toBeInTheDocument();
    expect(screen.getByText("Owner Brief")).toBeInTheDocument();
  });
});
