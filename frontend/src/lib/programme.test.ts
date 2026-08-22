import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  DEFAULT_PROGRAMME_SCALE,
  formatCompactDate,
  formatDayMonth,
  formatMonthLetter,
  formatMonthYear,
  formatQuarterLabel,
  formatWeekOfMonth,
  applyProgrammeOperationsLocally,
  coalesceProgrammeOperations,
  insertAfterProgrammeHeading,
  stripProgrammeSectionBody,
  isLinked,
  previousProgrammeKey,
  programmeActivitySpan,
  programmeBulkDeleteOperations,
  programmeHeaderLayers,
  ganttLinkPath,
  programmeLinkWouldCycle,
  programmeLinks,
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
    expect(formatCompactDate("2026-08-16")).toBe("16 Aug 26");
    expect(formatQuarterLabel("2026-08-16")).toBe("Q3 2026");
    expect(formatMonthLetter("2026-08-16")).toBe("A");
    expect(formatWeekOfMonth("2026-08-01")).toBe("1");
    expect(formatWeekOfMonth("2026-08-16")).toBe("3");
    expect(formatWeekOfMonth("2026-08-31")).toBe("5");
    expect(
      programmeScaleBands("2026-08-16", "2026-11-14", "month").map((band) => band.label),
    ).toEqual(["Aug 2026", "Sept 2026", "Oct 2026", "Nov 2026"]);
    expect(
      programmeScaleBands("2026-08-16", "2027-02-01", "quarter").map((band) => band.label),
    ).toEqual(["Q3 2026", "Q4 2026", "Q1 2027"]);
    expect(programmeWeekTicks("2026-08-16", "2026-08-30")[0]?.label).toBe("16 Aug");
  });

  it("builds a two-row header with compact labels that fit the available width", () => {
    const spaciousWeek = programmeHeaderLayers("2026-08-16", "2026-09-27", "week", 18);
    expect(spaciousWeek.major.map((band) => band.label)).toEqual(["Aug 2026", "Sep"]);
    expect(spaciousWeek.minor.map((band) => band.label)).toEqual([
      "16 Aug",
      "23 Aug",
      "30 Aug",
      "6 Sept",
      "13 Sept",
      "20 Sept",
    ]);

    const fittedMonth = programmeHeaderLayers("2026-08-16", "2028-01-13", "month", 0.5);
    expect(fittedMonth.major.map((band) => band.label)).toEqual(["2026", "2027"]);
    expect(fittedMonth.minor.map((band) => band.label)).toEqual([
      "A",
      "Se",
      "Oc",
      "No",
      "De",
      "Ja",
      "Fe",
      "Mr",
      "Ap",
      "My",
      "Jn",
      "Jl",
      "Au",
      "Se",
      "Oc",
      "No",
      "De",
    ]);

    const fittedWeek = programmeHeaderLayers("2026-08-16", "2028-01-13", "week", 0.5);
    expect(fittedWeek.major.map((band) => band.label)[0]).toMatch(/^Q3/);
    expect(fittedWeek.minor.every((band) => /^\d{1,2}$/.test(band.label))).toBe(true);

    const fittedQuarter = programmeHeaderLayers("2026-08-16", "2028-01-13", "quarter", 0.5);
    expect(fittedQuarter.major.map((band) => band.label)).toEqual(["2026", "2027"]);
    expect(fittedQuarter.minor.map((band) => band.label)).toEqual([
      "Q3",
      "Q4",
      "Q1",
      "Q2",
      "Q3",
      "Q4",
    ]);
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

  it("draws a single finish-to-start segment that always touches both bars", () => {
    function row(
      key: string,
      start: string,
      days: number,
      predecessor: string | null,
      kind: "stage" | "activity" | "milestone" = "activity",
    ) {
      return {
        activity_key: key,
        kind,
        parent_key: null,
        name: key,
        display_order: 0,
        start_date: start,
        duration_days: days,
        finish_date: addDays(start, days),
        predecessor_key: predecessor,
        lag_days: 0,
        assumption: true,
        notes: "",
      };
    }
    const sequential = [
      row("a", "2026-08-16", 90, null, "stage"),
      row("b", "2026-11-14", 60, "a"),
    ];
    const gapped = [
      row("a", "2026-08-16", 30, null),
      row("b", "2026-10-16", 30, "a"),
    ];
    const overlapping = [
      row("a", "2026-08-16", 90, null),
      row("b", "2026-09-16", 30, "a"),
    ];
    const skipped = [
      row("a", "2026-08-16", 14, null),
      row("mid", "2026-08-20", 7, null),
      row("b", "2026-08-30", 14, "a"),
    ];
    const milestone = [
      row("a", "2026-08-16", 0, null, "milestone"),
      row("b", "2026-08-16", 10, "a"),
    ];
    const missing = [row("b", "2026-08-16", 10, "gone")];

    const seq = programmeLinks(sequential, "2026-08-16");
    expect(seq).toEqual([
      { key: "a->b", fromOffset: 90, toOffset: 90, fromIndex: 0, toIndex: 1 },
    ]);
    expect(programmeActivitySpan("2026-08-16", sequential[0]).end).toBe(seq[0]?.fromOffset);
    expect(programmeActivitySpan("2026-08-16", sequential[1]).start).toBe(seq[0]?.toOffset);
    expect(ganttLinkPath(seq[0]!, 24, 12, 1)).toBe("M 90 12 V 36");
    expect(ganttLinkPath(seq[0]!, 24, 12, 2)).toBe("M 180 12 V 36");

    const gap = programmeLinks(gapped, "2026-08-16");
    expect(gap[0]).toMatchObject({ fromOffset: 30, toOffset: 61, fromIndex: 0, toIndex: 1 });
    expect(ganttLinkPath(gap[0]!, 24, 12, 1)).toBe("M 30 12 H 38 V 36 H 61");

    const overlap = programmeLinks(overlapping, "2026-08-16");
    expect(overlap[0]?.fromOffset).toBeGreaterThan(overlap[0]!.toOffset);
    expect(ganttLinkPath(overlap[0]!, 24, 12, 1)).toBe(
      `M ${overlap[0]!.fromOffset} 12 H ${overlap[0]!.fromOffset + 8} V 36 H ${overlap[0]!.toOffset}`,
    );

    const skip = programmeLinks(skipped, "2026-08-16");
    expect(skip[0]).toMatchObject({ fromIndex: 0, toIndex: 2 });
    expect(ganttLinkPath(skip[0]!, 24, 12, 1)).toBe("M 14 12 V 60");

    expect(programmeLinks(milestone, "2026-08-16")[0]).toMatchObject({
      fromOffset: 0,
      toOffset: 0,
    });
    expect(programmeLinks(missing, "2026-08-16")).toEqual([]);
  });

  it("inserts a figure under the Programme heading", () => {
    const markdown = "# Plan\n\n## Programme\n\nDates TBC.\n";
    expect(insertAfterProgrammeHeading(markdown, "<svg></svg>")).toContain(
      "## Programme\n\n<svg></svg>\n\nDates TBC.",
    );
  });

  it("strips leftover Programme section prose and tables", () => {
    const markdown = [
      "# Plan",
      "",
      "## Programme",
      "",
      "The project is currently in brief planning.",
      "",
      "| Sub-milestone | Status |",
      "| --- | --- |",
      "| Setup | Active |",
      "",
      "## Cost Planning",
      "",
      "Budget follows.",
      "",
    ].join("\n");
    expect(stripProgrammeSectionBody(markdown)).toBe(
      [
        "# Plan",
        "",
        "## Programme",
        "",
        "## Cost Planning",
        "",
        "Budget follows.",
        "",
      ].join("\n"),
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
