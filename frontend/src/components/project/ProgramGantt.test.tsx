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

  it("shows scale controls only in edit mode", () => {
    const { rerender } = render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByRole("button", { name: "week" })).toBeInTheDocument();
    rerender(<ProgramGantt state={state()} mode="figure" />);
    expect(screen.queryByRole("button", { name: "week" })).not.toBeInTheDocument();
  });

  it("omits drag handles in figure mode", () => {
    render(<ProgramGantt state={state()} mode="figure" />);
    expect(document.querySelector("[data-interactive]")).toBeNull();
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

  it("labels the time axis with months, not ISO fragments", () => {
    render(<ProgramGantt state={state()} mode="edit" />);
    expect(screen.getByText("Aug 2026")).toBeInTheDocument();
    expect(screen.queryByText("08-16")).not.toBeInTheDocument();
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
});
