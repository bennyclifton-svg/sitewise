import { describe, expect, it } from "vitest";

import {
  rebaseDraftBlockEdit,
  visibleBlockContent,
} from "@/lib/draft-block-rebase";
import type { DraftArtifact } from "@/lib/types/project";

const BLOCK_ID = "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

function draft(overrides: Partial<DraftArtifact> = {}): DraftArtifact {
  return {
    id: "draft-1",
    project_id: "project-1",
    workflow_type: "create_pmp",
    version: 1,
    status: "draft",
    title: "PMP",
    workspace_path: "PMP.md",
    author_user_id: "user-1",
    content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nAlpha\n\nBeta`,
    model: "gpt-5.6-luna",
    runtime: "test",
    provenance_metadata: null,
    created_at: "2026-08-10T00:00:00.000Z",
    updated_at: "2026-08-10T00:00:00.000Z",
    ...overrides,
  };
}

describe("rebaseDraftBlockEdit", () => {
  it("rebases an untouched block edit onto a newer revision", () => {
    const snapshot = draft();
    const pending = draft({
      content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nGamma\n\nBeta`,
    });
    const latest = draft({
      id: "draft-2",
      version: 2,
      content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nAlpha\n\nBeta changed`,
    });

    const result = rebaseDraftBlockEdit({
      snapshot,
      pending,
      latest,
      blockId: BLOCK_ID,
      editedContent: "Gamma",
      blockType: "paragraph",
    });

    expect(result).toEqual({
      status: "safe",
      state: {
        ...latest,
        content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nGamma\n\nBeta changed`,
      },
    });
  });

  it("rejects rebase when the same block changed on the server", () => {
    const snapshot = draft();
    const pending = draft({
      content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nMine\n\nBeta`,
    });
    const latest = draft({
      version: 2,
      content_markdown: `<!-- clerk:block id=${BLOCK_ID} -->\nTheirs\n\nBeta`,
    });

    expect(
      rebaseDraftBlockEdit({
        snapshot,
        pending,
        latest,
        blockId: BLOCK_ID,
        editedContent: "Mine",
        blockType: "paragraph",
      }),
    ).toEqual({ status: "unsafe" });
  });

  it("reads visible paragraph content without markers", () => {
    expect(
      visibleBlockContent(
        `<!-- clerk:block id=${BLOCK_ID} -->\nAlpha\n\nBeta`,
        BLOCK_ID,
      ),
    ).toBe("Alpha");
  });
});
