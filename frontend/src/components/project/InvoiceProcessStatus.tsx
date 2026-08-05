import type { ProcessInvoicesResult } from "@/lib/types/project";

export function InvoiceProcessStatus({ result }: { result: ProcessInvoicesResult }) {
  return (
    <p className="rounded-md border px-3 py-2 text-sm" role="status">
      Booked {result.booked_invoice_count} invoice
      {result.booked_invoice_count === 1 ? "" : "s"} across {result.register_row_count}{" "}
      register row{result.register_row_count === 1 ? "" : "s"}.
      {result.duplicate_count
        ? ` ${result.duplicate_count} duplicate${result.duplicate_count === 1 ? "" : "s"} skipped.`
        : ""}
      {result.conflict_count
        ? ` ${result.conflict_count} conflict${result.conflict_count === 1 ? "" : "s"} ${
            result.conflict_count === 1 ? "requires" : "require"
          } review.`
        : ""}
      {result.review_count
        ? ` ${result.review_count} allocation${result.review_count === 1 ? "" : "s"} ${
            result.review_count === 1 ? "needs" : "need"
          } review.`
        : ""}
      {result.extraction_error_count
        ? ` ${result.extraction_error_count} invoice${
            result.extraction_error_count === 1 ? "" : "s"
          } could not be extracted.`
        : ""}
      {result.pending_ingest_count
        ? ` ${result.pending_ingest_count} invoice upload${
            result.pending_ingest_count === 1 ? " is" : "s are"
          } still ingesting; run Process invoices again when ready.`
        : ""}
    </p>
  );
}
