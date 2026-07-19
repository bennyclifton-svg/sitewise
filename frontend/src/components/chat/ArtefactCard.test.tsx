import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ArtefactCard } from "@/components/chat/ArtefactCard";

describe("ArtefactCard", () => {
  it("renders a tender report link", () => {
    render(
      <MemoryRouter>
        <ArtefactCard
          projectId="project-1"
          artefact={{
            kind: "artefact",
            workflowType: "tender_report",
            draftId: "draft-1",
            comparisonId: "comparison-1",
            version: 3,
            title: "Tender comparison report",
          }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tender comparison report")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute(
      "href",
      "/projects/project-1/tender/comparison-1/report?revision=3",
    );
  });

  it("links a draft card to its exact revision", () => {
    render(
      <MemoryRouter>
        <ArtefactCard
          projectId="project-1"
          artefact={{
            kind: "artefact",
            workflowType: "create_pmp",
            draftId: "draft-2",
            version: 2,
            title: "Project plan",
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute(
      "href",
      "/projects/project-1?artefact=draft-2&workflow=create_pmp&revision=2",
    );
  });
});
