import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarkdownContent } from "@/components/project/MarkdownContent";

vi.mock("@/components/project/DecisionControl", () => ({
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
  parseEmbeddedDecision: (raw: string) => JSON.parse(raw),
}));

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

  it("renders compact RFP source values as provenance chips", () => {
    render(
      <MarkdownContent
        markdown={`| Field | Project detail | Source |
| --- | --- | --- |
| Site | 88 Westgate Street | [2] |
| State | NSW | Profile |
| Budget | TBC | Confirm |
| Risk | Clash | Conflict |`}
      />,
    );

    const citation = screen.getByText("[2]");
    const profile = screen.getByText("Profile");
    const confirm = screen.getByText("Confirm");
    const conflict = screen.getByText("Conflict");

    expect(citation).toHaveClass("evidence-status-chip");
    expect(profile).toHaveClass("evidence-status-chip");
    expect(confirm).toHaveClass("evidence-status-chip");
    expect(conflict).toHaveClass("evidence-status-chip");
    expect(citation.querySelector("[data-status-dot='info']")).toBeTruthy();
    expect(profile.querySelector("[data-status-dot='info']")).toBeTruthy();
    expect(confirm.querySelector("[data-status-dot='caution']")).toBeTruthy();
    expect(conflict.querySelector("[data-status-dot='critical']")).toBeTruthy();
  });

  it("marks grounded evidence chips with a positive status dot", () => {
    render(
      <MarkdownContent markdown={MARKDOWN} projectId="project-1" version={2} />,
    );
    const grounded = screen.getByText("Grounded");
    expect(grounded).toHaveClass("evidence-status-chip");
    expect(grounded.querySelector("[data-status-dot='positive']")).toBeTruthy();
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
