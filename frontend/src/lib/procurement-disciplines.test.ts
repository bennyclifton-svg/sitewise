import { describe, expect, it } from "vitest";

import {
  compareProcurementRequests,
  disciplinesFromPmpMarkdown,
  latestRequest,
  latestRequestForKind,
  kindForTargetName,
  latestRequestForTab,
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

  it("marks supplier quotes in the collapsed trade-package chip list", () => {
    const request = {
      kind: "trade_rfq",
      target_name: "Windows",
      revision: 1,
      current_draft: { version: 1 },
    } as ProcurementRequest;
    expect(requestChipLabel(request)).toBe("Windows RFQ v1");
  });

  it("marks supplier quotes in the collapsed trade-package chip list", () => {
    const request = {
      kind: "trade_rfq",
      target_name: "Windows",
      revision: 1,
      current_draft: { version: 1 },
    } as ProcurementRequest;
    expect(requestChipLabel(request)).toBe("Windows RFQ v1");
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
      "Main works v1",
      "Windows RFQ v1",
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

  it("treats supplier quotes as trade-package tab items", () => {
    const rft = {
      id: "rft",
      kind: "trade_rft",
      target_name: "Main works",
      updated_at: "2026-08-10T00:00:00Z",
    } as ProcurementRequest;
    const rfq = {
      id: "rfq",
      kind: "trade_rfq",
      target_name: "Windows",
      updated_at: "2026-08-12T00:00:00Z",
    } as ProcurementRequest;
    expect(latestRequestForTab([rft, rfq], "trade_rft")?.id).toBe("rfq");
    expect(latestRequestForTab([rft, rfq], "consultant_rfp")).toBeNull();
  });

  it("routes known consultants to RFP and other names to RFT", () => {
    expect(kindForTargetName("Architect")).toBe("consultant_rfp");
    expect(kindForTargetName("Electrical services")).toBe("trade_rft");
    expect(
      kindForTargetName("Structural engineer", ["Structural engineer"]),
    ).toBe("consultant_rfp");
    expect(
      kindForTargetName("Architect", [], [
        { kind: "consultant_rfp", target_name: "Architect" } as ProcurementRequest,
      ]),
    ).toBe("consultant_rfp");
  });
});
