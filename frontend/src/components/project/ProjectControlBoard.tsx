import {
  Bot,
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
  Square,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

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
  OverlayIssue,
  ProjectDetail,
  ProjectNextAction,
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
  nextActions = [],
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
  onRunRefreshCostPlan,
  onRunSortFiles,
  onCancelWorkflow,
  onCancelCostPlan,
  onCancelSortFiles,
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
  nextActions?: ProjectNextAction[];
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
  onSelectWorkflow?: (workflowId: string) => void;
  onRunCreatePmp: () => void;
  onRunUpdatePmp: () => void;
  onRunCreateCostPlan: () => void;
  onRunRefreshCostPlan?: () => void;
  onRunSortFiles: () => void;
  onCancelWorkflow?: () => void;
  onCancelCostPlan?: () => void;
  onCancelSortFiles?: () => void;
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

      {nextActions.length ? <ProjectNextActions actions={nextActions} /> : null}

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
          onSelectWorkflow={onSelectWorkflow}
          onRunCreatePmp={onRunCreatePmp}
          onRunUpdatePmp={onRunUpdatePmp}
          onRunCreateCostPlan={onRunCreateCostPlan}
          onRunRefreshCostPlan={onRunRefreshCostPlan}
          onRunSortFiles={onRunSortFiles}
          onCancelWorkflow={onCancelWorkflow}
          onCancelCostPlan={onCancelCostPlan}
          onCancelSortFiles={onCancelSortFiles}
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

function ProjectNextActions({ actions }: { actions: ProjectNextAction[] }) {
  return (
    <section aria-labelledby="project-next-actions" className="rounded-lg border bg-card p-4">
      <h2 id="project-next-actions" className="font-semibold">
        Next actions
      </h2>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {actions.map((action) => (
          <article key={`${action.code}-${action.blocking_fact}`} className="rounded-md border p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{action.label}</p>
                <p className="mt-1 text-xs text-muted-foreground">{action.reason}</p>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link to={action.route}>Open</Link>
              </Button>
            </div>
            <p className="mt-2 font-mono text-[11px] text-muted-foreground">
              {action.tool} · {action.blocking_fact}
            </p>
          </article>
        ))}
      </div>
    </section>
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
  const serverForm = profileFormFromProject(project);
  const serverRevision = project.profile_revision ?? 1;
  const [draft, setDraft] = useState<ProfileFormValue | null>(null);
  const [baseForm, setBaseForm] = useState<ProfileFormValue | null>(null);
  const [editingRevision, setEditingRevision] = useState<number | null>(null);
  const [conflictRevision, setConflictRevision] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const overlayIssues = [
    ...project.overlay_status.missing,
    ...project.overlay_status.invalid,
  ];
  const form = draft ?? serverForm;

  useEffect(() => {
    if (
      draft &&
      editingRevision !== null &&
      serverRevision > editingRevision &&
      conflictRevision !== serverRevision
    ) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setConflictRevision(serverRevision);
    }
  }, [conflictRevision, draft, editingRevision, serverRevision]);

  function updateDraft(next: ProfileFormValue) {
    const baseline = baseForm ?? serverForm;
    const changedFields = changedProfileFormFields(next, baseline);
    setSaved(false);
    setError(null);
    if (changedFields.length === 0) {
      setDraft(null);
      setBaseForm(null);
      setEditingRevision(null);
      setConflictRevision(null);
      return;
    }
    if (!baseForm) setBaseForm(baseline);
    if (editingRevision === null) setEditingRevision(serverRevision);
    setDraft(next);
  }

  function reloadLatestProfile() {
    setDraft(null);
    setBaseForm(null);
    setEditingRevision(null);
    setConflictRevision(null);
    setError(null);
    setSaved(false);
  }

  function keepEditing() {
    if (!draft || !baseForm) return;
    const changedFields = changedProfileFormFields(draft, baseForm);
    const rebased = rebaseProfileForm(serverForm, draft, changedFields);
    if (changedProfileFormFields(rebased, serverForm).length === 0) {
      reloadLatestProfile();
      return;
    }
    setDraft(rebased);
    setBaseForm(serverForm);
    setEditingRevision(serverRevision);
    setConflictRevision(null);
  }

  async function saveProfile() {
    if (saving || !onProjectUpdated) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateProject(project.id, {
        expected_revision: editingRevision ?? serverRevision,
        ...compactTaxonomyValue(form.profile),
        user_role: form.userRole || null,
        state: form.state || null,
      });
      onProjectUpdated({
        ...project,
        building_class: updated.profile.building_class,
        work_type: updated.profile.work_type,
        user_role: updated.profile.user_role,
        state: updated.profile.state,
        profile_revision: updated.new_revision,
        metadata: {
          ...(project.metadata ?? {}),
          taxonomy: {
            ...(project.metadata?.taxonomy ?? {}),
            subclasses: updated.profile.subclasses,
            scale: updated.profile.scale,
            complexity: updated.profile.complexity,
            work_scope: updated.profile.work_scope,
          },
        },
        overlay_status: updated.overlay_status,
        risk_flags: updated.risk_flags,
      });
      setDraft(null);
      setBaseForm(null);
      setEditingRevision(null);
      setConflictRevision(null);
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
      {conflictRevision !== null ? (
        <div
          className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"
          role="alert"
        >
          <p className="font-medium">Project profile changed elsewhere.</p>
          <p className="mt-1 text-xs">
            Revision {conflictRevision} arrived while you had unsaved edits.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" onClick={reloadLatestProfile}>
              Reload latest
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={keepEditing}>
              Keep editing
            </Button>
          </div>
        </div>
      ) : null}
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
          value={form.userRole}
          onChange={(userRole) => updateDraft({ ...form, userRole })}
          options={projectRoleOptions}
          placeholder="Select role"
          disabled={saving || !onProjectUpdated}
        />
        <OverlaySelectField
          id={`project-state-${project.id}`}
          label="State"
          value={form.state}
          onChange={(state) => updateDraft({ ...form, state })}
          options={projectStateOptions.map((item) => ({ value: item, label: item }))}
          placeholder="Select state"
          disabled={saving || !onProjectUpdated}
        />
      </div>
      <TaxonomyPicker
        catalog={taxonomyQuery.data}
        value={form.profile}
        onChange={(profile) => updateDraft({ ...form, profile })}
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
            disabled={saving || !taxonomyQuery.data || conflictRevision !== null}
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

type ProfileFormValue = {
  profile: TaxonomyPickerValue;
  userRole: string;
  state: string;
};

type ProfileFormField =
  | keyof TaxonomyPickerValue
  | "user_role"
  | "state";

const PROFILE_FORM_FIELDS: readonly ProfileFormField[] = [
  "building_class",
  "work_type",
  "subclasses",
  "scale",
  "complexity",
  "work_scope",
  "user_role",
  "state",
];

function profileFormFromProject(project: ProjectDetail): ProfileFormValue {
  return {
    profile: taxonomyValueFromProject(project),
    userRole: project.user_role ?? "",
    state: project.state ?? "",
  };
}

function changedProfileFormFields(
  current: ProfileFormValue,
  baseline: ProfileFormValue,
): ProfileFormField[] {
  return PROFILE_FORM_FIELDS.filter(
    (field) => !profileFormFieldEqual(current, baseline, field),
  );
}

function profileFormFieldEqual(
  left: ProfileFormValue,
  right: ProfileFormValue,
  field: ProfileFormField,
) {
  return JSON.stringify(profileFormField(left, field)) ===
    JSON.stringify(profileFormField(right, field));
}

function profileFormField(form: ProfileFormValue, field: ProfileFormField) {
  if (field === "user_role") return form.userRole;
  if (field === "state") return form.state;
  return form.profile[field];
}

function rebaseProfileForm(
  latest: ProfileFormValue,
  draft: ProfileFormValue,
  changedFields: ProfileFormField[],
): ProfileFormValue {
  const rebased: ProfileFormValue = {
    profile: { ...latest.profile },
    userRole: latest.userRole,
    state: latest.state,
  };
  for (const field of changedFields) {
    switch (field) {
      case "user_role":
        rebased.userRole = draft.userRole;
        break;
      case "state":
        rebased.state = draft.state;
        break;
      case "building_class":
        rebased.profile.building_class = draft.profile.building_class;
        break;
      case "work_type":
        rebased.profile.work_type = draft.profile.work_type;
        break;
      case "subclasses":
        rebased.profile.subclasses = draft.profile.subclasses;
        break;
      case "scale":
        rebased.profile.scale = draft.profile.scale;
        break;
      case "complexity":
        rebased.profile.complexity = draft.profile.complexity;
        break;
      case "work_scope":
        rebased.profile.work_scope = draft.profile.work_scope;
        break;
    }
  }
  return rebased;
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
  onSelectWorkflow,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunRefreshCostPlan,
  onRunSortFiles,
  onCancelWorkflow,
  onCancelCostPlan,
  onCancelSortFiles,
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
  onRunRefreshCostPlan?: () => void;
  onRunSortFiles: () => void;
  onCancelWorkflow?: () => void;
  onCancelCostPlan?: () => void;
  onCancelSortFiles?: () => void;
  onOpenDraft: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
  onSelectWorkflow?: (workflowId: string) => void;
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

  // Tender Comparison opens its own route; skip the intermediate gate panel.
  useEffect(() => {
    if (!isProcurement) return;
    onOpenTenderComparison();
  }, [isProcurement, onOpenTenderComparison]);

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
              <OverlayGateNotice
                workflow="Create PMP"
                issues={[
                  ...project.overlay_status.missing,
                  ...project.overlay_status.invalid,
                ]}
                onOpenProfile={
                  onSelectWorkflow
                    ? () => onSelectWorkflow("project-profile")
                    : undefined
                }
              />
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={onRunCreatePmp}
                disabled={isRunningWorkflow || !project.overlay_status.ready}
              >
                {isRunningWorkflow ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Play className="size-4" aria-hidden />
                )}
                {isRunningWorkflow ? "Running" : "Create PMP"}
              </Button>
              {isRunningWorkflow && onCancelWorkflow ? (
                <Button variant="outline" onClick={onCancelWorkflow}>
                  <Square className="size-4" aria-hidden />
                  Cancel
                </Button>
              ) : null}
              <Button
                variant="outline"
                onClick={onRunUpdatePmp}
                disabled={
                  isRunningWorkflow || !project.overlay_status.ready || !latestDraft
                }
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
              <OverlayGateNotice
                workflow="Create Cost Plan"
                issues={[
                  ...project.overlay_status.missing,
                  ...project.overlay_status.invalid,
                ]}
                onOpenProfile={
                  onSelectWorkflow
                    ? () => onSelectWorkflow("project-profile")
                    : undefined
                }
              />
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={onRunCreateCostPlan}
                disabled={isRunningCostPlan || !project.overlay_status.ready}
              >
                {isRunningCostPlan ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Play className="size-4" aria-hidden />
                )}
                {isRunningCostPlan ? "Running" : "Create cost plan"}
              </Button>
              {isRunningCostPlan && onCancelCostPlan ? (
                <Button variant="outline" onClick={onCancelCostPlan}>
                  <Square className="size-4" aria-hidden />
                  Cancel
                </Button>
              ) : null}
              <Button
                variant="outline"
                onClick={onRunRefreshCostPlan}
                disabled={
                  !onRunRefreshCostPlan ||
                  isRunningCostPlan ||
                  !project.overlay_status.ready ||
                  !activeDraft
                }
              >
                {isRunningCostPlan ? (
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                ) : (
                  <RefreshCw className="size-4" aria-hidden />
                )}
                Refresh cost plan
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
              <OverlayGateNotice
                workflow="Sort Files"
                issues={[
                  ...project.overlay_status.missing,
                  ...project.overlay_status.invalid,
                ]}
                onOpenProfile={
                  onSelectWorkflow
                    ? () => onSelectWorkflow("project-profile")
                    : undefined
                }
              />
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
              {isRunningSortFiles && onCancelSortFiles ? (
                <Button variant="outline" onClick={onCancelSortFiles}>
                  <Square className="size-4" aria-hidden />
                  Cancel
                </Button>
              ) : null}
            </div>

            <SortFilesResultPanel
              summary={sortFilesResult?.summary ?? null}
              rows={sortFilesResult?.rows ?? []}
            />

            <WorkflowTracePanel trace={activeTrace} isRunning={activeRunning} />
          </>
        ) : isProcurement ? (
          <div className="flex min-h-32 items-center justify-center rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
            Opening tender comparison
          </div>
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

function OverlayGateNotice({
  workflow,
  issues,
  onOpenProfile,
}: {
  workflow: string;
  issues: OverlayIssue[];
  onOpenProfile?: () => void;
}) {
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-medium">{workflow} is blocked by missing overlays.</p>
          <ul className="mt-2 space-y-1 text-xs">
            {issues.map((issue) => (
              <li key={`${workflow}-${issue.field}-${issue.reason}`}>
                {issue.field}: {issue.reason}
              </li>
            ))}
          </ul>
        </div>
        {onOpenProfile ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-fit border-destructive/30 bg-background text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={onOpenProfile}
          >
            <Settings2 className="size-4" aria-hidden />
            Set project profile
          </Button>
        ) : null}
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
