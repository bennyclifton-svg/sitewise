import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";

import {
  applyDocumentSelectionEvent,
  documentSelectionFromPart,
  resourceFromPart,
  toolStatusFromPart,
  workflowRunFromPart,
  workflowRunsFromMessage,
} from "@/lib/chat-events";

type MessagePart = UIMessage["parts"][number];

describe("toolStatusFromPart", () => {
  it("carries progress fields when the backend includes them", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "tool",
        tool: "get_comparison_status",
        state: "done",
        message: "Checked comparison progress",
        stage: "qa",
        percent: 42.9,
        doneUnits: 6,
        totalUnits: 14,
      },
    } as MessagePart;

    const event = toolStatusFromPart(part);

    expect(event).toEqual({
      kind: "tool",
      tool: "get_comparison_status",
      state: "done",
      message: "Checked comparison progress",
      stage: "qa",
      percent: 42.9,
      doneUnits: 6,
      totalUnits: 14,
    });
  });

  it("omits progress fields when the backend does not send them", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "tool",
        tool: "list_tender_comparisons",
        state: "running",
        message: "Listing tender comparisons",
      },
    } as MessagePart;

    const event = toolStatusFromPart(part);

    expect(event).toEqual({
      kind: "tool",
      tool: "list_tender_comparisons",
      state: "running",
      message: "Listing tender comparisons",
    });
  });

  it("carries platform knowledge fields when the backend includes them", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "tool",
        tool: "read_platform_knowledge",
        state: "done",
        message: "Read platform knowledge",
        knowledge_path: "seed/nsw/residential-refurb.md",
        section_ids: ["brief", "budget"],
      },
    } as MessagePart;

    const event = toolStatusFromPart(part);

    expect(event).toEqual({
      kind: "tool",
      tool: "read_platform_knowledge",
      state: "done",
      message: "Read platform knowledge",
      knowledgePath: "seed/nsw/residential-refurb.md",
      sectionIds: ["brief", "budget"],
    });
  });

  it("carries document filenames from search tool status", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "tool",
        tool: "find_document_text",
        state: "done",
        message: "Searched · L09 CC Plans - 02 Site Plan.pdf",
        query: "gross floor area",
        documents: ["L09 CC Plans - 02 Site Plan.pdf"],
      },
    } as MessagePart;

    expect(toolStatusFromPart(part)).toEqual({
      kind: "tool",
      tool: "find_document_text",
      state: "done",
      message: "Searched · L09 CC Plans - 02 Site Plan.pdf",
      query: "gross floor area",
      documents: ["L09 CC Plans - 02 Site Plan.pdf"],
    });
  });
});

describe("resourceFromPart", () => {
  it("parses a project resource acknowledgement for exact cache updates", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "resource",
        projectId: "project-1",
        resourceType: "project_profile",
        resourceId: "project-1",
        action: "updated",
        revision: 4,
        changedFields: ["state"],
        clearedFields: [],
      },
    } as MessagePart;

    expect(resourceFromPart(part)).toEqual({
      kind: "resource",
      projectId: "project-1",
      resourceType: "project_profile",
      resourceId: "project-1",
      action: "updated",
      revision: 4,
      changedFields: ["state"],
      clearedFields: [],
    });
  });

  it("keeps workflowType on queued workflow_run resources", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "resource",
        projectId: "project-1",
        resourceType: "workflow_run",
        resourceId: "run-1",
        action: "queued",
        workflowType: "consultant_procurement",
        changedFields: [],
        clearedFields: [],
      },
    } as MessagePart;

    expect(resourceFromPart(part)).toEqual({
      kind: "resource",
      projectId: "project-1",
      resourceType: "workflow_run",
      resourceId: "run-1",
      action: "queued",
      changedFields: [],
      clearedFields: [],
      workflowType: "consultant_procurement",
    });
  });
});

describe("documentSelectionFromPart", () => {
  it("parses the authoritative register selection from the agent stream", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "document_selection",
        projectId: "project-1",
        action: "replace",
        requestedAction: "add",
        documentIds: ["document-201", "document-250"],
      },
    } as MessagePart;

    expect(documentSelectionFromPart(part)).toEqual({
      kind: "document_selection",
      projectId: "project-1",
      action: "replace",
      requestedAction: "add",
      documentIds: ["document-201", "document-250"],
    });
  });

  it("replaces the visible selection and ignores stale register ids", () => {
    const next = applyDocumentSelectionEvent(
      new Set(["document-130"]),
      {
        kind: "document_selection",
        projectId: "project-1",
        action: "replace",
        documentIds: ["document-201", "document-stale"],
      },
      ["document-130", "document-201", "document-250"],
    );

    expect([...next]).toEqual(["document-201"]);
  });

  it("clears the visible selection", () => {
    const next = applyDocumentSelectionEvent(
      new Set(["document-130"]),
      {
        kind: "document_selection",
        projectId: "project-1",
        action: "clear",
        documentIds: [],
      },
      ["document-130"],
    );

    expect(next.size).toBe(0);
  });
});

describe("workflowRunFromPart", () => {
  it("extracts a queued consultant procurement run", () => {
    const part = {
      type: "data-clerk-status",
      data: {
        kind: "resource",
        projectId: "project-1",
        resourceType: "workflow_run",
        resourceId: "run-99",
        action: "queued",
        workflowType: "consultant_procurement",
      },
    } as MessagePart;

    expect(workflowRunFromPart(part)).toEqual({
      kind: "workflow_run",
      projectId: "project-1",
      runId: "run-99",
      workflowType: "consultant_procurement",
      action: "queued",
    });
  });
});

describe("workflowRunsFromMessage", () => {
  it("dedupes run refs from assistant message parts", () => {
    const message = {
      id: "m1",
      role: "assistant",
      parts: [
        {
          type: "data-clerk-status",
          data: {
            kind: "resource",
            projectId: "project-1",
            resourceType: "workflow_run",
            resourceId: "run-1",
            action: "queued",
            workflowType: "consultant_procurement",
          },
        },
        {
          type: "data-clerk-status",
          data: {
            kind: "resource",
            projectId: "project-1",
            resourceType: "workflow_run",
            resourceId: "run-1",
            action: "queued",
            workflowType: "consultant_procurement",
          },
        },
      ],
    } as UIMessage;

    expect(workflowRunsFromMessage(message)).toEqual([
      {
        kind: "workflow_run",
        projectId: "project-1",
        runId: "run-1",
        workflowType: "consultant_procurement",
        action: "queued",
      },
    ]);
  });
});
