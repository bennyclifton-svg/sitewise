import type { MarkdownRange } from "@/lib/markdown-selection";

// `tmp_` ids are the client's own, worn by a block it has just inserted and
// not yet had named by the server. Cell editing must see through both.
const BLOCK_MARKER_RE =
  /<!--\s*clerk:block\s+id=(?:blk_[a-f0-9]{32}|tmp_[a-f0-9]{8})\s*-->/gi;
const TRAILING_BLOCK_MARKER_RE =
  /^(<!--\s*clerk:block\s+id=(?:blk_[a-f0-9]{32}|tmp_[a-f0-9]{8})\s*-->)/i;

/**
 * Split a GFM table row on unescaped pipes.
 *
 * `\|` is a pipe *inside* a cell, not a column boundary, and `\\` is a literal
 * backslash. Splitting on raw `"|"` turns a three-column row into four and
 * silently corrupts the table, so the walk below is deliberate rather than a
 * `split("|")`. Inverse of `escapeCellText`.
 */
function splitRowCells(visible: string): string[] {
  const cells: string[] = [];
  let current = "";
  for (let index = 0; index < visible.length; index += 1) {
    const char = visible[index];
    if (char === "\\") {
      const next = visible[index + 1];
      if (next === "|" || next === "\\") {
        current += next;
        index += 1;
        continue;
      }
      current += char;
      continue;
    }
    if (char === "|") {
      cells.push(current);
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current);
  return cells;
}

/** Escape a cell's text so it survives as one column. Inverse of `splitRowCells`. */
function escapeCellText(cell: string): string {
  return cell.replaceAll("\\", "\\\\").replaceAll("|", "\\|");
}

/** Split a GFM table row into visible cell texts, ignoring provenance markers. */
export function editableTableCells(sourceRow: string): string[] {
  const visible = sourceRow.replace(BLOCK_MARKER_RE, "").trim();
  const raw = splitRowCells(visible).map((cell) => cell.trim());
  if (raw.length >= 2 && raw[0] === "" && raw[raw.length - 1] === "") {
    return raw.slice(1, -1);
  }
  return raw.filter((_, index, all) => !(index === 0 && all[0] === ""));
}

export function formatTableRow(cells: readonly string[]): string {
  const body = cells
    .map((cell) => escapeCellText(cell.replace(/\s+/g, " ").trim()))
    .join(" | ");
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
