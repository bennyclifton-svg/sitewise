import { describe, expect, it } from "vitest";

import { classifyChatError, toUiMessage } from "@/lib/chat-ui";

describe("classifyChatError", () => {
  it.each([
    ["429 rate limit exceeded", "rate_limit"],
    ["tool failed: start_tender_comparison", "tool"],
    ["partial pipeline incomplete", "partial_pipeline"],
  ] as const)("classifies %s", (message, kind) => {
    expect(classifyChatError(new Error(message)).kind).toBe(kind);
  });
});

describe("toUiMessage", () => {
  it("rehydrates sanitized terminal artefact events", () => {
    const message = toUiMessage({
      id: "message-1",
      role: "assistant",
      content: "Done",
      created_at: "2026-07-19T00:00:00Z",
      message_data: {
        agent: {
          terminalEvents: [
            {
              kind: "artefact",
              title: "Project plan",
              projectId: "project-1",
              draftId: "draft-2",
              workflowType: "create_pmp",
              version: 2,
            },
          ],
        },
      },
    });

    expect(message.parts).toContainEqual({
      type: "data-clerk-status",
      data: expect.objectContaining({ draftId: "draft-2", version: 2 }),
    });
  });
});
