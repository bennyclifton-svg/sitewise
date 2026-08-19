export type PulseSignalType =
  | "drawing_revision"
  | "approval_received"
  | "invoice_review_required"
  | "potential_cost_change"
  | "document_needs_classification"
  | "tender_received"
  | "unanswered_correspondence";

export type PulseAction =
  | "review_invoice"
  | "classify_document"
  | "view_evidence"
  | "dismiss"
  | "draft_reply"
  | "view_thread";

export type PulseSincePreset = "yesterday" | "7d" | "30d";

export type PulseEvidenceRef = {
  reference_type: string;
  reference_id: string;
  label: string;
};

export type PulseItem = {
  id: string;
  kind: "attention" | "other";
  signal_type: PulseSignalType | null;
  title: string;
  body: string;
  domain: string;
  evidence: PulseEvidenceRef[];
  actions: string[];
  confidence?: number | null;
  created_at: string;
};

export type PulseFeed = {
  attention: PulseItem[];
  other: PulseItem[];
  attention_count: number;
  generated_at: string;
  since: string;
};

export const EMPTY_PULSE_FEED: PulseFeed = {
  attention: [],
  other: [],
  attention_count: 0,
  generated_at: "1970-01-01T00:00:00Z",
  since: "1970-01-01T00:00:00Z",
};

const DAY_MS = 24 * 60 * 60 * 1000;

export function pulseSinceIso(
  preset: PulseSincePreset,
  now = new Date(),
): string {
  const days = preset === "yesterday" ? 1 : preset === "30d" ? 30 : 7;
  return new Date(now.getTime() - days * DAY_MS).toISOString();
}
