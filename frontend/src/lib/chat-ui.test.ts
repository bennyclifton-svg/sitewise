import { describe, expect, it } from "vitest";

import {
  classifyChatError,
  incompleteAgentTurnError,
  INTERRUPTED_TURN_MESSAGE,
  toUiMessage,
} from "@/lib/chat-ui";
import type { UIMessage } from "ai";

describe("classifyChatError", () => {
  it.each([
    ["429 rate limit exceeded", "rate_limit"],
    ["tool failed: start_tender_comparison", "tool"],
    ["partial pipeline incomplete", "partial_pipeline"],
    ["This turn was interrupted before Pi finished. Please try again.", "interrupted"],
    ["The operation was aborted.", "interrupted"],
    ["Agent turn cancelled.", "interrupted"],
  ] as const)("classifies %s", (message, kind) => {
    expect(classifyChatError(new Error(message)).kind).toBe(kind);
  });
});

describe("incompleteAgentTurnError", () => {
  const user: UIMessage = {
    id: "user-1",
    role: "user",
    parts: [{ type: "text", text: "Process the selected invoice." }],
  };

  it("returns an interrupted error when the latest user turn has no assistant text", () => {
    expect(incompleteAgentTurnError([user])?.message).toBe(INTERRUPTED_TURN_MESSAGE);
    expect(
      incompleteAgentTurnError([
        user,
        { id: "asst-1", role: "assistant", parts: [{ type: "text", text: "" }] },
      ])?.message,
    ).toBe(INTERRUPTED_TURN_MESSAGE);
  });

  it("is silent when the latest turn already has assistant text", () => {
    expect(
      incompleteAgentTurnError([
        user,
        {
          id: "asst-1",
          role: "assistant",
          parts: [{ type: "text", text: "Booked one invoice." }],
        },
      ]),
    ).toBeNull();
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
