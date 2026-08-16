import { Play } from "lucide-react";
import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { SuggestionField } from "@/components/ui/suggestion-field";
import { api } from "@/lib/api";
import {
  compareProcurementRequests,
  DEFAULT_CONSULTANT_DISCIPLINES,
  DEFAULT_TRADE_PACKAGES,
  disciplinesFromPmpMarkdown,
  kindShortLabel,
  latestRequest,
  latestRequestForKind,
  mergeDisciplineOptions,
  requestChipLabel,
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

const KIND_OPTIONS: Array<{
  value: RunnableProcurementRequestKind;
  label: string;
}> = [
  {
    value: "consultant_rfp",
    label: "Consultant",
  },
  {
    value: "trade_rft",
    label: "Trade package",
  },
  {
    value: "trade_rfq",
    label: "Supplier quote",
  },
];

function isRunnableKind(
  value: ProcurementRequestKind,
): value is RunnableProcurementRequestKind {
  return (
    value === "consultant_rfp" ||
    value === "trade_rft" ||
    value === "trade_rfq"
  );
}

export function ProcurementRequestPanel({
  project,
  error,
  refreshToken,
  renderGate,
  onCreate,
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
  const [kind, setKind] = useState<RunnableProcurementRequestKind>("consultant_rfp");
  const [discipline, setDiscipline] = useState("");
  const [pmpDisciplines, setPmpDisciplines] = useState<string[]>([]);
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const reportedDraftId = useRef<string | null>(null);
  const knownIds = useRef<Set<string>>(new Set());
  const loadedProjectId = useRef(project.id);

  useEffect(() => {
    let cancelled = false;
    if (loadedProjectId.current !== project.id) {
      loadedProjectId.current = project.id;
      knownIds.current = new Set();
    }
    void api
      .listProcurementRequests(project.id)
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
            setKind(pick.kind);
            setSelectedRequestId(pick.id);
          }
        } else {
          setSelectedRequestId((current) => {
            if (current && next.some((request) => request.id === current)) {
              return current;
            }
            return latestRequest(runnable)?.id ?? null;
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

  const selectedRequest = useMemo(
    () => requests.find((request) => request.id === selectedRequestId) ?? null,
    [requests, selectedRequestId],
  );
  const visibleRequests = useMemo(
    () =>
      requests
        .filter((request) => request.kind === kind)
        .sort(compareProcurementRequests),
    [kind, requests],
  );

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

  const capability =
    kind === "consultant_rfp"
      ? project.workflow_capabilities?.capabilities.consultant_procurement
      : project.workflow_capabilities?.capabilities.trade_procurement;
  const supported = !capability || capability.status === "supported";

  const disciplineOptions = useMemo(() => {
    const existingForKind = requests
      .filter((request) => request.kind === kind)
      .map((request) => request.target_name);
    if (kind === "consultant_rfp") {
      return mergeDisciplineOptions(
        pmpDisciplines,
        DEFAULT_CONSULTANT_DISCIPLINES,
        existingForKind,
      );
    }
    return mergeDisciplineOptions(
      existingForKind,
      DEFAULT_TRADE_PACKAGES,
      [],
    );
  }, [kind, pmpDisciplines, requests]);

  function selectKind(next: RunnableProcurementRequestKind) {
    setKind(next);
    setDiscipline("");
    setSelectedRequestId(latestRequestForKind(requests, next)?.id ?? null);
  }

  function submit() {
    const target = discipline.trim();
    if (!target || !supported) return;
    onCreate(kind, target);
  }

  return (
    <div className="space-y-4">
      {error || loadError ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error ?? loadError}
        </p>
      ) : null}

      {renderGate(kind)}

      {!supported ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {capability?.reasons.join(" ") || "This request is not supported yet."}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <WorkbenchTabs
          label="Request type"
          value={kind}
          options={KIND_OPTIONS}
          onChange={selectKind}
        />
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <SuggestionField
            id="procurement-discipline"
            className="w-56"
            value={discipline}
            suggestions={disciplineOptions}
            aria-label="Discipline"
            placeholder={
              kind === "consultant_rfp"
                ? "Architect"
                : kind === "trade_rfq"
                  ? "Electrical supplier"
                  : "Electrical services"
            }
            onChange={setDiscipline}
          />
          <Button onClick={submit} disabled={!discipline.trim() || !supported}>
            <Play className="size-4" aria-hidden />
            Create {kindShortLabel(kind)}
          </Button>
        </div>
      </div>

      {visibleRequests.length ? (
        <WorkbenchTabs
          label="Open procurement request"
          value={selectedRequestId ?? ""}
          options={visibleRequests.map((request) => ({
            value: request.id,
            label: requestChipLabel(request),
          }))}
          onChange={setSelectedRequestId}
        />
      ) : (
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

function WorkbenchTabs<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1" role="tablist" aria-label={label}>
      {options.map((option) => (
        <Button
          key={option.value}
          size="sm"
          variant={value === option.value ? "default" : "ghost"}
          role="tab"
          aria-selected={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}
