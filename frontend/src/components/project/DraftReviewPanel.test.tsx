import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { DraftArtifact, WorkbookPreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    acceptDraft: vi.fn(),
    applyDraftInstructions: vi.fn(),
    downloadWorkspaceFile: vi.fn(),
    getCostPlanState: vi.fn(),
    getWorkbookPreview: vi.fn(),
    getProjectDraft: vi.fn(),
    getLatestDraft: vi.fn(),
    listDecisions: vi.fn(),
    applyDraftBlockOperations: vi.fn(),
    applyCostPlanOperations: vi.fn(),
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

function blockOpsResponse(updated: DraftArtifact, changedBlockIds: string[] = []) {
  return {
    delta: {
      draft_id: updated.id,
      version: updated.version,
      updated_at: updated.updated_at,
      changed_block_ids: changedBlockIds,
      deleted_block_ids: [] as string[],
      blocks:
        (updated.provenance_metadata?.blocks as Record<string, unknown> | undefined) ??
        {},
      content_sha256: "c".repeat(64),
      generation_manifest_present: false,
    },
    changed_block_ids: changedBlockIds,
  };
}

describe("DraftReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The tray persists per draft+version by design, so it must be reset
    // between tests that reuse draft-1 v1.
    window.sessionStorage.clear();
    window.getSelection()?.removeAllRanges();
    vi.mocked(api.listDecisions).mockResolvedValue({
      decisions: [],
      set_revision: 1,
    });
    // Block saves re-fetch the authoritative draft; default to no body so
    // mutation-only tests still exercise the lean delta fallback.
    vi.mocked(api.getLatestDraft).mockResolvedValue(null);
    vi.mocked(api.getCostPlanState).mockResolvedValue({
      version: 1,
      items: [],
      totals: {
        budget: "0.00",
        committed: "0.00",
        forecast: "0.00",
        paid: "0.00",
        variance: "0.00",
        total_excluding_gst: "0.00",
        total_including_gst: "0.00",
      },
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  /** PMP drafts fetch decisions before leaving read-only; wait so remounts settle. */
  async function waitForPmpDecisions() {
    await waitFor(() => expect(api.listDecisions).toHaveBeenCalled());
    const pending = vi.mocked(api.listDecisions).mock.results.at(-1)?.value;
    if (pending) await pending;
    await waitFor(() => {
      expect(vi.mocked(api.listDecisions).mock.settledResults.at(-1)?.type).toBe(
        "fulfilled",
      );
    });
  }

  it("exposes exclusions, constraints and version tokens in Sources & Context", () => {
    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          provenance_metadata: {
            generation_manifest: {
              input_fingerprint: "a".repeat(64),
              context_version: 7,
              source_version: "srcsrcsrcsrcsrcs",
              seed_version: "seedseedseedseed",
              taxonomy: { building_class: "commercial" },
              known_profile: { "identity.title": "Demo" },
              unknown_relevant_fields: ["scale.gfa"],
              explicitly_excluded_fields: ["scope.ffe"],
              constraints: ["Keep PC allowances separate"],
              evidence_used: ["brief.pdf"],
              seed_knowledge: ["seed/pmp.md"],
            },
          },
        })}
        onDraftUpdated={vi.fn()}
      />,
    );

    const panel = screen.getByLabelText("Sources and context");
    expect(panel).toHaveTextContent("Excluded fields");
    expect(panel).toHaveTextContent("scope.ffe");
    expect(panel).toHaveTextContent("Constraints");
    expect(panel).toHaveTextContent("Keep PC allowances separate");
    expect(panel).toHaveTextContent("Context version");
    expect(panel).toHaveTextContent("7");
    expect(panel).toHaveTextContent("Source version");
    expect(panel).toHaveTextContent("srcsrcsrcsrc");
    expect(panel).toHaveTextContent("Seed version");
    expect(panel).toHaveTextContent("seedseedseed");
  });

  it("uses the document title and keeps export actions out of the reviewer", () => {
    const { container } = render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          content_markdown: `# Project Management Plan

## Snapshot

Issued content. [1]

## Trace & QA

**Inputs to resolve**
- Tender close date`,
        })}
        onDraftUpdated={vi.fn()}
      />,
    );

    const sheet = container.querySelector(".artifact-sheet");
    expect(sheet).not.toHaveTextContent("Tender close date");
    expect(screen.getByTestId("draft-supporting-details")).toHaveTextContent(
      "Tender close date",
    );
    expect(
      screen.getByRole("heading", { name: "Project Management Plan", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Issue document")).not.toBeInTheDocument();
    expect(screen.queryByText(/stays in the web review/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Copy for Word" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Word" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "PDF" })).not.toBeInTheDocument();
  });

  it.each([
    ["create_pmp", "Project Management Plan"],
    ["consultant_procurement_structural_engineer", "Request for Tender - Structural Engineer"],
    ["trade_rft_electrical_services", "Request for Tender - Electrical Services"],
    ["trade_rfq_joinery", "Request for Tender - Joinery"],
  ])("collapses supporting details for %s drafts by default", async (workflowType, title) => {
    const user = userEvent.setup();
    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          workflow_type: workflowType,
          title,
          provenance_metadata: {
            seed_consulted: ["data/seed/setup-and-commission-guide.md"],
            evidence_refs: ["04-projects/demo/brief.pdf"],
            context_refs: ["project-profile"],
          },
        })}
        onDraftUpdated={vi.fn()}
      />,
    );

    const details = screen.getByTestId("draft-supporting-details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent("Trace & QA");

    const summary = details.querySelector("summary");
    expect(summary).not.toBeNull();
    await user.click(summary!);

    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Seed consulted")).toBeVisible();
    expect(screen.getByText("Evidence refs")).toBeVisible();
    expect(screen.getByText("Context refs")).toBeVisible();
    expect(screen.queryByRole("button", { name: /accept/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit markdown/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /refresh pmp from documents/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reopen/i })).not.toBeInTheDocument();
  });

  it("opens the collapsed trace from the refresh provenance strip", async () => {
    const user = userEvent.setup();
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
      />,
    );

    const details = screen.getByTestId("draft-supporting-details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent("What changed in v3");
    expect(details).toHaveTextContent("Scope & client requirements");
    expect(details).toHaveTextContent("Evidence changes:");

    const mainSheet = document.querySelector(".artifact-sheet");
    expect(mainSheet).not.toHaveTextContent("What changed in v3");

    await user.click(screen.getByRole("button", { name: "View sweep trace" }));

    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Swept evidence batch 1 of 1.")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /refresh pmp from documents/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit markdown/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /accept pmp/i })).not.toBeInTheDocument();
  });

  it.each([
    ["create_pmp", "Project Management Plan"],
    ["consultant_procurement_structural_engineer", "Request for Tender - Structural Engineer"],
    ["trade_rft_electrical_services", "Request for Tender - Electrical Services"],
  ])("offers AI and block actions without a pen icon for %s drafts", async (workflowType, title) => {
    const user = userEvent.setup();
    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          workflow_type: workflowType,
          title,
          content_markdown: `# ${title}\n\n## Scope\n\nCurrent scope.`,
        })}
        onDraftUpdated={vi.fn()}
      />,
    );

    if (workflowType === "create_pmp") {
      await waitForPmpDecisions();
    }

    fireEvent.mouseEnter(
      screen.getByText("Current scope.").parentElement ??
        screen.getByText("Current scope."),
    );

    expect(screen.queryByRole("button", { name: "Edit paragraph manually" })).not.toBeInTheDocument();
    const menuTrigger = screen.getByRole("button", { name: "paragraph actions" });
    expect(
      screen.getByText("Current scope.").parentElement,
    ).toContainElement(menuTrigger);
    expect(screen.queryByRole("button", { name: "Add paragraph above" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit source/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit markdown/i })).not.toBeInTheDocument();

    await user.click(menuTrigger);
    expect(
      await screen.findByRole("menuitem", { name: "Add paragraph above" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Add paragraph below" })).toBeInTheDocument();
    await user.click(
      screen.getByRole("menuitem", { name: "Edit paragraph with AI" }),
    );
    expect(screen.getByLabelText("Instruction")).toBeInTheDocument();
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

  it("keeps a newer inline edit when the parent later passes an older summary", async () => {
    const original = draft({
      content_markdown: "# Title\n\n## First\n\nAlpha\n\n## Second\n\nBeta\n",
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## First\n\nGamma\n\n## Second\n\nBeta\n",
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(updated, ["blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]),
    );
    vi.mocked(api.getLatestDraft).mockResolvedValue(updated);
    // If the panel refetched the older summary id, it would restore Alpha.
    vi.mocked(api.getProjectDraft).mockResolvedValue(original);

    const view = render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={vi.fn()}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Alpha"));
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    editor.textContent = "Gamma";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    await waitFor(() => {
      expect(screen.getByText("Gamma")).toBeInTheDocument();
    });

    view.rerender(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={{
          id: "draft-1",
          project_id: PROJECT_ID,
          workflow_type: "create_pmp",
          version: 1,
          status: "draft",
          title: "Project Management Plan",
          workspace_path: original.workspace_path,
          author_user_id: "user-1",
          model: "gpt-5.6-luna",
          runtime: "clerk-sitewise-create-pmp",
          created_at: "2026-07-04T12:00:00.000Z",
          updated_at: "2026-07-04T12:00:00.000Z",
        }}
        onDraftUpdated={vi.fn()}
      />,
    );

    expect(screen.getByText("Gamma")).toBeInTheDocument();
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    expect(api.getProjectDraft).not.toHaveBeenCalled();
  });

  it("keeps a confirmed edit when a same-version poll returns older markdown", async () => {
    const original = draft({
      content_markdown: "# Title\n\n## Scope\n\nAlpha paragraph.\n",
    });
    const persisted = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## Scope\n\nGamma paragraph.\n",
    });
    // Event-poll race: same revision identity, body missing the local edit.
    const polledMissingEdit = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## Scope\n\nAlpha paragraph.\n",
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(persisted, ["blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]),
    );
    vi.mocked(api.getLatestDraft).mockResolvedValue(persisted);

    const view = render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={vi.fn()}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Alpha paragraph."));
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    editor.textContent = "Gamma paragraph.";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    await waitFor(() => {
      expect(screen.getByText("Gamma paragraph.")).toBeInTheDocument();
    });

    view.rerender(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={polledMissingEdit}
        onDraftUpdated={vi.fn()}
      />,
    );

    expect(screen.getByText("Gamma paragraph.")).toBeInTheDocument();
    expect(screen.queryByText("Alpha paragraph.")).not.toBeInTheDocument();
  });

  it("surfaces block-save failures above the draft, not inside Trace & QA", async () => {
    const original = draft({
      content_markdown: "# Title\n\n## First\n\nAlpha\n",
    });
    vi.mocked(api.applyDraftBlockOperations).mockRejectedValue(
      new ApiError("Draft revise failed", 500, {}),
    );

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={vi.fn()}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Alpha"));
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    editor.textContent = "Gamma";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Draft revise failed|Could not save/i);
    expect(alert.closest("details")).toBeNull();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
  });

  it("double-clicks into one formatted paragraph and persists via block UPDATE", async () => {
    const original = draft({
      content_markdown: "# Title\n\n## First\n\nAlpha\n\n## Second\n\nBeta\n",
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## First\n\nGamma\n\n## Second\n\nBeta\n",
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(updated, ["blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]),
    );
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Alpha"));
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    expect(editor).toHaveTextContent("Alpha");
    expect(editor).not.toHaveTextContent("## First");
    editor.textContent = "Gamma";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(expect.objectContaining({ id: updated.id, version: updated.version, content_markdown: updated.content_markdown }));
    });
    expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
      PROJECT_ID,
      "draft-1",
      1,
      [
        expect.objectContaining({
          operation: "UPDATE",
          content: "Gamma",
          target: expect.objectContaining({ type: "paragraph" }),
        }),
      ],
    );
  });

  it("double-clicks a table cell in place and persists via block UPDATE", async () => {
    const original = draft({
      content_markdown: `## Snapshot

| Field | Status |
| --- | --- |
| Budget | Grounded |
`,
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: `## Snapshot

| Field | Status |
| --- | --- |
| Budget | Partial |
`,
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(updated, ["blk_cccccccccccccccccccccccccccccccc"]),
    );
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Grounded"));
    const cells = screen.getAllByRole("textbox", { name: /Edit table cell/i });
    expect(cells[1]).toHaveFocus();
    expect(cells[1]).toHaveTextContent("Grounded");
    cells[1].textContent = "Partial";
    fireEvent.input(cells[1]);
    fireEvent.blur(cells[1]);

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(expect.objectContaining({ id: updated.id, version: updated.version, content_markdown: updated.content_markdown }));
    });
    expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
      PROJECT_ID,
      "draft-1",
      1,
      [
        expect.objectContaining({
          operation: "UPDATE",
          content: expect.stringContaining("| Budget | Partial |"),
          target: expect.objectContaining({ type: "table_row" }),
        }),
      ],
    );
  });

  it.each([
    ["create_pmp", "Project Management Plan"],
    ["consultant_procurement_structural_engineer", "Request for Tender - Structural Engineer"],
    ["trade_rft_electrical_services", "Request for Tender - Electrical Services"],
  ] as const)(
    "duplicates and deletes a list item via block ops for %s",
    async (workflowType, title) => {
      const marker = "<!-- clerk:block id=blk_dddddddddddddddddddddddddddddddd -->";
      const original = draft({
        workflow_type: workflowType,
        title,
        content_markdown: `## Scope\n\n- First item ${marker}\n- Second item\n`,
        provenance_metadata: {
          blocks: {
            blk_dddddddddddddddddddddddddddddddd: {
              id: "blk_dddddddddddddddddddddddddddddddd",
              type: "list_item",
              user_protected: false,
            },
          },
        },
      });
      const duplicated = draft({
        id: "draft-2",
        version: 2,
        workflow_type: workflowType,
        title,
        content_markdown: `## Scope\n\n- First item ${marker}\n- First item\n- Second item\n`,
      });
      vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(duplicated, ["blk_eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"]),
    );
      const onDraftUpdated = vi.fn();

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={original}
          onDraftUpdated={onDraftUpdated}
        />,
      );

      const user = userEvent.setup();
      if (workflowType === "create_pmp") {
        await waitForPmpDecisions();
      }
      fireEvent.mouseEnter(
        screen.getByText(/First item/).closest("li") ?? screen.getByText(/First item/),
      );
      await user.click(screen.getByRole("button", { name: "list item actions" }));
      expect(
        await screen.findByRole("menuitem", { name: "Add list item above" }),
      ).toBeInTheDocument();
      expect(screen.getByRole("menuitem", { name: "Add list item below" })).toBeInTheDocument();
      await user.click(
        screen.getByRole("menuitem", { name: "Duplicate list item" }),
      );

      await waitFor(() => {
        expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
          PROJECT_ID,
          "draft-1",
          1,
          [
            expect.objectContaining({
              operation: "DUPLICATE",
              target: expect.objectContaining({
                id: "blk_dddddddddddddddddddddddddddddddd",
                type: "list_item",
              }),
            }),
          ],
        );
      });
      expect(onDraftUpdated).toHaveBeenCalledWith(expect.objectContaining({ id: duplicated.id, version: duplicated.version }));
    },
  );

  it.each([
    ["create_pmp", "Project Management Plan"],
    ["consultant_procurement_structural_engineer", "Request for Tender - Structural Engineer"],
    ["trade_rft_electrical_services", "Request for Tender - Electrical Services"],
  ] as const)(
    "deletes a list item via block ops for %s",
    async (workflowType, title) => {
      const marker = "<!-- clerk:block id=blk_dddddddddddddddddddddddddddddddd -->";
      const original = draft({
        workflow_type: workflowType,
        title,
        content_markdown: `## Scope\n\n- First item ${marker}\n- Second item\n`,
      });
      const deleted = draft({
        id: "draft-2",
        version: 2,
        workflow_type: workflowType,
        title,
        content_markdown: "## Scope\n\n- Second item\n",
      });
      vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(deleted, ["blk_dddddddddddddddddddddddddddddddd"]),
    );

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={original}
          onDraftUpdated={vi.fn()}
        />,
      );

      const user = userEvent.setup();
      if (workflowType === "create_pmp") {
        await waitForPmpDecisions();
      }
      fireEvent.mouseEnter(
        screen.getByText(/First item/).closest("li") ?? screen.getByText(/First item/),
      );
      await user.click(screen.getByRole("button", { name: "list item actions" }));
      await user.click(
        await screen.findByRole("menuitem", { name: "Delete list item" }),
      );
      await waitFor(() => {
        expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
          PROJECT_ID,
          "draft-1",
          1,
          [
            expect.objectContaining({
              operation: "DELETE",
              target: expect.objectContaining({
                id: "blk_dddddddddddddddddddddddddddddddd",
                type: "list_item",
              }),
            }),
          ],
        );
      });
    },
  );

  it("keeps a conflicted block through a versioned KEEP operation", async () => {
    const marker = "<!-- clerk:block id=blk_cccccccccccccccccccccccccccccccc -->";
    const original = draft({
      content_markdown: `## Facts\n\n${marker}\nUser wording survives.\n`,
      provenance_metadata: {
        blocks: {
          blk_cccccccccccccccccccccccccccccccc: {
            id: "blk_cccccccccccccccccccccccccccccccc",
            type: "paragraph",
            status: "conflict",
          },
        },
        incremental_update: {
          conflicts: ["blk_cccccccccccccccccccccccccccccccc"],
          proposed_delete: [],
        },
      },
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: original.content_markdown,
      provenance_metadata: {
        blocks: {
          blk_cccccccccccccccccccccccccccccccc: {
            id: "blk_cccccccccccccccccccccccccccccccc",
            type: "paragraph",
            status: "active",
          },
        },
      },
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(updated, ["blk_cccccccccccccccccccccccccccccccc"]),
    );

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await waitForPmpDecisions();
    expect(screen.getByRole("status")).toHaveTextContent("1 conflict");
    fireEvent.mouseEnter(
      screen.getByText("User wording survives.").parentElement ??
        screen.getByText("User wording survives."),
    );
    await user.click(screen.getByRole("button", { name: "paragraph actions" }));
    await user.click(
      await screen.findByRole("menuitem", {
        name: "Keep paragraph after refresh conflict",
      }),
    );

    await waitFor(() => {
      expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
        PROJECT_ID,
        "draft-1",
        1,
        [
          expect.objectContaining({
            operation: "KEEP",
            target: expect.objectContaining({
              id: "blk_cccccccccccccccccccccccccccccccc",
              type: "paragraph",
            }),
          }),
        ],
      );
    });
  });

  it("protects a paragraph block through a versioned PROTECT operation", async () => {
    const marker = "<!-- clerk:block id=blk_ffffffffffffffffffffffffffffffff -->";
    const original = draft({
      content_markdown: `## Facts\n\n${marker}\nProtected fact.\n`,
      provenance_metadata: {
        blocks: {
          blk_ffffffffffffffffffffffffffffffff: {
            id: "blk_ffffffffffffffffffffffffffffffff",
            type: "paragraph",
            user_protected: false,
          },
        },
      },
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: original.content_markdown,
      provenance_metadata: {
        blocks: {
          blk_ffffffffffffffffffffffffffffffff: {
            id: "blk_ffffffffffffffffffffffffffffffff",
            type: "paragraph",
            user_protected: true,
          },
        },
      },
    });
    vi.mocked(api.applyDraftBlockOperations).mockResolvedValue(
      blockOpsResponse(updated, ["blk_ffffffffffffffffffffffffffffffff"]),
    );

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await waitForPmpDecisions();
    fireEvent.mouseEnter(
      screen.getByText("Protected fact.").parentElement ??
        screen.getByText("Protected fact."),
    );
    await user.click(screen.getByRole("button", { name: "paragraph actions" }));
    await user.click(
      await screen.findByRole("menuitem", { name: "Protect paragraph" }),
    );

    await waitFor(() => {
      expect(api.applyDraftBlockOperations).toHaveBeenCalledWith(
        PROJECT_ID,
        "draft-1",
        1,
        [
          expect.objectContaining({
            operation: "PROTECT",
            target: expect.objectContaining({
              id: "blk_ffffffffffffffffffffffffffffffff",
              type: "paragraph",
            }),
          }),
        ],
      );
    });
  });

  describe("anchored instructions", () => {
    const ANCHORED_MARKDOWN =
      "# Title\n\n## First\n\nAlpha paragraph.\n\nSecond paragraph.\n\n## Second\n\nBeta\n";

    async function queueOneInstruction(user: ReturnType<typeof userEvent.setup>) {
      await waitForPmpDecisions();
      fireEvent.mouseEnter(screen.getByText("Alpha paragraph."));
      await user.click(screen.getByRole("button", { name: "paragraph actions" }));
      await user.click(
        await screen.findByRole("menuitem", { name: "Edit paragraph with AI" }),
      );
      const instruction = await screen.findByLabelText("Instruction");
      await user.type(instruction, "tighten this");
      await user.click(screen.getByRole("button", { name: "Add to tray" }));
    }

    it("opens the card from the AI diamond and queues the instruction in the tray", async () => {
      const user = userEvent.setup();
      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );

      expect(screen.queryByLabelText("Instruction")).not.toBeInTheDocument();
      await queueOneInstruction(user);

      expect(screen.getByRole("button", { name: /Apply 1 change/ })).toBeInTheDocument();
      expect(screen.getByText(/tighten this/)).toBeInTheDocument();
      // The section label comes from the anchor's offset, not the DOM.
      expect(screen.getAllByText("First").length).toBeGreaterThan(0);
      // Quoted source text stays off the card and tray; only the instruction shows.
      expect(
        screen.queryByRole("dialog", { name: "Add an instruction for the selected text" }),
      ).not.toBeInTheDocument();
    });

    it("portals the tray into the cockpit right-panel host when present", async () => {
      const user = userEvent.setup();
      const host = document.createElement("div");
      host.setAttribute("data-instruction-tray-host", "");
      document.body.appendChild(host);

      try {
        render(
          <DraftReviewPanel
            projectId={PROJECT_ID}
            draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
            onDraftUpdated={vi.fn()}
          />,
        );
        await queueOneInstruction(user);

        expect(host.querySelector("[data-instruction-ui]")).not.toBeNull();
        expect(host).toHaveTextContent(/tighten this/);
        expect(host).not.toHaveTextContent("Alpha paragraph.");
      } finally {
        host.remove();
      }
    });

    it("applies with the exact source anchors and the current version", async () => {
      const user = userEvent.setup();
      const updated = draft({ version: 2, content_markdown: ANCHORED_MARKDOWN });
      vi.mocked(api.applyDraftInstructions).mockResolvedValue({
        draft: updated,
        applied_count: 1,
        failed: [],
      });
      const onDraftUpdated = vi.fn();

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={onDraftUpdated}
        />,
      );
      await queueOneInstruction(user);
      await user.click(screen.getByRole("button", { name: /Apply 1 change/ }));

      const start = ANCHORED_MARKDOWN.indexOf("Alpha paragraph.");
      await waitFor(() => {
        expect(api.applyDraftInstructions).toHaveBeenCalledWith(PROJECT_ID, "draft-1", 1, [
          {
            anchor_start: start,
            anchor_end: start + "Alpha paragraph.".length,
            quoted_text: "Alpha paragraph.",
            instruction: "tighten this",
          },
        ]);
      });
      expect(onDraftUpdated).toHaveBeenCalledWith(expect.objectContaining({ id: updated.id, version: updated.version, content_markdown: updated.content_markdown }));
      // Everything applied, so nothing is left queued.
      expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
    });

    it("tints only the blocks covered by changed_ranges", () => {
      const changedStart = ANCHORED_MARKDOWN.indexOf("Second paragraph.");
      const { container } = render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({
            version: 2,
            content_markdown: ANCHORED_MARKDOWN,
            provenance_metadata: {
              sections_changed: ["First"],
              changed_ranges: [
                { start: changedStart, end: changedStart + "Second paragraph.".length },
              ],
            },
          })}
          onDraftUpdated={vi.fn()}
        />,
      );

      const changed = container.querySelectorAll("[data-md-changed]");
      expect(changed).toHaveLength(1);
      expect(changed[0]).toHaveTextContent("Second paragraph.");
      expect(screen.getByText("Alpha paragraph.")).not.toHaveAttribute("data-md-changed");
    });

    it("the Hide changes toggle removes every tint and restores it", async () => {
      const user = userEvent.setup();
      const changedStart = ANCHORED_MARKDOWN.indexOf("Second paragraph.");
      const { container } = render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({
            version: 2,
            content_markdown: ANCHORED_MARKDOWN,
            provenance_metadata: {
              sections_changed: ["First"],
              changed_ranges: [
                { start: changedStart, end: changedStart + "Second paragraph.".length },
              ],
            },
          })}
          onDraftUpdated={vi.fn()}
        />,
      );

      expect(container.querySelectorAll("[data-md-changed]")).toHaveLength(1);

      await user.click(screen.getByRole("button", { name: "Hide changes" }));
      expect(container.querySelectorAll("[data-md-changed]")).toHaveLength(0);

      await user.click(screen.getByRole("button", { name: "Show changes" }));
      expect(container.querySelectorAll("[data-md-changed]")).toHaveLength(1);
    });

    it("offers no changes toggle when the version carries no changed_ranges", () => {
      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({
            version: 2,
            content_markdown: ANCHORED_MARKDOWN,
            provenance_metadata: { sections_changed: ["First"] },
          })}
          onDraftUpdated={vi.fn()}
        />,
      );

      expect(screen.queryByRole("button", { name: /changes/i })).not.toBeInTheDocument();
    });

    it("keeps the tray and shows the rebase message on a 409", async () => {
      const user = userEvent.setup();
      vi.mocked(api.applyDraftInstructions).mockRejectedValue(
        new ApiError("Expected create_pmp v1, current version is v4", {
          kind: "http",
          status: 409,
        }),
      );

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );
      await queueOneInstruction(user);
      await user.click(screen.getByRole("button", { name: /Apply 1 change/ }));

      const message = await screen.findByText(
        "Draft moved to v4 — review the current text and re-apply.",
      );
      expect(message).toBeInTheDocument();
      // It must land in the tray, not in the collapsed Trace & QA section,
      // or the user watches a long apply end in silence.
      expect(message.closest("[data-instruction-ui]")).not.toBeNull();
      expect(screen.getByTestId("draft-supporting-details")).not.toContainElement(message);
      expect(screen.getByRole("button", { name: /Apply 1 change/ })).toBeInTheDocument();
      expect(screen.getByText(/tighten this/)).toBeInTheDocument();
    });

    it("surfaces a 422 all-failed reason in the tray", async () => {
      const user = userEvent.setup();
      vi.mocked(api.applyDraftInstructions).mockRejectedValue(
        new ApiError("0: Draft instruction slice validation failed: heading line was modified", {
          kind: "http",
          status: 422,
        }),
      );

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );
      await queueOneInstruction(user);
      await user.click(screen.getByRole("button", { name: /Apply 1 change/ }));

      const message = await screen.findByText(/heading line was modified/);
      expect(message.closest("[data-instruction-ui]")).not.toBeNull();
    });

    it("re-seeds failed instructions into the tray with their reason", async () => {
      const user = userEvent.setup();
      vi.mocked(api.applyDraftInstructions).mockResolvedValue({
        draft: draft({ version: 2, content_markdown: ANCHORED_MARKDOWN }),
        applied_count: 0,
        failed: [{ index: 0, reason: "heading line was modified" }],
      });

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );
      await queueOneInstruction(user);
      await user.click(screen.getByRole("button", { name: /Apply 1 change/ }));

      expect(await screen.findByText("heading line was modified")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Apply 1 change/ })).toBeInTheDocument();
    });

    it("renders no paragraph editing affordance on an accepted draft", () => {
      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ status: "accepted", content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );

      const paragraph = screen.getByText("Alpha paragraph.");
      fireEvent.mouseEnter(paragraph);
      fireEvent.doubleClick(paragraph);

      expect(screen.queryByRole("button", { name: /Edit paragraph/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: "Edit selected text" })).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Instruction")).not.toBeInTheDocument();
    });

    it("renders no paragraph editing affordance for a tender comparison report", () => {
      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({
            workflow_type: "tender_report",
            content_markdown: ANCHORED_MARKDOWN,
          })}
          onDraftUpdated={vi.fn()}
        />,
      );

      const paragraph = screen.getByText("Alpha paragraph.");
      fireEvent.mouseEnter(paragraph);
      fireEvent.doubleClick(paragraph);

      expect(screen.queryByRole("button", { name: /Edit paragraph/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: "Edit selected text" })).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Instruction")).not.toBeInTheDocument();
    });

    it("keeps drag selection native without opening the AI pathway", () => {
      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: ANCHORED_MARKDOWN })}
          onDraftUpdated={vi.fn()}
        />,
      );

      // Endpoints must land *inside* the blocks: the resolver walks up from the
      // selection's nodes to find their [data-md-start] ancestors.
      const range = document.createRange();
      range.setStart(screen.getByText("Alpha paragraph.").firstChild!, 0);
      range.setEnd(screen.getByText("Beta").firstChild!, 4);
      const selection = window.getSelection()!;
      selection.removeAllRanges();
      selection.addRange(range);
      fireEvent.mouseUp(document);

      expect(screen.queryByLabelText("Instruction")).not.toBeInTheDocument();
      expect(selection.toString()).toContain("Alpha paragraph.");
      expect(selection.toString()).toContain("Beta");
    });

    it("anchors against the normalized markdown, not the stored '- |' artefact", async () => {
      const user = userEvent.setup();
      const raw = "# Title\n\n## First\n\n- | Section | Status |\n- | --- | --- |\n\nFollow up.\n";
      const normalized = "# Title\n\n## First\n\n| Section | Status |\n| --- | --- |\n\nFollow up.\n";
      vi.mocked(api.applyDraftInstructions).mockResolvedValue({
        draft: draft({ version: 2, content_markdown: raw }),
        applied_count: 1,
        failed: [],
      });

      render(
        <DraftReviewPanel
          projectId={PROJECT_ID}
          draft={draft({ content_markdown: raw })}
          onDraftUpdated={vi.fn()}
        />,
      );

      await waitForPmpDecisions();
      fireEvent.mouseEnter(screen.getByText("Follow up."));
      await user.click(screen.getByRole("button", { name: "paragraph actions" }));
      await user.click(
        await screen.findByRole("menuitem", { name: "Edit paragraph with AI" }),
      );
      const instruction = await screen.findByLabelText("Instruction");
      await user.type(instruction, "add a Ref column");
      await user.click(screen.getByRole("button", { name: "Add to tray" }));
      await user.click(screen.getByRole("button", { name: /Apply 1 change/ }));

      await waitFor(() => {
        expect(api.applyDraftInstructions).toHaveBeenCalled();
      });
      const [, , , sent] = vi.mocked(api.applyDraftInstructions).mock.calls[0]!;
      const anchored = normalized.slice(sent[0]!.anchor_start, sent[0]!.anchor_end);
      expect(anchored).toBe(sent[0]!.quoted_text);
      expect(anchored).toBe("Follow up.");
    });
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
            seed_consulted: ["data/seed/cost-planning.md"],
            evidence_refs: ["04-projects/greenbank/brief.pdf"],
            context_refs: ["project-profile"],
            trace: [
              {
                step: "cost_plan_complete",
                status: "complete",
                message: "Cost plan workbook generated.",
                metadata: {},
              },
            ],
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

    expect(screen.queryByRole("heading", { name: "Cost workbook" })).not.toBeInTheDocument();
    expect(screen.queryByText("Cost_Plan_v01.draft.xlsx")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Download Excel" })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Cost Plan" })).toBeInTheDocument();
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

    const details = screen.getByTestId("draft-supporting-details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent("Trace & QA");
    expect(screen.getByText("Seed consulted")).not.toBeVisible();

    await user.click(details.querySelector("summary")!);
    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Seed consulted")).toBeVisible();
    expect(screen.getByText("Evidence refs")).toBeVisible();
    expect(screen.getByText("Context refs")).toBeVisible();
    expect(screen.getByText("Cost plan workbook generated.")).toBeVisible();

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
