import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProgramGantt } from "@/components/project/ProgramGantt";
import type { ProgrammeState } from "@/lib/programme";

function state(overrides: Partial<ProgrammeState> = {}): ProgrammeState {
  return {
    id: "prog-1",
    project_id: "project-1",
    version: 1,
    status: "proposed",
    view_scale: "month",
    pmp_embed_visible: true,
    activities: [
      {
        activity_key: "planning",
        kind: "stage",
        parent_key: null,
        name: "Planning",
        display_order: 0,
        start_date: "2026-08-16",
        duration_days: 90,
        finish_date: "2026-11-14",
        predecessor_key: null,
        lag_days: 0,
        assumption: true,
        notes: "",
      },
      {
        activity_key: "procurement",
        kind: "stage",
        parent_key: null,
        name: "Procurement",
        display_order: 1,
        start_date: "2026-11-14",
        duration_days: 60,
        finish_date: "2027-01-13",
        predecessor_key: "planning",
        lag_days: 0,
        assumption: true,
        notes: "",
      },
      {
        activity_key: "delivery",
        kind: "stage",
        parent_key: null,
        name: "Delivery",
        display_order: 2,
        start_date: "2027-01-13",
        duration_days: 365,
        finish_date: "2028-01-13",
        predecessor_key: "procurement",
        lag_days: 0,
        assumption: true,
        notes: "",
      },
    ],
    ...overrides,
  };
}

describe("ProgramGantt", () => {
  it("renders the default stage names", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getAllByText("Planning").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Procurement").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Delivery").length).toBeGreaterThan(0);
  });

  it("shows week, month, and quarter scale controls in edit mode", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByRole("button", { name: "week" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "month" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "quarter" })).toBeInTheDocument();
  });

  it("styles the header like the cost plan and sits column labels on the bottom row", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    const header = document.querySelector("[data-gantt-header]");
    expect(header).toHaveClass("program-gantt-header");
    expect(header?.querySelector(".program-gantt-header-label")?.textContent).toBe("Activity");
    expect(screen.getByText("Activity").className).toContain("program-gantt-header-label");
    expect(screen.getByText("Start").className).toContain("bottom-1.5");
    expect(screen.getByText("Days").className).toContain("bottom-1.5");
    expect(screen.getByText("Activity").parentElement).toHaveClass("bottom-1");
  });

  it("lets the PMP figure toggle month and quarter without edit chrome", () => {
    const onScaleChange = vi.fn();
    render(
      <ProgramGantt state={state()} mode="figure" onScaleChange={onScaleChange} />,
    );
    expect(screen.getByRole("button", { name: "month" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "quarter" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "week" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open Program" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Delete/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Link|Unlink/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add activity|Add stage/ })).not.toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.getByText("Days")).toBeInTheDocument();
    expect(screen.getByText("16 Aug 26")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "quarter" }));
    expect(onScaleChange).toHaveBeenCalledWith("quarter");
  });

  it("omits drag handles and nested buttons in figure mode", () => {
    render(<ProgramGantt state={state()} mode="figure" />);
    expect(document.querySelector("[data-interactive]")).toBeNull();
    expect(document.querySelector("[data-gantt-bar] button")).toBeNull();
    expect(document.querySelector("[data-gantt-handle]")).toBeNull();
    expect(screen.queryByRole("button", { name: "Open Program" })).not.toBeInTheDocument();
  });

  it("notifies when the scale changes", async () => {
    const user = userEvent.setup();
    const onScaleChange = vi.fn();
    render(
      <ProgramGantt state={state()} mode="edit" onScaleChange={onScaleChange} />,
    );
    await user.click(screen.getByRole("button", { name: "quarter" }));
    expect(onScaleChange).toHaveBeenCalledWith("quarter");
  });

  it("edits the name in the row instead of a separate inspector", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Planning" }));
    await user.clear(screen.getByLabelText("stage name"));
    await user.type(screen.getByLabelText("stage name"), "Design{enter}");
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "UPDATE",
        target_id: "planning",
        values: { name: "Design" },
      }),
    ]);
  });

  it("uses the same compact type size for activity, date, days, and name editing", async () => {
    const user = userEvent.setup();
    render(<ProgramGantt state={state()} mode="edit" />);
    const name = screen.getByRole("button", { name: "Planning" });
    const date = screen.getByRole("button", { name: "Planning start date" });
    const days = screen.getByLabelText("Planning duration in days");
    expect(name.className).toContain("text-[10px]");
    expect(date.className).toContain("text-[10px]");
    expect(days.className).toContain("text-[10px]");
    expect(days.className).toContain("md:text-[10px]");
    await user.click(name);
    const editor = screen.getByLabelText("stage name");
    expect(editor.className).toContain("text-[10px]");
    expect(editor.className).toContain("md:text-[10px]");
    expect(editor.className).toContain("program-gantt-field");
  });

  it("uses the same compact type size for activity, date, days, and name editing", async () => {
    const user = userEvent.setup();
    render(<ProgramGantt state={state()} mode="edit" />);
    const name = screen.getByRole("button", { name: "Planning" });
    const date = screen.getByRole("button", { name: "Planning start date" });
    const days = screen.getByLabelText("Planning duration in days");
    expect(name.className).toContain("text-[10px]");
    expect(date.className).toContain("text-[10px]");
    expect(days.className).toContain("text-[10px]");
    expect(days.className).toContain("md:text-[10px]");
    await user.click(name);
    const editor = screen.getByLabelText("stage name");
    expect(editor.className).toContain("text-[10px]");
    expect(editor.className).toContain("md:text-[10px]");
    expect(editor.className).toContain("program-gantt-field");
  });

  it("deletes from the row trash control", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    await user.click(screen.getByRole("button", { name: "Delete Planning" }));
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "DELETE",
        target_id: "planning",
      }),
    ]);
  });

  it("opens a SiteWise date popover from the start field", async () => {
    const user = userEvent.setup();
    render(<ProgramGantt state={state()} mode="edit" />);
    await user.click(screen.getByRole("button", { name: "Planning start date" }));
    expect(screen.getByRole("dialog", { name: "Choose date" })).toBeInTheDocument();
  });

  it("shows compact start dates", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByText("16 Aug 26")).toBeInTheDocument();
    expect(screen.queryByText("16 Aug 2026")).not.toBeInTheDocument();
  });

  it("keeps fit to screen when the period changes", async () => {
    const user = userEvent.setup();
    const onScaleChange = vi.fn();
    render(
      <ProgramGantt state={state()} mode="edit" onScaleChange={onScaleChange} />,
    );
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "quarter" }));
    expect(onScaleChange).toHaveBeenCalledWith("quarter");
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("fits figure bars beside name, start, and duration columns", () => {
    render(<ProgramGantt state={state()} mode="figure" />);
    const bar = document.querySelector("[data-gantt-bar='planning']");
    const links = document.querySelector("[data-gantt-links]");
    expect(bar).toBeTruthy();
    expect(links).toBeTruthy();
    const barStyle = bar?.getAttribute("style") ?? "";
    const linkStyle = links?.getAttribute("style") ?? "";
    const pane = Number.parseFloat(linkStyle.match(/left:\s*([\d.]+)px/)?.[1] ?? "");
    expect(pane).toBeGreaterThan(300);
    expect(barStyle).toContain(`${pane}px`);
    expect(bar?.tagName).toBe("DIV");
  });

  it("aligns fitted bars with the chart pane used by links", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    const bar = document.querySelector("[data-gantt-bar='planning']");
    const links = document.querySelector("[data-gantt-links]");
    expect(bar).toBeTruthy();
    expect(links).toBeTruthy();
    const barStyle = bar?.getAttribute("style") ?? "";
    const linkStyle = links?.getAttribute("style") ?? "";
    expect(barStyle).toContain("(100% - ");
    expect(barStyle).not.toContain("- 8px");
    const pane = Number.parseFloat(linkStyle.match(/left:\s*([\d.]+)px/)?.[1] ?? "");
    expect(pane).toBeGreaterThan(0);
    expect(barStyle).toContain(`${pane}px`);
    expect(links?.getAttribute("viewBox") ?? "").toMatch(/^0 0 /);
    expect(links?.getAttribute("preserveAspectRatio")).toBe("none");
    const paths = [...document.querySelectorAll("[data-gantt-link]")];
    expect(paths.length).toBe(2);
    for (const path of paths) {
      expect(path.getAttribute("d") ?? "").toMatch(
        /^M -?\d+(?:\.\d+)? -?\d+(?:\.\d+)? [HV] -?\d+(?:\.\d+)?/,
      );
      expect(path.getAttribute("d") ?? "").not.toMatch(/\bL\b/);
    }
    expect(document.querySelector("[data-gantt-link='planning->procurement']")?.getAttribute("d")).toBe(
      "M 90 12 V 36",
    );
    expect(document.querySelector("[data-gantt-link='procurement->delivery']")?.getAttribute("d")).toBe(
      "M 150 36 V 60",
    );
  });

  it("shows compact start dates", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByText("16 Aug 26")).toBeInTheDocument();
    expect(screen.queryByText("16 Aug 2026")).not.toBeInTheDocument();
  });

  it("keeps fit to screen when the period changes", async () => {
    const user = userEvent.setup();
    const onScaleChange = vi.fn();
    render(
      <ProgramGantt state={state()} mode="edit" onScaleChange={onScaleChange} />,
    );
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "quarter" }));
    expect(onScaleChange).toHaveBeenCalledWith("quarter");
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("aligns fitted bars with the chart pane used by links", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    const bar = document.querySelector("[data-gantt-bar='planning']");
    const links = document.querySelector("[data-gantt-links]");
    expect(bar).toBeTruthy();
    expect(links).toBeTruthy();
    const barStyle = bar?.getAttribute("style") ?? "";
    const linkStyle = links?.getAttribute("style") ?? "";
    expect(barStyle).toContain("(100% - ");
    expect(barStyle).not.toContain("- 8px");
    const pane = Number.parseFloat(linkStyle.match(/left:\s*([\d.]+)px/)?.[1] ?? "");
    expect(pane).toBeGreaterThan(0);
    expect(barStyle).toContain(`${pane}px`);
    expect(links?.getAttribute("viewBox") ?? "").toMatch(/^0 0 /);
    expect(links?.getAttribute("preserveAspectRatio")).toBe("none");
    const paths = [...document.querySelectorAll("[data-gantt-link]")];
    expect(paths.length).toBe(2);
    for (const path of paths) {
      expect(path.getAttribute("d") ?? "").toMatch(
        /^M -?\d+(?:\.\d+)? -?\d+(?:\.\d+)? [HV] -?\d+(?:\.\d+)?/,
      );
      expect(path.getAttribute("d") ?? "").not.toMatch(/\bL\b/);
    }
    expect(document.querySelector("[data-gantt-link='planning->procurement']")?.getAttribute("d")).toBe(
      "M 90 12 V 36",
    );
    expect(document.querySelector("[data-gantt-link='procurement->delivery']")?.getAttribute("d")).toBe(
      "M 150 36 V 60",
    );
  });

  it("shows compact month letters under the year when fitted", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByText("2026")).toBeInTheDocument();
    expect(screen.getByTitle("Aug 2026")).toHaveTextContent("A");
    expect(screen.queryByText("08-16")).not.toBeInTheDocument();
  });

  it("shows week numbers under month or quarter labels in week scale", async () => {
    const user = userEvent.setup();
    render(<ProgramGantt state={state({ view_scale: "week" })} mode="edit" />);
    expect(screen.getByTitle("Q3 2026")).toBeInTheDocument();
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "month" }));
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("starts fitted to the screen in edit mode", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByRole("button", { name: "Fit to screen" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("offers fit to screen in edit mode only", () => {
    const { rerender } = render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByRole("button", { name: "Fit to screen" })).toBeInTheDocument();
    rerender(<ProgramGantt state={state()} mode="figure" />);
    expect(screen.queryByRole("button", { name: "Fit to screen" })).not.toBeInTheDocument();
  });

  it("adds an activity from the row plus and a stage from the header plus", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    expect(screen.queryByRole("menuitem", { name: "Activity" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add activity below Planning" }));
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "ADD",
        target_type: "activity",
        reference_id: "planning",
        values: expect.objectContaining({ parent_key: "planning" }),
      }),
    ]);
    await user.click(screen.getByRole("button", { name: "Add stage" }));
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "ADD",
        target_type: "stage",
      }),
    ]);
  });

  it("toggles a finish-to-start link on the row", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    await user.click(screen.getByRole("button", { name: "Unlink Procurement" }));
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "UPDATE",
        target_id: "procurement",
        values: { predecessor_key: null, lag_days: 0 },
      }),
    ]);
  });

  it("shift-clicks a range and deletes the selection from the header", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    const planning = document.querySelector('[data-activity-key="planning"]');
    const delivery = document.querySelector('[data-activity-key="delivery"]');
    expect(planning).toBeTruthy();
    expect(delivery).toBeTruthy();
    fireEvent.click(planning!);
    fireEvent.click(delivery!, { shiftKey: true });
    expect(planning).toHaveAttribute("aria-selected", "true");
    expect(delivery).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByRole("button", { name: "Delete 3 selected activities" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete 3 selected activities" }));
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({ operation: "DELETE", target_id: "planning" }),
      expect.objectContaining({ operation: "DELETE", target_id: "procurement" }),
      expect.objectContaining({ operation: "DELETE", target_id: "delivery" }),
    ]);
  });

  it("control-clicks to curate a selection", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    const planning = document.querySelector('[data-activity-key="planning"]');
    const delivery = document.querySelector('[data-activity-key="delivery"]');
    fireEvent.click(planning!);
    fireEvent.click(delivery!, { ctrlKey: true });
    expect(planning).toHaveAttribute("aria-selected", "true");
    expect(delivery).toHaveAttribute("aria-selected", "true");
    expect(
      document.querySelector('[data-activity-key="procurement"]'),
    ).toHaveAttribute("aria-selected", "false");
    expect(
      screen.getByRole("button", { name: "Delete 2 selected activities" }),
    ).toBeInTheDocument();
  });

  it("exposes a reorder handle in edit mode only", () => {
    const { rerender } = render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByRole("button", { name: "Reorder Planning" })).toBeInTheDocument();
    rerender(<ProgramGantt state={state()} mode="figure" />);
    expect(screen.queryByRole("button", { name: "Reorder Planning" })).not.toBeInTheDocument();
  });

  it("draws inbound resize ticks on edit bars and a time grid", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    const bar = document.querySelector("[data-gantt-bar='planning']");
    expect(bar?.querySelector("[data-gantt-handle='start']")).toBeTruthy();
    expect(bar?.querySelector("[data-gantt-handle='end']")).toBeTruthy();
    expect(screen.getByRole("separator", { name: "Resize start of Planning" })).toBeInTheDocument();
    expect(screen.getByRole("separator", { name: "Resize Planning" })).toBeInTheDocument();
    expect(document.querySelector("[data-gantt-grid]")).toBeTruthy();
    expect(document.querySelectorAll("[data-gantt-grid-x]").length).toBeGreaterThan(2);
  });

  it("resizes from the start edge without moving the finish", async () => {
    const user = userEvent.setup();
    const onOperate = vi.fn();
    render(<ProgramGantt state={state()} mode="edit" onOperate={onOperate} />);
    await user.click(screen.getByRole("button", { name: "Fit to screen" }));
    const handle = screen.getByRole("separator", { name: "Resize start of Planning" });
    fireEvent.pointerDown(handle, { clientX: 400, pointerId: 1 });
    fireEvent.pointerUp(window, { clientX: 340, pointerId: 1 });
    expect(onOperate).toHaveBeenCalledWith([
      expect.objectContaining({
        operation: "UPDATE",
        target_id: "planning",
        values: { start_date: "2026-08-06", duration_days: 100 },
      }),
    ]);
  });
});
