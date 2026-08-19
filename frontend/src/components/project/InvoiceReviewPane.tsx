import { Button } from "@/components/ui/button";
import type { InvoiceReview, InvoiceReviewFields } from "@/lib/types/project";
import { cn } from "@/lib/utils";

const REVIEW_FIELDS: { key: keyof InvoiceReviewFields; label: string }[] = [
  { key: "invoice_number", label: "Invoice number" },
  { key: "supplier_name", label: "Supplier" },
  { key: "supplier_abn", label: "ABN" },
  { key: "invoice_date", label: "Invoice date" },
  { key: "subtotal_ex_gst", label: "Subtotal ex GST" },
  { key: "gst", label: "GST" },
  { key: "total_including_gst", label: "Total incl GST" },
];

export function InvoiceReviewPane({
  review,
  onHold,
  onReject,
  onApprove,
  onReviewedChange,
}: {
  review: InvoiceReview;
  onHold?: () => void;
  onReject?: () => void;
  onApprove?: () => void;
  onReviewedChange?: (field: keyof InvoiceReviewFields, value: string) => void;
}) {
  const hasErrorIssues = review.issues.some((issue) => issue.severity === "error");

  return (
    <section className="grid gap-4" aria-label="Invoice review">
      <div className="grid gap-4 lg:grid-cols-3">
        <article className="border border-[var(--border-hair)] bg-[var(--bg-surface)] p-3">
          <h3 className="mb-2 text-sm font-medium">Original</h3>
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-[var(--text-body)]">
            {review.original_excerpt || "Source excerpt is not available for this invoice."}
          </pre>
        </article>
        <article className="border border-[var(--border-hair)] bg-[var(--bg-surface)] p-3">
          <h3 className="mb-2 text-sm font-medium">Extraction</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-[var(--text-muted)]">
                <th className="py-1 font-medium">Field</th>
                <th className="py-1 font-medium">Machine</th>
                <th className="py-1 font-medium">Secondary</th>
                <th className="py-1 font-medium">Reviewed</th>
              </tr>
            </thead>
            <tbody>
              {REVIEW_FIELDS.map(({ key, label }) => {
                const different = review.reconciliation[key] === "different";
                return (
                  <tr
                    key={key}
                    className={cn(different && "bg-[var(--warn-bg)]")}
                    data-field={key}
                    data-reconciliation={review.reconciliation[key] ?? "match"}
                  >
                    <td className="py-1 pr-2">{label}</td>
                    <td className="py-1 pr-2">{review.machine[key] ?? "—"}</td>
                    <td className="py-1 pr-2">{review.secondary[key] ?? "—"}</td>
                    <td className="py-1">
                      <input
                        className="cost-plan-field h-7 w-full px-1"
                        aria-label={`Reviewed ${label}`}
                        value={review.reviewed[key] ?? ""}
                        onChange={(event) =>
                          onReviewedChange?.(key, event.target.value)
                        }
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </article>
        <article className="border border-[var(--border-hair)] bg-[var(--bg-surface)] p-3">
          <h3 className="mb-2 text-sm font-medium">Cost allocation</h3>
          <ul className="space-y-2 text-xs">
            {review.allocations.map((allocation) => (
              <li key={`${allocation.description}-${allocation.amount_ex_gst}`}>
                <p>{allocation.description}</p>
                <p className="text-[var(--text-muted)]">
                  {allocation.cost_item_label} · {allocation.mapping_method} · $
                  {allocation.amount_ex_gst}
                </p>
              </li>
            ))}
          </ul>
        </article>
      </div>
      {review.issues.length > 0 ? (
        <ul className="text-xs" aria-label="Invoice issues">
          {review.issues.map((issue) => (
            <li key={`${issue.code}-${issue.message}`} className="text-[var(--alert-text)]">
              {issue.code}: {issue.message}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="sm" onClick={onHold}>
          Hold
        </Button>
        <Button type="button" variant="destructive" size="sm" onClick={onReject}>
          Reject
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={onApprove}
          disabled={hasErrorIssues}
        >
          Approve
        </Button>
      </div>
    </section>
  );
}
