export type SourceType = "project_evidence" | "doctrine" | "reference" | (string & {}) | null;

export type Citation = {
  sourceId: string;
  chunkId: string;
  documentId: string;
  title: string;
  project: string;
  phase: string | null;
  sourceType: SourceType;
  pageOrSection: string | null;
  excerpt: string;
  label: string | null;
};

export type AssistantMessageMeta = {
  evidenceSufficient: boolean;
  assumptions: string[];
  workflowDeferred: boolean;
  workflowNote: string | null;
};
