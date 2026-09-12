import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render as renderUI, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceFilePanel } from "@/components/project/WorkspaceFilePanel";
import { api } from "@/lib/api";
import { applyProjectResourceSignal } from "@/lib/queries/project-data";
import type { EvidencePreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getProjectEvidenceDocument: vi.fn(),
  },
}));

const PROJECT_ID = "project-1";
function render(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return { client, ...renderUI(ui, {
    wrapper: ({ children }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  }) };
}

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
  it("refreshes changed evidence without blanking cached content and isolates projects", async () => {
    vi.mocked(api.getProjectEvidenceDocument).mockReset();
    vi.mocked(api.getProjectEvidenceDocument).mockResolvedValue(evidence());
    const summary = evidence({ content: null });
    const view = render(<WorkspaceFilePanel projectId={PROJECT_ID} evidence={summary} />);
    await screen.findByRole("heading", { name: "Page 1" });
    let finish!: (value: EvidencePreview) => void;
    vi.mocked(api.getProjectEvidenceDocument).mockReturnValue(new Promise(resolve => { finish = resolve; }));
    act(() => applyProjectResourceSignal(view.client, { projectId: PROJECT_ID, resourceType: "source_document" }));
    expect(screen.getByRole("heading", { name: "Page 1" })).toBeInTheDocument();
    await act(async () => finish(evidence({ content: "## New evidence" })));
    await screen.findByRole("heading", { name: "New evidence" });
    vi.mocked(api.getProjectEvidenceDocument).mockResolvedValue(evidence({ content: "## Other project" }));
    view.rerender(<WorkspaceFilePanel projectId="project-2" evidence={summary} />);
    expect(screen.queryByRole("heading", { name: "New evidence" })).not.toBeInTheDocument();
    await screen.findByRole("heading", { name: "Other project" });
    expect(api.getProjectEvidenceDocument).toHaveBeenLastCalledWith("project-2", summary.id);
  });
  it("reuses loaded content when a file is reopened, but fetches a new revision", async () => {
    vi.mocked(api.getProjectEvidenceDocument).mockReset();
    vi.mocked(api.getProjectEvidenceDocument).mockResolvedValue(evidence());
    const summary = evidence({ content: null, revision: "A" });
    const view = render(<WorkspaceFilePanel projectId={PROJECT_ID} evidence={summary} />);
    await screen.findByRole("heading", { name: "Page 1" });
    view.rerender(<WorkspaceFilePanel projectId={PROJECT_ID} evidence={null} />);
    view.rerender(<WorkspaceFilePanel projectId={PROJECT_ID} evidence={summary} />);
    expect(screen.getByRole("heading", { name: "Page 1" })).toBeInTheDocument();
    expect(api.getProjectEvidenceDocument).toHaveBeenCalledTimes(1);
    vi.mocked(api.getProjectEvidenceDocument).mockResolvedValue(evidence({ content: "## Revised content" }));
    view.rerender(<WorkspaceFilePanel projectId={PROJECT_ID} evidence={{ ...summary, revision: "B" }} />);
    await screen.findByRole("heading", { name: "Revised content" });
    expect(api.getProjectEvidenceDocument).toHaveBeenCalledTimes(2);
  });
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

  it("shows the document name with metadata collapsed by default", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceFilePanel
        projectId={PROJECT_ID}
        evidence={evidence({
          title: "DSP ISSUE03 15-02-20",
          document_number: "150214",
          relative_path: "04-projects/mosaic-apartments/_inbox/DSP.pdf",
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "DSP ISSUE03 15-02-20" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Document content")).not.toBeInTheDocument();
    expect(screen.queryByText("Doc No")).not.toBeInTheDocument();
    expect(
      screen.queryByText("04-projects/mosaic-apartments/_inbox/DSP.pdf"),
    ).not.toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: /show document details/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Doc No")).toBeInTheDocument();
    expect(screen.getByText("150214")).toBeInTheDocument();
    expect(
      screen.getByText("04-projects/mosaic-apartments/_inbox/DSP.pdf"),
    ).toBeInTheDocument();
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
    expect(container.querySelector("[class*='--sw-link']")).not.toBeNull();

    await user.click(screen.getByRole("tab", { name: "Raw" }));
    expect(container.querySelector("pre")?.textContent).toBe(
      "## Page 1\n\n|Trade|Price|\n|---|---|\n|Demo|$1,000|",
    );
  });

  it("resets document controls when the selected file changes", async () => {
    const user = userEvent.setup();
    const view = render(
      <WorkspaceFilePanel projectId={PROJECT_ID} evidence={evidence()} />,
    );

    await user.click(screen.getByRole("button", { name: /show document details/i }));
    await user.click(screen.getByRole("tab", { name: "Raw" }));
    expect(screen.getByRole("button", { name: /hide document details/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Raw" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    view.rerender(
      <WorkspaceFilePanel
        projectId={PROJECT_ID}
        evidence={evidence({ id: "evidence-2", title: "Second document" })}
      />,
    );

    expect(screen.getByRole("button", { name: /show document details/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Markdown" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
