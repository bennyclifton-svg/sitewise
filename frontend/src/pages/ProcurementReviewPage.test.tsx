import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProcurementReviewPage } from "./ProcurementReviewPage";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import type { DraftArtifact } from "@/lib/types/project";
import type { ProcurementReviewRun } from "@/lib/types/procurement-review";

vi.mock("@/lib/api", () => ({ api: { getProcurementReview: vi.fn(), getProcurementReviewEvidence: vi.fn(), retryProcurementReview: vi.fn(), downloadDraftExport: vi.fn() } }));
vi.mock("@/components/project/DraftReviewPanel", () => ({ DraftReviewPanel: ({ draft }: { draft: DraftArtifact }) => <article>{draft.content_markdown}</article> }));

const run: ProcurementReviewRun = { comparison_id: "comparison", row_id: "row", package_name: "Structural", phase: "reading", activity: "running", started_at: "2026-09-06T01:00:00Z", draft: null, error: null, can_retry: true, documents: [{ id: "document", filename: "Fee.pdf", firm_name: "Engineers", state: "reading", pages: 3, pages_read: 2, complete: false }] };
function show() {
  return render(<MemoryRouter initialEntries={["/projects/project/procurement-reviews/comparison"]}><Routes><Route element={<Outlet context={{ project: { title: "Test project" } }} />}><Route path="/projects/:projectId/procurement-reviews/:comparisonId" element={<ProcurementReviewPage />} /></Route></Routes></MemoryRouter>);
}
beforeEach(() => { queryClient.clear(); vi.clearAllMocks(); });

describe("ProcurementReviewPage", () => {
  it("does not claim to be reading before receiving status", () => {
    vi.mocked(api.getProcurementReview).mockReturnValue(new Promise(() => {}));
    show();
    expect(screen.queryByText("Reading submissions")).toBeNull();
    expect(screen.getByRole("heading", { name: "Connecting to comparison" })).toBeTruthy();
  });

  it("keeps saved progress visible after a status request fails", async () => {
    queryClient.setQueryData(["procurement-review", "project", "comparison"], run);
    vi.mocked(api.getProcurementReview).mockRejectedValue(new Error("Temporary network failure"));
    const { container } = show();
    await act(async () => { await queryClient.refetchQueries({ queryKey: ["procurement-review", "project", "comparison"] }); });
    expect(screen.getAllByText("2 of 3 pages read").length).toBeGreaterThan(0);
    expect(screen.queryByText("Could not open this comparison.")).toBeNull();
    expect(await screen.findByText(/Showing the last saved progress/)).toBeTruthy();
    expect(container.querySelectorAll(".streaming-cube")).toHaveLength(1);
  });

  it("keeps the initial connection error stable during automatic retries and recovers", async () => {
    vi.useFakeTimers();
    let resolve!: (value: ProcurementReviewRun) => void;
    vi.mocked(api.getProcurementReview).mockRejectedValueOnce(new Error("offline")).mockReturnValue(new Promise((done) => { resolve = done; }));
    const view = show();
    try {
      await act(async () => { await vi.advanceTimersByTimeAsync(20); });
      expect(screen.getByRole("heading", { name: "Waiting for a status update" })).toBeTruthy();
      await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
      expect(api.getProcurementReview).toHaveBeenCalledTimes(2);
      expect(screen.getByRole("heading", { name: "Waiting for a status update" })).toBeTruthy();
      expect(screen.queryByText("Reading submissions")).toBeNull();
      await act(async () => { resolve(run); await vi.advanceTimersByTimeAsync(20); });
      expect(screen.getByRole("heading", { name: "Reading submissions" })).toBeTruthy();
      expect(screen.queryByText(/Status updates are temporarily unavailable/)).toBeNull();
    } finally { view.unmount(); vi.useRealTimers(); }
  });

  it("shows measured reading progress separately from preparation", async () => {
    vi.mocked(api.getProcurementReview).mockResolvedValue({ ...run, phase: "preparing", documents: [{ ...run.documents[0], complete: true, state: "complete", pages_read: 3 }] });
    show();
    expect(await screen.findByRole("heading", { name: "Preparing recommendation" })).toBeTruthy();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("3");
    expect(screen.getByRole("progressbar").getAttribute("aria-valuemax")).toBe("3");
    expect(screen.getByText("Prepare recommendation").closest("li")?.getAttribute("aria-current")).toBe("step");
    expect(screen.getByText("Report ready").closest("li")?.getAttribute("aria-current")).toBeNull();
  });

  it("does not invent a page total while a file is opening", async () => {
    vi.mocked(api.getProcurementReview).mockResolvedValue({ ...run, documents: [{ ...run.documents[0], pages: null, pages_read: 0, state: "opening" }] });
    show();
    expect(await screen.findByText("Opening file")).toBeTruthy();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByText("Page count available as files open")).toBeTruthy();
  });

  it("withholds cached progress if access is denied", async () => {
    queryClient.setQueryData(["procurement-review", "project", "comparison"], run);
    vi.mocked(api.getProcurementReview).mockRejectedValue(new ApiError("Not found", { kind: "http", status: 404 }));
    show();
    await act(async () => { await queryClient.refetchQueries({ queryKey: ["procurement-review", "project", "comparison"] }); });
    expect(await screen.findByRole("heading", { name: "Comparison unavailable" })).toBeTruthy();
    expect(screen.queryByText("Fee.pdf")).toBeNull();
  });

  it("does not offer a retry when processing needs a service update", async () => {
    vi.mocked(api.getProcurementReview).mockResolvedValue({ ...run, phase: "failed", can_retry: false, error: "This review needs a service update before it can continue." });
    show();
    expect(await screen.findByRole("heading", { name: "Review needs attention" })).toBeTruthy();
    expect(screen.getByText(/This review needs a service update/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Retry review" })).toBeNull();
  });

  it("reopens a running comparison and retries saved work", async () => {
    vi.mocked(api.getProcurementReview).mockResolvedValue({ ...run, phase: "failed", error: "Could not read Fee.pdf" });
    vi.mocked(api.retryProcurementReview).mockResolvedValue({ comparison_id: "comparison" });
    show();
    expect((await screen.findAllByText("2 of 3 pages read")).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: "Retry review" }));
    expect(api.retryProcurementReview).toHaveBeenCalledWith("comparison");
    expect(screen.getByRole("link", { name: "Procurement" }).getAttribute("href")).toBe("/projects/project?workflow=procurement-requests");
  });

  it("renders the Markdown artefact and uses the standard Word/PDF menu", async () => {
    const draft = { id: "draft", title: "Structural quote review", version: 1, workflow_type: "tender_report_row", content_markdown: "Recommendation with source [1]." } as DraftArtifact;
    vi.mocked(api.getProcurementReview).mockResolvedValue({ ...run, phase: "complete", draft });
    vi.mocked(api.downloadDraftExport).mockRejectedValue(new Error("download test"));
    show();
    expect(await screen.findByText("Recommendation with source [1].")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Download recommendation" }));
    expect(screen.getByRole("menuitem", { name: "Word" })).toBeTruthy();
    await userEvent.click(screen.getByRole("menuitem", { name: "PDF" }));
    await waitFor(() => expect(api.downloadDraftExport).toHaveBeenCalledWith("project", "draft", "pdf"));
  });
});
