import { describe, expect, it } from "vitest";

import {
  deleteBlock,
  duplicateBlock,
  insertAfterBlock,
  insertBeforeBlock,
  replaceBlock,
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
});
