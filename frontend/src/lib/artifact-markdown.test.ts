import { describe, expect, it } from "vitest";

import {
  maskArtifactBlockMarkers,
  stripArtifactBlockMarkers,
  splitTraceQa,
} from "@/lib/artifact-markdown";

const VALID_MARKER =
  "<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->";
const SHORT_MARKER =
  "<!-- clerk:block id=blk_dba9073a16ea8cddb7bc1e7117d5e43 -->";

it("groups review sections while preserving later editable offsets", () => {
  const source = "## Brief\nVisible.\n\n## Trace & QA\nAudit.\n\n## Profile basis\nProfile.\n\n## Profile clarifications\nQuestion.\n\n## Actions and decisions\nAction.\n\n## Costs\nBudget.";
  const result = splitTraceQa(source);
  expect(result.qa).toContain("Audit.");
  expect(result.profileBasis).toContain("Question.");
  expect(result.profileBasis).toContain("Profile.");
  expect(result.primary).not.toContain("Action.");
  expect(result.primary.indexOf("Budget.")).toBe(source.indexOf("Budget."));
});

describe("artifact block marker presentation", () => {
  it("masks valid and truncated markers without changing length", () => {
    const source = `Brief paragraph. ${SHORT_MARKER}`;
    const masked = maskArtifactBlockMarkers(source);
    expect(masked).toHaveLength(source.length);
    expect(masked).not.toContain("clerk:block");
    expect(maskArtifactBlockMarkers(VALID_MARKER)).toHaveLength(VALID_MARKER.length);
  });

  it("strips trailing and standalone markers from copied markdown", () => {
    const source = [
      VALID_MARKER,
      "Coordinate the issued design.",
      "",
      `Inclusions: kitchen. ${SHORT_MARKER}`,
    ].join("\n");

    const stripped = stripArtifactBlockMarkers(source);
    expect(stripped).toBe(
      "Coordinate the issued design.\n\nInclusions: kitchen.",
    );
  });
});
