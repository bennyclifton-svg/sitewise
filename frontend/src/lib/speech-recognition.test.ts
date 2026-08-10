import { describe, expect, it } from "vitest";

import { appendDictationTranscript } from "@/lib/speech-recognition";

describe("appendDictationTranscript", () => {
  it("returns the spoken text when the field is empty", () => {
    expect(appendDictationTranscript("", "  bearing capacity ")).toBe(
      "bearing capacity",
    );
  });

  it("adds a space when the current value has no trailing space", () => {
    expect(appendDictationTranscript("Check", "bearing capacity")).toBe(
      "Check bearing capacity",
    );
  });

  it("keeps an existing trailing space", () => {
    expect(appendDictationTranscript("Check ", "bearing capacity")).toBe(
      "Check bearing capacity",
    );
  });
});
