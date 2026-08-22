import { describe, expect, it } from "vitest";

import {
  applyArtefactBlockDelta,
  optimisticMatchesServer,
} from "@/lib/draft-block-delta";
import type { DraftArtifact } from "@/lib/types/project";

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
    content_markdown: "Original paragraph.",
    model: null,
    runtime: "test",
    provenance_metadata: {
      generation_manifest: { input_fingerprint: "a".repeat(64) },
      blocks: {
        blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa: {
          type: "paragraph",
          last_modified_by: "ai",
        },
      },
    },
    created_at: "2026-08-11T00:00:00.000Z",
    updated_at: "2026-08-11T00:00:00.000Z",
    ...overrides,
  };
}

describe("applyArtefactBlockDelta", () => {
  it("merges version and changed block provenance without replacing unrelated blocks", () => {
    const base = draft();
    const next = applyArtefactBlockDelta(
      base,
      {
        draft_id: "draft-2",
        version: 2,
        updated_at: "2026-08-11T01:00:00.000Z",
        changed_block_ids: ["blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        deleted_block_ids: [],
        blocks: {
          blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa: {
            type: "paragraph",
            last_modified_by: "user",
          },
        },
        content_sha256: "b".repeat(64),
        generation_manifest_present: true,
      },
      "Updated paragraph.",
    );

    expect(next.id).toBe("draft-2");
    expect(next.version).toBe(2);
    expect(next.content_markdown).toBe("Updated paragraph.");
    expect(next.provenance_metadata?.generation_manifest).toEqual({
      input_fingerprint: "a".repeat(64),
    });
    expect(
      (next.provenance_metadata?.blocks as Record<string, { last_modified_by: string }>)
        .blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.last_modified_by,
    ).toBe("user");
  });
});

describe("optimisticMatchesServer", () => {
  async function sha256(value: string): Promise<string> {
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(value),
    );
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  it("confirms an optimistic apply that already matches the server", async () => {
    const markdown = "| Alpha | Beta |\n| Gamma | Delta |";
    await expect(
      optimisticMatchesServer(markdown, { content_sha256: await sha256(markdown) }),
    ).resolves.toBe(true);
  });

  it("reports a mismatch so the caller falls back to a reload", async () => {
    await expect(
      optimisticMatchesServer("local text", {
        content_sha256: await sha256("server text"),
      }),
    ).resolves.toBe(false);
  });

  it("reports a mismatch when the server sent no hash", async () => {
    await expect(
      optimisticMatchesServer("anything", { content_sha256: "" }),
    ).resolves.toBe(false);
  });
});
