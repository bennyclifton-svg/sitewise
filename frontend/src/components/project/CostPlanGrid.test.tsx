import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CostPlanGrid } from "@/components/project/CostPlanGrid";
import { api } from "@/lib/api";
import {
  calculateCostPlanTotals,
  type CostPlanDelta,
  type CostPlanItem,
} from "@/lib/cost-plan";

vi.mock("@/lib/api", () => ({
  api: {
    getCostPlanState: vi.fn(),
    applyCostPlanOperations: vi.fn(),
    getInvoiceLedger: vi.fn(),
  },
}));

vi.mock("@/lib/performance", () => ({
  measureLocalMutation: vi.fn(),
}));

vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        index,
        start: index * 26,
        end: (index + 1) * 26,
        size: 26,
        key: index,
      })),
    getTotalSize: () => count * 26,
  }),
}));

function item(key: string, overrides: Partial<CostPlanItem> = {}): CostPlanItem {
  return {
    item_key: key,
    cost_code: key.toUpperCase(),
    category: "Construction",
    item: key,
    display_order: 1,
    budget: "100",
    committed: "0",
    forecast: "100",
    paid: "0",
    allowance_type: "none",
    basis: "Manual",
    source_refs: [],
    status: "manual",
    locked: false,
    ...overrides,
  };
}

const baseItems = [
  item("joinery", { display_order: 1, cost_code: "1" }),
  item("ffe", { display_order: 2, cost_code: "2", budget: "50", forecast: "50" }),
];

describe("CostPlanGrid", () => {
  beforeEach(() => {
    vi.mocked(api.getCostPlanState).mockResolvedValue({
      version: 1,
      items: baseItems,
      totals: calculateCostPlanTotals(baseItems),
      categories: ["Construction"],
    });
    vi.mocked(api.getInvoiceLedger).mockResolvedValue({
      cost_plan_version: 1,
      workbook_path: "cost-plan.xlsx",
      rows: [],
      cost_items: [],
    });
    vi.mocked(api.applyCostPlanOperations).mockResolvedValue({
      version: 2,
      changed_items: [],
      deleted_item_keys: [],
      totals: calculateCostPlanTotals(baseItems),
      workbook_status: "pending",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("reloads when the published revision changes", async () => {
    vi.mocked(api.getCostPlanState)
      .mockResolvedValueOnce({
        version: 13,
        items: baseItems,
        totals: calculateCostPlanTotals(baseItems),
        categories: ["Construction"],
      })
      .mockResolvedValueOnce({
        version: 14,
        items: [
          item("joinery", {
            display_order: 1,
            cost_code: "1",
            budget: "999000",
            forecast: "999000",
          }),
        ],
        totals: calculateCostPlanTotals([
          item("joinery", { budget: "999000", forecast: "999000" }),
        ]),
        categories: ["Construction"],
      });

    const { rerender } = render(<CostPlanGrid projectId="project-1" revision={13} />);
    expect(await screen.findByText("Cost Plan v13")).toBeInTheDocument();
    expect(api.getCostPlanState).toHaveBeenCalledTimes(1);

    rerender(<CostPlanGrid projectId="project-1" revision={14} />);
    expect(await screen.findByText("Cost Plan v14")).toBeInTheDocument();
    expect(api.getCostPlanState).toHaveBeenCalledTimes(2);
  });

  it("duplicates a row from the row menu and renumbers codes", async () => {
    const user = userEvent.setup();
    let resolveMutation!: (value: CostPlanDelta) => void;
    vi.mocked(api.applyCostPlanOperations).mockImplementation(
      () =>
        new Promise<CostPlanDelta>((resolve) => {
          resolveMutation = resolve;
        }),
    );

    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("joinery name")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions for joinery" }));
    await user.click(await screen.findByRole("menuitem", { name: "Duplicate" }));

    expect(screen.getByText("Construction subtotal")).toBeInTheDocument();
    expect(screen.getAllByText("250.00").length).toBeGreaterThan(0);

    resolveMutation({
      version: 2,
      changed_items: [
        item("joinery-copy", {
          display_order: 2,
          cost_code: "2",
          item: "joinery",
        }),
      ],
      deleted_item_keys: [],
      totals: calculateCostPlanTotals([
        ...baseItems,
        item("joinery-copy", { cost_code: "2", item: "joinery" }),
      ]),
      workbook_status: "pending",
    });
    await waitFor(() => expect(api.applyCostPlanOperations).toHaveBeenCalled());
  });

  it("supports shift-select bulk delete", async () => {
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("joinery name")).toBeInTheDocument();

    const joineryRow = screen.getByLabelText("joinery name").closest("tr");
    const ffeRow = screen.getByLabelText("ffe name").closest("tr");
    expect(joineryRow).toBeTruthy();
    expect(ffeRow).toBeTruthy();

    fireEvent.click(joineryRow!);
    fireEvent.click(ffeRow!, { shiftKey: true });
    expect(
      screen.getByRole("button", { name: "Delete 2 selected items" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete selected" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete 2 selected items" }));
    await waitFor(() =>
      expect(api.applyCostPlanOperations).toHaveBeenCalledWith(
        "project-1",
        1,
        [
          expect.objectContaining({ operation: "DELETE", target_id: "joinery" }),
          expect.objectContaining({ operation: "DELETE", target_id: "ffe" }),
        ],
      ),
    );
  });

  it("deletes a single row from the hover trash control", async () => {
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("joinery name")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete joinery" }));
    await waitFor(() =>
      expect(api.applyCostPlanOperations).toHaveBeenCalledWith(
        "project-1",
        1,
        [expect.objectContaining({ operation: "DELETE", target_id: "joinery" })],
      ),
    );
  });

  it("exposes Cost Plan, Invoices, and Variations tabs", async () => {
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByRole("tab", { name: "Cost Plan v1" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByText(/^Version /)).not.toBeInTheDocument();
    expect(screen.queryByText("Selected month")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Variations" }));
    expect(screen.getByText(/Variation schedule coming soon/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Invoices" }));
    expect(await screen.findByText(/No invoices in the register yet/i)).toBeInTheDocument();
  });

  it("shows automated codes and formats money without dollar signs", async () => {
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("joinery name")).toBeInTheDocument();

    const table = screen.getByRole("table");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent?.replace(/\s+/g, " ").trim() ?? "");
    expect(headers.slice(0, 3)).toEqual([
      expect.stringMatching(/^Code/),
      expect.stringMatching(/^Category/),
      expect.stringMatching(/^Item/),
    ]);
    expect(within(table).getByText("1")).toBeInTheDocument();
    expect(within(table).getByText("2")).toBeInTheDocument();
    expect(screen.queryByText("$100")).not.toBeInTheDocument();
    expect(screen.getAllByText("100.00").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Add category" })).toBeInTheDocument();
    expect(screen.getByLabelText("Selected billing month")).toBeInTheDocument();
  });

  it("closes the row actions menu on dismiss", async () => {
    const user = userEvent.setup();
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("joinery name")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions for joinery" }));
    expect(await screen.findByRole("menuitem", { name: "Duplicate" })).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("menuitem", { name: "Duplicate" })).not.toBeInTheDocument(),
    );
  });

  it("sorts by item as a view-only order", async () => {
    render(<CostPlanGrid projectId="project-1" />);
    expect(await screen.findByLabelText("ffe name")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Item/i }));
    const nameInputs = screen.getAllByLabelText(/ name$/);
    expect(nameInputs[0]).toHaveValue("ffe");
    expect(nameInputs[1]).toHaveValue("joinery");
  });
});
