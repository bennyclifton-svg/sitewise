import { describe, expect, it } from "vitest";

import {
  compareProcurementRequests,
  disciplinesFromPmpMarkdown,
  latestRequest,
  latestRequestForKind,
  mergeDisciplineOptions,
  requestChipLabel,
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

  it("extracts consultant disciplines when the register ends the document", () => {
    const markdown = `
## Consultants

| Discipline | Firm | Fee | Status | Citation |
| --- | --- | --- | --- | --- |
| Services engineer | Acme | — | Needed | [2] |
`;

    expect(disciplinesFromPmpMarkdown(markdown)).toEqual(["Services engineer"]);
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

  it("labels package chips with discipline and latest version", () => {
    const request = {
      kind: "consultant_rfp",
      target_name: "Structural engineer",
      revision: 1,
      current_draft: { version: 3 },
    } as ProcurementRequest;
    expect(requestChipLabel(request)).toBe("Structural engineer v3");
  });

  it("orders package chips by kind then discipline", () => {
    const requests = [
      { kind: "trade_rft", target_name: "Main works" },
      { kind: "consultant_rfp", target_name: "Certifier" },
      { kind: "trade_rfq", target_name: "Windows" },
      { kind: "consultant_rfp", target_name: "Architect" },
    ] as ProcurementRequest[];
    expect(
      [...requests].sort(compareProcurementRequests).map((request) =>
        requestChipLabel({
          ...request,
          revision: 1,
          current_draft: null,
        } as ProcurementRequest),
      ),
    ).toEqual([
      "Architect v1",
      "Certifier v1",
      "Windows v1",
      "Main works v1",
    ]);
  });

  it("picks the most recently updated request", () => {
    const older = {
      id: "architect",
      kind: "consultant_rfp",
      target_name: "Architect",
      updated_at: "2026-08-01T00:00:00Z",
    } as ProcurementRequest;
    const newer = {
      id: "structural",
      kind: "consultant_rfp",
      target_name: "Structural",
      updated_at: "2026-08-10T00:00:00Z",
    } as ProcurementRequest;
    expect(latestRequest([older, newer])?.id).toBe("structural");
    expect(latestRequestForKind([older, newer], "trade_rft")).toBeNull();
    expect(latestRequestForKind([older, newer], "consultant_rfp")?.id).toBe(
      "structural",
    );
  });
});
