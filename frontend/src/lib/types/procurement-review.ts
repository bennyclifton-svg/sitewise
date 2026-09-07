import type { DraftArtifact } from "@/lib/types/project";

export type ProcurementReviewRun = {
  comparison_id: string;
  row_id: string;
  package_name: string;
  phase: "reading" | "preparing" | "complete" | "failed";
  activity: "queued" | "running" | "retrying" | "waiting";
  started_at: string;
  draft: DraftArtifact | null;
  error: string | null;
  can_retry: boolean;
  documents: Array<{
    id: string;
    filename: string;
    firm_name: string;
    pages: number | null;
    pages_read: number;
    complete: boolean;
    state: "queued" | "opening" | "reading" | "retrying" | "waiting" | "complete" | "failed";
  }>;
};

export type ProcurementReviewEvidence = {
  review?: { selection: { matrix: Array<{ label: string; cells: Array<{ quote_id: string; fact_ids: string[] }> }> } };
  quotes: Array<{ id: string; name: string }>;
  documents: Array<{
    id: string; quote_id: string; filename: string; path: string; page_count: number;
    facts: Array<{ page_no: number; label: string; excerpt: string; kind: string; amount_printed: string | null; tax_basis: string }>;
  }>;
};
