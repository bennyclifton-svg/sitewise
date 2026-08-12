import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  DecisionControl,
  DecisionFinishSelect,
  DecisionSchedule,
  groupConsecutiveDecisionFences,
  selectionIsEvidenced,
} from "@/components/project/DecisionControl";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    putDecision: vi.fn(),
  },
}));

describe("DecisionControl", () => {
  it("renders compact row options without placeholder rationale", () => {
    render(
      <DecisionControl
        projectId="project-1"
        decision={{
          id: "kitchen-benchtop",
          label: "Kitchen benchtop",
          options: [
            { value: "laminate", label: "Laminate" },
            { value: "engineered_stone", label: "Engineered stone / quartz" },
            { value: "natural_stone", label: "Natural stone" },
            { value: "solid_surface", label: "Solid surface" },
            { value: "timber", label: "Timber" },
          ],
          selected: "engineered_stone",
          source: "agent",
          evidenced: false,
          rationale: "Selected default placeholder project sources do not nominate flooring.",
        }}
      />,
    );

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(5);
    expect(
      screen.queryByText(/selected default placeholder/i),
    ).not.toBeInTheDocument();
    const badge = screen.getByText("[AI]");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("evidence-status-chip");
    expect(badge.querySelector("[data-status-dot]")).toBeNull();
  });

  it("marks agent selections as AI and user overrides as User", async () => {
    const user = userEvent.setup();
    vi.mocked(api.putDecision).mockResolvedValue({
      decision: {
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
        revision: 2,
        set_revision: 3,
        locked: true,
        evidence_conflict: false,
        agent_suggestion: null,
        provenance: { interface: "http" },
        created_at: "2026-07-05T00:00:00.000Z",
        updated_at: "2026-07-05T00:00:00.000Z",
      },
      draft: {
        id: "draft-1",
        project_id: "project-1",
        workflow_type: "create_pmp",
        version: 1,
        status: "draft",
        title: "PMP",
        workspace_path: "path",
        author_user_id: "user-1",
        content_markdown: "updated",
        model: null,
        runtime: "test",
        provenance_metadata: null,
        created_at: "2026-07-05T00:00:00.000Z",
        updated_at: "2026-07-05T00:00:00.000Z",
      },
    });

    render(
      <DecisionControl
        projectId="project-1"
        decision={{
          id: "procurement-route",
          label: "Procurement route",
          options: [
            { value: "traditional", label: "Traditional" },
            { value: "design_construct", label: "Design & Construct" },
          ],
          selected: "traditional",
          source: "agent",
          evidenced: true,
          rationale: "Engagement letter states traditional lump-sum tender.",
        }}
      />,
    );

    expect(screen.getByText("[AI]")).toBeInTheDocument();
    expect(screen.queryByText("From evidence")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Design & Construct" }));
    expect(api.putDecision).toHaveBeenCalledWith(
      "project-1",
      "procurement-route",
      "design_construct",
      1,
      1,
    );
    expect(screen.getByText("[User]")).toBeInTheDocument();
    expect(screen.queryByText("Your selection")).not.toBeInTheDocument();
  });
});

describe("DecisionFinishSelect", () => {
  it("shows the selected finish in a combobox and commits overrides", async () => {
    const user = userEvent.setup();
    vi.mocked(api.putDecision).mockResolvedValue({
      decision: {
        id: "row-1",
        project_id: "project-1",
        decision_id: "flooring-finish",
        section: "FFE Schedule",
        label: "Primary flooring finish",
        options: [
          { value: "engineered", label: "Engineered timber" },
          { value: "tile", label: "Ceramic / porcelain tile" },
        ],
        selected: "engineered",
        source: "user",
        workflow_type: "create_pmp",
        revision: 2,
        set_revision: 3,
        locked: true,
        evidence_conflict: false,
        agent_suggestion: null,
        provenance: { interface: "http" },
        created_at: "2026-07-05T00:00:00.000Z",
        updated_at: "2026-07-05T00:00:00.000Z",
      },
      draft: {
        id: "draft-1",
        project_id: "project-1",
        workflow_type: "create_pmp",
        version: 1,
        status: "draft",
        title: "PMP",
        workspace_path: "path",
        author_user_id: "user-1",
        content_markdown: "updated",
        model: null,
        runtime: "test",
        provenance_metadata: null,
        created_at: "2026-07-05T00:00:00.000Z",
        updated_at: "2026-07-05T00:00:00.000Z",
      },
    });

    render(
      <DecisionFinishSelect
        projectId="project-1"
        decision={{
          id: "flooring-finish",
          label: "Primary flooring finish",
          options: [
            { value: "engineered", label: "Engineered timber" },
            { value: "tile", label: "Ceramic / porcelain tile" },
            { value: "carpet", label: "Carpet" },
          ],
          selected: "tile",
          source: "agent",
        }}
      />,
    );

    expect(screen.queryByRole("button", { name: "Carpet" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Primary flooring finish" })).toHaveTextContent(
      "Ceramic / porcelain tile",
    );
    expect(screen.getByText("[AI]")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Primary flooring finish" }));
    await user.click(screen.getByRole("menuitem", { name: "Engineered timber" }));

    expect(api.putDecision).toHaveBeenCalledWith(
      "project-1",
      "flooring-finish",
      "engineered",
      1,
      1,
    );
    expect(screen.getByText("[User]")).toBeInTheDocument();
  });
});

describe("DecisionSchedule", () => {
  it("renders consecutive finishes in one shell tile", () => {
    const { container } = render(
      <DecisionSchedule
        projectId="project-1"
        decisions={[
          {
            id: "primary-flooring",
            label: "Primary flooring system",
            options: [
              { value: "carpet", label: "Carpet" },
              { value: "timber", label: "Engineered timber" },
            ],
            selected: "carpet",
            source: "agent",
          },
          {
            id: "wall-finish",
            label: "Primary wall finish",
            options: [
              { value: "paint", label: "Paint" },
              { value: "tile", label: "Tile" },
            ],
            selected: "paint",
            source: "agent",
          },
        ]}
      />,
    );

    expect(container.querySelectorAll(".sw-specular")).toHaveLength(1);
    expect(screen.getByText("Primary flooring system")).toBeInTheDocument();
    expect(screen.getByText("Primary wall finish")).toBeInTheDocument();
    expect(screen.getAllByText("[AI]")).toHaveLength(2);
  });
});

describe("groupConsecutiveDecisionFences", () => {
  it("collapses consecutive decision fences into one group fence", () => {
    const markdown = `## Finishes

\`\`\`pmp-decision
{"id":"a","label":"A","options":[{"value":"1","label":"One"}],"selected":"1"}
\`\`\`

\`\`\`pmp-decision
{"id":"b","label":"B","options":[{"value":"2","label":"Two"}],"selected":"2"}
\`\`\`

## Next
`;
    const grouped = groupConsecutiveDecisionFences(markdown);
    expect(grouped).toContain("```pmp-decision-group");
    expect(grouped).not.toMatch(/```pmp-decision\n/);
    expect(grouped).toContain('\\"id\\":\\"a\\"');
    expect(grouped).toContain('\\"id\\":\\"b\\"');
    expect(grouped).toContain("## Next");
  });
});

describe("selectionIsEvidenced", () => {
  it("treats explicit evidenced flags and user locks as evidenced", () => {
    expect(
      selectionIsEvidenced(
        {
          id: "x",
          label: "X",
          options: [{ value: "a", label: "A" }],
          selected: "a",
          evidenced: true,
        },
        "agent",
      ),
    ).toBe(true);
    expect(
      selectionIsEvidenced(
        {
          id: "x",
          label: "X",
          options: [{ value: "a", label: "A" }],
          selected: "a",
          evidenced: false,
        },
        "user",
      ),
    ).toBe(true);
  });

  it("infers unevidenced from placeholder rationale when flag missing", () => {
    expect(
      selectionIsEvidenced(
        {
          id: "kitchen-benchtop",
          label: "Kitchen benchtop",
          options: [{ value: "engineered_stone", label: "Engineered stone" }],
          selected: "engineered_stone",
          rationale:
            "Kitchen benchtop selection is not evidenced; selected default is a placeholder.",
        },
        "agent",
      ),
    ).toBe(false);
  });
});
