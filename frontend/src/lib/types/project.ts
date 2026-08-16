import type { ChatMessage, ChatThread } from "@/lib/types/chat";

export type OverlayIssue = {
  field: string;
  value: string | null;
  reason: string;
};

export type OverlayStatus = {
  ready: boolean;
  missing: OverlayIssue[];
  invalid: OverlayIssue[];
};

export type TaxonomyOption = {
  value: string;
  label: string;
};

export type ScaleField = {
  key: string;
  label: string;
  type: "text" | "number" | "integer" | "boolean" | string;
  typical?: string;
  placeholder?: string;
  min?: number;
  max?: number;
};

export type Subclass = {
  value: string;
  label: string;
  ncc_class: string | null;
  scale_fields: ScaleField[];
};

export type BuildingClass = {
  value: string;
  label: string;
  multi_subclass: boolean;
  work_types: string[];
  subclasses: Subclass[];
};

export type ComplexityDimension = {
  key: string;
  label: string;
  options: TaxonomyOption[];
};

export type RiskSeverity = "critical" | "warning" | "info" | string;

export type RiskFlagDefinition = {
  value: string;
  severity: RiskSeverity;
  title: string;
  description: string;
};

export type WorkScopeItem = {
  value: string;
  label: string;
  consultants?: string[];
  riskFlag?: string;
  complexityPoints?: number;
};

export type WorkScopeCategory = {
  value: string;
  label: string;
  items: WorkScopeItem[];
};

export type WorkScopeDefinition = {
  categories: WorkScopeCategory[];
};

export type TaxonomyCatalog = {
  work_types: TaxonomyOption[];
  building_classes: BuildingClass[];
  complexity_dimensions: Record<string, ComplexityDimension[]>;
  risk_flags: Record<string, RiskFlagDefinition>;
  work_scopes: Record<string, WorkScopeDefinition>;
  emphasis_profiles: {
    sections: string[];
    base_weights: Record<string, Record<string, number>>;
    modifiers: Array<Record<string, unknown>>;
  };
};

export type TaxonomyScalar = string | number | boolean;

export type ProjectSubclassSelection = string | {
  value: string;
  label?: string;
};

/**
 * An existing asset a refurb, remediation or services project acts on. Scale
 * fields describe the building; this describes the plant being replaced, and on
 * a services job it is the scope.
 */
export type ProjectAsset = {
  type: string;
  count?: number | null;
  location?: string | null;
  make_model?: string | null;
  capacity?: string | null;
  age_years?: number | null;
  condition?: string | null;
  action?: string | null;
  replacement_spec?: string | null;
  notes?: string | null;
};

export type ProjectTaxonomyMetadata = {
  subclasses?: ProjectSubclassSelection[];
  scale?: Record<string, TaxonomyScalar>;
  complexity?: Record<string, string>;
  work_scope?: string[];
  assets?: ProjectAsset[];
  /** The scope in the user's own words. work_scope routes doctrine; this describes. */
  scope_narrative?: string[];
  budget?: string | null;
  site_address?: string | null;
  client?: string | null;
};

export type ProjectMetadata = Record<string, unknown> & {
  taxonomy?: ProjectTaxonomyMetadata;
  identity_review?: {
    fields?: ("client" | "site_address")[];
  };
};

export type ProjectTaxonomyInput = {
  building_class?: string | null;
  work_type?: string | null;
  subclasses?: ProjectSubclassSelection[];
  scale?: Record<string, TaxonomyScalar>;
  complexity?: Record<string, string>;
  work_scope?: string[];
};

export type RiskFlag = RiskFlagDefinition;

export type ProjectSummary = {
  id: string;
  slug: string;
  title: string;
  workspace_path: string;
  phase: string;
  archetype: string | null;
  building_class: string | null;
  work_type: string | null;
  // Role is pinned server-side and no longer user-facing; kept only because the
  // read model still returns a constant value. Nothing should branch on it.
  user_role?: string | null;
  state: string | null;
  profile_revision?: number;
  decision_set_revision?: number;
  status: string;
  overlay_status: OverlayStatus;
  updated_at: string;
};

export type CreateProjectInput = {
  title: string;
  slug?: string;
  building_class?: string | null;
  work_type?: string | null;
  subclasses?: ProjectSubclassSelection[];
  scale?: Record<string, TaxonomyScalar>;
  complexity?: Record<string, string>;
  work_scope?: string[];
  state?: string;
  phase?: string;
};

export type UpdateProjectInput = ProjectTaxonomyInput & {
  expected_revision: number;
  title?: string;
  state?: string | null;
  site_address?: string | null;
  client?: string | null;
  budget?: string | null;
  scope_narrative?: string[];
  clear_incompatible?: boolean;
};

export type ProjectProfileView = {
  project_id: string;
  profile_revision: number;
  title?: string;
  building_class: string | null;
  work_type: string | null;
  subclasses: ProjectSubclassSelection[];
  scale: Record<string, TaxonomyScalar>;
  complexity: Record<string, string>;
  work_scope: string[];
  assets?: ProjectAsset[];
  scope_narrative?: string[];
  budget?: string | null;
  user_role?: string | null;
  state: string | null;
  site_address: string | null;
  client: string | null;
};

export type ProjectProfileChange = {
  profile: ProjectProfileView;
  previous_revision: number;
  new_revision: number;
  changed_fields: Array<
    | "title"
    | "building_class"
    | "work_type"
    | "subclasses"
    | "scale"
    | "complexity"
    | "work_scope"
    | "assets"
    | "scope_narrative"
    | "budget"
    | "state"
    | "site_address"
    | "client"
  >;
  cleared_fields: ProjectProfileChange["changed_fields"];
  overlay_status: OverlayStatus;
  risk_flags: RiskFlag[];
};

export type ProjectEvent = {
  id: string;
  sequence: number;
  schema_version: number;
  project_id: string;
  actor_source: string;
  resource_type: string;
  resource_id: string;
  resource_revision: number | null;
  action: string;
  payload: Record<string, unknown>;
  deduplication_key: string | null;
  created_at: string;
};

export type ProjectEventListResponse = {
  events: ProjectEvent[];
  next_after: number;
};

export type DocumentUsageMark = {
  artefact_id: string;
  workflow_type: string;
  title: string;
  version: number;
};

export type EvidencePreview = {
  id: string;
  workspace_file_id?: string | null;
  title: string;
  filename: string;
  relative_path: string;
  source_type: string | null;
  document_class: string;
  excerpt: string;
  content?: string | null;
  document_number?: string | null;
  revision?: string | null;
  category?: string | null;
  invoice_status?:
    | "reading"
    | "ready_to_process"
    | "processing"
    | "booked"
    | "needs_review"
    | "failed"
    | null;
  /** Latest drafts that were built from this document. */
  used_by?: DocumentUsageMark[];
};

export type ProjectDetail = ProjectSummary & {
  metadata: ProjectMetadata | null;
  evidence_preview: EvidencePreview | null;
  risk_flags: RiskFlag[];
  workflow_capabilities?: WorkflowCapabilityMatrix | null;
};

export type WorkflowCapability = {
  status: "supported" | "needs_input" | "unsupported";
  reasons: string[];
  required_fields: string[];
  required_confirmations?: string[];
  reference_coverage?: string[];
};

export type WorkflowCapabilityMatrix = {
  schema_version: 1;
  snapshot_schema_version: 1;
  snapshot_content_fingerprint: string;
  capabilities: Record<string, WorkflowCapability>;
};

export type ProjectNextAction = {
  code: string;
  label: string;
  reason: string;
  blocking_fact: string;
  route: string;
  tool: string;
};

export type ProjectSnapshot = {
  schema_version: 1;
  generated_at: string;
  content_fingerprint: string;
  evidence: {
    active_count: number;
    ingest_failure_count: number;
  };
  purpose_selections: { purpose: string; revision: number }[];
  latest_artefacts: {
    artefact_id: string;
    workflow_type: string;
    title: string;
    version: number;
    status: string;
    is_stale: boolean;
    stale_reason: string | null;
  }[];
  active_workflow_runs: {
    run_id: string;
    workflow_type: string;
    state: string;
    error_class: string | null;
  }[];
  failed_workflow_runs: {
    run_id: string;
    workflow_type: string;
    state: string;
    error_class: string | null;
  }[];
  tender: {
    status: "not_started" | "draft" | "qa_required" | "approved";
    report_id: string | null;
    report_version: number | null;
    open_qa_count: number;
    qs_gate_passed: boolean;
  };
  budget: {
    status: "not_available" | "proposed" | "accepted";
    version: number | null;
    total: string | null;
    gst_treatment: string | null;
  };
  next_actions: ProjectNextAction[];
  open_profile_proposals?: ProjectProfileProposal[];
  open_profile_proposals_complete?: boolean;
};

export type ProjectProfileProposal = {
  id: string;
  project_id: string;
  profile_revision: number;
  current_values: Record<string, unknown>;
  proposed_values: Record<string, unknown>;
  evidence_references: {
    source_document_id: string;
    locator: string | null;
    claim: string | null;
  }[];
  confidence: number | null;
  state: "pending" | "accepted" | "rejected";
  proposer: string;
  resolver_source: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

export type ProfileProposalResolution = {
  proposal: ProjectProfileProposal;
  profile_change: unknown | null;
};

export type WorkflowRunState =
  | "queued"
  | "running"
  | "needs_input"
  | "complete"
  | "failed"
  | "cancelled";

export type WorkflowRun = {
  id: string;
  project_id: string;
  requested_by_user_id: string;
  requested_by_thread_id: string | null;
  requested_by_turn_id: string | null;
  workflow_type: string;
  idempotency_key: string;
  schema_version: number;
  frozen_project_context_version: number;
  frozen_profile_revision: number;
  frozen_snapshot_fingerprint: string;
  frozen_evidence_fingerprint: string;
  frozen_decision_set_revision: number;
  frozen_selection_revision: number | null;
  frozen_artefact_version: number | null;
  state: WorkflowRunState;
  attempt: number;
  max_attempts: number;
  cancel_requested: boolean;
  progress: Record<string, unknown>;
  stage_durations_ms: Record<string, number>;
  result_artefact_id: string | null;
  result_reference: Record<string, unknown> | null;
  error_class: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type WorkflowRunStartInput = {
  idempotency_key: string;
  expected_snapshot_fingerprint: string;
  expected_profile_revision: number;
  expected_decision_set_revision: number;
  expected_artefact_version?: number;
  thread_id?: string;
  chat_model?: string;
  parameters?: Record<string, unknown>;
};

export type WorkflowRunResult = {
  run: WorkflowRun;
  result: Record<string, unknown> | null;
};

export type ProcessInvoicesResult = {
  candidate_count: number;
  pending_ingest_count: number;
  booked_invoice_count: number;
  register_row_count: number;
  duplicate_count: number;
  conflict_count: number;
  review_count: number;
  extraction_error_count: number;
  conflicts: string[];
  review_items: string[];
  extraction_errors: string[];
  cost_plan_version: number;
  workbook_path: string | null;
  draft_id: string | null;
  draft?: DraftArtifact;
};

export type WorkspaceTreeNode = {
  name: string;
  path: string;
  kind: "directory" | string;
  description: string;
  document_count: number;
  related_workflows: string[];
  children: WorkspaceTreeNode[];
};

export type ProjectWorkspaceTree = {
  project_id: string;
  root_path: string;
  tree: WorkspaceTreeNode[];
};

export type WorkbookCellStyle = {
  fill_color: string | null;
  bold: boolean;
};

export type WorkbookSheetPreview = {
  name: string;
  column_count: number;
  rows: string[][];
  styles: WorkbookCellStyle[][];
};

export type WorkbookPreview = {
  filename: string;
  workspace_path: string;
  sheets: WorkbookSheetPreview[];
  warnings: string[];
};

export type InvoiceCostItemOption = {
  item_key: string;
  cost_code: string;
  category: string;
  item: string;
  budget: string | null;
};

export type InvoiceLedgerRow = {
  allocation_id: string;
  invoice_id: string;
  invoice_revision: number;
  invoice_date: string;
  company: string;
  po_number: string | null;
  invoice_number: string;
  description: string;
  cost_item_key: string | null;
  cost_item_label: string;
  amount_ex_gst: string;
  billing_month: string;
  paid: boolean;
  review_status: "mapped" | "needs_review";
  mapping_method:
    | "exact"
    | "related_reference"
    | "keyword"
    | "model"
    | "manual"
    | "remembered"
    | "unidentified";
};

export type InvoiceLedger = {
  cost_plan_version: number;
  workbook_path: string;
  rows: InvoiceLedgerRow[];
  cost_items: InvoiceCostItemOption[];
};

export type PlatformKnowledgeDocument = {
  filename: string;
  relative_path: string;
};

export type PlatformKnowledgeBucket = {
  kind: string;
  document_count: number;
  documents?: PlatformKnowledgeDocument[];
};

export type PlatformKnowledgeStatus = {
  available: boolean;
  buckets: PlatformKnowledgeBucket[];
};

export type PlatformKnowledgeContent = {
  filename: string;
  relative_path: string;
  kind?: string | null;
  content: string;
};

export type ProjectDecisionOption = {
  value: string;
  label: string;
};

export type ProjectDecision = {
  id: string;
  project_id: string;
  decision_id: string;
  section: string;
  label: string;
  options: ProjectDecisionOption[];
  selected: string;
  source: string;
  workflow_type: string;
  revision: number;
  set_revision: number;
  locked: boolean;
  evidence_conflict: boolean;
  agent_suggestion: string | null;
  provenance: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProjectDecisionListResponse = {
  decisions: ProjectDecision[];
  set_revision: number;
};

export type UpdateProjectDecisionResponse = {
  decision: ProjectDecision;
  draft: DraftArtifact;
};

export type DraftArtifactSummary = {
  id: string;
  project_id: string;
  workflow_type: string;
  version: number;
  status: string;
  title: string;
  workspace_path: string;
  author_user_id: string;
  model: string | null;
  runtime: string;
  is_stale?: boolean;
  stale_reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type DraftArtifact = DraftArtifactSummary & {
  content_markdown: string;
  provenance_metadata: Record<string, unknown> | null;
};

export type DraftInstructionInput = {
  anchor_start: number;
  anchor_end: number;
  quoted_text: string;
  instruction: string;
};

export type FailedInstruction = {
  index: number;
  reason: string;
};

export type ApplyDraftInstructionsResponse = {
  draft: DraftArtifact;
  applied_count: number;
  failed: FailedInstruction[];
};

export type ProcurementRequestKind =
  | "consultant_rfp"
  | "contractor_eoi"
  | "trade_rft"
  | "trade_rfq";

export type ProcurementRequestStatus =
  | "draft"
  | "issued"
  | "closed"
  | "cancelled";

export type ProcurementRequest = {
  id: string;
  project_id: string;
  created_by_user_id: string;
  kind: ProcurementRequestKind;
  target_name: string;
  target_slug: string;
  status: ProcurementRequestStatus;
  current_draft_artifact_id: string | null;
  current_draft: DraftArtifactSummary | null;
  issued_at: string | null;
  closed_at: string | null;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type ProcurementRequestListResponse = {
  requests: ProcurementRequest[];
};

export type ProjectCockpitBootstrap = {
  project: ProjectDetail;
  projects: ProjectSummary[];
  evidence: EvidencePreview[];
  workspace_tree: ProjectWorkspaceTree;
  platform_knowledge: PlatformKnowledgeStatus;
  latest_drafts: Record<string, DraftArtifactSummary | null>;
  snapshot: ProjectSnapshot;
  timings_ms: Record<string, number>;
};

export type ProjectChatBootstrap = {
  thread: ChatThread | null;
  messages: ChatMessage[];
};

export type BatchDeleteEvidenceResponse = {
  deleted: string[];
  failed: { evidence_id: string; detail: string }[];
};

export type DeleteDraftResponse = {
  deleted_id: string;
  workflow_type: string;
  latest_draft: DraftArtifactSummary | null;
};

export type WorkflowTraceEvent = {
  step: string;
  status: string;
  message: string;
  metadata: Record<string, unknown>;
};

export type ProjectActivityEvent = WorkflowTraceEvent & {
  id: string;
  created_at: string;
};

export type ProjectActivityReferences = {
  seed_consulted: string[];
  evidence_refs: string[];
  context_refs: string[];
};

export type ProjectActivityRun = {
  run_id: string;
  source: string;
  reference_type: string | null;
  reference_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  references?: ProjectActivityReferences | null;
  events: ProjectActivityEvent[];
};

export type ProjectActivityResponse = {
  runs: ProjectActivityRun[];
  newest_created_at: string | null;
};

export type DeleteProjectActivityResponse = {
  deleted: number;
};

export type CreatePmpResponse = {
  status: "blocked" | "failed" | "complete" | string;
  gate: OverlayStatus;
  trace: WorkflowTraceEvent[];
  draft: DraftArtifact | null;
  message: string | null;
};

export type CreateCostPlanResponse = CreatePmpResponse;

export type SortFilesSummary = {
  inspected: number;
  moved: number;
  already_filed: number;
  unresolved: number;
  skipped: number;
  refused: number;
};

export type SortFileRow = {
  source_path: string;
  filename: string;
  outcome: string;
  destination_path: string | null;
  destination_filename: string | null;
  reason: string | null;
  document_number: string | null;
  title: string | null;
  revision: string | null;
  category: string | null;
};

export type SortFilesResponse = {
  status: "blocked" | "failed" | "complete" | string;
  gate: OverlayStatus;
  trace: WorkflowTraceEvent[];
  summary: SortFilesSummary | null;
  rows: SortFileRow[];
  warnings: string[];
  draft: DraftArtifact | null;
  message: string | null;
};

export type InboxUploadResult = {
  id: string;
  filename: string;
  workspace_path: string;
  content_hash: string;
  size_bytes: number;
  ingest_status: string;
  message: string | null;
  workflow_run_id?: string | null;
};

export type DocumentRepairPreviewRow = {
  status: "change" | "unchanged" | "needs_review" | "conflict";
  current_path: string;
  current_filename: string;
  proposed_path: string;
  proposed_filename: string;
  document_number: string | null;
  title: string | null;
  revision: string | null;
  category: string | null;
  confidence: string;
  changes: string[];
  reason: string | null;
};

export type DocumentRepairPreview = {
  inspected: number;
  changes: number;
  needs_review: number;
  conflicts: number;
  unchanged: number;
  rows: DocumentRepairPreviewRow[];
};

export type DocumentRepairApplyResult = {
  applied: number;
  failed: number;
  skipped: number;
  rows: {
    current_path: string;
    proposed_path: string;
    status: "applied" | "failed" | "skipped";
    reason: string | null;
  }[];
};

export type PdfSheetProposal = {
  index: number;
  proposed_title: string;
  filename: string;
  has_text: boolean;
};

export type PdfAnalyzeResult = {
  staging_id: string;
  is_drawing_set: boolean;
  confidence: number;
  page_count: number;
  scores: Record<string, unknown>;
  pages: PdfSheetProposal[];
};
