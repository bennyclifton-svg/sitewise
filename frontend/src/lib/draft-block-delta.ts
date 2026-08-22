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

/** SHA-256 hex of `value`, or null where WebCrypto is unavailable. */
async function sha256Hex(value: string): Promise<string | null> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) return null;
  try {
    const digest = await subtle.digest(
      "SHA-256",
      new TextEncoder().encode(value),
    );
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  } catch {
    return null;
  }
}

/**
 * True when the locally-applied markdown is byte-identical to what the server
 * stored, so no reconciliation fetch is needed.
 *
 * The server returns `content_sha256` over the markdown it persisted. Hashing
 * the optimistic string locally turns "refetch the whole draft after every
 * keystroke-sized edit" into "refetch only when we actually diverged"
 * (plan §13). Returns false when WebCrypto is unavailable, which keeps the
 * old reload path as the safe default.
 */
export async function optimisticMatchesServer(
  optimisticMarkdown: string,
  delta: Pick<ArtefactBlockDelta, "content_sha256">,
): Promise<boolean> {
  if (!delta.content_sha256) return false;
  const local = await sha256Hex(optimisticMarkdown);
  return local !== null && local === delta.content_sha256;
}

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
