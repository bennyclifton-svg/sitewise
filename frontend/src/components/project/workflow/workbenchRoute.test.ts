import { describe, expect, it } from "vitest";

import {
  readWorkbenchWorkflow,
  workbenchSearchFor,
} from "@/components/project/workflow/workbenchRoute";

describe("workbenchRoute", () => {
  it("reads a known workbench workflow from the query string", () => {
    expect(readWorkbenchWorkflow("?workflow=cost-plan")).toBe("cost-plan");
    expect(readWorkbenchWorkflow("workflow=create-pmp")).toBe("create-pmp");
    expect(readWorkbenchWorkflow("?workflow=program")).toBe("program");
    expect(readWorkbenchWorkflow("?workflow=project-profile")).toBe(
      "project-profile",
    );
    expect(readWorkbenchWorkflow("?workflow=procurement-requests")).toBe(
      "procurement-requests",
    );
  });

  it("ignores unknown or missing workflow values", () => {
    expect(readWorkbenchWorkflow("")).toBeNull();
    expect(readWorkbenchWorkflow("?workflow=procurement")).toBeNull();
    expect(readWorkbenchWorkflow("?artefact=draft-1")).toBeNull();
  });

  it("builds a workbench search string and clears artefact deep-link params", () => {
    expect(workbenchSearchFor("cost-plan")).toBe("?workflow=cost-plan");
    expect(
      workbenchSearchFor(
        "cost-plan",
        "?artefact=draft-1&workflow=create-pmp&revision=3",
      ),
    ).toBe("?workflow=cost-plan");
  });
});
