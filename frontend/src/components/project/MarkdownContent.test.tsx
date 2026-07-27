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
| Budget | TBC | Confirm |`}
      />,
    );

    expect(screen.getByText("[2]")).toHaveClass("evidence-status-chip");
    expect(screen.getByText("Profile")).toHaveClass("evidence-status-chip");
    expect(screen.getByText("Confirm")).toHaveClass("evidence-status-chip");
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
