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
    getLatestDraft: vi.fn(),
    getProjectDraft: vi.fn(),
    downloadDraftExport: vi.fn(),
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
const supplierDraft = draftSummary(
  "windows-rfq-v1",
  "Request for Quotation - Windows",
  "trade_rfq_windows",
  1,
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
const supplier = request({
  id: "supplier",
  kind: "trade_rfq",
  target_name: "Windows",
  current_draft: supplierDraft,
  updated_at: "2026-08-13T00:00:00Z",
});

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
      linked_request_ids: [],
      no_longer_required: false,
    },
  ],
};

function renderPanel(
  requests: ProcurementRequest[],
  onDraftSelected: (draft: DraftArtifactSummary) => void = vi.fn(),
) {
  vi.mocked(api.listProcurementRequests).mockResolvedValue(requests);
  const onCreate = vi.fn();
  const onUpdate = vi.fn();
  return {
    onDraftSelected,
    onCreate,
    onUpdate,
    ...render(
      <QueryClientProvider client={queryClient}>
        <ProcurementRequestPanel
          project={{ id: "mosaic", title: "Mosaic Apartments" } as ProjectDetail}
          activeRun={null}
          isRunning={false}
          error={null}
          refreshToken={0}
          renderGate={() => null}
          onCreate={onCreate}
          onUpdate={onUpdate}
          onDraftSelected={onDraftSelected}
        />
      </QueryClientProvider>,
    ),
  };
}

describe("ProcurementRequestPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    vi.mocked(api.getLatestDraft).mockResolvedValue(null);
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

  async function openDisciplineMenu() {
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Discipline suggestions" }));
    return user;
  }

  it("opens the latest package on revisit and reports its draft", async () => {
    const { onDraftSelected } = renderPanel([planner, architect, trade]);

    expect(await screen.findByLabelText("Discipline")).toHaveValue("Architect");
    expect(screen.queryByRole("tab")).toBeNull();
    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(architectDraft),
    );
    expect(await screen.findByText(architectDraft.title)).toBeTruthy();
  });

  it("opens a trade package from the discipline menu", async () => {
    const { onDraftSelected } = renderPanel([planner, architect, trade]);
    await screen.findByText(architectDraft.title);

    const user = await openDisciplineMenu();
    await user.click(screen.getByRole("option", { name: "Main Works 2" }));

    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(tradeDraft),
    );
    expect(await screen.findByText(tradeDraft.title)).toBeTruthy();
    expect(screen.getByLabelText("Discipline")).toHaveValue("Main Works");
  });

  it("opens a package when its discipline is selected", async () => {
    const { onDraftSelected } = renderPanel([planner, architect]);
    await screen.findByText(architectDraft.title);

    const user = await openDisciplineMenu();
    await user.click(screen.getByRole("option", { name: "Town planner 1" }));

    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(plannerDraft),
    );
    expect(await screen.findByText(plannerDraft.title)).toBeTruthy();
  });

  it("uses a PMP-style create/update row with revision markers in the menu", async () => {
    renderPanel([architect]);

    expect(await screen.findByLabelText("Discipline")).toHaveValue("Architect");
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.getByRole("button", { name: "Generate RFT" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Update RFT" })).toBeEnabled();

    await userEvent.click(screen.getByRole("button", { name: "Discipline suggestions" }));
    expect(screen.getByRole("option", { name: "Architect 1" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Electrical Services" })).toBeTruthy();
  });

  it("creates a consultant RFP or trade RFT from the combined list", async () => {
    const user = userEvent.setup();
    const { onCreate } = renderPanel([]);

    await screen.findByText("No requests yet. Create the first one above.");
    const field = screen.getByLabelText("Discipline");
    await user.type(field, "Architect");
    await user.click(screen.getByRole("button", { name: "Generate RFT" }));
    expect(onCreate).toHaveBeenCalledWith("consultant_rfp", "Architect");

    await user.clear(field);
    await user.type(field, "Electrical services");
    await user.click(screen.getByRole("button", { name: "Generate RFT" }));
    expect(onCreate).toHaveBeenCalledWith("trade_rft", "Electrical services");
  });

  it("opens Strategy beside the RFT controls and hides document exports", async () => {
    vi.mocked(api.ensureProcurementStrategy).mockResolvedValue(strategy);
    renderPanel([architect]);

    const strategyButton = await screen.findByRole("button", { name: "Strategy" });
    await userEvent.click(strategyButton);

    expect(await screen.findByRole("columnheader", { name: "Tenderer 1" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Tenderer 3" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Strategy" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.queryByRole("button", { name: /Download request/ })).toBeNull();
    expect(api.ensureProcurementStrategy).toHaveBeenCalledWith("mosaic");
  });

  it("updates the selected package", async () => {
    const user = userEvent.setup();
    const { onUpdate } = renderPanel([architect]);

    await screen.findByText(architectDraft.title);
    await user.click(screen.getByRole("button", { name: "Update RFT" }));
    expect(onUpdate).toHaveBeenCalledWith("consultant_rfp", "Architect");
  });

  it("shows an empty hint when there are no packages", async () => {
    renderPanel([]);

    expect(
      await screen.findByText("No requests yet. Create the first one above."),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Update RFT" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Download request for/ })).toBeDisabled();
  });

  it("places download and copy beside the package chips above the RFP", async () => {
    renderPanel([architect]);

    expect(await screen.findByText(architectDraft.title)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Download request for proposal" }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "Copy request for proposal" }),
    ).toBeEnabled();
  });

  it("downloads Word and PDF for the selected RFP", async () => {
    const user = userEvent.setup();
    vi.mocked(api.downloadDraftExport).mockResolvedValue(new Blob(["export"]));
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    renderPanel([architect]);
    await screen.findByText(architectDraft.title);

    await user.click(
      screen.getByRole("button", { name: "Download request for proposal" }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "Word" }));
    await waitFor(() => {
      expect(api.downloadDraftExport).toHaveBeenCalledWith(
        "mosaic",
        architectDraft.id,
        "docx",
      );
    });

    await user.click(
      screen.getByRole("button", { name: "Download request for proposal" }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "PDF" }));
    await waitFor(() => {
      expect(api.downloadDraftExport).toHaveBeenCalledWith(
        "mosaic",
        architectDraft.id,
        "pdf",
      );
    });
  });

  it("copies the selected RFP without block markers", async () => {
    const user = userEvent.setup();
    const documentMarkdown = [
      "# Request for Proposal - Architect",
      "",
      "Prepare a fee proposal. <!-- clerk:block id=blk_rfp -->",
    ].join("\n");
    vi.mocked(api.getProjectDraft).mockResolvedValue({
      ...architectDraft,
      content_markdown: documentMarkdown,
      provenance_metadata: null,
    });
    renderPanel([architect]);
    await screen.findByText(architectDraft.title);

    await user.click(
      screen.getByRole("button", { name: "Copy request for proposal" }),
    );

    await waitFor(async () => {
      expect(await navigator.clipboard.readText()).toBe(
        "# Request for Proposal - Architect\n\nPrepare a fee proposal.",
      );
    });
  });

  it("relabels download and copy for the selected RFT", async () => {
    renderPanel([architect, trade]);
    await screen.findByText(architectDraft.title);

    const user = await openDisciplineMenu();
    await user.click(screen.getByRole("option", { name: "Main Works 2" }));
    await screen.findByText(tradeDraft.title);

    expect(
      screen.getByRole("button", { name: "Download request for tender" }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "Copy request for tender" }),
    ).toBeEnabled();
  });

  it("lists supplier quotes with trades and opens the RFQ from the menu", async () => {
    const { onDraftSelected } = renderPanel([
      architect,
      trade,
      {
        ...supplier,
        updated_at: "2026-08-09T00:00:00Z",
      },
    ]);

    await screen.findByText(architectDraft.title);
    const user = await openDisciplineMenu();
    expect(screen.getByRole("option", { name: "Windows 1" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Main Works 2" })).toBeTruthy();

    await user.click(screen.getByRole("option", { name: "Windows 1" }));
    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(supplierDraft),
    );
    expect(await screen.findByText(supplierDraft.title)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Download request for quotation" }),
    ).toBeEnabled();
  });

  it("opens the latest supplier quote in the discipline field", async () => {
    const { onDraftSelected } = renderPanel([architect, supplier]);

    expect(await screen.findByLabelText("Discipline")).toHaveValue("Windows");
    await waitFor(() =>
      expect(onDraftSelected).toHaveBeenCalledWith(supplierDraft),
    );
    await openDisciplineMenu();
    expect(screen.getByRole("option", { name: "Architect 1" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Windows 1" })).toBeTruthy();
  });
});
