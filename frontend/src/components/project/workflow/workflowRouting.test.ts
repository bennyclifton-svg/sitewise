import { describe, expect, it } from "vitest";

import { resolveWorkflowTileId } from "@/components/project/workflow/workflowRouting";

describe("resolveWorkflowTileId", () => {
  it("routes contractor EOIs to procurement", () => {
    expect(resolveWorkflowTileId(["contractor_eoi"])).toBe("procurement");
  });
});
