import { LoaderCircle, Play } from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";

import { WorkflowProgressStrip } from "@/components/project/WorkflowProgressStrip";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type {
  DraftArtifact,
  ProcurementRequest,
  ProcurementRequestKind,
  ProjectDetail,
  WorkflowRun,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { workflowProgressStage, workflowProgressTitle } from "@/lib/workflow-progress";

export type RunnableProcurementRequestKind = Exclude<
  ProcurementRequestKind,
  "contractor_eoi"
>;

const DraftReviewPanel = lazy(() =>
  import("@/components/project/DraftReviewPanel").then((module) => ({
    default: module.DraftReviewPanel,
  })),
);

const KIND_OPTIONS: Array<{ value: RunnableProcurementRequestKind; label: string }> = [
  { value: "consultant_rfp", label: "RFP" },
  { value: "trade_rft", label: "RFT" },
  { value: "trade_rfq", label: "RFQ" },
];

export function ProcurementRequestPanel({
  project,
  activeRun,
  isRunning,
  error,
  refreshToken,
  renderGate,
  onCreate,
  onCancel,
  onDraftUpdated,
}: {
  project: ProjectDetail;
  activeRun: WorkflowRun | null;
  isRunning: boolean;
  error: string | null;
  refreshToken: number;
  renderGate: (kind: ProcurementRequestKind) => ReactNode;
  onCreate: (kind: RunnableProcurementRequestKind, targetName: string) => void;
  onCancel?: () => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
}) {
  const [kind, setKind] = useState<RunnableProcurementRequestKind>("consultant_rfp");
  const [targetName, setTargetName] = useState("");
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api
      .listProcurementRequests(project.id)
      .then((next) => {
        if (cancelled) return;
        setRequests(next);
        setSelectedRequestId((current) =>
          current && next.some((request) => request.id === current)
            ? current
            : next[0]?.id ?? null,
        );
        setLoadError(null);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Could not load procurement requests.");
      });
    return () => {
      cancelled = true;
    };
  }, [project.id, refreshToken]);

  const selectedRequest = useMemo(
    () => requests.find((request) => request.id === selectedRequestId) ?? requests[0] ?? null,
    [requests, selectedRequestId],
  );
  const capability =
    kind === "consultant_rfp"
      ? project.workflow_capabilities?.capabilities.consultant_procurement
      : project.workflow_capabilities?.capabilities.trade_procurement;
  const supported = !capability || capability.status === "supported";
  const trace: WorkflowTraceEvent[] = activeRun
    ? [
        {
          step: "procurement_request",
          status: activeRun.state,
          message: activeRun.error_message ?? "Preparing procurement request.",
          metadata: { workflow_type: activeRun.workflow_type },
        },
      ]
    : [];

  function submit() {
    const target = targetName.trim();
    if (!target || isRunning || !supported) return;
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

      {isRunning ? (
        <WorkflowProgressStrip
          title={workflowProgressTitle("procurement", "create")}
          kind="procurement"
          runId={activeRun?.id ?? "pending-procurement-request"}
          runState={activeRun?.state ?? "queued"}
          progressStage={workflowProgressStage(activeRun?.progress) ?? "queued"}
          onCancel={activeRun ? onCancel : undefined}
        />
      ) : null}

      <div className="grid gap-3 sm:grid-cols-[9rem_minmax(0,1fr)_auto] sm:items-end">
        <div className="grid gap-1.5">
          <Label htmlFor="procurement-kind">Request</Label>
          <select
            id="procurement-kind"
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={kind}
            onChange={(event) =>
              setKind(event.target.value as RunnableProcurementRequestKind)
            }
            disabled={isRunning}
          >
            {KIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="procurement-target">Target</Label>
          <Input
            id="procurement-target"
            value={targetName}
            onChange={(event) => setTargetName(event.target.value)}
            placeholder={kind === "consultant_rfp" ? "Structural engineer" : "Electrical services"}
            disabled={isRunning}
          />
        </div>
        <Button onClick={submit} disabled={!targetName.trim() || isRunning || !supported}>
          {isRunning ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <Play className="size-4" aria-hidden />
          )}
          Create
        </Button>
      </div>

      {requests.length ? (
        <div className="flex flex-wrap gap-2" aria-label="Procurement requests">
          {requests.map((request) => (
            <Button
              key={request.id}
              variant={request.id === selectedRequest?.id ? "secondary" : "outline"}
              size="sm"
              onClick={() => setSelectedRequestId(request.id)}
            >
              {kindLabel(request.kind)}: {request.target_name}
              <Badge variant="outline" className="ml-1.5 text-[0.65rem]">
                {request.status}
              </Badge>
            </Button>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No procurement requests yet.</p>
      )}

      {selectedRequest?.current_draft ? (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading draft...</p>}>
          <DraftReviewPanel
            projectId={project.id}
            draft={selectedRequest.current_draft}
            workflowType={selectedRequest.current_draft.workflow_type}
            embedded
            onDraftUpdated={onDraftUpdated}
          />
        </Suspense>
      ) : selectedRequest ? (
        <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
          The current draft will appear here when it is ready.
        </p>
      ) : null}

      <WorkflowTracePanel trace={trace} isRunning={isRunning} />
    </div>
  );
}

function kindLabel(kind: ProcurementRequestKind): string {
  if (kind === "consultant_rfp") return "RFP";
  if (kind === "contractor_eoi") return "EOI";
  if (kind === "trade_rft") return "RFT";
  return "RFQ";
}
