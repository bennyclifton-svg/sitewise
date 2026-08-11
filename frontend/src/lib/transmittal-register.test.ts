import { describe, expect, it } from "vitest";

import {
  displayTransmittalHeading,
  isTransmittalHeading,
  matchTransmittalEvidenceIds,
  parseTransmittalRows,
} from "@/lib/transmittal-register";
import type { EvidencePreview } from "@/lib/types/project";

function evidence(
  partial: Partial<EvidencePreview> & Pick<EvidencePreview, "id" | "title">,
): EvidencePreview {
  return {
    filename: `${partial.title}.pdf`,
    relative_path: `04-projects/demo/${partial.filename ?? `${partial.title}.pdf`}`,
    source_type: "project_evidence",
    document_class: "drawing",
    excerpt: "",
    ...partial,
  };
}

describe("transmittal-register", () => {
  it("recognises legacy and new headings", () => {
    expect(isTransmittalHeading("Project Documents (2 documents)")).toBe(true);
    expect(isTransmittalHeading("Transmittal (1 document)")).toBe(true);
    expect(isTransmittalHeading("Citation key")).toBe(false);
    expect(displayTransmittalHeading("Project Documents (2 documents)")).toBe(
      "Transmittal (2 documents)",
    );
  });

  it("parses register rows and matches evidence", () => {
    const rows = parseTransmittalRows(
      [
        "# Request for Proposal",
        "",
        "## Project Documents (2 documents)",
        "",
        "| Document number | Title | Rev | Category |",
        "| --- | --- | --- | --- |",
        "| A001 | General arrangement | C | Architectural |",
        "| E001 | Electrical layout | B | Electrical |",
        "",
        "## Citation key",
      ].join("\n"),
    );

    expect(rows).toEqual([
      {
        documentNumber: "A001",
        title: "General arrangement",
        revision: "C",
        category: "Architectural",
      },
      {
        documentNumber: "E001",
        title: "Electrical layout",
        revision: "B",
        category: "Electrical",
      },
    ]);

    const ids = matchTransmittalEvidenceIds(rows, [
      evidence({
        id: "ev-a",
        title: "General arrangement",
        document_number: "A001",
        revision: "C",
      }),
      evidence({
        id: "ev-e",
        title: "Electrical layout",
        document_number: "E001",
        revision: "B",
      }),
      evidence({
        id: "ev-other",
        title: "Other",
        document_number: "X001",
      }),
    ]);

    expect(ids).toEqual(["ev-a", "ev-e"]);
  });
});
