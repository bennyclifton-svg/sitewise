import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ToolActivityFeed } from "@/components/chat/ToolActivityFeed";
import type { ToolStatusEvent } from "@/lib/chat-events";

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
  {
    kind: "tool",
    tool: "get_document",
    state: "running",
    message: "Reading · L09 CC Plans - 05 Elevations.pdf",
  },
  {
    kind: "tool",
    tool: "get_document",
    state: "done",
    message: "Read · L09 CC Plans - 05 Elevations.pdf",
    documents: ["L09 CC Plans - 05 Elevations.pdf"],
  },
];

describe("ToolActivityFeed", () => {
  it("shows a quiet two-line ticker with document names, not tool-name chips", () => {
    render(<ToolActivityFeed events={events} />);

    const feed = screen.getByLabelText("Tool activity");
    expect(feed).toHaveTextContent("L09 CC Plans - 04 First Floor.pdf");
    expect(feed).toHaveTextContent("L09 CC Plans - 05 Elevations.pdf");
    expect(feed).not.toHaveTextContent("find_document_text");
    expect(screen.queryByRole("button", { name: /find_document_text/i })).toBeNull();
  });

  it("expands to the full quiet log", async () => {
    render(<ToolActivityFeed events={events} />);

    await userEvent.click(screen.getByRole("button", { name: /show all/i }));
    expect(screen.getByLabelText("Tool activity")).toHaveTextContent(
      "L09 CC Plans - 02 Site Plan.pdf",
    );
    expect(screen.getByRole("button", { name: /hide log/i })).toBeInTheDocument();
  });
});
