import {
  Bot,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FileText,
  HandCoins,
  Inbox,
  ListChecks,
  LoaderCircle,
  MessageSquareWarning,
  Play,
  RefreshCw,
  Scale,
  ShieldAlert,
  Stamp,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import {
  workflowDockTileClass,
  workflowSpineNodeClass,
  workflowStatusBadgeClass,
  workflowTileClass,
  type WorkflowStatus,
} from "@/components/project/workflow/workflowStatus";
import type {
  DraftArtifactSummary,
  EvidencePreview,
  ProjectDetail,
  SortFilesResponse,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

type WorkflowTile = {
  id: string;
  label: string;
  folder: string;
  icon: LucideIcon;
  status: WorkflowStatus;
  statusLabel: string;
  description: string;
  implemented: boolean;
};

export function ProjectControlBoard({
  project,
  evidence,
  latestDraft,
  latestCostPlanDraft,
  trace,
  costPlanTrace,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
  selectedWorkflowId,
  onSelectWorkflow,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunSortFiles,
  onOpenDraft,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
}: {
  project: ProjectDetail;
  evidence: EvidencePreview[];
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  trace: WorkflowTraceEvent[];
  costPlanTrace: WorkflowTraceEvent[];
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
  selectedWorkflowId: string;
  onSelectWorkflow: (workflowId: string) => void;
  onRunCreatePmp: () => void;
  onRunUpdatePmp: () => void;
  onRunCreateCostPlan: () => void;
  onRunSortFiles: () => void;
  onOpenDraft: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
}) {
  const lifecycle = buildLifecycleTiles({
    project,
    latestDraft,
    latestCostPlanDraft,
    workflowError,
    costPlanWorkflowError,
    isRunningWorkflow,
    isRunningCostPlan,
  });
  const recurring = buildRecurringTiles({
    inboxCount,
    project,
    sortFilesDraft,
    sortFilesError,
    isRunningSortFiles,
  });
  const selectedTile =
    lifecycle.find((tile) => tile.id === selectedWorkflowId) ??
    recurring.find((tile) => tile.id === selectedWorkflowId) ??
    lifecycle[0];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 lg:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="cockpit-eyebrow">Project cockpit</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{project.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            SiteWise lifecycle, evidence, workflow trace, and draft review.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-sm sm:grid-cols-4">
          <Metric label="Evidence" value={String(evidence.length)} />
          <Metric label="Gate" value={project.overlay_status.ready ? "Ready" : "Blocked"} />
          <Metric label="PMP" value={latestDraft ? `v${latestDraft.version}` : "None"} />
          <Metric label="Cost" value={latestCostPlanDraft ? `v${latestCostPlanDraft.version}` : "None"} />
        </div>
      </header>

      <section className="cockpit-signature-card cockpit-signature-card--bracketed rounded-lg border bg-card shadow-sm">
        <header className="border-b px-4 py-3">
          <p className="cockpit-zone-title">Lifecycle</p>
        </header>
        <LifecycleSpine
          tiles={lifecycle}
          selectedId={selectedTile.id}
          onSelect={onSelectWorkflow}
        />
        <div className="grid gap-2 p-3 md:grid-cols-3 xl:grid-cols-6">
          {lifecycle.map((tile) => (
            <WorkflowButton
              key={tile.id}
              tile={tile}
              selected={selectedTile.id === tile.id}
              onSelect={() => onSelectWorkflow(tile.id)}
            />
          ))}
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <WorkflowDetail
          tile={selectedTile}
          project={project}
          evidenceCount={evidence.length}
          latestDraft={latestDraft}
          latestCostPlanDraft={latestCostPlanDraft}
          trace={trace}
          costPlanTrace={costPlanTrace}
          workflowError={workflowError}
          costPlanWorkflowError={costPlanWorkflowError}
          isRunningWorkflow={isRunningWorkflow}
          isRunningCostPlan={isRunningCostPlan}
          onRunCreatePmp={onRunCreatePmp}
          onRunUpdatePmp={onRunUpdatePmp}
          onRunCreateCostPlan={onRunCreateCostPlan}
          onRunSortFiles={onRunSortFiles}
          onOpenDraft={onOpenDraft}
          onOpenTenderComparison={onOpenTenderComparison}
          inboxCount={inboxCount}
          sortFilesResult={sortFilesResult}
          sortFilesDraft={sortFilesDraft}
          sortFilesError={sortFilesError}
          isRunningSortFiles={isRunningSortFiles}
        />

        <section className="cockpit-signature-card rounded-lg border bg-card shadow-sm">
          <header className="border-b px-4 py-3">
            <p className="cockpit-zone-title">Always on</p>
          </header>
          <div className="space-y-2 p-3">
            {recurring.map((tile) => (
              <WorkflowDockButton
                key={tile.id}
                tile={tile}
                selected={selectedTile.id === tile.id}
                onSelect={() => onSelectWorkflow(tile.id)}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function WorkflowDetail({
  tile,
  project,
  evidenceCount,
  latestDraft,
  latestCostPlanDraft,
  trace,
  costPlanTrace,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunSortFiles,
  onOpenDraft,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
}: {
  tile: WorkflowTile;
  project: ProjectDetail;
  evidenceCount: number;
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  trace: WorkflowTraceEvent[];
  costPlanTrace: WorkflowTraceEvent[];
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
  onRunCreatePmp: () => void;
  onRunUpdatePmp: () => void;
  onRunCreateCostPlan: () => void;
  onRunSortFiles: () => void;
  onOpenDraft: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
}) {
  const Icon = tile.icon;
  const isCreatePmp = tile.id === "create-pmp";
  const isCostPlan = tile.id === "cost-plan";
  const isDocumentIntake = tile.id === "document-intake";
  const isProcurement = tile.id === "procurement";
  const activeTrace = isDocumentIntake
    ? (sortFilesResult?.trace ?? [])
    : isCostPlan
      ? costPlanTrace
      : trace;
  const activeRunning = isDocumentIntake
    ? isRunningSortFiles
    : isCostPlan
      ? isRunningCostPlan
      : isRunningWorkflow;
  const activeError = isCostPlan ? costPlanWorkflowError : workflowError;
  const activeDraft = isCostPlan ? latestCostPlanDraft : latestDraft;

  return (
    <section className="cockpit-signature-card cockpit-signature-card--bracketed min-w-0 rounded-lg border bg-card shadow-sm">
      <header className="border-b p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted/80">
              <Icon className="size-5 text-muted-foreground" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="cockpit-eyebrow">{tile.folder}</p>
              <h2 className="text-xl font-semibold tracking-tight">{tile.label}</h2>
              <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
                {tile.description}
              </p>
            </div>
          </div>
          <Badge variant="outline" className={workflowStatusBadgeClass(tile.status)}>
            {tile.statusLabel}
          </Badge>
        </div>
      </header>

      <div className="space-y-4 p-4">
        {isCreatePmp ? (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <ReadinessItem
                icon={project.overlay_status.ready ? CheckCircle2 : ShieldAlert}
                label="Overlay gate"
                value={project.overlay_status.ready ? "Ready" : "Blocked"}
                attention={!project.overlay_status.ready}
              />
              <ReadinessItem
                icon={FileText}
                label="Evidence"
                value={`${evidenceCount} indexed`}
                attention={evidenceCount === 0}
              />
              <ReadinessItem
                icon={latestDraft ? CheckCircle2 : ClipboardList}
                label="Latest draft"
                value={latestDraft ? `v${latestDraft.version}` : "None"}
              />
            </div>

            {workflowError ? (
              <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {workflowError}
              </p>
            ) : null}

            {!project.overlay_status.ready ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <p className="font-medium">Create PMP is blocked by missing overlays.</p>
                <ul className="mt-2 space-y-1 text-xs">
                  {[...project.overlay_status.missing, ...project.overlay_status.invalid].map(
                    (issue) => (
                      <li key={`${issue.field}-${issue.reason}`}>
                        {issue.field}: {issue.reason}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button onClick={onRunCreatePmp} disabled={isRunningWorkflow}>
                {isRunningWorkflow ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Play className="size-4" aria-hidden />
                )}
                {isRunningWorkflow ? "Running" : "Create PMP"}
              </Button>
              <Button
                variant="outline"
                onClick={onRunUpdatePmp}
                disabled={isRunningWorkflow || !latestDraft}
              >
                {isRunningWorkflow ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <RefreshCw className="size-4" aria-hidden />
                )}
                Update PMP
              </Button>
              <Button variant="secondary" onClick={onOpenDraft} disabled={!latestDraft}>
                <Bot className="size-4" aria-hidden />
                Review draft
              </Button>
            </div>

            <WorkflowTracePanel trace={activeTrace} isRunning={activeRunning} />
          </>
        ) : isCostPlan ? (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <ReadinessItem
                icon={project.overlay_status.ready ? CheckCircle2 : ShieldAlert}
                label="Overlay gate"
                value={project.overlay_status.ready ? "Ready" : "Blocked"}
                attention={!project.overlay_status.ready}
              />
              <ReadinessItem
                icon={HandCoins}
                label="Cost evidence"
                value={`${evidenceCount} indexed`}
                attention={evidenceCount === 0}
              />
              <ReadinessItem
                icon={activeDraft ? CheckCircle2 : ClipboardList}
                label="Latest draft"
                value={activeDraft ? `v${activeDraft.version}` : "None"}
              />
            </div>

            {activeError ? (
              <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {activeError}
              </p>
            ) : null}

            {!project.overlay_status.ready ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <p className="font-medium">Create Cost Plan is blocked by missing overlays.</p>
                <ul className="mt-2 space-y-1 text-xs">
                  {[...project.overlay_status.missing, ...project.overlay_status.invalid].map(
                    (issue) => (
                      <li key={`${issue.field}-${issue.reason}`}>
                        {issue.field}: {issue.reason}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button onClick={onRunCreateCostPlan} disabled={isRunningCostPlan}>
                {isRunningCostPlan ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Play className="size-4" aria-hidden />
                )}
                {isRunningCostPlan ? "Running" : "Create cost plan"}
              </Button>
              <Button variant="secondary" onClick={onOpenDraft} disabled={!activeDraft}>
                <Bot className="size-4" aria-hidden />
                Review draft
              </Button>
            </div>

            <WorkflowTracePanel trace={activeTrace} isRunning={activeRunning} />
          </>
        ) : isDocumentIntake ? (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <ReadinessItem
                icon={project.overlay_status.ready ? CheckCircle2 : ShieldAlert}
                label="Overlay gate"
                value={project.overlay_status.ready ? "Ready" : "Blocked"}
                attention={!project.overlay_status.ready}
              />
              <ReadinessItem
                icon={Inbox}
                label="Inbox files"
                value={inboxCount ? `${inboxCount} waiting` : "Empty"}
                attention={inboxCount === 0}
              />
              <ReadinessItem
                icon={sortFilesDraft ? CheckCircle2 : ClipboardList}
                label="Latest manifest"
                value={sortFilesDraft ? `v${sortFilesDraft.version}` : "None"}
              />
            </div>

            {sortFilesError ? (
              <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {sortFilesError}
              </p>
            ) : null}

            {!project.overlay_status.ready ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <p className="font-medium">Sort Files is blocked by missing overlays.</p>
                <ul className="mt-2 space-y-1 text-xs">
                  {[...project.overlay_status.missing, ...project.overlay_status.invalid].map(
                    (issue) => (
                      <li key={`${issue.field}-${issue.reason}`}>
                        {issue.field}: {issue.reason}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={onRunSortFiles}
                disabled={
                  isRunningSortFiles || !project.overlay_status.ready || inboxCount === 0
                }
              >
                {isRunningSortFiles ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Play className="size-4" aria-hidden />
                )}
                {isRunningSortFiles ? "Running" : "Run Sort Files"}
              </Button>
            </div>

            <SortFilesResultPanel
              summary={sortFilesResult?.summary ?? null}
              rows={sortFilesResult?.rows ?? []}
            />

            <WorkflowTracePanel trace={activeTrace} isRunning={activeRunning} />
          </>
        ) : isProcurement ? (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <ReadinessItem
                icon={BriefcaseBusiness}
                label="Workflow"
                value="Tender comparison"
              />
              <ReadinessItem
                icon={FileText}
                label="Evidence"
                value={`${evidenceCount} indexed`}
                attention={evidenceCount === 0}
              />
              <ReadinessItem
                icon={ClipboardList}
                label="QA"
                value="Review gated"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={onOpenTenderComparison}>
                <Play className="size-4" aria-hidden />
                Run Tender Comparison
              </Button>
            </div>
          </>
        ) : (
          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            {tile.implemented
              ? "This workflow is available in the cockpit."
              : "This workflow is visible in the cockpit roadmap and is not available yet."}
          </div>
        )}
      </div>
    </section>
  );
}

function LifecycleSpine({
  tiles,
  selectedId,
  onSelect,
}: {
  tiles: WorkflowTile[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="cockpit-lifecycle-spine border-b px-2" role="presentation">
      {tiles.map((tile) => {
        const selected = tile.id === selectedId;
        return (
          <div key={tile.id} className="cockpit-spine-segment">
            <button
              type="button"
              className={workflowSpineNodeClass(tile.status, selected)}
              title={`${tile.label}: ${tile.statusLabel}`}
              onClick={() => onSelect(tile.id)}
            >
              <span className="size-1.5 rounded-full bg-current" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function WorkflowButton({
  tile,
  selected,
  onSelect,
}: {
  tile: WorkflowTile;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = tile.icon;
  return (
    <button
      type="button"
      className={workflowTileClass(selected, tile.status)}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <Badge variant="outline" className={workflowStatusBadgeClass(tile.status)}>
          {tile.statusLabel}
        </Badge>
      </div>
      <p className="mt-3 font-medium leading-tight">{tile.label}</p>
      <p className="mt-1 text-xs text-muted-foreground">{tile.folder}</p>
    </button>
  );
}

function WorkflowDockButton({
  tile,
  selected,
  onSelect,
}: {
  tile: WorkflowTile;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = tile.icon;
  return (
    <button type="button" className={workflowDockTileClass(selected)} onClick={onSelect}>
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <span className="min-w-0 flex-1 truncate font-medium">{tile.label}</span>
      <Badge variant="outline" className={cn("shrink-0", workflowStatusBadgeClass(tile.status))}>
        {tile.statusLabel}
      </Badge>
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-24 rounded-md border bg-background px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}

function ReadinessItem({
  icon: Icon,
  label,
  value,
  attention = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  attention?: boolean;
}) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className={cn("size-4", attention && "text-destructive")} aria-hidden />
        {label}
      </div>
      <p className="mt-2 font-medium">{value}</p>
    </div>
  );
}

function buildLifecycleTiles({
  project,
  latestDraft,
  latestCostPlanDraft,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
}): WorkflowTile[] {
  const createPmpStatus = getCreatePmpStatus({
    project,
    latestDraft,
    workflowError,
    isRunningWorkflow,
  });
  const costPlanStatus = getCreateCostPlanStatus({
    project,
    latestDraft: latestCostPlanDraft,
    workflowError: costPlanWorkflowError,
    isRunningWorkflow: isRunningCostPlan,
  });

  return [
    {
      id: "create-pmp",
      label: "Brief / PMP",
      folder: "00-brief-pmp",
      icon: FileText,
      status: createPmpStatus.status,
      statusLabel: createPmpStatus.label,
      description:
        "Create and review the project management plan from active project evidence and SiteWise knowledge.",
      implemented: true,
    },
    {
      id: "cost-plan",
      label: "Cost",
      folder: "01-cost",
      icon: HandCoins,
      status: costPlanStatus.status,
      statusLabel: costPlanStatus.label,
      description:
        "Create and review the project cost plan from cost evidence, claims, and SiteWise cost doctrine.",
      implemented: true,
    },
    {
      id: "design",
      label: "Design",
      folder: "02-consultant / 03-design",
      icon: Stamp,
      status: "unavailable",
      statusLabel: "Soon",
      description: "Design and consultant coordination workflow placeholder.",
      implemented: false,
    },
    {
      id: "procurement",
      label: "Procurement",
      folder: "05-procurement",
      icon: BriefcaseBusiness,
      status: "ready",
      statusLabel: "Ready",
      description:
        "Create tender comparisons, review QA, inspect the matrix, and approve reports.",
      implemented: true,
    },
    {
      id: "delivery",
      label: "Delivery",
      folder: "07-construction",
      icon: ClipboardList,
      status: "unavailable",
      statusLabel: "Soon",
      description: "Delivery workflow placeholder.",
      implemented: false,
    },
    {
      id: "handover",
      label: "Handover",
      folder: "09-handover-dlp",
      icon: CalendarDays,
      status: "unavailable",
      statusLabel: "Soon",
      description: "Handover workflow placeholder.",
      implemented: false,
    },
  ];
}

function buildRecurringTiles({
  inboxCount,
  project,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
}: {
  inboxCount: number;
  project: ProjectDetail;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
}): WorkflowTile[] {
  const intakeStatus = getDocumentIntakeStatus({
    project,
    inboxCount,
    sortFilesDraft,
    sortFilesError,
    isRunningSortFiles,
  });

  return [
    {
      id: "document-intake",
      label: "Document Intake",
      folder: "_inbox",
      icon: Inbox,
      status: intakeStatus.status,
      statusLabel: intakeStatus.label,
      description:
        "Upload to the inbox, then run Sort Files to classify and file documents into lifecycle folders.",
      implemented: true,
    },
    {
      id: "risk-register",
      label: "Risk Register",
      folder: "07-construction",
      icon: MessageSquareWarning,
      status: "unavailable",
      statusLabel: "Soon",
      description: "Risk register workflow placeholder.",
      implemented: false,
    },
    {
      id: "rfis",
      label: "RFIs",
      folder: "03-design",
      icon: ListChecks,
      status: "unavailable",
      statusLabel: "Soon",
      description: "RFI workflow placeholder.",
      implemented: false,
    },
    {
      id: "variations",
      label: "Variations / EOT",
      folder: "07-construction",
      icon: Scale,
      status: "unavailable",
      statusLabel: "Soon",
      description: "Variation and extension-of-time workflow placeholder.",
      implemented: false,
    },
  ];
}

function getDocumentIntakeStatus({
  project,
  inboxCount,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
}: {
  project: ProjectDetail;
  inboxCount: number;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunningSortFiles) return { status: "running", label: "Running" };
  if (sortFilesError) return { status: "failed", label: "Failed" };
  if (!project.overlay_status.ready) return { status: "blocked", label: "Blocked" };
  if (inboxCount > 0) return { status: "ready", label: `${inboxCount} in inbox` };
  if (sortFilesDraft) return { status: "draft", label: `Manifest v${sortFilesDraft.version}` };
  return { status: "ready", label: "Empty" };
}

function getCreatePmpStatus({
  project,
  latestDraft,
  workflowError,
  isRunningWorkflow,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  isRunningWorkflow: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunningWorkflow) return { status: "running", label: "Running" };
  if (workflowError) return { status: "failed", label: "Failed" };
  if (!project.overlay_status.ready) return { status: "blocked", label: "Blocked" };
  if (latestDraft) return { status: "draft", label: `Draft v${latestDraft.version}` };
  return { status: "ready", label: "Ready" };
}

function getCreateCostPlanStatus({
  project,
  latestDraft,
  workflowError,
  isRunningWorkflow,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  isRunningWorkflow: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunningWorkflow) return { status: "running", label: "Running" };
  if (workflowError) return { status: "failed", label: "Failed" };
  if (!project.overlay_status.ready) return { status: "blocked", label: "Blocked" };
  if (latestDraft) return { status: "draft", label: `Draft v${latestDraft.version}` };
  return { status: "ready", label: "Ready" };
}
