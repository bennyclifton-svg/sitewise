export type TenderProjectContext = {
  context_version: number;
  context_source: "manual" | "repository_selection";
  state: "NSW" | "VIC" | "QLD" | null;
  region: "metro" | "regional" | null;
  build_type: "new_build" | "renovation" | "addition" | null;
  dwelling_class: "class_1a";
  storeys: number | null;
  floor_area_m2: number | null;
  site_area_m2: number | null;
  soil_class: "A" | "S" | "M" | "H1" | "H2" | "E" | "P" | "unknown";
  slope_class: "flat" | "moderate" | "steep" | "unknown";
  bal_rating: "none" | "12.5" | "19" | "29" | "40" | "FZ" | "unknown";
  wind_rating: string | null;
  flood_overlay: boolean | null;
  heritage_overlay: boolean | null;
  existing_dwelling_era: string | null;
  demolition_required: boolean | null;
  spec_level: "builder_base" | "mid" | "high" | "architectural" | null;
  target_budget_cents: number | null;
  notes: string | null;
};

export type TenderDocument = {
  id: string;
  quote_id: string;
  storage_path: string;
  original_filename: string;
  mime_type: string;
  doc_type: string | null;
  ocr_applied: boolean;
  page_count: number | null;
  ingest_status: string;
  created_at: string;
};

export type TenderQuote = {
  id: string;
  comparison_id: string;
  builder_name: string;
  builder_abn: string | null;
  quote_ref: string | null;
  quote_date: string | null;
  stated_total_cents: number | null;
  gst_treatment: string;
  contract_type: string;
  validity_days: number | null;
  stage: string;
  created_at: string;
  documents?: TenderDocument[];
};

export type TenderComparison = {
  id: string;
  project_id: string;
  status: string;
  context: TenderProjectContext;
  created_by: string;
  created_at: string;
  updated_at: string;
  quotes: TenderQuote[];
};

export type TenderComparisonCreate = {
  project_id: string;
  context: TenderProjectContext;
};

export type TenderComparisonFromProjectFilesCreate = {
  project_id: string;
  workspace_paths: string[];
};

export type TenderComparisonListResponse = {
  comparisons: TenderComparison[];
  next_cursor?: string | null;
};

export type TenderQuoteCreate = {
  builder_name: string;
  builder_abn?: string | null;
  quote_ref?: string | null;
  quote_date?: string | null;
  stated_total_cents?: number | null;
  gst_treatment?: "inclusive" | "exclusive" | "unclear";
  contract_type?: "hia" | "mba" | "custom" | "cost_plus" | "unknown";
  validity_days?: number | null;
};

export type TenderJob = {
  id: string;
  kind: string;
  comparison_id: string | null;
  quote_id: string | null;
  status: string;
  attempts: number;
  last_error: string | null;
  run_after: string;
  created_at: string;
};

export type TenderDocumentUploadResponse = {
  document: TenderDocument;
  job: TenderJob;
};

export type TenderMilestoneKey =
  | "ingest"
  | "extract"
  | "map"
  | "analyse"
  | "review"
  | "report";

export type TenderMilestoneState =
  | "pending"
  | "running"
  | "done"
  | "failed"
  | "attention";

export type TenderProgressMilestone = {
  key: TenderMilestoneKey;
  label: string;
  state: TenderMilestoneState;
  detail: string | null;
};

export type TenderProgressDocument = {
  filename: string;
  ingest_status: string;
};

export type TenderProgressQuote = {
  quote_id: string;
  builder_name: string;
  stage: string;
  stated_total_cents: number | null;
  documents: TenderProgressDocument[];
};

export type TenderStageTiming = {
  stage: string;
  duration_ms: number;
  status: string;
  llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_hits: number;
  metadata: Record<string, unknown>;
};

export type TenderComparisonProgress = {
  comparison_id: string;
  status: string;
  percent: number;
  is_processing: boolean;
  qa_pending: number;
  milestones: TenderProgressMilestone[];
  quotes: TenderProgressQuote[];
  stage_timings?: TenderStageTiming[];
};

export type TenderProcessComparisonResponse = {
  queued: TenderJob[];
  notes: string[];
};

export type TenderQaEntityType =
  | "cell_status"
  | "mapping"
  | "flag"
  | "document_classification";

export type TenderQaItem = {
  id: string;
  entity_type: TenderQaEntityType;
  report_impact_cents: number;
  confidence: number | null;
  payload: Record<string, unknown>;
};

export type TenderQaQueueResponse = {
  items: TenderQaItem[];
};

export type TenderQaResolveAction = "accept" | "correct" | "suppress";

export type TenderQaResolveRequest = {
  action: TenderQaResolveAction;
  corrected_value: Record<string, unknown> | null;
  reason: string | null;
};

export type TenderQaResolveResponse = {
  id: string;
  entity_type: string;
  action: string;
  qa_state: string | null;
};

export type TenderQaAcceptAllResponse = {
  accepted: number;
  skipped_documents: number;
};

export type TenderTaxonomyCell = {
  code: string;
  name: string;
  group: string;
  stage: string;
  description: string | null;
};

export type TenderTaxonomySearchResult = TenderTaxonomyCell & {
  similarity: number;
  via: string;
};

export type TenderMatrixQuoteCell = {
  status: string;
  amount_cents: number | null;
  flags: string[];
  mapping_choices: TenderMatrixMappingChoice[];
};

export type TenderMatrixMappingCandidate = {
  cell_code: string;
  name: string | null;
  similarity: number | null;
  via: string | null;
};

export type TenderMatrixMappingChoice = {
  mapping_id: string;
  selected_cell_code: string;
  candidates: TenderMatrixMappingCandidate[];
  locked: boolean;
};

export type TenderMatrixCell = {
  code: string;
  name: string;
  quotes: Record<string, TenderMatrixQuoteCell>;
};

export type TenderMatrixGroup = {
  name: string;
  cells: TenderMatrixCell[];
};

export type TenderMatrixQuoteTotal = {
  quote_id: string;
  computed_total_cents: number;
  basis?: "ex";
  residual_cents?: number;
  unallocated_cents?: number;
  not_itemised_cents?: number;
  stated_native_cents?: number | null;
  stated_total_cents: number | null;
  stated_total_source: "manual" | "extracted" | null;
  non_comparable?: boolean;
  delta_cents: number | null;
  delta_ratio: number | null;
  reconciliation: "match" | "mismatch" | "not_stated";
};

export type TenderMatrixResponse = {
  comparison_id: string;
  groups: TenderMatrixGroup[];
  totals: TenderMatrixQuoteTotal[];
};

export type TenderReportLifecycle = {
  report_id: string;
  comparison_id: string;
  draft_id: string;
  version: number;
  html_path: string | null;
  pdf_path: string | null;
  status: string;
  approved_at: string | null;
  delivered_at: string | null;
};
export type TenderSelectedWorkspaceFile = {
  workspace_file_id: string;
  workspace_path: string;
  filename: string;
  content_hash: string;
  storage_bucket: string;
  storage_key: string;
  position: number;
};

export type TenderReportState = {
  comparison_id: string;
  report: TenderReportLifecycle | null;
  draft: import("./project").DraftArtifact | null;
};

export type TenderQuoteSelectionGroup = {
  group_id: string;
  builder_name: string;
  position: number;
  files: TenderSelectedWorkspaceFile[];
};

export type TenderQuoteSelection = {
  selection_id: string | null;
  selection_revision_id: string | null;
  project_id: string;
  purpose: "tender_comparison";
  revision: number;
  selected_by: string | null;
  created_at: string | null;
  quote_groups: TenderQuoteSelectionGroup[];
};

export type ReplaceTenderQuoteSelection = {
  expected_revision: number;
  quote_candidates: Array<{
    builder_name: string;
    ordered_workspace_file_ids: string[];
  }>;
};

export type TenderPreparationInput = {
  project_id: string;
  expected_profile_revision: number;
  expected_selection_revision: number;
  context_overrides: Partial<TenderProjectContext>;
};

export type TenderPreparation = {
  supported: boolean;
  ready: boolean;
  context: TenderProjectContext | null;
  missing_fields: string[];
  unsupported_reasons: string[];
  provenance: Record<string, unknown>;
};

export type TenderIntakeInput = TenderPreparationInput & { turn_id: string };
export type TenderIntakeResponse = {
  comparison: TenderComparison;
  idempotent_replay: boolean;
};

export type QuoteLedgerItem = {
  id: string | null;
  figure_key: string;
  page_no: number | null;
  description_raw: string;
  printed_text: string | null;
  amount_cents: number | null;
  amount_ex_gst_cents: number | null;
  gst_basis: string | null;
  role: string | null;
  is_rollup: boolean;
  counted_in_total: boolean;
  duplicate_of_id: string | null;
  parent_id: string | null;
  children: QuoteLedgerItem[];
};

export type QuoteLedgerResponse = {
  quote_id: string;
  builder_name: string;
  stated_total_cents: number | null;
  stated_basis: string | null;
  status: string;
  residual_cents: number;
  computed_ex_gst_cents: number | null;
  uncaptured: Array<Record<string, unknown>>;
  items: QuoteLedgerItem[];
};

export type TenderCellLineItem = {
  line_item_id: string;
  description_raw: string;
  page_no: number | null;
  role: string | null;
  allocation_fraction: number;
  amount_cents: number | null;
  amount_ex_gst_cents: number | null;
  mapping_tier: string;
  qa_state: string;
};

export type TenderCellItemsResponse = {
  cell_code: string;
  name: string;
  quote_id: string;
  items: TenderCellLineItem[];
  sum_ex_gst_cents: number;
};
