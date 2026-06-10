import { getAccessToken } from "@/lib/auth";
import { workflowChatModelPayload, type ChatModelsResponse } from "@/lib/chat-model";
import { env } from "@/lib/env";
import { ApiError, httpRequest } from "@/lib/http";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type {
  BillingPlansResponse,
  BillingStatus,
} from "@/lib/types/billing";
import type {
  CreateCostPlanResponse,
  CreatePmpResponse,
  SortFilesResponse,
  CreateProjectInput,
  DraftArtifact,
  EvidencePreview,
  InboxUploadResult,
  PdfAnalyzeResult,
  PlatformKnowledgeStatus,
  ProjectCockpitBootstrap,
  ProjectDetail,
  ProjectSummary,
  ProjectWorkspaceTree,
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

  getProject: async (projectId: string): Promise<ProjectDetail> =>
    api.get<ProjectDetail>(`/projects/${projectId}`),

  getProjectCockpitBootstrap: async (
    projectId: string,
  ): Promise<ProjectCockpitBootstrap> =>
    api.get<ProjectCockpitBootstrap>(`/projects/${projectId}/cockpit-bootstrap`),

  getProjectWorkspaceTree: async (
    projectId: string,
  ): Promise<ProjectWorkspaceTree> =>
    api.get<ProjectWorkspaceTree>(`/projects/${projectId}/workspace-tree`),

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

    const token = await getAccessToken();
    if (!token) {
      throw new ApiError("Not signed in.", { kind: "http", status: 401 });
    }

    const base = env.apiBaseUrl.replace(/\/$/, "");
    return httpRequest<PdfAnalyzeResult>(
      `${base}/projects/${projectId}/inbox/analyze`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        timeoutMs: WORKFLOW_TIMEOUT_MS,
      },
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
