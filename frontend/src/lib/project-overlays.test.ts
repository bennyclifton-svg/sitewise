import { describe, expect, it } from "vitest";

import { overlayIssuesFromProfile } from "@/lib/project-overlays";

describe("overlayIssuesFromProfile", () => {
  it("reports each unset overlay field", () => {
    expect(overlayIssuesFromProfile({})).toEqual([
      { field: "building_class", value: null, reason: "missing" },
      { field: "work_type", value: null, reason: "missing" },
      { field: "state", value: null, reason: "missing" },
    ]);
  });

  it("is empty when state, class, and work type are set", () => {
    expect(
      overlayIssuesFromProfile({
        buildingClass: "infrastructure",
        workType: "refurb",
        state: "NSW",
      }),
    ).toEqual([]);
  });
});
