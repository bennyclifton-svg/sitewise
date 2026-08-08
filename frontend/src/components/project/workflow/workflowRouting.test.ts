import { describe, expect, it } from "vitest";

import { resolveWorkflowTileId } from "@/components/project/workflow/workflowRouting";

describe("resolveWorkflowTileId", () => {
  it("routes procurement drafting to the Request for Tender tile", () => {
    expect(resolveWorkflowTileId(["consultant_procurement"])).toBe(
      "procurement-requests",
    );
    expect(resolveWorkflowTileId(["contractor_eoi"])).toBe(
      "procurement-requests",
    );
    expect(resolveWorkflowTileId(["rft"])).toBe("procurement-requests");
    expect(resolveWorkflowTileId(["rfq"])).toBe("procurement-requests");
  });

  it("keeps tender evaluation on Tender Comparison", () => {
    expect(resolveWorkflowTileId(["tender_evaluation"])).toBe("procurement");
  });
});
