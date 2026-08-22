import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CostInvoiceRegister } from "@/components/project/CostInvoiceRegister";
import { api } from "@/lib/api";
import { resetInvoiceEditQueues } from "@/lib/invoice-edit-queue";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
import type { InvoiceLedger } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getInvoiceLedger: vi.fn(),
    updateInvoiceAllocation: vi.fn(),
    updateInvoice: vi.fn(),
    getInvoiceReview: vi.fn(),
    decideInvoice: vi.fn(),
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
        description:
          "Stage 1 — Concept design and footing investigation — 30% of agreed fee",
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
    resetInvoiceEditQueues();
    queryClient.clear();
    window.sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("renders a cached ledger immediately without waiting for a refetch", () => {
    queryClient.setQueryData(workbenchKeys.invoiceLedger("project-1"), ledger());

    render(<CostInvoiceRegister projectId="project-1" />);

    expect(screen.getByText("Ardent Structural")).toBeInTheDocument();
    expect(screen.queryByText("Loading invoices…")).not.toBeInTheDocument();
    expect(api.getInvoiceLedger).not.toHaveBeenCalled();
  });

  it("renders a cached ledger immediately without waiting for a refetch", () => {
    queryClient.setQueryData(workbenchKeys.invoiceLedger("project-1"), ledger());

    render(<CostInvoiceRegister projectId="project-1" />);

    expect(screen.getByText("Ardent Structural")).toBeInTheDocument();
    expect(screen.queryByText("Loading invoices…")).not.toBeInTheDocument();
    expect(api.getInvoiceLedger).not.toHaveBeenCalled();
  });

  it("exposes truncated invoice text on hover without wrapping rows", async () => {
    render(<CostInvoiceRegister projectId="project-1" />);
    const company = await screen.findByText("Ardent Structural");
    const description = screen.getByText(
      "Stage 1 — Concept design and footing investigation — 30% of agreed fee",
    );

    expect(company).toHaveAttribute("title", "Ardent Structural");
    expect(description).toHaveAttribute(
      "title",
      "Stage 1 — Concept design and footing investigation — 30% of agreed fee",
    );
    expect(company.closest("table")).toHaveClass("cost-invoice-table");
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

  it("keeps remaining allocations queued when one invoice save fails", async () => {
    const user = userEvent.setup();
    const twoRows = ledger({
      rows: [
        ledger().rows[0]!,
        {
          ...ledger().rows[0]!,
          allocation_id: "alloc-2",
          invoice_id: "inv-2",
          invoice_number: "INV-AS-2612",
        },
      ],
      cost_items: [
        ...ledger().cost_items,
        {
          item_key: "architect",
          cost_code: "1",
          category: "Consultants",
          item: "Architect",
          budget: "20000",
        },
      ],
    });
    queryClient.setQueryData(workbenchKeys.invoiceLedger("project-1"), twoRows);
    let rejectFirst: (error: ApiError) => void = () => undefined;
    vi.mocked(api.updateInvoiceAllocation)
      .mockImplementationOnce(
        () =>
          new Promise<InvoiceLedger>((_resolve, reject) => {
            rejectFirst = reject;
          }),
      )
      .mockResolvedValueOnce(
        ledger({
          ...twoRows,
          rows: [
            twoRows.rows[0]!,
            {
              ...twoRows.rows[1]!,
              invoice_revision: 2,
              cost_item_key: "architect",
              cost_item_label: "Architect",
              review_status: "mapped",
              mapping_method: "manual",
            },
          ],
        }),
      );

    render(<CostInvoiceRegister projectId="project-1" />);
    const first = await screen.findByLabelText(
      /cost item for invoice INV-AS-2611/i,
    );
    const second = screen.getByLabelText(/cost item for invoice INV-AS-2612/i);
    await user.selectOptions(first, "6");
    await user.selectOptions(second, "architect");
    expect(api.updateInvoiceAllocation).toHaveBeenCalledTimes(1);

    rejectFirst(
      new ApiError("Invoice change could not be saved.", {
        kind: "http",
        status: 500,
      }),
    );

    await waitFor(() =>
      expect(api.updateInvoiceAllocation).toHaveBeenCalledTimes(2),
    );
    expect(api.updateInvoiceAllocation).toHaveBeenLastCalledWith(
      "project-1",
      "alloc-2",
      {
        expected_revision: 1,
        expected_cost_plan_version: 11,
        cost_item_key: "architect",
      },
    );
    expect(second).toHaveValue("architect");
  });

  it("finishes queued allocations after the register unmounts", async () => {
    const user = userEvent.setup();
    let resolveFirst: (value: InvoiceLedger) => void = () => undefined;
    vi.mocked(api.updateInvoiceAllocation)
      .mockImplementationOnce(
        () =>
          new Promise<InvoiceLedger>((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockResolvedValueOnce(
        ledger({
          rows: [
            {
              ...ledger().rows[0]!,
              allocation_id: "alloc-2",
              invoice_id: "inv-2",
              invoice_revision: 2,
              cost_item_key: "architect",
              cost_item_label: "Architect",
              review_status: "mapped",
              mapping_method: "manual",
            },
          ],
        }),
      );
    queryClient.setQueryData(
      workbenchKeys.invoiceLedger("project-1"),
      ledger({
        rows: [
          ledger().rows[0]!,
          {
            ...ledger().rows[0]!,
            allocation_id: "alloc-2",
            invoice_id: "inv-2",
            invoice_number: "INV-AS-2612",
          },
        ],
        cost_items: [
          ...ledger().cost_items,
          {
            item_key: "architect",
            cost_code: "1",
            category: "Consultants",
            item: "Architect",
            budget: "20000",
          },
        ],
      }),
    );

    const { unmount } = render(<CostInvoiceRegister projectId="project-1" />);
    await user.selectOptions(
      await screen.findByLabelText(/cost item for invoice INV-AS-2611/i),
      "6",
    );
    await user.selectOptions(
      screen.getByLabelText(/cost item for invoice INV-AS-2612/i),
      "architect",
    );
    unmount();

    resolveFirst(
      ledger({
        rows: [
          {
            ...ledger().rows[0]!,
            invoice_revision: 2,
            cost_item_key: "6",
            cost_item_label: "Structural engineer",
            review_status: "mapped",
            mapping_method: "manual",
          },
          {
            ...ledger().rows[0]!,
            allocation_id: "alloc-2",
            invoice_id: "inv-2",
            invoice_number: "INV-AS-2612",
          },
        ],
      }),
    );

    await waitFor(() =>
      expect(api.updateInvoiceAllocation).toHaveBeenCalledTimes(2),
    );
    expect(api.updateInvoiceAllocation).toHaveBeenNthCalledWith(
      2,
      "project-1",
      "alloc-2",
      {
        expected_revision: 1,
        expected_cost_plan_version: 11,
        cost_item_key: "architect",
      },
    );
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
