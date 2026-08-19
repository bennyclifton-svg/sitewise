export type PulseSignalType =
  | "drawing_revision"
  | "approval_received"
  | "invoice_review_required"
  | "potential_cost_change"
  | "document_needs_classification";

export type PulseAction =
  | "review_invoice"
  | "classify_document"
  | "view_evidence"
  | "dismiss";

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
};

export const EMPTY_PULSE_FEED: PulseFeed = {
  attention: [],
  other: [],
  attention_count: 0,
  generated_at: "1970-01-01T00:00:00Z",
};
