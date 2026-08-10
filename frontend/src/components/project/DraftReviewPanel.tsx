import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronRight,
  Eye,
  EyeOff,
  Table2,
} from "lucide-react";

import { InstructionTray } from "@/components/project/InstructionTray";
import { MarkdownContent } from "@/components/project/MarkdownContent";
import { SelectionInstructionCard } from "@/components/project/SelectionInstructionCard";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { WorkbookGrid } from "@/components/project/WorkbookGrid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { normalizeDraftMarkdown, splitTraceQa } from "@/lib/artifact-markdown";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import {
  clearTray,
  dropStaleTrays,
  loadTray,
  saveTray,
  type InstructionItem,
} from "@/lib/instruction-tray";
import {
  splitMarkdownSections,
  type MarkdownSectionSlice,
} from "@/lib/markdown-sections";
import { replaceMarkdownRange } from "@/lib/inline-markdown";
import {
  type MarkdownAnchor,
  type MarkdownRange,
} from "@/lib/markdown-selection";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  ProjectDecision,
  WorkflowTraceEvent,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

/**
 * Anchored instructions route through `revise_workflow_artefact`, which refuses
 * cost plans (canonical typed state) and tender reports (TCM owns them). The
 * affordance must not render where the server would reject the batch.
 */
function supportsAnchoredInstructions(workflowType: string): boolean {
  return workflowType !== "create_cost_plan" && workflowType !== "tender_report";
}

function changedRangesFrom(value: unknown): MarkdownRange[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (entry): entry is MarkdownRange =>
      typeof entry === "object" &&
      entry !== null &&
      typeof (entry as MarkdownRange).start === "number" &&
      typeof (entry as MarkdownRange).end === "number",
  );
}

function headingForOffset(sections: MarkdownSectionSlice[], offset: number): string {
  return (
    sections.find((section) => section.start <= offset && offset < section.end)
      ?.heading ?? "Document"
  );
}

function rebaseMessage(error: ApiError): string {
  const moved = /current version is v(\d+)/.exec(error.message);
  return moved
    ? `Draft moved to v${moved[1]} — review the current text and re-apply.`
    : `${error.message} Review the current text and re-apply.`;
}

export function DraftReviewPanel({
  projectId,
  draft,
  onDraftUpdated,
  workflowType,
  embedded = false,
  projectTitle,
}: {
  projectId: string;
  draft: DraftArtifact | DraftArtifactSummary | null;
  onDraftUpdated: (draft: DraftArtifact) => void;
  workflowType?: string;
  projectTitle?: string;
  /** Compact layout when nested inside a workflow panel. */
  embedded?: boolean;
}) {
  const [loadedDraft, setLoadedDraft] = useState<DraftArtifact | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectionEdit, setSelectionEdit] = useState<{
    draftId: string;
    version: number;
    range: MarkdownRange;
  } | null>(null);
  const [anchor, setAnchor] = useState<MarkdownAnchor | null>(null);
  const [trayOverride, setTrayOverride] = useState<{
    key: string;
    items: InstructionItem[];
  } | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  /** Kept separate from `actionError`, which renders inside the collapsed trace. */
  const [applyError, setApplyError] = useState<string | null>(null);
  const [showChanges, setShowChanges] = useState(true);
  const draftDetailsRef = useRef<HTMLDetailsElement>(null);
  const [decisionState, setDecisionState] = useState<{
    key: string;
    decisions: ProjectDecision[] | null;
    error: string | null;
  }>({ key: "", decisions: null, error: null });
  const decisionContextKey =
    draft && isPmpDraft(draft.workflow_type) ? `${projectId}:${draft.id}` : "";
  const projectDecisions =
    decisionState.key === decisionContextKey
      ? decisionState.decisions
      : decisionContextKey
        ? null
        : [];
  const decisionLoadError =
    decisionState.key === decisionContextKey ? decisionState.error : null;

  useEffect(() => {
    let cancelled = false;

    async function loadDraftContent() {
      setActionError(null);
      if (!draft) {
        setLoadedDraft(null);
        setIsLoadingDraft(false);
        return;
      }

      if (isFullDraft(draft)) {
        setLoadedDraft(draft);
        setIsLoadingDraft(false);
        return;
      }

      setLoadedDraft(null);
      setIsLoadingDraft(true);
      try {
        const data = await api.getProjectDraft(projectId, draft.id);
        if (!cancelled) {
          setLoadedDraft(data);
        }
      } catch (error) {
        if (!cancelled) {
          setActionError(error instanceof ApiError ? error.message : "Could not load draft.");
        }
      } finally {
        if (!cancelled) setIsLoadingDraft(false);
      }
    }

    void loadDraftContent();
    return () => {
      cancelled = true;
    };
  }, [projectId, draft]);

  useEffect(() => {
    let cancelled = false;
    if (!draft || !isPmpDraft(draft.workflow_type)) {
      return;
    }
    const requestKey = `${projectId}:${draft.id}`;
    async function loadDecisions() {
      try {
        const response = await api.listDecisions(projectId);
        if (!cancelled) {
          setDecisionState({
            key: requestKey,
            decisions: response.decisions,
            error: null,
          });
        }
      } catch {
        if (!cancelled) {
          setDecisionState({
            key: requestKey,
            decisions: null,
            error:
              "Current decision state could not be loaded. Reload before changing a selection.",
          });
        }
      }
    }
    void loadDecisions();
    return () => {
      cancelled = true;
    };
  }, [projectId, draft]);

  /**
   * One normalization for the whole panel (design decision D3). Section slices,
   * anchors, and the offsets the renderer stamps must all live in this same
   * offset space, and the server normalizes identically before verifying an
   * anchor — so `MarkdownContent` receives `source`, never the raw markdown.
   */
  const source = useMemo(
    () => (loadedDraft ? normalizeDraftMarkdown(loadedDraft.content_markdown) : ""),
    [loadedDraft],
  );
  const issueContent = useMemo(() => splitTraceQa(source), [source]);
  const sections = useMemo(() => splitMarkdownSections(source), [source]);
  const selectionEditRange =
    loadedDraft &&
    selectionEdit?.draftId === loadedDraft.id &&
    selectionEdit.version === loadedDraft.version
      ? selectionEdit.range
      : null;
  const changedRanges = useMemo(
    () => changedRangesFrom(loadedDraft?.provenance_metadata?.changed_ranges),
    [loadedDraft],
  );

  const trayKey = loadedDraft ? `${loadedDraft.id}:v${loadedDraft.version}` : "";
  const persistedTray = useMemo(
    () => (loadedDraft ? loadTray(loadedDraft.id, loadedDraft.version) : []),
    [loadedDraft],
  );
  const trayItems =
    trayOverride && trayOverride.key === trayKey ? trayOverride.items : persistedTray;

  const canInstruct =
    !!loadedDraft &&
    loadedDraft.status !== "accepted" &&
    !selectionEditRange &&
    supportsAnchoredInstructions(loadedDraft.workflow_type);

  const isCostPlanWorkflow =
    workflowType === "create_cost_plan" || draft?.workflow_type === "create_cost_plan";

  function writeTray(draftId: string, version: number, items: InstructionItem[]) {
    setTrayOverride({ key: `${draftId}:v${version}`, items });
    saveTray(draftId, version, items);
  }

  function addInstruction(instruction: string) {
    if (!loadedDraft || !anchor) return;
    writeTray(loadedDraft.id, loadedDraft.version, [
      ...trayItems,
      {
        id: crypto.randomUUID(),
        kind: "revise",
        anchorStart: anchor.start,
        anchorEnd: anchor.end,
        quotedText: anchor.quotedText,
        instruction,
        sectionHeading: headingForOffset(sections, anchor.start),
      },
    ]);
    setAnchor(null);
    window.getSelection()?.removeAllRanges();
  }

  async function applyInstructions() {
    if (!loadedDraft || trayItems.length === 0) return;
    setIsApplying(true);
    setApplyError(null);
    try {
      const response = await api.applyDraftInstructions(
        projectId,
        loadedDraft.id,
        loadedDraft.version,
        trayItems.map((item) => ({
          anchor_start: item.anchorStart,
          anchor_end: item.anchorEnd,
          quoted_text: item.quotedText,
          instruction: item.instruction,
        })),
      );
      const reasons = new Map(response.failed.map((item) => [item.index, item.reason]));
      // Items the server could not apply are re-seeded against the NEW version
      // carrying their reason; anything that landed is dropped.
      const reseeded = trayItems
        .map((item, index) => ({ ...item, error: reasons.get(index) }))
        .filter((item): item is typeof item & { error: string } => Boolean(item.error));
      clearTray(loadedDraft.id, loadedDraft.version);
      writeTray(response.draft.id, response.draft.version, reseeded);
      dropStaleTrays(response.draft.id, response.draft.version);
      setAnchor(null);
      setShowChanges(true);
      setLoadedDraft(response.draft);
      onDraftUpdated(response.draft);
    } catch (error) {
      // A 409 leaves the tray untouched: the anchors are stale, so the user
      // must re-read the current text rather than silently re-send them.
      setApplyError(
        error instanceof ApiError && error.status === 409
          ? rebaseMessage(error)
          : error instanceof ApiError
            ? error.message
            : "Could not apply changes.",
      );
    } finally {
      setIsApplying(false);
    }
  }

  if (!draft) {
    if (isCostPlanWorkflow) {
      return (
        <CostWorkbookSection
          workbook={null}
          emptyMessage="Create cost plan to generate the workbook."
        />
      );
    }
    return (
      <div
        className={cn(
          embedded
            ? "rounded-md border border-dashed p-4 text-sm text-muted-foreground"
            : "flex min-h-full items-center justify-center p-6",
        )}
      >
        {embedded ? (
          emptyDraftMessage(workflowType)
        ) : (
          <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
            {emptyDraftMessage(workflowType)}
          </div>
        )}
      </div>
    );
  }

  const displayDraft = loadedDraft ?? draft;

  const seed = metadataList(loadedDraft?.provenance_metadata?.seed_consulted);
  const evidence = metadataList(loadedDraft?.provenance_metadata?.evidence_refs);
  const context = metadataList(loadedDraft?.provenance_metadata?.context_refs);
  const trace = metadataTrace(loadedDraft?.provenance_metadata?.trace);
  const sectionsChanged = metadataStringList(loadedDraft?.provenance_metadata?.sections_changed);
  const evidenceChanged = evidenceChangedSummary(loadedDraft?.provenance_metadata?.evidence_changed);
  const workbook = workbookMetadata(loadedDraft?.provenance_metadata?.workbook);
  const isAccepted = displayDraft.status === "accepted";
  const canEditDraft =
    !isAccepted && supportsAnchoredInstructions(displayDraft.workflow_type);

  function startSelectionEdit(range: MarkdownRange) {
    if (!loadedDraft) return;
    setSelectionEdit({
      draftId: loadedDraft.id,
      version: loadedDraft.version,
      range,
    });
    setAnchor(null);
    setActionError(null);
    window.getSelection()?.removeAllRanges();
  }

  function startAiEdit(range: MarkdownRange, rect: DOMRect) {
    if (!loadedDraft || range.start < 0 || range.end > source.length) return;
    setSelectionEdit(null);
    setActionError(null);
    setAnchor({
      ...range,
      quotedText: source.slice(range.start, range.end),
      rect,
    });
    window.getSelection()?.removeAllRanges();
  }

  function openWorkflowTrace() {
    if (draftDetailsRef.current) {
      draftDetailsRef.current.open = true;
    }
    document.getElementById("draft-workflow-trace")?.scrollIntoView?.({
      behavior: "smooth",
      block: "start",
    });
  }

  async function saveSelectionEdit(range: MarkdownRange, replacement: string) {
    if (!loadedDraft || !selectionEditRange) return;
    if (
      range.start !== selectionEditRange.start ||
      range.end !== selectionEditRange.end
    ) {
      return;
    }

    const nextMarkdown = replaceMarkdownRange(source, range, replacement);
    if (nextMarkdown === source) {
      setSelectionEdit(null);
      return;
    }

    setIsSaving(true);
    setActionError(null);
    try {
      const updated = await api.patchDraft(
        projectId,
        loadedDraft.id,
        nextMarkdown,
        loadedDraft.version,
      );
      setLoadedDraft(updated);
      onDraftUpdated(updated);
      setSelectionEdit(null);
    } catch (error) {
      setActionError(
        error instanceof ApiError ? error.message : "Could not save selection.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  if (displayDraft.workflow_type === "create_cost_plan") {
    return (
      <article
        className={cn(
          "flex w-full min-w-0 flex-col gap-4",
          embedded ? "" : "p-4 lg:p-6",
        )}
      >
        <CostWorkbookSection
          workbook={workbook}
          isLoading={isLoadingDraft}
          error={actionError}
          emptyMessage="Cost workbook is not available. Refresh cost plan to regenerate it."
          projectId={projectId}
        />
        {!isLoadingDraft && loadedDraft ? (
          <details
            ref={draftDetailsRef}
            className="group border bg-background"
            data-testid="draft-supporting-details"
          >
            <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
              <ChevronRight
                className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90"
                aria-hidden
              />
              <span className="text-sm font-semibold">Trace &amp; QA</span>
            </summary>

            <div className="border-t p-4">
              <p className="break-all text-sm text-muted-foreground">
                {displayDraft.workspace_path}
              </p>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <MetaItem
                  label="Saved"
                  value={dateFormatter.format(new Date(displayDraft.created_at))}
                />
                <MetaItem label="Model" value={draftModelLabel(displayDraft)} />
                <MetaItem label="Runtime" value={displayDraft.runtime} />
                <MetaItem label="Workflow" value={displayDraft.workflow_type} />
                <MetaItem
                  label="Draft mode"
                  value={draftModeLabel(loadedDraft.provenance_metadata?.draft_mode)}
                />
              </dl>

              <div id="draft-workflow-trace" className="mt-4">
                <WorkflowTracePanel trace={trace} />
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-3">
                <ReferenceList title="Seed consulted" items={seed} />
                <ReferenceList title="Evidence refs" items={evidence} />
                <ReferenceList title="Context refs" items={context} />
              </div>
            </div>
          </details>
        ) : null}
      </article>
    );
  }

  return (
    <article
      className={cn(
        "flex w-full min-w-0 flex-col gap-4",
        embedded ? "" : "p-4 lg:p-6",
      )}
    >
      <section className="artifact-sheet border bg-background">
        {isLoadingDraft ? (
          <p className="p-4 text-sm text-muted-foreground" role="status">
            Loading draft content...
          </p>
        ) : !loadedDraft ? (
          <p className="p-4 text-sm text-muted-foreground">
            Draft content could not be loaded.
          </p>
        ) : (
          <div className="p-4">
            <MarkdownContent
              markdown={source}
              version={displayDraft.version}
              projectId={projectId}
              decisions={projectDecisions ?? undefined}
              projectTitle={projectTitle}
              readOnly={isAccepted || projectDecisions === null}
              changedRanges={changedRanges}
              showChanges={showChanges}
              showTraceQa={false}
              onDraftUpdated={(updated) => {
                setLoadedDraft(updated);
                onDraftUpdated(updated);
                void api.listDecisions(projectId).then(
                  (response) =>
                    setDecisionState({
                      key: decisionContextKey,
                      decisions: response.decisions,
                      error: null,
                    }),
                  () =>
                    setDecisionState({
                      key: decisionContextKey,
                      decisions: null,
                      error:
                        "Decision saved, but current decision state could not be refreshed.",
                    }),
                );
              }}
              editingRange={selectionEditRange}
              isSavingEdit={isSaving}
              editError={selectionEditRange ? actionError : null}
              onEditSelection={canEditDraft ? startSelectionEdit : undefined}
              onEditWithAi={canInstruct ? startAiEdit : undefined}
              onCancelSelectionEdit={() => {
                setSelectionEdit(null);
                setActionError(null);
              }}
              onSaveSelectionEdit={saveSelectionEdit}
            />
          </div>
        )}
      </section>

      {canInstruct && anchor ? (
        <SelectionInstructionCard
          anchor={anchor}
          sectionHeading={headingForOffset(sections, anchor.start)}
          onAdd={addInstruction}
          onDismiss={() => {
            setAnchor(null);
            window.getSelection()?.removeAllRanges();
          }}
        />
      ) : null}

      {canInstruct ? (
        <InstructionTray
          items={trayItems}
          isApplying={isApplying}
          error={applyError}
          onRemove={(id) => {
            setApplyError(null);
            writeTray(
              loadedDraft!.id,
              loadedDraft!.version,
              trayItems.filter((item) => item.id !== id),
            );
          }}
          onClearAll={() => {
            setApplyError(null);
            writeTray(loadedDraft!.id, loadedDraft!.version, []);
          }}
          onApply={() => void applyInstructions()}
        />
      ) : null}

      {workbook ? (
        <section className="artifact-workbook border bg-background">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <Table2 className="size-4 shrink-0 text-muted-foreground" aria-hidden />
              <h3 className="text-sm font-semibold">Cost workbook</h3>
            </div>
            <span className="max-w-full truncate text-xs text-muted-foreground">
              {workbook.file_name}
            </span>
          </header>
          <WorkbookGrid projectId={projectId} workbookPath={workbook.workspace_path} />
        </section>
      ) : null}

      <details
        ref={draftDetailsRef}
        className="group border bg-background"
        data-testid="draft-supporting-details"
      >
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
          <ChevronRight
            className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90"
            aria-hidden
          />
          <span className="text-sm font-semibold">Trace &amp; QA</span>
        </summary>

        <div className="border-t p-4">
          {sectionsChanged.length || evidenceChanged ? (
            <section className="mb-6 space-y-3 border-b pb-6">
              {sectionsChanged.length ? (
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">
                      What changed in v{displayDraft.version}
                    </h3>
                    {changedRanges.length ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="print:hidden"
                        onClick={() => setShowChanges((current) => !current)}
                      >
                        {showChanges ? (
                          <EyeOff className="size-4" aria-hidden />
                        ) : (
                          <Eye className="size-4" aria-hidden />
                        )}
                        {showChanges ? "Hide changes" : "Show changes"}
                      </Button>
                    ) : null}
                  </div>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {sectionsChanged.map((section) => (
                      <Badge key={section} variant="secondary">
                        {section}
                      </Badge>
                    ))}
                  </ul>
                </div>
              ) : null}
              {evidenceChanged ? (
                <EvidenceChangeStrip
                  summary={evidenceChanged}
                  onOpenTrace={openWorkflowTrace}
                />
              ) : null}
            </section>
          ) : null}
          {issueContent.qa ? (
            <section className="mb-6 border-b pb-6">
              <p className="mb-3 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                Document review
              </p>
              <MarkdownContent markdown={issueContent.qa} readOnly showTraceQa={false} />
            </section>
          ) : null}
          <p className="break-all text-sm text-muted-foreground">
            {displayDraft.workspace_path}
          </p>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <MetaItem
              label="Saved"
              value={dateFormatter.format(new Date(displayDraft.created_at))}
            />
            <MetaItem label="Model" value={draftModelLabel(displayDraft)} />
            <MetaItem label="Runtime" value={displayDraft.runtime} />
            <MetaItem label="Workflow" value={displayDraft.workflow_type} />
            <MetaItem
              label="Draft mode"
              value={draftModeLabel(loadedDraft?.provenance_metadata?.draft_mode)}
            />
          </dl>
          {actionError ? (
            <p className="mt-4 text-sm text-destructive">{actionError}</p>
          ) : null}
          {decisionLoadError ? (
            <p className="mt-3 text-sm text-destructive">{decisionLoadError}</p>
          ) : null}

          <div id="draft-workflow-trace" className="mt-4">
            <WorkflowTracePanel trace={trace} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <ReferenceList title="Seed consulted" items={seed} />
            <ReferenceList title="Evidence refs" items={evidence} />
            <ReferenceList title="Context refs" items={context} />
          </div>
        </div>
      </details>
    </article>
  );
}

function CostWorkbookSection({
  workbook,
  projectId,
  isLoading = false,
  error = null,
  emptyMessage,
}: {
  workbook: WorkbookMetadata | null;
  projectId?: string;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage: string;
}) {
  return (
    <section className="artifact-workbook overflow-hidden border bg-background">
      {error ? (
        <p className="p-4 text-sm text-destructive">{error}</p>
      ) : isLoading ? (
        <p className="p-4 text-sm text-muted-foreground" role="status">
          Loading cost workbook...
        </p>
      ) : workbook && projectId ? (
        <WorkbookGrid projectId={projectId} workbookPath={workbook.workspace_path} />
      ) : (
        <p className="p-4 text-sm text-muted-foreground">{emptyMessage}</p>
      )}
    </section>
  );
}

function isPmpDraft(workflowType: string): boolean {
  return workflowType === "create_pmp" || workflowType === "update_pmp";
}

function metadataStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

type EvidenceChangedSummary = {
  added: number;
  removed: number;
  superseded: number;
  downgraded: number;
  conflicted: number;
};

function evidenceChangedSummary(value: unknown): EvidenceChangedSummary | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Record<string, unknown>;
  const summary = {
    added: metadataStringList(candidate.added).length,
    removed: metadataStringList(candidate.removed).length,
    superseded: metadataStringList(candidate.superseded).length,
    downgraded: metadataStringList(candidate.downgraded).length,
    conflicted: metadataStringList(candidate.conflicted).length,
  };
  if (
    summary.added +
      summary.removed +
      summary.superseded +
      summary.downgraded +
      summary.conflicted ===
    0
  ) {
    return null;
  }
  return summary;
}

function EvidenceChangeStrip({
  summary,
  onOpenTrace,
}: {
  summary: EvidenceChangedSummary;
  onOpenTrace: () => void;
}) {
  const parts = [
    summary.added ? `${summary.added} added` : null,
    summary.removed ? `${summary.removed} removed` : null,
    summary.superseded ? `${summary.superseded} superseded` : null,
    summary.downgraded ? `${summary.downgraded} downgraded` : null,
    summary.conflicted ? `${summary.conflicted} conflicted` : null,
  ].filter((part): part is string => part !== null);

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="font-medium">Evidence changes:</span>
      <span className="text-muted-foreground">{parts.join(" · ")}</span>
      <Button variant="link" size="sm" className="h-auto px-0" onClick={onOpenTrace}>
        View sweep trace
      </Button>
    </div>
  );
}

function emptyDraftMessage(workflowType?: string): string {
  if (workflowType === "create_cost_plan") {
    return "No cost plan draft saved yet.";
  }
  if (workflowType === "create_pmp" || workflowType === "update_pmp") {
    return "No PMP draft saved yet.";
  }
  return "No draft saved yet.";
}

function isFullDraft(draft: DraftArtifact | DraftArtifactSummary): draft is DraftArtifact {
  return "content_markdown" in draft;
}

function draftModelLabel(draft: DraftArtifact | DraftArtifactSummary): string {
  if (isFullDraft(draft)) {
    const label = draft.provenance_metadata?.model_label;
    if (typeof label === "string" && label.trim()) {
      return label;
    }
  }
  return draft.model ?? "Unknown";
}

function draftModeLabel(value: unknown): string {
  if (value === "platform_seeded") {
    return "Platform seeded (doctrine + seed)";
  }
  if (value === "evidence_grounded") {
    return "Evidence grounded";
  }
  if (value === "baseline_refresh") {
    return "Baseline refresh";
  }
  return "Unknown";
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium" title={value}>
        {value}
      </dd>
    </div>
  );
}

function ReferenceList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-md border bg-background p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      {items.length ? (
        <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
          {items.map((item) => (
            <li key={item} className="break-all">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-muted-foreground">None recorded.</p>
      )}
    </section>
  );
}

function metadataList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function metadataTrace(value: unknown): WorkflowTraceEvent[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isTraceEvent);
}

type WorkbookMetadata = {
  file_name: string;
  workspace_path: string;
};

function workbookMetadata(value: unknown): WorkbookMetadata | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Partial<WorkbookMetadata>;
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

function isTraceEvent(value: unknown): value is WorkflowTraceEvent {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<WorkflowTraceEvent>;
  return (
    typeof candidate.step === "string" &&
    typeof candidate.status === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.metadata === "object" &&
    candidate.metadata !== null
  );
}
