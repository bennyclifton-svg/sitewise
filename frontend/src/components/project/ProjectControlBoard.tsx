import {
  CheckCircle2,
  ClipboardList,
  Inbox,
  ListChecks,
  LoaderCircle,
  MessageSquareWarning,
  Play,
  ReceiptText,
  RefreshCw,
  Save,
  Scale,
  Settings2,
  ShieldAlert,
  Square,
  Table2,
  type LucideIcon,
} from "lucide-react";
import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProfileProposalStrip } from "@/components/project/ProfileProposalStrip";
import {
  ProcurementRequestPanel,
  type RunnableProcurementRequestKind,
} from "@/components/project/ProcurementRequestPanel";
import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import { WorkflowProgressStrip } from "@/components/project/WorkflowProgressStrip";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { type WorkflowStatus } from "@/components/project/workflow/workflowStatus";
import {
  buildLifecycleTiles,
  type WorkflowTile,
} from "@/components/project/workflow/workflowTiles";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  OverlayIssue,
  ProcessInvoicesResult,
  ProjectDetail,
  ProjectProfileProposal,
  SortFilesResponse,
  WorkflowCapability,
  WorkflowRun,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import {
  compactTaxonomyValue,
  taxonomyValueFromProject,
} from "@/lib/project-taxonomy";
import { projectStateOptions } from "@/lib/project-overlays";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import { cn } from "@/lib/utils";
import {
  workflowProgressStage,
  workflowProgressTitle,
  workflowRunPreview,
  type WorkflowProgressMode,
} from "@/lib/workflow-progress";

const DraftReviewPanel = lazy(() =>
  import("@/components/project/DraftReviewPanel").then((module) => ({
    default: module.DraftReviewPanel,
  })),
);
const CopyContentButton = lazy(() =>
  import("@/components/project/CopyContentButton").then((module) => ({
    default: module.CopyContentButton,
  })),
);
const WorkflowDraftPreview = lazy(() =>
  import("@/components/project/WorkflowDraftPreview").then((module) => ({
    default: module.WorkflowDraftPreview,
  })),
);
const InvoiceProcessStatus = lazy(() =>
  import("@/components/project/InvoiceProcessStatus").then((module) => ({
    default: module.InvoiceProcessStatus,
  })),
);

export function ProjectControlBoard({
  project,
  profileProposals = [],
  latestDraft,
  latestCostPlanDraft,
  trace,
  costPlanTrace,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
  pmpRunMode = null,
  costPlanRunMode = null,
  pmpProgressKey = null,
  costPlanProgressKey = null,
  activeWorkflowRun = null,
  activeCostPlanRun = null,
  activeProcurementRun = null,
  procurementError = null,
  isRunningProcurement = false,
  procurementRefreshToken = 0,
  selectedWorkflowId,
  onSelectWorkflow,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunRefreshCostPlan,
  onRunProcessInvoices,
  onRunSortFiles,
  onCancelWorkflow,
  onCancelCostPlan,
  onCancelProcurement,
  onRunProcurement,
  onCancelSortFiles,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
  onProjectUpdated,
  onProfileProposalsResolved,
  onDraftUpdated,
  invoiceProcessResult = null,
}: {
  project: ProjectDetail;
  profileProposals?: ProjectProfileProposal[];
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  trace: WorkflowTraceEvent[];
  costPlanTrace: WorkflowTraceEvent[];
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
  /** Which Project Plan action started the active run (create vs update). */
  pmpRunMode?: WorkflowProgressMode | null;
  /** Which Cost Plan action started the active run (create vs refresh). */
  costPlanRunMode?: WorkflowProgressMode | null;
  /** Stable key for the Project Plan progress strip session. */
  pmpProgressKey?: string | null;
  /** Stable key for the Cost Plan progress strip session. */
  costPlanProgressKey?: string | null;
  activeWorkflowRun?: WorkflowRun | null;
  activeCostPlanRun?: WorkflowRun | null;
  activeProcurementRun?: WorkflowRun | null;
  procurementError?: string | null;
  isRunningProcurement?: boolean;
  procurementRefreshToken?: number;
  selectedWorkflowId: string;
  onSelectWorkflow?: (workflowId: string) => void;
  onRunCreatePmp: () => void;
  onRunUpdatePmp: () => void;
  onRunCreateCostPlan: () => void;
  onRunRefreshCostPlan?: () => void;
  onRunProcessInvoices?: () => void;
  onRunSortFiles: () => void;
  onCancelWorkflow?: () => void;
  onCancelCostPlan?: () => void;
  onCancelProcurement?: () => void;
  onRunProcurement?: (kind: RunnableProcurementRequestKind, targetName: string) => void;
  onCancelSortFiles?: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
  onProjectUpdated?: (project: ProjectDetail) => void;
  onProfileProposalsResolved?: () => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  invoiceProcessResult?: ProcessInvoicesResult | null;
}) {
  const lifecycle = buildLifecycleTiles({
    project,
    latestDraft,
    latestCostPlanDraft,
    workflowError,
    costPlanWorkflowError,
    isRunningWorkflow,
    isRunningCostPlan,
    procurementError,
    isRunningProcurement,
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
      <ProfileProposalStrip
        projectId={project.id}
        proposals={profileProposals}
        onResolved={() => {
          onProfileProposalsResolved?.();
        }}
      />

      <section className="cockpit-signature-card cockpit-signature-card--bracketed min-w-0 rounded-lg border bg-card shadow-sm">
        <WorkflowDetail
          tile={selectedTile}
          project={project}
          latestDraft={latestDraft}
          latestCostPlanDraft={latestCostPlanDraft}
          trace={trace}
          costPlanTrace={costPlanTrace}
          workflowError={workflowError}
          costPlanWorkflowError={costPlanWorkflowError}
          isRunningWorkflow={isRunningWorkflow}
          isRunningCostPlan={isRunningCostPlan}
          pmpRunMode={pmpRunMode}
          costPlanRunMode={costPlanRunMode}
          pmpProgressKey={pmpProgressKey}
          costPlanProgressKey={costPlanProgressKey}
          activeWorkflowRun={activeWorkflowRun}
          activeCostPlanRun={activeCostPlanRun}
          activeProcurementRun={activeProcurementRun}
          procurementError={procurementError}
          isRunningProcurement={isRunningProcurement}
          procurementRefreshToken={procurementRefreshToken}
          onSelectWorkflow={onSelectWorkflow}
          onRunCreatePmp={onRunCreatePmp}
          onRunUpdatePmp={onRunUpdatePmp}
          onRunCreateCostPlan={onRunCreateCostPlan}
          onRunRefreshCostPlan={onRunRefreshCostPlan}
          onRunProcessInvoices={onRunProcessInvoices}
          onRunSortFiles={onRunSortFiles}
          onCancelWorkflow={onCancelWorkflow}
          onCancelCostPlan={onCancelCostPlan}
          onCancelProcurement={onCancelProcurement}
          onRunProcurement={onRunProcurement}
          onCancelSortFiles={onCancelSortFiles}
          onOpenTenderComparison={onOpenTenderComparison}
          inboxCount={inboxCount}
          sortFilesResult={sortFilesResult}
          sortFilesDraft={sortFilesDraft}
          sortFilesError={sortFilesError}
          isRunningSortFiles={isRunningSortFiles}
          onProjectUpdated={onProjectUpdated}
          onDraftUpdated={onDraftUpdated}
          invoiceProcessResult={invoiceProcessResult}
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
        state: form.state || null,
        site_address: form.siteAddress || null,
        client: form.client || null,
      });
      onProjectUpdated({
        ...project,
        building_class: updated.profile.building_class,
        work_type: updated.profile.work_type,
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
            site_address: updated.profile.site_address,
            client: updated.profile.client,
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
            Set state, class, and work type here so chat, knowledge
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
      <div className="grid gap-3">
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
      <div className="grid gap-3 md:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={`project-site-address-${project.id}`}>Site address</Label>
          <Input
            id={`project-site-address-${project.id}`}
            value={form.siteAddress}
            onChange={(event) =>
              updateDraft({ ...form, siteAddress: event.target.value })
            }
            placeholder="Street, suburb STATE postcode"
            disabled={saving || !onProjectUpdated}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor={`project-client-${project.id}`}>Client / owners</Label>
          <Input
            id={`project-client-${project.id}`}
            value={form.client}
            onChange={(event) =>
              updateDraft({ ...form, client: event.target.value })
            }
            placeholder="Client or owner name"
            disabled={saving || !onProjectUpdated}
          />
        </div>
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
  state: string;
  siteAddress: string;
  client: string;
};

type ProfileFormField =
  | keyof TaxonomyPickerValue
  | "state"
  | "site_address"
  | "client";

const PROFILE_FORM_FIELDS: readonly ProfileFormField[] = [
  "building_class",
  "work_type",
  "subclasses",
  "scale",
  "complexity",
  "work_scope",
  "state",
  "site_address",
  "client",
];

function profileFormFromProject(project: ProjectDetail): ProfileFormValue {
  const taxonomy = project.metadata?.taxonomy;
  const siteAddress =
    (typeof taxonomy?.site_address === "string" && taxonomy.site_address) ||
    (typeof project.metadata?.site_address === "string" &&
      project.metadata.site_address) ||
    "";
  const client =
    (typeof taxonomy?.client === "string" && taxonomy.client) ||
    (typeof project.metadata?.client === "string" && project.metadata.client) ||
    "";
  return {
    profile: taxonomyValueFromProject(project),
    state: project.state ?? "",
    siteAddress,
    client,
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
  if (field === "state") return form.state;
  if (field === "site_address") return form.siteAddress;
  if (field === "client") return form.client;
  return form.profile[field];
}

function rebaseProfileForm(
  latest: ProfileFormValue,
  draft: ProfileFormValue,
  changedFields: ProfileFormField[],
): ProfileFormValue {
  const rebased: ProfileFormValue = {
    profile: { ...latest.profile },
    state: latest.state,
    siteAddress: latest.siteAddress,
    client: latest.client,
  };
  for (const field of changedFields) {
    switch (field) {
      case "state":
        rebased.state = draft.state;
        break;
      case "site_address":
        rebased.siteAddress = draft.siteAddress;
        break;
      case "client":
        rebased.client = draft.client;
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

function WorkflowDetail({
  tile,
  project,
  latestDraft,
  latestCostPlanDraft,
  trace,
  costPlanTrace,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
  pmpRunMode,
  costPlanRunMode,
  pmpProgressKey,
  costPlanProgressKey,
  activeWorkflowRun,
  activeCostPlanRun,
  activeProcurementRun,
  procurementError,
  isRunningProcurement,
  procurementRefreshToken,
  onSelectWorkflow,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunRefreshCostPlan,
  onRunProcessInvoices,
  onRunSortFiles,
  onCancelWorkflow,
  onCancelCostPlan,
  onCancelProcurement,
  onRunProcurement,
  onCancelSortFiles,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
  onProjectUpdated,
  onDraftUpdated,
  invoiceProcessResult,
}: {
  tile: WorkflowTile;
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  trace: WorkflowTraceEvent[];
  costPlanTrace: WorkflowTraceEvent[];
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
  pmpRunMode: WorkflowProgressMode | null;
  costPlanRunMode: WorkflowProgressMode | null;
  pmpProgressKey: string | null;
  costPlanProgressKey: string | null;
  activeWorkflowRun: WorkflowRun | null;
  activeCostPlanRun: WorkflowRun | null;
  activeProcurementRun: WorkflowRun | null;
  procurementError: string | null;
  isRunningProcurement: boolean;
  procurementRefreshToken: number;
  onRunCreatePmp: () => void;
  onRunUpdatePmp: () => void;
  onRunCreateCostPlan: () => void;
  onRunRefreshCostPlan?: () => void;
  onRunProcessInvoices?: () => void;
  onRunSortFiles: () => void;
  onCancelWorkflow?: () => void;
  onCancelCostPlan?: () => void;
  onCancelProcurement?: () => void;
  onRunProcurement?: (kind: RunnableProcurementRequestKind, targetName: string) => void;
  onCancelSortFiles?: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
  onSelectWorkflow?: (workflowId: string) => void;
  onProjectUpdated?: (project: ProjectDetail) => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  invoiceProcessResult: ProcessInvoicesResult | null;
}) {
  const isProjectProfile = tile.id === "project-profile";
  const isCreatePmp = tile.id === "create-pmp";
  const isCostPlan = tile.id === "cost-plan";
  const isDocumentIntake = tile.id === "document-intake";
  const isProcurementRequests = tile.id === "procurement-requests";
  const isProcurement = tile.id === "procurement";
  // Only while the run owns the panel: a completed run clears its preview, so
  // the accepted draft takes the space back.
  const pmpPreview = isRunningWorkflow
    ? workflowRunPreview(activeWorkflowRun?.progress)
    : null;
  const costPlanPreview = isRunningCostPlan
    ? workflowRunPreview(activeCostPlanRun?.progress)
    : null;
  const costPlanCapability = project.workflow_capabilities?.capabilities.create_cost_plan;
  const costPlanSupported = !costPlanCapability || costPlanCapability.status === "supported";
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
      <div className="space-y-4 p-4">
        {isProjectProfile ? (
          <ProjectProfilePanel
            key={project.id}
            project={project}
            onProjectUpdated={onProjectUpdated}
          />
        ) : isCreatePmp ? (
          <>
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

            {isRunningWorkflow ? (
              <WorkflowProgressStrip
                title={workflowProgressTitle("project_plan", pmpRunMode ?? "create")}
                kind="project_plan"
                runId={pmpProgressKey ?? activeWorkflowRun?.id ?? "pending-project-plan"}
                runState={activeWorkflowRun?.state ?? "queued"}
                progressStage={
                  workflowProgressStage(activeWorkflowRun?.progress) ?? "queued"
                }
                onCancel={activeWorkflowRun ? onCancelWorkflow : undefined}
              />
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={onRunCreatePmp}
                disabled={isRunningWorkflow || !project.overlay_status.ready}
              >
                <Play className="size-4" aria-hidden />
                Create PMP
              </Button>
              <Button
                variant="outline"
                onClick={onRunUpdatePmp}
                disabled={
                  isRunningWorkflow || !project.overlay_status.ready || !latestDraft
                }
              >
                <RefreshCw className="size-4" aria-hidden />
                Update PMP
              </Button>
              <Suspense fallback={null}>
                <CopyContentButton
                  loadContent={async () => {
                    if (!latestDraft) return "";
                    const fullDraft = await api.getProjectDraft(project.id, latestDraft.id);
                    return fullDraft.content_markdown;
                  }}
                  label="Copy project management plan"
                  disabled={!latestDraft}
                  size="icon"
                />
              </Suspense>
            </div>

            {pmpPreview ? (
              <Suspense fallback={<DraftReviewFallback label="Building project plan..." />}>
                <WorkflowDraftPreview
                  preview={pmpPreview}
                  title={workflowProgressTitle("project_plan", pmpRunMode ?? "create")}
                />
              </Suspense>
            ) : (
              <Suspense
                fallback={<DraftReviewFallback label="Loading project plan..." />}
              >
                <DraftReviewPanel
                  projectId={project.id}
                  draft={latestDraft}
                  workflowType="create_pmp"
                  embedded
                  onDraftUpdated={(draft) => {
                    onDraftUpdated?.(draft);
                  }}
                />
              </Suspense>
            )}

          </>
        ) : isCostPlan ? (
          <>
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

            {!costPlanSupported ? (
              <CapabilityGateNotice workflow="Cost Plan" capability={costPlanCapability} />
            ) : null}

            {isRunningCostPlan ? (
              <WorkflowProgressStrip
                title={workflowProgressTitle("cost_plan", costPlanRunMode ?? "create")}
                kind="cost_plan"
                runId={
                  costPlanProgressKey ??
                  activeCostPlanRun?.id ??
                  "pending-cost-plan"
                }
                runState={activeCostPlanRun?.state ?? "queued"}
                progressStage={
                  workflowProgressStage(activeCostPlanRun?.progress) ?? "queued"
                }
                onCancel={activeCostPlanRun ? onCancelCostPlan : undefined}
              />
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={onRunCreateCostPlan}
                disabled={
                  isRunningCostPlan || !project.overlay_status.ready || !costPlanSupported
                }
              >
                <Play className="size-4" aria-hidden />
                Create cost plan
              </Button>
              <Button
                variant="outline"
                onClick={onRunRefreshCostPlan}
                disabled={
                  !onRunRefreshCostPlan ||
                  isRunningCostPlan ||
                  !project.overlay_status.ready ||
                  !costPlanSupported ||
                  !activeDraft
                }
              >
                <RefreshCw className="size-4" aria-hidden />
                Refresh cost plan
              </Button>
              <Button
                variant="outline"
                onClick={onRunProcessInvoices}
                disabled={
                  !onRunProcessInvoices ||
                  isRunningCostPlan ||
                  !project.overlay_status.ready ||
                  !costPlanSupported ||
                  !activeDraft
                }
              >
                <ReceiptText className="size-4" aria-hidden />
                Process invoices
              </Button>
            </div>

            {invoiceProcessResult ? (
              <Suspense fallback={null}>
                <InvoiceProcessStatus result={invoiceProcessResult} />
              </Suspense>
            ) : null}

            {costPlanPreview ? (
              <Suspense fallback={<DraftReviewFallback label="Building cost plan..." />}>
                <WorkflowDraftPreview
                  preview={costPlanPreview}
                  title={workflowProgressTitle(
                    "cost_plan",
                    costPlanRunMode ?? "create",
                  )}
                />
              </Suspense>
            ) : (
              <Suspense fallback={<DraftReviewFallback costWorkbook />}>
                <DraftReviewPanel
                  projectId={project.id}
                  draft={latestCostPlanDraft}
                  workflowType="create_cost_plan"
                  embedded
                  onDraftUpdated={(draft) => {
                    onDraftUpdated?.(draft);
                  }}
                />
              </Suspense>
            )}
          </>
        ) : isProcurementRequests ? (
          <ProcurementRequestPanel
            project={project}
            activeRun={activeProcurementRun}
            isRunning={isRunningProcurement}
            error={procurementError}
            refreshToken={procurementRefreshToken}
            renderGate={(kind) => {
              const capability =
                kind === "consultant_rfp"
                  ? project.workflow_capabilities?.capabilities.consultant_procurement
                  : project.workflow_capabilities?.capabilities.trade_procurement;
              if (capability && capability.status !== "supported") {
                return (
                  <CapabilityGateNotice
                    workflow={kind === "consultant_rfp" ? "RFP" : "Trade procurement"}
                    capability={capability}
                  />
                );
              }
              return null;
            }}
            onCreate={(kind, targetName) => onRunProcurement?.(kind, targetName)}
            onCancel={onCancelProcurement}
            onDraftUpdated={onDraftUpdated}
          />
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

function DraftReviewFallback({
  label = "Loading cost workbook...",
  costWorkbook = false,
}: {
  label?: string;
  costWorkbook?: boolean;
}) {
  if (!costWorkbook) {
    return <p className="text-sm text-muted-foreground">{label}</p>;
  }
  return (
    <section className="rounded-md border bg-background">
      <header className="flex items-center gap-2 border-b px-4 py-3">
        <Table2 className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <h2 className="text-sm font-semibold">Cost workbook</h2>
      </header>
      <p className="p-4 text-sm text-muted-foreground" role="status">
        {label}
      </p>
    </section>
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

function CapabilityGateNotice({
  workflow,
  capability,
}: {
  workflow: string;
  capability?: WorkflowCapability;
}) {
  const reasons = capability?.reasons ?? [];
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
      <p className="font-medium">{workflow} is not supported for this project yet.</p>
      {reasons.length ? (
        <ul className="mt-2 space-y-1 text-xs">
          {reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
    </div>
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
