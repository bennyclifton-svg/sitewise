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
  it("offers document linking in every empty firm cell and respects locked rows", () => {
    const props = { strategy, disciplines, saving: false, onApply: vi.fn(), onRefresh: vi.fn() };
    const { rerender } = render(<ProcurementStrategyGrid {...props} />);
    for (const slot of [1, 2, 3]) {
      expect(screen.getByRole("button", { name: `Link documents for Structural, Firm ${slot}` })).toBeEnabled();
    }
    rerender(<ProcurementStrategyGrid {...props} strategy={{ ...strategy, rows: strategy.rows.map((row) => ({ ...row, locked: true })) }} />);
    expect(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" })).toBeDisabled();
  });
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

  it("shows chronological actions and only opens a completed comparison", async () => {
    const user = userEvent.setup();
    const onCreateRequest = vi.fn();
    const onCompare = vi.fn();
    const onOpenReview = vi.fn();
    const props = { strategy, disciplines, saving: false, onApply: vi.fn(), onRefresh: vi.fn(), onCreateRequest, onCompare, onOpenReview };
    const { rerender } = render(<ProcurementStrategyGrid {...props} />);
    expect(screen.queryByRole("button", { name: "Structural: Issued" })).toBeNull();
    expect(screen.getByRole("button", { name: "View comparison for Structural" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Create RFP for Structural" }));
    await user.click(screen.getByRole("button", { name: "Compare tenders for Structural" }));
    expect(onCreateRequest).toHaveBeenCalledWith(strategy.rows[0]);
    expect(onCompare).toHaveBeenCalledWith(strategy.rows[0]);
    rerender(<ProcurementStrategyGrid {...props} comparingRowId="row-1" />);
    expect(screen.getByRole("button", { name: "Compare tenders for Structural" })).toBeDisabled();
    rerender(<ProcurementStrategyGrid {...props} strategy={{ ...strategy, rows: [{ ...strategy.rows[0], recommendation_draft_id: "report-v2", comparison_id: "comparison-2" }] }} />);
    await user.click(screen.getByRole("button", { name: "View comparison for Structural" }));
    expect(onOpenReview).toHaveBeenCalledWith("report-v2");
  });

  it("marks only the explicitly awarded firm", () => {
    const candidate = { id: "firm-1", slot: 1, company_name: "Caposi", website_url: null, location_text: null, source_url: null, source_title: null, researched_at: null };
    render(<ProcurementStrategyGrid strategy={{ ...strategy, rows: [{ ...strategy.rows[0], awarded_candidate_id: candidate.id, status: "awarded", candidates: [candidate, { ...candidate, id: "firm-2", slot: 2, company_name: "Other firm" }] }] }} disciplines={disciplines} saving={false} onApply={vi.fn()} onRefresh={vi.fn()} />);
    expect(screen.getByTitle("Caposi — Awarded")).toHaveValue("Caposi");
    expect(screen.getAllByLabelText("Awarded")).toHaveLength(1);
    expect(screen.getByLabelText("Structural, Firm 2")).not.toHaveAttribute("title", expect.stringContaining("Awarded"));
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
    expect(screen.getByRole("columnheader", { name: "Procurement" })).toBeTruthy();
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

  it("shows the full discipline names in the add-discipline menu", async () => {
    const user = userEvent.setup();
    const longDisciplineLabel =
      "Mechanical, electrical, fire and hydraulic services";

    render(
      <ProcurementStrategyGrid
        strategy={strategy}
        disciplines={[
          ...disciplines,
          {
            code: "consultant.building-services",
            label: longDisciplineLabel,
            participant_type: "consultant",
            request_kind: "consultant_rfp",
            workspace_slug: "building-services-engineer",
          },
        ]}
        saving={false}
        onApply={vi.fn().mockResolvedValue(undefined)}
        onRefresh={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add discipline" }));
    await user.click(screen.getByRole("button", { name: "Discipline to add" }));

    const optionLabel = screen.getByText(longDisciplineLabel);
    const menu = optionLabel.closest('[data-slot="dropdown-menu-content"]');

    expect(optionLabel).not.toHaveClass("truncate");
    expect(menu).toHaveClass("w-max");
    expect(menu).toHaveClass(
      "min-w-[var(--radix-dropdown-menu-trigger-width)]",
    );
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
