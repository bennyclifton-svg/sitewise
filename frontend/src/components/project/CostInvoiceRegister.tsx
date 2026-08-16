import { Check, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { InvoiceLedger } from "@/lib/types/project";
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
}: {
  projectId: string;
  /** When the published Cost Plan revision changes, reload the register. */
  revision?: number | null;
}) {
  return (
    <CostInvoiceRegisterState projectId={projectId} revision={revision} />
  );
}

function CostInvoiceRegisterState({
  projectId,
  revision,
}: {
  projectId: string;
  revision: number | null;
}) {
  const [ledger, setLedger] = useState<InvoiceLedger | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const confirmedLedgerRef = useRef<InvoiceLedger | null>(null);
  const queueRef = useRef<InvoiceEdit[]>([]);
  const drainingRef = useRef(false);
  const projectIdRef = useRef<string | null>(projectId);

  useEffect(() => {
    return () => {
      projectIdRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (queueRef.current.length > 0 || drainingRef.current) {
      return () => {
        cancelled = true;
      };
    }

    void api.getInvoiceLedger(projectId).then(
      (data) => {
        if (cancelled) return;
        confirmedLedgerRef.current = data;
        setLedger(replayEdits(data, queueRef.current));
        setError(null);
      },
      (loadError) => {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Invoice register could not load.",
          );
        }
      },
    );

    return () => {
      cancelled = true;
    };
  }, [projectId, revision]);

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
        <table className="cost-invoice-table w-full min-w-[64rem] text-sm">
          <thead className="sticky top-0 z-10 text-left">
            <tr>
              <th className="px-3 py-2">Invoice Date</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">PO</th>
              <th className="px-3 py-2">Invoice #</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Cost Item</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Billing Month</th>
              <th className="px-3 py-2">Paid?</th>
            </tr>
          </thead>
          <tbody>
            {ledger.rows.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  className="px-3 py-8 text-center text-muted-foreground"
                >
                  No invoices in the register yet. Upload invoice files, then
                  Process invoices to populate this list.
                </td>
              </tr>
            ) : (
              ledger.rows.map((row) => (
                <tr key={row.allocation_id}>
                  <td className="px-3 py-2 whitespace-nowrap">{row.invoice_date}</td>
                  <td className="px-3 py-2">{row.company}</td>
                  <td className="px-3 py-2">{row.po_number ?? ""}</td>
                  <td className="px-3 py-2">{row.invoice_number}</td>
                  <td className="px-3 py-2">{row.description}</td>
                  <td className="cost-invoice-cell--editable px-3 py-1.5">
                    <select
                      className={cn(
                        "cost-plan-field h-8 w-full min-w-40 px-2 text-xs",
                        row.review_status === "needs_review" && "cost-plan-field--attention",
                      )}
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
                  <td className="px-3 py-2 text-right tabular-nums">
                    ${Number(row.amount_ex_gst).toLocaleString()}
                  </td>
                  <td className="cost-invoice-cell--editable px-3 py-1.5">
                    <input
                      type="month"
                      className="cost-plan-field h-8 px-2 text-xs"
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
                  <td className="px-3 py-1.5">
                    <button
                      type="button"
                      className={cn(
                        "cost-invoice-paid-toggle inline-flex h-8 min-w-14 items-center justify-center gap-1 px-2 text-xs",
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
