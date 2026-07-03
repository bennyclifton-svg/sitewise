import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

function HarnessSmoke() {
  return <p>Vitest is rendering Clerk.</p>;
}

describe("frontend test harness", () => {
  it("renders React components", () => {
    render(<HarnessSmoke />);

    expect(screen.getByText("Vitest is rendering Clerk.")).toBeInTheDocument();
  });
});
