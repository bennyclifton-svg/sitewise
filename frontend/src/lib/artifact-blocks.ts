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

const BLOCK_MARKER_RE = /<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->\s*/gi;

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

export function replaceBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
): string {
  return replaceRange(source, target.range, content);
}

export function insertBeforeBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
): string {
  return replaceRange(
    source,
    { start: target.range.start, end: target.range.start },
    `${content}${siblingSeparator(target.type)}`,
  );
}

export function insertAfterBlock(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
): string {
  return replaceRange(
    source,
    { start: target.range.end, end: target.range.end },
    `${siblingSeparator(target.type)}${content}`,
  );
}

export function deleteBlock(source: string, target: ArtifactBlockTarget): string {
  return replaceRange(source, target.range, "").replace(/\n{3,}/g, "\n\n");
}

export function duplicateBlock(source: string, target: ArtifactBlockTarget): string {
  const raw = source.slice(target.range.start, target.range.end);
  // Optimistic copy must not reuse the source block marker id.
  const content = raw.replace(BLOCK_MARKER_RE, "").trimEnd();
  return insertAfterBlock(source, target, content);
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
    return source;
  }
  return source.slice(0, range.start) + content + source.slice(range.end);
}
