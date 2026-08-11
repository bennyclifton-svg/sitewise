import type { MarkdownRange } from "@/lib/markdown-selection";
import { maskArtifactBlockMarkers } from "@/lib/artifact-markdown";

/** Convert the small, allowed rich-text surface back into inline Markdown. */
export function serializeInlineMarkdown(root: HTMLElement): string {
  return serializeNodes(root.childNodes)
    .replace(/\u00a0/g, " ")
    .replace(/\u200b/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function serializeNodes(nodes: NodeListOf<ChildNode> | NodeList): string {
  return Array.from(nodes, serializeNode).join("");
}

function serializeNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (!(node instanceof HTMLElement)) return "";

  const content = serializeNodes(node.childNodes);
  switch (node.tagName.toLowerCase()) {
    case "strong":
    case "b":
      return content ? `**${content}**` : "";
    case "em":
    case "i":
      return content ? `*${content}*` : "";
    case "del":
    case "s":
      return content ? `~~${content}~~` : "";
    case "code": {
      if (!content) return "";
      const fence = content.includes("`") ? "``" : "`";
      return `${fence}${content}${fence}`;
    }
    case "a": {
      const href = node.getAttribute("href");
      return href ? `[${content}](${href})` : content;
    }
    case "br":
      return "\n";
    case "div":
    case "p":
      return `${content}\n\n`;
    default:
      return content;
  }
}

/**
 * Renderer-only transforms can change offsets around decision controls. Map an
 * addressable rendered block back to the matching occurrence in canonical
 * Markdown before exposing it to a save operation.
 *
 * Provenance markers are masked to spaces in the rendered tree. When another
 * renderer-only transform also changes document length (e.g. grouping decision
 * fences), the equal-offset shortcut no longer applies — search the
 * marker-masked source so stamped table rows still resolve.
 */
export function sourceRangeForRenderedBlock(
  source: string,
  rendered: string,
  renderedRange: MarkdownRange,
): MarkdownRange | null {
  if (
    renderedRange.start < 0 ||
    renderedRange.end > rendered.length ||
    renderedRange.start >= renderedRange.end
  ) {
    return null;
  }

  const block = rendered.slice(renderedRange.start, renderedRange.end);
  if (!block) return null;
  const sourceBlock = source.slice(renderedRange.start, renderedRange.end);
  if (sourceBlock === block) {
    return { ...renderedRange };
  }
  if (
    source.length === rendered.length &&
    maskArtifactBlockMarkers(sourceBlock) === block
  ) {
    return { ...renderedRange };
  }

  let occurrence = 0;
  let cursor = 0;
  while (cursor < renderedRange.start) {
    const index = rendered.indexOf(block, cursor);
    if (index < 0 || index >= renderedRange.start) break;
    occurrence += 1;
    cursor = index + block.length;
  }

  // Masking preserves length, so offsets in masked source match canonical source.
  const searchableSource = maskArtifactBlockMarkers(source);
  let sourceStart = -1;
  cursor = 0;
  for (let index = 0; index <= occurrence; index += 1) {
    sourceStart = searchableSource.indexOf(block, cursor);
    if (sourceStart < 0) return null;
    cursor = sourceStart + block.length;
  }
  return { start: sourceStart, end: sourceStart + block.length };
}
