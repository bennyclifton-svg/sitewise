import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CostInvoiceRegister } from "@/components/project/CostInvoiceRegister";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { InvoiceLedger } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getInvoiceLedger: vi.fn(),
    updateInvoiceAllocation: vi.fn(),
    updateInvoice: vi.fn(),
  },
}));

function ledger(overrides: Partial<InvoiceLedger> = {}): InvoiceLedger {
  return {
    cost_plan_version: 11,
    workbook_path: "01-cost/Cost_Plan_v11.draft.xlsx",
    rows: [
      {
        allocation_id: "alloc-1",
        invoice_id: "inv-1",
        invoice_revision: 1,
        invoice_date: "2025-05-16",
        company: "Ardent Structural",
        po_number: null,
        invoice_number: "INV-AS-2611",
        description: "Stage 1 — Concept design",
        cost_item_key: null,
        cost_item_label: "Unidentified",
        amount_ex_gst: "3450",
        billing_month: "2025-05-01",
        paid: false,
        review_status: "needs_review",
        mapping_method: "unidentified",
      },
    ],
    cost_items: [
      {
        item_key: "6",
        cost_code: "6",
        category: "Consultants",
        item: "Structural engineer",
        budget: "11500",
      },
    ],
    ...overrides,
  };
}

describe("CostInvoiceRegister", () => {
  beforeEach(() => {
    vi.mocked(api.getInvoiceLedger).mockResolvedValue(ledger());
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("retries a stale Cost Plan version instead of dropping the mapping", async () => {
    const user = userEvent.setup();
    vi.mocked(api.updateInvoiceAllocation)
      .mockRejectedValueOnce(
        new ApiError("Expected Cost Plan v11, current version is v12", {
          kind: "http",
          status: 409,
        }),
      )
      .mockResolvedValueOnce(
        ledger({
          cost_plan_version: 12,
          rows: [
            {
              ...ledger().rows[0]!,
              invoice_revision: 2,
              cost_item_key: "6",
              cost_item_label: "Structural engineer",
              review_status: "mapped",
              mapping_method: "manual",
            },
          ],
        }),
      );
    vi.mocked(api.getInvoiceLedger)
      .mockResolvedValueOnce(ledger())
      .mockResolvedValueOnce(ledger({ cost_plan_version: 12 }));

    render(<CostInvoiceRegister projectId="project-1" revision={11} />);
    const select = await screen.findByLabelText(
      /cost item for invoice INV-AS-2611/i,
    );
    await user.selectOptions(select, "6");

    await waitFor(() =>
      expect(api.updateInvoiceAllocation).toHaveBeenCalledTimes(2),
    );
    expect(api.updateInvoiceAllocation).toHaveBeenLastCalledWith(
      "project-1",
      "alloc-1",
      {
        expected_revision: 1,
        expected_cost_plan_version: 12,
        cost_item_key: "6",
      },
    );
    expect(select).toHaveValue("6");
    expect(
      await screen.findByText("Saved against Cost Plan v12"),
    ).toBeInTheDocument();
  });

  it("keeps an in-flight mapping when the Cost Plan revision prop changes", async () => {
    const user = userEvent.setup();
    let resolveSave: (value: InvoiceLedger) => void = () => undefined;
    vi.mocked(api.updateInvoiceAllocation).mockImplementation(
      () =>
        new Promise<InvoiceLedger>((resolve) => {
          resolveSave = resolve;
        }),
    );

    const { rerender } = render(
      <CostInvoiceRegister projectId="project-1" revision={11} />,
    );
    const select = await screen.findByLabelText(
      /cost item for invoice INV-AS-2611/i,
    );
    await user.selectOptions(select, "6");
    expect(screen.getByText(/Saving 1 invoice change/)).toBeInTheDocument();

    rerender(<CostInvoiceRegister projectId="project-1" revision={12} />);
    expect(select).toHaveValue("6");
    expect(api.getInvoiceLedger).toHaveBeenCalledTimes(1);

    resolveSave(
      ledger({
        cost_plan_version: 12,
        rows: [
          {
            ...ledger().rows[0]!,
            invoice_revision: 2,
            cost_item_key: "6",
            cost_item_label: "Structural engineer",
            review_status: "mapped",
            mapping_method: "manual",
          },
        ],
      }),
    );
    expect(
      await screen.findByText("Saved against Cost Plan v12"),
    ).toBeInTheDocument();
    expect(select).toHaveValue("6");
  });
});
