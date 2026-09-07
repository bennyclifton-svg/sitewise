import { render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProcurementRequestPanel } from "@/components/project/ProcurementRequestPanel";
import { api } from "@/lib/api";
import { queryClient } from "@/lib/query-client";
import type {
  DraftArtifactSummary,
  ProcurementRequest,
  ProcurementStrategy,
  ProjectDetail,
} from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    listProcurementRequests: vi.fn(),
    listProjectDisciplines: vi.fn(),
    ensureProcurementStrategy: vi.fn(),
    getProcurementStrategy: vi.fn(),
    refreshProcurementStrategy: vi.fn(),
    applyProcurementStrategyOperations: vi.fn(),
    getProjectDraft: vi.fn(),
    downloadDraftExport: vi.fn(),
    startProcurementReview: vi.fn(),
  },
}));

vi.mock("@/components/project/DraftReviewPanel", () => ({
  DraftReviewPanel: ({ draft }: { draft: DraftArtifactSummary }) => (
    <div>{draft.title}</div>
  ),
}));

const architectDraft: DraftArtifactSummary = {
  id: "architect-rfp-v1",
  project_id: "mosaic",
  workflow_type: "consultant_procurement_architect",
  version: 1,
  status: "draft",
  title: "Request for Proposal - Architect",
  workspace_path: "04-projects/mosaic/architect-rfp-v1.draft.md",
  author_user_id: "user-1",
  model: null,
  runtime: "clerk-consultant-procurement",
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

const architectRequest: ProcurementRequest = {
  id: "architect-request",
  project_id: "mosaic",
  created_by_user_id: "user-1",
  kind: "consultant_rfp",
  target_name: "Architect",
  target_slug: "architect",
  discipline_code: "consultant.architect",
  strategy_row_id: "row-1",
  status: "draft",
  current_draft_artifact_id: architectDraft.id,
  current_draft: architectDraft,
  issued_at: null,
  closed_at: null,
  revision: 1,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-12T00:00:00Z",
};

const strategy: ProcurementStrategy = {
  id: "strategy-1",
  project_id: "mosaic",
  revision: 1,
  tenderer_column_count: 3,
  source_fingerprint: "abc",
  created_at: "2026-08-22T00:00:00Z",
  updated_at: "2026-08-22T00:00:00Z",
  rows: [
    {
      id: "row-1",
      discipline_code: "consultant.architect",
      discipline_label: "Architect",
      participant_type: "consultant",
      request_kind: "consultant_rfp",
      status: "not_started",
      notes: "",
      display_order: 100,
      origin: "derived",
      locked: false,
      candidates: [],
      linked_request_ids: [architectRequest.id],
      no_longer_required: false,
    },
  ],
};

function renderPanel({
  requests = [],
  openDraftId = null,
  onDraftSelected = vi.fn(),
  onOpenTenderComparison = vi.fn(),
}: {
  requests?: ProcurementRequest[];
  openDraftId?: string | null;
  onDraftSelected?: (draft: DraftArtifactSummary) => void;
  onOpenTenderComparison?: () => void;
} = {}) {
  vi.mocked(api.listProcurementRequests).mockResolvedValue(requests);
  const onCreate = vi.fn();
  const onUpdate = vi.fn();
  return {
    onCreate,
    onUpdate,
    onDraftSelected,
    onOpenTenderComparison,
    ...render(
      <QueryClientProvider client={queryClient}>
        <ProcurementRequestPanel
          project={{ id: "mosaic", title: "Mosaic Apartments" } as ProjectDetail}
          error={null}
          refreshToken={0}
          openDraftId={openDraftId}
          renderGate={() => null}
          onCreate={onCreate}
          onUpdate={onUpdate}
          onDraftSelected={onDraftSelected}
          onOpenTenderComparison={onOpenTenderComparison}
        />
      </QueryClientProvider>,
    ),
  };
}

describe("ProcurementRequestPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    vi.mocked(api.ensureProcurementStrategy).mockResolvedValue(strategy);
    vi.mocked(api.listProjectDisciplines).mockResolvedValue([
      {
        code: "consultant.architect",
        label: "Architect",
        participant_type: "consultant",
        request_kind: "consultant_rfp",
        workspace_slug: "architect",
      },
      {
        code: "trade.electrical",
        label: "Electrical Services",
        participant_type: "trade",
        request_kind: "trade_rft",
        workspace_slug: "electrical-services",
      },
    ]);
  });

  it("opens directly on the strategy table without the old global controls", async () => {
    renderPanel({ requests: [architectRequest] });

    expect(await screen.findByLabelText("Procurement Strategy")).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Firm 1" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Notes" })).toBeNull();
    const requestLink = screen.getByRole("button", { name: "Open Architect RFP" });
    expect(requestLink.closest("td")).toContainElement(
      screen.getByLabelText("Architect status"),
    );
    expect(screen.queryByLabelText("Architect notes")).toBeNull();
    expect(
      screen.getByRole("rowheader", { name: "Architect" }),
    ).not.toHaveTextContent("RFP");
    expect(screen.queryByLabelText("Discipline")).toBeNull();
    expect(screen.queryByRole("button", { name: "Generate RFT" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Strategy" })).toBeNull();
  });

  it("creates the correct request from its discipline row", async () => {
    const user = userEvent.setup();
    const { onCreate } = renderPanel();

    await user.click(await screen.findByRole("button", { name: "Actions for Architect" }));
    await user.click(screen.getByRole("menuitem", { name: "Create RFP" }));

    expect(onCreate).toHaveBeenCalledWith("consultant_rfp", "Architect");
  });

  it("opens an RFP from the row and keeps update actions in the detail view", async () => {
    const user = userEvent.setup();
    const onDraftSelected = vi.fn();
    const { onUpdate } = renderPanel({
      requests: [architectRequest],
      onDraftSelected,
    });

    await user.click(
      await screen.findByRole("button", { name: "Open Architect RFP" }),
    );

    expect(await screen.findByText(architectDraft.title)).toBeTruthy();
    await waitFor(() => expect(onDraftSelected).toHaveBeenCalledWith(architectDraft));
    await user.click(screen.getByRole("button", { name: "Update RFP" }));
    expect(onUpdate).toHaveBeenCalledWith(
      "consultant_rfp",
      architectRequest.target_name,
    );

    await user.click(screen.getByRole("button", { name: "Procurement" }));
    expect(await screen.findByLabelText("Procurement Strategy")).toBeTruthy();
  });

  it("opens the exact RFP selected by an artefact deep link", async () => {
    renderPanel({
      requests: [architectRequest],
      openDraftId: architectDraft.id,
    });

    expect(await screen.findByText(architectDraft.title)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Update RFP" })).toBeTruthy();
  });

  it("links a Civil engineer RFP to the Civil strategy row", async () => {
    vi.mocked(api.listProjectDisciplines).mockResolvedValue([
      {
        code: "consultant.civil",
        label: "Civil",
        participant_type: "consultant",
        request_kind: "consultant_rfp",
        workspace_slug: "civil-engineer",
      },
    ]);
    const civilDraft = {
      ...architectDraft,
      id: "civil-rfp-v1",
      workflow_type: "consultant_procurement_civil_engineer",
      title: "Request for Proposal - Civil Engineer",
    } satisfies DraftArtifactSummary;
    const civilRequest = {
      ...architectRequest,
      id: "civil-request",
      target_name: "Civil engineer",
      target_slug: "civil_engineer",
      discipline_code: null,
      strategy_row_id: null,
      current_draft_artifact_id: civilDraft.id,
      current_draft: civilDraft,
    } satisfies ProcurementRequest;
    vi.mocked(api.ensureProcurementStrategy).mockResolvedValue({
      ...strategy,
      rows: [
        {
          ...strategy.rows[0],
          id: "civil-row",
          discipline_code: "consultant.civil",
          discipline_label: "Civil",
          linked_request_ids: [],
        },
      ],
    });
    const user = userEvent.setup();
    renderPanel({ requests: [civilRequest] });

    const link = await screen.findByRole("button", { name: "Open Civil RFP" });
    await user.click(link);

    expect(await screen.findByText(civilDraft.title)).toBeTruthy();
  });

  it("shows a newly added discipline before its save completes", async () => {
    const user = userEvent.setup();
    let finishSave: ((value: ProcurementStrategy) => void) | undefined;
    vi.mocked(api.applyProcurementStrategyOperations).mockReturnValue(
      new Promise<ProcurementStrategy>((resolve) => {
        finishSave = resolve;
      }),
    );
    renderPanel({ requests: [architectRequest] });

    await user.click(
      await screen.findByRole("button", { name: "Actions for Architect" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Add row below" }));
    await user.click(screen.getByRole("button", { name: "Add row" }));

    expect(screen.getByLabelText("Electrical Services, Firm 1")).toBeTruthy();
    expect(api.applyProcurementStrategyOperations).toHaveBeenCalledWith(
      "mosaic",
      1,
      [
        {
          operation: "ADD_ROW",
          discipline_code: "trade.electrical",
          after_row_id: "row-1",
        },
      ],
    );

    finishSave?.({
      ...strategy,
      revision: 2,
      rows: [
        ...strategy.rows,
        {
          ...strategy.rows[0],
          id: "row-2",
          discipline_code: "trade.electrical",
          discipline_label: "Electrical Services",
          participant_type: "trade",
          request_kind: "trade_rft",
          display_order: 200,
          origin: "manual",
          linked_request_ids: [],
        },
      ],
    });
    await waitFor(() =>
      expect(screen.getByLabelText("Electrical Services, Firm 1")).toBeTruthy(),
    );
  });

  it("shows a changed status immediately while saving in the background", async () => {
    const user = userEvent.setup();
    let finishSave: ((value: ProcurementStrategy) => void) | undefined;
    vi.mocked(api.applyProcurementStrategyOperations).mockReturnValue(
      new Promise<ProcurementStrategy>((resolve) => {
        finishSave = resolve;
      }),
    );
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Architect: Recommendation" }),
    );

    expect(
      screen.getByRole("button", { name: "Architect: Recommendation" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: "Actions for Architect" }),
    ).not.toBeDisabled();

    finishSave?.({
      ...strategy,
      revision: 2,
      rows: [{ ...strategy.rows[0], status: "evaluating" }],
    });
  });

  it("queues further status changes without freezing the grid", async () => {
    const user = userEvent.setup();
    const saves: Array<(value: ProcurementStrategy) => void> = [];
    vi.mocked(api.applyProcurementStrategyOperations).mockImplementation(
      () =>
        new Promise<ProcurementStrategy>((resolve) => {
          saves.push(resolve);
        }),
    );
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Architect: Submitted" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Architect: Recommendation" }),
    );

    expect(
      screen.getByRole("button", { name: "Architect: Recommendation" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(api.applyProcurementStrategyOperations).toHaveBeenCalledTimes(1);

    saves[0]?.({
      ...strategy,
      revision: 2,
      rows: [{ ...strategy.rows[0], status: "responses_received" }],
    });
    await waitFor(() =>
      expect(api.applyProcurementStrategyOperations).toHaveBeenNthCalledWith(
        2,
        "mosaic",
        2,
        [
          {
            operation: "UPDATE_ROW",
            row_id: "row-1",
            status: "evaluating",
          },
        ],
      ),
    );
    saves[1]?.({
      ...strategy,
      revision: 3,
      rows: [{ ...strategy.rows[0], status: "evaluating" }],
    });
  });

  it("keeps a deleted row removed when an older strategy reload finishes afterward", async () => {
    const user = userEvent.setup();
    let finishSave: ((value: ProcurementStrategy) => void) | undefined;
    let finishReload: ((value: ProcurementStrategy) => void) | undefined;
    const unlinkedStrategy = {
      ...strategy,
      rows: [{ ...strategy.rows[0], linked_request_ids: [] }],
    } satisfies ProcurementStrategy;
    vi.mocked(api.applyProcurementStrategyOperations).mockReturnValue(
      new Promise<ProcurementStrategy>((resolve) => {
        finishSave = resolve;
      }),
    );
    vi.mocked(api.ensureProcurementStrategy).mockReset();
    vi.mocked(api.ensureProcurementStrategy)
      .mockResolvedValueOnce(unlinkedStrategy)
      .mockReturnValueOnce(
        new Promise<ProcurementStrategy>((resolve) => {
          finishReload = resolve;
        }),
      );
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Actions for Architect" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Delete Architect" }));

    expect(screen.queryByRole("rowheader", { name: "Architect" })).toBeNull();

    void queryClient.invalidateQueries({
      queryKey: ["project", "mosaic", "workbench", "procurement-strategy"],
      exact: true,
    });
    await waitFor(() =>
      expect(api.ensureProcurementStrategy).toHaveBeenCalledTimes(2),
    );

    finishSave?.({ ...strategy, revision: 2, rows: [] });
    await waitFor(() =>
      expect(screen.queryByRole("rowheader", { name: "Architect" })).toBeNull(),
    );

    finishReload?.(strategy);
    await waitFor(() =>
      expect(screen.queryByRole("rowheader", { name: "Architect" })).toBeNull(),
    );
  });

  it("starts one review from a single submitted firm with multiple files", async () => {
    const user = userEvent.setup();
    const comparisonReady = {
      ...strategy,
      rows: [
        {
          ...strategy.rows[0],
          candidates: [
            {
              id: "candidate-1",
              slot: 1,
              company_name: "North & Co",
              submission_files: [
                { workspace_file_id: "main", filename: "Fee.pdf", workspace_path: "quotes/Fee.pdf" },
                { workspace_file_id: "insurance", filename: "Insurance.pdf", workspace_path: "quotes/Insurance.pdf" },
              ],
              website_url: null,
              location_text: null,
              source_url: null,
              source_title: null,
              researched_at: null,
            },
            {
              id: "candidate-2",
              slot: 2,
              company_name: "South Studio",
              website_url: null,
              location_text: null,
              source_url: null,
              source_title: null,
              researched_at: null,
            },
          ],
        },
      ],
    } satisfies ProcurementStrategy;
    vi.mocked(api.ensureProcurementStrategy).mockResolvedValue(comparisonReady);
    vi.mocked(api.startProcurementReview).mockResolvedValue({ comparison_id: "review-1" });
    const onOpenTenderComparison = vi.fn();
    renderPanel({ onOpenTenderComparison });

    await user.click(
      await screen.findByRole("button", { name: "Actions for Architect" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Compare firms" }));

    await waitFor(() => expect(onOpenTenderComparison).toHaveBeenCalledWith("review-1"));
    expect(api.startProcurementReview).toHaveBeenCalledWith({ project_id: "mosaic", row_id: "row-1", expected_submission_revision: 1, rerun: true });
  });
});
