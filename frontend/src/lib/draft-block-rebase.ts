import type { ArtifactBlockType } from "@/lib/artifact-blocks";
import type { RebaseResult } from "@/lib/optimistic-mutation";
import type { DraftArtifact } from "@/lib/types/project";

const MARKER_RE = /<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->/gi;

/** Rebase a single-block draft edit onto the latest revision when safe. */
export function rebaseDraftBlockEdit(args: {
  snapshot: DraftArtifact;
  pending: DraftArtifact;
  latest: DraftArtifact;
  blockId?: string;
  editedContent?: string;
  blockType?: ArtifactBlockType;
}): RebaseResult<DraftArtifact> {
  const { snapshot, pending, latest, blockId, editedContent, blockType } = args;

  if (!blockId) {
    if (latest.content_markdown === snapshot.content_markdown) {
      return {
        status: "safe",
        state: { ...pending, id: latest.id, version: latest.version },
      };
    }
    return { status: "unsafe" };
  }

  const snapshotBlock = visibleBlockContent(snapshot.content_markdown, blockId);
  const latestBlock = visibleBlockContent(latest.content_markdown, blockId);

  // Protect / unprotect: markdown unchanged; only require the block still exists.
  if (
    editedContent === undefined &&
    pending.content_markdown === snapshot.content_markdown
  ) {
    if (latestBlock === null) return { status: "unsafe" };
    return {
      status: "safe",
      state: {
        ...latest,
        provenance_metadata: mergeBlockProvenance(
          latest.provenance_metadata,
          pending.provenance_metadata,
          blockId,
        ),
      },
    };
  }

  if (snapshotBlock === null || latestBlock === null) {
    return { status: "unsafe" };
  }
  if (snapshotBlock !== latestBlock) {
    return { status: "unsafe" };
  }

  if (editedContent !== undefined && blockType) {
    const nextMarkdown = replaceVisibleBlockContent(
      latest.content_markdown,
      blockId,
      editedContent,
      blockType,
    );
    if (nextMarkdown === null) return { status: "unsafe" };
    return {
      status: "safe",
      state: { ...latest, content_markdown: nextMarkdown },
    };
  }

  // Structural mutation against an untouched target: only auto-rebase when the
  // rest of the document is still identical (pure stale-version race).
  if (latest.content_markdown === snapshot.content_markdown) {
    return {
      status: "safe",
      state: { ...pending, id: latest.id, version: latest.version },
    };
  }
  return { status: "unsafe" };
}

export function visibleBlockContent(
  markdown: string,
  blockId: string,
): string | null {
  const marker = `<!-- clerk:block id=${blockId} -->`;
  const index = markdown.indexOf(marker);
  if (index < 0) return null;

  // Paragraph markers precede content.
  if (index === 0 || markdown[index - 1] === "\n") {
    const contentStart = index + marker.length;
    const after = markdown.slice(contentStart).replace(/^\r?\n/, "");
    const end = after.search(
      /\r?\n\r?\n|\r?\n<!--\s*clerk:block|\r?\n#|\r?\n[-*+] |\r?\n\d+[.)] |\r?\n\|/,
    );
    const body = end < 0 ? after : after.slice(0, end);
    return body.replace(MARKER_RE, "").trimEnd();
  }

  // List / table markers trail on the same line.
  const lineStart = markdown.lastIndexOf("\n", index - 1) + 1;
  const line = markdown.slice(lineStart, index + marker.length);
  return line.replace(MARKER_RE, "").trimEnd();
}

function replaceVisibleBlockContent(
  markdown: string,
  blockId: string,
  content: string,
  blockType: ArtifactBlockType,
): string | null {
  const marker = `<!-- clerk:block id=${blockId} -->`;
  const index = markdown.indexOf(marker);
  if (index < 0) return null;
  const normalized = content.replace(MARKER_RE, "").trimEnd();

  if (blockType === "paragraph") {
    const contentStart = index + marker.length;
    const afterMarker = markdown.slice(contentStart);
    const leading = afterMarker.match(/^\r?\n/)?.[0] ?? "";
    const body = afterMarker.slice(leading.length);
    const end = body.search(
      /\r?\n\r?\n|\r?\n<!--\s*clerk:block|\r?\n#|\r?\n[-*+] |\r?\n\d+[.)] |\r?\n\|/,
    );
    const rest = end < 0 ? "" : body.slice(end);
    return `${markdown.slice(0, index)}${marker}${leading}${normalized}${rest}`;
  }

  const lineStart = markdown.lastIndexOf("\n", index - 1) + 1;
  const lineEnd = index + marker.length;
  const suffix = blockType === "list_item" ? ` ${marker}` : marker;
  return `${markdown.slice(0, lineStart)}${normalized}${suffix}${markdown.slice(lineEnd)}`;
}

function mergeBlockProvenance(
  latest: DraftArtifact["provenance_metadata"],
  pending: DraftArtifact["provenance_metadata"],
  blockId: string,
): DraftArtifact["provenance_metadata"] {
  const latestBlocks =
    latest &&
    typeof latest === "object" &&
    latest.blocks &&
    typeof latest.blocks === "object"
      ? { ...(latest.blocks as Record<string, unknown>) }
      : {};
  const pendingBlocks =
    pending &&
    typeof pending === "object" &&
    pending.blocks &&
    typeof pending.blocks === "object"
      ? (pending.blocks as Record<string, unknown>)
      : {};
  if (pendingBlocks[blockId]) {
    latestBlocks[blockId] = pendingBlocks[blockId];
  }
  return {
    ...(latest && typeof latest === "object" ? latest : {}),
    blocks: latestBlocks,
  };
}
