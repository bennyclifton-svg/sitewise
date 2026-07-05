import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarkdownContent } from "@/components/project/MarkdownContent";

vi.mock("@/components/project/DecisionControl", () => ({
  DecisionControl: ({ decision }: { decision: { label: string } }) => (
    <div data-testid="decision-control">{decision.label}</div>
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
});
