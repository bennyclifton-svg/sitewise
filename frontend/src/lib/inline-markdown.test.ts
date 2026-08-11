import { describe, expect, it } from "vitest";

import { maskArtifactBlockMarkers } from "@/lib/artifact-markdown";
import { sourceRangeForRenderedBlock } from "@/lib/inline-markdown";

describe("sourceRangeForRenderedBlock", () => {
  it("maps marker-masked table rows when rendered length diverges", () => {
    const marker =
      "<!-- clerk:block id=blk_ade5ba1bfc81abd258442ace94e4a835 -->";
    const addressRow =
      `| Address | 82 Queen Street, Petersham NSW 2049 | [1] |${marker}`;
    const source = [
      "## Project Summary",
      "",
      "| Project | Petersham |  |",
      "| --- | --- | --- |",
      addressRow,
      "| Owner | JOINS WIN PTY LTD | [1] |",
      "",
      "## Governance",
      "",
      "```pmp-decision",
      '{"id":"a"}',
      "```",
      "",
      "```pmp-decision",
      '{"id":"b"}',
      "```",
      "",
      "## Later",
      "",
      "Tail.",
    ].join("\n");

    // Simulate decision-fence grouping changing overall length while Project
    // Summary row text (with markers masked to spaces) stays findable.
    const rendered = `${maskArtifactBlockMarkers(source)}\n\n<!-- length drift -->`;
    expect(rendered.length).not.toBe(source.length);

    const maskedAddress = maskArtifactBlockMarkers(addressRow);
    const start = rendered.indexOf(maskedAddress);
    expect(start).toBeGreaterThanOrEqual(0);

    const mapped = sourceRangeForRenderedBlock(source, rendered, {
      start,
      end: start + maskedAddress.length,
    });
    expect(mapped).toEqual({
      start: source.indexOf(addressRow),
      end: source.indexOf(addressRow) + addressRow.length,
    });
  });

  it("keeps equal-offset mapping when only markers are masked", () => {
    const marker =
      "<!-- clerk:block id=blk_9a7b77fe4970e4836f3c148540452ecf -->";
    const source = `| Owner | David Walsh | [1] |${marker}\n`;
    const rendered = maskArtifactBlockMarkers(source);
    expect(rendered.length).toBe(source.length);

    const mapped = sourceRangeForRenderedBlock(source, rendered, {
      start: 0,
      end: rendered.trimEnd().length,
    });
    expect(mapped).toEqual({ start: 0, end: rendered.trimEnd().length });
  });
});
