import { render, screen, waitFor, within } from "@testing-library/react";
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

function draftSummary(
  id: string,
  title: string,
  workflowType: string,
  version: number,
): DraftArtifactSummary {
  return {
    id,
    project_id: "mosaic",
    workflow_type: workflowType,
    version,
    status: "draft",
    title,
    workspace_path: `04-projects/mosaic/${id}.draft.md`,
    author_user_id: "user-1",
    model: null,
    runtime: "clerk-consultant-procurement",
    created_at: "2026-08-09T00:00:00Z",
    updated_at: "2026-08-09T00:00:00Z",
  };
}

function request(partial: Partial<ProcurementRequest> & Pick<
  ProcurementRequest,
  "id" | "kind" | "target_name" | "current_draft"
>): ProcurementRequest {
  return {
    project_id: "mosaic",
    created_by_user_id: "user-1",
    target_slug: partial.target_name.toLowerCase().replace(/\s+/g, "_"),
    status: "draft",
    current_draft_artifact_id: partial.current_draft?.id ?? null,
    issued_at: null,
    closed_at: null,
    revision: 1,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...partial,
  };
}

const architectDraft = draftSummary(
  "architect-rfp-v1",
  "Request for Proposal - Architect",
  "consultant_procurement_architect",
  1,
);
const plannerDraft = draftSummary(
  "planner-rfp-v1",
  "Request for Proposal - Town planner",
  "consultant_procurement_town_planner",
  1,
);
const tradeDraft = draftSummary(
  "main-works-rft-v2",
  "Request for Tender - Main Works",
  "trade_rft_main_works",
  2,
);

const architect = request({
  id: "architect",
  kind: "consultant_rfp",
  target_name: "Architect",
  current_draft: architectDraft,
  updated_at: "2026-08-12T00:00:00Z",
});
const planner = request({
  id: "planner",
  kind: "consultant_rfp",
  target_name: "Town planner",
  current_draft: plannerDraft,
  updated_at: "2026-08-08T00:00:00Z",
});
const trade = request({
  id: "trade",
  kind: "trade_rft",
  target_name: "Main Works",
  current_draft: tradeDraft,
  updated_at: "2026-08-10T00:00:00Z",
});

function renderPanel(
  requests: ProcurementRequest[],
  onDraftSelected: (draft: DraftArtifactSummary) => void = vi.fn(),
) {
  vi.mocked(api.listProcurementRequests).mockResolvedValue(requests);
  return {
    onDraftSelected,
    ...render(
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
    ),
  };
}

describe("ProcurementRequestPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getLatestDraft).mockResolvedValue(null);
  });

  it("opens the latest package on revisit and reports its draft", async () => {
    const { onDraftSelected } = renderPanel([planner, architect, trade]);

    expect(
      await screen.findByRole("tab", { name: "Architect v1" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Consultant" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByRole("tab", { name: "Main Works v2" })).toBeNull();
    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(architectDraft),
    );
    expect(await screen.findByText(architectDraft.title)).toBeTruthy();
  });

  it("filters chips by kind and opens the latest package in that kind", async () => {
    const user = userEvent.setup();
    const { onDraftSelected } = renderPanel([planner, architect, trade]);

    await screen.findByText(architectDraft.title);
    await user.click(screen.getByRole("tab", { name: "Trade package" }));

    expect(
      await screen.findByRole("tab", { name: "Main Works v2" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Architect v1" })).toBeNull();
    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(tradeDraft),
    );
    expect(await screen.findByText(tradeDraft.title)).toBeTruthy();
  });

  it("opens a package when its chip is selected", async () => {
    const user = userEvent.setup();
    const { onDraftSelected } = renderPanel([planner, architect]);

    await screen.findByText(architectDraft.title);
    await user.click(screen.getByRole("tab", { name: "Town planner v1" }));

    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(plannerDraft),
    );
    expect(await screen.findByText(plannerDraft.title)).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Town planner v1" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("uses Cost Plan tab buttons for kind and packages, with create beside them", async () => {
    renderPanel([architect]);

    const kinds = await screen.findByRole("tablist", { name: "Request type" });
    expect(within(kinds).getByRole("tab", { name: "Consultant" })).toBeTruthy();
    expect(within(kinds).getByRole("tab", { name: "Trade package" })).toBeTruthy();
    expect(within(kinds).getByRole("tab", { name: "Supplier quote" })).toBeTruthy();

    const packages = screen.getByRole("tablist", {
      name: "Open procurement request",
    });
    expect(within(packages).getByRole("tab", { name: "Architect v1" })).toBeTruthy();

    expect(screen.queryByText("Select a package to view or open")).toBeNull();
    expect(
      screen.queryByText(/Latest version opens automatically/i),
    ).toBeNull();
    expect(screen.queryByText(/^Type$/)).toBeNull();
    expect(screen.queryByText(/^Discipline$/)).toBeNull();
    expect(screen.getByLabelText("Discipline")).toHaveAttribute(
      "placeholder",
      "Architect",
    );
    expect(screen.getByRole("button", { name: /create consultant/i })).toBeTruthy();
  });

  it("shows an empty hint when the selected kind has no packages", async () => {
    const user = userEvent.setup();
    renderPanel([architect]);

    await screen.findByRole("tab", { name: "Architect v1" });
    await user.click(screen.getByRole("tab", { name: "Trade package" }));

    expect(
      await screen.findByText("No requests yet. Create the first one above."),
    ).toBeTruthy();
    expect(screen.queryByRole("tab", { name: "Architect v1" })).toBeNull();
    expect(screen.queryByText(architectDraft.title)).toBeNull();
  });
});
