import type { TenderQaItem } from "@/lib/types/tender";

import { formatTenderMoney, formatTenderStatus } from "./format";

export function cellKey(quoteId: string, cellCode: string): string {
  return `${quoteId}:${cellCode}`;
}

export function qaItemKey(item: TenderQaItem): string | null {
  const quoteId = readString(item.payload.quote_id);
  const cellCode = readString(item.payload.cell_code);
  if (!quoteId || !cellCode) return null;
  return cellKey(quoteId, cellCode);
}

export function groupQaByCell(items: TenderQaItem[]): Map<string, TenderQaItem[]> {
  const map = new Map<string, TenderQaItem[]>();
  for (const item of items) {
    const key = qaItemKey(item);
    if (!key) continue;
    const existing = map.get(key);
    if (existing) {
      existing.push(item);
    } else {
      map.set(key, [item]);
    }
  }
  return map;
}

/** Items with no cell anchor: document classifications and quote-level flags. */
export function unanchoredQaItems(items: TenderQaItem[]): TenderQaItem[] {
  return items.filter((item) => qaItemKey(item) === null);
}

export function qaQuestion(item: TenderQaItem): string {
  const payload = item.payload;
  if (item.entity_type === "cell_status") {
    const status = readString(payload.status);
    const amount = readNumber(payload.amount_cents);
    const statusLabel = status ? formatTenderStatus(status) : "this reading";
    return amount !== null
      ? `Read as ${statusLabel} at ${formatTenderMoney(amount)} — is this correctly allocated?`
      : `Read as ${statusLabel} — is this correctly allocated?`;
  }
  if (item.entity_type === "mapping") {
    const description = readString(payload.description_raw);
    return description
      ? `"${description}" was mapped to this line item — is that where it belongs?`
      : "Confirm this line item mapping.";
  }
  if (item.entity_type === "flag") {
    return readString(payload.headline) ?? "Review this flag.";
  }
  return readString(payload.filename) ?? "Review this document classification.";
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
