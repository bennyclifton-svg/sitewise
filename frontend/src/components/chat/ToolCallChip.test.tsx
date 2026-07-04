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

  it("shows stage progress when the event carries percent and stage", () => {
    render(
      <ToolCallChip
        event={{
          ...baseEvent,
          tool: "get_comparison_status",
          state: "done",
          message: "Checked comparison progress",
          stage: "qa",
          percent: 42.9,
          doneUnits: 6,
          totalUnits: 14,
        }}
      />,
    );

    const chip = screen.getByRole("button", {
      name: /done get_comparison_status/i,
    });
    expect(chip).toHaveTextContent("43%");
  });

  it("shows the stage name in the expanded detail when present", async () => {
    render(
      <ToolCallChip
        event={{
          ...baseEvent,
          tool: "get_comparison_status",
          state: "done",
          message: "Checked comparison progress",
          stage: "qa",
          percent: 42.9,
        }}
      />,
    );

    const chip = screen.getByRole("button", {
      name: /done get_comparison_status/i,
    });
    await userEvent.click(chip);
    expect(screen.getByText(/stage: qa/i)).toBeInTheDocument();
  });

  it("omits the progress badge when the event carries no percent", () => {
    render(<ToolCallChip event={baseEvent} />);

    const chip = screen.getByRole("button", {
      name: /running list_tender_comparisons/i,
    });
    expect(chip).not.toHaveTextContent("%");
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
