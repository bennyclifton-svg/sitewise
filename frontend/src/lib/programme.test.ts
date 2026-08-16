import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  DEFAULT_PROGRAMME_SCALE,
  formatDayMonth,
  formatMonthYear,
  formatQuarterLabel,
  applyProgrammeOperationsLocally,
  coalesceProgrammeOperations,
  insertAfterProgrammeHeading,
  isLinked,
  previousProgrammeKey,
  programmeBulkDeleteOperations,
  programmeLinkWouldCycle,
  programmeRowMove,
  programmeScaleBands,
  programmeSpan,
  programmeWeekTicks,
  type ProgrammeState,
} from "@/lib/programme";

describe("programme helpers", () => {
  it("exposes the default month scale", () => {
    expect(DEFAULT_PROGRAMME_SCALE).toBe("month");
  });

  it("omits children when a selected stage is also deleted", () => {
    expect(
      programmeBulkDeleteOperations(
        [
          {
            activity_key: "delivery",
            kind: "stage",
            parent_key: null,
            name: "Delivery",
            display_order: 0,
            start_date: "2027-01-13",
            duration_days: 365,
            finish_date: "2028-01-13",
            predecessor_key: null,
            lag_days: 0,
            assumption: true,
            notes: "",
          },
          {
            activity_key: "slab",
            kind: "activity",
            parent_key: "delivery",
            name: "Slab",
            display_order: 1,
            start_date: "2027-01-13",
            duration_days: 14,
            finish_date: "2027-01-27",
            predecessor_key: null,
            lag_days: 0,
            assumption: true,
            notes: "",
          },
          {
            activity_key: "planning",
            kind: "stage",
            parent_key: null,
            name: "Planning",
            display_order: 2,
            start_date: "2026-08-16",
            duration_days: 90,
            finish_date: "2026-11-14",
            predecessor_key: null,
            lag_days: 0,
            assumption: true,
            notes: "",
          },
        ],
        ["delivery", "slab", "planning"],
      ),
    ).toEqual([
      { operation: "DELETE", target_type: "stage", target_id: "delivery" },
      { operation: "DELETE", target_type: "stage", target_id: "planning" },
    ]);
  });

  it("treats a predecessor as linked", () => {
    expect(
      isLinked({
        activity_key: "delivery",
        kind: "stage",
        parent_key: null,
        name: "Delivery",
        display_order: 2,
        start_date: "2026-11-14",
        duration_days: 365,
        finish_date: "2027-11-14",
        predecessor_key: "procurement",
        lag_days: 0,
        assumption: true,
        notes: "",
      }),
    ).toBe(true);
  });

  it("adds calendar days", () => {
    expect(addDays("2026-08-16", 90)).toBe("2026-11-14");
    expect(daysBetween("2026-08-16", "2026-11-14")).toBe(90);
  });

  it("spans the earliest start and latest finish", () => {
    expect(
      programmeSpan([
        {
          activity_key: "planning",
          kind: "stage",
          parent_key: null,
          name: "Planning",
          display_order: 0,
          start_date: "2026-08-16",
          duration_days: 90,
          finish_date: "2026-11-14",
          predecessor_key: null,
          lag_days: 0,
          assumption: true,
          notes: "",
        },
        {
          activity_key: "delivery",
          kind: "stage",
          parent_key: null,
          name: "Delivery",
          display_order: 1,
          start_date: "2027-01-01",
          duration_days: 30,
          finish_date: "2027-01-31",
          predecessor_key: null,
          lag_days: 0,
          assumption: true,
          notes: "",
        },
      ]),
    ).toEqual({ start: "2026-08-16", end: "2027-01-31" });
  });

  it("labels axis bands by month or quarter, not raw ISO fragments", () => {
    expect(formatMonthYear("2026-08-16")).toBe("Aug 2026");
    expect(formatDayMonth("2026-08-16")).toBe("16 Aug");
    expect(formatQuarterLabel("2026-08-16")).toBe("Q3 2026");
    expect(
      programmeScaleBands("2026-08-16", "2026-11-14", "month").map((band) => band.label),
    ).toEqual(["Aug 2026", "Sept 2026", "Oct 2026", "Nov 2026"]);
    expect(
      programmeScaleBands("2026-08-16", "2027-02-01", "quarter").map((band) => band.label),
    ).toEqual(["Q3 2026", "Q4 2026", "Q1 2027"]);
    expect(programmeWeekTicks("2026-08-16", "2026-08-30")[0]?.label).toBe("16 Aug");
  });

  it("builds a MOVE only when the drop target changes order", () => {
    const rows = [
      {
        activity_key: "planning",
        kind: "stage" as const,
        parent_key: null,
        name: "Planning",
        display_order: 0,
        start_date: "2026-08-16",
        duration_days: 90,
        finish_date: "2026-11-14",
        predecessor_key: null,
        lag_days: 0,
        assumption: true,
        notes: "",
      },
      {
        activity_key: "delivery",
        kind: "stage" as const,
        parent_key: null,
        name: "Delivery",
        display_order: 1,
        start_date: "2027-01-01",
        duration_days: 30,
        finish_date: "2027-01-31",
        predecessor_key: null,
        lag_days: 0,
        assumption: true,
        notes: "",
      },
    ];
    expect(programmeRowMove(rows, "planning", "planning", "after")).toBeNull();
    expect(programmeRowMove(rows, "planning", "delivery", "before")).toBeNull();
    expect(programmeRowMove(rows, "planning", "delivery", "after")).toEqual({
      operation: "MOVE",
      target_type: "stage",
      target_id: "planning",
      reference_id: "delivery",
      placement: "after",
    });
  });

  it("links to the previous row and detects cycles", () => {
    const rows = [
      {
        activity_key: "planning",
        kind: "stage" as const,
        parent_key: null,
        name: "Planning",
        display_order: 0,
        start_date: "2026-08-16",
        duration_days: 90,
        finish_date: "2026-11-14",
        predecessor_key: null,
        lag_days: 0,
        assumption: true,
        notes: "",
      },
      {
        activity_key: "delivery",
        kind: "stage" as const,
        parent_key: null,
        name: "Delivery",
        display_order: 1,
        start_date: "2027-01-01",
        duration_days: 30,
        finish_date: "2027-01-31",
        predecessor_key: "planning",
        lag_days: 0,
        assumption: true,
        notes: "",
      },
    ];
    expect(previousProgrammeKey(rows, "delivery")).toBe("planning");
    expect(programmeLinkWouldCycle(rows, "planning", "delivery")).toBe(true);
    expect(programmeLinkWouldCycle(rows, "delivery", "planning")).toBe(false);
  });

  it("inserts a figure under the Programme heading", () => {
    const markdown = "# Plan\n\n## Programme\n\nDates TBC.\n";
    expect(insertAfterProgrammeHeading(markdown, "<svg></svg>")).toContain(
      "## Programme\n\n<svg></svg>\n\nDates TBC.",
    );
  });

  it("applies duration updates locally and coalesces repeated saves", () => {
    const current: ProgrammeState = {
      id: "prog-1",
      project_id: "project-1",
      version: 1,
      status: "proposed",
      view_scale: "month",
      pmp_embed_visible: true,
      activities: [
        {
          activity_key: "planning",
          kind: "stage",
          parent_key: null,
          name: "Planning",
          display_order: 0,
          start_date: "2026-08-16",
          duration_days: 90,
          finish_date: "2026-11-14",
          predecessor_key: null,
          lag_days: 0,
          assumption: true,
          notes: "",
        },
        {
          activity_key: "procurement",
          kind: "stage",
          parent_key: null,
          name: "Procurement",
          display_order: 1,
          start_date: "2026-11-14",
          duration_days: 60,
          finish_date: "2027-01-13",
          predecessor_key: "planning",
          lag_days: 0,
          assumption: true,
          notes: "",
        },
      ],
    };
    const next = applyProgrammeOperationsLocally(current, [
      {
        operation: "UPDATE",
        target_type: "stage",
        target_id: "planning",
        values: { duration_days: 95 },
      },
    ]);
    expect(next.activities[0]?.duration_days).toBe(95);
    expect(next.activities[0]?.finish_date).toBe("2026-11-19");
    expect(next.activities[1]?.start_date).toBe("2026-11-19");
    expect(
      coalesceProgrammeOperations([
        {
          operation: "UPDATE",
          target_type: "stage",
          target_id: "planning",
          values: { duration_days: 91 },
        },
        {
          operation: "UPDATE",
          target_type: "stage",
          target_id: "planning",
          values: { duration_days: 95 },
        },
      ]),
    ).toEqual([
      {
        operation: "UPDATE",
        target_type: "stage",
        target_id: "planning",
        values: { duration_days: 95 },
      },
    ]);
  });
});
