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

  describe("escaped pipes", () => {
    it("keeps an escaped pipe inside one cell instead of splitting the row", () => {
      const row = String.raw`| Architect | Design \| documentation | Appointed |`;
      expect(editableTableCells(row)).toEqual([
        "Architect",
        "Design | documentation",
        "Appointed",
      ]);
    });

    it("re-escapes pipes when formatting so the column count is stable", () => {
      expect(formatTableRow(["Architect", "Design | documentation", "Appointed"])).toBe(
        String.raw`| Architect | Design \| documentation | Appointed |`,
      );
    });

    it("round-trips a row containing an escaped pipe without gaining a column", () => {
      const row = String.raw`| Architect | Design \| documentation | Appointed |`;
      const cells = editableTableCells(row);
      expect(cells).toHaveLength(3);
      expect(formatTableRow(cells)).toBe(row);
    });

    it("round-trips a row whose cell ends with a literal backslash", () => {
      const row = String.raw`| Path | C:\\ | Done |`;
      const cells = editableTableCells(row);
      expect(cells).toHaveLength(3);
      expect(cells[1]).toBe("C:\\");
      expect(formatTableRow(cells)).toBe(row);
    });

    it("round-trips an escaped pipe alongside a provenance marker", () => {
      const marker = "<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->";
      const cells = editableTableCells(
        String.raw`| Scope | Fee \| disbursements |` + marker,
      );
      expect(cells).toEqual(["Scope", "Fee | disbursements"]);
      expect(formatTableRow(cells)).toBe(
        String.raw`| Scope | Fee \| disbursements |`,
      );
    });

    it("leaves rows without escapes byte-identical", () => {
      const row = "| Address | Paddington | [1] |";
      expect(formatTableRow(editableTableCells(row))).toBe(row);
    });
  });
});
