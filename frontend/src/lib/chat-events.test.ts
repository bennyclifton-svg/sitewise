import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";

import { toolStatusFromPart } from "@/lib/chat-events";

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
});
