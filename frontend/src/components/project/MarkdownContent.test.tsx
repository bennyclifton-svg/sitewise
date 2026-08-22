import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("hides the leading document title when asked", () => {
    render(
      <MarkdownContent
        markdown={[
          "# Request for Proposal - Structural engineer",
          "",
          "## Services and deliverables",
          "",
          "Structural design.",
        ].join("\n")}
        version={1}
        hideLeadingHeading
      />,
    );

    expect(
      screen.queryByRole("heading", {
        name: "Request for Proposal - Structural engineer",
        level: 1,
      }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("v1")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Services and deliverables", level: 2 }),
    ).toBeInTheDocument();
  });

  it("lifts inline paragraph and list citations into a trailing column", () => {
    const onMutateBlock = vi.fn();
    render(
      <MarkdownContent
        markdown={[
          "## Services and deliverables",
          "",
          "Provide a concise return brief identifying amendments. [2] [4]",
          "",
          "- Design the extension structure to the approved DA drawings [3]",
          "",
          "## Citation key",
          "",
          "- [2] Geotech report.pdf",
        ].join("\n")}
        onMutateBlock={onMutateBlock}
      />,
    );

    const paragraph = screen.getByText(
      "Provide a concise return brief identifying amendments.",
    );
    expect(paragraph.textContent).not.toMatch(/\[\d+\]/);
    const paragraphRow =
      paragraph.closest<HTMLElement>(".group\\/block") ?? paragraph.parentElement;
    expect(paragraphRow).not.toBeNull();
    const paragraphCitations = within(paragraphRow!).getByTestId("block-citation-slot");
    expect(paragraphCitations).toHaveTextContent("[2]");
    expect(paragraphCitations).toHaveTextContent("[4]");
    expect(paragraphRow).toContainElement(
      within(paragraphRow!).getByRole("button", { name: "paragraph actions" }),
    );

    const listItem = screen.getByText(
      "Design the extension structure to the approved DA drawings",
    );
    expect(listItem.textContent).not.toMatch(/\[\d+\]/);
    const listRow = listItem.closest("li");
    expect(listRow).not.toBeNull();
    const listCitations = within(listRow!).getByTestId("block-citation-slot");
    expect(listCitations).toHaveTextContent("[3]");

    expect(screen.getByText("[2] Geotech report.pdf")).toBeInTheDocument();
    expect(
      screen.getByText("[2] Geotech report.pdf").closest("li")?.querySelector(
        "[data-testid='block-citation-slot']",
      ),
    ).toBeNull();
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

  it("keeps ⋯ row actions on stamped Project Summary rows when decision fences are grouped", () => {
    const addressMarker =
      "<!-- clerk:block id=blk_ade5ba1bfc81abd258442ace94e4a835 -->";
    const ownerMarker =
      "<!-- clerk:block id=blk_d43c2c86c0565308ec1d324c2420c5fb -->";
    const markdown = `## Project Summary
| Project | Petersham |  |
| --- | --- | --- |
| Address | 82 Queen Street, Petersham NSW 2049 | [1] |${addressMarker}
| Owner | JOINS WIN PTY LTD | [1] |${ownerMarker}
| Description | New mixed-use development | [1] |

## Procurement and Delivery
\`\`\`pmp-decision
{"id":"procurement-route","section":"Procurement and Delivery","label":"Procurement route","options":[{"value":"design_construct","label":"Design & Construct"}],"selected":"design_construct","source":"agent","evidenced":true,"rationale":"D&C."}
\`\`\`
\`\`\`pmp-decision
{"id":"contract-form","section":"Procurement and Delivery","label":"Contract form","options":[{"value":"bespoke","label":"Bespoke"}],"selected":"bespoke","source":"agent","evidenced":false,"rationale":"Placeholder."}
\`\`\`
`;
    const { container } = render(
      <MarkdownContent
        markdown={markdown}
        projectTitle="Petersham"
        onEditSelection={vi.fn()}
        onEditWithAi={vi.fn()}
        onMutateBlock={vi.fn()}
      />,
    );

    const summaryTable = container.querySelector("table");
    expect(summaryTable).not.toBeNull();
    const rows = Array.from(summaryTable!.querySelectorAll("tr")).map((row) => ({
      label: row.querySelector("td,th")?.textContent?.trim(),
      actions: Boolean(row.querySelector("[data-block-actions]")),
    }));

    expect(rows).toEqual([
      { label: "Project", actions: true },
      { label: "Address", actions: true },
      { label: "Owner", actions: true },
      { label: "Description", actions: true },
    ]);
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

  it("hides truncated clerk:block comments in Brief prose", () => {
    const stamped = `## Brief

Rear extension and first-floor addition. [1] Inclusions: kitchen. <!-- clerk:block id=blk_dba9073a16ea8cddb7bc1e7117d5e43 -->
`;

    const { container } = render(<MarkdownContent markdown={stamped} />);

    expect(container).toHaveTextContent("Inclusions: kitchen.");
    expect(container).not.toHaveTextContent("clerk:block");
    expect(container).not.toHaveTextContent("blk_dba9073a16ea8cddb7bc1e7117d5e43");
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

  it("collapses the transmittal schedule behind a chevron", async () => {
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
      name: "Transmittal (2 documents)",
    });
    const register = document.getElementById("project-documents-register");

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(register).toHaveClass("hidden");

    await user.click(toggle);

    expect(
      screen.getByRole("button", {
        name: "Transmittal (2 documents)",
      }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById("project-documents-register")).not.toHaveClass(
      "hidden",
    );
    expect(screen.getByText("General arrangement")).toBeVisible();
  });

  it("loads the transmittal into the document schedule selection", async () => {
    const user = userEvent.setup();
    const onLoadTransmittal = vi.fn();
    render(
      <MarkdownContent
        markdown={[
          "# Request for Proposal",
          "",
          "## Transmittal (1 document)",
          "",
          "| Document number | Title | Rev | Category |",
          "| --- | --- | --- | --- |",
          "| A001 | General arrangement | C | Architectural |",
        ].join("\n")}
        canLoadTransmittal
        onLoadTransmittal={onLoadTransmittal}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Load Transmittal" }));
    expect(onLoadTransmittal).toHaveBeenCalledTimes(1);
  });

  it("saves the curated transmittal from the heading row", async () => {
    const user = userEvent.setup();
    const onSaveTransmittal = vi.fn();
    render(
      <MarkdownContent
        markdown={[
          "# Request for Proposal",
          "",
          "## Transmittal (0 documents)",
          "",
          "| Document number | Title | Rev | Category |",
          "| --- | --- | --- | --- |",
        ].join("\n")}
        canLoadTransmittal
        onLoadTransmittal={vi.fn()}
        canSaveTransmittal
        onSaveTransmittal={onSaveTransmittal}
      />,
    );

    expect(screen.getByRole("button", { name: "Load Transmittal" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save Transmittal" }));
    expect(onSaveTransmittal).toHaveBeenCalledTimes(1);
  });

  it("renders services and deliverables as a numbered list with visible markers", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "## Services and deliverables",
          "",
          "1. Review the project brief and planning pathway.",
          "2. Define architectural design scope and approval support.",
          "",
          "**Required deliverables**",
          "",
          "1. Fee proposal with staged architectural services.",
          "2. Scope schedule by phase.",
        ].join("\n")}
      />,
    );

    const lists = container.querySelectorAll(".draft-markdown ol");
    expect(lists.length).toBeGreaterThanOrEqual(1);
    for (const list of lists) {
      expect(list).toHaveClass("list-decimal");
    }
    const items = container.querySelectorAll(".draft-markdown ol > li");
    expect(items.length).toBe(4);
    for (const item of items) {
      expect(item).toHaveClass("list-item");
      expect(item.className).not.toMatch(/\bflex\b/);
    }
    expect(screen.getByText("Review the project brief and planning pathway.")).toBeInTheDocument();
  });

  it("renders citation key entries as a list, one per row", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "# Request for Proposal - Architect",
          "",
          "## Citation key",
          "",
          "[1] Project Profile — current",
          "[2] project-brief.pdf — on file",
          "[3] engagement-letter.pdf — on file",
        ].join("\n")}
      />,
    );

    const citationList = container.querySelector(".draft-markdown ul");
    expect(citationList).toBeTruthy();
    const items = citationList?.querySelectorAll("li") ?? [];
    expect([...items].map((item) => item.textContent?.trim())).toEqual([
      "[1] Project Profile — current",
      "[2] project-brief.pdf — on file",
      "[3] engagement-letter.pdf — on file",
    ]);
    expect(
      screen.queryByText(/\[1\] Project Profile — current \[2\] project-brief/i),
    ).not.toBeInTheDocument();
  });

  it("marks grounded evidence chips with a positive status dot", () => {
    render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" version={2} />,
    );
    const grounded = screen.getByText("Grounded");
    expect(grounded).toHaveClass("evidence-status-chip");
    expect(grounded.querySelector("[data-status-dot='positive']")).toBeTruthy();
  });

  it("drops consultant Scope / services and blanks Fee Not evidenced", () => {
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

    const consultantsTable = container.querySelector(
      "table.pmp-table-consultants",
    );
    expect(consultantsTable).toBeTruthy();
    expect(consultantsTable?.className).toMatch(/min-w-\[52rem\]/);
    expect(container.querySelector("col.pmp-col-discipline")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-firm")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-fee")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-status")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-citation")).toBeTruthy();
    expect(container.querySelector("col.pmp-col-scope")).toBeNull();
    expect(screen.queryByText("Scope / services")).not.toBeInTheDocument();
    expect(screen.queryByText(/services not yet appointed/i)).not.toBeInTheDocument();

    const rows = screen.getAllByRole("row");
    const structuralCells = rows[1]?.querySelectorAll("td") ?? [];
    expect(structuralCells).toHaveLength(5);
    expect(structuralCells[2]?.textContent?.trim()).toBe("");
    expect(structuralCells[3]?.textContent).toMatch(/Not evidenced/);
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
    expect(editor).toHaveClass("leading-relaxed");
    const host = editor.parentElement;
    expect(host).toHaveAttribute("data-inline-markdown-host");
    expect(host).toHaveClass("min-w-0", "flex-1");
    expect(host?.parentElement).toHaveClass("my-3");
    expect(host?.parentElement).not.toHaveClass("border", "p-3");
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

  it("keeps in-progress table cell text when MarkdownContent re-renders", () => {
    const markdown = [
      "## Consultants",
      "",
      "| Discipline | Firm | Fee | Status | Citation |",
      "| --- | --- | --- | --- | --- |",
      "| Surveyor | Acme Survey | $4,200 | Partial | [1] |",
    ].join("\n");
    const row = "| Surveyor | Acme Survey | $4,200 | Partial | [1] |";
    const start = markdown.indexOf(row);
    const range = { start, end: start + row.length };

    const view = render(
      <MarkdownContent
        markdown={markdown}
        editingRange={range}
        editingFocusCellIndex={2}
        onEditSelection={vi.fn()}
        onCancelSelectionEdit={vi.fn()}
        onSaveSelectionEdit={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const feeCell = screen.getByRole("textbox", { name: "Edit table cell 3" });
    expect(feeCell).toHaveTextContent("$4,200");
    feeCell.textContent = "8500";
    fireEvent.input(feeCell);

    // Parent polls / pulse refreshes rebuild callback identities every render.
    // Recreating react-markdown's `components` map used to remount the editor
    // and wipe the in-progress fee (often saving empty → displayed as blank/0).
    view.rerender(
      <MarkdownContent
        markdown={markdown}
        editingRange={range}
        editingFocusCellIndex={2}
        onEditSelection={vi.fn()}
        onCancelSelectionEdit={vi.fn()}
        onSaveSelectionEdit={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(screen.getByRole("textbox", { name: "Edit table cell 3" })).toHaveTextContent(
      "8500",
    );
  });

  it("keeps in-progress paragraph text when MarkdownContent re-renders", () => {
    const markdown = "## Scope\n\nAlpha paragraph.";
    const start = markdown.indexOf("Alpha");
    const range = { start, end: markdown.length };

    const view = render(
      <MarkdownContent
        markdown={markdown}
        editingRange={range}
        onEditSelection={vi.fn()}
        onCancelSelectionEdit={vi.fn()}
        onSaveSelectionEdit={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    editor.textContent = "Halfway typed";
    fireEvent.input(editor);

    view.rerender(
      <MarkdownContent
        markdown={markdown}
        editingRange={range}
        onEditSelection={vi.fn()}
        onCancelSelectionEdit={vi.fn()}
        onSaveSelectionEdit={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(screen.getByRole("textbox", { name: "Edit selected text" })).toHaveTextContent(
      "Halfway typed",
    );
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

    const editor = await screen.findByRole("textbox", {
      name: "Edit selected text",
    });
    expect(editor).toHaveTextContent(
      "Physical brief: new residential house and garage. [4]",
    );
    await waitFor(() => {
      expect(editor).toHaveFocus();
    });
    expect(range.start).toBe(markdown.indexOf("**Physical brief:**"));
  });

  it("shows one FFE list without dropdowns or Not evidenced chips", () => {
    const markdown = `## FFE Schedule

| Item | Location | Qty | Finish | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| External cladding | Extension | Not evidenced | Not evidenced | To be confirmed | Typical |
| Filtered tap | Kitchen | 1 | Chrome | Confirmed | Owner selection |

\`\`\`pmp-decision
{"id":"external-cladding","section":"FFE Schedule","label":"Primary external cladding","options":[{"value":"brick_veneer","label":"Brick veneer"},{"value":"fibre_cement","label":"Fibre cement sheet / weatherboard"}],"selected":"brick_veneer","source":"agent"}
\`\`\`
`;
    const { container } = render(
      <MarkdownContent
        markdown={markdown}
        projectId="project-1"
        decisions={[
          {
            id: "row-1",
            project_id: "project-1",
            decision_id: "external-cladding",
            section: "FFE Schedule",
            label: "Primary external cladding",
            options: [
              { value: "brick_veneer", label: "Brick veneer" },
              {
                value: "fibre_cement",
                label: "Fibre cement sheet / weatherboard",
              },
            ],
            selected: "brick_veneer",
            source: "agent",
            workflow_type: "create_pmp",
            revision: 1,
            set_revision: 1,
            locked: false,
            evidence_conflict: false,
            agent_suggestion: null,
            provenance: {},
            created_at: "2026-07-05T00:00:00.000Z",
            updated_at: "2026-07-05T00:00:00.000Z",
          },
        ]}
      />,
    );

    const table = container.querySelector("table.pmp-table-ffe");
    expect(table).toBeTruthy();
    const headers = within(table as HTMLElement)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent?.trim());
    expect(headers).toEqual(["Item", "Location", "Finish", "Comment", ""]);
    expect(screen.getByText("External cladding")).toBeInTheDocument();
    expect(screen.getByText("Brick veneer")).toBeInTheDocument();
    expect(screen.getByText("Filtered tap")).toBeInTheDocument();
    expect(screen.getByText("Chrome")).toBeInTheDocument();
    expect(screen.getByText("Owner selection")).toBeInTheDocument();
    expect(screen.queryByText("Primary external cladding")).not.toBeInTheDocument();
    expect(screen.queryByText("Not evidenced")).not.toBeInTheDocument();
    expect(screen.queryByText("Typical")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Primary external cladding" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("decision-schedule")).not.toBeInTheDocument();
    expect(screen.queryByTestId("decision-control")).not.toBeInTheDocument();
  });

  it("simplifies the Brief exclusions table to four columns plus a citation chip", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "## Brief",
          "",
          "| Item | Position | Basis / source | Owner | Verification action |",
          "| --- | --- | --- | --- | --- |",
          "| Tenant racking | Confirmed exclusion | Owner brief [1] | Owner | Lock the exclusion in the signed brief |",
          "| Solar PV | Design-development gap | No operational brief | Owner | Confirm with the client |",
        ].join("\n")}
      />,
    );

    const table = container.querySelector("table");
    expect(table).toBeTruthy();
    const headers = within(table as HTMLElement)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent?.trim());
    expect(headers).toEqual(["Item", "Position", "Owner", "Verification action", ""]);
    expect(screen.queryByText("Basis / source")).not.toBeInTheDocument();
    expect(screen.queryByText(/Owner brief/)).not.toBeInTheDocument();
    expect(screen.getByText("Tenant racking")).toBeInTheDocument();
    expect(screen.getByText("Lock the exclusion in the signed brief")).toBeInTheDocument();
    const citation = screen.getByText("[1]");
    expect(citation).toHaveClass("evidence-status-chip");
    const citedRow = citation.closest("tr");
    const citedCells = citedRow?.querySelectorAll("td") ?? [];
    expect(citedCells).toHaveLength(5);
    expect(citedCells[4]?.textContent?.trim()).toBe("[1]");
  });

  it("gives FFE and planning tables an independent citation column", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "## FFE Schedule",
          "",
          "| Item | Location | Finish | Comment |",
          "| --- | --- | --- | --- |",
          "| Facade cladding | Envelope | Brick veneer [2] | Match adjoining house |",
          "",
          "## Planning and Compliance",
          "",
          "| Approval / compliance item | Status | Basis | Next action |",
          "| --- | --- | --- | --- |",
          "| NCC pathway | Assumption | Taxonomy and loaded seed doctrine [3] | Confirm DtS with certifier |",
        ].join("\n")}
      />,
    );

    const tables = container.querySelectorAll("table");
    expect(tables).toHaveLength(2);

    const ffeHeaders = within(tables[0] as HTMLElement)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent?.trim());
    expect(ffeHeaders).toEqual(["Item", "Location", "Finish", "Comment", ""]);
    expect(screen.getByText("Brick veneer")).toBeInTheDocument();
    expect(screen.queryByText("Brick veneer [2]")).not.toBeInTheDocument();
    const ffeCitation = screen.getByText("[2]");
    expect(ffeCitation).toHaveClass("evidence-status-chip");
    expect(ffeCitation.closest("table")).toBe(tables[0]);

    const planningHeaders = within(tables[1] as HTMLElement)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent?.trim());
    expect(planningHeaders).toEqual([
      "Approval / compliance item",
      "Status",
      "Basis",
      "Next action",
      "",
    ]);
    expect(screen.getByText("Taxonomy and loaded seed doctrine")).toBeInTheDocument();
    const planningCitation = screen.getByText("[3]");
    expect(planningCitation).toHaveClass("evidence-status-chip");
    expect(planningCitation.closest("table")).toBe(tables[1]);
  });

  it("gives programme, risks, and actions tables an independent citation column", () => {
    const { container } = render(
      <MarkdownContent
        markdown={[
          "## Programme",
          "",
          "| Sub-milestone | Control requirement |",
          "| --- | --- |",
          "| DA submission | Lodgement package issued [4] |",
          "",
          "## Risks and mitigations",
          "",
          "| Risk | Owner | Mitigation / escalation |",
          "| --- | --- | --- |",
          "| Planning pathway changes scope | Owner / planner | Verify controls before scheme lock [5] |",
          "",
          "## Actions and decisions",
          "",
          "| Item | Owner | Status | Due basis | Next action |",
          "| --- | --- | --- | --- | --- |",
          "| Consultant appointments | Owner | Open | Before concept lock | Appoint design lead [6] |",
        ].join("\n")}
      />,
    );

    const tables = container.querySelectorAll("table");
    expect(tables).toHaveLength(3);

    expect(
      within(tables[0] as HTMLElement)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(["Sub-milestone", "Control requirement", ""]);
    const programmeCitation = screen.getByText("[4]");
    expect(programmeCitation).toHaveClass("evidence-status-chip");
    expect(screen.getByText("Lodgement package issued")).toBeInTheDocument();

    expect(
      within(tables[1] as HTMLElement)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(["Risk", "Owner", "Mitigation / escalation", ""]);
    expect(screen.getByText("[5]")).toHaveClass("evidence-status-chip");

    expect(
      within(tables[2] as HTMLElement)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(["Item", "Owner", "Status", "Due basis", "Next action", ""]);
    expect(screen.getByText("[6]")).toHaveClass("evidence-status-chip");
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
    expect(onEditSelection).toHaveBeenCalledWith(
      {
        start,
        end: start + "Editable after decisions.".length,
      },
      expect.objectContaining({
        caretPoint: expect.objectContaining({
          x: expect.any(Number),
          y: expect.any(Number),
        }),
      }),
    );
  });

  it("places a ⋯ menu with add/edit actions on the hovered paragraph", async () => {
    const user = userEvent.setup();
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
    const firstParagraph = screen.getByText("First paragraph.");
    const row = firstParagraph.parentElement;
    const reserved = row?.querySelector("[data-block-actions]");
    expect(reserved).not.toBeNull();
    expect(reserved).toHaveClass("w-6");

    expect(screen.queryByRole("button", { name: "Edit paragraph manually" })).not.toBeInTheDocument();
    const menuTrigger = within(row!).getByRole("button", { name: "paragraph actions" });
    expect(row).toContainElement(menuTrigger);
    expect(row?.querySelector("[data-block-gutter]")).toBeNull();
    expect(row?.querySelector("[data-block-actions]")).toHaveClass("w-6");
    expect(screen.queryByRole("button", { name: "Add paragraph above" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit paragraph with AI" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Duplicate paragraph" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete paragraph" })).not.toBeInTheDocument();

    await user.click(menuTrigger);
    expect(
      await screen.findByRole("menuitem", { name: "Edit paragraph with AI" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Add paragraph above" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Add paragraph below" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Duplicate paragraph" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Delete paragraph" })).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Add paragraph above" }));
    expect(onMutateBlock).toHaveBeenCalledWith(
      "ADD",
      expect.objectContaining({ type: "paragraph" }),
      "before",
    );

    await user.click(within(row!).getByRole("button", { name: "paragraph actions" }));
    await user.click(
      await screen.findByRole("menuitem", { name: "Edit paragraph with AI" }),
    );
    const firstStart = markdown.indexOf("First paragraph.");
    expect(onEditWithAi).toHaveBeenCalledWith(
      { start: firstStart, end: firstStart + "First paragraph.".length },
      expect.objectContaining({ top: expect.any(Number), left: expect.any(Number) }),
    );

    fireEvent.doubleClick(screen.getByText("Second paragraph."));
    const secondStart = markdown.indexOf("Second paragraph.");
    expect(onEditSelection).toHaveBeenCalledWith(
      {
        start: secondStart,
        end: secondStart + "Second paragraph.".length,
      },
      expect.objectContaining({
        caretPoint: expect.objectContaining({
          x: expect.any(Number),
          y: expect.any(Number),
        }),
      }),
    );
  });

  it("keeps list item action triggers mounted without a hover remount", () => {
    render(
      <MarkdownContent
        markdown={"## Scope\n\n- First item\n- Second item\n"}
        onEditWithAi={vi.fn()}
        onMutateBlock={vi.fn()}
      />,
    );

    const first = screen.getByText("First item").closest("li");
    const second = screen.getByText("Second item").closest("li");
    expect(first).not.toBeNull();
    expect(second).not.toBeNull();
    expect(
      within(first!).getByRole("button", { name: "list item actions" }),
    ).toBeInTheDocument();
    expect(
      within(second!).getByRole("button", { name: "list item actions" }),
    ).toBeInTheDocument();
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
