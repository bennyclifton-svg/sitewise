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
});
