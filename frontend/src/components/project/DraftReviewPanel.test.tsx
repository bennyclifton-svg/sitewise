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
    patchDraft: vi.fn(),
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
  ])("offers AI and block actions without a pen icon for %s drafts", (workflowType, title) => {
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

    fireEvent.mouseEnter(screen.getByText("Current scope."));

    const headingRow = screen.getByRole("heading", { name: "Scope", level: 2 }).parentElement;
    expect(screen.queryByRole("button", { name: "Edit paragraph manually" })).not.toBeInTheDocument();
    const aiAction = screen.getByRole("button", { name: "Edit paragraph with AI" });
    expect(headingRow).toContainElement(aiAction);
    expect(screen.queryByRole("button", { name: /edit source/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit markdown/i })).not.toBeInTheDocument();

    fireEvent.click(aiAction);
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

  it("double-clicks into one formatted paragraph and leaves the other section unchanged", async () => {
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

    fireEvent.doubleClick(screen.getByText("Alpha"));
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    expect(editor).toHaveTextContent("Alpha");
    expect(editor).not.toHaveTextContent("## First");
    editor.textContent = "Gamma";
    fireEvent.input(editor);
    fireEvent.blur(editor);

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

  it("double-clicks a table cell in place and persists via patchDraft", async () => {
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
    vi.mocked(api.patchDraft).mockResolvedValue(updated);
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
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
    });
    expect(api.patchDraft).toHaveBeenCalledWith(
      PROJECT_ID,
      "draft-1",
      expect.stringContaining("| Budget | Partial |"),
      1,
    );
    expect(api.applyDraftBlockOperations).not.toHaveBeenCalled();
  });

  describe("anchored instructions", () => {
    const ANCHORED_MARKDOWN =
      "# Title\n\n## First\n\nAlpha paragraph.\n\nSecond paragraph.\n\n## Second\n\nBeta\n";

    async function queueOneInstruction(user: ReturnType<typeof userEvent.setup>) {
      fireEvent.mouseEnter(screen.getByText("Alpha paragraph."));
      fireEvent.click(screen.getByRole("button", { name: "Edit paragraph with AI" }));
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
      expect(screen.getByText("tighten this")).toBeInTheDocument();
      // The section badge comes from the anchor's offset, not the DOM.
      expect(screen.getAllByText("First").length).toBeGreaterThan(0);
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
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
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
      expect(screen.getByText("tighten this")).toBeInTheDocument();
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

      fireEvent.mouseEnter(screen.getByText("Follow up."));
      fireEvent.click(screen.getByRole("button", { name: "Edit paragraph with AI" }));
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
