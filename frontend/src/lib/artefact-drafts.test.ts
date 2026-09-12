import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/http";
import {
  applyArtefactDeleted,
  isDraftNotFoundError,
  isPmpWorkflowType,
  missingDraftDeleteResult,
  repositoryArtefactDrafts,
} from "@/lib/artefact-drafts";
import type { DraftArtifactSummary } from "@/lib/types/project";

function draft(
  overrides: Partial<DraftArtifactSummary> = {},
): DraftArtifactSummary {
  return {
    id: "draft-1",
    project_id: "project-1",
    workflow_type: "create_pmp",
    version: 1,
    status: "draft",
    title: "Project Management Plan",
    workspace_path: "04-projects/merricks/00-brief-pmp/PMP.md",
    author_user_id: "user-1",
    model: null,
    runtime: "clerk-sitewise-create-pmp",
    created_at: "2026-07-18T10:09:29.000Z",
    updated_at: "2026-07-18T10:09:29.000Z",
    ...overrides,
  };
}

describe("isPmpWorkflowType", () => {
  it("treats create and update as one plan lineage", () => {
    expect(isPmpWorkflowType("create_pmp")).toBe(true);
    expect(isPmpWorkflowType("update_pmp")).toBe(true);
    expect(isPmpWorkflowType("create_cost_plan")).toBe(false);
  });
});

describe("repositoryArtefactDrafts", () => {
  it("lists one project management plan when create and update both have v1", () => {
    const created = draft({ id: "pmp-create", workflow_type: "create_pmp", version: 1 });
    const updated = draft({
      id: "pmp-update",
      workflow_type: "update_pmp",
      version: 1,
      updated_at: "2026-08-02T08:24:52.000Z",
    });

    const rows = repositoryArtefactDrafts([created, updated]);

    expect(rows).toEqual([updated]);
  });

  it("does not list the same draft twice when it is stored under two keys", () => {
    const pmp = draft();

    expect(repositoryArtefactDrafts([pmp, pmp])).toEqual([pmp]);
  });

  it("keeps distinct generated artefacts and drops sort-files manifests", () => {
    const pmp = draft();
    const cost = draft({
      id: "cost-1",
      workflow_type: "create_cost_plan",
      title: "Project Cost Plan",
      version: 2,
    });
    const sort = draft({
      id: "sort-1",
      workflow_type: "sort_files",
      title: "Intake manifest v01",
    });

    const rows = repositoryArtefactDrafts([pmp, cost, sort, null]);

    expect(rows.map((row) => row.id).sort()).toEqual(["cost-1", "draft-1"]);
  });
});

describe("applyArtefactDeleted", () => {
  it("clears every project-plan key instead of leaving a duplicate v1 row", () => {
    const pmp = draft();
    const current = {
      create_pmp: pmp,
      update_pmp: { ...pmp, workflow_type: "update_pmp" as const },
      create_cost_plan: draft({
        id: "cost-1",
        workflow_type: "create_cost_plan",
        title: "Project Cost Plan",
      }),
    };

    const next = applyArtefactDeleted(current, {
      deleted_id: pmp.id,
      workflow_type: "create_pmp",
      latest_draft: null,
    });

    expect(next.create_pmp).toBeUndefined();
    expect(next.update_pmp).toBeUndefined();
    expect(next.create_cost_plan?.id).toBe("cost-1");
    expect(repositoryArtefactDrafts(Object.values(next))).toEqual([
      current.create_cost_plan,
    ]);
  });

  it("stores a remaining plan under create_pmp only", () => {
    const remaining = draft({ id: "pmp-2", version: 2 });

    const next = applyArtefactDeleted(
      { create_pmp: draft(), update_pmp: remaining },
      {
        deleted_id: "draft-1",
        workflow_type: "update_pmp",
        latest_draft: remaining,
      },
    );

    expect(next.create_pmp).toEqual(remaining);
    expect(next.update_pmp).toBeUndefined();
    expect(repositoryArtefactDrafts(Object.values(next))).toEqual([remaining]);
  });
});

describe("missing draft delete", () => {
  it("recognises the repository 404 as already gone", () => {
    const error = new ApiError("Draft not found", { kind: "http", status: 404 });
    const pmp = draft();

    expect(isDraftNotFoundError(error)).toBe(true);
    expect(missingDraftDeleteResult(pmp)).toEqual({
      deleted_id: pmp.id,
      workflow_type: "create_pmp",
      latest_draft: null,
    });
  });
});
