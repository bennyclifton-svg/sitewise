import { getAccessToken } from "@/lib/auth";
import type { AgentModelsResponse } from "@/lib/agent-model";
import { workflowChatModelPayload, type ChatModelsResponse } from "@/lib/chat-model";
import { env } from "@/lib/env";
import { ApiError, httpRequest } from "@/lib/http";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type {
  BillingPlansResponse,
  BillingStatus,
} from "@/lib/types/billing";
import type {
  TenderComparison,
  TenderComparisonCreate,
  TenderComparisonListResponse,
  TenderDocumentUploadResponse,
  TenderJob,
  TenderMatrixResponse,
  TenderQaQueueResponse,
  TenderQaResolveRequest,
  TenderQaResolveResponse,
  TenderQuote,
  TenderQuoteCreate,
  TenderReportLifecycle,
  TenderTaxonomyCell,
  TenderTaxonomySearchResult,
} from "@/lib/types/tender";
import type {
  CreateCostPlanResponse,
  CreatePmpResponse,
  DeleteProjectActivityResponse,
  SortFilesResponse,
  CreateProjectInput,
  DraftArtifact,
  EvidencePreview,
  InboxUploadResult,
  PdfAnalyzeResult,
  PlatformKnowledgeStatus,
  ProjectActivityResponse,
  ProjectCockpitBootstrap,
  ProjectDetail,
  ProjectSummary,
  TaxonomyCatalog,
  UpdateProjectInput,
  UpdateProjectDecisionResponse,
  ProjectWorkspaceTree,
  WorkbookPreview,
} from "@/lib/types/project";

const WORKFLOW_TIMEOUT_MS = 600_000;

type JsonBody = Record<string, unknown> | unknown[] | null;

type ApiRequestOptions = {
  method?: string;
  body?: JsonBody;
  timeoutMs?: number;
  auth?: boolean;
};

async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { method = "GET", body, timeoutMs, auth = true } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = await getAccessToken();
    if (!token) {
      throw new ApiError("Not signed in.", { kind: "http", status: 401 });
    }
    headers.Authorization = `Bearer ${token}`;
  }

  const base = env.apiBaseUrl.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}`;

  return httpRequest<T>(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    timeoutMs,
  });
}

async function apiBlobRequest(path: string, timeoutMs = 30_000): Promise<Blob> {
  const token = await getAccessToken();
  if (!token) {
    throw new ApiError("Not signed in.", { kind: "http", status: 401 });
  }

  const base = env.apiBaseUrl.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      let detail = `Request failed with status ${response.status}`;
      try {
        const body = JSON.parse(text) as unknown;
        if (
          typeof body === "object" &&
          body !== null &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
        ) {
          detail = (body as { detail: string }).detail;
        }
      } catch {
        if (text) detail = text;
      }
      throw new ApiError(detail, { kind: "http", status: response.status });
    }

    return await response.blob();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out.", { kind: "timeout", cause: error });
    }
    throw new ApiError("Could not download the file.", {
      kind: "network",
      cause: error,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function apiFormRequest<T>(
  path: string,
  formData: FormData,
  timeoutMs = WORKFLOW_TIMEOUT_MS,
): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new ApiError("Not signed in.", { kind: "http", status: 401 });
  }

  const base = env.apiBaseUrl.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return httpRequest<T>(`${base}${normalizedPath}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: formData,
    timeoutMs,
  });
}

export const api = {
  get: <T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...options, method: "GET" }),

  post: <T>(
    path: string,
    body?: JsonBody,
    options?: Omit<ApiRequestOptions, "method">,
  ) => apiRequest<T>(path, { ...options, method: "POST", body }),

  put: <T>(
    path: string,
    body?: JsonBody,
    options?: Omit<ApiRequestOptions, "method">,
  ) => apiRequest<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(
    path: string,
    body?: JsonBody,
    options?: Omit<ApiRequestOptions, "method">,
  ) => apiRequest<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...options, method: "DELETE" }),

  listThreads: async (): Promise<ChatThread[]> => {
    const response = await api.get<{ threads: ChatThread[] }>("/chat/threads");
    return response.threads;
  },

  createThread: async (title?: string, projectId?: string): Promise<ChatThread> =>
    api.post<ChatThread>(
      "/chat/threads",
      {
        ...(title ? { title } : {}),
        ...(projectId ? { projectId } : {}),
      },
    ),

  getThread: async (threadId: string): Promise<ChatThread> =>
    api.get<ChatThread>(`/chat/threads/${threadId}`),

  updateThreadTitle: async (threadId: string, title: string): Promise<ChatThread> =>
    api.patch<ChatThread>(`/chat/threads/${threadId}`, { title }),

  deleteThread: async (threadId: string): Promise<void> => {
    await api.delete<void>(`/chat/threads/${threadId}`);
  },

  cancelAgentTurn: async (threadId: string): Promise<boolean> => {
    const response = await api.post<{ cancelled: boolean }>(
      `/chat/agent/${threadId}/cancel`,
      {},
    );
    return response.cancelled;
  },

  getThreadMessages: async (threadId: string): Promise<ChatMessage[]> => {
    const response = await api.get<{ messages: ChatMessage[] }>(
      `/chat/threads/${threadId}/messages`,
    );
    return response.messages;
  },

  listProjects: async (): Promise<ProjectSummary[]> => {
    const response = await api.get<{ projects: ProjectSummary[] }>("/projects");
    return response.projects;
  },

  createProject: async (input: CreateProjectInput): Promise<ProjectDetail> =>
    api.post<ProjectDetail>("/projects", input),

  updateProject: async (
    projectId: string,
    input: UpdateProjectInput,
  ): Promise<ProjectDetail> =>
    api.patch<ProjectDetail>(`/projects/${projectId}`, input),

  getProject: async (projectId: string): Promise<ProjectDetail> =>
    api.get<ProjectDetail>(`/projects/${projectId}`),

  getTaxonomy: async (): Promise<TaxonomyCatalog> =>
    api.get<TaxonomyCatalog>("/projects/taxonomy"),

  listTenderComparisons: async (projectId: string): Promise<TenderComparison[]> => {
    const response = await api.get<TenderComparisonListResponse>(
      `/api/tender/comparisons?project_id=${encodeURIComponent(projectId)}`,
    );
    return response.comparisons;
  },

  getTenderComparison: async (comparisonId: string): Promise<TenderComparison> =>
    api.get<TenderComparison>(`/api/tender/comparisons/${comparisonId}`),

  createTenderComparison: async (
    input: TenderComparisonCreate,
  ): Promise<TenderComparison> =>
    api.post<TenderComparison>("/api/tender/comparisons", input),

  createTenderQuote: async (
    comparisonId: string,
    input: TenderQuoteCreate,
  ): Promise<TenderQuote> =>
    api.post<TenderQuote>(`/api/tender/comparisons/${comparisonId}/quotes`, input),

  attachTenderProjectDocument: async (
    quoteId: string,
    workspacePath: string,
  ): Promise<TenderDocumentUploadResponse> =>
    api.post<TenderDocumentUploadResponse>(
      `/api/tender/quotes/${quoteId}/documents/from-project-file`,
      { workspace_path: workspacePath },
    ),

  uploadTenderQuoteDocument: async (
    quoteId: string,
    file: File,
  ): Promise<TenderDocumentUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFormRequest<TenderDocumentUploadResponse>(
      `/api/tender/quotes/${quoteId}/documents`,
      formData,
    );
  },

  retryTenderQuoteStage: async (
    quoteId: string,
    stage: string,
  ): Promise<TenderJob> =>
    api.post<TenderJob>(
      `/api/tender/quotes/${quoteId}/retry/${encodeURIComponent(stage)}`,
    ),

  retryTenderComparisonStage: async (
    comparisonId: string,
    stage: string,
  ): Promise<TenderJob> =>
    api.post<TenderJob>(
      `/api/tender/comparisons/${comparisonId}/retry/${encodeURIComponent(stage)}`,
    ),

  getTenderQaQueue: async (
    comparisonId: string,
  ): Promise<TenderQaQueueResponse> =>
    api.get<TenderQaQueueResponse>(
      `/api/tender/comparisons/${comparisonId}/qa/queue`,
    ),

  resolveTenderQaItem: async (
    itemId: string,
    body: TenderQaResolveRequest,
  ): Promise<TenderQaResolveResponse> =>
    api.post<TenderQaResolveResponse>(`/api/tender/qa/items/${itemId}/resolve`, body),

  getTenderTaxonomy: async (): Promise<TenderTaxonomyCell[]> => {
    const response = await api.get<{ cells: TenderTaxonomyCell[] }>(
      "/api/tender/taxonomy",
    );
    return response.cells;
  },

  searchTenderTaxonomy: async (
    query: string,
  ): Promise<TenderTaxonomySearchResult[]> => {
    const response = await api.get<{ results: TenderTaxonomySearchResult[] }>(
      `/api/tender/taxonomy/search?q=${encodeURIComponent(query)}`,
    );
    return response.results;
  },

  getTenderMatrix: async (comparisonId: string): Promise<TenderMatrixResponse> =>
    api.get<TenderMatrixResponse>(`/api/tender/comparisons/${comparisonId}/matrix`),

  buildTenderReport: async (
    comparisonId: string,
  ): Promise<TenderReportLifecycle> =>
    api.post<TenderReportLifecycle>(
      `/api/tender/comparisons/${comparisonId}/report/build`,
    ),

  approveTenderReport: async (
    comparisonId: string,
  ): Promise<TenderReportLifecycle> =>
    api.post<TenderReportLifecycle>(
      `/api/tender/comparisons/${comparisonId}/report/approve`,
    ),

  getProjectDraft: async (
    projectId: string,
    draftId: string,
  ): Promise<DraftArtifact> =>
    api.get<DraftArtifact>(`/projects/${projectId}/drafts/${draftId}`),

  getProjectCockpitBootstrap: async (
    projectId: string,
  ): Promise<ProjectCockpitBootstrap> =>
    api.get<ProjectCockpitBootstrap>(`/projects/${projectId}/cockpit-bootstrap`),

  getProjectWorkspaceTree: async (
    projectId: string,
  ): Promise<ProjectWorkspaceTree> =>
    api.get<ProjectWorkspaceTree>(`/projects/${projectId}/workspace-tree`),

  getProjectActivity: async (
    projectId: string,
    since?: string,
  ): Promise<ProjectActivityResponse> =>
    api.get<ProjectActivityResponse>(
      `/projects/${projectId}/activity${since ? `?since=${encodeURIComponent(since)}` : ""}`,
    ),

  deleteProjectActivityRuns: async (
    projectId: string,
    runIds: string[],
  ): Promise<number> => {
    const response = await apiRequest<DeleteProjectActivityResponse>(
      `/projects/${projectId}/activity`,
      {
        method: "DELETE",
        body: { run_ids: runIds },
      },
    );
    return response.deleted;
  },

  getWorkbookPreview: async (
    projectId: string,
    workspacePath: string,
  ): Promise<WorkbookPreview> =>
    api.get<WorkbookPreview>(
      `/projects/${projectId}/workspace-files/preview?path=${encodeURIComponent(
        workspacePath,
      )}`,
    ),

  downloadWorkspaceFile: async (
    projectId: string,
    workspacePath: string,
  ): Promise<Blob> =>
    apiBlobRequest(
      `/projects/${projectId}/workspace-files/download?path=${encodeURIComponent(
        workspacePath,
      )}`,
    ),

  getProjectEvidence: async (projectId: string): Promise<EvidencePreview[]> => {
    const response = await api.get<{ evidence: EvidencePreview[] }>(
      `/projects/${projectId}/evidence`,
    );
    return response.evidence;
  },

  getProjectEvidenceDocument: async (
    projectId: string,
    evidenceId: string,
  ): Promise<EvidencePreview> =>
    api.get<EvidencePreview>(`/projects/${projectId}/evidence/${evidenceId}`),

  deleteProjectEvidence: async (
    projectId: string,
    evidenceId: string,
  ): Promise<void> => {
    await api.delete<void>(`/projects/${projectId}/evidence/${evidenceId}`);
  },

  analyzePdf: async (
    projectId: string,
    file: File,
  ): Promise<PdfAnalyzeResult> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFormRequest<PdfAnalyzeResult>(
      `/projects/${projectId}/inbox/analyze`,
      formData,
    );
  },

  splitStagedPdf: async (
    projectId: string,
    stagingId: string,
    sourceFilename: string,
  ): Promise<InboxUploadResult[]> => {
    const response = await api.post<{ files: InboxUploadResult[] }>(
      `/projects/${projectId}/inbox/${stagingId}/split`,
      { source_filename: sourceFilename },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    );
    return response.files;
  },

  commitStagedPdf: async (
    projectId: string,
    stagingId: string,
    sourceFilename: string,
  ): Promise<InboxUploadResult[]> => {
    const response = await api.post<{ files: InboxUploadResult[] }>(
      `/projects/${projectId}/inbox/${stagingId}/commit`,
      { source_filename: sourceFilename },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    );
    return response.files;
  },

  createProjectThread: async (projectId: string): Promise<ChatThread> =>
    api.post<ChatThread>(`/projects/${projectId}/threads`, {}),

  getPlatformKnowledgeStatus: async (): Promise<PlatformKnowledgeStatus> =>
    api.get<PlatformKnowledgeStatus>("/sitewise/platform-knowledge"),

  getLlmModels: async (): Promise<ChatModelsResponse> =>
    api.get<ChatModelsResponse>("/config/llm/models"),

  getAgentModels: async (): Promise<AgentModelsResponse> =>
    api.get<AgentModelsResponse>("/config/agent/models"),

  getBillingPlans: async (): Promise<BillingPlansResponse> =>
    api.get<BillingPlansResponse>("/billing/plans", { auth: false }),

  getBillingStatus: async (): Promise<BillingStatus> =>
    api.get<BillingStatus>("/billing/subscription"),

  createBillingCheckout: async (planId: string): Promise<string> => {
    const response = await api.post<{ checkout_url: string }>("/billing/checkout", {
      plan_id: planId,
    });
    return response.checkout_url;
  },

  openBillingPortal: async (): Promise<string> => {
    const response = await api.post<{ portal_url: string }>("/billing/portal", {});
    return response.portal_url;
  },

  getLatestDraft: async (
    projectId: string,
    workflowType = "create_pmp",
  ): Promise<DraftArtifact | null> =>
    api.get<DraftArtifact | null>(
      `/projects/${projectId}/drafts/latest?workflow_type=${encodeURIComponent(
        workflowType,
      )}`,
    ),

  runCreatePmp: async (
    projectId: string,
    threadId?: string,
  ): Promise<CreatePmpResponse> =>
    api.post<CreatePmpResponse>(
      `/projects/${projectId}/workflows/create-pmp`,
      {
        ...workflowChatModelPayload(),
        ...(threadId ? { thread_id: threadId } : {}),
      },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    ),

  runCreateCostPlan: async (
    projectId: string,
    threadId?: string,
  ): Promise<CreateCostPlanResponse> =>
    api.post<CreateCostPlanResponse>(
      `/projects/${projectId}/workflows/create-cost-plan`,
      {
        ...workflowChatModelPayload(),
        ...(threadId ? { thread_id: threadId } : {}),
      },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    ),

  runUpdatePmp: async (
    projectId: string,
    threadId?: string,
  ): Promise<CreatePmpResponse> =>
    api.post<CreatePmpResponse>(
      `/projects/${projectId}/workflows/update-pmp`,
      {
        ...workflowChatModelPayload(),
        ...(threadId ? { thread_id: threadId } : {}),
      },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    ),

  patchDraft: async (
    projectId: string,
    draftId: string,
    contentMarkdown: string,
  ): Promise<DraftArtifact> =>
    api.patch<DraftArtifact>(`/projects/${projectId}/drafts/${draftId}`, {
      content_markdown: contentMarkdown,
    }),

  putDecision: async (
    projectId: string,
    decisionId: string,
    selected: string,
  ): Promise<UpdateProjectDecisionResponse> =>
    api.put<UpdateProjectDecisionResponse>(
      `/projects/${projectId}/decisions/${decisionId}`,
      { selected },
    ),

  acceptDraft: async (projectId: string, draftId: string): Promise<DraftArtifact> =>
    api.post<DraftArtifact>(`/projects/${projectId}/drafts/${draftId}/accept`),

  runSortFiles: async (
    projectId: string,
    threadId?: string,
  ): Promise<SortFilesResponse> =>
    api.post<SortFilesResponse>(
      `/projects/${projectId}/workflows/sort-files`,
      {
        ...workflowChatModelPayload(),
        ...(threadId ? { thread_id: threadId } : {}),
      },
      { timeoutMs: WORKFLOW_TIMEOUT_MS },
    ),

  uploadInboxFiles: async (
    projectId: string,
    files: File[],
    relativePath?: string,
  ): Promise<InboxUploadResult[]> => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    if (relativePath) {
      formData.append("relative_path", relativePath);
    }

    const token = await getAccessToken();
    if (!token) {
      throw new ApiError("Not signed in.", { kind: "http", status: 401 });
    }

    const base = env.apiBaseUrl.replace(/\/$/, "");
    const url = `${base}/projects/${projectId}/inbox/upload`;

    const response = await httpRequest<{ files: InboxUploadResult[] }>(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: formData,
      timeoutMs: WORKFLOW_TIMEOUT_MS,
    });

    return response.files;
  },
};
