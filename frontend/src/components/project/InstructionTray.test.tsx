import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InstructionTray } from "@/components/project/InstructionTray";
import { SelectionInstructionCard } from "@/components/project/SelectionInstructionCard";
import {
  clearTray,
  dropStaleTrays,
  loadStaleTray,
  loadTray,
  saveTray,
  type InstructionItem,
} from "@/lib/instruction-tray";

const DRAFT_ID = "draft-1";

function item(overrides: Partial<InstructionItem> = {}): InstructionItem {
  return {
    id: "item-1",
    kind: "revise",
    anchorStart: 40,
    anchorEnd: 66,
    quotedText: "single-stage invited tender",
    instruction: "make it two-stage",
    sectionHeading: "Procurement posture",
    ...overrides,
  };
}

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("instruction tray persistence", () => {
  it("round-trips a tray for one draft version", () => {
    saveTray(DRAFT_ID, 3, [item()]);

    expect(loadTray(DRAFT_ID, 3)).toEqual([item()]);
  });

  it("keeps versions isolated so v3 anchors never leak into v4", () => {
    saveTray(DRAFT_ID, 3, [item()]);

    expect(loadTray(DRAFT_ID, 4)).toEqual([]);
  });

  it("clears a tray", () => {
    saveTray(DRAFT_ID, 3, [item()]);
    clearTray(DRAFT_ID, 3);

    expect(loadTray(DRAFT_ID, 3)).toEqual([]);
  });

  it("saving an empty list removes the entry", () => {
    saveTray(DRAFT_ID, 3, [item()]);
    saveTray(DRAFT_ID, 3, []);

    expect(window.sessionStorage.getItem("sitewise:tray:draft-1:v3")).toBeNull();
  });

  it("surfaces an older version's tray as a rebase candidate", () => {
    saveTray(DRAFT_ID, 2, [item({ id: "old-1" })]);
    saveTray(DRAFT_ID, 3, [item({ id: "older-kept" })]);

    expect(loadStaleTray(DRAFT_ID, 5)).toEqual({
      version: 3,
      items: [item({ id: "older-kept" })],
    });
  });

  it("does not report the current version as stale", () => {
    saveTray(DRAFT_ID, 4, [item()]);

    expect(loadStaleTray(DRAFT_ID, 4)).toBeNull();
  });

  it("does not report another draft's tray as stale", () => {
    saveTray("draft-2", 2, [item()]);

    expect(loadStaleTray(DRAFT_ID, 4)).toBeNull();
  });

  it("drops stale trays without touching the current one", () => {
    saveTray(DRAFT_ID, 2, [item({ id: "old" })]);
    saveTray(DRAFT_ID, 4, [item({ id: "current" })]);

    dropStaleTrays(DRAFT_ID, 4);

    expect(loadStaleTray(DRAFT_ID, 4)).toBeNull();
    expect(loadTray(DRAFT_ID, 4)).toHaveLength(1);
  });

  it("survives corrupt storage without throwing", () => {
    window.sessionStorage.setItem("sitewise:tray:draft-1:v3", "{not json");

    expect(loadTray(DRAFT_ID, 3)).toEqual([]);
  });

  it("discards entries that are not instruction items", () => {
    window.sessionStorage.setItem(
      "sitewise:tray:draft-1:v3",
      JSON.stringify([item(), { id: "junk" }]),
    );

    expect(loadTray(DRAFT_ID, 3)).toEqual([item()]);
  });
});

describe("InstructionTray", () => {
  it("renders nothing when the tray is empty", () => {
    const { container } = render(
      <InstructionTray
        items={[]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("shows each item with its section badge and instruction", () => {
    render(
      <InstructionTray
        items={[item(), item({ id: "item-2", sectionHeading: "Programme", instruction: "add float" })]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Apply 2 changes/ })).toBeInTheDocument();
    expect(screen.getByText("Procurement posture")).toBeInTheDocument();
    expect(screen.getByText("Programme")).toBeInTheDocument();
    expect(screen.getByText("add float")).toBeInTheDocument();
  });

  it("uses the singular label for one item", () => {
    render(
      <InstructionTray
        items={[item()]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Apply 1 change$/ })).toBeInTheDocument();
  });

  it("removes, clears and applies through its callbacks", () => {
    const onRemove = vi.fn();
    const onClearAll = vi.fn();
    const onApply = vi.fn();
    render(
      <InstructionTray
        items={[item()]}
        onRemove={onRemove}
        onClearAll={onClearAll}
        onApply={onApply}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Remove instruction: make it two-stage" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    fireEvent.click(screen.getByRole("button", { name: /Apply 1 change/ }));

    expect(onRemove).toHaveBeenCalledWith("item-1");
    expect(onClearAll).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it("renders a failed item's reason", () => {
    render(
      <InstructionTray
        items={[item({ error: "selection is outside any section" })]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByText("selection is outside any section")).toBeInTheDocument();
  });

  it("collapses and expands the item list", () => {
    render(
      <InstructionTray
        items={[item()]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    const toggle = screen.getByRole("button", { name: /1 change queued/ });
    fireEvent.click(toggle);
    expect(screen.queryByText("make it two-stage")).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.getByText("make it two-stage")).toBeInTheDocument();
  });

  it("disables its controls while a batch is applying", () => {
    render(
      <InstructionTray
        items={[item()]}
        isApplying
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Applying/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Clear all" })).toBeDisabled();
  });

  it("runs the agent-thinking indicator while applying", () => {
    const { container, rerender } = render(
      <InstructionTray
        items={[item()]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(container.querySelectorAll(".streaming-trace__point")).toHaveLength(0);

    rerender(
      <InstructionTray
        items={[item()]}
        isApplying
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(container.querySelectorAll(".streaming-trace__point")).toHaveLength(6);
    expect(screen.getByText("Revising the sections you marked…")).toBeInTheDocument();
  });

  it("shows why the last apply failed, next to the button that failed", () => {
    render(
      <InstructionTray
        items={[item()]}
        error="Draft moved to v4 — review the current text and re-apply."
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Draft moved to v4 — review the current text and re-apply."),
    ).toBeInTheDocument();
  });

  it("marks itself as instruction UI so selection anchoring suppresses inside it", () => {
    const { container } = render(
      <InstructionTray
        items={[item()]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(container.querySelector("[data-instruction-ui]")).not.toBeNull();
  });

  it("uses the Sitewise floating surface, never bg-background", () => {
    // `.project-main-panel` sets `--background: transparent` so nested in-flow
    // sections show the panel surface. This tray floats over document text, so
    // it must use an opaque raised surface (sw-surface), not bg-background.
    const { container } = render(
      <InstructionTray
        items={[item()]}
        onRemove={vi.fn()}
        onClearAll={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    const tray = container.querySelector("[data-instruction-ui]")!;
    expect(tray).toHaveClass("sw-surface");
    expect(tray).toHaveClass("sw-contact");
    expect(tray.className).not.toMatch(/\bbg-background\b/);
  });
});

describe("SelectionInstructionCard", () => {
  const anchor = {
    start: 40,
    end: 66,
    quotedText: "single-stage invited tender",
    rect: new DOMRect(20, 30, 100, 16),
  };

  it("adds the typed instruction on click", () => {
    const onAdd = vi.fn();
    render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={onAdd}
        onDismiss={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Instruction"), {
      target: { value: "make it two-stage" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add to tray" }));

    expect(onAdd).toHaveBeenCalledWith("make it two-stage");
  });

  it("adds on Enter and newlines on Shift+Enter", () => {
    const onAdd = vi.fn();
    render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={onAdd}
        onDismiss={vi.fn()}
      />,
    );
    const textarea = screen.getByLabelText("Instruction");
    fireEvent.change(textarea, { target: { value: "make it two-stage" } });

    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onAdd).not.toHaveBeenCalled();

    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("make it two-stage");
  });

  it("dismisses on Escape", () => {
    const onDismiss = vi.fn();
    render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={vi.fn()}
        onDismiss={onDismiss}
      />,
    );

    fireEvent.keyDown(screen.getByLabelText("Instruction"), { key: "Escape" });

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("will not add an empty instruction", () => {
    const onAdd = vi.fn();
    render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={onAdd}
        onDismiss={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Add to tray" })).toBeDisabled();
    fireEvent.keyDown(screen.getByLabelText("Instruction"), { key: "Enter" });
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("shows the quoted snippet and marks itself as instruction UI", () => {
    const { container } = render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    expect(screen.getByText("single-stage invited tender")).toBeInTheDocument();
    expect(container.querySelector("[data-instruction-ui]")).not.toBeNull();
  });

  it("paints on the opaque overlay token, never bg-background", () => {
    // The card floats over document text. `--background` is transparent inside
    // the dark cockpit panels, so bg-background would render it see-through.
    const { container } = render(
      <SelectionInstructionCard
        anchor={anchor}
        sectionHeading="Procurement posture"
        onAdd={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );

    const card = container.querySelector("[role='dialog']")!;
    expect(card).toHaveClass("bg-popover");
    expect(card.className).not.toMatch(/\bbg-background\b/);
  });
});
