import { LoaderCircle, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { QuoteLedgerItem, QuoteLedgerResponse } from "@/lib/types/tender";
import { cn } from "@/lib/utils";

import { formatTenderMoney } from "./format";

export function QuoteLedgerPanel({
  comparisonId,
  quoteId,
  onClose,
}: {
  comparisonId: string;
  quoteId: string;
  onClose: () => void;
}) {
  const [ledger, setLedger] = useState<QuoteLedgerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getTenderQuoteLedger(comparisonId, quoteId);
        if (!cancelled) setLedger(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load quote ledger.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [comparisonId, quoteId]);

  const countedSum =
    ledger?.items.reduce((sum, item) => {
      return sum + sumCounted(item);
    }, 0) ?? 0;

  return (
    <div className="mb-3 rounded-md border bg-background p-3 text-sm">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <div className="font-medium">
            {ledger?.builder_name ?? "Quote"} ledger
          </div>
          <div className="text-xs text-muted-foreground">
            Status: {ledger?.status ?? "…"} · Stated{" "}
            {formatTenderMoney(ledger?.stated_total_cents)}
            {ledger?.stated_basis ? ` (${ledger.stated_basis} GST)` : ""}
          </div>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" /> Loading ledger…
        </div>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {ledger ? (
        <>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-background text-muted-foreground">
                <tr>
                  <th className="px-1 py-1 font-medium">Description</th>
                  <th className="px-1 py-1 font-medium">Page</th>
                  <th className="px-1 py-1 font-medium">Role</th>
                  <th className="px-1 py-1 text-right font-medium">Native</th>
                  <th className="px-1 py-1 text-right font-medium">Ex GST</th>
                </tr>
              </thead>
              <tbody>
                {ledger.items.map((item) => (
                  <LedgerRows key={item.figure_key} item={item} depth={0} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 space-y-0.5 border-t pt-2 text-xs">
            <div className="flex justify-between">
              <span>Counted</span>
              <span className="font-mono tabular-nums">
                {formatTenderMoney(countedSum)}
              </span>
            </div>
            <div
              className={cn(
                "flex justify-between",
                ledger.residual_cents !== 0 && "text-amber-700",
              )}
            >
              <span>Residual</span>
              <span className="font-mono tabular-nums">
                {formatTenderMoney(ledger.residual_cents)}
              </span>
            </div>
            <div className="flex justify-between font-medium">
              <span>Stated total</span>
              <span className="font-mono tabular-nums">
                {formatTenderMoney(ledger.stated_total_cents)}
              </span>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

function LedgerRows({ item, depth }: { item: QuoteLedgerItem; depth: number }) {
  const muted = !item.counted_in_total || item.duplicate_of_id != null;
  return (
    <>
      <tr className={cn(muted && "text-muted-foreground")}>
        <td className="px-1 py-1" style={{ paddingLeft: `${depth * 12 + 4}px` }}>
          {item.description_raw}
          {item.duplicate_of_id ? (
            <span className="ml-1 rounded bg-muted px-1 text-[0.65rem]">reprint</span>
          ) : null}
          {item.is_rollup ? (
            <span className="ml-1 rounded bg-muted px-1 text-[0.65rem]">rollup</span>
          ) : null}
        </td>
        <td className="px-1 py-1">{item.page_no ?? "—"}</td>
        <td className="px-1 py-1">{item.role ?? "—"}</td>
        <td className="px-1 py-1 text-right font-mono tabular-nums">
          {formatTenderMoney(item.amount_cents)}
        </td>
        <td className="px-1 py-1 text-right font-mono tabular-nums">
          {formatTenderMoney(item.amount_ex_gst_cents)}
        </td>
      </tr>
      {item.children.map((child) => (
        <LedgerRows key={child.figure_key} item={child} depth={depth + 1} />
      ))}
    </>
  );
}

function sumCounted(item: QuoteLedgerItem): number {
  const self = item.counted_in_total ? (item.amount_cents ?? 0) : 0;
  return self + item.children.reduce((sum, child) => sum + sumCounted(child), 0);
}
