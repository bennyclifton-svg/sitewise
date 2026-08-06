import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkbookGrid } from "@/components/project/WorkbookGrid";
import { api } from "@/lib/api";
import type { InvoiceLedger, WorkbookPreview } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({
  api: {
    getWorkbookPreview: vi.fn(),
    getInvoiceLedger: vi.fn(),
    updateInvoice: vi.fn(),
    updateInvoiceAllocation: vi.fn(),
  },
}));

const PROJECT_ID = "project-1";
const WORKBOOK_PATH = "projects/kavanagh/01-cost/Cost_Plan_v12.draft.xlsx";

describe("WorkbookGrid invoice controls", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getWorkbookPreview).mockResolvedValue(workbookPreview());
    vi.mocked(api.getInvoiceLedger).mockResolvedValue(invoiceLedger());
  });

  it("lets the user override a suggested mapping to an existing TBC trade", async () => {
    const user = userEvent.setup();
    vi.mocked(api.updateInvoiceAllocation).mockResolvedValue(
      invoiceLedger({
        cost_plan_version: 13,
        workbook_path: "projects/kavanagh/01-cost/Cost_Plan_v13.draft.xlsx",
        rows: [
          {
            ...invoiceLedger().rows[0]!,
            invoice_revision: 2,
            cost_item_key: "6",
            cost_item_label: "Structural engineer",
            mapping_method: "manual",
            review_status: "mapped",
          },
        ],
      }),
    );

    render(<WorkbookGrid projectId={PROJECT_ID} workbookPath={WORKBOOK_PATH} />);

    const mapping = await screen.findByRole("combobox", {
      name: /cost item for invoice CST-2601/i,
    });
    await user.selectOptions(mapping, "6");

    expect(api.updateInvoiceAllocation).toHaveBeenCalledWith(
      PROJECT_ID,
      "allocation-1",
      {
        expected_revision: 1,
        expected_cost_plan_version: 12,
        cost_item_key: "6",
      },
    );
    expect(await screen.findByText("Saved as Cost Plan v13.")).toBeInTheDocument();
  });

  it("toggles paid status and publishes the invoice-level change", async () => {
    const user = userEvent.setup();
    vi.mocked(api.updateInvoice).mockResolvedValue(
      invoiceLedger({ cost_plan_version: 13 }),
    );

    render(<WorkbookGrid projectId={PROJECT_ID} workbookPath={WORKBOOK_PATH} />);

    const paid = await screen.findByRole("button", {
      name: "Mark invoice CST-2601 paid",
    });
    await user.click(paid);

    await waitFor(() =>
      expect(api.updateInvoice).toHaveBeenCalledWith(PROJECT_ID, "invoice-1", {
        expected_revision: 1,
        expected_cost_plan_version: 12,
        paid: true,
      }),
    );
  });

  it("changes the billing month using a month-safe value", async () => {
    vi.mocked(api.updateInvoice).mockResolvedValue(
      invoiceLedger({ cost_plan_version: 13 }),
    );

    render(<WorkbookGrid projectId={PROJECT_ID} workbookPath={WORKBOOK_PATH} />);

    const month = await screen.findByLabelText("Billing month for invoice CST-2601");
    fireEvent.change(month, { target: { value: "2026-04" } });

    await waitFor(() =>
      expect(api.updateInvoice).toHaveBeenCalledWith(PROJECT_ID, "invoice-1", {
        expected_revision: 1,
        expected_cost_plan_version: 12,
        billing_month: "2026-04-01",
      }),
    );
  });

  it("keeps the schedule visible while the regenerated workbook refreshes", async () => {
    const user = userEvent.setup();
    const previewRefresh = deferred<WorkbookPreview>();
    vi.mocked(api.getWorkbookPreview)
      .mockResolvedValueOnce(workbookPreview())
      .mockImplementationOnce(() => previewRefresh.promise);
    vi.mocked(api.updateInvoice).mockResolvedValue(
      invoiceLedger({
        cost_plan_version: 13,
        workbook_path: "projects/kavanagh/01-cost/Cost_Plan_v13.draft.xlsx",
        rows: [
          {
            ...invoiceLedger().rows[0]!,
            invoice_revision: 2,
            paid: true,
          },
        ],
      }),
    );

    render(<WorkbookGrid projectId={PROJECT_ID} workbookPath={WORKBOOK_PATH} />);

    await user.click(
      await screen.findByRole("button", { name: "Mark invoice CST-2601 paid" }),
    );
    await waitFor(() => expect(api.getWorkbookPreview).toHaveBeenCalledTimes(2));

    expect(screen.queryByText("Loading workbook...")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Mark invoice CST-2601 unpaid" }),
    ).toBeInTheDocument();
  });

  it("queues a later invoice edit while the first save is still running", async () => {
    const user = userEvent.setup();
    const firstSave = deferred<InvoiceLedger>();
    vi.mocked(api.updateInvoice)
      .mockImplementationOnce(() => firstSave.promise)
      .mockResolvedValueOnce(
        invoiceLedger({
          cost_plan_version: 14,
          workbook_path: "projects/kavanagh/01-cost/Cost_Plan_v14.draft.xlsx",
          rows: [
            {
              ...invoiceLedger().rows[0]!,
              invoice_revision: 3,
              paid: true,
              billing_month: "2026-04-01",
            },
          ],
        }),
      );

    render(<WorkbookGrid projectId={PROJECT_ID} workbookPath={WORKBOOK_PATH} />);

    await user.click(
      await screen.findByRole("button", { name: "Mark invoice CST-2601 paid" }),
    );
    const month = screen.getByLabelText("Billing month for invoice CST-2601");
    expect(month).toBeEnabled();
    fireEvent.change(month, { target: { value: "2026-04" } });
    expect(api.updateInvoice).toHaveBeenCalledTimes(1);

    firstSave.resolve(
      invoiceLedger({
        cost_plan_version: 13,
        workbook_path: "projects/kavanagh/01-cost/Cost_Plan_v13.draft.xlsx",
        rows: [
          {
            ...invoiceLedger().rows[0]!,
            invoice_revision: 2,
            paid: true,
          },
        ],
      }),
    );

    await waitFor(() => expect(api.updateInvoice).toHaveBeenCalledTimes(2));
    expect(api.updateInvoice).toHaveBeenLastCalledWith(PROJECT_ID, "invoice-1", {
      expected_revision: 2,
      expected_cost_plan_version: 13,
      billing_month: "2026-04-01",
    });
  });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

function invoiceLedger(overrides: Partial<InvoiceLedger> = {}): InvoiceLedger {
  return {
    cost_plan_version: 12,
    workbook_path: WORKBOOK_PATH,
    rows: [
      {
        allocation_id: "allocation-1",
        invoice_id: "invoice-1",
        invoice_revision: 1,
        invoice_date: "2026-03-18",
        company: "Catenary Structures Pty Ltd",
        po_number: null,
        invoice_number: "CST-2601",
        description: "Preliminary structural scheme and civil constraints review",
        cost_item_key: null,
        cost_item_label: "Unidentified",
        amount_ex_gst: "12540.00",
        billing_month: "2026-03-01",
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
        budget: null,
      },
    ],
    ...overrides,
  };
}

function workbookPreview(): WorkbookPreview {
  const style = { fill_color: null, bold: false };
  const rows = [
    ["INVOICES REGISTER", "", "", "", "", "", "", "", ""],
    ["Kavanagh", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    [
      "Invoice Date",
      "Company",
      "PO Number",
      "Invoice Number",
      "Description",
      "Cost Item",
      "Amount ex GST",
      "Billing Month",
      "Paid?",
    ],
    [
      "18-Mar-26",
      "Catenary Structures Pty Ltd",
      "",
      "CST-2601",
      "Preliminary structural scheme and civil constraints review",
      "Unidentified",
      "$12,540",
      "Mar-26",
      "No",
    ],
  ];
  return {
    filename: "Cost_Plan_v12.draft.xlsx",
    workspace_path: WORKBOOK_PATH,
    warnings: [],
    sheets: [
      {
        name: "Invoices",
        column_count: 9,
        rows,
        styles: rows.map(() => Array.from({ length: 9 }, () => style)),
      },
    ],
  };
}
