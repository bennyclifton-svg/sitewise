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
  onDraftSelected = vi.fn(),
  onOpenTenderComparison = vi.fn(),
}: {
  requests?: ProcurementRequest[];
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
    expect(
      screen.getByRole("columnheader", { name: "Status & notes" }),
    ).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Status" })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: "Notes" })).toBeNull();
    const requestLink = screen.getByRole("button", { name: /RFP v1 · Draft/ });
    expect(requestLink.closest("td")).toContainElement(
      screen.getByLabelText("Architect status"),
    );
    expect(requestLink.closest("td")).toContainElement(
      screen.getByLabelText("Architect notes"),
    );
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

    await user.click(await screen.findByRole("button", { name: /RFP v1 · Draft/ }));

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

    await user.click(await screen.findByLabelText("Architect status"));
    await user.click(screen.getByRole("menuitem", { name: "Recommendation" }));

    expect(screen.getByLabelText("Architect status")).toHaveTextContent(
      "Recommendation",
    );
    expect(
      screen
        .getByRole("button", { name: "Procurement strategy actions" })
        .querySelector(".animate-spin"),
    ).toBeNull();

    finishSave?.({
      ...strategy,
      revision: 2,
      rows: [{ ...strategy.rows[0], status: "evaluating" }],
    });
  });

  it("launches comparison from a row with at least two firms", async () => {
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
    const onOpenTenderComparison = vi.fn();
    renderPanel({ onOpenTenderComparison });

    await user.click(
      await screen.findByRole("button", { name: "Actions for Architect" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Compare firms" }));

    expect(onOpenTenderComparison).toHaveBeenCalledOnce();
  });
});
