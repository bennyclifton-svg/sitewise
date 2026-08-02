import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { api } from "@/lib/api";
import type { DraftArtifact, WorkbookPreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    acceptDraft: vi.fn(),
    downloadWorkspaceFile: vi.fn(),
    getWorkbookPreview: vi.fn(),
    getProjectDraft: vi.fn(),
    getLatestDraft: vi.fn(),
    listDecisions: vi.fn(),
    patchDraft: vi.fn(),
  },
}));

const PROJECT_ID = "project-1";
const GREENBANK_COST_ITEMS = [
  ["Fees and charges", "Architect-PM architect / PM fee"],
  ["Fees and charges", "DA and CC authority fees"],
  ["Fees and charges", "BASIX certificate fee"],
  ["Fees and charges", "Sydney Water / infrastructure"],
  ["Fees and charges", "Levies and statutory"],
  ["Consultants", "Structural engineer"],
  ["Consultants", "Geotechnical engineer"],
  ["Consultants", "Surveyor"],
  ["Consultants", "Hydraulic / wastewater"],
  ["Consultants", "BASIX / energy assessor"],
  ["Consultants", "Principal certifier"],
  ["Construction", "Investigations, surveys and opening-up"],
  ["Construction", "Preliminaries, protection and temporary works"],
  ["Construction", "Hazardous-material controls and demolition"],
  ["Construction", "Existing-structure repair and new structural work"],
  ["Construction", "Envelope, roofing and old-to-new weatherproofing"],
  ["Construction", "Partitions, linings, doors and joinery"],
  ["Construction", "Kitchen, bathrooms and fittings"],
  ["Construction", "Building-services alterations and upgrades"],
  ["Construction", "Finishes, external works and making good"],
  ["PC allowances", "Kitchen joinery PC"],
  ["PC allowances", "Wet area / sanitary PC"],
  ["PC allowances", "Floor coverings PC"],
  ["PC allowances", "Lighting fittings PC"],
  ["Contingency / allowances", "Owner-held contingency"],
] as const;

function draft(overrides: Partial<DraftArtifact> = {}): DraftArtifact {
  return {
    id: "draft-1",
    project_id: PROJECT_ID,
    workflow_type: "create_pmp",
    version: 1,
    status: "draft",
    title: "Project Management Plan",
    workspace_path: "04-projects/demo/00-brief-pmp/PMP.md",
    author_user_id: "user-1",
    content_markdown: "# Original",
    model: "gpt-5.6-luna",
    runtime: "clerk-sitewise-create-pmp",
    provenance_metadata: null,
    created_at: "2026-07-04T12:00:00.000Z",
    updated_at: "2026-07-04T12:00:00.000Z",
    ...overrides,
  };
}

describe("DraftReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listDecisions).mockResolvedValue({
      decisions: [],
      set_revision: 1,
    });
  });

  it("shows refresh provenance strips for update drafts", () => {
    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          version: 3,
          provenance_metadata: {
            sections_changed: ["Scope & client requirements", "Risks & actions"],
            evidence_changed: {
              added: ["04-projects/demo/new-brief.md"],
              removed: ["04-projects/demo/old-brief.md"],
              superseded: ["04-projects/demo/old-brief.md"],
              downgraded: ["Appointment & fee"],
              conflicted: [],
            },
            trace: [
              {
                step: "evidence_sweep",
                status: "complete",
                message: "Swept evidence batch 1 of 1.",
                metadata: { batch_index: 0 },
              },
            ],
          },
        })}
        onDraftUpdated={vi.fn()}
        onRunUpdatePmp={vi.fn()}
      />,
    );

    expect(screen.getByText("What changed in v3")).toBeInTheDocument();
    expect(screen.getByText("Scope & client requirements")).toBeInTheDocument();
    expect(screen.getByText(/Evidence changes:/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh pmp from documents/i })).toBeInTheDocument();
  });

  it("saves edits and swaps to the returned draft version", async () => {
    const user = userEvent.setup();
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Edited",
      created_at: "2026-07-04T12:05:00.000Z",
      updated_at: "2026-07-04T12:05:00.000Z",
    });
    vi.mocked(api.patchDraft).mockResolvedValue(updated);
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft()}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /edit markdown/i }));
    const editor = screen.getByRole("textbox");
    await user.clear(editor);
    await user.type(editor, "# Edited");
    await user.click(screen.getByRole("button", { name: /save edits/i }));

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
    });
    expect(api.patchDraft).toHaveBeenCalledWith(PROJECT_ID, "draft-1", "# Edited", 1);
    expect(screen.getAllByText("v2")[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Edited" })).toBeInTheDocument();
  });

  it("loads the selected summary draft by id", async () => {
    const fullDraft = draft({ content_markdown: "# Loaded PMP\n\nContent" });
    vi.mocked(api.getProjectDraft).mockResolvedValue(fullDraft);

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={{
          id: "draft-1",
          project_id: PROJECT_ID,
          workflow_type: "create_pmp",
          version: 1,
          status: "draft",
          title: "Project Management Plan",
          workspace_path: "04-projects/demo/00-brief-pmp/PMP.md",
          author_user_id: "user-1",
          model: "gpt-5.6-luna",
          runtime: "clerk-sitewise-create-pmp",
          created_at: "2026-07-04T12:00:00.000Z",
          updated_at: "2026-07-04T12:00:00.000Z",
        }}
        onDraftUpdated={vi.fn()}
      />,
    );

    expect(api.getProjectDraft).toHaveBeenCalledWith(PROJECT_ID, "draft-1");
    expect(await screen.findByRole("heading", { name: "Loaded PMP" })).toBeInTheDocument();
    expect(api.getLatestDraft).not.toHaveBeenCalled();
  });

  it("edits one section and leaves the other section unchanged", async () => {
    const user = userEvent.setup();
    const original = draft({
      content_markdown: "# Title\n\n## First\n\nAlpha\n\n## Second\n\nBeta\n",
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## First\n\nGamma\n\n## Second\n\nBeta\n",
    });
    vi.mocked(api.patchDraft).mockResolvedValue(updated);
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Edit section" })[0]!);
    const editor = screen.getByRole("textbox");
    await user.clear(editor);
    await user.type(editor, "## First\n\nGamma\n");
    await user.click(screen.getByRole("button", { name: /save section/i }));

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
    });
    expect(api.patchDraft).toHaveBeenCalledWith(
      PROJECT_ID,
      "draft-1",
      expect.stringContaining("## Second\n\nBeta"),
      1,
    );
    expect(vi.mocked(api.patchDraft).mock.calls[0]?.[2]).toContain("Gamma");
    expect(vi.mocked(api.patchDraft).mock.calls[0]?.[2]).not.toContain("Alpha");
  });

  it("shows only the three-tab cost workbook with all 25 Greenbank items", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getWorkbookPreview).mockResolvedValue(greenbankWorkbookPreview());

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          workflow_type: "create_cost_plan",
          title: "Greenbank Cost Plan",
          workspace_path: "04-projects/greenbank/01-cost/cost_plan_v01.md",
          content_markdown: [
            "# Project Cost Plan",
            "## Cost plan summary and control decision",
            "## Budget reconciliation and cost breakdown",
            "## Commitments, allowances and exclusions",
            "## Risks, delivery gates and next actions",
          ].join("\n\n"),
          provenance_metadata: {
            workbook: {
              file_name: "Cost_Plan_v01.draft.xlsx",
              workspace_path:
                "04-projects/greenbank/01-cost/Cost_Plan_v01.draft.xlsx",
            },
          },
        })}
        workflowType="create_cost_plan"
        onDraftUpdated={vi.fn()}
        embedded
      />,
    );

    expect(await screen.findByRole("heading", { name: "Cost workbook" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summary" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Invoices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Variations" })).toBeInTheDocument();
    for (const [, item] of GREENBANK_COST_ITEMS) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }

    expect(screen.queryByText("Sections")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Cost plan summary and control decision" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /accept cost plan/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit markdown/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Seed consulted")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Invoices" }));
    expect(screen.getByText("INVOICES REGISTER")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Variations" }));
    expect(screen.getByText("VARIATIONS REGISTER")).toBeInTheDocument();
  });
});

function greenbankWorkbookPreview(): WorkbookPreview {
  const blankStyle = { fill_color: null, bold: false };
  const summaryRows = [
    ["Project Cost Plan - Greenbank", ...Array.from({ length: 11 }, () => "")],
    ["All figures exclude GST", ...Array.from({ length: 11 }, () => "")],
    Array.from({ length: 12 }, () => ""),
    [
      "Cost Code",
      "Category",
      "Cost Items",
      "Budget",
      "Approved Contract",
      "Forecast Variations",
      "Approved Variations",
      "Forecast Final Cost",
      "Budget Variance",
      "Claimed to Date",
      "This Month",
      "Remaining",
    ],
    ...GREENBANK_COST_ITEMS.map(([category, item], index) => [
      String(index + 1),
      category,
      item,
      ...Array.from({ length: 9 }, () => ""),
    ]),
  ];
  const registerSheet = (name: "Invoices" | "Variations", title: string) => {
    const headers =
      name === "Invoices"
        ? [
            "Invoice Date",
            "Company",
            "PO Number",
            "Invoice Number",
            "Invoice Description",
            "Cost Item",
            "Amount",
            "Billing Month",
            "Paid?",
          ]
        : [
            "Date Submitted",
            "Cost Item",
            "Variation To",
            "Status",
            "Amount",
            "Date Approved",
            "Approved Amount",
          ];
    const rows = [
      [title, ...Array.from({ length: headers.length - 1 }, () => "")],
      ["Greenbank", ...Array.from({ length: headers.length - 1 }, () => "")],
      Array.from({ length: headers.length }, () => ""),
      headers,
    ];
    return {
      name,
      column_count: headers.length,
      rows,
      styles: rows.map((row) => row.map(() => blankStyle)),
    };
  };

  return {
    filename: "Cost_Plan_v01.draft.xlsx",
    workspace_path: "04-projects/greenbank/01-cost/Cost_Plan_v01.draft.xlsx",
    warnings: [],
    sheets: [
      {
        name: "Summary",
        column_count: 12,
        rows: summaryRows,
        styles: summaryRows.map((row) => row.map(() => blankStyle)),
      },
      registerSheet("Invoices", "INVOICES REGISTER"),
      registerSheet("Variations", "VARIATIONS REGISTER"),
    ],
  };
}
