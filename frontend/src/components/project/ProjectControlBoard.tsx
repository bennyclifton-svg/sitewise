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
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import {
  workflowStatusBadgeClass,
  type WorkflowStatus,
} from "@/components/project/workflow/workflowStatus";
import {
  buildLifecycleTiles,
  type WorkflowTile,
} from "@/components/project/workflow/workflowTiles";
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
import {
  projectRoleOptions,
  projectStateOptions,
} from "@/lib/project-overlays";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import { cn } from "@/lib/utils";

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
      <RiskFlagChips flags={project.risk_flags} />

      <section className="cockpit-signature-card cockpit-signature-card--bracketed min-w-0 rounded-lg border bg-card shadow-sm">
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
          onProjectUpdated={onProjectUpdated}
        />
      </section>
    </div>
  );
}

function ProjectProfilePanel({
  project,
  onProjectUpdated,
}: {
  project: ProjectDetail;
  onProjectUpdated?: (project: ProjectDetail) => void;
}) {
  const taxonomyQuery = useTaxonomy();
  const [profile, setProfile] = useState<TaxonomyPickerValue>(() =>
    taxonomyValueFromProject(project),
  );
  const [userRole, setUserRole] = useState(project.user_role ?? "");
  const [state, setState] = useState(project.state ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const overlayIssues = [
    ...project.overlay_status.missing,
    ...project.overlay_status.invalid,
  ];

  async function saveProfile() {
    if (saving || !onProjectUpdated) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateProject(project.id, {
        ...compactTaxonomyValue(profile),
        user_role: userRole || null,
        state: state || null,
      });
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
    <div className="grid gap-4">
      {overlayIssues.length ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
          <p className="font-medium">Project overlays are incomplete.</p>
          <p className="mt-1 text-xs">
            Set role, state, class, and work type here so chat, knowledge
            tools, and workflows use the right SiteWise context.
          </p>
          <ul className="mt-2 space-y-1 text-xs">
            {overlayIssues.map((issue) => (
              <li key={`${issue.field}-${issue.reason}`}>
                {issue.field.replace("_", " ")}: {issue.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {saved ? (
        <div className="flex justify-end">
          <Badge variant="secondary">Saved</Badge>
        </div>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2">
        <OverlaySelectField
          id={`project-role-${project.id}`}
          label="Your role"
          value={userRole}
          onChange={setUserRole}
          options={projectRoleOptions}
          placeholder="Select role"
          disabled={saving || !onProjectUpdated}
        />
        <OverlaySelectField
          id={`project-state-${project.id}`}
          label="State"
          value={state}
          onChange={setState}
          options={projectStateOptions.map((item) => ({ value: item, label: item }))}
          placeholder="Select state"
          disabled={saving || !onProjectUpdated}
        />
      </div>
      <TaxonomyPicker
        catalog={taxonomyQuery.data}
        value={profile}
        onChange={setProfile}
        disabled={saving || !onProjectUpdated}
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
      {onProjectUpdated ? (
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
      ) : null}
    </div>
  );
}

function OverlaySelectField({
  id,
  label,
  value,
  options,
  placeholder,
  onChange,
  disabled = false,
}: {
  id: string;
  label: string;
  value: string;
  options: ReadonlyArray<{ value: string; label: string }>;
  placeholder: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        className="h-9 rounded-md border border-input bg-background px-2.5 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function RiskFlagChips({ flags }: { flags: ProjectDetail["risk_flags"] }) {
  if (!flags.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
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
  onProjectUpdated,
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
  onProjectUpdated?: (project: ProjectDetail) => void;
}) {
  const isProjectProfile = tile.id === "project-profile";
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
        {isProjectProfile ? (
          <ProjectProfilePanel
            key={project.id}
            project={project}
            onProjectUpdated={onProjectUpdated}
          />
        ) : isCreatePmp ? (
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
