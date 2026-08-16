import { beforeEach, describe, expect, it } from "vitest";

import {
  explorerExpandedPathsKey,
  findDraftByWorkspacePath,
  isDraftArtifactWorkspaceFile,
  isConsultantProcurementWorkspaceFile,
  isCostPlanWorkspaceFile,
  isContractorEoiWorkspaceFile,
  isTradeProcurementWorkspaceFile,
  readExplorerExpandedPaths,
  writeExplorerExpandedPaths,
} from "@/components/project/workflow/workspaceRouting";
import type { DraftArtifactSummary } from "@/lib/types/project";

const structuralDraft: DraftArtifactSummary = {
  id: "draft-1",
  project_id: "project-1",
  workflow_type: "consultant_procurement_structural_engineer",
  version: 1,
  status: "draft",
  title: "Request for Fee Proposal - Structural engineer",
  workspace_path:
    "04-projects/walsh-reno/02-consultant/consultant_procurement_structural_engineer_v01.draft.md",
  author_user_id: "user-1",
  model: null,
  runtime: "clerk-consultant-procurement",
  created_at: "2026-07-06T10:00:00.000Z",
  updated_at: "2026-07-06T10:00:00.000Z",
};

const costPlanDraft: DraftArtifactSummary = {
  id: "draft-2",
  project_id: "project-1",
  workflow_type: "create_cost_plan",
  version: 10,
  status: "draft",
  title: "Project Cost Plan",
  workspace_path: "04-projects/walsh-reno/01-cost/cost_plan_v10.md",
  author_user_id: "user-1",
  model: null,
  runtime: "clerk-cost-plan",
  created_at: "2026-08-02T10:00:00.000Z",
  updated_at: "2026-08-02T10:00:00.000Z",
};

describe("isCostPlanWorkspaceFile", () => {
  it("matches the workbook export", () => {
    expect(
      isCostPlanWorkspaceFile(
        "04-projects/walsh-reno/01-cost/Cost_Plan_v10.draft.xlsx",
      ),
    ).toBe(true);
  });
});

describe("isConsultantProcurementWorkspaceFile", () => {
  it("matches consultant procurement draft paths", () => {
    expect(
      isConsultantProcurementWorkspaceFile(
        "04-projects/walsh-reno/02-consultant/consultant_procurement_structural_engineer_v01.draft.md",
      ),
    ).toBe(true);
  });

  it("does not match source consultant correspondence", () => {
    expect(
      isConsultantProcurementWorkspaceFile(
        "04-projects/walsh-reno/02-consultant/architect/02-fee-proposal-atelier-north.md",
      ),
    ).toBe(false);
  });
});

describe("isContractorEoiWorkspaceFile", () => {
  it("matches contractor EOI draft paths", () => {
    expect(
      isContractorEoiWorkspaceFile(
        "04-projects/walsh-reno/02-procurement/contractor_eoi_main_works_v01.draft.md",
      ),
    ).toBe(true);
  });

  it("does not match consultant procurement paths", () => {
    expect(
      isContractorEoiWorkspaceFile(structuralDraft.workspace_path),
    ).toBe(false);
  });
});

describe("isTradeProcurementWorkspaceFile", () => {
  const rftPath =
    "04-projects/walsh-reno/05-procurement/electrical/02-tender-pack/electrical_rft_v01.draft.md";

  it("matches trade RFT and RFQ draft paths", () => {
    expect(isTradeProcurementWorkspaceFile(rftPath)).toBe(true);
    expect(
      isTradeProcurementWorkspaceFile(
        rftPath.replace("_rft_", "_rfq_"),
      ),
    ).toBe(true);
  });

  it("recognises every generated draft family", () => {
    expect(isDraftArtifactWorkspaceFile(rftPath)).toBe(true);
    expect(isDraftArtifactWorkspaceFile(structuralDraft.workspace_path)).toBe(true);
    expect(
      isDraftArtifactWorkspaceFile(
        "04-projects/walsh-reno/03-design/window-schedule.md",
      ),
    ).toBe(false);
  });
});

describe("findDraftByWorkspacePath", () => {
  it("returns the draft summary for a generated workspace path", () => {
    expect(
      findDraftByWorkspacePath(
        {
          create_pmp: null,
          consultant_procurement_structural_engineer: structuralDraft,
        },
        structuralDraft.workspace_path,
      ),
    ).toEqual(structuralDraft);
  });

  it("resolves a Cost Plan workbook to its draft revision", () => {
    expect(
      findDraftByWorkspacePath(
        { create_cost_plan: costPlanDraft },
        "04-projects/walsh-reno/01-cost/Cost_Plan_v10.draft.xlsx",
      ),
    ).toEqual(costPlanDraft);
  });
});

describe("explorer expanded-path persistence", () => {
  const projectId = "project-1";

  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts collapsed when nothing is stored", () => {
    expect(readExplorerExpandedPaths(projectId).size).toBe(0);
  });

  it("round-trips expanded folders for one project", () => {
    writeExplorerExpandedPaths(projectId, new Set(["04-projects/demo/01-cost"]));

    expect([...readExplorerExpandedPaths(projectId)]).toEqual([
      "04-projects/demo/01-cost",
    ]);
    expect(window.localStorage.getItem(explorerExpandedPathsKey(projectId))).toBe(
      JSON.stringify(["04-projects/demo/01-cost"]),
    );
  });

  it("keeps projects isolated and treats invalid storage as collapsed", () => {
    writeExplorerExpandedPaths(projectId, new Set(["04-projects/demo/01-cost"]));
    window.localStorage.setItem(explorerExpandedPathsKey("project-2"), "{not json");

    expect(readExplorerExpandedPaths("project-2").size).toBe(0);
    expect([...readExplorerExpandedPaths(projectId)]).toEqual([
      "04-projects/demo/01-cost",
    ]);
  });

  it("clears storage when every folder is collapsed", () => {
    writeExplorerExpandedPaths(projectId, new Set(["04-projects/demo/01-cost"]));
    writeExplorerExpandedPaths(projectId, new Set());

    expect(window.localStorage.getItem(explorerExpandedPathsKey(projectId))).toBeNull();
  });
});
