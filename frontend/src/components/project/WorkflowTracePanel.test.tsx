import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { formatMetadataSummary } from "@/lib/workflow-trace-format";

describe("formatMetadataSummary", () => {
  it("shows array lengths instead of joining evidence chunk refs", () => {
    const refs = Array.from({ length: 109 }, (_, index) =>
      [
        "project_evidence:04-projects/mosaic-apartments/_inbox/",
        `11049 E001 T${index}.pdf#chunk=e3bdc59a-13a8-52d7-a18e-4d019d142e9e`,
      ].join(""),
    );

    expect(
      formatMetadataSummary({
        backfilled_facts: [],
        added_evidence_refs: refs,
      }),
    ).toBe("backfilled_facts: 0 · added_evidence_refs: 109");
  });

  it("prefers scalar metadata and truncates long paths", () => {
    expect(
      formatMetadataSummary({
        model: "gpt-5.2",
        attempt: 1,
        added_evidence_refs: ["project_evidence:demo/brief.pdf#chunk=1"],
      }),
    ).toBe("model: gpt-5.2 · attempt: 1");

    expect(
      formatMetadataSummary({
        ledger_path:
          "_sitewise/evidence/ledger_2026-08-11T01-26-13Z_a1b2c3d4e5f6.json",
      }),
    ).toBe("ledger_path: _sitewise/evidence/ledger_2026-08-11T01-26-13…");
  });
});

describe("WorkflowTracePanel", () => {
  it("keeps the coverage advisory message readable beside compact metadata", () => {
    render(
      <WorkflowTracePanel
        trace={[
          {
            step: "coverage",
            status: "advisory",
            message:
              "Coverage advisory (not enforced): 0 evidence fact(s) remain outside the narrative body; merged 109 missing evidence ref(s).",
            metadata: {
              backfilled_facts: [],
              added_evidence_refs: Array.from(
                { length: 109 },
                (_, index) =>
                  `project_evidence:04-projects/demo/_inbox/file-${index}.pdf#chunk=abc`,
              ),
            },
          },
        ]}
      />,
    );

    expect(
      screen.getByText(/Coverage advisory \(not enforced\): 0 evidence fact/),
    ).toBeInTheDocument();
    expect(screen.getByText("backfilled_facts: 0 · added_evidence_refs: 109")).toBeInTheDocument();
    expect(screen.queryByText(/#chunk=/)).not.toBeInTheDocument();
  });
});
