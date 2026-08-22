import { Download, Play, RefreshCw } from "lucide-react";
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
  DEFAULT_CONSULTANT_DISCIPLINES,
  DEFAULT_TRADE_PACKAGES,
  disciplinesFromPmpMarkdown,
  kindForTargetName,
  latestRequest,
  mergeDisciplineOptions,
} from "@/lib/procurement-disciplines";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
  ProcurementRequest,
  ProcurementRequestKind,
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
}) {
  const [discipline, setDiscipline] = useState("");
  const [pmpDisciplines, setPmpDisciplines] = useState<string[]>([]);
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draftExportAction, setDraftExportAction] = useState<"docx" | "pdf" | null>(
    null,
  );
  const [draftExportError, setDraftExportError] = useState<string | null>(null);
  const reportedDraftId = useRef<string | null>(null);
  const knownIds = useRef<Set<string>>(new Set());
  const loadedProjectId = useRef(project.id);

  useEffect(() => {
    let cancelled = false;
    if (loadedProjectId.current !== project.id) {
      loadedProjectId.current = project.id;
      knownIds.current = new Set();
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
    void api
      .getLatestDraft(project.id, "create_pmp")
      .then((draft) => {
        if (cancelled) return;
        setPmpDisciplines(
          draft?.content_markdown
            ? disciplinesFromPmpMarkdown(draft.content_markdown)
            : [],
        );
      })
      .catch(() => {
        if (!cancelled) setPmpDisciplines([]);
      });
    return () => {
      cancelled = true;
    };
  }, [project.id, refreshToken]);

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
  const createKind = kindForTargetName(discipline, pmpDisciplines, requests);
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
      pmpDisciplines,
      [...DEFAULT_CONSULTANT_DISCIPLINES, ...DEFAULT_TRADE_PACKAGES],
      existingTargets,
    );
  }, [pmpDisciplines, requests]);
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
    onCreate(createKind, target);
  }

  function submitUpdate() {
    if (!selectedRequest || !updateSupported) return;
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

  return (
    <div className="space-y-4">
      {error || loadError ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error ?? loadError}
        </p>
      ) : null}

      {renderGate(activeKind)}

      {!supported ? (
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
            Create RFT
          </Button>
          <Button
            variant="outline"
            onClick={submitUpdate}
            disabled={!currentDraft || !updateSupported}
          >
            <RefreshCw className="size-4" aria-hidden />
            Update RFT
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
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

      {hasGeneratedRequests ? null : (
        <p className="text-sm text-muted-foreground">
          No requests yet. Create the first one above.
        </p>
      )}

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
