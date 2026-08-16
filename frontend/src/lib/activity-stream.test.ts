import { describe, expect, it } from "vitest";

import {
  STARTING_ACTIVITY_LABEL,
  buildActivityLines,
  formatWorkflowActivityLabel,
} from "@/lib/activity-stream";
import type { ToolStatusEvent } from "@/lib/chat-events";

describe("buildActivityLines", () => {
  it("merges tool steps and workflow progress into one stack", () => {
    const toolEvents: ToolStatusEvent[] = [
      {
        kind: "tool",
        tool: "search_documents",
        state: "done",
        message: "Searched · plant schedule.pdf",
        documents: ["plant schedule.pdf"],
      },
      {
        kind: "tool",
        tool: "get_document",
        state: "running",
        message: "Reading · plant schedule.pdf",
      },
    ];

    const lines = buildActivityLines({
      statusMessage: "Workflow queued",
      toolEvents,
      workflowLines: [
        {
          id: "workflow-1",
          label: "Queued Cost Plan…",
          state: "running",
        },
      ],
    });

    expect(lines.map((line) => line.label)).toEqual([
      "Searched · plant schedule.pdf",
      "Reading · plant schedule.pdf",
      "Queued Cost Plan…",
    ]);
  });

  it("keeps a concrete status message when nothing richer is available", () => {
    expect(
      buildActivityLines({ statusMessage: "Loading project context…" }).map(
        (line) => line.label,
      ),
    ).toEqual(["Loading project context…"]);
  });

  it("shows a starting line while busy before any real activity arrives", () => {
    expect(
      buildActivityLines({ busy: true }).map((line) => line.label),
    ).toEqual([STARTING_ACTIVITY_LABEL]);
  });

  it("drops the starting line once a tool or workflow line exists", () => {
    expect(
      buildActivityLines({
        busy: true,
        statusMessage: STARTING_ACTIVITY_LABEL,
        toolEvents: [
          {
            kind: "tool",
            tool: "search_documents",
            state: "running",
            message: "Searching project documents",
          },
        ],
      }).map((line) => line.label),
    ).toEqual(["Searching project documents"]);
  });
});

describe("formatWorkflowActivityLabel", () => {
  it("uses a queued cost-plan label instead of a generic workflow status", () => {
    expect(
      formatWorkflowActivityLabel({
        workflow_type: "create_cost_plan",
        state: "queued",
        progress: { percent: 0 },
      }),
    ).toBe("Queued Cost Plan…");
  });

  it("surfaces the active section while generating", () => {
    expect(
      formatWorkflowActivityLabel({
        workflow_type: "create_cost_plan",
        state: "running",
        progress: {
          stage: "section_started",
          active_section: "budget",
          sections: [
            { id: "budget", label: "Budget & rates", status: "generating" },
            { id: "risks", label: "Risks", status: "queued" },
          ],
        },
      }),
    ).toBe("Writing Budget & rates…");
  });
});
