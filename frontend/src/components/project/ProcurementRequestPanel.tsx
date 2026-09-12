import { ArrowLeft, Download, RefreshCw } from "lucide-react";
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
import { api } from "@/lib/api";
import { stripArtifactBlockMarkers } from "@/lib/artifact-markdown";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
import { cn } from "@/lib/utils";
import { latestRequest } from "@/lib/procurement-disciplines";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
  ProcurementRequest,
  ProcurementRequestKind,
  ProcurementStrategy,
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

function normaliseDisciplineIdentity(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function participantTypeForRequest(
  request: ProcurementRequest,
): ProjectDiscipline["participant_type"] | null {
  if (request.kind === "consultant_rfp") return "consultant";
  if (request.kind === "trade_rft") return "trade";
  if (request.kind === "trade_rfq") return "supplier";
  return null;
}

function disciplineForRequestTarget(
  request: ProcurementRequest,
  disciplines: readonly ProjectDiscipline[],
): ProjectDiscipline | null {
  const target = normaliseDisciplineIdentity(request.target_name);
  const participantType = participantTypeForRequest(request);
  if (!target || !participantType) return null;
  return (
    disciplines.find((item) => {
      if (item.participant_type !== participantType) return false;
      return [item.label, item.workspace_slug].some(
        (value) => normaliseDisciplineIdentity(value) === target,
      );
    }) ?? null
  );
}

function requestTargetLabel(
  request: ProcurementRequest,
  disciplines: readonly ProjectDiscipline[],
): string {
  return disciplineForRequestTarget(request, disciplines)?.label ?? request.target_name.trim();
}

function artefactLabel(kind: ProcurementRequestKind): string {
  if (kind === "consultant_rfp") return "request for proposal";
  if (kind === "trade_rfq") return "request for quotation";
  return "request for tender";
}

function requestTypeLabel(kind: ProcurementRequestKind): "RFP" | "RFT" | "RFQ" {
  if (kind === "consultant_rfp") return "RFP";
  if (kind === "trade_rfq") return "RFQ";
  return "RFT";
}

function requestForStrategyRow(
  row: ProcurementStrategyRow,
  requests: ProcurementRequest[],
  disciplines: ProjectDiscipline[],
): ProcurementRequest | null {
  const compatible = requests.filter(
    (request) => isRunnableKind(request.kind) && request.kind === row.request_kind,
  );
  const directlyLinked = latestRequest(
    compatible.filter((request) => request.strategy_row_id === row.id),
  );
  if (directlyLinked) return directlyLinked;

  const disciplineLinked = row.discipline_code
    ? latestRequest(
        compatible.filter(
          (request) =>
            !request.strategy_row_id &&
            request.discipline_code === row.discipline_code,
        ),
      )
    : null;
  if (disciplineLinked) return disciplineLinked;

  const rowLabel = normaliseDisciplineIdentity(row.discipline_label);
  return (
    latestRequest(
      compatible.filter(
        (request) =>
          !request.strategy_row_id &&
          normaliseDisciplineIdentity(requestTargetLabel(request, disciplines)) ===
            rowLabel,
      ),
    ) ?? null
  );
}

export function ProcurementRequestPanel({
  project,
  error,
  refreshToken,
  openDraftId = null,
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
  onOpenTenderComparison,
}: {
  project: ProjectDetail;
  /** @deprecated Progress now lives in chat; retained for call-site compatibility. */
  activeRun?: WorkflowRun | null;
  /** @deprecated Progress now lives in chat; retained for call-site compatibility. */
  isRunning?: boolean;
  error: string | null;
  refreshToken: number;
  openDraftId?: string | null;
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
  onOpenTenderComparison?: (comparisonId: string) => void;
}) {
  const [disciplines, setDisciplines] = useState<ProjectDiscipline[]>([]);
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [view, setView] = useState<"request" | "strategy">("strategy");
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [dismissedOpenDraftId, setDismissedOpenDraftId] = useState<string | null>(
    null,
  );
  const [strategyRefreshing, setStrategyRefreshing] = useState(false);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [comparingRowId, setComparingRowId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draftExportAction, setDraftExportAction] = useState<"docx" | "pdf" | null>(
    null,
  );
  const [draftExportError, setDraftExportError] = useState<string | null>(null);
  const reportedDraftId = useRef<string | null>(null);
  const confirmedStrategyRef = useRef<ProcurementStrategy | null>(null);
  const strategySaveQueue = useRef(Promise.resolve());
  const pendingStrategyOperationsRef = useRef<
    Array<{ id: string; operations: ProcurementStrategyOperation[] }>
  >([]);
  const [pendingStrategyOperations, setPendingStrategyOperations] = useState<
    Array<{ id: string; operations: ProcurementStrategyOperation[] }>
  >([]);
  const strategyQuery = useQuery({
    queryKey: workbenchKeys.procurementStrategy(project.id),
    queryFn: () => api.ensureProcurementStrategy(project.id),
    structuralSharing: (previous, next) => {
      const current = previous as ProcurementStrategy | undefined;
      const incoming = next as ProcurementStrategy;
      return current && current.revision > incoming.revision ? current : incoming;
    },
  }, queryClient);
  const confirmedStrategy = strategyQuery.data ?? null;
  useEffect(() => {
    if (
      confirmedStrategy &&
      (!confirmedStrategyRef.current ||
        confirmedStrategy.revision >= confirmedStrategyRef.current.revision)
    ) {
      confirmedStrategyRef.current = confirmedStrategy;
    }
  }, [confirmedStrategy]);
  const strategy = useMemo(() => {
    if (!confirmedStrategy) return null;
    return pendingStrategyOperations.reduce(
      (current, pending) =>
        optimisticallyApplyStrategyOperations(current, disciplines, pending.operations),
      confirmedStrategy,
    );
  }, [confirmedStrategy, disciplines, pendingStrategyOperations]);
  const strategyLoading = strategyQuery.isFetching && !strategy;

  useEffect(() => {
    let cancelled = false;
    void queryClient
      .fetchQuery({
        queryKey: workbenchKeys.procurementRequests(project.id),
        queryFn: () => api.listProcurementRequests(project.id),
      })
      .then((next) => {
        if (cancelled) return;
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

  const selectableDisciplines = useMemo(
    () => disciplines.filter((item) => item.picker_visible !== false),
    [disciplines],
  );
  const deepLinkedRequest =
    openDraftId && dismissedOpenDraftId !== openDraftId
      ? requests.find(
          (request) =>
            request.current_draft_artifact_id === openDraftId ||
            request.current_draft?.id === openDraftId,
        ) ?? null
      : null;
  const selectedRequest =
    deepLinkedRequest ??
    requests.find((request) => request.id === selectedRequestId) ??
    null;
  const activeView = deepLinkedRequest ? "request" : view;
  const requestsByRowId = useMemo(() => {
    if (!strategy) return {};
    return Object.fromEntries(
      strategy.rows.map((row) => [
        row.id,
        requestForStrategyRow(row, requests, disciplines) ?? undefined,
      ]),
    );
  }, [disciplines, requests, strategy]);
  const activeKind = selectedRequest?.kind ?? "consultant_rfp";

  useEffect(() => {
    if (activeView !== "request") return;
    const draft = selectedRequest?.current_draft ?? null;
    if (!draft) {
      reportedDraftId.current = null;
      return;
    }
    if (draft.id === reportedDraftId.current) return;
    reportedDraftId.current = draft.id;
    onDraftSelected?.(draft);
  }, [activeView, onDraftSelected, selectedRequest?.current_draft]);

  const updateCapability =
    selectedRequest?.kind === "consultant_rfp"
      ? project.workflow_capabilities?.capabilities.consultant_procurement
      : project.workflow_capabilities?.capabilities.trade_procurement;
  const updateSupported = !updateCapability || updateCapability.status === "supported";
  const supported = !selectedRequest || updateSupported;

  function createRequestForRow(row: ProcurementStrategyRow) {
    if (!isRunnableKind(row.request_kind)) return;
    onCreate(row.request_kind, row.discipline_label);
  }

  function openRequest(request: ProcurementRequest) {
    setSelectedRequestId(request.id);
    setView("request");
  }

  function submitUpdate() {
    if (!selectedRequest || !updateSupported) return;
    onUpdate?.(
      isRunnableKind(selectedRequest.kind) ? selectedRequest.kind : "trade_rft",
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

  async function applyStrategyOperations(
    operations: ProcurementStrategyOperation[],
  ) {
    if (!confirmedStrategy) return;
    const pending = { id: crypto.randomUUID(), operations };
    pendingStrategyOperationsRef.current = [
      ...pendingStrategyOperationsRef.current,
      pending,
    ];
    setPendingStrategyOperations(pendingStrategyOperationsRef.current);
    setStrategyError(null);
    strategySaveQueue.current = strategySaveQueue.current.then(async () => {
      try {
        const saved = await api.applyProcurementStrategyOperations(
          project.id,
          (confirmedStrategyRef.current ?? confirmedStrategy).revision,
          pending.operations,
        );
        confirmedStrategyRef.current = saved;
        queryClient.setQueryData(workbenchKeys.procurementStrategy(project.id), saved);
      } catch (nextError) {
        setStrategyError(
          nextError instanceof ApiError
            ? nextError.message
            : "Could not save the Procurement Strategy change.",
        );
        if (nextError instanceof ApiError && nextError.status === 409) {
          try {
            const current = await api.getProcurementStrategy(project.id);
            confirmedStrategyRef.current = current;
            queryClient.setQueryData(
              workbenchKeys.procurementStrategy(project.id),
              current,
            );
          } catch {
            // Preserve the last readable snapshot when conflict recovery also fails.
          }
        }
      } finally {
        pendingStrategyOperationsRef.current = pendingStrategyOperationsRef.current.filter(
          (item) => item.id !== pending.id,
        );
        setPendingStrategyOperations(pendingStrategyOperationsRef.current);
      }
    });
    await strategySaveQueue.current;
  }

  async function refreshStrategy() {
    if (!strategy) return;
    setStrategyRefreshing(true);
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
      setStrategyRefreshing(false);
    }
  }

  async function compareRow(row: ProcurementStrategyRow) {
    if (comparingRowId) return;
    setComparingRowId(row.id);
    setStrategyError(null);
    try {
      await strategySaveQueue.current;
      const current = confirmedStrategyRef.current?.rows.find((item) => item.id === row.id) ?? row;
      if (!current.candidates.some((candidate) => candidate.submission_files?.length)) {
        setStrategyError("Link at least one quote to a firm using Link quote, then compare firms.");
        return;
      }
      const result = await api.startProcurementReview({ project_id: project.id, row_id: current.id, expected_submission_revision: current.submission_revision ?? 1, rerun: true });
      void strategyQuery.refetch();
      onOpenTenderComparison?.(result.comparison_id);
    } catch (error) {
      setStrategyError(error instanceof ApiError ? error.message : "Could not start the comparison. Try again.");
    } finally { setComparingRowId(null); }
  }

  async function openRecommendation(draftId: string) {
    try {
      const draft = await api.getProjectDraft(project.id, draftId);
      const id = draft.provenance_metadata?.comparison_id;
      if (typeof id === "string") onOpenTenderComparison?.(id);
    } catch { setStrategyError("Could not open the recommendation. Try again."); }
  }

  const strategyLoadError = strategyQuery.error
    ? strategyQuery.error instanceof ApiError
      ? strategyQuery.error.message
      : "Could not open Procurement Strategy."
    : null;

  return (
    <div className="space-y-4">
      {error || loadError || strategyError || strategyLoadError ? (
        <p className="rounded-md border border-[var(--sw-error-border)] bg-[var(--sw-error-bg)] px-3 py-2 text-sm text-destructive">
          {error ?? loadError ?? strategyError ?? strategyLoadError}
        </p>
      ) : null}

      {activeView === "request" ? renderGate(activeKind) : null}

      {activeView === "request" && !supported ? (
        <p className="rounded-md border border-[var(--sw-error-border)] bg-[var(--sw-error-bg)] px-3 py-2 text-sm text-destructive">
          {updateCapability?.reasons.join(" ") || "This request is not supported yet."}
        </p>
      ) : null}

      {activeView === "strategy" ? (
        strategy ? (
          <ProcurementStrategyGrid
            strategy={strategy}
            disciplines={selectableDisciplines}
            requestsByRowId={requestsByRowId}
            saving={false}
            refreshing={strategyRefreshing}
            onApply={applyStrategyOperations}
            onRefresh={refreshStrategy}
            onCreateRequest={createRequestForRow}
            onOpenRequest={openRequest}
            onCompare={(row) => void compareRow(row)}
            comparingRowId={comparingRowId}
            onOpenReview={(draftId) => void openRecommendation(draftId)}
            onOpenComparison={onOpenTenderComparison}
            evidence={repositoryEvidence}
            selectedEvidenceIds={selectedEvidenceIds}
            onEditWithAi={onEditStrategyRowWithAi}
          />
        ) : strategyLoading ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            Opening procurement…
          </p>
        ) : null
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
            <div className="flex min-w-0 items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDismissedOpenDraftId(openDraftId);
                  setView("strategy");
                }}
              >
                <ArrowLeft className="size-4" aria-hidden />
                Procurement
              </Button>
              {selectedRequest ? (
                <span className="truncate text-sm font-medium">
                  {selectedRequest.target_name}
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={submitUpdate}
                disabled={!currentDraft || !updateSupported}
              >
                <RefreshCw className="size-4" aria-hidden />
                Update {requestTypeLabel(activeKind)}
              </Button>
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
            </div>
          </div>

          {selectedRequest?.current_draft ? (
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
          ) : selectedRequest ? (
            <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
              The current document will appear here when it is ready.
            </p>
          ) : (
            <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
              This procurement request is no longer available.
            </p>
          )}
        </>
      )}
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

function optimisticallyApplyStrategyOperations(
  strategy: ProcurementStrategy,
  disciplines: ProjectDiscipline[],
  operations: ProcurementStrategyOperation[],
): ProcurementStrategy {
  let rows = strategy.rows;
  let tendererColumnCount = strategy.tenderer_column_count;

  for (const operation of operations) {
    if (operation.operation === "SET_TENDERER_COLUMN_COUNT") {
      if (operation.tenderer_column_count) {
        tendererColumnCount = operation.tenderer_column_count;
      }
      continue;
    }

    if (operation.operation !== "ADD_ROW") {
      const rowIndex = operation.row_id
        ? rows.findIndex((row) => row.id === operation.row_id)
        : -1;
      if (rowIndex < 0) continue;
      const row = rows[rowIndex];
      let nextRow = row;

      if (operation.operation === "UPDATE_ROW") {
        nextRow = {
          ...row,
          ...(operation.status ? { status: operation.status } : {}),
          ...(operation.notes !== undefined ? { notes: operation.notes } : {}),
          ...(operation.discipline_label !== undefined
            ? { discipline_label: operation.discipline_label }
            : {}),
        };
      } else if (operation.operation === "LOCK_ROW") {
        nextRow = { ...row, locked: true };
      } else if (operation.operation === "UNLOCK_ROW") {
        nextRow = { ...row, locked: false };
      } else if (operation.operation === "DELETE_ROW") {
        rows = rows.filter((item) => item.id !== row.id);
        continue;
      }

      if (nextRow !== row) {
        if (rows === strategy.rows) rows = [...rows];
        rows[rowIndex] = nextRow;
      }
      continue;
    }

    if (!operation.discipline_code) continue;
    if (rows.some((row) => row.discipline_code === operation.discipline_code)) continue;

    const discipline = disciplines.find(
      (item) => item.code === operation.discipline_code,
    );
    if (!discipline) continue;

    if (rows === strategy.rows) rows = [...rows];
    const row: ProcurementStrategyRow = {
      id: `pending:${discipline.code}`,
      discipline_code: discipline.code,
      discipline_label: discipline.label,
      participant_type: discipline.participant_type,
      request_kind: discipline.request_kind,
      status: "not_started",
      notes: "",
      display_order: 0,
      origin: "manual",
      locked: false,
      candidates: [],
      linked_request_ids: [],
      no_longer_required: false,
    };
    const beforeIndex = operation.before_row_id
      ? rows.findIndex((item) => item.id === operation.before_row_id)
      : -1;
    const afterIndex = operation.after_row_id
      ? rows.findIndex((item) => item.id === operation.after_row_id)
      : -1;
    const insertionIndex =
      beforeIndex >= 0 ? beforeIndex : afterIndex >= 0 ? afterIndex + 1 : rows.length;
    rows.splice(insertionIndex, 0, row);
  }

  if (
    rows === strategy.rows &&
    tendererColumnCount === strategy.tenderer_column_count
  ) {
    return strategy;
  }
  return {
    ...strategy,
    tenderer_column_count: tendererColumnCount,
    rows: rows.map((row, index) => ({ ...row, display_order: (index + 1) * 100 })),
  };
}
