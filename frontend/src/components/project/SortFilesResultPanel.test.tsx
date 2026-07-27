import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";

describe("SortFilesResultPanel", () => {
  it("shows the complete document-control identity for each result", () => {
    render(
      <SortFilesResultPanel
        summary={{
          inspected: 1,
          moved: 1,
          unresolved: 0,
          refused: 0,
          already_filed: 0,
          skipped: 0,
        }}
        rows={[
          {
            source_path: "04-projects/demo/_inbox/HY-SK~1.PDF",
            filename: "HY-SK~1.PDF",
            outcome: "moved",
            destination_path:
              "04-projects/demo/03-design/hydraulic/HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF",
            destination_filename: "HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF",
            reason: "Classified and filed",
            document_number: "HY-SK-06",
            title: "ROOF DRAINAGE PLAN",
            revision: "P1",
            category: "Hydraulic",
          },
        ]}
      />,
    );

    expect(screen.getByText("ROOF DRAINAGE PLAN")).toBeInTheDocument();
    expect(screen.getByText("P1")).toBeInTheDocument();
  });
});
