import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProcurementRequestPanel } from "@/components/project/ProcurementRequestPanel";
import { api } from "@/lib/api";
import type {
  DraftArtifactSummary,
  ProcurementRequest,
  ProjectDetail,
} from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    listProcurementRequests: vi.fn(),
    getLatestDraft: vi.fn(),
  },
}));

vi.mock("@/components/project/DraftReviewPanel", () => ({
  DraftReviewPanel: ({ draft }: { draft: DraftArtifactSummary }) => (
    <div>{draft.title}</div>
  ),
}));

const draft: DraftArtifactSummary = {
  id: "main-works-rft-v2",
  project_id: "mosaic",
  workflow_type: "trade_rft_main_works",
  version: 2,
  status: "draft",
  title: "Request for Tender - Main Works",
  workspace_path:
    "04-projects/mosaic-apartments/05-procurement/main_works/02-tender-pack/main_works_rft_v02.draft.md",
  author_user_id: "user-1",
  model: null,
  runtime: "clerk-trade-procurement",
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

const request: ProcurementRequest = {
  id: "request-1",
  project_id: "mosaic",
  created_by_user_id: "user-1",
  kind: "trade_rft",
  target_name: "Main Works",
  target_slug: "main_works",
  status: "draft",
  current_draft_artifact_id: draft.id,
  current_draft: draft,
  issued_at: null,
  closed_at: null,
  revision: 1,
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

describe("ProcurementRequestPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listProcurementRequests).mockResolvedValue([request]);
    vi.mocked(api.getLatestDraft).mockResolvedValue(null);
  });

  it("does not auto-select a request or report a draft until the user opens one", async () => {
    const user = userEvent.setup();
    const onDraftSelected = vi.fn();

    render(
      <ProcurementRequestPanel
        project={{ id: "mosaic", title: "Mosaic Apartments" } as ProjectDetail}
        activeRun={null}
        isRunning={false}
        error={null}
        refreshToken={0}
        renderGate={() => null}
        onCreate={vi.fn()}
        onDraftSelected={onDraftSelected}
      />,
    );

    const open = await screen.findByLabelText("Open procurement request");
    expect(open).toHaveTextContent("Select a package to view or open");
    expect(onDraftSelected).not.toHaveBeenCalled();
    expect(screen.queryByText(draft.title)).toBeNull();

    await user.click(open);
    await user.click(
      screen.getByRole("menuitem", { name: "Main Works · Trade package · v2" }),
    );

    await waitFor(() => expect(onDraftSelected).toHaveBeenCalledWith(draft));
    expect(await screen.findByText(draft.title)).toBeTruthy();
  });

  it("puts create controls above the package list with no type or discipline labels", async () => {
    const user = userEvent.setup();

    render(
      <ProcurementRequestPanel
        project={{ id: "mosaic", title: "Mosaic Apartments" } as ProjectDetail}
        activeRun={null}
        isRunning={false}
        error={null}
        refreshToken={0}
        renderGate={() => null}
        onCreate={vi.fn()}
      />,
    );

    const open = await screen.findByLabelText("Open procurement request");
    await user.click(open);
    expect(
      screen.getByRole("menuitem", {
        name: "Select a package to view or open",
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole("menuitem", {
        name: "Main Works · Trade package · v2",
      }),
    ).toBeTruthy();
    await user.keyboard("{Escape}");

    expect(screen.queryByText(/^draft$/i)).toBeNull();
    expect(screen.queryByText(/^Open$/)).toBeNull();
    expect(screen.queryByText(/^Type$/)).toBeNull();
    expect(screen.queryByText(/^Discipline$/)).toBeNull();
    expect(screen.getByLabelText("Request type")).toBeTruthy();
    expect(screen.getByLabelText("Discipline")).toHaveAttribute(
      "placeholder",
      "Architect",
    );
    expect(screen.getByRole("button", { name: /create consultant/i })).toBeTruthy();

    const type = screen.getByLabelText("Request type");
    expect(type.compareDocumentPosition(open) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
