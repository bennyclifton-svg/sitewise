import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ToolCallChip } from "@/components/chat/ToolCallChip";
import type { ToolStatusEvent } from "@/lib/chat-events";

const baseEvent: ToolStatusEvent = {
  kind: "tool",
  tool: "list_tender_comparisons",
  state: "running",
  message: "Listing tender comparisons",
};

describe("ToolCallChip", () => {
  it.each(["running", "done", "error"] as const)("renders %s state", (state) => {
    render(<ToolCallChip event={{ ...baseEvent, state }} />);

    expect(
      screen.getByRole("button", {
        name: new RegExp(`^${state}`, "i"),
      }),
    ).toHaveTextContent("list_tender_comparisons");
  });

  it("expands detail on click", async () => {
    render(<ToolCallChip event={baseEvent} />);

    const chip = screen.getByRole("button", {
      name: /running list_tender_comparisons/i,
    });

    expect(chip).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(chip);
    expect(chip).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Listing tender comparisons")).toBeInTheDocument();
  });
});
