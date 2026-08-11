import type { DraftArtifact } from "@/lib/types/project";

export type ArtefactBlockDelta = {
  draft_id: string;
  version: number;
  updated_at: string;
  changed_block_ids: string[];
  deleted_block_ids: string[];
  blocks: Record<string, unknown>;
  content_sha256: string;
  generation_manifest_present: boolean;
};

/** Merge a lean block-mutation delta into local optimistic draft state. */
export function applyArtefactBlockDelta(
  base: DraftArtifact,
  delta: ArtefactBlockDelta,
  optimisticMarkdown: string,
): DraftArtifact {
  const provenance = { ...(base.provenance_metadata ?? {}) };
  const priorBlocks =
    provenance.blocks && typeof provenance.blocks === "object"
      ? { ...(provenance.blocks as Record<string, unknown>) }
      : {};
  for (const blockId of delta.deleted_block_ids) {
    delete priorBlocks[blockId];
  }
  Object.assign(priorBlocks, delta.blocks);
  return {
    ...base,
    id: delta.draft_id,
    version: delta.version,
    updated_at: delta.updated_at,
    content_markdown: optimisticMarkdown,
    provenance_metadata: {
      ...provenance,
      blocks: priorBlocks,
      changed_block_ids: delta.changed_block_ids,
    },
  };
}
