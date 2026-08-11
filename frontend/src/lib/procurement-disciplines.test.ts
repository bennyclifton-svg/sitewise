import { describe, expect, it } from "vitest";

import {
  disciplinesFromPmpMarkdown,
  mergeDisciplineOptions,
  requestOptionLabel,
} from "@/lib/procurement-disciplines";
import type { ProcurementRequest } from "@/lib/types/project";

describe("procurement-disciplines", () => {
  it("extracts consultant disciplines from the PMP register", () => {
    const markdown = `
## Consultants

| Discipline | Firm | Fee | Status | Citation |
| --- | --- | --- | --- | --- |
| Structural engineer | Acme | — | Needed | [2] |
| Certifier | — | — | Needed | — |
| Structural engineer | Acme | — | Needed | [2] |

## Programme
`;
    expect(disciplinesFromPmpMarkdown(markdown)).toEqual([
      "Structural engineer",
      "Certifier",
    ]);
  });

  it("prefers PMP disciplines ahead of fallbacks", () => {
    expect(
      mergeDisciplineOptions(
        ["Certifier"],
        ["Architect", "Certifier"],
        ["Structural engineer"],
      ),
    ).toEqual(["Certifier", "Structural engineer", "Architect"]);
  });

  it("labels open-document options with kind and latest version", () => {
    const request = {
      kind: "consultant_rfp",
      target_name: "Structural engineer",
      revision: 1,
      current_draft: { version: 3 },
    } as ProcurementRequest;
    expect(requestOptionLabel(request)).toBe(
      "Structural engineer · Consultant · v3",
    );
  });
});
