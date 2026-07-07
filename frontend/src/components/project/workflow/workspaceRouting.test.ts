import { describe, expect, it } from "vitest";

import {
  findDraftByWorkspacePath,
  isConsultantProcurementWorkspaceFile,
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
});
