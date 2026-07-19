import { LoaderCircle, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  TenderCellItemsResponse,
  TenderMatrixMappingChoice,
  TenderQaItem,
  TenderQaResolveRequest,
  TenderTaxonomyCell,
} from "@/lib/types/tender";

import { formatTenderMoney, formatTenderStatus } from "./format";
import { MatrixQaPanel } from "./MatrixQaPanel";

const NOT_ITEMISED_CODE = "_not_itemised";

/**
 * Cell drill-down: line items for the quote/cell, with QA / mapping choices beneath.
 */
export function TenderCellDrilldown({
  comparisonId,
  cellCode,
  cellName,
  quoteId,
  quoteName,
  items,
  choices,
  taxonomy,
  resolving,
  error,
  onClose,
  onAccept,
  onResolve,
  onMappingChoice,
}: {
  comparisonId: string;
  cellCode: string;
  cellName: string;
  quoteId: string;
  quoteName: string | null;
  items: TenderQaItem[];
  choices: TenderMatrixMappingChoice[];
  taxonomy: TenderTaxonomyCell[];
  resolving: string | null;
  error: string | null;
  onClose: () => void;
  onAccept: (item: TenderQaItem) => void;
  onResolve: (item: TenderQaItem, request: TenderQaResolveRequest) => Promise<void>;
  onMappingChoice: (mappingId: string, cellCode: string) => Promise<void>;
}) {
  const [cellItems, setCellItems] = useState<TenderCellItemsResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const skipFetch = cellCode === NOT_ITEMISED_CODE;

  useEffect(() => {
    if (skipFetch) {
      setCellItems(null);
      setLoadError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await api.getTenderCellItems(comparisonId, cellCode, quoteId);
        if (!cancelled) setCellItems(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof ApiError ? err.message : "Could not load line items.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [comparisonId, cellCode, quoteId, skipFetch]);

  const hasQa = items.length > 0 || choices.length > 0;

  return (
    <div className="border-b bg-background">
      <div className="px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium">
            {cellName}
            <span className="ml-2 font-mono text-xs text-muted-foreground">{cellCode}</span>
            {quoteName ? (
              <span className="ml-2 text-xs text-muted-foreground">{quoteName}</span>
            ) : null}
          </p>
          <button
            type="button"
            className="cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close cell details"
            onClick={onClose}
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>

        {skipFetch ? (
          <p className="mt-2 text-sm text-muted-foreground">
            Remainder of the computed ex-GST total not mapped to a taxonomy row.
          </p>
        ) : null}

        {isLoading ? (
          <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Loading line items…
          </p>
        ) : null}

        {loadError ? (
          <p className="mt-2 text-sm text-destructive">{loadError}</p>
        ) : null}

        {cellItems ? (
          <div className="mt-3">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="py-1 pr-2 font-medium">Description</th>
                  <th className="py-1 pr-2 font-medium">Page</th>
                  <th className="py-1 pr-2 font-medium">Role</th>
                  <th className="py-1 pr-2 font-medium">Frac</th>
                  <th className="py-1 text-right font-medium">Ex GST</th>
                </tr>
              </thead>
              <tbody>
                {cellItems.items.map((item) => (
                  <tr key={item.line_item_id} className="border-b border-border/60">
                    <td className="max-w-[20rem] truncate py-1.5 pr-2" title={item.description_raw}>
                      {item.description_raw}
                    </td>
                    <td className="py-1.5 pr-2 font-mono text-xs text-muted-foreground">
                      {item.page_no ?? "—"}
                    </td>
                    <td className="py-1.5 pr-2 text-xs">
                      {item.role ? formatTenderStatus(item.role) : "—"}
                    </td>
                    <td className="py-1.5 pr-2 font-mono text-xs tabular-nums">
                      {item.allocation_fraction.toFixed(2)}
                    </td>
                    <td className="py-1.5 text-right font-mono text-xs tabular-nums">
                      {formatTenderMoney(
                        item.amount_ex_gst_cents != null
                          ? Math.round(item.amount_ex_gst_cents * item.allocation_fraction)
                          : item.amount_cents != null
                            ? Math.round(item.amount_cents * item.allocation_fraction)
                            : null,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4} className="pt-2 text-xs font-medium text-muted-foreground">
                    Sum (ex GST)
                  </td>
                  <td className="pt-2 text-right font-mono text-sm font-semibold tabular-nums">
                    {formatTenderMoney(cellItems.sum_ex_gst_cents)}
                  </td>
                </tr>
              </tfoot>
            </table>
            {!cellItems.items.length ? (
              <p className="mt-2 text-sm text-muted-foreground">No mapped line items.</p>
            ) : null}
          </div>
        ) : null}
      </div>

      {hasQa ? (
        <MatrixQaPanel
          cellCode={cellCode}
          cellName={cellName}
          quoteName={quoteName}
          items={items}
          choices={choices}
          taxonomy={taxonomy}
          resolving={resolving}
          error={error}
          onClose={onClose}
          onAccept={onAccept}
          onResolve={onResolve}
          onMappingChoice={onMappingChoice}
          embedded
        />
      ) : null}
    </div>
  );
}

export { NOT_ITEMISED_CODE };
