import {
  CheckCircle2,
  ClipboardList,
  Download,
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

import {
  ExcelFileIcon,
  PdfFileIcon,
  WordFileIcon,
} from "@/components/icons/OfficeFileIcons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MenuSelect } from "@/components/ui/menu-select";
import { ProfileProposalStrip } from "@/components/project/ProfileProposalStrip";
import { ProgramWorkbench } from "@/components/project/ProgramWorkbench";
import {
  ProcurementRequestPanel,
  type RunnableProcurementRequestKind,
} from "@/components/project/ProcurementRequestPanel";
import { SortFilesResultPanel } from "@/components/project/SortFilesResultPanel";
import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { type WorkflowStatus } from "@/components/project/workflow/workflowStatus";
import {
  buildLifecycleTiles,
  type WorkflowTile,
} from "@/components/project/workflow/workflowTiles";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
  OverlayIssue,
  ProcessInvoicesResult,
  ProcurementStrategyRow,
  ProjectDetail,
  ProjectProfileProposal,
  SortFilesResponse,
  WorkflowCapability,
  WorkflowRun,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { api } from "@/lib/api";
import { stripArtifactBlockMarkers } from "@/lib/artifact-markdown";
import { ApiError } from "@/lib/http";
import { runOptimisticMutation } from "@/lib/optimistic-mutation";
import { taxonomyValueFromProject } from "@/lib/project-taxonomy";
import {
  overlayIssuesFromProfile,
  projectStateOptions,
} from "@/lib/project-overlays";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import { cn } from "@/lib/utils";
import { type WorkflowProgressMode } from "@/lib/workflow-progress";

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

const WARM_WORKFLOW_IDS = [
  "create-pmp",
  "cost-plan",
  "program",
  "procurement-requests",
  "project-profile",
] as const;
const WARM_WORKFLOW_ID_SET: ReadonlySet<string> = new Set(WARM_WORKFLOW_IDS);

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
  onEditProcurementStrategyRow,
  onCancelSortFiles,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
  onProjectUpdated,
  onProfileProposalsResolved,
  onDraftSelected,
  onDraftUpdated,
  repositoryEvidence = [],
  selectedEvidenceIds,
  onSelectEvidenceIds,
  onTransmittalSessionChange,
  invoiceProcessResult = null,
  openInvoiceId = null,
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
  onRunProcurement?: (
    kind: RunnableProcurementRequestKind,
    targetName: string,
    action?: "create" | "update",
  ) => void;
  onEditProcurementStrategyRow?: (row: ProcurementStrategyRow) => void;
  onCancelSortFiles?: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
  onProjectUpdated?: (project: ProjectDetail) => void;
  onProfileProposalsResolved?: () => void;
  onDraftSelected?: (draft: DraftArtifactSummary) => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  repositoryEvidence?: EvidencePreview[];
  selectedEvidenceIds?: Set<string>;
  onSelectEvidenceIds?: (evidenceIds: Set<string>) => void;
  onTransmittalSessionChange?: (
    session: { draftId: string; workflowType: string } | null,
  ) => void;
  invoiceProcessResult?: ProcessInvoicesResult | null;
  openInvoiceId?: string | null;
}) {
  const [warmedProjectId, setWarmedProjectId] = useState<string | null>(null);
  useEffect(() => {
    const id = project.id;
    const timer = window.setTimeout(() => setWarmedProjectId(id), 0);
    return () => window.clearTimeout(timer);
  }, [project.id]);
  const warmReady = warmedProjectId === project.id;

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
  const warmTiles = WARM_WORKFLOW_IDS.map((id) =>
    lifecycle.find((tile) => tile.id === id),
  ).filter((tile): tile is WorkflowTile => Boolean(tile));
  const detailProps = {
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
    onEditProcurementStrategyRow,
    onCancelSortFiles,
    onOpenTenderComparison,
    inboxCount,
    sortFilesResult,
    sortFilesDraft,
    sortFilesError,
    isRunningSortFiles,
    onProjectUpdated,
    onDraftSelected,
    onDraftUpdated,
    repositoryEvidence,
    selectedEvidenceIds,
    onSelectEvidenceIds,
    onTransmittalSessionChange,
    invoiceProcessResult,
    openInvoiceId,
  };

  function shouldMountWarm(id: string): boolean {
    if (selectedWorkflowId === id) return true;
    if (!warmReady) return false;
    if (id === "create-pmp") return latestDraft != null;
    if (id === "cost-plan") return latestCostPlanDraft != null;
    return true;
  }

  return (
    <div
      data-testid="workbench-frame"
      className="flex w-full min-w-0 flex-col gap-5 p-4 lg:p-6"
    >
      <ProfileProposalStrip
        projectId={project.id}
        proposals={profileProposals}
        onResolved={() => {
          onProfileProposalsResolved?.();
        }}
      />

      <section className="relative min-w-0">
        {warmTiles.map((tile) =>
          shouldMountWarm(tile.id) ? (
            <WarmPane
              key={tile.id}
              workflowId={tile.id}
              active={selectedWorkflowId === tile.id}
            >
              <WorkflowDetail
                tile={tile}
                active={selectedWorkflowId === tile.id}
                {...detailProps}
              />
            </WarmPane>
          ) : null,
        )}
        {selectedTile && !WARM_WORKFLOW_ID_SET.has(selectedTile.id) ? (
          <WorkflowDetail tile={selectedTile} {...detailProps} />
        ) : null}
      </section>
    </div>
  );
}

function WarmPane({
  workflowId,
  active,
  children,
}: {
  workflowId: string;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div
      data-testid={`workbench-pane-${workflowId}`}
      hidden={!active}
      aria-hidden={!active}
      inert={!active}
      className={cn(!active && "hidden")}
    >
      {children}
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
  const form = draft ?? serverForm;
  const formOverlayIssues = overlayIssuesFromProfile({
    buildingClass: form.profile.building_class,
    workType: form.profile.work_type,
    state: form.state,
  });
  const serverOverlayIssues = [
    ...project.overlay_status.missing,
    ...project.overlay_status.invalid,
  ];
  const overlayPendingSave =
    formOverlayIssues.length === 0 && serverOverlayIssues.length > 0;
  const overlayIssues = overlayPendingSave
    ? serverOverlayIssues
    : formOverlayIssues;

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
    if (saving || !onProjectUpdated || !draft || !baseForm) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    const snapshot = {
      form: draft,
      baseForm,
      revision: editingRevision ?? serverRevision,
    };
    let unresolvedConflict = false;
    try {
      const updated = await runOptimisticMutation({
        snapshot,
        optimistic: snapshot,
        apply: (state) => {
          setDraft(state.form);
          setBaseForm(state.baseForm);
          setEditingRevision(state.revision);
        },
        commit: (base) =>
          api.updateProject(project.id, {
            expected_revision: base.revision,
            title: base.form.title.trim(),
            building_class: base.form.profile.building_class ?? null,
            work_type: base.form.profile.work_type ?? null,
            subclasses: base.form.profile.subclasses ?? [],
            scale: base.form.profile.scale ?? {},
            complexity: base.form.profile.complexity ?? {},
            work_scope: base.form.profile.work_scope ?? [],
            state: base.form.state || null,
            site_address: base.form.siteAddress || null,
            client: base.form.client || null,
            budget: base.form.budget.trim() || null,
            scope_narrative: scopeNarrativeItems(base.form.scopeNarrative),
          }),
        confirmed: (result) => {
          const nextForm: ProfileFormValue = {
            title: result.profile.title ?? snapshot.form.title,
            profile: {
              building_class: result.profile.building_class,
              work_type: result.profile.work_type,
              subclasses: result.profile.subclasses,
              scale: result.profile.scale,
              complexity: result.profile.complexity,
              work_scope: result.profile.work_scope,
            },
            state: result.profile.state ?? "",
            siteAddress: result.profile.site_address ?? "",
            client: result.profile.client ?? "",
            budget: result.profile.budget ?? "",
            scopeNarrative: scopeNarrativeText(result.profile.scope_narrative),
          };
          return {
            form: nextForm,
            baseForm: nextForm,
            revision: result.new_revision,
          };
        },
        reload: async () => {
          const latest = await api.getProject(project.id);
          return {
            form: profileFormFromProject(latest),
            baseForm: profileFormFromProject(latest),
            revision: latest.profile_revision ?? 1,
          };
        },
        rebase: ({ pending, latest }) => {
          const changedFields = changedProfileFormFields(
            pending.form,
            pending.baseForm,
          );
          const rebased = rebaseProfileForm(
            latest.form,
            pending.form,
            changedFields,
          );
          if (changedProfileFormFields(rebased, latest.form).length === 0) {
            return { status: "unsafe" };
          }
          return {
            status: "safe",
            state: {
              form: rebased,
              baseForm: latest.form,
              revision: latest.revision,
            },
          };
        },
        onUnresolvedConflict: ({ pending, latest }) => {
          unresolvedConflict = true;
          setDraft(pending.form);
          setBaseForm(pending.baseForm);
          setEditingRevision(pending.revision);
          setConflictRevision(latest.revision);
          setError(
            "Project profile changed elsewhere. Your edit was kept locally.",
          );
        },
      });
      onProjectUpdated({
        ...project,
        title: updated.profile.title || draft.title,
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
            budget: updated.profile.budget,
            scope_narrative: updated.profile.scope_narrative,
          },
        },
        overlay_status: updated.overlay_status,
        risk_flags: updated.risk_flags,
      });
      setDraft(null);
      setBaseForm(null);
      setEditingRevision(null);
      setConflictRevision(null);
      setSaved(updated.overlay_status.ready);
    } catch (saveError) {
      if (!(saveError instanceof ApiError && saveError.status === 409) || !unresolvedConflict) {
        setError(
          saveError instanceof ApiError
            ? saveError.message
            : "Project profile could not be saved.",
        );
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-3">
      {conflictRevision !== null ? (
        <div
          className="border border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_12%,transparent)] p-3 text-sm text-[var(--sw-caution)]"
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
      {overlayIssues.length || overlayPendingSave ? (
        <div className="border border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_12%,transparent)] p-3 text-sm text-[var(--sw-caution)]">
          <p className="font-medium">
            {overlayPendingSave
              ? "Save profile to apply these overlays."
              : "Project overlays are incomplete."}
          </p>
          <p className="mt-1 text-xs">
            {overlayPendingSave
              ? "Class, work type, and state are selected here but not saved yet. Chat and workflows still see the previous profile."
              : "Set state, class, and work type here so chat, knowledge tools, and workflows use the right SiteWise context."}
          </p>
          {overlayPendingSave ? null : (
            <ul className="mt-2 space-y-1 text-xs">
              {overlayIssues.map((issue) => (
                <li key={`${issue.field}-${issue.reason}`}>
                  {issue.field.replace("_", " ")}: {issue.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      {onProjectUpdated ? (
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button
            type="button"
            onClick={() => void saveProfile()}
            disabled={
              saving ||
              !draft ||
              !draft.title.trim() ||
              !taxonomyQuery.data ||
              conflictRevision !== null
            }
            title={
              conflictRevision !== null
                ? "Resolve the profile conflict before saving"
                : !draft
                  ? "No unsaved changes"
                  : !draft.title.trim()
                    ? "Project name is required"
                    : undefined
            }
          >
            {saving ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Save className="size-4" aria-hidden />
            )}
            {saving ? "Saving" : "Save profile"}
          </Button>
          {saved ? <Badge variant="secondary">Saved</Badge> : null}
        </div>
      ) : null}
      <div className="grid gap-1">
        <Label
          htmlFor={`project-title-${project.id}`}
          className="text-xs font-normal text-muted-foreground"
        >
          Project name
        </Label>
        <Input
          id={`project-title-${project.id}`}
          value={form.title}
          onChange={(event) =>
            updateDraft({ ...form, title: event.target.value })
          }
          placeholder="Project name"
          disabled={saving || !onProjectUpdated}
        />
      </div>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(7.5rem,9rem)]">
        <div className="grid gap-1">
          <Label
            htmlFor={`project-site-address-${project.id}`}
            className="text-xs font-normal text-muted-foreground"
          >
            Site address
          </Label>
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
        <div className="grid gap-1">
          <Label
            htmlFor={`project-client-${project.id}`}
            className="text-xs font-normal text-muted-foreground"
          >
            Client / owners
          </Label>
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
        budget={form.budget}
        onBudgetChange={(next) => updateDraft({ ...form, budget: next })}
        scopeNarrative={form.scopeNarrative}
        onScopeNarrativeChange={(next) =>
          updateDraft({ ...form, scopeNarrative: next })
        }
      />
      {taxonomyQuery.error ? (
        <p className="text-sm text-destructive" role="alert">
          Project profile options could not load.
        </p>
      ) : null}
    </div>
  );
}

type ProfileFormValue = {
  title: string;
  profile: TaxonomyPickerValue;
  state: string;
  siteAddress: string;
  client: string;
  budget: string;
  scopeNarrative: string;
};

type ProfileFormField =
  | keyof TaxonomyPickerValue
  | "title"
  | "state"
  | "site_address"
  | "client"
  | "budget"
  | "scope_narrative";

const PROFILE_FORM_FIELDS: readonly ProfileFormField[] = [
  "title",
  "building_class",
  "work_type",
  "subclasses",
  "scale",
  "complexity",
  "work_scope",
  "state",
  "site_address",
  "client",
  "budget",
  "scope_narrative",
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
  const budget = typeof taxonomy?.budget === "string" ? taxonomy.budget : "";
  return {
    title: project.title,
    profile: taxonomyValueFromProject(project),
    state: project.state ?? "",
    siteAddress,
    client,
    budget,
    scopeNarrative: scopeNarrativeText(taxonomy?.scope_narrative),
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
  if (field === "title") return form.title;
  if (field === "state") return form.state;
  if (field === "site_address") return form.siteAddress;
  if (field === "client") return form.client;
  if (field === "budget") return form.budget;
  if (field === "scope_narrative") return form.scopeNarrative;
  return form.profile[field];
}

function rebaseProfileForm(
  latest: ProfileFormValue,
  draft: ProfileFormValue,
  changedFields: ProfileFormField[],
): ProfileFormValue {
  const rebased: ProfileFormValue = {
    title: latest.title,
    profile: { ...latest.profile },
    state: latest.state,
    siteAddress: latest.siteAddress,
    client: latest.client,
    budget: latest.budget,
    scopeNarrative: latest.scopeNarrative,
  };
  for (const field of changedFields) {
    switch (field) {
      case "title":
        rebased.title = draft.title;
        break;
      case "state":
        rebased.state = draft.state;
        break;
      case "site_address":
        rebased.siteAddress = draft.siteAddress;
        break;
      case "client":
        rebased.client = draft.client;
        break;
      case "budget":
        rebased.budget = draft.budget;
        break;
      case "scope_narrative":
        rebased.scopeNarrative = draft.scopeNarrative;
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

function scopeNarrativeText(items: string[] | undefined): string {
  return (items ?? []).filter((item) => item.trim()).join("\n");
}

function scopeNarrativeItems(text: string): string[] {
  return text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
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
    <div className="grid gap-1">
      <Label htmlFor={id} className="text-xs font-normal text-muted-foreground">
        {label}
      </Label>
      <MenuSelect
        id={id}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        options={[{ value: "", label: placeholder }, ...options]}
        onChange={onChange}
        aria-label={label}
      />
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
  procurementError,
  procurementRefreshToken,
  onSelectWorkflow,
  onRunCreatePmp,
  onRunUpdatePmp,
  onRunCreateCostPlan,
  onRunRefreshCostPlan,
  onRunProcessInvoices,
  onRunSortFiles,
  onRunProcurement,
  onEditProcurementStrategyRow,
  onCancelSortFiles,
  onOpenTenderComparison,
  inboxCount,
  sortFilesResult,
  sortFilesDraft,
  sortFilesError,
  isRunningSortFiles,
  onProjectUpdated,
  onDraftSelected,
  onDraftUpdated,
  repositoryEvidence = [],
  selectedEvidenceIds,
  onSelectEvidenceIds,
  onTransmittalSessionChange,
  openInvoiceId = null,
  active = true,
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
  onRunProcurement?: (
    kind: RunnableProcurementRequestKind,
    targetName: string,
    action?: "create" | "update",
  ) => void;
  onEditProcurementStrategyRow?: (row: ProcurementStrategyRow) => void;
  onCancelSortFiles?: () => void;
  onOpenTenderComparison: () => void;
  inboxCount: number;
  sortFilesResult: SortFilesResponse | null;
  sortFilesDraft: DraftArtifactSummary | null;
  sortFilesError: string | null;
  isRunningSortFiles: boolean;
  onSelectWorkflow?: (workflowId: string) => void;
  onProjectUpdated?: (project: ProjectDetail) => void;
  onDraftSelected?: (draft: DraftArtifactSummary) => void;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  repositoryEvidence?: EvidencePreview[];
  selectedEvidenceIds?: Set<string>;
  onSelectEvidenceIds?: (evidenceIds: Set<string>) => void;
  onTransmittalSessionChange?: (
    session: { draftId: string; workflowType: string } | null,
  ) => void;
  invoiceProcessResult: ProcessInvoicesResult | null;
  openInvoiceId?: string | null;
  active?: boolean;
}) {
  const isProjectProfile = tile.id === "project-profile";
  const isCreatePmp = tile.id === "create-pmp";
  const isCostPlan = tile.id === "cost-plan";
  const isProgram = tile.id === "program";
  const isDocumentIntake = tile.id === "document-intake";
  const isProcurementRequests = tile.id === "procurement-requests";
  const isProcurement = tile.id === "procurement";
  const costPlanCapability = project.workflow_capabilities?.capabilities.create_cost_plan;
  const costPlanSupported = !costPlanCapability || costPlanCapability.status === "supported";
  const activeTrace = isDocumentIntake
    ? (sortFilesResult?.trace ?? [])
    : isCostPlan
      ? costPlanTrace
      : trace;
  const activeRunning = isDocumentIntake ? isRunningSortFiles : false;
  const activeError = isCostPlan ? costPlanWorkflowError : workflowError;
  const activeDraft = isCostPlan ? latestCostPlanDraft : latestDraft;
  const [draftExportAction, setDraftExportAction] = useState<
    "docx" | "pdf" | "xlsx" | null
  >(null);
  const [draftExportError, setDraftExportError] = useState<string | null>(null);

  async function downloadDraftExport(format: "docx" | "pdf") {
    if (!latestDraft) return;
    setDraftExportAction(format);
    setDraftExportError(null);
    try {
      const blob = await api.downloadDraftExport(project.id, latestDraft.id, format);
      downloadBlob(
        blob,
        `${safeFilename(latestDraft.title)}_v${String(latestDraft.version).padStart(2, "0")}.${format}`,
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

  async function downloadCostPlanExcel() {
    if (!latestCostPlanDraft) return;
    setDraftExportAction("xlsx");
    setDraftExportError(null);
    try {
      const fullDraft = await api.getProjectDraft(project.id, latestCostPlanDraft.id);
      const workbook = costPlanWorkbookMetadata(fullDraft.provenance_metadata?.workbook);
      if (!workbook) {
        throw new Error("Cost workbook is not available for download.");
      }
      const blob = await api.downloadWorkspaceFile(project.id, workbook.workspace_path);
      downloadBlob(blob, workbook.file_name);
    } catch (error) {
      setDraftExportError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Could not download the Excel workbook.",
      );
    } finally {
      setDraftExportAction(null);
    }
  }

  async function downloadCostPlanPdf() {
    if (!latestCostPlanDraft) return;
    setDraftExportAction("pdf");
    setDraftExportError(null);
    try {
      const blob = await api.downloadDraftExport(
        project.id,
        latestCostPlanDraft.id,
        "pdf",
      );
      downloadBlob(
        blob,
        `${safeFilename(latestCostPlanDraft.title)}_v${String(latestCostPlanDraft.version).padStart(2, "0")}.pdf`,
      );
    } catch (error) {
      setDraftExportError(
        error instanceof ApiError
          ? error.message
          : "Could not export PDF.",
      );
    } finally {
      setDraftExportAction(null);
    }
  }

  // Tender Comparison opens its own route; skip the intermediate gate panel.
  useEffect(() => {
    if (!isProcurement) return;
    onOpenTenderComparison();
  }, [isProcurement, onOpenTenderComparison]);

  return (
    <div className="min-w-0">
      <div className="space-y-4">
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

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={onRunCreatePmp}
                  disabled={!project.overlay_status.ready}
                >
                  <Play className="size-4" aria-hidden />
                  Create PMP
                </Button>
                <Button
                  variant="outline"
                  onClick={onRunUpdatePmp}
                  disabled={!project.overlay_status.ready || !latestDraft}
                >
                  <RefreshCw className="size-4" aria-hidden />
                  Update PMP
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
                      disabled={!latestDraft || draftExportAction !== null}
                      aria-label="Download project management plan"
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
                <Suspense fallback={null}>
                  <CopyContentButton
                    loadContent={async () => {
                      if (!latestDraft) return "";
                      const fullDraft = await api.getProjectDraft(
                        project.id,
                        latestDraft.id,
                      );
                      const { insertAfterProgrammeHeading, stripProgrammeSectionBody } =
                        await import("@/lib/programme");
                      const markdown = stripProgrammeSectionBody(
                        stripArtifactBlockMarkers(fullDraft.content_markdown),
                      );
                      try {
                        const programme = await api.getProgrammeState(project.id);
                        if (!programme.pmp_embed_visible) return markdown;
                        const svg = await api.getProgrammeFigureSvg(project.id);
                        return insertAfterProgrammeHeading(markdown, svg);
                      } catch {
                        return markdown;
                      }
                    }}
                    label="Copy project management plan"
                    disabled={!latestDraft}
                    size="icon"
                    className="size-10"
                  />
                </Suspense>
              </div>
            </div>

            <Suspense
              fallback={<DraftReviewFallback label="Loading project plan..." />}
            >
                <DraftReviewPanel
                projectId={project.id}
                draft={latestDraft}
                projectTitle={project.title}
                workflowType="create_pmp"
                embedded
                active={active}
                repositoryEvidence={repositoryEvidence}
                selectedEvidenceIds={selectedEvidenceIds}
                onSelectEvidenceIds={onSelectEvidenceIds}
                onTransmittalSessionChange={onTransmittalSessionChange}
                onDraftUpdated={(draft) => {
                  onDraftUpdated?.(draft);
                }}
              />
            </Suspense>

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

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={onRunCreateCostPlan}
                  disabled={!project.overlay_status.ready || !costPlanSupported}
                >
                  <Play className="size-4" aria-hidden />
                  Create cost plan
                </Button>
                <Button
                  variant="outline"
                  onClick={onRunRefreshCostPlan}
                  disabled={
                    !onRunRefreshCostPlan ||
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
                    !project.overlay_status.ready ||
                    !costPlanSupported ||
                    !activeDraft
                  }
                >
                  <ReceiptText className="size-4" aria-hidden />
                  Process invoices
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
                      disabled={!activeDraft || draftExportAction !== null}
                      aria-label="Download cost plan"
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
                        void downloadCostPlanExcel();
                      }}
                    >
                      <ExcelFileIcon className="size-6" />
                      <span>Excel</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="gap-2.5 py-2"
                      disabled={draftExportAction !== null}
                      onSelect={() => {
                        void downloadCostPlanPdf();
                      }}
                    >
                      <PdfFileIcon className="size-6" />
                      <span>PDF</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Suspense fallback={null}>
                  <CopyContentButton
                    loadContent={async () => {
                      if (!latestCostPlanDraft) return "";
                      const fullDraft = await api.getProjectDraft(
                        project.id,
                        latestCostPlanDraft.id,
                      );
                      return stripArtifactBlockMarkers(fullDraft.content_markdown);
                    }}
                    label="Copy cost plan"
                    disabled={!activeDraft}
                    size="icon"
                    className="size-10"
                  />
                </Suspense>
              </div>
            </div>

            <Suspense fallback={<DraftReviewFallback costWorkbook />}>
              <DraftReviewPanel
                projectId={project.id}
                draft={latestCostPlanDraft}
                workflowType="create_cost_plan"
                embedded
                active={active}
                onDraftUpdated={(draft) => {
                  onDraftUpdated?.(draft);
                }}
                reviewInvoiceId={openInvoiceId}
              />
            </Suspense>
          </>
        ) : isProgram ? (
          <>
            {!project.overlay_status.ready ? (
              <OverlayGateNotice
                workflow="Program"
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
            {project.workflow_capabilities?.capabilities.edit_programme &&
            project.workflow_capabilities.capabilities.edit_programme.status !==
              "supported" ? (
              <CapabilityGateNotice
                workflow="Program"
                capability={project.workflow_capabilities.capabilities.edit_programme}
              />
            ) : null}
            {project.overlay_status.ready &&
            (!project.workflow_capabilities?.capabilities.edit_programme ||
              project.workflow_capabilities.capabilities.edit_programme.status ===
                "supported") ? (
              <ProgramWorkbench projectId={project.id} active={active} />
            ) : null}
          </>
        ) : isProcurementRequests ? (
          <ProcurementRequestPanel
            project={project}
            activeRun={null}
            isRunning={false}
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
                    workflow={
                      kind === "consultant_rfp"
                        ? "Request for Proposal"
                        : "Request for Tender"
                    }
                    capability={capability}
                  />
                );
              }
              return null;
            }}
            onCreate={(kind, targetName) => onRunProcurement?.(kind, targetName)}
            onUpdate={(kind, targetName) =>
              onRunProcurement?.(kind, targetName, "update")
            }
            onEditStrategyRowWithAi={onEditProcurementStrategyRow}
            onDraftSelected={onDraftSelected}
            onDraftUpdated={onDraftUpdated}
            repositoryEvidence={repositoryEvidence}
            selectedEvidenceIds={selectedEvidenceIds}
            onSelectEvidenceIds={onSelectEvidenceIds}
            onTransmittalSessionChange={onTransmittalSessionChange}
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

function costPlanWorkbookMetadata(
  value: unknown,
): { file_name: string; workspace_path: string } | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as { file_name?: unknown; workspace_path?: unknown };
  if (
    typeof candidate.file_name === "string" &&
    typeof candidate.workspace_path === "string"
  ) {
    return {
      file_name: candidate.file_name,
      workspace_path: candidate.workspace_path,
    };
  }
  return null;
}
