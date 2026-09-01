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
  it("keeps strategy controls at the toolbar edges and removes the discipline count", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={disciplines}
        saving={false}
        onApply={vi.fn().mockResolvedValue(undefined)}
        onRefresh={onRefresh}
      />,
    );

    expect(screen.getByRole("button", { name: "Add discipline" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sync" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Download procurement strategy" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Copy procurement strategy" }),
    ).toBeTruthy();
    expect(screen.queryByText("1 discipline")).toBeNull();

    await user.click(
      screen.getByRole("button", { name: "Download procurement strategy" }),
    );
    expect(screen.getByRole("menuitem", { name: "Excel" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "CSV" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Word" })).toBeTruthy();

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Sync" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("starts at three firms and requests a persisted fourth column", async () => {
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

    expect(screen.getByRole("columnheader", { name: "Firm 3" })).toBeTruthy();
    expect(screen.queryByLabelText("Structural, Firm 4")).toBeNull();

    await userEvent.click(
      screen.getByRole("button", { name: "Add firm column" }),
    );
    expect(onApply).toHaveBeenCalledWith([
      {
        operation: "SET_TENDERER_COLUMN_COUNT",
        tenderer_column_count: 4,
      },
    ]);
  });

  it("commits a firm on blur", async () => {
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

    const firm = screen.getByLabelText("Structural, Firm 1");
    await user.type(firm, "North & Co");
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

  it("presents the four status milestones as cumulative toggle buttons", async () => {
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

    const issued = screen.getByRole("button", { name: "Structural: Issued" });
    const submitted = screen.getByRole("button", {
      name: "Structural: Submitted",
    });
    const recommendation = screen.getByRole("button", {
      name: "Structural: Recommendation",
    });
    const contract = screen.getByRole("button", { name: "Structural: Contract" });

    expect(issued).toHaveAttribute("aria-pressed", "false");
    expect(submitted).toHaveAttribute("aria-pressed", "false");
    expect(recommendation).toHaveTextContent("Rec.");
    expect(contract).toHaveAttribute("aria-pressed", "false");

    await user.click(recommendation);
    expect(onApply).toHaveBeenCalledWith([
      {
        operation: "UPDATE_ROW",
        row_id: "row-1",
        status: "evaluating",
      },
    ]);
  });

  it("removes notes and consultant source links from the row", () => {
    const strategyWithSource: ProcurementStrategy = {
      ...strategy,
      rows: [
        {
          ...strategy.rows[0],
          notes: "Old note",
          candidates: [
            {
              id: "candidate-1",
              slot: 1,
              company_name: "North & Co",
              website_url: "https://north.example",
              location_text: null,
              source_url: "https://source.example",
              source_title: "Directory listing",
              researched_at: null,
            },
          ],
        },
      ],
    };

    render(
      <ProcurementStrategyGrid
        strategy={strategyWithSource}
        disciplines={disciplines}
        saving={false}
        onApply={vi.fn().mockResolvedValue(undefined)}
        onRefresh={vi.fn()}
      />,
    );

    expect(screen.queryByPlaceholderText("Add note")).toBeNull();
    expect(screen.queryByRole("link", { name: "Source" })).toBeNull();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeTruthy();
  });

  it("uses clear labels in the row action menu", async () => {
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

    expect(edit).toHaveTextContent("Edit with AI");
    expect(above).toHaveTextContent("Add discipline above");
    expect(below).toHaveTextContent("Add discipline below");
    expect(lock).toHaveTextContent("Lock row");
    expect(remove).toHaveTextContent("Delete row");
  });

  it("groups consultants and trades and sorts each list alphanumerically", () => {
    const mixedStrategy: ProcurementStrategy = {
      ...strategy,
      rows: [
        {
          ...strategy.rows[0],
          id: "trade-10",
          discipline_code: null,
          discipline_label: "Trade 10",
          participant_type: "trade",
          request_kind: "trade_rft",
          display_order: 100,
        },
        {
          ...strategy.rows[0],
          id: "consultant-zulu",
          discipline_code: null,
          discipline_label: "Zulu Consultant",
          display_order: 200,
        },
        {
          ...strategy.rows[0],
          id: "trade-2",
          discipline_code: null,
          discipline_label: "Trade 2",
          participant_type: "trade",
          request_kind: "trade_rft",
          display_order: 300,
        },
        {
          ...strategy.rows[0],
          id: "consultant-alpha",
          discipline_code: null,
          discipline_label: "Alpha Consultant",
          display_order: 400,
        },
      ],
    };

    render(
      <ProcurementStrategyGrid
        strategy={mixedStrategy}
        disciplines={disciplines}
        saving={false}
        onApply={vi.fn().mockResolvedValue(undefined)}
        onRefresh={vi.fn()}
      />,
    );

    const bodyRows = screen.getAllByRole("row").slice(1);
    expect(bodyRows.map((row) => row.textContent)).toEqual([
      "Consultants",
      expect.stringMatching(/^Alpha Consultant/),
      expect.stringMatching(/^Zulu Consultant/),
      "Trades",
      expect.stringMatching(/^Trade 2/),
      expect.stringMatching(/^Trade 10/),
    ]);
  });
});
