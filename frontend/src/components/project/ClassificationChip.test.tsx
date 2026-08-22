import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClassificationChip } from "@/components/project/ClassificationChip";

describe("ClassificationChip", () => {
  it("renders the current class and a low-confidence warning", () => {
    render(
      <ClassificationChip
        documentClass="report"
        documentSubject="structural"
        confidence={0.4}
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /document class/i }),
    ).toHaveTextContent("Report");
    expect(
      screen.getByRole("button", { name: /category/i }),
    ).toHaveTextContent("Structural");
    expect(screen.getByText(/low confidence/i)).toBeInTheDocument();
  });

  it("fires the mutation and reverts on a rejected promise", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn().mockRejectedValue(new Error("save failed"));

    render(
      <ClassificationChip
        documentClass="report"
        documentSubject="heritage"
        confidence={0.9}
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: /document class/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Certificate" }));

    expect(onChange).toHaveBeenCalledWith({
      documentClass: "certificate",
      documentSubject: "heritage",
    });

    expect(
      await screen.findByRole("button", { name: /document class/i }),
    ).toHaveTextContent("Report");
  });

  it("offers Architect as a category", async () => {
    const user = userEvent.setup();

    render(
      <ClassificationChip
        documentClass="drawing"
        documentSubject="none"
        category="Architectural"
        confidence={0.9}
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /category/i }),
    ).toHaveTextContent("Architect");

    await user.click(screen.getByRole("button", { name: /category/i }));
    expect(
      await screen.findByRole("menuitem", { name: "Mechanical" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Fire Services" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "BCA" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "ESD" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Interior Design" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Civil" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Civil Stormwater" })).not.toBeInTheDocument();
  });

  it("sorts both menus by their visible labels and gives them room for full names", async () => {
    const user = userEvent.setup();

    render(
      <ClassificationChip
        documentClass="statutory_instrument"
        documentSubject="quantity_surveyor"
        confidence={0.9}
        onChange={vi.fn()}
      />,
    );

    const classTrigger = screen.getByRole("button", { name: /document class/i });
    const categoryTrigger = screen.getByRole("button", { name: /category/i });

    expect(classTrigger).toHaveTextContent("Statutory Instrument");
    expect(categoryTrigger).toHaveTextContent("Quantity Surveyor");
    expect(classTrigger).toHaveClass("w-[11.5rem]");
    expect(categoryTrigger).toHaveClass("w-[11.5rem]");

    await user.click(classTrigger);
    const classLabels = screen
      .getAllByRole("menuitem")
      .map((item) => item.textContent?.trim() ?? "");
    expect(classLabels).toEqual(
      [...classLabels].sort((left, right) =>
        left.localeCompare(right, "en-AU", { numeric: true, sensitivity: "base" }),
      ),
    );

    await user.keyboard("{Escape}");
    await user.click(categoryTrigger);
    const categoryLabels = screen
      .getAllByRole("menuitem")
      .map((item) => item.textContent?.trim() ?? "");
    expect(categoryLabels).toEqual(
      [...categoryLabels].sort((left, right) =>
        left.localeCompare(right, "en-AU", { numeric: true, sensitivity: "base" }),
      ),
    );
  });
});
