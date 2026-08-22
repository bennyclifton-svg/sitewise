import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProcurementStrategyGrid } from "@/components/project/ProcurementStrategyGrid";
import type { ProcurementStrategy } from "@/lib/types/project";

const strategy: ProcurementStrategy = {
  id: "strategy-1",
  project_id: "project-1",
  revision: 2,
  tenderer_column_count: 3,
  source_fingerprint: "fingerprint",
  created_at: "2026-08-22T00:00:00Z",
  updated_at: "2026-08-22T00:00:00Z",
  rows: [
    {
      id: "row-1",
      discipline_code: "consultant.structural",
      discipline_label: "Structural",
      participant_type: "consultant",
      request_kind: "consultant_rfp",
      status: "not_started",
      notes: "",
      display_order: 100,
      origin: "derived",
      locked: false,
      candidates: [],
      linked_request_ids: [],
      no_longer_required: false,
    },
  ],
};

const disciplines = [
  {
    code: "consultant.structural",
    label: "Structural",
    participant_type: "consultant" as const,
    request_kind: "consultant_rfp" as const,
    workspace_slug: "structural-engineer",
  },
  {
    code: "consultant.civil",
    label: "Civil",
    participant_type: "consultant" as const,
    request_kind: "consultant_rfp" as const,
    workspace_slug: "civil-engineer",
  },
];

describe("ProcurementStrategyGrid", () => {
  it("starts at three tenderers and requests a persisted fourth column", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={disciplines}
        saving={false}
        onApply={onApply}
        onRefresh={vi.fn()}
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Tenderer 3" })).toBeTruthy();
    expect(screen.queryByLabelText("Structural, Tenderer 4")).toBeNull();

    await userEvent.click(
      screen.getByRole("button", { name: "Add tenderer column" }),
    );
    expect(onApply).toHaveBeenCalledWith([
      {
        operation: "SET_TENDERER_COLUMN_COUNT",
        tenderer_column_count: 4,
      },
    ]);
  });

  it("commits a tenderer on blur", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={disciplines}
        saving={false}
        onApply={onApply}
        onRefresh={vi.fn()}
      />,
    );

    const tenderer = screen.getByLabelText("Structural, Tenderer 1");
    await user.type(tenderer, "North & Co");
    await user.tab();

    expect(onApply).toHaveBeenCalledWith([
      {
        operation: "UPSERT_CANDIDATE",
        row_id: "row-1",
        slot: 1,
        company_name: "North & Co",
      },
    ]);
  });

  it("presents the four simplified procurement statuses", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={disciplines}
        saving={false}
        onApply={onApply}
        onRefresh={vi.fn()}
      />,
    );

    await user.click(screen.getByLabelText("Structural status"));
    expect(screen.getByRole("menuitem", { name: "RFP issued" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Received" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Recommendation" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Awarded" })).toBeTruthy();
    expect(screen.queryByRole("menuitem", { name: "Researching" })).toBeNull();

    await user.click(screen.getByRole("menuitem", { name: "Recommendation" }));
    expect(onApply).toHaveBeenCalledWith([
      {
        operation: "UPDATE_ROW",
        row_id: "row-1",
        status: "evaluating",
      },
    ]);
  });

  it("uses the compact icon-only artefact action menu", async () => {
    const user = userEvent.setup();
    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={disciplines}
        saving={false}
        onApply={vi.fn().mockResolvedValue(undefined)}
        onRefresh={vi.fn()}
        onEditWithAi={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Actions for Structural" }));
    const edit = screen.getByRole("menuitem", { name: "Edit Structural with AI" });
    const above = screen.getByRole("menuitem", { name: "Add row above" });
    const below = screen.getByRole("menuitem", { name: "Add row below" });
    const lock = screen.getByRole("menuitem", { name: "Lock Structural" });
    const remove = screen.getByRole("menuitem", { name: "Delete Structural" });

    for (const action of [edit, above, below, lock, remove]) {
      expect(action.textContent).toBe("");
    }
  });
});
