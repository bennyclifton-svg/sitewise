import {
  Bot,
  BriefcaseBusiness,
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
  Save,
  Scale,
  Settings2,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import {
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
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import {
  compactTaxonomyValue,
  taxonomyValueFromProject,
} from "@/lib/project-taxonomy";
import { useTaxonomy } from "@/lib/queries/taxonomy";
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
  onProjectUpdated,
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
  onProjectUpdated?: (project: ProjectDetail) => void;
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
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{project.title}</h1>
        <RiskFlagChips flags={project.risk_flags} />
      </header>

      {onProjectUpdated ? (
        <ProjectProfileSection
          key={project.id}
          project={project}
          onProjectUpdated={onProjectUpdated}
        />
      ) : null}

      <section className="cockpit-signature-card cockpit-signature-card--bracketed min-w-0 rounded-lg border bg-card shadow-sm">
        <div className="grid gap-2 p-3 md:grid-cols-3">
          {lifecycle.map((tile) => (
            <WorkflowButton
              key={tile.id}
              tile={tile}
              selected={selectedTile.id === tile.id}
              onSelect={() => onSelectWorkflow(tile.id)}
            />
          ))}
        </div>

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
      </section>
    </div>
  );
}

function ProjectProfileSection({
  project,
  onProjectUpdated,
}: {
  project: ProjectDetail;
  onProjectUpdated: (project: ProjectDetail) => void;
}) {
  const taxonomyQuery = useTaxonomy();
  const [profile, setProfile] = useState<TaxonomyPickerValue>(() =>
    taxonomyValueFromProject(project),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function saveProfile() {
    if (saving) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateProject(
        project.id,
        compactTaxonomyValue(profile),
      );
      onProjectUpdated(updated);
      setSaved(true);
    } catch (saveError) {
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : "Project profile could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border bg-card shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Settings2 className="size-4 text-muted-foreground" aria-hidden />
          <h2 className="text-base font-semibold">Project profile</h2>
        </div>
        {saved ? <Badge variant="secondary">Saved</Badge> : null}
      </header>
      <div className="grid gap-4 p-4">
        <TaxonomyPicker
          catalog={taxonomyQuery.data}
          value={profile}
          onChange={setProfile}
          disabled={saving}
          idPrefix={`project-profile-${project.id}`}
        />
        {taxonomyQuery.error ? (
          <p className="text-sm text-destructive" role="alert">
            Project profile options could not load.
          </p>
        ) : null}
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end">
          <Button
            type="button"
            onClick={() => void saveProfile()}
            disabled={saving || !taxonomyQuery.data}
          >
            {saving ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Save className="size-4" aria-hidden />
            )}
            {saving ? "Saving" : "Save profile"}
          </Button>
        </div>
      </div>
    </section>
  );
}

function RiskFlagChips({ flags }: { flags: ProjectDetail["risk_flags"] }) {
  if (!flags.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {flags.map((flag) => (
        <Badge
          key={flag.value}
          variant="outline"
          title={flag.description}
          className={riskFlagClass(flag.severity)}
        >
          {flag.title}
        </Badge>
      ))}
    </div>
  );
}

function riskFlagClass(severity: string): string {
  if (severity === "critical") {
    return "border-destructive/40 bg-destructive/10 text-destructive";
  }
  if (severity === "warning") {
    return "border-amber-300 bg-amber-50 text-amber-900";
  }
  return "border-sky-300 bg-sky-50 text-sky-900";
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
    <div className="min-w-0">
      <header className="border-t border-b p-4">
        <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
          {tile.description}
        </p>
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
                trailing={draftReadinessTrailing(latestDraft, tile.status, tile.statusLabel)}
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
                trailing={draftReadinessTrailing(activeDraft, tile.status, tile.statusLabel)}
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
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <p className="mt-3 text-[1.2rem] font-medium leading-tight">{tile.label}</p>
    </button>
  );
}

function ReadinessItem({
  icon: Icon,
  label,
  value,
  trailing,
  attention = false,
}: {
  icon: LucideIcon;
  label: string;
  value?: string;
  trailing?: ReactNode;
  attention?: boolean;
}) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className={cn("size-4", attention && "text-destructive")} aria-hidden />
        {label}
      </div>
      <div className={cn("mt-2 flex items-center", trailing ? "justify-end" : "")}>
        {trailing ?? <p className="font-medium">{value}</p>}
      </div>
    </div>
  );
}

function draftReadinessTrailing(
  draft: DraftArtifactSummary | null,
  status: WorkflowStatus,
  statusLabel: string,
) {
  if (!draft) {
    return <span className="font-medium">None</span>;
  }

  return (
    <Badge variant="outline" className={workflowStatusBadgeClass(status)}>
      {statusLabel}
    </Badge>
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
      label: "Project Plan",
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
      label: "Cost Plan",
      folder: "01-cost",
      icon: HandCoins,
      status: costPlanStatus.status,
      statusLabel: costPlanStatus.label,
      description:
        "Create and review the project cost plan from cost evidence, claims, and SiteWise cost doctrine.",
      implemented: true,
    },
    {
      id: "procurement",
      label: "Tender Comparison",
      folder: "05-procurement",
      icon: BriefcaseBusiness,
      status: "ready",
      statusLabel: "Ready",
      description:
        "Create tender comparisons, review QA, inspect the matrix, and approve reports.",
      implemented: true,
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
