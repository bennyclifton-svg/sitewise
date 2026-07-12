import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenderIntakePanel } from "@/components/project/tender/TenderIntakePanel";
import { api } from "@/lib/api";
import type { ProjectDecision } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    createTenderComparison: vi.fn(),
    createTenderQuote: vi.fn(),
    attachTenderProjectDocument: vi.fn(),
    uploadTenderQuoteDocument: vi.fn(),
    getProjectEvidence: vi.fn(),
    listDecisions: vi.fn(),
    putDecision: vi.fn(),
  },
}));

describe("TenderIntakePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getProjectEvidence).mockResolvedValue([]);
    vi.mocked(api.listDecisions).mockResolvedValue([contractFormDecision()]);
    vi.mocked(api.putDecision).mockResolvedValue({
      decision: contractFormDecision({ selected: "cost_plus", source: "user" }),
      draft: {
        id: "draft-1",
        project_id: "project-1",
        workflow_type: "create_pmp",
        version: 1,
        status: "draft",
        title: "PMP",
        workspace_path: "pmp.md",
        author_user_id: "user-1",
        content_markdown: "updated",
        model: null,
        runtime: "test",
        provenance_metadata: null,
        created_at: "2026-07-12T00:00:00.000Z",
        updated_at: "2026-07-12T00:00:00.000Z",
      },
    });
  });

  it("prefills shared contract form decisions and saves overrides", async () => {
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText("AI selection")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "HIA" })).toHaveAttribute(
      "data-slot",
      "button",
    );
    expect(
      screen
        .getAllByLabelText("Contract")
        .map((field) => (field as HTMLSelectElement).value),
    ).toEqual(["hia", "hia", "hia"]);

    await user.click(screen.getByRole("button", { name: "Cost Plus" }));

    await waitFor(() =>
      expect(api.putDecision).toHaveBeenCalledWith(
        "project-1",
        "contract-form",
        "cost_plus",
      ),
    );
    expect(screen.getByText("Your selection")).toBeInTheDocument();
  });
});

function renderPanel() {
  return render(
    <MemoryRouter initialEntries={["/projects/project-1/tender"]}>
      <Routes>
        <Route
          path="/projects/:projectId/tender"
          element={<TenderIntakePanel projectId="project-1" />}
        />
        <Route
          path="/projects/:projectId/tender/:comparisonId"
          element={<ComparisonOpened />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

function ComparisonOpened() {
  const { comparisonId } = useParams();
  return <p>opened {comparisonId}</p>;
}

function contractFormDecision(
  overrides: Partial<ProjectDecision> = {},
): ProjectDecision {
  return {
    id: "decision-row-1",
    project_id: "project-1",
    decision_id: "contract-form",
    section: "Procurement & delivery",
    label: "Contract form",
    options: [
      { value: "as4000", label: "AS 4000" },
      { value: "hia", label: "HIA" },
      { value: "design_construct", label: "Design & Construct" },
      { value: "cost_plus", label: "Cost Plus" },
    ],
    selected: "hia",
    source: "agent",
    workflow_type: "create_pmp",
    evidence_conflict: false,
    agent_suggestion: null,
    created_at: "2026-07-12T00:00:00.000Z",
    updated_at: "2026-07-12T00:00:00.000Z",
    ...overrides,
  };
}
