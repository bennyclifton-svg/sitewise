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

export type ProjectSummary = {
  id: string;
  slug: string;
  title: string;
  workspace_path: string;
  phase: string;
  archetype: string | null;
  user_role: string | null;
  state: string | null;
  status: string;
  overlay_status: OverlayStatus;
  updated_at: string;
};

export type CreateProjectInput = {
  title: string;
  slug?: string;
  archetype?: string;
  user_role?: string;
  state?: string;
  phase?: string;
};

export type EvidencePreview = {
  id: string;
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
};

export type ProjectDetail = ProjectSummary & {
  metadata: Record<string, unknown> | null;
  evidence_preview: EvidencePreview | null;
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

export type PlatformKnowledgeBucket = {
  kind: string;
  document_count: number;
};

export type PlatformKnowledgeStatus = {
  available: boolean;
  buckets: PlatformKnowledgeBucket[];
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
  created_at: string;
  updated_at: string;
};

export type DraftArtifact = DraftArtifactSummary & {
  content_markdown: string;
  provenance_metadata: Record<string, unknown> | null;
};

export type ProjectCockpitBootstrap = {
  project: ProjectDetail;
  projects: ProjectSummary[];
  evidence: EvidencePreview[];
  workspace_tree: ProjectWorkspaceTree;
  platform_knowledge: PlatformKnowledgeStatus;
  latest_drafts: Record<string, DraftArtifactSummary | null>;
  timings_ms: Record<string, number>;
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

export type ProjectActivityRun = {
  run_id: string;
  source: string;
  reference_type: string | null;
  reference_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  events: ProjectActivityEvent[];
};

export type ProjectActivityResponse = {
  runs: ProjectActivityRun[];
  newest_created_at: string | null;
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
