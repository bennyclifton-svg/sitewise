import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StreamingIndicator } from "@/components/chat/StreamingIndicator";

describe("StreamingIndicator", () => {
  it("shows the default writing state with six trace points", () => {
    const { container } = render(<StreamingIndicator />);

    expect(screen.getByRole("status")).toHaveTextContent("Pi is writing");
    expect(container.querySelectorAll(".streaming-trace__point")).toHaveLength(6);
  });

  it("uses a live status message when one is available", () => {
    render(<StreamingIndicator message="Checking the tender schedule" />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking the tender schedule",
    );
  });
});
