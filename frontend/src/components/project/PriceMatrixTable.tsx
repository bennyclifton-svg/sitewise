import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { priceMatrixTsv, type PriceMatrix } from "@/lib/price-matrix";

export function PriceMatrixTable({ matrix }: { matrix: PriceMatrix }) {
  const [showNotes, setShowNotes] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  useEffect(() => {
    if (copyState !== "copied") return;
    const timer = window.setTimeout(() => setCopyState("idle"), 2000);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(priceMatrixTsv(matrix));
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

  const itemCount = matrix.rows.length - 3;
  return (
    <div className="my-4">
      <div className="mb-1 flex flex-wrap items-center justify-end gap-1 print:hidden">
        <Button type="button" variant="ghost" size="sm" aria-pressed={showNotes} onClick={() => setShowNotes(!showNotes)}>
          {showNotes ? "Compact view" : "Separate notes"}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => void copy()}>
          {copyState === "copied" ? <Check aria-hidden className="size-3.5" /> : <Copy aria-hidden className="size-3.5" />}
          {copyState === "copied" ? "Copied" : "Copy for Excel"}
        </Button>
      </div>
      {copyState === "failed" && <p role="alert" className="mb-2 text-sm text-destructive">Couldn’t copy. Allow clipboard access in your browser and try again.</p>}
      <span role="status" className="sr-only">{copyState === "copied" ? "Matrix copied for Excel" : ""}</span>
      <div className="overflow-x-auto border pmp-table-wrap">
        <table className="w-full min-w-[32rem] border-collapse text-left text-[0.9375rem]" aria-label="Price comparison matrix">
          <thead className="bg-muted/50">
            <tr>
              {matrix.headers.map((header, index) => <th key={index} scope={showNotes && index > 0 ? "colgroup" : "col"} rowSpan={showNotes && index === 0 ? 2 : undefined} colSpan={showNotes && index > 0 ? 2 : 1} className={`border-b px-3 py-2 align-top font-medium ${index === 0 ? "min-w-48" : ""}`}>{header}</th>)}
            </tr>
            {showNotes && <tr>{matrix.headers.slice(1).flatMap((_, index) => [
              <th key={`${index}-amount`} scope="col" className="border-b px-3 py-1 text-right text-xs font-medium text-muted-foreground">Amount</th>,
              <th key={`${index}-notes`} scope="col" className="border-b px-3 py-1 text-xs font-medium text-muted-foreground">Notes</th>,
            ])}</tr>}
          </thead>
          <tbody>
            {matrix.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex >= itemCount ? "border-t bg-muted/30" : "even:bg-muted/20"}>
                <th scope="row" className={`px-3 py-2 align-top ${rowIndex >= itemCount ? "font-semibold" : "font-normal"}`}>{row.label}</th>
                {row.cells.flatMap((cell, columnIndex) => {
                  const amount = <span className="block whitespace-nowrap text-right font-medium tabular-nums">{cell.displayAmount ?? "—"}</span>;
                  const note = <span className="block text-left text-xs leading-relaxed text-muted-foreground">{cell.note}</span>;
                  return showNotes ? [
                    <td key={`${columnIndex}-amount`} className="px-3 py-2 align-top">{amount}</td>,
                    <td key={`${columnIndex}-notes`} className="min-w-40 px-3 py-2 align-top">{note}</td>,
                  ] : [<td key={columnIndex} className="min-w-32 space-y-1 px-3 py-2 align-top">{amount}{note}</td>];
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
