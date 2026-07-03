import { describe, expect, it } from "vitest";

import { classifyChatError } from "@/lib/chat-ui";

describe("classifyChatError", () => {
  it.each([
    ["429 rate limit exceeded", "rate_limit"],
    ["tool failed: start_tender_comparison", "tool"],
    ["partial pipeline incomplete", "partial_pipeline"],
  ] as const)("classifies %s", (message, kind) => {
    expect(classifyChatError(new Error(message)).kind).toBe(kind);
  });
});
