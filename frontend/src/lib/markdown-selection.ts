/**
 * Resolve a DOM selection inside rendered markdown to offsets in the source.
 *
 * Design decision D1: the DOM selection identifies *which block* the user
 * touched and nothing more. The quoted text is then sliced out of the source
 * markdown using that block's `data-md-start` / `data-md-end` offsets. Reading
 * `selection.toString()` and searching for it in the source would silently
 * produce wrong anchors wherever the renderer replaces source text with
 * synthesized elements — evidence badges in table cells, and `pmp-decision`
 * fences rendered as `DecisionControl`.
 */

export type MarkdownRange = {
  start: number;
  end: number;
};

export type MarkdownAnchor = MarkdownRange & {
  quotedText: string;
  rect: DOMRect;
};

export type MarkdownAnchorError = {
  error: string;
};

export type MarkdownAnchorResult = MarkdownAnchor | MarkdownAnchorError | null;

/** Blocks the tray must not annotate: decisions own their control; the tray owns itself. */
const SUPPRESSED_SELECTOR = "[data-decision-id],[data-instruction-ui]";
const BLOCK_SELECTOR = "[data-md-start]";

export function isAnchorError(
  result: MarkdownAnchorResult,
): result is MarkdownAnchorError {
  return result !== null && "error" in result;
}

function closestElement(node: Node | null, selector: string): HTMLElement | null {
  const element =
    node instanceof Element ? node : ((node?.parentElement ?? null) as Element | null);
  return element ? element.closest<HTMLElement>(selector) : null;
}

function offsetsOf(block: HTMLElement): MarkdownRange | null {
  const start = Number(block.getAttribute("data-md-start"));
  const end = Number(block.getAttribute("data-md-end"));
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  return { start, end };
}

export function resolveSelectionAnchor(
  selection: Selection | null,
  container: HTMLElement,
  source: string,
): MarkdownAnchorResult {
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  if (!selection.toString().trim()) return null;

  const { anchorNode, focusNode } = selection;
  if (!anchorNode || !focusNode) return null;
  if (!container.contains(anchorNode) || !container.contains(focusNode)) return null;

  if (
    closestElement(anchorNode, SUPPRESSED_SELECTOR) ||
    closestElement(focusNode, SUPPRESSED_SELECTOR)
  ) {
    return null;
  }

  const anchorBlock = closestElement(anchorNode, BLOCK_SELECTOR);
  const focusBlock = closestElement(focusNode, BLOCK_SELECTOR);
  if (!anchorBlock || !focusBlock) return null;

  const anchorRange = offsetsOf(anchorBlock);
  const focusRange = offsetsOf(focusBlock);
  if (!anchorRange || !focusRange) return null;

  const start = Math.min(anchorRange.start, focusRange.start);
  const end = Math.max(anchorRange.end, focusRange.end);
  if (start < 0 || end > source.length || start >= end) return null;

  const quotedText = source.slice(start, end);
  if (quotedText.includes("\n## ")) {
    return { error: "Select text within a single section." };
  }

  return {
    start,
    end,
    quotedText,
    rect: selection.getRangeAt(0).getBoundingClientRect(),
  };
}
