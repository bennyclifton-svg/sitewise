import type { MarkdownRange } from "@/lib/markdown-selection";

export type ArtifactBlockType = "paragraph" | "list_item" | "table_row";
export type ArtifactBlockOperationType =
  | "ADD"
  | "UPDATE"
  | "DELETE"
  | "MOVE"
  | "DUPLICATE"
  | "PROTECT"
  | "UNPROTECT"
  | "KEEP"
  | "CONFIRM_DELETE";

export type ArtifactBlockTarget = {
  id?: string;
  type: ArtifactBlockType;
  range: MarkdownRange;
  sectionStart: number;
};

export type ArtifactBlockOperation = {
  operation: ArtifactBlockOperationType;
  target: {
    id?: string;
    type: ArtifactBlockType;
    start?: number;
    end?: number;
  };
  content?: string;
  placement?: "before" | "after";
  reference_id?: string;
};

// Server ids are `blk_` + 32 hex; optimistic ids are `tmp_` + 8 hex (D5).
const BLOCK_MARKER_RE =
  /<!--\s*clerk:block\s+id=(?:blk_[a-f0-9]{32}|tmp_[a-f0-9]{8})\s*-->\s*/gi;
const TEMPORARY_MARKER_RE = /<!--\s*clerk:block\s+id=(tmp_[a-f0-9]{8})\s*-->/gi;

/** A block range no longer addresses the current document. */
export class StaleBlockRangeError extends Error {
  readonly range: MarkdownRange;
  readonly sourceLength: number;

  constructor(range: MarkdownRange, sourceLength: number) {
    super(
      `Block range ${range.start}-${range.end} is stale for a ${sourceLength}-character document.`,
    );
    this.name = "StaleBlockRangeError";
    this.range = range;
    this.sourceLength = sourceLength;
  }
}

/**
 * Mint an id for a block the client is inserting before the server has named
 * it. Written straight into the optimistic markdown so the inserted block is
 * addressable at once and the local body can be hashed against the server's
 * once the real id arrives. Never sent to the server: `ArtefactBlockTarget.id`
 * only accepts `blk_`.
 */
export function newTemporaryBlockId(): string {
  const bytes = new Uint8Array(4);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  return `tmp_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

/**
 * Wrap content in its block marker exactly as the server does.
 *
 * Must stay byte-identical to `_marked` in
 * `backend/app/projects/artefact_blocks.py`: after the id swap the optimistic
 * body is SHA-256'd against the body the server persisted, and a marker one
 * space out of place costs a full document reload (plan §13, G2).
 */
export function markedBlock(
  blockId: string,
  content: string,
  type: ArtifactBlockType,
): string {
  const marker = `<!-- clerk:block id=${blockId} -->`;
  // Mirrors `_normalise_content`: leading/trailing line breaks only.
  const normalized = content.replace(/^[\r\n]+/, "").replace(/[\r\n]+$/, "");
  if (type === "table_row") return `${normalized.replace(/\s+$/, "")}${marker}`;
  if (type === "list_item") return `${normalized.replace(/\s+$/, "")} ${marker}`;
  return `${marker}\n${normalized}`;
}

/**
 * Adopt the ids the server assigned, in place.
 *
 * Temporary markers are replaced in document order by the returned block ids
 * that are not already present, so the swapped body is byte-identical to the
 * server's without re-rendering the document or re-fetching it.
 */
export function swapTemporaryBlockIds(
  markdown: string,
  serverBlockIds: readonly string[],
): string {
  const unclaimed = serverBlockIds.filter(
    (id) => id.startsWith("blk_") && !markdown.includes(id),
  );
  if (unclaimed.length === 0) return markdown;
  let next = 0;
  return markdown.replace(TEMPORARY_MARKER_RE, (marker) =>
    next < unclaimed.length
      ? `<!-- clerk:block id=${unclaimed[next++]} -->`
      : marker,
  );
}

export function operationForTarget(
  operation: ArtifactBlockOperationType,
  target: ArtifactBlockTarget,
  options: {
    content?: string;
    placement?: "before" | "after";
    referenceId?: string;
  } = {},
): ArtifactBlockOperation {
  return {
    operation,
    target: {
      ...(target.id ? { id: target.id } : {}),
      type: target.type,
      start: target.range.start,
      end: target.range.end,
    },
    ...(options.content === undefined ? {} : { content: options.content }),
    ...(options.placement ? { placement: options.placement } : {}),
    ...(options.referenceId ? { reference_id: options.referenceId } : {}),
  };
}

/**
 * Reject a target that no longer addresses this document.
 *
 * Every mutation validates the *whole* target range, not just the offsets it
 * happens to read. An insert only needs `range.start`, but if `range.end` is
 * past the end of the document the block it claims to sit beside is gone, and
 * inserting anyway puts content in an arbitrary place (plan §8).
 */
function assertAddressable(source: string, range: MarkdownRange): void {
  if (range.start < 0 || range.start > range.end || range.end > source.length) {
    throw new StaleBlockRangeError(range, source.length);
  }
}

export function replaceBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
): string {
  assertAddressable(source, target.range);
  return replaceRange(source, target.range, content);
}

export function insertBeforeBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
  blockId?: string,
): string {
  assertAddressable(source, target.range);
  return replaceRange(
    source,
    { start: target.range.start, end: target.range.start },
    `${insertionFor(content, target.type, blockId)}${siblingSeparator(target.type)}`,
  );
}

export function insertAfterBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
  blockId?: string,
): string {
  assertAddressable(source, target.range);
  return replaceRange(
    source,
    { start: target.range.end, end: target.range.end },
    `${siblingSeparator(target.type)}${insertionFor(content, target.type, blockId)}`,
  );
}

export function deleteBlock(source: string, target: ArtifactBlockTarget): string {
  assertAddressable(source, target.range);
  let { start, end } = target.range;
  // Block ranges end at content (not the line terminator). Consume one
  // trailing newline so table/list deletes do not leave a blank line that
  // splits a GFM table or CommonMark list.
  if (end < source.length && source[end] === "\n") {
    end += 1;
  } else if (start > 0 && source[start - 1] === "\n") {
    start -= 1;
  }
  return replaceRange(source, { start, end }, "").replace(/\n{3,}/g, "\n\n");
}

export function duplicateBlock(
  source: string,
  target: ArtifactBlockTarget,
  blockId?: string,
): string {
  assertAddressable(source, target.range);
  const raw = source.slice(target.range.start, target.range.end);
  // Optimistic copy must not reuse the source block marker id.
  const content = raw.replace(BLOCK_MARKER_RE, "").trimEnd();
  return insertAfterBlock(source, target, content, blockId);
}

/** Marked when the caller minted a temporary id, bare otherwise. */
function insertionFor(
  content: string,
  type: ArtifactBlockType,
  blockId: string | undefined,
): string {
  return blockId ? markedBlock(blockId, content, type) : content;
}

function siblingSeparator(type: ArtifactBlockType): string {
  // Paragraphs need a blank line or CommonMark merges them into one block.
  return type === "paragraph" ? "\n\n" : "\n";
}

function replaceRange(source: string, range: MarkdownRange, content: string): string {
  if (
    range.start < 0 ||
    range.end > source.length ||
    range.start > range.end
  ) {
    // Returning `source` unchanged here made a stale range look like a click
    // that did nothing: no edit, no error, no retry (plan §8). Callers catch
    // this and surface a retryable message instead.
    throw new StaleBlockRangeError(range, source.length);
  }
  return source.slice(0, range.start) + content + source.slice(range.end);
}
