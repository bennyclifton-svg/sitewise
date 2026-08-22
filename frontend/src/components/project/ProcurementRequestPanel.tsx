import { Download, Play, RefreshCw, Table2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { PdfFileIcon, WordFileIcon } from "@/components/icons/OfficeFileIcons";
import { CopyContentButton } from "@/components/project/CopyContentButton";
import { ProcurementStrategyGrid } from "@/components/project/ProcurementStrategyGrid";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SuggestionField } from "@/components/ui/suggestion-field";
import { api } from "@/lib/api";
import { stripArtifactBlockMarkers } from "@/lib/artifact-markdown";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
import { cn } from "@/lib/utils";
import {
  latestRequest,
  mergeDisciplineOptions,
} from "@/lib/procurement-disciplines";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
  ProcurementRequest,
  ProcurementRequestKind,
  ProcurementStrategyOperation,
  ProcurementStrategyRow,
  ProjectDiscipline,
  ProjectDetail,
  WorkflowRun,
} from "@/lib/types/project";

export type RunnableProcurementRequestKind =
  | "consultant_rfp"
  | "trade_rft"
  | "trade_rfq";

const DraftReviewPanel = lazy(() =>
  import("@/components/project/DraftReviewPanel").then((module) => ({
    default: module.DraftReviewPanel,
  })),
);

function isRunnableKind(
  value: ProcurementRequestKind,
): value is RunnableProcurementRequestKind {
  return (
    value === "consultant_rfp" ||
    value === "trade_rft" ||
    value === "trade_rfq"
  );
}

function artefactLabel(kind: ProcurementRequestKind): string {
  if (kind === "consultant_rfp") return "request for proposal";
  if (kind === "trade_rfq") return "request for quotation";
  return "request for tender";
}

export function ProcurementRequestPanel({
  project,
  error,
  refreshToken,
  renderGate,
  onCreate,
  onUpdate,
  onDraftSelected,
  onDraftUpdated,
  repositoryEvidence = [],
  selectedEvidenceIds,
  onSelectEvidenceIds,
  onTransmittalSessionChange,
  onEditStrategyRowWithAi,
}: {
  project: ProjectDetail;
  /** @deprecated Progress now lives in chat; retained for call-site compatibility. */
  activeRun?: WorkflowRun | null;
  /** @deprecated Progress now lives in chat; retained for call-site compatibility. */
  isRunning?: boolean;
  error: string | null;
  refreshToken: number;
  renderGate: (kind: ProcurementRequestKind) => ReactNode;
  onCreate: (kind: RunnableProcurementRequestKind, targetName: string) => void;
  onUpdate?: (kind: RunnableProcurementRequestKind, targetName: string) => void;
  onCancel?: () => void;
  onDraftSelected?: (draft: DraftArtifactSummary) => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  repositoryEvidence?: EvidencePreview[];
  selectedEvidenceIds?: Set<string>;
  onSelectEvidenceIds?: (evidenceIds: Set<string>) => void;
  onTransmittalSessionChange?: (
    session: { draftId: string; workflowType: string } | null,
  ) => void;
  onEditStrategyRowWithAi?: (row: ProcurementStrategyRow) => void;
}) {
  const [discipline, setDiscipline] = useState("");
  const [disciplines, setDisciplines] = useState<ProjectDiscipline[]>([]);
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [view, setView] = useState<"request" | "strategy">("request");
  const [strategyReady, setStrategyReady] = useState(false);
  const [strategyOpening, setStrategyOpening] = useState(false);
  const [strategySaving, setStrategySaving] = useState(false);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draftExportAction, setDraftExportAction] = useState<"docx" | "pdf" | null>(
    null,
  );
  const [draftExportError, setDraftExportError] = useState<string | null>(null);
  const reportedDraftId = useRef<string | null>(null);
  const knownIds = useRef<Set<string>>(new Set());
  const loadedProjectId = useRef(project.id);
  const strategyQuery = useQuery({
    queryKey: workbenchKeys.procurementStrategy(project.id),
    queryFn: () => api.getProcurementStrategy(project.id),
    enabled: strategyReady && view === "strategy",
  }, queryClient);
  const strategy = strategyQuery.data ?? null;
  const strategyLoading = strategyOpening || (strategyQuery.isFetching && !strategy);

  useEffect(() => {
    let cancelled = false;
    if (loadedProjectId.current !== project.id) {
      loadedProjectId.current = project.id;
      knownIds.current = new Set();
      setStrategyReady(false);
      setView("request");
    }
    void queryClient
      .fetchQuery({
        queryKey: workbenchKeys.procurementRequests(project.id),
        queryFn: () => api.listProcurementRequests(project.id),
      })
      .then((next) => {
        if (cancelled) return;
        const newcomers = next.filter((request) => !knownIds.current.has(request.id));
        knownIds.current = new Set(next.map((request) => request.id));
        const runnable = next.filter((request) => isRunnableKind(request.kind));
        if (newcomers.length) {
          const pick = latestRequest(
            newcomers.filter((request) => isRunnableKind(request.kind)),
          );
          if (pick && isRunnableKind(pick.kind)) {
            setDiscipline(pick.target_name);
          }
        } else {
          setDiscipline((current) => {
            const key = current.trim().toLowerCase();
            if (
              key &&
              next.some(
                (request) => request.target_name.trim().toLowerCase() === key,
              )
            ) {
              return current;
            }
            return latestRequest(runnable)?.target_name ?? current;
          });
        }
        setRequests(next);
        setLoadError(null);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Could not load procurement requests.");
      });
    return () => {
      cancelled = true;
    };
  }, [project.id, refreshToken]);

  useEffect(() => {
    let cancelled = false;
    void queryClient
      .fetchQuery({
        queryKey: workbenchKeys.disciplines(project.id),
        queryFn: () => api.listProjectDisciplines(project.id),
      })
      .then((next) => {
        if (!cancelled) setDisciplines(next);
      })
      .catch(() => {
        if (!cancelled) setDisciplines([]);
      });
    return () => {
      cancelled = true;
    };
  }, [project.id]);

  const selectedRequest = useMemo(() => {
    const key = discipline.trim().toLowerCase();
    if (!key) return null;
    return (
      latestRequest(
        requests.filter(
          (request) =>
            isRunnableKind(request.kind) &&
            request.target_name.trim().toLowerCase() === key,
        ),
      ) ?? null
    );
  }, [discipline, requests]);
  const selectedDiscipline = disciplines.find(
    (item) => item.label.toLowerCase() === discipline.trim().toLowerCase(),
  );
  const createKind =
    selectedRequest && isRunnableKind(selectedRequest.kind)
      ? selectedRequest.kind
      : selectedDiscipline && isRunnableKind(selectedDiscipline.request_kind)
      ? selectedDiscipline.request_kind
      : "trade_rft";
  const activeKind = selectedRequest?.kind ?? createKind;

  useEffect(() => {
    const draft = selectedRequest?.current_draft ?? null;
    if (!draft) {
      reportedDraftId.current = null;
      return;
    }
    if (draft.id === reportedDraftId.current) return;
    reportedDraftId.current = draft.id;
    onDraftSelected?.(draft);
  }, [onDraftSelected, selectedRequest?.current_draft]);

  const createCapability =
    createKind === "consultant_rfp"
      ? project.workflow_capabilities?.capabilities.consultant_procurement
      : project.workflow_capabilities?.capabilities.trade_procurement;
  const updateCapability =
    selectedRequest?.kind === "consultant_rfp"
      ? project.workflow_capabilities?.capabilities.consultant_procurement
      : project.workflow_capabilities?.capabilities.trade_procurement;
  const createSupported = !createCapability || createCapability.status === "supported";
  const updateSupported = !updateCapability || updateCapability.status === "supported";
  const capability = selectedRequest ? updateCapability : createCapability;
  const supported = selectedRequest ? updateSupported : createSupported;

  const disciplineOptions = useMemo(() => {
    const existingTargets = requests
      .filter((request) => isRunnableKind(request.kind))
      .map((request) => request.target_name);
    return mergeDisciplineOptions(
      disciplines.map((item) => item.label),
      [],
      existingTargets,
    );
  }, [disciplines, requests]);
  const disciplineBadges = useMemo(() => {
    const badges: Record<string, string> = {};
    for (const name of disciplineOptions) {
      const match = latestRequest(
        requests.filter(
          (request) =>
            isRunnableKind(request.kind) &&
            request.target_name.trim().toLowerCase() === name.toLowerCase(),
        ),
      );
      if (!match) continue;
      badges[name] = String(match.current_draft?.version ?? match.revision);
    }
    return badges;
  }, [disciplineOptions, requests]);
  const hasGeneratedRequests = requests.some((request) => isRunnableKind(request.kind));

  function submitCreate() {
    const target = discipline.trim();
    if (!target || !createSupported) return;
    setView("request");
    onCreate(createKind, target);
  }

  function submitUpdate() {
    if (!selectedRequest || !updateSupported) return;
    setView("request");
    onUpdate?.(
      isRunnableKind(selectedRequest.kind) ? selectedRequest.kind : createKind,
      selectedRequest.target_name,
    );
  }

  const currentDraft = selectedRequest?.current_draft ?? null;
  const currentArtefactLabel = artefactLabel(activeKind);

  async function downloadDraftExport(format: "docx" | "pdf") {
    if (!currentDraft) return;
    setDraftExportAction(format);
    setDraftExportError(null);
    try {
      const blob = await api.downloadDraftExport(
        project.id,
        currentDraft.id,
        format,
      );
      downloadBlob(
        blob,
        `${safeFilename(currentDraft.title)}_v${String(currentDraft.version).padStart(2, "0")}.${format}`,
      );
    } catch (error) {
      setDraftExportError(
        error instanceof ApiError
          ? error.message
          : `Could not export ${format.toUpperCase()}.`,
      );
    } finally {
      setDraftExportAction(null);
    }
  }

  async function openStrategy() {
    setView("strategy");
    setStrategyError(null);
    if (strategy) return;
    setStrategyOpening(true);
    try {
      const next = await queryClient.fetchQuery({
        queryKey: workbenchKeys.procurementStrategy(project.id),
        queryFn: () => api.ensureProcurementStrategy(project.id),
      });
      queryClient.setQueryData(workbenchKeys.procurementStrategy(project.id), next);
      setStrategyReady(true);
    } catch (nextError) {
      setView("request");
      setStrategyError(
        nextError instanceof ApiError
          ? nextError.message
          : "Could not open Procurement Strategy.",
      );
    } finally {
      setStrategyOpening(false);
    }
  }

  async function applyStrategyOperations(
    operations: ProcurementStrategyOperation[],
  ) {
    if (!strategy) return;
    setStrategySaving(true);
    setStrategyError(null);
    try {
      const next = await api.applyProcurementStrategyOperations(
        project.id,
        strategy.revision,
        operations,
      );
      queryClient.setQueryData(workbenchKeys.procurementStrategy(project.id), next);
    } catch (nextError) {
      setStrategyError(
        nextError instanceof ApiError
          ? nextError.message
          : "Could not save the Procurement Strategy change.",
      );
      if (nextError instanceof ApiError && nextError.status === 409) {
        await queryClient.invalidateQueries({
          queryKey: workbenchKeys.procurementStrategy(project.id),
          exact: true,
        });
        try {
          const current = await api.getProcurementStrategy(project.id);
          queryClient.setQueryData(
            workbenchKeys.procurementStrategy(project.id),
            current,
          );
        } catch {
          // Preserve the last readable snapshot when conflict recovery also fails.
        }
      }
    } finally {
      setStrategySaving(false);
    }
  }

  async function refreshStrategy() {
    if (!strategy) return;
    setStrategySaving(true);
    setStrategyError(null);
    try {
      const next = await api.refreshProcurementStrategy(project.id);
      queryClient.setQueryData(workbenchKeys.procurementStrategy(project.id), next);
    } catch (nextError) {
      setStrategyError(
        nextError instanceof ApiError
          ? nextError.message
          : "Could not refresh the discipline roster.",
      );
    } finally {
      setStrategySaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {error || loadError || strategyError ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error ?? loadError ?? strategyError}
        </p>
      ) : null}

      {view === "request" ? renderGate(activeKind) : null}

      {view === "request" && !supported ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {capability?.reasons.join(" ") || "This request is not supported yet."}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <SuggestionField
            id="procurement-discipline"
            className="w-56"
            value={discipline}
            suggestions={disciplineOptions}
            badges={disciplineBadges}
            aria-label="Discipline"
            placeholder="Architect"
            onChange={setDiscipline}
          />
          <Button onClick={submitCreate} disabled={!discipline.trim() || !createSupported}>
            <Play className="size-4" aria-hidden />
            Generate RFT
          </Button>
          <Button
            variant="outline"
            onClick={submitUpdate}
            disabled={!currentDraft || !updateSupported}
          >
            <RefreshCw className="size-4" aria-hidden />
            Update RFT
          </Button>
          <Button
            type="button"
            variant={view === "strategy" ? "secondary" : "outline"}
            aria-pressed={view === "strategy"}
            disabled={strategyLoading}
            onClick={() => void openStrategy()}
          >
            <Table2 className="size-4" aria-hidden />
            {strategyLoading ? "Opening…" : "Strategy"}
          </Button>
        </div>
        {view === "request" ? <div className="flex flex-wrap items-center gap-1.5">
          {draftExportError ? (
            <span className="self-center text-xs text-destructive" role="alert">
              {draftExportError}
            </span>
          ) : null}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-10 text-muted-foreground hover:text-foreground"
                disabled={!currentDraft || draftExportAction !== null}
                aria-label={`Download ${currentArtefactLabel}`}
                title="Download"
              >
                <Download
                  className={cn(
                    "size-5",
                    draftExportAction !== null && "animate-pulse",
                  )}
                  aria-hidden
                />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[11rem]">
              <DropdownMenuItem
                className="gap-2.5 py-2"
                disabled={draftExportAction !== null}
                onSelect={() => {
                  void downloadDraftExport("docx");
                }}
              >
                <WordFileIcon className="size-6" />
                <span>Word</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2.5 py-2"
                disabled={draftExportAction !== null}
                onSelect={() => {
                  void downloadDraftExport("pdf");
                }}
              >
                <PdfFileIcon className="size-6" />
                <span>PDF</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <CopyContentButton
            loadContent={async () => {
              if (!currentDraft) return "";
              const fullDraft = await api.getProjectDraft(
                project.id,
                currentDraft.id,
              );
              return stripArtifactBlockMarkers(fullDraft.content_markdown);
            }}
            label={`Copy ${currentArtefactLabel}`}
            disabled={!currentDraft}
            size="icon"
            className="size-10"
          />
        </div> : null}
      </div>

      {view === "request" && !hasGeneratedRequests ? (
        <p className="text-sm text-muted-foreground">
          No requests yet. Create the first one above.
        </p>
      ) : null}

      {view === "strategy" && strategy ? (
        <ProcurementStrategyGrid
          strategy={strategy}
          disciplines={disciplines}
          saving={strategySaving}
          onApply={applyStrategyOperations}
          onRefresh={refreshStrategy}
          onEditWithAi={onEditStrategyRowWithAi}
        />
      ) : view === "request" && selectedRequest?.current_draft ? (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
          <DraftReviewPanel
            projectId={project.id}
            draft={selectedRequest.current_draft}
            workflowType={selectedRequest.current_draft.workflow_type}
            projectTitle={project.title}
            embedded
            repositoryEvidence={repositoryEvidence}
            selectedEvidenceIds={selectedEvidenceIds}
            onSelectEvidenceIds={onSelectEvidenceIds}
            onTransmittalSessionChange={onTransmittalSessionChange}
            onDraftUpdated={(draft) => onDraftUpdated?.(draft)}
          />
        </Suspense>
      ) : view === "request" && selectedRequest ? (
        <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
          The current document will appear here when it is ready.
        </p>
      ) : null}
    </div>
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function safeFilename(value: string): string {
  return value.replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "") || "Artefact";
}
