import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DecisionControl } from "@/components/project/DecisionControl";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    putDecision: vi.fn(),
  },
}));

describe("DecisionControl", () => {
  it("renders segmented controls and saves a new selection", async () => {
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
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Design & Construct" }));
    expect(api.putDecision).toHaveBeenCalledWith(
      "project-1",
      "procurement-route",
      "design_construct",
    );
    expect(screen.getByText("Your selection")).toBeInTheDocument();
  });
});
