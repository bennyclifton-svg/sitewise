const moneyFormatter = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "AUD",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
});

export const TENDER_QUOTE_STAGES = [
  "ingest_document",
  "classify_document",
  "extract_line_items",
  "embed_items",
  "map_items",
] as const;

export const TENDER_COMPARISON_STAGES = [
  "run_expectations",
  "run_analysis",
  "generate_flags",
] as const;

/** Mirrors `report.labels.cost_plus_non_comparable` in data/tender/report_language.yaml. */
export const COST_PLUS_NON_COMPARABLE_LABEL =
  "Cost-plus — excludes builder's margin; not directly comparable";

export function formatTenderMoney(cents: number | null | undefined): string {
  if (typeof cents !== "number") return "Not stated";
  return moneyFormatter.format(cents / 100);
}

/** Native stated-total GST gloss for reconciliation strips / headers. */
export function formatStatedGstBasis(
  gstTreatment: string | null | undefined,
): string {
  if (gstTreatment === "exclusive") return "ex GST";
  if (gstTreatment === "inclusive") return "inc GST";
  return "inc GST";
}

export function formatTenderDate(value: string | null | undefined): string {
  if (!value) return "No date";
  return dateFormatter.format(new Date(value));
}

export function formatTenderStage(value: string | null | undefined): string {
  if (!value) return "Not stated";
  return value
    .split("_")
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatTenderStatus(value: string): string {
  if (value === "pc" || value === "pc_allowance") return "PC allowance";
  if (value === "ps" || value === "ps_allowance") return "PS allowance";
  if (value === "excluded_explicit" || value === "excluded") return "Excluded";
  if (value === "silent_ambiguous") return "Not itemised";
  if (value === "contract_component") return "Included";
  if (value === "mixed") return "Mixed";
  return formatTenderStage(value);
}

export function formatTenderPercent(value: number | null | undefined): string {
  if (typeof value !== "number") return "Unknown";
  return `${Math.round(value * 100)}%`;
}

export function tenderStatusGlyph(status: string): string {
  if (status === "included") return "\u2713";
  if (status === "pc" || status === "ps") return "\u25C7";
  if (status === "excluded_explicit") return "\u2715";
  if (status === "not_required") return "\u2013";
  if (status === "mixed") return "\u25D1";
  return "\u25CB";
}

export function tenderStatusTone(status: string): string {
  if (status === "included") return "text-[var(--ok-text)] bg-[var(--ok-bg)]";
  if (status === "pc" || status === "ps") return "text-[var(--warn-text)] bg-[var(--warn-bg)]";
  if (status === "excluded_explicit") return "text-[var(--alert-text)] bg-[var(--alert-bg)]";
  if (status === "not_required") return "text-muted-foreground bg-muted";
  return "text-[var(--info-text)] bg-[var(--info-bg)]";
}

/** Background tint applied to the whole matrix cell so status reads at a glance. */
export function tenderStatusCellTint(status: string): string {
  if (status === "included") return "bg-[var(--ok-bg)]";
  if (status === "pc" || status === "ps") return "bg-[var(--warn-bg)]";
  if (status === "excluded_explicit") return "bg-[var(--alert-bg)]";
  if (status === "not_required") return "bg-muted/50";
  if (status === "mixed") return "bg-[var(--warn-bg)]";
  return "bg-[var(--info-bg)]";
}

export function tenderStatusTextTone(status: string): string {
  if (status === "included") return "text-[var(--ok-text)]";
  if (status === "pc" || status === "ps") return "text-[var(--warn-text)]";
  if (status === "excluded_explicit") return "text-[var(--alert-text)]";
  if (status === "not_required") return "text-muted-foreground";
  return "text-[var(--info-text)]";
}
