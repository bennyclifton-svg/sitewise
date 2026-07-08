import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenderQuoteSelectionPanel } from "@/components/project/tender/TenderQuoteSelectionPanel";
import { api } from "@/lib/api";
import type { EvidencePreview } from "@/lib/types/project";
import type { TenderComparison } from "@/lib/types/tender";

vi.mock("@/lib/api", () => ({
  api: {
    createTenderComparisonFromProjectFiles: vi.fn(),
  },
}));

describe("TenderQuoteSelectionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.createTenderComparisonFromProjectFiles).mockResolvedValue({
      id: "comparison-1",
    } as TenderComparison);
  });

  it("renders selected repository files without the manual intake fields", () => {
    renderPanel(selectedEvidence.slice(0, 3));

    expect(screen.getByText("Quote selection")).toBeInTheDocument();
    expect(screen.getByText("NexusBuilt quote")).toBeInTheDocument();
    expect(screen.getByText("Kaposi tender")).toBeInTheDocument();
    expect(screen.getByText("Enmore tender")).toBeInTheDocument();
    expect(screen.queryByLabelText("State")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Builder")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("ABN")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Stated total")).not.toBeInTheDocument();
  });

  it("only enables saving for 2-5 selected quote files", () => {
    const { rerender } = renderPanel(selectedEvidence.slice(0, 1));
    expect(screen.getByRole("button", { name: "Save quote selection" })).toBeDisabled();

    rerender(panelTree(selectedEvidence.slice(0, 2)));
    expect(screen.getByRole("button", { name: "Save quote selection" })).toBeEnabled();

    rerender(panelTree(selectedEvidence));
    expect(screen.getByRole("button", { name: "Save quote selection" })).toBeDisabled();
  });

  it("saves selected repository paths and opens the created comparison", async () => {
    const user = userEvent.setup();
    renderPanel(selectedEvidence.slice(0, 2));

    await user.click(screen.getByRole("button", { name: "Save quote selection" }));

    await waitFor(() =>
      expect(api.createTenderComparisonFromProjectFiles).toHaveBeenCalledWith({
        project_id: "project-1",
        workspace_paths: ["quotes/nexus.pdf", "quotes/kaposi.pdf"],
      }),
    );
    expect(await screen.findByText("opened comparison-1")).toBeInTheDocument();
  });
});

function renderPanel(evidence: EvidencePreview[]) {
  return render(panelTree(evidence));
}

function panelTree(evidence: EvidencePreview[]) {
  return (
    <MemoryRouter initialEntries={["/projects/project-1/tender"]}>
      <Routes>
        <Route
          path="/projects/:projectId/tender"
          element={
            <TenderQuoteSelectionPanel
              projectId="project-1"
              selectedEvidence={evidence}
            />
          }
        />
        <Route
          path="/projects/:projectId/tender/:comparisonId"
          element={<ComparisonOpened />}
        />
      </Routes>
    </MemoryRouter>
  );
}

function ComparisonOpened() {
  const { comparisonId } = useParams();
  return <p>opened {comparisonId}</p>;
}

const selectedEvidence: EvidencePreview[] = [
  evidence("1", "NexusBuilt quote", "quotes/nexus.pdf"),
  evidence("2", "Kaposi tender", "quotes/kaposi.pdf"),
  evidence("3", "Enmore tender", "quotes/enmore.pdf"),
  evidence("4", "Fourth quote", "quotes/fourth.pdf"),
  evidence("5", "Fifth quote", "quotes/fifth.pdf"),
  evidence("6", "Sixth quote", "quotes/sixth.pdf"),
];

function evidence(id: string, title: string, relativePath: string): EvidencePreview {
  return {
    id,
    title,
    filename: relativePath.split("/").at(-1) ?? relativePath,
    relative_path: relativePath,
    source_type: "project_evidence",
    document_class: "quote",
    excerpt: "",
    document_number: null,
    revision: null,
    category: "Tender",
  };
}
