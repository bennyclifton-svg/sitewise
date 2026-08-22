import { Check, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { InvoiceReviewPane } from "@/components/project/InvoiceReviewPane";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { pulseKeys } from "@/lib/queries/pulse";
import { workbenchKeys } from "@/lib/queries/workbench";
import type { InvoiceLedger, InvoiceReview } from "@/lib/types/project";
import { cn } from "@/lib/utils";

type InvoiceEdit =
  | {
      kind: "allocation";
      allocationId: string;
      costItemKey: string;
    }
  | {
      kind: "invoice";
      invoiceId: string;
      changes: { paid?: boolean; billing_month?: string };
    };

export function CostInvoiceRegister({
  projectId,
  revision = null,
  reviewInvoiceId = null,
  ledger,
}: {
  projectId: string;
  /** When the published Cost Plan revision changes, reload the register. */
  revision?: number | null;
  reviewInvoiceId?: string | null;
  /** Parent-owned ledger. Omit to load from the workbench cache. */
  ledger?: InvoiceLedger | null;
}) {
  return (
    <CostInvoiceRegisterState
      projectId={projectId}
      revision={revision}
      reviewInvoiceId={reviewInvoiceId}
      ledger={ledger}
    />
  );
}

function readCachedInvoiceLedger(projectId: string): InvoiceLedger | null {
  return (
    queryClient.getQueryData<InvoiceLedger>(
      workbenchKeys.invoiceLedger(projectId),
    ) ?? null
  );
}

function rememberInvoiceLedger(projectId: string, ledger: InvoiceLedger): void {
  queryClient.setQueryData(workbenchKeys.invoiceLedger(projectId), ledger);
}

function CostInvoiceRegisterState({
  projectId,
  revision,
  reviewInvoiceId,
  ledger: ledgerProp,
}: {
  projectId: string;
  revision: number | null;
  reviewInvoiceId?: string | null;
  ledger?: InvoiceLedger | null;
}) {
  const [ledger, setLedger] = useState<InvoiceLedger | null>(
    () => ledgerProp ?? readCachedInvoiceLedger(projectId),
  );
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [review, setReview] = useState<InvoiceReview | null>(null);
  const confirmedLedgerRef = useRef<InvoiceLedger | null>(
    ledgerProp ?? readCachedInvoiceLedger(projectId),
  );
  const queueRef = useRef<InvoiceEdit[]>([]);
  const drainingRef = useRef(false);
  const projectIdRef = useRef<string | null>(projectId);
  const loadedRevisionRef = useRef(revision);

  useEffect(() => {
    return () => {
      projectIdRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ledgerProp) return;
    if (queueRef.current.length > 0 || drainingRef.current) return;
    confirmedLedgerRef.current = ledgerProp;
    setLedger(replayEdits(ledgerProp, queueRef.current));
    setError(null);
  }, [ledgerProp]);

  useEffect(() => {
    if (ledgerProp) return;
    let cancelled = false;
    if (queueRef.current.length > 0 || drainingRef.current) {
      return () => {
        cancelled = true;
      };
    }
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
        confirmedLedgerRef.current = data;
        setLedger(replayEdits(data, queueRef.current));
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Invoice register could not load.",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, revision, ledgerProp]);

  function enqueue(edit: InvoiceEdit) {
    const confirmed = confirmedLedgerRef.current;
    if (!confirmed) return;
    mergeQueuedEdit(queueRef.current, edit);
    setLedger(replayEdits(confirmed, queueRef.current));
    setPendingCount(queueRef.current.length + (drainingRef.current ? 1 : 0));
    setError(null);
    setSaveMessage(null);
    void drainQueue();
  }

  async function drainQueue() {
    if (drainingRef.current) return;
    const editingProjectId = projectIdRef.current;
    if (!editingProjectId) return;
    drainingRef.current = true;
    let latestSaved: InvoiceLedger | null = null;
    let conflictRetries = 0;

    try {
      while (queueRef.current.length > 0) {
        const edit = queueRef.current[0];
        if (!edit) break;
        setPendingCount(queueRef.current.length);
        const confirmed = confirmedLedgerRef.current;
        if (!confirmed) throw new Error("Invoice register is not ready.");
        try {
          const updated = await commitEdit(editingProjectId, confirmed, edit);
          if (projectIdRef.current !== editingProjectId) return;
          queueRef.current.shift();
          conflictRetries = 0;
          latestSaved = updated;
          confirmedLedgerRef.current = updated;
          setLedger(replayEdits(updated, queueRef.current));
        } catch (saveError) {
          if (
            saveError instanceof ApiError &&
            saveError.status === 409 &&
            projectIdRef.current === editingProjectId
          ) {
            const latest = await api.getInvoiceLedger(editingProjectId);
            if (projectIdRef.current !== editingProjectId) return;
            latestSaved = latest;
            confirmedLedgerRef.current = latest;
            rememberInvoiceLedger(editingProjectId, latest);
            setLedger(replayEdits(latest, queueRef.current));
            setError(
              "An invoice changed elsewhere. Remaining edits will use the latest values.",
            );
            conflictRetries += 1;
            if (conflictRetries > 1) queueRef.current.shift();
            continue;
          }
          queueRef.current = [];
          if (projectIdRef.current === editingProjectId) {
            setLedger(confirmedLedgerRef.current);
            setError(
              saveError instanceof ApiError
                ? saveError.message
                : "Invoice change could not be saved.",
            );
          }
          return;
        }
      }
      if (latestSaved && projectIdRef.current === editingProjectId) {
        rememberInvoiceLedger(editingProjectId, latestSaved);
        setSaveMessage(`Saved against Cost Plan v${latestSaved.cost_plan_version}`);
      }
    } finally {
      drainingRef.current = false;
      if (projectIdRef.current === editingProjectId) {
        setPendingCount(queueRef.current.length);
      }
      if (projectIdRef.current && queueRef.current.length > 0) void drainQueue();
    }
  }

  async function openReview(invoiceId: string) {
    try {
      setReview(await api.getInvoiceReview(projectId, invoiceId));
      setError(null);
    } catch (loadError) {
      setError(
        loadError instanceof ApiError
          ? loadError.message
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
          setError(null);
        }
      },
      (loadError) => {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
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
      setError(null);
      void queryClient.invalidateQueries({ queryKey: pulseKeys.feed(projectId) });
    } catch (decideError) {
      setError(
        decideError instanceof ApiError
          ? decideError.message
          : "Invoice decision could not be saved.",
      );
    }
  }

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
      {saveMessage || pendingCount > 0 ? (
        <p className="flex items-center gap-1 border-b px-3 py-2 text-xs text-muted-foreground">
          {pendingCount > 0 ? (
            <>
              <Loader2 className="size-3 animate-spin" aria-hidden />
              Saving {pendingCount} invoice change{pendingCount === 1 ? "" : "s"}…
            </>
          ) : (
            saveMessage
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
                          enqueue({
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
                          enqueue({
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
                        enqueue({
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

function mergeQueuedEdit(queue: InvoiceEdit[], next: InvoiceEdit) {
  const last = queue.at(-1);
  if (
    last?.kind === "invoice" &&
    next.kind === "invoice" &&
    last.invoiceId === next.invoiceId
  ) {
    last.changes = { ...last.changes, ...next.changes };
    return;
  }
  if (
    last?.kind === "allocation" &&
    next.kind === "allocation" &&
    last.allocationId === next.allocationId
  ) {
    last.costItemKey = next.costItemKey;
    return;
  }
  queue.push(next);
}

function replayEdits(ledger: InvoiceLedger, edits: InvoiceEdit[]): InvoiceLedger {
  return edits.reduce((current, edit) => applyEdit(current, edit), ledger);
}

function applyEdit(ledger: InvoiceLedger, edit: InvoiceEdit): InvoiceLedger {
  if (edit.kind === "allocation") {
    const option = ledger.cost_items.find((item) => item.item_key === edit.costItemKey);
    return {
      ...ledger,
      rows: ledger.rows.map((row) =>
        row.allocation_id === edit.allocationId
          ? {
              ...row,
              cost_item_key: edit.costItemKey,
              cost_item_label: option?.item ?? row.cost_item_label,
              review_status: "mapped",
              mapping_method: "manual",
            }
          : row,
      ),
    };
  }
  return {
    ...ledger,
    rows: ledger.rows.map((row) =>
      row.invoice_id === edit.invoiceId ? { ...row, ...edit.changes } : row,
    ),
  };
}

async function commitEdit(
  projectId: string,
  confirmed: InvoiceLedger,
  edit: InvoiceEdit,
): Promise<InvoiceLedger> {
  if (edit.kind === "allocation") {
    const row = confirmed.rows.find(
      (candidate) => candidate.allocation_id === edit.allocationId,
    );
    if (!row) throw new Error("The invoice allocation is no longer available.");
    return api.updateInvoiceAllocation(projectId, edit.allocationId, {
      expected_revision: row.invoice_revision,
      expected_cost_plan_version: confirmed.cost_plan_version,
      cost_item_key: edit.costItemKey,
    });
  }
  const row = confirmed.rows.find(
    (candidate) => candidate.invoice_id === edit.invoiceId,
  );
  if (!row) throw new Error("The invoice is no longer available.");
  return api.updateInvoice(projectId, edit.invoiceId, {
    expected_revision: row.invoice_revision,
    expected_cost_plan_version: confirmed.cost_plan_version,
    ...edit.changes,
  });
}
