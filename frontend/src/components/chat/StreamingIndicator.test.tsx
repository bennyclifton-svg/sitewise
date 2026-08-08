import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StreamingIndicator } from "@/components/chat/StreamingIndicator";

describe("StreamingIndicator", () => {
  it("shows the default writing state with cube vertex points", () => {
    const { container } = render(<StreamingIndicator />);

    expect(screen.getByRole("status")).toHaveTextContent("Pi is writing");
    expect(container.querySelectorAll(".streaming-cube__point")).toHaveLength(8);
  });

  it("uses a live status message when one is available", () => {
    render(<StreamingIndicator message="Checking the tender schedule" />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking the tender schedule",
    );
  });
});
