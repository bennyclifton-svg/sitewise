import { describe, expect, it } from "vitest";

import {
  briefTableLayoutFromHeaders,
  extractCitationTokens,
  planningTableLayoutFromHeaders,
  pmpRegisterTableLayoutFromHeaders,
  stripCitationTokens,
} from "@/lib/pmp-register-tables";

describe("briefTableLayoutFromHeaders", () => {
  it("drops Basis / source from the five-column exclusions table and appends a citation column", () => {
    const layout = briefTableLayoutFromHeaders([
      "Item",
      "Position",
      "Basis / source",
      "Owner",
      "Verification action",
    ]);
    expect(layout).toEqual({
      dropColumnIndexes: [2],
      citationColumnIndex: null,
      appendCitation: true,
      blankCitationHeader: true,
    });
  });

  it("keeps a four-column brief table and only appends citation", () => {
    const layout = briefTableLayoutFromHeaders([
      "Item",
      "Position",
      "Owner",
      "Verification action",
    ]);
    expect(layout?.dropColumnIndexes).toEqual([]);
    expect(layout?.appendCitation).toBe(true);
  });

  it("uses an existing trailing citation column without appending another", () => {
    const layout = briefTableLayoutFromHeaders([
      "Item",
      "Position",
      "Owner",
      "Verification action",
      "Citation",
    ]);
    expect(layout?.dropColumnIndexes).toEqual([]);
    expect(layout?.citationColumnIndex).toBe(4);
    expect(layout?.appendCitation).toBe(false);
    expect(layout?.blankCitationHeader).toBe(true);
  });

  it("ignores FFE and ordinary item tables", () => {
    expect(
      briefTableLayoutFromHeaders(["Item", "Location", "Finish", "Comment"]),
    ).toBeNull();
    expect(
      briefTableLayoutFromHeaders(["Item", "Owner", "Status", "Due basis", "Next action"]),
    ).toBeNull();
  });
});

describe("planningTableLayoutFromHeaders", () => {
  it("appends a citation column to the planning register", () => {
    const layout = planningTableLayoutFromHeaders([
      "Approval / compliance item",
      "Status",
      "Basis",
      "Next action",
    ]);
    expect(layout).toEqual({
      dropColumnIndexes: [],
      citationColumnIndex: null,
      appendCitation: true,
      blankCitationHeader: true,
    });
  });

  it("recognises the shorter authority-gate table", () => {
    const layout = planningTableLayoutFromHeaders([
      "Authority / compliance gate",
      "Status",
      "Verification action",
    ]);
    expect(layout?.appendCitation).toBe(true);
  });

  it("does not treat consultants as a planning table", () => {
    expect(
      planningTableLayoutFromHeaders([
        "Discipline",
        "Firm",
        "Fee",
        "Status",
        "Citation",
      ]),
    ).toBeNull();
  });

  it("recognises the due-diligence checklist under Planning and Compliance", () => {
    const layout = planningTableLayoutFromHeaders([
      "Item",
      "Status",
      "Filing path",
      "Next action",
    ]);
    expect(layout?.appendCitation).toBe(true);
  });
});

describe("pmpRegisterTableLayoutFromHeaders", () => {
  it("appends a citation column to the programme milestone table", () => {
    expect(
      pmpRegisterTableLayoutFromHeaders(["Sub-milestone", "Control requirement"])
        ?.appendCitation,
    ).toBe(true);
    expect(
      pmpRegisterTableLayoutFromHeaders([
        "Milestone",
        "Status",
        "Basis",
        "Next action",
      ])?.appendCitation,
    ).toBe(true);
  });

  it("appends a citation column to Risks and Actions registers", () => {
    expect(
      pmpRegisterTableLayoutFromHeaders([
        "Risk",
        "Owner",
        "Mitigation / escalation",
      ])?.appendCitation,
    ).toBe(true);
    expect(
      pmpRegisterTableLayoutFromHeaders([
        "Item",
        "Owner",
        "Status",
        "Due basis",
        "Next action",
      ])?.appendCitation,
    ).toBe(true);
  });

  it("does not steal Brief, FFE or Consultants tables", () => {
    expect(
      pmpRegisterTableLayoutFromHeaders([
        "Item",
        "Position",
        "Owner",
        "Verification action",
      ]),
    ).toBeNull();
    expect(
      pmpRegisterTableLayoutFromHeaders(["Item", "Location", "Finish", "Comment"]),
    ).toBeNull();
    expect(
      pmpRegisterTableLayoutFromHeaders([
        "Discipline",
        "Firm",
        "Fee",
        "Status",
        "Citation",
      ]),
    ).toBeNull();
  });
});

describe("citation tokens", () => {
  it("lifts numbered citations out of mixed cell text", () => {
    expect(extractCitationTokens("Owner brief [1] and survey [3]")).toBe("[1] [3]");
    expect(stripCitationTokens("Owner brief [1] and survey [3]")).toBe(
      "Owner brief and survey",
    );
    expect(extractCitationTokens("No source")).toBe("");
    expect(stripCitationTokens("[2]")).toBe("");
  });
});
