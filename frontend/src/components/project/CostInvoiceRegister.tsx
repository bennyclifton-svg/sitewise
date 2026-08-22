import { Check, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { InvoiceReviewPane } from "@/components/project/InvoiceReviewPane";
import { api } from "@/lib/api";
import {
  enqueueInvoiceEdit,
  hydrateInvoiceLedger,
  subscribeInvoiceEdits,
  type InvoiceEditSnapshot,
} from "@/lib/invoice-edit-queue";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { pulseKeys } from "@/lib/queries/pulse";
import { workbenchKeys } from "@/lib/queries/workbench";
import type { InvoiceLedger, InvoiceReview } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function CostInvoiceRegister({
  projectId,
  revision = null,
  reviewInvoiceId = null,
  ledger,
  onLedgerChange,
}: {
  projectId: string;
  /** When the published Cost Plan revision changes, reload the register. */
  revision?: number | null;
  reviewInvoiceId?: string | null;
  /** Parent-owned ledger. Omit to load from the workbench cache. */
  ledger?: InvoiceLedger | null;
  onLedgerChange?: (ledger: InvoiceLedger) => void;
}) {
  return (
    <CostInvoiceRegisterState
      projectId={projectId}
      revision={revision}
      reviewInvoiceId={reviewInvoiceId}
      ledger={ledger}
      onLedgerChange={onLedgerChange}
    />
  );
}

function CostInvoiceRegisterState({
  projectId,
  revision,
  reviewInvoiceId,
  ledger: ledgerProp,
  onLedgerChange,
}: {
  projectId: string;
  revision: number | null;
  reviewInvoiceId?: string | null;
  ledger?: InvoiceLedger | null;
  onLedgerChange?: (ledger: InvoiceLedger) => void;
}) {
  const [snapshot, setSnapshot] = useState<InvoiceEditSnapshot>(() => ({
    ledger:
      ledgerProp ??
      queryClient.getQueryData<InvoiceLedger>(
        workbenchKeys.invoiceLedger(projectId),
      ) ??
      null,
    pendingCount: 0,
    error: null,
    saveMessage: null,
  }));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [review, setReview] = useState<InvoiceReview | null>(null);
  const onLedgerChangeRef = useRef(onLedgerChange);
  const loadedRevisionRef = useRef(revision);

  useEffect(() => {
    onLedgerChangeRef.current = onLedgerChange;
  }, [onLedgerChange]);

  useEffect(() => {
    return subscribeInvoiceEdits(projectId, (next) => {
      setSnapshot(next);
      if (next.ledger) onLedgerChangeRef.current?.(next.ledger);
    });
  }, [projectId]);

  useEffect(() => {
    if (!ledgerProp) return;
    hydrateInvoiceLedger(projectId, ledgerProp);
  }, [projectId, ledgerProp]);

  useEffect(() => {
    if (ledgerProp) return;
    let cancelled = false;
    const fresh = loadedRevisionRef.current !== revision;
    loadedRevisionRef.current = revision;

    void (async () => {
      try {
        if (fresh) {
          await queryClient.invalidateQueries({
            queryKey: workbenchKeys.invoiceLedger(projectId),
          });
        }
        const data = await queryClient.fetchQuery({
          queryKey: workbenchKeys.invoiceLedger(projectId),
          queryFn: () => api.getInvoiceLedger(projectId),
        });
        if (cancelled) return;
        hydrateInvoiceLedger(projectId, data);
        setLoadError(null);
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof ApiError
              ? error.message
              : "Invoice register could not load.",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, revision, ledgerProp]);

  async function openReview(invoiceId: string) {
    try {
      setReview(await api.getInvoiceReview(projectId, invoiceId));
      setLoadError(null);
    } catch (error) {
      setLoadError(
        error instanceof ApiError
          ? error.message
          : "Invoice review could not load.",
      );
    }
  }

  useEffect(() => {
    if (!reviewInvoiceId) return;
    let cancelled = false;
    void api.getInvoiceReview(projectId, reviewInvoiceId).then(
      (data) => {
        if (!cancelled) {
          setReview(data);
          setLoadError(null);
        }
      },
      (error) => {
        if (!cancelled) {
          setLoadError(
            error instanceof ApiError
              ? error.message
              : "Invoice review could not load.",
          );
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [projectId, reviewInvoiceId]);

  async function decide(decision: "hold" | "reject" | "approve") {
    if (!review) return;
    try {
      setReview(await api.decideInvoice(projectId, review.invoice_id, { decision }));
      setLoadError(null);
      void queryClient.invalidateQueries({ queryKey: pulseKeys.feed(projectId) });
    } catch (error) {
      setLoadError(
        error instanceof ApiError
          ? error.message
          : "Invoice decision could not be saved.",
      );
    }
  }

  const ledger = snapshot.ledger;
  const error = snapshot.error ?? loadError;

  if (!ledger && !error) {
    return (
      <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
        Loading invoices…
      </div>
    );
  }

  if (!ledger) {
    return <p className="p-3 text-sm text-destructive">{error}</p>;
  }

  return (
    <div className="cost-invoice-register flex flex-col">
      {error ? (
        <p className="border-b px-3 py-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      {snapshot.saveMessage || snapshot.pendingCount > 0 ? (
        <p className="flex items-center gap-1 border-b px-3 py-2 text-xs text-muted-foreground">
          {snapshot.pendingCount > 0 ? (
            <>
              <Loader2 className="size-3 animate-spin" aria-hidden />
              Saving {snapshot.pendingCount} invoice change
              {snapshot.pendingCount === 1 ? "" : "s"}…
            </>
          ) : (
            snapshot.saveMessage
          )}
        </p>
      ) : null}
      <div className="max-h-[32rem] overflow-auto">
        <table className="cost-invoice-table">
          <colgroup>
            <col className="cost-invoice-col-date" />
            <col className="cost-invoice-col-company" />
            <col className="cost-invoice-col-po" />
            <col className="cost-invoice-col-number" />
            <col className="cost-invoice-col-description" />
            <col className="cost-invoice-col-item" />
            <col className="cost-invoice-col-amount" />
            <col className="cost-invoice-col-month" />
            <col className="cost-invoice-col-paid" />
          </colgroup>
          <thead className="sticky top-0 z-10 text-left">
            <tr>
              <th>Invoice Date</th>
              <th>Company</th>
              <th>PO</th>
              <th>Invoice #</th>
              <th>Description</th>
              <th>Cost Item</th>
              <th className="text-right">Amount</th>
              <th>Billing Month</th>
              <th>Paid?</th>
            </tr>
          </thead>
          <tbody>
            {ledger.rows.length === 0 ? (
              <tr>
                <td colSpan={9} className="cost-invoice-empty">
                  No invoices in the register yet. Upload invoice files, then
                  Process invoices to populate this list.
                </td>
              </tr>
            ) : (
              ledger.rows.map((row) => (
                <tr key={row.allocation_id}>
                  <td title={row.invoice_date}>{row.invoice_date}</td>
                  <td title={row.company}>{row.company}</td>
                  <td title={row.po_number ?? undefined}>{row.po_number ?? ""}</td>
                  <td title={row.invoice_number}>
                    <button
                      type="button"
                      className="cost-invoice-number-link"
                      onClick={() => void openReview(row.invoice_id)}
                    >
                      {row.invoice_number}
                    </button>
                  </td>
                  <td title={row.description}>{row.description}</td>
                  <td
                    className={cn(
                      "cost-invoice-cell--editable",
                      row.review_status === "needs_review" &&
                        "cost-invoice-cell--attention",
                    )}
                  >
                    <select
                      className="cost-invoice-field"
                      value={row.cost_item_key ?? ""}
                      aria-label={`Cost item for invoice ${row.invoice_number}: ${row.description}`}
                      onChange={(event) => {
                        if (event.target.value) {
                          enqueueInvoiceEdit(projectId, {
                            kind: "allocation",
                            allocationId: row.allocation_id,
                            costItemKey: event.target.value,
                          });
                        }
                      }}
                    >
                      <option value="" disabled>
                        Choose cost item
                      </option>
                      {costItemGroups(ledger).map(([category, items]) => (
                        <optgroup key={category} label={category}>
                          {items.map((item) => (
                            <option key={item.item_key} value={item.item_key}>
                              {item.cost_code} · {item.item}
                              {item.budget === null ? " · TBC" : ""}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </td>
                  <td className="cost-invoice-cell--amount">
                    ${Number(row.amount_ex_gst).toLocaleString()}
                  </td>
                  <td className="cost-invoice-cell--editable">
                    <input
                      type="month"
                      className="cost-invoice-field"
                      value={row.billing_month.slice(0, 7)}
                      aria-label={`Billing month for invoice ${row.invoice_number}`}
                      onChange={(event) => {
                        if (event.target.value) {
                          enqueueInvoiceEdit(projectId, {
                            kind: "invoice",
                            invoiceId: row.invoice_id,
                            changes: {
                              billing_month: `${event.target.value}-01`,
                            },
                          });
                        }
                      }}
                    />
                  </td>
                  <td className="cost-invoice-cell--editable">
                    <button
                      type="button"
                      className={cn(
                        "cost-invoice-paid-toggle",
                        row.paid && "cost-invoice-paid-toggle--paid",
                      )}
                      aria-pressed={row.paid}
                      aria-label={`Mark invoice ${row.invoice_number} ${
                        row.paid ? "unpaid" : "paid"
                      }`}
                      onClick={() =>
                        enqueueInvoiceEdit(projectId, {
                          kind: "invoice",
                          invoiceId: row.invoice_id,
                          changes: { paid: !row.paid },
                        })
                      }
                    >
                      {row.paid ? <Check className="size-3" aria-hidden /> : null}
                      {row.paid ? "Yes" : "No"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {review ? (
        <div className="border-t border-[var(--border-hair)] p-3">
          <InvoiceReviewPane
            review={review}
            onHold={() => void decide("hold")}
            onReject={() => void decide("reject")}
            onApprove={() => void decide("approve")}
          />
        </div>
      ) : null}
    </div>
  );
}

function costItemGroups(
  ledger: InvoiceLedger,
): [string, InvoiceLedger["cost_items"]][] {
  const groups = new Map<string, InvoiceLedger["cost_items"]>();
  for (const item of ledger.cost_items) {
    const group = groups.get(item.category) ?? [];
    group.push(item);
    groups.set(item.category, group);
  }
  return [...groups.entries()];
}
