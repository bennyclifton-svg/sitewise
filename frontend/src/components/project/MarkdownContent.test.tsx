import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { MarkdownContent } from "@/components/project/MarkdownContent";

vi.mock("@/components/project/DecisionControl", async () => {
  const actual = await vi.importActual<
    typeof import("@/components/project/DecisionControl")
  >("@/components/project/DecisionControl");
  return {
    ...actual,
    DecisionControl: ({
      decision,
    }: {
      decision: {
        label: string;
        selected: string;
        revision?: number;
        set_revision?: number;
      };
    }) => (
      <div
        data-testid="decision-control"
        data-selected={decision.selected}
        data-revision={decision.revision}
        data-set-revision={decision.set_revision}
      >
        {decision.label}
      </div>
    ),
    DecisionSchedule: ({
      decisions,
    }: {
      decisions: Array<{ label: string }>;
    }) => (
      <div data-testid="decision-schedule">
        {decisions.map((decision) => (
          <div key={decision.label} data-testid="decision-control">
            {decision.label}
          </div>
        ))}
      </div>
    ),
  };
});

const MARKDOWN = `# Project Management Plan

## Snapshot

| Item | Status |
| --- | --- |
| Budget | Grounded |

## Actions

Follow up.

\`\`\`pmp-decision
{"id":"procurement-route","label":"Procurement route","options":[{"value":"traditional","label":"Traditional"}],"selected":"traditional"}
\`\`\`
`;
describe("MarkdownContent", () => {
  it("renders decision widgets and evidence chips", () => {
    render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" version={2} />,
    );
    expect(screen.getByTestId("decision-control")).toHaveTextContent("Procurement route");
    expect(screen.getByText("Grounded")).toBeInTheDocument();
    expect(screen.getByText("Sections")).toBeInTheDocument();
  });

  it("renders provenance-stamped PMP summary rows as a table without exposing markers", () => {
    const stamped = `## Project Summary

| Project | Walsh 2 |
| --- | --- |
| Address | 42 Hargrave Street, Paddington NSW 2021 |<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->
| Owner | David and Emma Walsh |<!-- clerk:block id=blk_9a7b77fe4970e4836f3c148540452ecf -->`;

    const { container } = render(<MarkdownContent markdown={stamped} />);

    const table = container.querySelector("table");
    expect(table).not.toBeNull();
    expect(table?.querySelectorAll("tr")).toHaveLength(3);
    expect(table?.querySelectorAll("th, td")).toHaveLength(6);
    expect(container).not.toHaveTextContent("clerk:block");
    expect(screen.getByText("Walsh 2")).toBeInTheDocument();
  });

  it("keeps stamped table-row edit ranges in canonical Markdown offsets", () => {
    const onEditSelection = vi.fn();
    const addressRow =
      "| Address | Paddington |<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->";
    const stamped = `## Project Summary

| Field | Value |
| --- | --- |
${addressRow}`;
    render(
      <MarkdownContent
        markdown={stamped}
        onEditSelection={onEditSelection}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Paddington"));

    const start = stamped.indexOf(addressRow);
    expect(onEditSelection).toHaveBeenCalledWith(
      {
        start,
        end: start + addressRow.length,
      },
      { focusCellIndex: 1 },
    );
  });

  it("hides paragraph and list markers in primary and review content", () => {
    const stamped = `## Scope

<!-- clerk:block id=blk_ae7e9c02710fe52df14282380c2979db -->
Coordinate the issued design.

- Confirm the tender programme. <!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->

## Trace & QA

<!-- clerk:block id=blk_9a7b77fe4970e4836f3c148540452ecf -->
Review note.`;

    const { container } = render(<MarkdownContent markdown={stamped} />);

    expect(screen.getByText("Coordinate the issued design.")).toBeInTheDocument();
    expect(screen.getByText("Confirm the tender programme.")).toBeInTheDocument();
    expect(screen.getByText("Review note.")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("clerk:block");
  });

  it("keeps Trace & QA collapsed, out of section navigation, and optionally hidden", () => {
    const markdown = `${MARKDOWN}\n## Trace & QA\n\n**Inputs to resolve**\n- Tender close date\n`;
    const view = render(<MarkdownContent markdown={markdown} />);

    const details = screen.getByText("Trace & QA").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveClass("print:hidden");
    expect(screen.getByRole("navigation", { name: "Document sections" })).not.toHaveTextContent(
      "Trace & QA",
    );

    view.rerender(<MarkdownContent markdown={markdown} showTraceQa={false} />);
    expect(screen.queryByText("Trace & QA")).not.toBeInTheDocument();
    expect(screen.queryByText("Tender close date")).not.toBeInTheDocument();
  });

  it("omits the owner-side governance disclaimer from existing PMPs", () => {
    render(
      <MarkdownContent
        markdown={`## Project Summary

This is an owner side review and governance plan, not an instruction, statutory submission, tender document or construction management plan.

## Brief

Repair the existing roof.`}
      />,
    );

    expect(screen.queryByText(/owner side review and governance plan/i)).not.toBeInTheDocument();
    expect(screen.getByText("Repair the existing roof.")).toBeInTheDocument();
  });

  it("leads the Brief with project content instead of draft-status prose", () => {
    render(
      <MarkdownContent
        markdown={`## Brief

Draft owner project brief - formal sign-off pending. Investigate and rectify the upper metal roof and associated stormwater drainage.`}
      />,
    );

    expect(screen.queryByText(/formal sign-off pending/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(
        "Investigate and rectify the upper metal roof and associated stormwater drainage.",
      ),
    ).toBeInTheDocument();
  });

  it("uses the citation number without repeating Evidence on file", () => {
    render(
      <MarkdownContent
        projectTitle="Roof Repair"
        markdown={`| Project | Roof remedial works addressing water ingress near mechanical plant; residential aged care subclass — User provided | [2] |
| --- | --- | --- |
| Critical current position | Draft summary | — |
| Client / owner | Uniting Church of Australia. Proposal addressed to Cheyenne Shen. Evidence on file. | [1] |
| Site / asset | Uniting Abrina, 19-21 Victoria Street, Ashfield, New South Wales 2131. Investigate concerns the upper metal roof and associated stormwater drainage. | [1] |

## Scope

**Evidence on file:**

- Engagement letter executed 16/05/2026.

Address detail. Evidence on file.`}
      />,
    );

    expect(screen.queryByText(/evidence on file/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/user[- ]provided/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/critical current position/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/project detail/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Field$/i)).not.toBeInTheDocument();
    expect(screen.queryByText("[2]")).not.toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
    expect(screen.getByText("Roof Repair")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Roof remedial works addressing water ingress near mechanical plant; residential aged care subclass",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Proposal addressed to Cheyenne Shen/)).not.toBeInTheDocument();
    expect(screen.getByText("Uniting Church of Australia")).toBeInTheDocument();
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("Address")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Uniting Abrina, 19-21 Victoria Street, Ashfield, New South Wales 2131",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Investigate concerns/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("[1]")).toHaveLength(2);
    expect(
      screen
        .getAllByRole("row")
        .map((row) => row.querySelector("td")?.textContent),
    ).toEqual(["Project", "Address", "Owner", "Description"]);
  });

  it("splits combined identity rows and hides Confirmed prefixes", () => {
    render(
      <MarkdownContent
        projectTitle="Walsh 2"
        markdown={`## Project Summary

| Project / Owners / Site | Confirmed Walsh House / David and Emma Walsh / 42 Harvey Street | [1] |
| --- | --- | --- |

Bridge summary paragraph that should not render.

## Brief

Scope.`}
      />,
    );

    expect(screen.getByText("Walsh 2")).toBeInTheDocument();
    expect(screen.getByText("David and Emma Walsh")).toBeInTheDocument();
    expect(screen.getByText("42 Harvey Street")).toBeInTheDocument();
    expect(screen.queryByText(/Confirmed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Bridge summary/i)).not.toBeInTheDocument();
    expect(
      screen
        .getAllByRole("row")
        .map((row) => row.querySelector("td")?.textContent),
    ).toEqual(["Project", "Address", "Owner"]);
  });

  it("renders compact RFP source values as provenance chips", () => {
    render(
      <MarkdownContent
        markdown={`| Site | 88 Westgate Street | [2] |
| --- | --- | --- |
| State | NSW | Profile |
| Budget | TBC | Confirm |
| Occupation / staging | Sign brief seeks occupation. User setup says vacant. Conflict requiring resolution. | [3] |`}
      />,
    );

    const citation = screen.getByText("[2]");
    const profile = screen.getByText("Profile");
    const confirm = screen.getByText("Confirm");
    const conflictCitation = screen.getByText("[3]");

    expect(citation).toHaveClass("evidence-status-chip");
    expect(profile).toHaveClass("evidence-status-chip");
    expect(confirm).toHaveClass("evidence-status-chip");
    expect(screen.queryByText("Conflict")).not.toBeInTheDocument();
    expect(screen.queryByText(/requiring resolution/i)).not.toBeInTheDocument();
    expect(citation.querySelector("[data-status-dot]")).toBeNull();
    expect(profile.querySelector("[data-status-dot='info']")).toBeTruthy();
    expect(confirm.querySelector("[data-status-dot='caution']")).toBeTruthy();
    expect(conflictCitation).toHaveClass("evidence-status-chip");
    expect(conflictCitation.className).toMatch(/sw-critical/);
  });

  it("collapses the project document schedule behind a chevron", async () => {
    const user = userEvent.setup();
    render(
      <MarkdownContent
        markdown={[
          "# Request for Tender - Main Works",
          "",
          "## Tender conditions and RFI process",
          "",
          "Issue conditions.",
          "",
          "## Project Documents (2 documents)",
          "",
          "| Document number | Title | Rev | Category |",
          "| --- | --- | --- | --- |",
          "| A001 | General arrangement | C | Architectural |",
          "| E001 | Electrical layout | B | Electrical |",
        ].join("\n")}
      />,
    );

    const toggle = screen.getByRole("button", {
      name: "Project Documents (2 documents)",
    });
    const register = document.getElementById("project-documents-register");

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(register).toHaveClass("hidden");

    await user.click(toggle);

    expect(
      screen.getByRole("button", {
        name: "Project Documents (2 documents)",
      }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById("project-documents-register")).not.toHaveClass(
      "hidden",
    );
    expect(screen.getByText("General arrangement")).toBeVisible();
  });

  it("marks grounded evidence chips with a positive status dot", () => {
    render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" version={2} />,
    );
    const grounded = screen.getByText("Grounded");
    expect(grounded).toHaveClass("evidence-status-chip");
    expect(grounded.querySelector("[data-status-dot='positive']")).toBeTruthy();
  });

  it("narrows consultant discipline and blanks Fee Not evidenced", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "## Consultants",
          "",
          "| Discipline | Firm | Scope / services | Fee | Status | Citation |",
          "| --- | --- | --- | --- | --- | --- |",
          "| Structural engineer | — | Assumption — services not yet appointed | Not evidenced | Not evidenced | — |",
          "| Surveyor | Acme Survey | Contour and detail survey | $4,200 | Partial | [1] |",
        ].join("\n")}
      />,
    );

    expect(container.querySelector("table.pmp-table-consultants")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-discipline")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-firm")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-scope")).toBeTruthy();

    const rows = screen.getAllByRole("row");
    const structuralCells = rows[1]?.querySelectorAll("td") ?? [];
    expect(structuralCells[3]?.textContent?.trim()).toBe("");
    expect(structuralCells[4]?.textContent).toMatch(/Not evidenced/);
    expect(screen.getByText("$4,200")).toBeInTheDocument();
  });

  it("stamps source offsets on block elements that slice back to the markdown", () => {
    const { container } = render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" version={2} />,
    );

    const blocks = container.querySelectorAll("[data-md-start]");
    expect(blocks.length).toBeGreaterThan(0);

    for (const block of blocks) {
      const start = Number(block.getAttribute("data-md-start"));
      const end = Number(block.getAttribute("data-md-end"));
      expect(end).toBeGreaterThan(start);
      expect(MARKDOWN.slice(start, end).length).toBe(end - start);
    }

    const paragraph = container.querySelector("p[data-md-start]")!;
    expect(
      MARKDOWN.slice(
        Number(paragraph.getAttribute("data-md-start")),
        Number(paragraph.getAttribute("data-md-end")),
      ),
    ).toBe("Follow up.");

    // A table row's source is the pipe-delimited line, not the rendered badge text.
    const row = container.querySelector("tbody tr[data-md-start]")!;
    expect(
      MARKDOWN.slice(
        Number(row.getAttribute("data-md-start")),
        Number(row.getAttribute("data-md-end")),
      ),
    ).toBe("| Budget | Grounded |");

    const heading = container.querySelector("h2[data-md-start]")!;
    expect(
      MARKDOWN.slice(
        Number(heading.getAttribute("data-md-start")),
        Number(heading.getAttribute("data-md-end")),
      ),
    ).toBe("## Snapshot");
  });

  it("keeps inline formatting visible while a paragraph is edited", async () => {
    const markdown = "## Scope\n\nAlpha **scope** with [guidance](https://example.com). [1]";
    const start = markdown.indexOf("Alpha");
    const range = { start, end: markdown.length };
    const onSaveSelectionEdit = vi.fn().mockResolvedValue(undefined);

    render(
      <MarkdownContent
        markdown={markdown}
        editingRange={range}
        onEditSelection={vi.fn()}
        onCancelSelectionEdit={vi.fn()}
        onSaveSelectionEdit={onSaveSelectionEdit}
      />,
    );

    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    expect(editor.tagName).toBe("P");
    expect(editor).toHaveClass("my-3", "leading-relaxed");
    expect(editor.parentElement).not.toHaveClass("border", "p-3");
    expect(editor).toHaveTextContent("Alpha scope with guidance. [1]");
    expect(editor.querySelector("strong")).toHaveTextContent("scope");
    expect(editor.querySelector("a")).toHaveTextContent("guidance");
    expect(editor).not.toHaveTextContent("**scope**");
    expect(screen.queryByRole("button", { name: "Save selection" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Edit paragraph manually/i })).not.toBeInTheDocument();

    editor.innerHTML = "Gamma <strong>scope</strong> with <a href=\"https://example.com\">guidance</a>. [1]";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    expect(onSaveSelectionEdit).toHaveBeenCalledWith(
      range,
      "Gamma **scope** with [guidance](https://example.com). [1]",
    );
  });

  it("does not offer a pen icon; double-click edits the clicked table cell in place", async () => {
    const markdown = `## Snapshot

| Field | Status |
| --- | --- |
| Budget | Grounded |
`;
    const row = "| Budget | Grounded |";
    const start = markdown.indexOf(row);
    const range = { start, end: start + row.length };
    const onSaveSelectionEdit = vi.fn().mockResolvedValue(undefined);

    function Harness() {
      const [editingRange, setEditingRange] = useState<{
        start: number;
        end: number;
      } | null>(null);
      const [focusCellIndex, setFocusCellIndex] = useState(0);
      return (
        <MarkdownContent
          markdown={markdown}
          editingRange={editingRange}
          editingFocusCellIndex={focusCellIndex}
          onEditSelection={(next, options) => {
            setEditingRange(next);
            setFocusCellIndex(options?.focusCellIndex ?? 0);
          }}
          onCancelSelectionEdit={() => setEditingRange(null)}
          onSaveSelectionEdit={onSaveSelectionEdit}
        />
      );
    }

    render(<Harness />);

    fireEvent.mouseEnter(screen.getByText("Budget").closest("tr")!);
    expect(screen.queryByRole("button", { name: /Edit paragraph manually/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Edit .* manually/i })).not.toBeInTheDocument();

    fireEvent.doubleClick(screen.getByText("Grounded"));

    const cells = screen.getAllByRole("textbox", { name: /Edit table cell/i });
    expect(cells).toHaveLength(2);
    expect(cells[0]).toHaveTextContent("Budget");
    expect(cells[1]).toHaveTextContent("Grounded");
    expect(cells[1]).toHaveFocus();
    expect(screen.queryByDisplayValue(/\| Budget \|/)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /Add paragraph|Edit paragraph/i })).not.toBeInTheDocument();

    cells[1].textContent = "Partial";
    fireEvent.input(cells[1]);
    fireEvent.blur(cells[1]);

    expect(onSaveSelectionEdit).toHaveBeenCalledWith(range, "| Budget | Partial |");
  });

  it("enters inline editing from a real double-click sequence", async () => {
    const user = userEvent.setup();
    const markdown = "## Brief\n\n**Physical brief:** new residential house and garage. [4]";
    const start = markdown.indexOf("**Physical brief:**");
    const range = { start, end: markdown.length };

    function Harness() {
      const [editingRange, setEditingRange] = useState<{
        start: number;
        end: number;
      } | null>(null);
      return (
        <MarkdownContent
          markdown={markdown}
          editingRange={editingRange}
          onEditSelection={setEditingRange}
          onCancelSelectionEdit={() => setEditingRange(null)}
          onSaveSelectionEdit={vi.fn().mockResolvedValue(undefined)}
        />
      );
    }

    render(<Harness />);
    await user.hover(screen.getByText("Physical brief:"));
    await user.dblClick(screen.getByText("Physical brief:"));

    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    expect(editor).toHaveTextContent("Physical brief: new residential house and garage. [4]");
    expect(editor).toHaveFocus();
    expect(range.start).toBe(markdown.indexOf("**Physical brief:**"));
  });

  it("maps an editable paragraph back to canonical offsets after decision grouping", () => {
    const markdown = `## Decisions

\`\`\`pmp-decision
{"id":"one","label":"First","options":[{"value":"yes","label":"Yes"}],"selected":"yes"}
\`\`\`

\`\`\`pmp-decision
{"id":"two","label":"Second","options":[{"value":"yes","label":"Yes"}],"selected":"yes"}
\`\`\`

## Later

Editable after decisions.`;
    const onEditSelection = vi.fn();

    render(
      <MarkdownContent
        markdown={markdown}
        projectId="project-1"
        onEditSelection={onEditSelection}
      />,
    );

    fireEvent.doubleClick(screen.getByText("Editable after decisions."));

    const start = markdown.indexOf("Editable after decisions.");
    expect(onEditSelection).toHaveBeenCalledWith({
      start,
      end: start + "Editable after decisions.".length,
    });
  });

  it("places block actions beside the hovered paragraph without a pen or heading toolbar", () => {
    const markdown = "## Brief\n\nFirst paragraph.\n\nSecond paragraph.\n\n## Risks\n\nRisk text.";
    const onEditSelection = vi.fn();
    const onEditWithAi = vi.fn();
    const onMutateBlock = vi.fn();

    render(
      <MarkdownContent
        markdown={markdown}
        onEditSelection={onEditSelection}
        onEditWithAi={onEditWithAi}
        onMutateBlock={onMutateBlock}
      />,
    );

    expect(screen.queryByRole("button", { name: /Edit paragraph/i })).not.toBeInTheDocument();
    const reserved = screen.getByText("First paragraph.").parentElement?.querySelector(
      "[data-block-actions]",
    );
    expect(reserved).not.toBeNull();
    expect(reserved).toHaveClass("w-[6.75rem]");

    fireEvent.mouseEnter(
      screen.getByText("First paragraph.").parentElement ??
        screen.getByText("First paragraph."),
    );

    expect(screen.queryByRole("button", { name: "Edit paragraph manually" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add paragraph above/i })).not.toBeInTheDocument();
    const firstParagraph = screen.getByText("First paragraph.");
    const row = firstParagraph.parentElement;
    const ai = screen.getByRole("button", { name: "Edit paragraph with AI" });
    const addBelow = screen.getByRole("button", { name: "Add paragraph below" });
    const duplicate = screen.getByRole("button", { name: "Duplicate paragraph" });
    const remove = screen.getByRole("button", { name: "Delete paragraph" });
    expect(row).toContainElement(ai);
    expect(row).toContainElement(addBelow);
    expect(row).toContainElement(duplicate);
    expect(row).toContainElement(remove);
    expect(row?.querySelector("[data-block-actions]")).toHaveClass("w-[6.75rem]");
    expect(
      screen.getByRole("heading", { name: "Brief", level: 2 }).parentElement,
    ).not.toContainElement(ai);
    expect(ai.querySelector('img[src="/style-guide/logo/mark-solid.svg"]')).not.toBeNull();
    expect(remove.querySelector("svg.lucide-trash")).not.toBeNull();

    fireEvent.click(ai);
    const firstStart = markdown.indexOf("First paragraph.");
    expect(onEditWithAi).toHaveBeenCalledWith(
      { start: firstStart, end: firstStart + "First paragraph.".length },
      expect.objectContaining({ top: expect.any(Number), left: expect.any(Number) }),
    );

    fireEvent.doubleClick(screen.getByText("Second paragraph."));
    const secondStart = markdown.indexOf("Second paragraph.");
    expect(onEditSelection).toHaveBeenCalledWith({
      start: secondStart,
      end: secondStart + "Second paragraph.".length,
    });
  });

  it("renders a chrome-free add-paragraph editor below the target paragraph", () => {
    const markdown = "## Brief\n\nFirst paragraph.\n\nSecond paragraph.";
    const firstStart = markdown.indexOf("First paragraph.");
    const firstEnd = firstStart + "First paragraph.".length;
    const target = {
      type: "paragraph" as const,
      range: { start: firstStart, end: firstEnd },
      sectionStart: 0,
    };

    render(
      <MarkdownContent
        markdown={markdown}
        onEditSelection={vi.fn()}
        onMutateBlock={vi.fn()}
        blockComposer={{
          operation: "ADD",
          target,
          placement: "after",
          initialContent: "",
        }}
        onCancelBlockComposer={vi.fn()}
        onSaveBlockComposer={vi.fn()}
      />,
    );

    const composer = screen.getByRole("textbox", { name: /Add paragraph/i });
    expect(composer.tagName).toBe("P");
    expect(composer).not.toHaveClass("border");
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    const firstAfter = screen.getByText("First paragraph.");
    expect(
      firstAfter.compareDocumentPosition(composer) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("does not stamp offsets on table cells, whose rendered text is synthesized", () => {
    const { container } = render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" />,
    );

    expect(container.querySelectorAll("td[data-md-start]")).toHaveLength(0);
    expect(container.querySelectorAll("th[data-md-start]")).toHaveLength(0);
  });

  it("hydrates embedded decisions from canonical server state", () => {
    render(
      <MarkdownContent
        markdown={MARKDOWN}
        projectId="project-1"
        decisions={[
          {
            id: "row-1",
            project_id: "project-1",
            decision_id: "procurement-route",
            section: "Procurement",
            label: "Procurement route",
            options: [
              { value: "traditional", label: "Traditional" },
              { value: "design_construct", label: "Design & Construct" },
            ],
            selected: "design_construct",
            source: "user",
            workflow_type: "create_pmp",
            revision: 4,
            set_revision: 5,
            locked: true,
            evidence_conflict: false,
            agent_suggestion: null,
            provenance: {},
            created_at: "2026-07-25T00:00:00.000Z",
            updated_at: "2026-07-25T00:00:00.000Z",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("decision-control")).toHaveAttribute(
      "data-selected",
      "design_construct",
    );
    expect(screen.getByTestId("decision-control")).toHaveAttribute(
      "data-revision",
      "4",
    );
    expect(screen.getByTestId("decision-control")).toHaveAttribute(
      "data-set-revision",
      "5",
    );
  });
});
