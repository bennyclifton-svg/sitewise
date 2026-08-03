import { describe, expect, it } from "vitest";

import type { ToolStatusEvent } from "@/lib/chat-events";
import {
  formatToolActivityLabel,
  toolActivityLines,
} from "@/lib/tool-activity";

describe("formatToolActivityLabel", () => {
  it("keeps backend messages that already include a document subject", () => {
    const event: ToolStatusEvent = {
      kind: "tool",
      tool: "find_document_text",
      state: "running",
      message: "Searching · L09 CC Plans - 02 Site Plan.pdf",
    };

    expect(formatToolActivityLabel(event)).toBe(
      "Searching · L09 CC Plans - 02 Site Plan.pdf",
    );
  });

  it("appends document filenames when the message has no subject", () => {
    const event: ToolStatusEvent = {
      kind: "tool",
      tool: "find_document_text",
      state: "done",
      message: "Searched documents",
      documents: [
        "L09 CC Plans - 02 Site Plan.pdf",
        "L09 CC Plans - 04 First Floor.pdf",
      ],
    };

    expect(formatToolActivityLabel(event)).toBe(
      "Searched documents · L09 CC Plans - 02 Site Plan.pdf, L09 CC Plans - 04 First Floor.pdf",
    );
  });
});

describe("toolActivityLines", () => {
  it("collapses a running/done pair into one line", () => {
    const events: ToolStatusEvent[] = [
      {
        kind: "tool",
        tool: "find_document_text",
        state: "running",
        message: "Searching · L09 CC Plans - 02 Site Plan.pdf",
      },
      {
        kind: "tool",
        tool: "find_document_text",
        state: "done",
        message: "Searched · L09 CC Plans - 02 Site Plan.pdf",
        documents: ["L09 CC Plans - 02 Site Plan.pdf"],
      },
      {
        kind: "tool",
        tool: "find_document_text",
        state: "running",
        message: "Searching · L09 CC Plans - 04 First Floor.pdf",
      },
      {
        kind: "tool",
        tool: "find_document_text",
        state: "done",
        message: "Searched · L09 CC Plans - 04 First Floor.pdf",
        documents: ["L09 CC Plans - 04 First Floor.pdf"],
      },
    ];

    const lines = toolActivityLines(events);

    expect(lines).toHaveLength(2);
    expect(lines[0]).toMatchObject({
      state: "done",
      label: "Searched · L09 CC Plans - 02 Site Plan.pdf",
    });
    expect(lines[1]).toMatchObject({
      state: "done",
      label: "Searched · L09 CC Plans - 04 First Floor.pdf",
    });
  });

  it("keeps a running line visible until done arrives", () => {
    const events: ToolStatusEvent[] = [
      {
        kind: "tool",
        tool: "search_documents",
        state: "running",
        message: "Searching · “gross floor area”",
      },
    ];

    expect(toolActivityLines(events)).toEqual([
      {
        id: "search_documents-0-running",
        state: "running",
        label: "Searching · “gross floor area”",
        detail: "Searching · “gross floor area”",
      },
    ]);
  });
});
