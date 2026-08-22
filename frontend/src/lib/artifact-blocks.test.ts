import { describe, expect, it } from "vitest";

import {
  deleteBlock,
  duplicateBlock,
  insertAfterBlock,
  insertBeforeBlock,
  markedBlock,
  newTemporaryBlockId,
  replaceBlock,
  swapTemporaryBlockIds,
  StaleBlockRangeError,
  type ArtifactBlockTarget,
} from "@/lib/artifact-blocks";

const listSource = "Before\n\n- Item\n\nAfter";
const listTarget: ArtifactBlockTarget = {
  type: "list_item",
  range: { start: 8, end: 14 },
  sectionStart: 0,
};

describe("artifact block operations", () => {
  it("centralises replace, insert, duplicate, and delete", () => {
    expect(replaceBlock(listSource, listTarget, "- Revised")).toContain("- Revised");
    expect(insertBeforeBlock(listSource, listTarget, "- Above")).toContain("- Above\n- Item");
    expect(insertAfterBlock(listSource, listTarget, "- Below")).toContain("- Item\n- Below");
    expect(duplicateBlock(listSource, listTarget).match(/- Item/g)).toHaveLength(2);
    expect(deleteBlock(listSource, listTarget)).not.toContain("- Item");
  });

  it("duplicates paragraphs with a blank-line separator so they stay distinct blocks", () => {
    const source = "Intro\n\nFirst paragraph.\n\nOutro";
    const target: ArtifactBlockTarget = {
      type: "paragraph",
      range: {
        start: source.indexOf("First paragraph."),
        end: source.indexOf("First paragraph.") + "First paragraph.".length,
      },
      sectionStart: 0,
    };

    const duplicated = duplicateBlock(source, target);
    expect(duplicated).toContain("First paragraph.\n\nFirst paragraph.");
    expect(duplicated.split("First paragraph.")).toHaveLength(3);
  });

  it("deletes a table row without leaving a blank line that splits the GFM table", () => {
    const marker = "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->";
    const source = [
      "## Project Summary",
      "",
      "| Field | Detail | Citation |",
      "| --- | --- | --- |",
      "| Project | Walsh2 |  |",
      `| Address | 42 Hargrave Street | [1] |${marker}`,
      "| Owner | David and Emma Walsh | [1] |",
      "| Description | Terrace renovation | [1] |",
      "",
    ].join("\n");
    const row = `| Address | 42 Hargrave Street | [1] |${marker}`;
    const start = source.indexOf(row);
    const target: ArtifactBlockTarget = {
      type: "table_row",
      range: { start, end: start + row.length },
      sectionStart: 0,
    };

    const deleted = deleteBlock(source, target);
    expect(deleted).not.toContain("Address");
    expect(deleted).toContain(
      "| Project | Walsh2 |  |\n| Owner | David and Emma Walsh | [1] |",
    );
    expect(deleted).not.toContain("\n\n| Owner |");
  });

  it("strips block markers from optimistic duplicates", () => {
    const marker = "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->";
    const source = `${marker}\nFirst paragraph.`;
    const target: ArtifactBlockTarget = {
      type: "paragraph",
      range: { start: 0, end: source.length },
      sectionStart: 0,
    };

    const duplicated = duplicateBlock(source, target);
    expect(duplicated.match(/blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/g)).toHaveLength(1);
    expect(duplicated).toContain("First paragraph.\n\nFirst paragraph.");
  });

  describe("stale ranges", () => {
    const source = "Intro\n\nFirst paragraph.\n\nOutro";
    const stale = (): ArtifactBlockTarget => ({
      type: "paragraph",
      range: { start: 7, end: source.length + 40 },
      sectionStart: 0,
    });

    it("raises instead of silently returning the document unchanged", () => {
      // Plan §8: a no-op looked like "the click did nothing" to the user.
      expect(() => replaceBlock(source, stale(), "New text")).toThrow(
        StaleBlockRangeError,
      );
    });

    it("raises for inserts and deletes against a stale range too", () => {
      expect(() => insertAfterBlock(source, stale(), "New")).toThrow(
        StaleBlockRangeError,
      );
      expect(() => insertBeforeBlock(source, stale(), "New")).toThrow(
        StaleBlockRangeError,
      );
      expect(() => deleteBlock(source, stale())).toThrow(StaleBlockRangeError);
    });

    it("carries the offending range for diagnostics", () => {
      try {
        replaceBlock(source, stale(), "New text");
        expect.unreachable("should have thrown");
      } catch (error) {
        expect(error).toBeInstanceOf(StaleBlockRangeError);
        expect((error as StaleBlockRangeError).range).toEqual({
          start: 7,
          end: source.length + 40,
        });
      }
    });
  });
});

describe("temporary block ids", () => {
  const SERVER_ID = `blk_${"b".repeat(32)}`;

  it("mints a tmp_ id that cannot be mistaken for a server block id", () => {
    const id = newTemporaryBlockId();
    expect(id).toMatch(/^tmp_[0-9a-f]{8}$/);
    expect(id).not.toBe(newTemporaryBlockId());
  });

  it("marks an inserted list item with the temporary id", () => {
    expect(insertAfterBlock(listSource, listTarget, "- Below", "tmp_1a2b3c4d")).toContain(
      "- Item\n- Below <!-- clerk:block id=tmp_1a2b3c4d -->",
    );
    expect(insertBeforeBlock(listSource, listTarget, "- Above", "tmp_1a2b3c4d")).toContain(
      "- Above <!-- clerk:block id=tmp_1a2b3c4d -->\n- Item",
    );
  });

  it("places the marker exactly where the server places it, per block type", () => {
    // Byte-identical to `_marked` in backend/app/projects/artefact_blocks.py:
    // the optimistic string is hashed against the server's own body.
    expect(markedBlock("tmp_1a2b3c4d", "| A | B |", "table_row")).toBe(
      "| A | B |<!-- clerk:block id=tmp_1a2b3c4d -->",
    );
    expect(markedBlock("tmp_1a2b3c4d", "- Item", "list_item")).toBe(
      "- Item <!-- clerk:block id=tmp_1a2b3c4d -->",
    );
    expect(markedBlock("tmp_1a2b3c4d", "Body text.", "paragraph")).toBe(
      "<!-- clerk:block id=tmp_1a2b3c4d -->\nBody text.",
    );
  });

  it("marks an optimistic duplicate with the temporary id and drops the source id", () => {
    const marker = "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->";
    const source = `Before\n\n- Item ${marker}\n\nAfter`;
    const start = source.indexOf("- Item");
    const target: ArtifactBlockTarget = {
      type: "list_item",
      range: { start, end: start + `- Item ${marker}`.length },
      sectionStart: 0,
    };

    const duplicated = duplicateBlock(source, target, "tmp_1a2b3c4d");
    expect(duplicated).toContain(
      `- Item ${marker}\n- Item <!-- clerk:block id=tmp_1a2b3c4d -->`,
    );
    expect(duplicated.match(/blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/g)).toHaveLength(1);
  });

  it("swaps the temporary id for the server block id in place", () => {
    const existing = `blk_${"a".repeat(32)}`;
    const markdown = [
      `- First <!-- clerk:block id=${existing} -->`,
      "- New <!-- clerk:block id=tmp_1a2b3c4d -->",
    ].join("\n");

    expect(swapTemporaryBlockIds(markdown, [existing, SERVER_ID])).toBe(
      [
        `- First <!-- clerk:block id=${existing} -->`,
        `- New <!-- clerk:block id=${SERVER_ID} -->`,
      ].join("\n"),
    );
  });

  it("leaves markdown untouched when it carries no temporary id", () => {
    const markdown = `- First <!-- clerk:block id=blk_${"a".repeat(32)} -->`;
    expect(swapTemporaryBlockIds(markdown, [SERVER_ID])).toBe(markdown);
  });

  it("leaves the temporary marker alone when the server named no new block", () => {
    const markdown = "- New <!-- clerk:block id=tmp_1a2b3c4d -->";
    expect(swapTemporaryBlockIds(markdown, [])).toBe(markdown);
  });
});
