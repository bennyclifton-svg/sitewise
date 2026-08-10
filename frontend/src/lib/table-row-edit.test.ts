import { describe, expect, it } from "vitest";

import {
  editableTableCells,
  expandRangeWithTrailingMarker,
  formatTableRow,
} from "@/lib/table-row-edit";

describe("table-row-edit", () => {
  it("expands a short row range so inserts land after the trailing marker", () => {
    const marker = "<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->";
    const row = `| Address | Bankstown | [1] |${marker}`;
    const source = `## Summary\n\n${row}\n| Owner | FULLERTON | [2] |`;
    const start = source.indexOf("| Address");
    const shortEnd = source.indexOf("<!--", start);
    const expanded = expandRangeWithTrailingMarker(source, {
      start,
      end: shortEnd,
    });
    expect(expanded.end).toBe(start + row.length);
  });

  it("parses visible cells and ignores provenance markers", () => {
    expect(
      editableTableCells(
        "| Address | Paddington |<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->",
      ),
    ).toEqual(["Address", "Paddington"]);
  });

  it("round-trips cell edits into a GFM row", () => {
    expect(formatTableRow(["Budget", "Partial"])).toBe("| Budget | Partial |");
  });

  it("expands a short row range to include a trailing provenance marker", () => {
    const marker = "<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->";
    const row = `| Address | Paddington |${marker}`;
    const source = `## Summary\n\n${row}\n`;
    const start = source.indexOf("| Address |");
    const shortEnd = start + "| Address | Paddington |".length;
    expect(expandRangeWithTrailingMarker(source, { start, end: shortEnd })).toEqual({
      start,
      end: start + row.length,
    });
  });
});
