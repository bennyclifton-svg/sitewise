import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceFilePanel } from "@/components/project/WorkspaceFilePanel";
import type { EvidencePreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getProjectEvidenceDocument: vi.fn(),
  },
}));

const PROJECT_ID = "project-1";

function evidence(overrides: Partial<EvidencePreview> = {}): EvidencePreview {
  return {
    id: "evidence-1",
    title: "Kaposi",
    filename: "Kaposi.pdf",
    relative_path: "04-projects/caves-beach-reno/_inbox/Kaposi.pdf",
    source_type: "project_evidence",
    document_class: "unknown",
    excerpt: "",
    content: "## Page 1\n\nLine one\nLine two",
    document_number: null,
    revision: null,
    category: null,
    ...overrides,
  };
}

describe("WorkspaceFilePanel", () => {
  it("renders the markdown tab as formatted content", () => {
    render(
      <WorkspaceFilePanel
        projectId={PROJECT_ID}
        evidence={evidence({
          content: "## Page 1\n\n|Trade|Price|\n|---|---|\n|Demo|$1,000|",
        })}
      />,
    );

    expect(screen.getByRole("heading", { name: "Page 1" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "$1,000" })).toBeInTheDocument();
  });

  it("switches between rendered HTML, highlighted YAML, and raw views", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <WorkspaceFilePanel
        projectId={PROJECT_ID}
        evidence={evidence({
          content: "## Page 1\n\n|Trade|Price|\n|---|---|\n|Demo|$1,000|",
        })}
      />,
    );

    await user.click(screen.getByRole("tab", { name: "HTML" }));
    expect(screen.getByRole("heading", { name: "Page 1" })).toBeInTheDocument();
    expect(container.querySelector(".document-html table")).not.toBeNull();
    expect(container.querySelector(".document-html")?.textContent).not.toContain("<article>");

    await user.click(screen.getByRole("tab", { name: "YAML" }));
    const yaml = container.querySelector("pre");
    expect(yaml?.textContent).toContain("document:");
    expect(container.querySelector("pre")?.textContent).toContain('filename: "Kaposi.pdf"');
    expect(container.querySelector(".text-sky-700")).not.toBeNull();

    await user.click(screen.getByRole("tab", { name: "Raw" }));
    expect(container.querySelector("pre")?.textContent).toBe(
      "## Page 1\n\n|Trade|Price|\n|---|---|\n|Demo|$1,000|",
    );
  });
});
