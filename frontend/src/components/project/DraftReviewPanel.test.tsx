import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { api } from "@/lib/api";
import type { DraftArtifact } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    acceptDraft: vi.fn(),
    downloadWorkspaceFile: vi.fn(),
    getProjectDraft: vi.fn(),
    getLatestDraft: vi.fn(),
    patchDraft: vi.fn(),
  },
}));

const PROJECT_ID = "project-1";

function draft(overrides: Partial<DraftArtifact> = {}): DraftArtifact {
  return {
    id: "draft-1",
    project_id: PROJECT_ID,
    workflow_type: "create_pmp",
    version: 1,
    status: "draft",
    title: "Project Management Plan",
    workspace_path: "04-projects/demo/00-brief-pmp/PMP.md",
    author_user_id: "user-1",
    content_markdown: "# Original",
    model: "gpt-4.1-mini",
    runtime: "clerk-sitewise-create-pmp",
    provenance_metadata: null,
    created_at: "2026-07-04T12:00:00.000Z",
    updated_at: "2026-07-04T12:00:00.000Z",
    ...overrides,
  };
}

describe("DraftReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows refresh provenance strips for update drafts", () => {
    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft({
          version: 3,
          provenance_metadata: {
            sections_changed: ["Scope & client requirements", "Risks & actions"],
            evidence_changed: {
              added: ["04-projects/demo/new-brief.md"],
              removed: ["04-projects/demo/old-brief.md"],
              superseded: ["04-projects/demo/old-brief.md"],
              downgraded: ["Appointment & fee"],
              conflicted: [],
            },
            trace: [
              {
                step: "evidence_sweep",
                status: "complete",
                message: "Swept evidence batch 1 of 1.",
                metadata: { batch_index: 0 },
              },
            ],
          },
        })}
        onDraftUpdated={vi.fn()}
        onRunUpdatePmp={vi.fn()}
      />,
    );

    expect(screen.getByText("What changed in v3")).toBeInTheDocument();
    expect(screen.getByText("Scope & client requirements")).toBeInTheDocument();
    expect(screen.getByText(/Evidence changes:/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh pmp from documents/i })).toBeInTheDocument();
  });

  it("saves edits and swaps to the returned draft version", async () => {
    const user = userEvent.setup();
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Edited",
      created_at: "2026-07-04T12:05:00.000Z",
      updated_at: "2026-07-04T12:05:00.000Z",
    });
    vi.mocked(api.patchDraft).mockResolvedValue(updated);
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={draft()}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /edit markdown/i }));
    const editor = screen.getByRole("textbox");
    await user.clear(editor);
    await user.type(editor, "# Edited");
    await user.click(screen.getByRole("button", { name: /save edits/i }));

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
    });
    expect(api.patchDraft).toHaveBeenCalledWith(PROJECT_ID, "draft-1", "# Edited");
    expect(screen.getAllByText("v2")[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Edited" })).toBeInTheDocument();
  });

  it("loads the selected summary draft by id", async () => {
    const fullDraft = draft({ content_markdown: "# Loaded PMP\n\nContent" });
    vi.mocked(api.getProjectDraft).mockResolvedValue(fullDraft);

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={{
          id: "draft-1",
          project_id: PROJECT_ID,
          workflow_type: "create_pmp",
          version: 1,
          status: "draft",
          title: "Project Management Plan",
          workspace_path: "04-projects/demo/00-brief-pmp/PMP.md",
          author_user_id: "user-1",
          model: "gpt-4.1-mini",
          runtime: "clerk-sitewise-create-pmp",
          created_at: "2026-07-04T12:00:00.000Z",
          updated_at: "2026-07-04T12:00:00.000Z",
        }}
        onDraftUpdated={vi.fn()}
      />,
    );

    expect(api.getProjectDraft).toHaveBeenCalledWith(PROJECT_ID, "draft-1");
    expect(await screen.findByRole("heading", { name: "Loaded PMP" })).toBeInTheDocument();
    expect(api.getLatestDraft).not.toHaveBeenCalled();
  });

  it("edits one section and leaves the other section unchanged", async () => {
    const user = userEvent.setup();
    const original = draft({
      content_markdown: "# Title\n\n## First\n\nAlpha\n\n## Second\n\nBeta\n",
    });
    const updated = draft({
      id: "draft-2",
      version: 2,
      content_markdown: "# Title\n\n## First\n\nGamma\n\n## Second\n\nBeta\n",
    });
    vi.mocked(api.patchDraft).mockResolvedValue(updated);
    const onDraftUpdated = vi.fn();

    render(
      <DraftReviewPanel
        projectId={PROJECT_ID}
        draft={original}
        onDraftUpdated={onDraftUpdated}
      />,
    );

    await user.click(screen.getAllByRole("button", { name: "Edit section" })[0]!);
    const editor = screen.getByRole("textbox");
    await user.clear(editor);
    await user.type(editor, "## First\n\nGamma\n");
    await user.click(screen.getByRole("button", { name: /save section/i }));

    await waitFor(() => {
      expect(onDraftUpdated).toHaveBeenCalledWith(updated);
    });
    expect(api.patchDraft).toHaveBeenCalledWith(
      PROJECT_ID,
      "draft-1",
      expect.stringContaining("## Second\n\nBeta"),
    );
    expect(vi.mocked(api.patchDraft).mock.calls[0]?.[2]).toContain("Gamma");
    expect(vi.mocked(api.patchDraft).mock.calls[0]?.[2]).not.toContain("Alpha");
  });
});
