import { describe, expect, it } from "vitest";

import { buildLifecycleTiles } from "@/components/project/workflow/workflowTiles";
import type { ProjectDetail, WorkflowCapabilityMatrix } from "@/lib/types/project";

function projectWithCapabilities(
  capabilities: WorkflowCapabilityMatrix["capabilities"],
): ProjectDetail {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    slug: "test",
    title: "Test",
    workspace_path: "04-projects/test",
    phase: "brief-planning",
    archetype: null,
    building_class: "commercial",
    work_type: "new",
    user_role: "architect-pm",
    state: "VIC",
    profile_revision: 1,
    status: "active",
    overlay_status: { ready: true, missing: [], invalid: [] },
    updated_at: "2026-07-19T00:00:00Z",
    metadata: null,
    evidence_preview: null,
    risk_flags: [],
    workflow_capabilities: {
      schema_version: 1,
      snapshot_schema_version: 1,
      snapshot_content_fingerprint: "fingerprint",
      capabilities,
    },
  };
}

describe("buildLifecycleTiles workflow capabilities", () => {
  it("uses the shared capability result instead of overlay readiness", () => {
    const capabilities: WorkflowCapabilityMatrix["capabilities"] = {
      create_pmp: { status: "supported", reasons: [], required_fields: [] },
      create_cost_plan: {
        status: "unsupported",
        reasons: ["Residential reference data only."],
        required_fields: [],
      },
      tender_comparison: {
        status: "unsupported",
        reasons: ["Class 1a only."],
        required_fields: [],
      },
    };

    const tiles = buildLifecycleTiles({
      project: projectWithCapabilities(capabilities),
      latestDraft: null,
      latestCostPlanDraft: null,
      workflowError: null,
      costPlanWorkflowError: null,
      isRunningWorkflow: false,
      isRunningCostPlan: false,
    });

    expect(tiles.find((tile) => tile.id === "create-pmp")?.status).toBe("ready");
    expect(tiles.find((tile) => tile.id === "cost-plan")?.status).toBe("blocked");
    expect(tiles.find((tile) => tile.id === "procurement")?.status).toBe("blocked");
  });
});
