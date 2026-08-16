import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StreamingIndicator } from "@/components/chat/StreamingIndicator";

describe("StreamingIndicator", () => {
  it("shows the cube without a default writing label", () => {
    const { container } = render(<StreamingIndicator />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Working");
    expect(status).not.toHaveTextContent("Pi is writing");
    // One spinning cube (8 vertices).
    expect(container.querySelectorAll(".streaming-cube__point")).toHaveLength(8);
  });

  it("uses a live status message when one is available", () => {
    render(<StreamingIndicator message="Checking the tender schedule" />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Checking the tender schedule");
    expect(status.querySelector(".streaming-status-live")).toHaveTextContent(
      "Checking the tender schedule",
    );
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "Checking the tender schedule",
    );
  });

  it("can show a secondary description under the status message", () => {
    render(
      <StreamingIndicator
        message="Generating Project Plan…"
        description="Draft will open here when ready."
      />,
    );

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Generating Project Plan…");
    expect(status).toHaveTextContent("Draft will open here when ready.");
  });
});
