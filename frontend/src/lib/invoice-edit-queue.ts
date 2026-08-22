import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
import type { InvoiceLedger } from "@/lib/types/project";

export type InvoiceEdit =
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

export type InvoiceEditSnapshot = {
  ledger: InvoiceLedger | null;
  pendingCount: number;
  error: string | null;
  saveMessage: string | null;
};

type ProjectQueue = {
  edits: InvoiceEdit[];
  confirmed: InvoiceLedger | null;
  draining: boolean;
  listeners: Set<(snapshot: InvoiceEditSnapshot) => void>;
  error: string | null;
  saveMessage: string | null;
};

const STORAGE_PREFIX = "clerk:invoice-edits:";
const queues = new Map<string, ProjectQueue>();

function storageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function loadStoredEdits(projectId: string): InvoiceEdit[] {
  if (typeof sessionStorage === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(storageKey(projectId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as InvoiceEdit[]) : [];
  } catch {
    return [];
  }
}

function persistEdits(projectId: string, edits: InvoiceEdit[]): void {
  if (typeof sessionStorage === "undefined") return;
  if (edits.length === 0) {
    sessionStorage.removeItem(storageKey(projectId));
    return;
  }
  sessionStorage.setItem(storageKey(projectId), JSON.stringify(edits));
}

function ensureQueue(projectId: string): ProjectQueue {
  const existing = queues.get(projectId);
  if (existing) return existing;
  const created: ProjectQueue = {
    edits: loadStoredEdits(projectId),
    confirmed:
      queryClient.getQueryData<InvoiceLedger>(
        workbenchKeys.invoiceLedger(projectId),
      ) ?? null,
    draining: false,
    listeners: new Set(),
    error: null,
    saveMessage: null,
  };
  queues.set(projectId, created);
  return created;
}

function ledgerRevisionScore(ledger: InvoiceLedger | null): number {
  if (!ledger) return -1;
  return ledger.rows.reduce((sum, row) => sum + row.invoice_revision, 0);
}

function ledgersMatch(left: InvoiceLedger | null, right: InvoiceLedger | null): boolean {
  if (left === right) return true;
  if (!left || !right) return false;
  if (left.cost_plan_version !== right.cost_plan_version) return false;
  if (left.rows.length !== right.rows.length) return false;
  return left.rows.every((row, index) => {
    const other = right.rows[index];
    return (
      other != null &&
      row.allocation_id === other.allocation_id &&
      row.invoice_revision === other.invoice_revision &&
      row.cost_item_key === other.cost_item_key &&
      row.paid === other.paid &&
      row.billing_month === other.billing_month
    );
  });
}

function remember(projectId: string, ledger: InvoiceLedger): void {
  queryClient.setQueryData(workbenchKeys.invoiceLedger(projectId), ledger);
}

export function replayEdits(
  ledger: InvoiceLedger,
  edits: InvoiceEdit[],
): InvoiceLedger {
  return edits.reduce((current, edit) => applyEdit(current, edit), ledger);
}

export function applyEdit(ledger: InvoiceLedger, edit: InvoiceEdit): InvoiceLedger {
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

export function mergeQueuedEdit(
  queue: InvoiceEdit[],
  next: InvoiceEdit,
  skipFirst = false,
): void {
  const start = skipFirst ? 1 : 0;
  for (let index = queue.length - 1; index >= start; index -= 1) {
    const edit = queue[index];
    if (
      next.kind === "invoice" &&
      edit?.kind === "invoice" &&
      edit.invoiceId === next.invoiceId
    ) {
      edit.changes = { ...edit.changes, ...next.changes };
      return;
    }
    if (
      next.kind === "allocation" &&
      edit?.kind === "allocation" &&
      edit.allocationId === next.allocationId
    ) {
      edit.costItemKey = next.costItemKey;
      return;
    }
  }
  queue.push(next);
}

function snapshotOf(projectId: string): InvoiceEditSnapshot {
  const queue = ensureQueue(projectId);
  return {
    ledger: queue.confirmed ? replayEdits(queue.confirmed, queue.edits) : null,
    pendingCount: queue.edits.length,
    error: queue.error,
    saveMessage: queue.saveMessage,
  };
}

function emit(projectId: string): void {
  const snapshot = snapshotOf(projectId);
  for (const listener of ensureQueue(projectId).listeners) listener(snapshot);
}

export function resetInvoiceEditQueues(projectId?: string): void {
  if (projectId) {
    persistEdits(projectId, []);
    queues.delete(projectId);
    return;
  }
  for (const id of queues.keys()) persistEdits(id, []);
  queues.clear();
}

export function hydrateInvoiceLedger(projectId: string, ledger: InvoiceLedger): void {
  const queue = ensureQueue(projectId);
  const incoming = ledgerRevisionScore(ledger);
  const current = ledgerRevisionScore(queue.confirmed);
  if (queue.edits.length > 0 || queue.draining) {
    if (incoming > current) {
      queue.confirmed = ledger;
      emit(projectId);
    }
    return;
  }
  if (queue.confirmed && (incoming < current || ledgersMatch(queue.confirmed, ledger))) {
    return;
  }
  queue.confirmed = ledger;
  remember(projectId, ledger);
  emit(projectId);
}

export function enqueueInvoiceEdit(projectId: string, edit: InvoiceEdit): void {
  const queue = ensureQueue(projectId);
  mergeQueuedEdit(queue.edits, edit, queue.draining);
  persistEdits(projectId, queue.edits);
  queue.error = null;
  queue.saveMessage = null;
  emit(projectId);
  void drainInvoiceEdits(projectId);
}

export function subscribeInvoiceEdits(
  projectId: string,
  listener: (snapshot: InvoiceEditSnapshot) => void,
): () => void {
  const queue = ensureQueue(projectId);
  queue.listeners.add(listener);
  listener(snapshotOf(projectId));
  if (queue.edits.length > 0) void drainInvoiceEdits(projectId);
  return () => {
    queue.listeners.delete(listener);
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

export async function drainInvoiceEdits(projectId: string): Promise<void> {
  const queue = ensureQueue(projectId);
  if (queue.draining) return;
  queue.draining = true;
  emit(projectId);
  try {
    while (queue.edits.length > 0) {
      const edit = queue.edits[0];
      if (!edit) break;
      if (!queue.confirmed) throw new Error("Invoice register is not ready.");
      emit(projectId);
      try {
        const updated = await commitEdit(projectId, queue.confirmed, edit);
        queue.edits.shift();
        persistEdits(projectId, queue.edits);
        queue.confirmed = updated;
        remember(projectId, updated);
        queue.saveMessage = `Saved against Cost Plan v${updated.cost_plan_version}`;
        emit(projectId);
      } catch (saveError) {
        if (saveError instanceof ApiError && saveError.status === 409) {
          const latest = await api.getInvoiceLedger(projectId);
          queue.confirmed = latest;
          remember(projectId, latest);
          queue.error =
            "An invoice changed elsewhere. Remaining edits will use the latest values.";
          emit(projectId);
          try {
            const retried = await commitEdit(projectId, latest, edit);
            queue.edits.shift();
            persistEdits(projectId, queue.edits);
            queue.confirmed = retried;
            remember(projectId, retried);
            queue.saveMessage = `Saved against Cost Plan v${retried.cost_plan_version}`;
            queue.error = null;
            emit(projectId);
          } catch (retryError) {
            queue.edits.shift();
            persistEdits(projectId, queue.edits);
            queue.error =
              retryError instanceof ApiError
                ? retryError.message
                : "Invoice change could not be saved.";
            emit(projectId);
          }
          continue;
        }
        queue.edits.shift();
        persistEdits(projectId, queue.edits);
        queue.error =
          saveError instanceof ApiError
            ? saveError.message
            : "Invoice change could not be saved.";
        emit(projectId);
      }
    }
  } finally {
    queue.draining = false;
    emit(projectId);
    if (queue.edits.length > 0) void drainInvoiceEdits(projectId);
  }
}
