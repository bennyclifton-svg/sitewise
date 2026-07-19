import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenderQuoteSelectionPanel } from "@/components/project/tender/TenderQuoteSelectionPanel";
import { api } from "@/lib/api";
import type { EvidencePreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getTenderQuoteSelection: vi.fn(),
    replaceTenderQuoteSelection: vi.fn(),
    getProject: vi.fn(),
    prepareTenderComparison: vi.fn(),
    startTenderComparison: vi.fn(),
  },
}));

describe("TenderQuoteSelectionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getTenderQuoteSelection).mockResolvedValue(emptySelection());
    vi.mocked(api.replaceTenderQuoteSelection).mockImplementation(async (_projectId, input) => ({
      ...emptySelection(),
      revision: 1,
      selection_id: "selection-1",
      selection_revision_id: "revision-1",
      quote_groups: input.quote_candidates.map((group, position) => ({
        group_id: `group-${position}`,
        builder_name: group.builder_name,
        position,
        files: group.ordered_workspace_file_ids.map((id, filePosition) => ({
          workspace_file_id: id,
          workspace_path: `quotes/${id}.pdf`,
          filename: `${id}.pdf`,
          content_hash: "a".repeat(64),
          storage_bucket: "project-files",
          storage_key: `project/${id}.pdf`,
          position: filePosition,
        })),
      })),
    }));
  });

  it("persists explicit ordered builder groups using workspace file identities", async () => {
    const user = userEvent.setup();
    renderPanel(selectedEvidence.slice(0, 2));
    await screen.findByText("Select repository rows, then add them as quote groups.");

    await user.click(screen.getByRole("button", { name: "Add selected files" }));
    await user.clear(screen.getByLabelText("Builder 1"));
    await user.type(screen.getByLabelText("Builder 1"), "Nexus Built");
    await user.clear(screen.getByLabelText("Builder 2"));
    await user.type(screen.getByLabelText("Builder 2"), "Kaposi Homes");
    await user.click(screen.getByRole("button", { name: "Save quote selection" }));

    await waitFor(() => expect(api.replaceTenderQuoteSelection).toHaveBeenCalledWith(
      "project-1",
      {
        expected_revision: 0,
        quote_candidates: [
          { builder_name: "Nexus Built", ordered_workspace_file_ids: ["workspace-1"] },
          { builder_name: "Kaposi Homes", ordered_workspace_file_ids: ["workspace-2"] },
        ],
      },
    ));
    expect(await screen.findByText(/revision 1/)).toBeInTheDocument();
  });

  it("restores saved group and file order on reload", async () => {
    vi.mocked(api.getTenderQuoteSelection).mockResolvedValue({
      ...emptySelection(),
      revision: 3,
      selection_id: "selection-1",
      selection_revision_id: "revision-3",
      quote_groups: [
        {
          group_id: "group-1",
          builder_name: "Nexus Built",
          position: 0,
          files: [
            { workspace_file_id: "workspace-2", workspace_path: "quotes/addendum.pdf", filename: "addendum.pdf", content_hash: "a".repeat(64), storage_bucket: "project-files", storage_key: "p/addendum.pdf", position: 0 },
            { workspace_file_id: "workspace-1", workspace_path: "quotes/main.pdf", filename: "main.pdf", content_hash: "b".repeat(64), storage_bucket: "project-files", storage_key: "p/main.pdf", position: 1 },
          ],
        },
      ],
    });
    renderPanel([]);
    expect(await screen.findByDisplayValue("Nexus Built")).toBeInTheDocument();
    expect(screen.getByText("1. addendum.pdf")).toBeInTheDocument();
    expect(screen.getByText("2. main.pdf")).toBeInTheDocument();
  });
});

function renderPanel(evidence: EvidencePreview[]) {
  return render(<MemoryRouter><TenderQuoteSelectionPanel projectId="project-1" selectedEvidence={evidence} /></MemoryRouter>);
}

function emptySelection() {
  return {
    selection_id: null,
    selection_revision_id: null,
    project_id: "project-1",
    purpose: "tender_comparison" as const,
    revision: 0,
    selected_by: null,
    created_at: null,
    quote_groups: [],
  };
}

const selectedEvidence: EvidencePreview[] = [
  evidence("1", "Nexus quote", "workspace-1"),
  evidence("2", "Kaposi quote", "workspace-2"),
];

function evidence(id: string, title: string, workspaceFileId: string): EvidencePreview {
  return {
    id,
    workspace_file_id: workspaceFileId,
    title,
    filename: `${id}.pdf`,
    relative_path: `quotes/${id}.pdf`,
    source_type: "project_evidence",
    document_class: "quote",
    excerpt: "",
  };
}
