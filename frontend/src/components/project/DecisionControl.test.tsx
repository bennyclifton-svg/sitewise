import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  DecisionControl,
  selectionIsEvidenced,
} from "@/components/project/DecisionControl";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    putDecision: vi.fn(),
  },
}));

describe("DecisionControl", () => {
  it("renders button options even when there are more than four", () => {
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
          rationale: "Selected default is a placeholder.",
        }}
      />,
    );

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(5);
    expect(screen.getByText("AI selection")).toBeInTheDocument();
  });

  it("marks evidenced agent selections and saves a new selection", async () => {
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
        evidence_conflict: false,
        agent_suggestion: null,
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

    expect(screen.getByText("From evidence")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Design & Construct" }));
    expect(api.putDecision).toHaveBeenCalledWith(
      "project-1",
      "procurement-route",
      "design_construct",
    );
    expect(screen.getByText("Your selection")).toBeInTheDocument();
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
