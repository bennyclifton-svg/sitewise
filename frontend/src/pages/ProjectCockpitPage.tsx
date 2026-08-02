import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useOutlet, useParams } from "react-router-dom";

import { DocumentRepositoryPanel } from "@/components/project/DocumentRepositoryPanel";
import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import type { RunnableProcurementRequestKind } from "@/components/project/ProcurementRequestPanel";
import { ChatRail } from "@/components/chat/ChatRail";
import { ProjectLeftNav, type ProjectNavView } from "@/components/project/ProjectLeftNav";
import {
  findDraftByWorkspacePath,
  isCostPlanWorkspaceFile,
  isDraftArtifactWorkspaceFile,
  isPmpWorkspaceFile,
} from "@/components/project/workflow/workspaceRouting";
import { buildLifecycleTiles } from "@/components/project/workflow/workflowTiles";
import { projectChatLayoutState } from "@/components/project/projectChatLayout";
import { ProjectShell } from "@/components/project/ProjectShell";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { projectSiteAddress } from "@/lib/project-taxonomy";
import {
  projectKeys,
  reloadProjectWorkspaceTree,
  seedProjectData,
  setProjectDetail,
  useProjectDetail,
  useProjectEvidence,
  useProjectEventCursor,
  useProjectWorkspaceTree,
} from "@/lib/queries/project-data";
import { projectActivityKeys } from "@/lib/queries/project-activity";
import { useWorkflowRun, waitForWorkflowRun } from "@/lib/queries/workflow-runs";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type {
  CreatePmpResponse,
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
  InboxUploadResult,
  PlatformKnowledgeStatus,
  ProjectDetail,
  ProjectEvent,
  ProjectSummary,
  ProjectSnapshot,
  SortFilesResponse,
  WorkspaceTreeNode,
  WorkflowRunStartInput,
} from "@/lib/types/project";
import type { WorkflowProgressMode } from "@/lib/workflow-progress";

/* eslint-disable react-hooks/set-state-in-effect */

/**
 * Errors we raise carry a message written for the user. Anything else is a bug
 * we did not anticipate, so keep the readable fallback but append the raw
 * message and log the error: a failure nobody can name is a failure nobody can
 * fix.
 */
function formatApiError(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof WorkflowRunError) {
    return error.message;
  }
  console.error(fallback, error);
  return error instanceof Error && error.message
    ? `${fallback} (${error.message})`
    : fallback;
}

class WorkflowRunError extends Error {}

const EMPTY_EVIDENCE: EvidencePreview[] = [];
const EMPTY_WORKSPACE_TREE: WorkspaceTreeNode[] = [];

const DraftReviewPanel = lazy(() =>
  import("@/components/project/DraftReviewPanel").then((module) => ({
    default: module.DraftReviewPanel,
  })),
);
const WorkspaceFilePanel = lazy(() =>
  import("@/components/project/WorkspaceFilePanel").then((module) => ({
    default: module.WorkspaceFilePanel,
  })),
);
const WorkspaceFolderPanel = lazy(() =>
  import("@/components/project/WorkspaceFolderPanel").then((module) => ({
    default: module.WorkspaceFolderPanel,
  })),
);

function workflowRunInput(
  project: ProjectDetail,
  threadId?: string,
  expectedArtefactVersion?: number,
): WorkflowRunStartInput {
  const fingerprint =
    project.workflow_capabilities?.snapshot_content_fingerprint;
  if (!fingerprint) {
    throw new WorkflowRunError("Project workflow inputs are still loading.");
  }
  return {
    idempotency_key: crypto.randomUUID(),
    expected_snapshot_fingerprint: fingerprint,
    expected_profile_revision: project.profile_revision ?? 1,
    expected_decision_set_revision: project.decision_set_revision ?? 1,
    ...(expectedArtefactVersion
      ? { expected_artefact_version: expectedArtefactVersion }
      : {}),
    ...(threadId ? { thread_id: threadId } : {}),
  };
}

function workflowPayload<T>(
  payload: Record<string, unknown> | null,
  fallback: string,
): T {
  if (!payload) throw new WorkflowRunError(fallback);
  return payload as T;
}

function isProcurementDraftWorkflow(workflowType: string): boolean {
  return (
    workflowType.startsWith("consultant_procurement_") ||
    workflowType.startsWith("contractor_eoi_") ||
    workflowType.startsWith("trade_rft_") ||
    workflowType.startsWith("trade_rfq_")
  );
}

/**
 * Context handed to nested cockpit routes (e.g. the tender comparison views)
 * that render inside the project shell's middle panel.
 */
export type ProjectCockpitOutletContext = {
  project: ProjectDetail | null;
  selectedRepositoryEvidence?: EvidencePreview[];
};

export function ProjectCockpitPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [bootstrapLoaded, setBootstrapLoaded] = useState(false);
  const { data: project = null } = useProjectDetail(projectId ?? "", {
    enabled: bootstrapLoaded && !!projectId,
  });
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("create-pmp");
  const { data: evidence = EMPTY_EVIDENCE } = useProjectEvidence(
    projectId ?? "",
    { enabled: bootstrapLoaded && !!projectId },
  );
  const { data: workspaceTree = EMPTY_WORKSPACE_TREE } = useProjectWorkspaceTree(
    projectId ?? "",
    { enabled: bootstrapLoaded && !!projectId },
  );
  const [platformStatus, setPlatformStatus] =
    useState<PlatformKnowledgeStatus | null>(null);
  const [snapshot, setSnapshot] = useState<ProjectSnapshot | null>(null);
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [latestDraft, setLatestDraft] = useState<DraftArtifactSummary | null>(null);
  const [latestCostPlanDraft, setLatestCostPlanDraft] =
    useState<DraftArtifactSummary | null>(null);
  const [latestDraftsMap, setLatestDraftsMap] = useState<
    Record<string, DraftArtifactSummary | null>
  >({});
  const [reviewDraft, setReviewDraft] = useState<DraftArtifactSummary | null>(null);
  const [workflowResult, setWorkflowResult] = useState<CreatePmpResponse | null>(null);
  const [costPlanWorkflowResult, setCostPlanWorkflowResult] = useState<CreatePmpResponse | null>(
    null,
  );
  const [sortFilesResult, setSortFilesResult] = useState<SortFilesResponse | null>(null);
  const [sortFilesDraft, setSortFilesDraft] = useState<DraftArtifactSummary | null>(null);
  const [sortFilesError, setSortFilesError] = useState<string | null>(null);
  const [isRunningSortFiles, setIsRunningSortFiles] = useState(false);
  const [activeView, setActiveView] = useState<ProjectNavView>("workbench");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [selectedRepositoryEvidenceIds, setSelectedRepositoryEvidenceIds] = useState<
    Set<string>
  >(() => new Set<string>());
  const [selectedWorkspacePath, setSelectedWorkspacePath] = useState<string | null>(null);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [chatRevision, setChatRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatReloadToken, setChatReloadToken] = useState(0);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [costPlanWorkflowError, setCostPlanWorkflowError] = useState<string | null>(null);
  const [procurementError, setProcurementError] = useState<string | null>(null);
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);
  const [isRunningCostPlan, setIsRunningCostPlan] = useState(false);
  const [isRunningProcurement, setIsRunningProcurement] = useState(false);
  const [pmpRunMode, setPmpRunMode] = useState<WorkflowProgressMode | null>(null);
  const [costPlanRunMode, setCostPlanRunMode] = useState<WorkflowProgressMode | null>(
    null,
  );
  /** Stable strip session keys so the bar does not reset when the server run id arrives. */
  const [pmpProgressKey, setPmpProgressKey] = useState<string | null>(null);
  const [costPlanProgressKey, setCostPlanProgressKey] = useState<string | null>(null);
  const [workflowRunId, setWorkflowRunId] = useState<string | null>(null);
  const [costPlanRunId, setCostPlanRunId] = useState<string | null>(null);
  const [procurementRunId, setProcurementRunId] = useState<string | null>(null);
  const [procurementRefreshToken, setProcurementRefreshToken] = useState(0);
  const [sortFilesRunId, setSortFilesRunId] = useState<string | null>(null);
  const activeWorkflowRunQuery = useWorkflowRun(projectId ?? "", workflowRunId);
  const activeCostPlanRunQuery = useWorkflowRun(projectId ?? "", costPlanRunId);
  const activeProcurementRunQuery = useWorkflowRun(projectId ?? "", procurementRunId);
  const [chatPanelCollapsed, setChatPanelCollapsed] = useState(true);
  const reconcileArtefactEvent = useCallback(
    (event: ProjectEvent) => {
      if (event.resource_type !== "artefact_revision" || !projectId) return;
      const workflowType = event.payload.workflow_type;
      if (typeof workflowType !== "string") return;
      const tracked =
        workflowType === "create_pmp" ||
        workflowType === "create_cost_plan" ||
        workflowType.startsWith("consultant_procurement") ||
        workflowType.startsWith("contractor_eoi") ||
        workflowType.startsWith("trade_rft") ||
        workflowType.startsWith("trade_rfq");
      if (!tracked) return;
      void api.getLatestDraft(projectId, workflowType).then((draft) => {
        if (!draft) return;
        setLatestDraftsMap((current) => ({
          ...current,
          [workflowType]: draft,
        }));
        if (workflowType === "create_cost_plan") setLatestCostPlanDraft(draft);
        else if (workflowType === "create_pmp") setLatestDraft(draft);
        else setProcurementRefreshToken((current) => current + 1);
      });
    },
    [projectId],
  );
  const projectEvents = useProjectEventCursor({
    projectId: projectId ?? "",
    enabled: bootstrapLoaded && !!projectId,
    active:
      isRunningWorkflow ||
      isRunningCostPlan ||
      isRunningProcurement ||
      isRunningSortFiles,
    onEvent: reconcileArtefactEvent,
  });

  useEffect(() => {
    if (!projectId) return;
    const id = projectId;
    let cancelled = false;

    async function loadProject() {
      setLoading(true);
      setProjectsLoading(true);
      setBootstrapLoaded(false);
      setProjectError(null);
      setChatError(null);
      setThread(null);
      setMessages([]);
      try {
        const data = await api.getProjectCockpitBootstrap(id);
        if (cancelled) return;
        setProjects(data.projects);
        seedProjectData(queryClient, id, {
          project: data.project,
          evidence: data.evidence,
          workspaceTree: data.workspace_tree.tree,
        });
        setBootstrapLoaded(true);
        setPlatformStatus(data.platform_knowledge);
        setSnapshot(data.snapshot);
        setLatestDraft(data.latest_drafts.create_pmp ?? null);
        setLatestCostPlanDraft(data.latest_drafts.create_cost_plan ?? null);
        setLatestDraftsMap(data.latest_drafts);
        setSortFilesDraft(data.latest_drafts.sort_files ?? null);
        setSelectedEvidenceId((current) =>
          current && data.evidence.some((item) => item.id === current)
            ? current
            : data.evidence[0]?.id ?? null,
        );
        setSelectedWorkspacePath((current) =>
          current && findWorkspaceNode(data.workspace_tree.tree, current)
            ? current
            : data.workspace_tree.tree[0]?.path ?? null,
        );
      } catch (loadError) {
        if (!cancelled) {
          setProjectError(formatApiError(loadError, "Could not load this project."));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setProjectsLoading(false);
        }
      }
    }

    void loadProject();
    return () => {
      cancelled = true;
    };
  }, [projectId, queryClient]);

  // Keep the selected evidence valid as the cached list changes (delete,
  // upload, sort). Preserves the current selection when it still exists.
  useEffect(() => {
    setSelectedEvidenceId((current) =>
      current && evidence.some((item) => item.id === current)
        ? current
        : evidence[0]?.id ?? null,
    );
  }, [evidence]);

  useEffect(() => {
    const evidenceIds = new Set(evidence.map((item) => item.id));
    setSelectedRepositoryEvidenceIds((current) => {
      const next = new Set([...current].filter((id) => evidenceIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [evidence]);

  useEffect(() => {
    setSelectedWorkspacePath((current) =>
      current && findWorkspaceNode(workspaceTree, current)
        ? current
        : workspaceTree[0]?.path ?? null,
    );
  }, [workspaceTree]);

  useEffect(() => {
    if (!projectId || !bootstrapLoaded) return;
    const params = new URLSearchParams(location.search);
    const draftId = params.get("artefact");
    if (!draftId) return;
    const expectedRevision = params.get("revision");
    let cancelled = false;
    void api.getProjectDraft(projectId, draftId).then((draft) => {
      if (cancelled) return;
      if (expectedRevision && draft.version !== Number(expectedRevision)) {
        setProjectError(`Artefact revision v${expectedRevision} is no longer available.`);
        return;
      }
      setReviewDraft(draft);
      setLatestDraftsMap((current) => ({ ...current, [draft.workflow_type]: draft }));
      setSelectedWorkspacePath(draft.workspace_path);
      setSelectedWorkflowId(
        draft.workflow_type === "create_cost_plan"
          ? "cost-plan"
          : isProcurementDraftWorkflow(draft.workflow_type)
            ? "procurement-requests"
            : "create-pmp",
      );
      setChatPanelCollapsed(true);
      setActiveView("draft");
    }).catch((error: unknown) => {
      if (!cancelled) {
        setProjectError(formatApiError(error, "Could not open that artefact revision."));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [bootstrapLoaded, location.search, projectId]);

  useEffect(() => {
    if (!projectId) return;
    const id = projectId;
    let cancelled = false;

    async function loadProjectChat() {
      setChatLoading(true);
      setChatError(null);
      try {
        const bootstrap = await api.getProjectChatBootstrap(id);
        const existingThread = bootstrap.thread ?? (await api.createProjectThread(id));
        const loadedMessages = bootstrap.thread ? bootstrap.messages : [];
        if (cancelled) return;
        setThread(existingThread);
        setMessages(loadedMessages);
        setChatRevision((current) => current + 1);
      } catch (loadError) {
        if (!cancelled) {
          setChatError(formatApiError(loadError, "Could not open project chat."));
        }
      } finally {
        if (!cancelled) setChatLoading(false);
      }
    }

    void loadProjectChat();
    return () => {
      cancelled = true;
    };
  }, [projectId, chatReloadToken]);

  async function refreshEvidence() {
    if (!projectId) return;
    await queryClient.refetchQueries({
      queryKey: projectKeys.evidence(projectId),
    });
  }

  async function refreshWorkspaceTree() {
    if (!projectId) return;
    await reloadProjectWorkspaceTree(queryClient, projectId);
  }

  async function refreshLatestDraft(workflowType: "create_pmp" | "create_cost_plan") {
    if (!projectId) return null;
    return await api.getLatestDraft(projectId, workflowType);
  }

  async function refreshActivity() {
    if (!projectId) return;
    await queryClient.invalidateQueries({
      queryKey: projectActivityKeys.root(projectId),
    });
  }

  async function refreshMessages() {
    if (!thread) return;
    try {
      const loadedMessages = await api.getThreadMessages(thread.id);
      // Keep ChatPanel mounted; remounting resets scroll through full history.
      setMessages(loadedMessages);
      setChatError(null);
    } catch (loadError) {
      setChatError(formatApiError(loadError, "Could not refresh project chat."));
    }
  }

  function refreshWorkflowSurfaces() {
    void Promise.allSettled([
      refreshMessages(),
      refreshWorkspaceTree(),
      refreshActivity(),
      projectId
        ? queryClient.invalidateQueries({
            queryKey: projectKeys.detail(projectId),
            exact: true,
          })
        : Promise.resolve(),
    ]);
  }

  async function freshWorkflowRunInput(
    expectedArtefactVersion?: number,
  ): Promise<WorkflowRunStartInput> {
    if (!projectId) {
      throw new WorkflowRunError("Project workflow inputs are still loading.");
    }
    // Read the project directly instead of through `fetchQuery`. The detail
    // cache entry is owned by the project-event poller, which invalidates it on
    // every durable event, and `invalidateQueries` cancels an in-flight read
    // (`cancelRefetch` defaults to true) — that rejection surfaces as a bare
    // `CancelledError` and aborts the launch before any request is sent. The
    // cache read also inherited the global 30s `staleTime`, so the OCC
    // fingerprint this call exists to refresh could be handed back stale.
    const fresh = await api.getProject(projectId);
    setProjectDetail(queryClient, fresh);
    return workflowRunInput(fresh, thread?.id, expectedArtefactVersion);
  }

  function refreshLatestDraftInBackground(
    workflowType: "create_pmp" | "create_cost_plan",
  ) {
    void refreshLatestDraft(workflowType)
      .then((draft) => {
        if (!draft) return;
        if (workflowType === "create_cost_plan") {
          setLatestCostPlanDraft(draft);
        } else {
          setLatestDraft(draft);
        }
      })
      .catch(() => undefined);
  }

  function openDraftReview(draft: DraftArtifactSummary) {
    setReviewDraft(draft);
    setLatestDraftsMap((current) => ({
      ...current,
      [draft.workflow_type]: draft,
    }));
    setSelectedWorkspacePath(draft.workspace_path);
    setChatPanelCollapsed(true);
    if (draft.workflow_type === "create_cost_plan") {
      setLatestCostPlanDraft(draft);
      setSelectedWorkflowId("cost-plan");
      // Cost plan drafts render inline on the Cost Plan workbench.
      setActiveView("workbench");
      return;
    }
    if (draft.workflow_type === "create_pmp") {
      setLatestDraft(draft);
      setSelectedWorkflowId("create-pmp");
      // PMP drafts render inline on the Project Plan workbench.
      setActiveView("workbench");
      return;
    }
    if (isProcurementDraftWorkflow(draft.workflow_type)) {
      setSelectedWorkflowId("procurement-requests");
      setProcurementRefreshToken((current) => current + 1);
      setActiveView("workbench");
      return;
    }
    setActiveView("draft");
  }

  function showPmpDraft(draft: DraftArtifactSummary) {
    openDraftReview(draft);
  }

  async function handleDraftUpdated(draft: DraftArtifact) {
    setReviewDraft(draft);
    setLatestDraftsMap((current) => ({
      ...current,
      [draft.workflow_type]: draft,
    }));
    if (draft.workflow_type === "create_cost_plan") {
      setLatestCostPlanDraft(draft);
      setSelectedWorkspacePath(draft.workspace_path);
    } else if (isProcurementDraftWorkflow(draft.workflow_type)) {
      setSelectedWorkspacePath(draft.workspace_path);
      setProcurementRefreshToken((current) => current + 1);
    } else {
      setLatestDraft(draft);
      const pmpPath = isPmpWorkspaceFile(draft.workspace_path)
        ? draft.workspace_path
        : project
          ? `${project.workspace_path}/00-brief-pmp/PMP.md`
          : null;
      if (pmpPath) {
        setSelectedWorkspacePath(pmpPath);
      }
    }
    await refreshWorkspaceTree();
  }

  function showCostPlanDraft(draft: DraftArtifactSummary) {
    openDraftReview(draft);
  }

  async function handleSelectThread(threadId: string) {
    setChatPanelCollapsed(false);
    setChatLoading(true);
    setSelectedCitationId(null);
    setChatError(null);
    try {
      const loadedThread = await api.getThread(threadId);
      const loadedMessages = await api.getThreadMessages(threadId);
      setThread(loadedThread);
      setMessages(loadedMessages);
      setChatRevision((current) => current + 1);
    } catch (loadError) {
      setChatError(formatApiError(loadError, "Could not open that chat session."));
    } finally {
      setChatLoading(false);
    }
  }

  function handleCreateThread(created: ChatThread) {
    setChatPanelCollapsed(false);
    setThread(created);
    setMessages([]);
    setSelectedCitationId(null);
    setChatError(null);
    setChatRevision((current) => current + 1);
  }

  async function handleActiveThreadDeleted() {
    if (!project) return;
    setChatLoading(true);
    setSelectedCitationId(null);
    setChatError(null);
    try {
      const threads = await api.listThreads();
      const existingThread = threads.find((candidate) => candidate.project_id === project.id);
      if (existingThread) {
        await handleSelectThread(existingThread.id);
        return;
      }
      const created = await api.createProjectThread(project.id);
      handleCreateThread(created);
    } catch (loadError) {
      setChatError(formatApiError(loadError, "Could not restore project chat."));
    } finally {
      setChatLoading(false);
    }
  }

  function handleSelectCitation(citation: Citation | null) {
    setSelectedCitationId(citation?.sourceId ?? null);
  }

  function promoteChatFromComposer() {
    leaveTenderRoute();
    setActiveView("workbench");
    setChatPanelCollapsed(false);
  }

  function handleChatCollapsedChange(collapsed: boolean) {
    if (!collapsed) {
      leaveTenderRoute();
      setActiveView("workbench");
    }
    setChatPanelCollapsed(collapsed);
  }

  async function runSortFiles() {
    if (!project) return;
    setIsRunningSortFiles(true);
    setSortFilesError(null);
    try {
      const queued = await api.startWorkflowRun(
        project.id,
        "sort-files",
        await freshWorkflowRunInput(),
      );
      setSortFilesRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(run.error_message ?? `Sort Files ${run.state}.`);
      }
      const response = await api.getWorkflowResult(project.id, run.id);
      const result = workflowPayload<SortFilesResponse>(
        response.result,
        "Sort Files completed without a result.",
      );
      setSortFilesResult(result);
      if (result.draft) {
        setSortFilesDraft(result.draft);
      }
      await Promise.all([
        refreshEvidence(),
        refreshWorkspaceTree(),
        refreshMessages(),
        refreshActivity(),
      ]);
    } catch (runError) {
      setSortFilesError(formatApiError(runError, "Sort Files could not run."));
    } finally {
      setSortFilesRunId(null);
      setIsRunningSortFiles(false);
    }
  }

  async function runCreatePmp() {
    if (!project) return;
    setPmpRunMode("create");
    setPmpProgressKey(`pmp-${Date.now()}`);
    setIsRunningWorkflow(true);
    setWorkflowError(null);
    try {
      const queued = await api.startWorkflowRun(
        project.id,
        "project-plan",
        await freshWorkflowRunInput(),
      );
      setWorkflowRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(
          run.error_message ?? `Create Project Plan ${run.state}.`,
        );
      }
      const response = await api.getWorkflowResult(project.id, run.id);
      const result = workflowPayload<CreatePmpResponse>(
        response.result,
        "Create Project Plan completed without a result.",
      );
      setWorkflowResult(result);
      if (result.status === "failed" || result.status === "blocked") {
        setWorkflowError(result.message ?? "Create PMP did not complete.");
      }
      if (result.draft) {
        showPmpDraft(result.draft);
      }
      refreshLatestDraftInBackground("create_pmp");
      refreshWorkflowSurfaces();
    } catch (runError) {
      setWorkflowError(formatApiError(runError, "Create PMP could not run."));
    } finally {
      setWorkflowRunId(null);
      setPmpRunMode(null);
      setPmpProgressKey(null);
      setIsRunningWorkflow(false);
    }
  }

  async function runCreateCostPlan() {
    if (!project) return;
    setCostPlanRunMode("create");
    setCostPlanProgressKey(`cost-${Date.now()}`);
    setIsRunningCostPlan(true);
    setCostPlanWorkflowError(null);
    try {
      const queued = await api.startWorkflowRun(
        project.id,
        "cost-plan",
        await freshWorkflowRunInput(),
      );
      setCostPlanRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(
          run.error_message ?? `Create Cost Plan ${run.state}.`,
        );
      }
      const response = await api.getWorkflowResult(project.id, run.id);
      const result = workflowPayload<CreatePmpResponse>(
        response.result,
        "Create Cost Plan completed without a result.",
      );
      setCostPlanWorkflowResult(result);
      if (result.status === "failed" || result.status === "blocked") {
        setCostPlanWorkflowError(result.message ?? "Create Cost Plan did not complete.");
      }
      if (result.draft) {
        showCostPlanDraft(result.draft);
      }
      refreshLatestDraftInBackground("create_cost_plan");
      refreshWorkflowSurfaces();
    } catch (runError) {
      setCostPlanWorkflowError(formatApiError(runError, "Create Cost Plan could not run."));
    } finally {
      setCostPlanRunId(null);
      setCostPlanRunMode(null);
      setCostPlanProgressKey(null);
      setIsRunningCostPlan(false);
    }
  }

  async function runRefreshCostPlan() {
    if (!project) return;
    setCostPlanRunMode("update");
    setCostPlanProgressKey(`cost-${Date.now()}`);
    setIsRunningCostPlan(true);
    setCostPlanWorkflowError(null);
    try {
      if (!latestCostPlanDraft) {
        throw new WorkflowRunError("Create a Cost Plan before refreshing it.");
      }
      const queued = await api.startWorkflowRun(
        project.id,
        "cost-plan/refresh",
        {
          ...(await freshWorkflowRunInput(latestCostPlanDraft.version)),
          parameters: { proposed_items: [] },
        },
      );
      setCostPlanRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(
          run.error_message ?? `Refresh Cost Plan ${run.state}.`,
        );
      }
      const response = await api.getWorkflowResult(project.id, run.id);
      const result = workflowPayload<CreatePmpResponse>(
        response.result,
        "Refresh Cost Plan completed without a result.",
      );
      setCostPlanWorkflowResult(result);
      if (result.status === "failed" || result.status === "blocked") {
        setCostPlanWorkflowError(result.message ?? "Refresh Cost Plan did not complete.");
      }
      if (result.draft) {
        showCostPlanDraft(result.draft);
      }
      refreshLatestDraftInBackground("create_cost_plan");
      refreshWorkflowSurfaces();
    } catch (runError) {
      setCostPlanWorkflowError(
        formatApiError(runError, "Refresh Cost Plan could not run."),
      );
    } finally {
      setCostPlanRunId(null);
      setCostPlanRunMode(null);
      setCostPlanProgressKey(null);
      setIsRunningCostPlan(false);
    }
  }

  async function runUpdatePmp() {
    if (!project) return;
    setPmpRunMode("update");
    setPmpProgressKey(`pmp-${Date.now()}`);
    setIsRunningWorkflow(true);
    setWorkflowError(null);
    try {
      if (!latestDraft) {
        throw new WorkflowRunError(
          "Create a Project Plan before refreshing it.",
        );
      }
      const queued = await api.startWorkflowRun(
        project.id,
        "project-plan/refresh",
        await freshWorkflowRunInput(latestDraft.version),
      );
      setWorkflowRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(
          run.error_message ?? `Refresh Project Plan ${run.state}.`,
        );
      }
      const response = await api.getWorkflowResult(project.id, run.id);
      const result = workflowPayload<CreatePmpResponse>(
        response.result,
        "Refresh Project Plan completed without a result.",
      );
      setWorkflowResult(result);
      if (result.status === "failed" || result.status === "blocked") {
        setWorkflowError(result.message ?? "Update PMP did not complete.");
      }
      if (result.draft) {
        showPmpDraft(result.draft);
      }
      refreshLatestDraftInBackground("create_pmp");
      refreshWorkflowSurfaces();
    } catch (runError) {
      setWorkflowError(formatApiError(runError, "Update PMP could not run."));
    } finally {
      setWorkflowRunId(null);
      setPmpRunMode(null);
      setPmpProgressKey(null);
      setIsRunningWorkflow(false);
    }
  }

  async function runProcurementRequest(
    kind: RunnableProcurementRequestKind,
    targetName: string,
  ) {
    if (!project) return;
    setIsRunningProcurement(true);
    setProcurementError(null);
    try {
      const parameters =
        kind === "consultant_rfp"
          ? {
              discipline: targetName,
              max_pages: 3,
            }
          : {
              package: targetName,
              kind: kind === "trade_rft" ? "rft" : "rfq",
              max_pages: 3,
            };
      const queued = await api.startWorkflowRun(
        project.id,
        kind === "consultant_rfp" ? "consultant-procurement" : "trade-procurement",
        {
          ...(await freshWorkflowRunInput()),
          parameters,
        },
      );
      setProcurementRunId(queued.id);
      const run = await waitForWorkflowRun(queryClient, project.id, queued);
      if (run.state === "failed" || run.state === "cancelled") {
        throw new WorkflowRunError(
          run.error_message ?? `Procurement request ${run.state}.`,
        );
      }
      await api.getWorkflowResult(project.id, run.id);
      setProcurementRefreshToken((current) => current + 1);
      refreshWorkflowSurfaces();
    } catch (runError) {
      setProcurementError(
        formatApiError(runError, "Procurement request could not be created."),
      );
    } finally {
      setProcurementRunId(null);
      setIsRunningProcurement(false);
    }
  }

  // Nested tender routes render in the middle panel via <Outlet>. Any
  // interaction that switches the middle panel back to a state-driven view must
  // also leave the tender route so the outlet stops taking precedence.
  function leaveTenderRoute() {
    if (projectId && location.pathname !== `/projects/${projectId}`) {
      navigate(`/projects/${projectId}`);
    }
  }

  function isTenderRouteActive() {
    return Boolean(projectId && location.pathname.startsWith(`/projects/${projectId}/tender`));
  }

  function openWorkflowFromExplorer(workflowId: string) {
    if (workflowId === "procurement") {
      setSelectedWorkflowId(workflowId);
      setChatPanelCollapsed(true);
      navigate(`/projects/${projectId}/tender`);
      return;
    }
    leaveTenderRoute();
    setSelectedWorkflowId(workflowId);
    setChatPanelCollapsed(true);
    setActiveView("workbench");
  }

  function selectEvidenceFromRepository(evidenceId: string) {
    const keepTenderRoute = isTenderRouteActive();
    if (!keepTenderRoute) {
      leaveTenderRoute();
    }
    setSelectedEvidenceId(evidenceId);
    const item = evidence.find((candidate) => candidate.id === evidenceId);
    if (item) {
      setSelectedWorkspacePath(normalizeWorkspacePath(item.relative_path));
      if (keepTenderRoute) {
        return;
      }
      if (isPmpWorkspaceFile(item.relative_path)) {
        setSelectedWorkflowId("create-pmp");
        setChatPanelCollapsed(true);
        setActiveView("workbench");
        return;
      }
      if (isCostPlanWorkspaceFile(item.relative_path)) {
        setSelectedWorkflowId("cost-plan");
        setChatPanelCollapsed(true);
        setActiveView("workbench");
        return;
      }
    }
    if (activeView === "draft") {
      return;
    }
    setChatPanelCollapsed(true);
    setActiveView("file");
  }

  async function selectWorkspacePath(path: string) {
    const keepTenderRoute = isTenderRouteActive();
    if (!keepTenderRoute) {
      leaveTenderRoute();
    }
    setSelectedWorkspacePath(path);
    const selectedNode = findWorkspaceNode(workspaceTree, path);
    if (selectedNode?.kind === "file") {
      const draft =
        findDraftByWorkspacePath(latestDraftsMap, path) ??
        (isDraftArtifactWorkspaceFile(path) && projectId
          ? await api.getProjectDraftByWorkspacePath(projectId, path)
          : null);
      if (draft) {
        openDraftReview(draft);
        return;
      }
      const selectedDocument = findEvidenceByPath(evidence, selectedNode.path);
      if (selectedDocument) {
        setSelectedEvidenceId(selectedDocument.id);
        if (keepTenderRoute) {
          return;
        }
        setReviewDraft(null);
        setChatPanelCollapsed(true);
        setActiveView("file");
        return;
      }
    }
    setReviewDraft(null);
    setChatPanelCollapsed(true);
    setActiveView("folder");
  }

  // When a nested tender route is active, its element renders in the middle
  // panel; otherwise we fall back to the state-driven cockpit views below.
  const selectedRepositoryEvidence = useMemo(
    () => evidence.filter((item) => selectedRepositoryEvidenceIds.has(item.id)),
    [evidence, selectedRepositoryEvidenceIds],
  );
  const tenderOutlet = useOutlet({
    project,
    selectedRepositoryEvidence,
  } satisfies ProjectCockpitOutletContext);

  if (!projectId) return null;

  if (loading) {
    return (
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-8">
        <div className="h-8 w-64 animate-pulse rounded-md bg-muted" />
        <div className="h-[34rem] animate-pulse rounded-md bg-muted" />
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-10">
        <Button asChild variant="outline" className="w-fit">
          <Link to="/">
            <ArrowLeft className="size-4" aria-hidden />
            Back home
          </Link>
        </Button>
        <p className="text-sm text-destructive" role="alert">
          {projectError ?? "Project not found."}
        </p>
      </div>
    );
  }

  const trace = workflowResult?.trace ?? [];
  const costPlanTrace = costPlanWorkflowResult?.trace ?? [];
  const activeDraft =
    reviewDraft ??
    (selectedWorkflowId === "cost-plan" ? latestCostPlanDraft : latestDraft);
  const activeWorkflowType =
    reviewDraft?.workflow_type ??
    (selectedWorkflowId === "cost-plan" ? "create_cost_plan" : "create_pmp");
  const usageHighlightArtefactId =
    activeDraft?.workflow_type === "create_pmp" &&
    ((activeView === "workbench" && selectedWorkflowId === "create-pmp") ||
      activeView === "draft")
      ? activeDraft.id
      : null;
  const inboxCount = evidence.filter((item) => item.relative_path.includes("/_inbox/")).length;
  const selectedEvidence =
    evidence.find((item) => item.id === selectedEvidenceId) ?? evidence[0] ?? null;
  const selectedFolder = findWorkspaceNode(workspaceTree, selectedWorkspacePath);
  const lifecycleTiles = buildLifecycleTiles({
    project,
    latestDraft,
    latestCostPlanDraft,
    workflowError,
    costPlanWorkflowError,
    isRunningWorkflow,
    isRunningCostPlan,
    procurementError,
    isRunningProcurement,
  });

  function selectWorkflow(workflowId: string) {
    if (workflowId === "procurement") {
      setSelectedWorkflowId(workflowId);
      setChatPanelCollapsed(true);
      navigate(`/projects/${projectId}/tender`);
      return;
    }
    leaveTenderRoute();
    setSelectedWorkflowId(workflowId);
    setChatPanelCollapsed(true);
    setActiveView("workbench");
  }

  const { chatCollapsed, chatFullScreen } = projectChatLayoutState({
    activeView,
    chatPanelCollapsed,
    hasTenderOutlet: tenderOutlet != null,
  });

  return (
    <ProjectShell
      projectTitle={project.title}
      projectAddress={projectSiteAddress(project)}
      chatCollapsed={chatCollapsed}
      chatFullScreen={chatFullScreen}
      onShowWorkbench={() => {
        leaveTenderRoute();
        setChatPanelCollapsed(true);
        setActiveView("workbench");
      }}
      leftNav={
        <ProjectLeftNav
          project={project}
          projects={projects}
          projectsLoading={projectsLoading}
          workflows={{
            tiles: lifecycleTiles,
            selectedWorkflowId,
            onSelectWorkflow: selectWorkflow,
          }}
          chatHistory={{
            projectId: project.id,
            activeThreadId: thread?.id,
            onSelectThread: (threadId) => void handleSelectThread(threadId),
            onCreateSession: handleCreateThread,
            onActiveThreadDeleted: () => void handleActiveThreadDeleted(),
          }}
        />
      }
      chatPanel={
        <ChatRail
          layout="main"
          collapsed={chatCollapsed}
          onCollapsedChange={handleChatCollapsedChange}
          thread={thread}
          messages={messages}
          chatRevision={chatRevision}
          chatLoading={chatLoading}
          chatError={chatError}
          onRetry={() => setChatReloadToken((current) => current + 1)}
          selectedCitationId={selectedCitationId}
          onConversationUpdate={() => {
            void refreshMessages();
            projectEvents.pollNow();
          }}
          onResourceEvent={projectEvents.applyResource}
          onUserSubmit={promoteChatFromComposer}
          onSelectCitation={handleSelectCitation}
        />
      }
      repository={
        <DocumentRepositoryPanel
          projectId={project.id}
          evidence={evidence}
          selectedEvidenceId={selectedEvidence?.id ?? null}
          selectedEvidenceIds={selectedRepositoryEvidenceIds}
          workspaceTree={workspaceTree}
          selectedWorkspacePath={selectedWorkspacePath}
          onSelectEvidence={selectEvidenceFromRepository}
          onSelectedEvidenceIdsChange={setSelectedRepositoryEvidenceIds}
          onSelectWorkspacePath={selectWorkspacePath}
          onOpenWorkflow={openWorkflowFromExplorer}
          onViewWorkbench={() => {
            leaveTenderRoute();
            setChatPanelCollapsed(true);
            setActiveView("workbench");
          }}
          onViewFolder={() => {
            leaveTenderRoute();
            setChatPanelCollapsed(true);
            setActiveView("folder");
          }}
          onUploadComplete={async (outcomes: InboxUploadResult[] = []) => {
            await Promise.all(
              outcomes
                .flatMap((outcome) => (outcome.workflow_run_id ? [outcome.workflow_run_id] : []))
                .map(async (runId) => {
                  const run = await api.getWorkflowRun(project.id, runId);
                  await waitForWorkflowRun(queryClient, project.id, run);
                }),
            );
            await Promise.all([
              refreshEvidence(),
              refreshWorkspaceTree(),
              refreshActivity(),
            ]);
          }}
          onRunSortFiles={() => void runSortFiles()}
          isRunningSortFiles={isRunningSortFiles}
          overlayReady={project.overlay_status.ready}
          platformStatus={platformStatus}
          artefactDrafts={Object.values(latestDraftsMap).filter(
            (draft): draft is DraftArtifactSummary => draft !== null,
          )}
          onOpenDraft={openDraftReview}
          usageHighlightArtefactId={usageHighlightArtefactId}
        />
      }
    >
      {tenderOutlet ?? (
        <>
      {activeView === "workbench" ? (
        <ProjectControlBoard
          project={project}
          profileProposals={snapshot?.open_profile_proposals ?? []}
          latestDraft={latestDraft}
          latestCostPlanDraft={latestCostPlanDraft}
          trace={trace}
          costPlanTrace={costPlanTrace}
          workflowError={workflowError}
          costPlanWorkflowError={costPlanWorkflowError}
          isRunningWorkflow={isRunningWorkflow}
          isRunningCostPlan={isRunningCostPlan}
          pmpRunMode={pmpRunMode}
          costPlanRunMode={costPlanRunMode}
          pmpProgressKey={pmpProgressKey}
          costPlanProgressKey={costPlanProgressKey}
          activeWorkflowRun={activeWorkflowRunQuery.data ?? null}
          activeCostPlanRun={activeCostPlanRunQuery.data ?? null}
          activeProcurementRun={activeProcurementRunQuery.data ?? null}
          procurementError={procurementError}
          isRunningProcurement={isRunningProcurement}
          procurementRefreshToken={procurementRefreshToken}
          selectedWorkflowId={selectedWorkflowId}
          onSelectWorkflow={selectWorkflow}
          onRunCreatePmp={() => void runCreatePmp()}
          onRunUpdatePmp={() => void runUpdatePmp()}
          onRunCreateCostPlan={() => void runCreateCostPlan()}
          onRunRefreshCostPlan={() => void runRefreshCostPlan()}
          onRunSortFiles={() => void runSortFiles()}
          onCancelWorkflow={() => {
            if (workflowRunId) void api.cancelWorkflowRun(project.id, workflowRunId);
          }}
          onCancelCostPlan={() => {
            if (costPlanRunId) void api.cancelWorkflowRun(project.id, costPlanRunId);
          }}
          onCancelProcurement={() => {
            if (procurementRunId) void api.cancelWorkflowRun(project.id, procurementRunId);
          }}
          onRunProcurement={(kind, targetName) =>
            void runProcurementRequest(kind, targetName)
          }
          onCancelSortFiles={() => {
            if (sortFilesRunId) void api.cancelWorkflowRun(project.id, sortFilesRunId);
          }}
          onDraftUpdated={(draft) => {
            void handleDraftUpdated(draft);
          }}
          onOpenTenderComparison={() => navigate(`/projects/${project.id}/tender`)}
          inboxCount={inboxCount}
          sortFilesResult={sortFilesResult}
          sortFilesDraft={sortFilesDraft}
          sortFilesError={sortFilesError}
          isRunningSortFiles={isRunningSortFiles}
          onProjectUpdated={(updatedProject) => {
            setProjectDetail(queryClient, updatedProject);
            void queryClient.invalidateQueries({
              queryKey: projectKeys.detail(updatedProject.id),
              exact: true,
            });
            setProjects((current) =>
              current.map((item) =>
                item.id === updatedProject.id ? updatedProject : item,
              ),
            );
          }}
          onProfileProposalsResolved={() => {
            void (async () => {
              try {
                const data = await api.getProjectCockpitBootstrap(project.id);
                setSnapshot(data.snapshot);
                seedProjectData(queryClient, project.id, {
                  project: data.project,
                  evidence: data.evidence,
                  workspaceTree: data.workspace_tree.tree,
                });
                setProjects(data.projects);
              } catch {
                // Keep the current cockpit state if refresh fails.
              }
            })();
          }}
        />
      ) : null}
      {activeView === "file" ? (
        <Suspense fallback={null}>
          <WorkspaceFilePanel projectId={project.id} evidence={selectedEvidence} />
        </Suspense>
      ) : null}
      {activeView === "folder" ? (
        <Suspense fallback={null}>
          <WorkspaceFolderPanel folder={selectedFolder} evidence={evidence} />
        </Suspense>
      ) : null}
      {activeView === "draft" && project ? (
        <Suspense fallback={null}>
          <DraftReviewPanel
          projectId={project.id}
          draft={activeDraft}
          workflowType={activeWorkflowType}
          onRunUpdatePmp={() => void runUpdatePmp()}
          isRunningUpdatePmp={isRunningWorkflow}
          onDraftUpdated={(draft) => {
            void handleDraftUpdated(draft);
          }}
          />
        </Suspense>
      ) : null}
        </>
      )}
    </ProjectShell>
  );
}

function findWorkspaceNode(
  nodes: WorkspaceTreeNode[],
  path: string | null,
): WorkspaceTreeNode | null {
  if (!path) return null;
  for (const node of nodes) {
    if (node.path === path) return node;
    const childMatch = findWorkspaceNode(node.children, path);
    if (childMatch) return childMatch;
  }
  return null;
}

function findEvidenceByPath(
  evidence: EvidencePreview[],
  path: string,
): EvidencePreview | null {
  const selectedPath = normalizeWorkspacePath(path);
  return (
    evidence.find((item) => normalizeWorkspacePath(item.relative_path) === selectedPath) ?? null
  );
}

function normalizeWorkspacePath(path: string): string {
  return path.replaceAll("\\", "/");
}
