import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useOutlet, useParams } from "react-router-dom";

import { DocumentRepositoryPanel } from "@/components/project/DocumentRepositoryPanel";
import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { WorkspaceFilePanel } from "@/components/project/WorkspaceFilePanel";
import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import { ChatRail } from "@/components/chat/ChatRail";
import { ProjectLeftNav, type ProjectNavView } from "@/components/project/ProjectLeftNav";
import { isCostPlanWorkspaceFile, isPmpWorkspaceFile, findDraftByWorkspacePath } from "@/components/project/workflow/workspaceRouting";
import { buildLifecycleTiles } from "@/components/project/workflow/workflowTiles";
import { projectChatLayoutState } from "@/components/project/projectChatLayout";
import { ProjectShell } from "@/components/project/ProjectShell";
import { WorkspaceFolderPanel } from "@/components/project/WorkspaceFolderPanel";
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
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type {
  CreatePmpResponse,
  DraftArtifactSummary,
  EvidencePreview,
  PlatformKnowledgeStatus,
  ProjectDetail,
  ProjectSummary,
  SortFilesResponse,
  WorkspaceTreeNode,
} from "@/lib/types/project";

/* eslint-disable react-hooks/set-state-in-effect */

function formatApiError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

const EMPTY_EVIDENCE: EvidencePreview[] = [];
const EMPTY_WORKSPACE_TREE: WorkspaceTreeNode[] = [];

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
  const [crossProject, setCrossProject] = useState(false);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [chatRevision, setChatRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [costPlanWorkflowError, setCostPlanWorkflowError] = useState<string | null>(null);
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);
  const [isRunningCostPlan, setIsRunningCostPlan] = useState(false);
  const [chatPanelCollapsed, setChatPanelCollapsed] = useState(true);
  const projectEvents = useProjectEventCursor({
    projectId: projectId ?? "",
    enabled: bootstrapLoaded && !!projectId,
    active:
      isRunningWorkflow ||
      isRunningCostPlan ||
      isRunningSortFiles,
  });

  useEffect(() => {
    if (!projectId) return;
    const id = projectId;
    let cancelled = false;

    async function loadProject() {
      setLoading(true);
      setProjectsLoading(true);
      setChatLoading(true);
      setBootstrapLoaded(false);
      setError(null);
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
          setError(formatApiError(loadError, "Could not load this project."));
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

  const activeProjectId = project?.id;
  useEffect(() => {
    if (!activeProjectId) return;
    const id = activeProjectId;
    let cancelled = false;

    async function ensureProjectThread() {
      setChatLoading(true);
      try {
        const threads = await api.listThreads();
        const existingThread =
          threads.find((candidate) => candidate.project_id === id) ??
          (await api.createProjectThread(id));
        const loadedMessages = await api.getThreadMessages(existingThread.id);
        if (cancelled) return;
        setThread(existingThread);
        setMessages(loadedMessages);
        setChatRevision((current) => current + 1);
      } catch (loadError) {
        if (!cancelled) {
          setError(formatApiError(loadError, "Could not open project chat."));
        }
      } finally {
        if (!cancelled) setChatLoading(false);
      }
    }

    void ensureProjectThread();
    return () => {
      cancelled = true;
    };
  }, [activeProjectId]);

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
    const loadedMessages = await api.getThreadMessages(thread.id);
    // Keep ChatPanel mounted; remounting resets scroll through full history.
    setMessages(loadedMessages);
  }

  function refreshWorkflowSurfaces() {
    void Promise.allSettled([
      refreshMessages(),
      refreshWorkspaceTree(),
      refreshActivity(),
    ]);
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
    if (draft.workflow_type === "create_cost_plan") {
      setLatestCostPlanDraft(draft);
      setSelectedWorkflowId("cost-plan");
    } else if (draft.workflow_type === "create_pmp") {
      setLatestDraft(draft);
      setSelectedWorkflowId("create-pmp");
    }
    setSelectedWorkspacePath(draft.workspace_path);
    setChatPanelCollapsed(true);
    setActiveView("draft");
  }

  function showPmpDraft(draft: DraftArtifactSummary) {
    openDraftReview(draft);
  }

  function showCostPlanDraft(draft: DraftArtifactSummary) {
    openDraftReview(draft);
  }

  async function handleSelectThread(threadId: string) {
    setChatPanelCollapsed(false);
    setChatLoading(true);
    setSelectedCitationId(null);
    try {
      const loadedThread = await api.getThread(threadId);
      const loadedMessages = await api.getThreadMessages(threadId);
      setThread(loadedThread);
      setMessages(loadedMessages);
      setChatRevision((current) => current + 1);
    } catch (loadError) {
      setError(formatApiError(loadError, "Could not open that chat session."));
    } finally {
      setChatLoading(false);
    }
  }

  function handleCreateThread(created: ChatThread) {
    setChatPanelCollapsed(false);
    setThread(created);
    setMessages([]);
    setSelectedCitationId(null);
    setChatRevision((current) => current + 1);
  }

  async function handleActiveThreadDeleted() {
    if (!project) return;
    setChatLoading(true);
    setSelectedCitationId(null);
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
      setError(formatApiError(loadError, "Could not restore project chat."));
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
      const result = await api.runSortFiles(project.id, thread?.id);
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
      setIsRunningSortFiles(false);
    }
  }

  async function runCreatePmp() {
    if (!project) return;
    setIsRunningWorkflow(true);
    setWorkflowError(null);
    try {
      const result = await api.runCreatePmp(project.id, thread?.id);
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
      setIsRunningWorkflow(false);
    }
  }

  async function runCreateCostPlan() {
    if (!project) return;
    setIsRunningCostPlan(true);
    setCostPlanWorkflowError(null);
    try {
      const result = await api.runCreateCostPlan(project.id, thread?.id);
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
      setIsRunningCostPlan(false);
    }
  }

  async function runUpdatePmp() {
    if (!project) return;
    setIsRunningWorkflow(true);
    setWorkflowError(null);
    try {
      const result = await api.runUpdatePmp(project.id, thread?.id);
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
      setIsRunningWorkflow(false);
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
    if (workflowId === "create-pmp" || workflowId === "cost-plan") {
      setSelectedEvidenceId(null);
      setChatPanelCollapsed(true);
      setActiveView("draft");
      return;
    }
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
        setActiveView("draft");
        return;
      }
      if (isCostPlanWorkspaceFile(item.relative_path)) {
        setSelectedWorkflowId("cost-plan");
        setChatPanelCollapsed(true);
        setActiveView("draft");
        return;
      }
    }
    if (activeView === "draft") {
      return;
    }
    setChatPanelCollapsed(true);
    setActiveView("file");
  }

  function selectWorkspacePath(path: string) {
    const keepTenderRoute = isTenderRouteActive();
    if (!keepTenderRoute) {
      leaveTenderRoute();
    }
    setSelectedWorkspacePath(path);
    const selectedNode = findWorkspaceNode(workspaceTree, path);
    if (selectedNode?.kind === "file") {
      const draft = findDraftByWorkspacePath(latestDraftsMap, path);
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

  if (error || !project) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-10">
        <Button asChild variant="outline" className="w-fit">
          <Link to="/">
            <ArrowLeft className="size-4" aria-hidden />
            Back home
          </Link>
        </Button>
        <p className="text-sm text-destructive" role="alert">
          {error ?? "Project not found."}
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
          crossProject={crossProject}
          selectedCitationId={selectedCitationId}
          onCrossProjectChange={setCrossProject}
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
          onUploadComplete={async () => {
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
        />
      }
    >
      {tenderOutlet ?? (
        <>
      {activeView === "workbench" ? (
        <ProjectControlBoard
          project={project}
          evidence={evidence}
          latestDraft={latestDraft}
          latestCostPlanDraft={latestCostPlanDraft}
          trace={trace}
          costPlanTrace={costPlanTrace}
          workflowError={workflowError}
          costPlanWorkflowError={costPlanWorkflowError}
          isRunningWorkflow={isRunningWorkflow}
          isRunningCostPlan={isRunningCostPlan}
          selectedWorkflowId={selectedWorkflowId}
          onSelectWorkflow={selectWorkflow}
          onRunCreatePmp={() => void runCreatePmp()}
          onRunUpdatePmp={() => void runUpdatePmp()}
          onRunCreateCostPlan={() => void runCreateCostPlan()}
          onRunSortFiles={() => void runSortFiles()}
          onOpenDraft={() => {
            setReviewDraft(null);
            setChatPanelCollapsed(true);
            setActiveView("draft");
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
        />
      ) : null}
      {activeView === "file" ? (
        <WorkspaceFilePanel projectId={project.id} evidence={selectedEvidence} />
      ) : null}
      {activeView === "folder" ? (
        <WorkspaceFolderPanel folder={selectedFolder} evidence={evidence} />
      ) : null}
      {activeView === "draft" && project ? (
        <DraftReviewPanel
          projectId={project.id}
          draft={activeDraft}
          workflowType={activeWorkflowType}
          onRunUpdatePmp={() => void runUpdatePmp()}
          isRunningUpdatePmp={isRunningWorkflow}
          onDraftUpdated={async (draft) => {
            setReviewDraft(draft);
            setLatestDraftsMap((current) => ({
              ...current,
              [draft.workflow_type]: draft,
            }));
            if (draft.workflow_type === "create_cost_plan") {
              setLatestCostPlanDraft(draft);
              setSelectedWorkspacePath(draft.workspace_path);
            } else if (draft.workflow_type.startsWith("consultant_procurement_")) {
              setSelectedWorkspacePath(draft.workspace_path);
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
          }}
        />
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
