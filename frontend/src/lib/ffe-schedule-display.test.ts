import { describe, expect, it } from "vitest";

import {
  FFE_DECISION_MARKER_RE,
  ffeTableLayoutFromHeaders,
  foldFfeScheduleDecisions,
  formatFfeDecisionMarker,
  isFfeDecisionDuplicateRow,
  parseFfeDecisionMarker,
  presentFfeComment,
  presentFfeFinish,
  projectFfeScheduleRow,
  selectedFinishForItem,
} from "@/lib/ffe-schedule-display";

describe("foldFfeScheduleDecisions", () => {
  it("strips FFE-section decision fences without adding duplicate rows", () => {
    const markdown = `## Brief

Scope body.

## FFE Schedule

Finishes, Fixtures and Equipment (FFE) schedule.

| Item | Location | Qty | Finish | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Filtered tap | Kitchen | 1 | Chrome | Confirmed | — |
| External cladding | Extension | Not evidenced | Not evidenced | To be confirmed | Typical |

\`\`\`pmp-decision
{"id":"flooring-finish","section":"FFE Schedule","label":"Primary flooring finish","options":[{"value":"engineered","label":"Engineered timber"},{"value":"tile","label":"Ceramic / porcelain tile"}],"selected":"tile","source":"agent"}
\`\`\`

\`\`\`pmp-decision
{"id":"kitchen-benchtop","section":"FFE Schedule","label":"Kitchen benchtop","options":[{"value":"laminate","label":"Laminate"},{"value":"engineered_stone","label":"Engineered stone / quartz"}],"selected":"engineered_stone","source":"user"}
\`\`\`

## Consultants

Roster.
`;

    const result = foldFfeScheduleDecisions(markdown);

    expect(result.markdown).toContain("| Filtered tap | Kitchen | 1 | Chrome | Confirmed | — |");
    expect(result.markdown).toContain("| External cladding | Extension | Not evidenced | Not evidenced | To be confirmed | Typical |");
    expect(result.markdown).not.toContain("Primary flooring finish");
    expect(result.markdown).not.toContain("Kitchen benchtop");
    expect(result.markdown).not.toContain(formatFfeDecisionMarker("flooring-finish"));
    expect(result.markdown).not.toContain("```pmp-decision");
    expect(result.markdown).toContain("## Consultants");
    expect(result.foldedById.get("flooring-finish")?.selected).toBe("tile");
    expect(result.foldedById.get("kitchen-benchtop")?.source).toBe("user");
  });

  it("strips grouped decision fences under FFE Schedule", () => {
    const bodies = [
      JSON.stringify({
        id: "flooring-finish",
        label: "Primary flooring finish",
        options: [{ value: "tile", label: "Ceramic / porcelain tile" }],
        selected: "tile",
        source: "agent",
      }),
      JSON.stringify({
        id: "wet-area-finish",
        label: "Wet-area floor and wall finish",
        options: [{ value: "ceramic_tile", label: "Ceramic / porcelain tile" }],
        selected: "ceramic_tile",
        source: "agent",
      }),
    ];
    const markdown = `## FFE Schedule

| Item | Location | Qty | Finish | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| TBC — record finishes, fixtures and equipment selections | TBC | TBC | TBC | To be confirmed | — |

\`\`\`pmp-decision-group
${JSON.stringify(bodies)}
\`\`\`
`;

    const result = foldFfeScheduleDecisions(markdown);
    expect(result.markdown).not.toContain(formatFfeDecisionMarker("flooring-finish"));
    expect(result.markdown).not.toContain("```pmp-decision-group");
    expect(result.foldedById.size).toBe(2);
  });

  it("relocates legacy Brief finish decisions without inserting table rows", () => {
    const markdown = `## Brief

Scope body.

\`\`\`pmp-decision
{"id":"flooring-finish","section":"Brief and scope","label":"Primary flooring finish","options":[{"value":"tile","label":"Ceramic / porcelain tile"}],"selected":"tile","source":"agent"}
\`\`\`

\`\`\`pmp-decision
{"id":"dwelling-storeys","section":"Brief and scope","label":"Dwelling storeys","options":[{"value":"single_storey","label":"Single storey"}],"selected":"single_storey","source":"agent"}
\`\`\`

## FFE Schedule

| Item | Location | Qty | Finish | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Filtered tap | Kitchen | 1 | Chrome | Confirmed | — |
`;

    const result = foldFfeScheduleDecisions(markdown);
    expect(result.markdown).not.toContain("Primary flooring finish");
    expect(result.markdown).toContain("```pmp-decision");
    expect(result.markdown).toContain("dwelling-storeys");
    expect(result.markdown).not.toMatch(
      /## Brief[\s\S]*flooring-finish[\s\S]*## FFE Schedule/,
    );
    expect(result.foldedById.get("flooring-finish")?.selected).toBe("tile");
  });

  it("leaves non-FFE decision fences alone", () => {
    const markdown = `## Procurement

\`\`\`pmp-decision
{"id":"procurement-route","label":"Procurement route","options":[{"value":"traditional","label":"Traditional"}],"selected":"traditional","source":"agent"}
\`\`\`
`;
    const result = foldFfeScheduleDecisions(markdown);
    expect(result.markdown).toContain("```pmp-decision");
    expect(result.foldedById.size).toBe(0);
  });

  it("is a no-op when FFE Schedule has no decision fences", () => {
    const markdown = `## FFE Schedule

| Item | Location | Qty | Finish | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Bath | Ensuite | 1 | White | Confirmed | — |
`;
    const result = foldFfeScheduleDecisions(markdown);
    expect(result.markdown).toBe(markdown);
    expect(result.foldedById.size).toBe(0);
  });
});

describe("parseFfeDecisionMarker", () => {
  it("round-trips decision markers", () => {
    const marker = formatFfeDecisionMarker("flooring-finish");
    expect(parseFfeDecisionMarker(marker)).toBe("flooring-finish");
    expect(FFE_DECISION_MARKER_RE.test(marker)).toBe(true);
    expect(parseFfeDecisionMarker("Ceramic / porcelain tile")).toBeNull();
  });
});

describe("FFE presentation helpers", () => {
  it("maps a six-column header to Item, Location, Finish, Comment", () => {
    const layout = ffeTableLayoutFromHeaders([
      "Item",
      "Location",
      "Qty",
      "Finish",
      "Status",
      "Notes",
    ]);
    expect(layout).toEqual({
      dropColumnIndexes: [2, 4],
      finishColumnIndex: 3,
      commentColumnIndex: 5,
      citationColumnIndex: null,
      appendCitation: true,
      blankCitationHeader: true,
      renameHeaders: { notes: "Comment" },
    });
  });

  it("leaves an already-narrow FFE header alone", () => {
    const layout = ffeTableLayoutFromHeaders([
      "Item",
      "Location",
      "Finish",
      "Comment",
    ]);
    expect(layout?.dropColumnIndexes).toEqual([]);
    expect(layout?.finishColumnIndex).toBe(2);
    expect(layout?.appendCitation).toBe(true);
  });

  it("fills a placeholder Finish from the matching catalog selection", () => {
    const foldedById = new Map([
      [
        "external-cladding",
        {
          id: "external-cladding",
          label: "Primary external cladding",
          options: [{ value: "brick_veneer", label: "Brick veneer" }],
          selected: "brick_veneer",
          source: "agent" as const,
        },
      ],
    ]);
    expect(selectedFinishForItem("External cladding", foldedById)).toBe(
      "Brick veneer",
    );
    expect(
      presentFfeFinish("External cladding", "Not evidenced", foldedById),
    ).toBe("Brick veneer");
    expect(presentFfeFinish("Filtered tap", "Chrome", foldedById)).toBe("Chrome");
    expect(presentFfeComment("Not evidenced")).toBe("");
    expect(presentFfeComment("Owner selection")).toBe("Owner selection");
  });

  it("hides legacy primary-finish duplicate rows", () => {
    expect(isFfeDecisionDuplicateRow("Primary external cladding")).toBe(true);
    expect(isFfeDecisionDuplicateRow("External cladding")).toBe(false);
  });

  it("projects a six-column row for editing and writes it back", () => {
    const projected = projectFfeScheduleRow(
      "| External cladding | Extension | Not evidenced | Not evidenced | To be confirmed | Typical |",
    );
    expect(projected.cells).toEqual([
      "External cladding",
      "Extension",
      "Not evidenced",
      "Typical",
    ]);
    expect(projected.commit(["External cladding", "Extension", "Brick veneer", ""])).toBe(
      "| External cladding | Extension | Not evidenced | Brick veneer | To be confirmed |  |",
    );
  });
});
