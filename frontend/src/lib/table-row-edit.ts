import type { MarkdownRange } from "@/lib/markdown-selection";

const BLOCK_MARKER_RE = /<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->/gi;
const TRAILING_BLOCK_MARKER_RE =
  /^(<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->)/i;

/** Split a GFM table row into visible cell texts, ignoring provenance markers. */
export function editableTableCells(sourceRow: string): string[] {
  const visible = sourceRow.replace(BLOCK_MARKER_RE, "").trim();
  const raw = visible.split("|").map((cell) => cell.trim());
  if (raw.length >= 2 && raw[0] === "" && raw[raw.length - 1] === "") {
    return raw.slice(1, -1);
  }
  return raw.filter((_, index, all) => !(index === 0 && all[0] === ""));
}

export function formatTableRow(cells: readonly string[]): string {
  const body = cells.map((cell) => cell.replace(/\s+/g, " ").trim()).join(" | ");
  return `| ${body} |`;
}

/**
 * Mdast table-row offsets sometimes end before an embedded provenance marker.
 * Expand so replaces/saves keep the marker attached to the row.
 */
export function expandRangeWithTrailingMarker(
  source: string,
  range: MarkdownRange,
): MarkdownRange {
  if (range.start < 0 || range.end < range.start || range.end > source.length) {
    return range;
  }
  if (BLOCK_MARKER_RE.test(source.slice(range.start, range.end))) {
    BLOCK_MARKER_RE.lastIndex = 0;
    return range;
  }
  BLOCK_MARKER_RE.lastIndex = 0;
  const trailing = source.slice(range.end).match(TRAILING_BLOCK_MARKER_RE);
  if (!trailing) return range;
  return { start: range.start, end: range.end + trailing[1].length };
}
