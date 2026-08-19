import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InvoiceReviewPane } from "@/components/project/InvoiceReviewPane";
import type { InvoiceReview } from "@/lib/types/project";

function review(overrides: Partial<InvoiceReview> = {}): InvoiceReview {
  return {
    invoice_id: "inv-1",
    invoice_number: "INV-1O42",
    original_excerpt: "# TAX INVOICE\nInvoice number INV-1O42",
    machine: {
      invoice_number: "INV-1O42",
      supplier_name: "Acme",
      supplier_abn: "51000000680",
      invoice_date: "2026-03-18",
      subtotal_ex_gst: "100.00",
      gst: "10.00",
      total_including_gst: "110.00",
    },
    secondary: {
      invoice_number: null,
      supplier_name: null,
      supplier_abn: null,
      invoice_date: null,
      subtotal_ex_gst: null,
      gst: null,
      total_including_gst: null,
    },
    reviewed: {
      invoice_number: "INV-1042",
      supplier_name: null,
      supplier_abn: null,
      invoice_date: null,
      subtotal_ex_gst: null,
      gst: null,
      total_including_gst: null,
    },
    reconciliation: { invoice_number: "different" },
    issues: [],
    allocations: [
      {
        description: "Stage 1",
        amount_ex_gst: "100.00",
        cost_item_label: "Architect",
        mapping_method: "exact",
      },
    ],
    review_state: "ready_for_review",
    processing_status: "booked",
    revision: 1,
    ...overrides,
  };
}

describe("InvoiceReviewPane", () => {
  afterEach(() => {
    cleanup();
  });

  it("highlights fields that disagree and disables approve when error issues exist", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    const { rerender } = render(
      <InvoiceReviewPane review={review()} onApprove={onApprove} />,
    );

    const row = document.querySelector('[data-field="invoice_number"]');
    expect(row).toHaveAttribute("data-reconciliation", "different");
    expect(row?.className).toContain("bg-[var(--warn-bg)]");

    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(onApprove).toHaveBeenCalledTimes(1);

    rerender(
      <InvoiceReviewPane
        review={review({
          issues: [
            {
              code: "TOTAL_MISMATCH",
              severity: "error",
              field: "subtotal_ex_gst",
              message: "totals do not match",
            },
          ],
        })}
        onApprove={onApprove}
      />,
    );
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  });
});
