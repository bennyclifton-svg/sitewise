import { describe, expect, it } from "vitest";

import {
  compareProcurementRequests,
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
      "Consultant · Structural engineer · v3",
    );
  });

  it("orders open-document options by kind then discipline", () => {
    const requests = [
      { kind: "trade_rft", target_name: "Main works" },
      { kind: "consultant_rfp", target_name: "Certifier" },
      { kind: "trade_rfq", target_name: "Windows" },
      { kind: "consultant_rfp", target_name: "Architect" },
    ] as ProcurementRequest[];
    expect(
      [...requests].sort(compareProcurementRequests).map((request) =>
        requestOptionLabel({
          ...request,
          revision: 1,
          current_draft: null,
        } as ProcurementRequest),
      ),
    ).toEqual([
      "Consultant · Architect · v1",
      "Consultant · Certifier · v1",
      "Supplier quote · Windows · v1",
      "Trade package · Main works · v1",
    ]);
  });
});
