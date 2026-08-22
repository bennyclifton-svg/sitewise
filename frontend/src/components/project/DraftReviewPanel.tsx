import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useInstructionTraySlot } from "@/components/project/cockpitShellLayout";
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
import { CostPlanGrid } from "@/components/project/CostPlanGrid";
import {
  PmpProgrammeFigure,
  PmpProgrammeProvider,
} from "@/components/project/PmpProgrammeEmbed";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { normalizeDraftMarkdown, splitTraceQa } from "@/lib/artifact-markdown";
import {
  deleteBlock,
  duplicateBlock,
  insertAfterBlock,
  insertBeforeBlock,
  operationForTarget,
  replaceBlock,
  type ArtifactBlockOperationType,
  type ArtifactBlockTarget,
} from "@/lib/artifact-blocks";
import { api } from "@/lib/api";
import {
  applyArtefactBlockDelta,
  type ArtefactBlockDelta,
} from "@/lib/draft-block-delta";
import { rebaseDraftBlockEdit } from "@/lib/draft-block-rebase";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";
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
import { runOptimisticMutation } from "@/lib/optimistic-mutation";
import {
  type MarkdownAnchor,
  type MarkdownRange,
} from "@/lib/markdown-selection";
import { measureLocalMutation } from "@/lib/performance";
import { expandRangeWithTrailingMarker } from "@/lib/table-row-edit";
import {
  matchTransmittalEvidenceIds,
  parseTransmittalRows,
  replaceTransmittalSection,
} from "@/lib/transmittal-register";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  EvidencePreview,
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

function blockTargetForRange(
  source: string,
  sections: MarkdownSectionSlice[],
  range: MarkdownRange,
): ArtifactBlockTarget {
  const content = editableBlockContent(
    source.slice(range.start, range.end),
  ).trimStart();
  const type = /^\|.*\|\s*$/.test(content)
    ? "table_row"
    : /^(?:[-*+]\s+|\d+[.)]\s+)/.test(content)
      ? "list_item"
      : "paragraph";
  const markerPattern = /<!--\s*clerk:block\s+id=(blk_[a-f0-9]{32})\s*-->/i;
  const embeddedMarker = source.slice(range.start, range.end).match(markerPattern);
  const precedingMarker = source
    .slice(Math.max(0, range.start - 80), range.start)
    .match(/<!--\s*clerk:block\s+id=(blk_[a-f0-9]{32})\s*-->\s*$/i);
  const marker = embeddedMarker ?? precedingMarker;
  return {
    ...(marker ? { id: marker[1] } : {}),
    type,
    range,
    sectionStart:
      sections.find(
        (section) => section.start <= range.start && range.start < section.end,
      )?.start ?? 0,
  };
}

function editableBlockContent(content: string): string {
  return content
    .replace(/<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->\s*/gi, "")
    .trimEnd();
}

function contentWithPreservedMarker(
  source: string,
  target: ArtifactBlockTarget,
  content: string,
): string {
  const raw = source.slice(target.range.start, target.range.end);
  const marker = raw.match(/<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->/i)?.[0];
  const normalized = editableBlockContent(content);
  if (!marker) return normalized;
  if (target.type === "table_row") return `${normalized}${marker}`;
  if (target.type === "list_item") return `${normalized} ${marker}`;
  return `${marker}\n${normalized}`;
}

function emptySiblingBlock(
  targetContent: string,
  type: ArtifactBlockTarget["type"],
): string {
  if (type === "list_item") {
    const marker = targetContent.match(/^\s*(?:[-*+] |\d+[.)] )/)?.[0] ?? "- ";
    return marker;
  }
  if (type === "table_row") {
    const columns = Math.max(1, targetContent.split("|").length - 2);
    return `| ${Array.from({ length: columns }, () => "").join(" | ")} |`;
  }
  return "";
}

type GenerationManifestViewModel = {
  taxonomy: Record<string, unknown>;
  known_profile: Record<string, unknown>;
  unknown_relevant_fields: string[];
  explicitly_excluded_fields: string[];
  constraints: string[];
  evidence_used: string[];
  seed_knowledge: string[];
  input_fingerprint: string;
  context_version: number | null;
  source_version: string | null;
  seed_version: string | null;
};

function generationManifestFrom(value: unknown): GenerationManifestViewModel | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.input_fingerprint !== "string") return null;
  return {
    taxonomy:
      raw.taxonomy && typeof raw.taxonomy === "object"
        ? (raw.taxonomy as Record<string, unknown>)
        : {},
    known_profile:
      raw.known_profile && typeof raw.known_profile === "object"
        ? (raw.known_profile as Record<string, unknown>)
        : {},
    unknown_relevant_fields: metadataStringList(raw.unknown_relevant_fields),
    explicitly_excluded_fields: metadataStringList(raw.explicitly_excluded_fields),
    constraints: metadataStringList(raw.constraints),
    evidence_used: metadataStringList(raw.evidence_used),
    seed_knowledge: metadataStringList(raw.seed_knowledge),
    input_fingerprint: raw.input_fingerprint,
    context_version:
      typeof raw.context_version === "number" ? raw.context_version : null,
    source_version:
      typeof raw.source_version === "string" ? raw.source_version : null,
    seed_version: typeof raw.seed_version === "string" ? raw.seed_version : null,
  };
}

function GenerationManifestView({
  manifest,
}: {
  manifest: GenerationManifestViewModel | null;
}) {
  if (!manifest) return null;
  return (
    <section className="mt-4 border-t pt-4" aria-label="Sources and context">
      <p className="text-sm font-semibold">Sources &amp; Context</p>
      <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
        <MetaItem
          label="Taxonomy"
          value={Object.entries(manifest.taxonomy)
            .map(([key, value]) => `${key}: ${String(value)}`)
            .join(" · ") || "None"}
        />
        <MetaItem
          label="Known profile facts"
          value={String(Object.keys(manifest.known_profile).length)}
        />
        <MetaItem
          label="Unknown relevant fields"
          value={manifest.unknown_relevant_fields.join(", ") || "None"}
        />
        <MetaItem
          label="Excluded fields"
          value={manifest.explicitly_excluded_fields.join(", ") || "None"}
        />
        <MetaItem
          label="Constraints"
          value={manifest.constraints.join(", ") || "None"}
        />
        <MetaItem
          label="Context version"
          value={
            manifest.context_version != null
              ? String(manifest.context_version)
              : "—"
          }
        />
        <MetaItem
          label="Source version"
          value={manifest.source_version?.slice(0, 12) || "—"}
        />
        <MetaItem
          label="Seed version"
          value={manifest.seed_version?.slice(0, 12) || "—"}
        />
        <MetaItem
          label="Input fingerprint"
          value={manifest.input_fingerprint.slice(0, 12)}
        />
      </dl>
      <div className="mt-3 grid gap-4 lg:grid-cols-2">
        <ReferenceList title="Evidence used" items={manifest.evidence_used} />
        <ReferenceList title="Seed knowledge" items={manifest.seed_knowledge} />
      </div>
    </section>
  );
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
  repositoryEvidence = [],
  selectedEvidenceIds,
  onSelectEvidenceIds,
  onTransmittalSessionChange,
  reviewInvoiceId = null,
  active = true,
}: {
  projectId: string;
  draft: DraftArtifact | DraftArtifactSummary | null;
  onDraftUpdated: (draft: DraftArtifact) => void;
  workflowType?: string;
  projectTitle?: string;
  /** Compact layout when nested inside a workflow panel. */
  embedded?: boolean;
  repositoryEvidence?: EvidencePreview[];
  selectedEvidenceIds?: Set<string>;
  onSelectEvidenceIds?: (evidenceIds: Set<string>) => void;
  onTransmittalSessionChange?: (
    session: { draftId: string; workflowType: string } | null,
  ) => void;
  reviewInvoiceId?: string | null;
  /** False while the workbench is kept mounted but hidden. */
  active?: boolean;
}) {
  const [loadedDraft, setLoadedDraft] = useState<DraftArtifact | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectionEdit, setSelectionEdit] = useState<{
    draftId: string;
    version: number;
    range: MarkdownRange;
    focusCellIndex?: number;
    caretPoint?: { x: number; y: number };
  } | null>(null);
  const [blockComposer, setBlockComposer] = useState<{
    operation: "ADD" | "UPDATE";
    target: ArtifactBlockTarget;
    placement?: "before" | "after";
    initialContent: string;
  } | null>(null);
  const [anchor, setAnchor] = useState<MarkdownAnchor | null>(null);
  const [trayOverride, setTrayOverride] = useState<{
    key: string;
    items: InstructionItem[];
  } | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [programmeHost, setProgrammeHost] = useState<HTMLElement | null>(null);
  /** Kept separate from `actionError`, which renders inside the collapsed trace. */
  const [applyError, setApplyError] = useState<string | null>(null);
  const [showChanges, setShowChanges] = useState(true);
  const [isSavingTransmittal, setIsSavingTransmittal] = useState(false);
  const [transmittalSaveError, setTransmittalSaveError] = useState<string | null>(
    null,
  );
  const draftDetailsRef = useRef<HTMLDetailsElement>(null);
  const selectionEditRef = useRef(selectionEdit);
  selectionEditRef.current = selectionEdit;
  const blockComposerRef = useRef(blockComposer);
  blockComposerRef.current = blockComposer;
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
  const instructionTraySlot = useInstructionTraySlot();
  const fallbackTrayHost = useMemo(
    () =>
      typeof document === "undefined"
        ? null
        : document.querySelector<HTMLElement>("[data-instruction-tray-host]"),
    [],
  );

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
        // Parent props can briefly regress to an older revision (event refresh,
        // summary bootstrap). Never clobber a newer local edit with older text.
        // While the user is typing, freeze the loaded body so a same-version
        // poll cannot remount the editor and wipe in-progress keystrokes.
        setLoadedDraft((current) => {
          if ((selectionEditRef.current || blockComposerRef.current) && current) {
            return current;
          }
          return preferNewerDraft(current, draft);
        });
        setIsLoadingDraft(false);
        return;
      }

      // Summary props have no markdown. Keep a matching/newer local full draft
      // instead of blanking the panel and refetching a possibly stale id.
      let shouldFetch = true;
      setLoadedDraft((current) => {
        if (
          current &&
          current.workflow_type === draft.workflow_type &&
          current.version >= draft.version
        ) {
          shouldFetch = false;
          return current;
        }
        return current;
      });
      if (!shouldFetch) {
        setIsLoadingDraft(false);
        return;
      }

      setIsLoadingDraft(true);
      try {
        const data = await queryClient.fetchQuery({
          queryKey: workbenchKeys.draft(projectId, draft.id, draft.version),
          queryFn: () => api.getProjectDraft(projectId, draft.id),
        });
        if (!cancelled) {
          setLoadedDraft((current) => preferNewerDraft(current, data));
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
        const response = await queryClient.fetchQuery({
          queryKey: workbenchKeys.decisions(projectId),
          queryFn: () => api.listDecisions(projectId),
        });
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
  const draftMarkdown = loadedDraft?.content_markdown ?? "";
  const source = useMemo(
    () => (draftMarkdown ? normalizeDraftMarkdown(draftMarkdown) : ""),
    [draftMarkdown],
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

  // The cockpit right panel owns the tray; this publishes into that slot.
  useLayoutEffect(() => {
    if (!instructionTraySlot) return;
    if (!canInstruct || !loadedDraft || trayItems.length === 0) {
      instructionTraySlot.setTray(null);
      return () => instructionTraySlot.setTray(null);
    }
    instructionTraySlot.setTray({
      items: trayItems,
      isApplying,
      error: applyError,
      onRemove: (id) => {
        setApplyError(null);
        writeTray(
          loadedDraft.id,
          loadedDraft.version,
          trayItems.filter((item) => item.id !== id),
        );
      },
      onClearAll: () => {
        setApplyError(null);
        writeTray(loadedDraft.id, loadedDraft.version, []);
      },
      onApply: () => {
        void applyInstructions();
      },
    });
    return () => instructionTraySlot.setTray(null);
  }, [
    instructionTraySlot,
    canInstruct,
    loadedDraft,
    trayItems,
    isApplying,
    applyError,
  ]);

  if (!draft) {
    if (isCostPlanWorkflow) {
      return (
        <div
          className={cn(
            embedded
              ? "rounded-md border border-dashed p-4 text-sm text-muted-foreground"
              : "flex min-h-full items-center justify-center p-6",
          )}
        >
          Create cost plan to open the editable Cost Plan grid.
        </div>
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
  const generationManifest = generationManifestFrom(
    loadedDraft?.provenance_metadata?.generation_manifest,
  );
  const isAccepted = displayDraft.status === "accepted";
  const canEditDraft =
    !isAccepted && supportsAnchoredInstructions(displayDraft.workflow_type);
  const canLoadTransmittal =
    Boolean(loadedDraft) &&
    !isAccepted &&
    Boolean(onSelectEvidenceIds) &&
    /(?:Transmittal|Project Documents|Information to review)\b/i.test(source);
  const canSaveTransmittal = canLoadTransmittal;

  function handleLoadTransmittal() {
    if (!loadedDraft || !onSelectEvidenceIds) return;
    setTransmittalSaveError(null);
    const rows = parseTransmittalRows(source);
    const matchedIds = matchTransmittalEvidenceIds(rows, repositoryEvidence);
    onSelectEvidenceIds(new Set(matchedIds));
    onTransmittalSessionChange?.({
      draftId: loadedDraft.id,
      workflowType: loadedDraft.workflow_type,
    });
  }

  async function handleSaveTransmittal() {
    if (!loadedDraft || isSavingTransmittal) return;
    const snapshot = loadedDraft;
    const evidenceIds = [...(selectedEvidenceIds ?? [])];
    const selected = evidenceIds
      .map((id) => repositoryEvidence.find((item) => item.id === id))
      .filter((item): item is EvidencePreview => item !== undefined);
    let nextMarkdown = source;
    try {
      nextMarkdown = replaceTransmittalSection(source, selected);
    } catch {
      // Server still owns the rewrite if local markdown has no register heading.
    }
    setIsSavingTransmittal(true);
    setTransmittalSaveError(null);
    try {
      const updated = await runOptimisticMutation({
        snapshot,
        optimistic: { ...snapshot, content_markdown: nextMarkdown },
        apply: setLoadedDraft,
        commit: (base) =>
          api.replaceDraftTransmittal(
            projectId,
            base.id,
            base.version,
            evidenceIds,
          ),
        confirmed: (draft) => draft,
        reload: async () =>
          (await api.getLatestDraft(projectId, snapshot.workflow_type)) ??
          snapshot,
        rebase: ({ latest }) => {
          try {
            return {
              status: "safe",
              state: {
                ...latest,
                content_markdown: replaceTransmittalSection(
                  latest.content_markdown,
                  selected,
                ),
              },
            };
          } catch {
            return { status: "unsafe" };
          }
        },
      });
      onDraftUpdated(updated);
      onTransmittalSessionChange?.(null);
    } catch (error) {
      setTransmittalSaveError(
        error instanceof ApiError
          ? error.status === 409
            ? rebaseMessage(error)
            : error.message
          : error instanceof Error
            ? error.message
            : "Could not save transmittal.",
      );
    } finally {
      setIsSavingTransmittal(false);
    }
  }

  function startSelectionEdit(
    range: MarkdownRange,
    options?: {
      focusCellIndex?: number;
      caretPoint?: { x: number; y: number };
    },
  ) {
    if (!loadedDraft) return;
    setBlockComposer(null);
    setSelectionEdit({
      draftId: loadedDraft.id,
      version: loadedDraft.version,
      range,
      ...(options?.focusCellIndex !== undefined
        ? { focusCellIndex: options.focusCellIndex }
        : {}),
      ...(options?.caretPoint ? { caretPoint: options.caretPoint } : {}),
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

    const expandedRange = expandRangeWithTrailingMarker(source, range);
    const target = blockTargetForRange(source, sections, expandedRange);
    const content = editableBlockContent(replacement);
    const canonical = { ...target, range: expandedRange };
    const nextMarkdown = replaceBlock(
      source,
      canonical,
      contentWithPreservedMarker(source, canonical, content),
    );
    if (nextMarkdown === source) {
      setSelectionEdit(null);
      return;
    }

    const snapshot = loadedDraft;
    const startedAt = performance.now();
    setIsSaving(true);
    setActionError(null);
    setSelectionEdit(null);
    let unresolvedConflict = false;
    try {
      const response = await runOptimisticMutation({
        snapshot,
        optimistic: { ...snapshot, content_markdown: nextMarkdown },
        apply: setLoadedDraft,
        commit: (base) =>
          api.applyDraftBlockOperations(projectId, base.id, base.version, [
            operationForTarget("UPDATE", canonical, { content }),
          ]),
        confirmed: (value) =>
          applyArtefactBlockDelta(
            snapshot,
            value.delta,
            nextMarkdown,
          ),
        reload: async () =>
          (await api.getLatestDraft(projectId, snapshot.workflow_type)) ?? snapshot,
        rebase: ({ snapshot: base, pending, latest }) =>
          rebaseDraftBlockEdit({
            snapshot: base,
            pending,
            latest,
            blockId: canonical.id,
            editedContent: content,
            blockType: canonical.type,
          }),
        onUnresolvedConflict: ({ pending }) => {
          unresolvedConflict = true;
          setLoadedDraft(pending);
          setActionError(
            "This draft changed elsewhere. Your edit was kept locally — resolve before saving again.",
          );
        },
      });
      measureLocalMutation("paragraph-edit", startedAt);
      const confirmed = await resolveConfirmedDraft({
        projectId,
        workflowType: snapshot.workflow_type,
        snapshot,
        delta: response.delta,
        optimisticMarkdown: nextMarkdown,
        expectedSnippet: content,
      });
      setLoadedDraft(confirmed.draft);
      if (confirmed.warning) setActionError(confirmed.warning);
      onDraftUpdated(confirmed.draft);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        if (!unresolvedConflict) setActionError(rebaseMessage(error));
      } else {
        setActionError(
          error instanceof ApiError ? error.message : "Could not save selection.",
        );
      }
    } finally {
      setIsSaving(false);
    }
  }

  function canonicalBlockTarget(target: ArtifactBlockTarget): ArtifactBlockTarget {
    const expanded = expandRangeWithTrailingMarker(source, target.range);
    const resolved = blockTargetForRange(source, sections, expanded);
    return {
      ...resolved,
      // Keep the caller's type when marker sniffing is ambiguous on empty inserts.
      type: target.type || resolved.type,
      sectionStart: target.sectionStart || resolved.sectionStart,
    };
  }

  function openBlockOperation(
    operation:
      | "ADD"
      | "DELETE"
      | "DUPLICATE"
      | "PROTECT"
      | "UNPROTECT"
      | "KEEP"
      | "CONFIRM_DELETE",
    target: ArtifactBlockTarget,
    placement?: "before" | "after",
  ) {
    const canonical = canonicalBlockTarget(target);
    if (operation === "ADD") {
      setBlockComposer({
        operation,
        target: canonical,
        placement,
        initialContent: emptySiblingBlock(
          source.slice(canonical.range.start, canonical.range.end),
          canonical.type,
        ),
      });
      return;
    }
    void mutateBlock(operation, canonical);
  }

  function protectedBlockIds(): Set<string> {
    const blocks = loadedDraft?.provenance_metadata?.blocks;
    if (!blocks || typeof blocks !== "object") return new Set();
    return new Set(
      Object.entries(blocks as Record<string, unknown>)
        .filter(([, value]) => {
          return (
            value !== null &&
            typeof value === "object" &&
            (value as { user_protected?: unknown }).user_protected === true
          );
        })
        .map(([id]) => id),
    );
  }

  function reviewBlockStatuses(): Map<string, "conflict" | "propose_delete"> {
    const blocks = loadedDraft?.provenance_metadata?.blocks;
    const statuses = new Map<string, "conflict" | "propose_delete">();
    if (!blocks || typeof blocks !== "object") return statuses;
    for (const [id, value] of Object.entries(blocks as Record<string, unknown>)) {
      if (!value || typeof value !== "object") continue;
      const status = (value as { status?: unknown }).status;
      if (status === "conflict" || status === "propose_delete") {
        statuses.set(id, status);
      }
    }
    return statuses;
  }

  function optimisticProtectProvenance(
    draft: DraftArtifact,
    blockId: string | undefined,
    protectedFlag: boolean,
  ): DraftArtifact["provenance_metadata"] {
    if (!blockId) return draft.provenance_metadata;
    const existing =
      draft.provenance_metadata && typeof draft.provenance_metadata === "object"
        ? draft.provenance_metadata
        : {};
    const blocks =
      existing.blocks && typeof existing.blocks === "object"
        ? { ...(existing.blocks as Record<string, unknown>) }
        : {};
    const prior =
      blocks[blockId] && typeof blocks[blockId] === "object"
        ? (blocks[blockId] as Record<string, unknown>)
        : { id: blockId };
    blocks[blockId] = { ...prior, user_protected: protectedFlag };
    return { ...existing, blocks };
  }

  function optimisticReviewProvenance(
    draft: DraftArtifact,
    blockId: string | undefined,
    operation: "KEEP" | "CONFIRM_DELETE",
  ): DraftArtifact["provenance_metadata"] {
    if (!blockId) return draft.provenance_metadata;
    const existing =
      draft.provenance_metadata && typeof draft.provenance_metadata === "object"
        ? draft.provenance_metadata
        : {};
    const blocks =
      existing.blocks && typeof existing.blocks === "object"
        ? { ...(existing.blocks as Record<string, unknown>) }
        : {};
    if (operation === "CONFIRM_DELETE") {
      delete blocks[blockId];
      return { ...existing, blocks };
    }
    const prior =
      blocks[blockId] && typeof blocks[blockId] === "object"
        ? (blocks[blockId] as Record<string, unknown>)
        : { id: blockId };
    blocks[blockId] = { ...prior, status: "active" };
    return { ...existing, blocks };
  }

  async function mutateBlock(
    operation: ArtifactBlockOperationType,
    target: ArtifactBlockTarget,
    content?: string,
    placement?: "before" | "after",
  ) {
    if (!loadedDraft) return;
    const snapshot = loadedDraft;
    const canonical = canonicalBlockTarget(target);
    const nextMarkdown =
      operation === "UPDATE"
        ? replaceBlock(
            source,
            canonical,
            contentWithPreservedMarker(source, canonical, content ?? ""),
          )
        : operation === "ADD" && placement === "before"
          ? insertBeforeBlock(source, canonical, content ?? "")
          : operation === "ADD"
            ? insertAfterBlock(source, canonical, content ?? "")
            : operation === "DUPLICATE"
              ? duplicateBlock(source, canonical)
              : operation === "DELETE" || operation === "CONFIRM_DELETE"
                ? deleteBlock(source, canonical)
                : source;
    const optimistic: DraftArtifact = {
      ...snapshot,
      content_markdown: nextMarkdown,
      provenance_metadata:
        operation === "PROTECT" || operation === "UNPROTECT"
          ? optimisticProtectProvenance(
              snapshot,
              canonical.id,
              operation === "PROTECT",
            )
          : operation === "KEEP" || operation === "CONFIRM_DELETE"
            ? optimisticReviewProvenance(snapshot, canonical.id, operation)
            : snapshot.provenance_metadata,
    };
    setBlockComposer(null);
    setIsSaving(true);
    setActionError(null);
    let unresolvedConflict = false;
    try {
      const response = await runOptimisticMutation({
        snapshot,
        optimistic,
        apply: setLoadedDraft,
        commit: (base) =>
          api.applyDraftBlockOperations(projectId, base.id, base.version, [
            operationForTarget(operation, canonical, { content, placement }),
          ]),
        confirmed: (value) =>
          applyArtefactBlockDelta(
            snapshot,
            value.delta,
            optimistic.content_markdown,
          ),
        reload: async () =>
          (await api.getLatestDraft(projectId, snapshot.workflow_type)) ?? snapshot,
        rebase: ({ snapshot: base, pending, latest }) =>
          rebaseDraftBlockEdit({
            snapshot: base,
            pending,
            latest,
            blockId: canonical.id,
            editedContent:
              operation === "UPDATE" ? editableBlockContent(content ?? "") : undefined,
            blockType: canonical.type,
          }),
        onUnresolvedConflict: ({ pending }) => {
          unresolvedConflict = true;
          setLoadedDraft(pending);
          setActionError(
            "This draft changed elsewhere. Your edit was kept locally — resolve before saving again.",
          );
        },
      });
      const confirmed = await resolveConfirmedDraft({
        projectId,
        workflowType: snapshot.workflow_type,
        snapshot,
        delta: response.delta,
        optimisticMarkdown: optimistic.content_markdown,
        expectedSnippet: content,
      });
      setLoadedDraft(confirmed.draft);
      if (confirmed.warning) setActionError(confirmed.warning);
      onDraftUpdated(confirmed.draft);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        if (!unresolvedConflict) setActionError(rebaseMessage(error));
      } else {
        setActionError(
          error instanceof ApiError ? error.message : "Could not update this block.",
        );
      }
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
        <CostPlanGrid
          projectId={projectId}
          revision={displayDraft.version}
          reviewInvoiceId={reviewInvoiceId}
          active={active}
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
              <span className="ml-auto text-xs text-muted-foreground">
                Sources &amp; Context
              </span>
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
              <GenerationManifestView manifest={generationManifest} />
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
          <PmpProgrammeProvider projectId={projectId}>
          <div className="p-4" ref={setProgrammeHost}>
            {actionError ? (
              <p
                className="mb-3 border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                role="alert"
              >
                {actionError}
              </p>
            ) : null}
            {(() => {
              const reviews = reviewBlockStatuses();
              if (reviews.size === 0) return null;
              let conflicts = 0;
              let proposedDeletes = 0;
              for (const status of reviews.values()) {
                if (status === "conflict") conflicts += 1;
                if (status === "propose_delete") proposedDeletes += 1;
              }
              return (
                <p
                  className="mb-3 border border-amber-600/30 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-50"
                  role="status"
                >
                  Refresh review needed:
                  {conflicts
                    ? ` ${conflicts} conflict${conflicts === 1 ? "" : "s"}`
                    : ""}
                  {conflicts && proposedDeletes ? "," : ""}
                  {proposedDeletes
                    ? ` ${proposedDeletes} proposed deletion${
                        proposedDeletes === 1 ? "" : "s"
                      }`
                    : ""}
                  . Keep or confirm delete on the highlighted blocks.
                </p>
              );
            })()}
            <MarkdownContent
              markdown={source}
              version={displayDraft.version}
              hideLeadingHeading={isProcurementDraft(displayDraft.workflow_type)}
              hideProgrammeSectionBody={isPmpDraft(displayDraft.workflow_type)}
              projectId={projectId}
              decisions={projectDecisions ?? undefined}
              projectTitle={projectTitle}
              // Keep the document editable while PMP decisions load. Tying
              // readOnly to `projectDecisions === null` remounted markdown when
              // the fetch settled and closed open block-action menus mid-click.
              readOnly={isAccepted}
              changedRanges={changedRanges}
              showChanges={showChanges}
              showTraceQa={false}
              onDraftUpdated={(updated) => {
                setLoadedDraft(updated);
                onDraftUpdated(updated);
                void queryClient
                  .fetchQuery({
                    queryKey: workbenchKeys.decisions(projectId),
                    queryFn: () => api.listDecisions(projectId),
                    staleTime: 0,
                  })
                  .then(
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
              editingFocusCellIndex={selectionEdit?.focusCellIndex}
              editingCaretPoint={selectionEdit?.caretPoint}
              isSavingEdit={isSaving}
              editError={selectionEditRange ? actionError : null}
              blockComposer={blockComposer}
              isSavingBlockComposer={isSaving}
              onEditSelection={canEditDraft ? startSelectionEdit : undefined}
              onEditWithAi={canInstruct ? startAiEdit : undefined}
              onCancelSelectionEdit={() => {
                setSelectionEdit(null);
                setActionError(null);
              }}
              onSaveSelectionEdit={saveSelectionEdit}
              onCancelBlockComposer={() => setBlockComposer(null)}
              onSaveBlockComposer={(content) => {
                if (!blockComposer) return;
                if (!content.trim()) {
                  setBlockComposer(null);
                  return;
                }
                void mutateBlock(
                  blockComposer.operation,
                  blockComposer.target,
                  content,
                  blockComposer.placement,
                );
              }}
              onMutateBlock={canEditDraft ? openBlockOperation : undefined}
              protectedBlockIds={canEditDraft ? protectedBlockIds() : undefined}
              reviewBlockStatuses={
                canEditDraft ? reviewBlockStatuses() : undefined
              }
              canLoadTransmittal={canLoadTransmittal}
              onLoadTransmittal={
                canLoadTransmittal ? handleLoadTransmittal : undefined
              }
              canSaveTransmittal={canSaveTransmittal}
              onSaveTransmittal={
                canSaveTransmittal ? () => void handleSaveTransmittal() : undefined
              }
              isSavingTransmittal={isSavingTransmittal}
              transmittalSaveError={transmittalSaveError}
            />
            {isPmpDraft(displayDraft.workflow_type) ? (
              <PmpProgrammeFigure host={programmeHost} contentKey={source} />
            ) : null}
          </div>
          </PmpProgrammeProvider>
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

      {canInstruct
        ? renderInstructionTray(
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
            />,
            instructionTraySlot,
            fallbackTrayHost,
          )
        : null}

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
          <span className="ml-auto text-xs text-muted-foreground">
            Sources &amp; Context
          </span>
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
          {decisionLoadError ? (
            <p className="mt-3 text-sm text-destructive" role="alert">
              {decisionLoadError}
            </p>
          ) : null}

          <div id="draft-workflow-trace" className="mt-4">
            <WorkflowTracePanel trace={trace} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <ReferenceList title="Seed consulted" items={seed} />
            <ReferenceList title="Evidence refs" items={evidence} />
            <ReferenceList title="Context refs" items={context} />
          </div>
          <GenerationManifestView manifest={generationManifest} />
        </div>
      </details>
    </article>
  );
}

function isPmpDraft(workflowType: string): boolean {
  return workflowType === "create_pmp" || workflowType === "update_pmp";
}

function isProcurementDraft(workflowType: string): boolean {
  return (
    workflowType.startsWith("consultant_procurement_") ||
    workflowType.startsWith("trade_rft_") ||
    workflowType.startsWith("trade_rfq_")
  );
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

/** Right-panel slot from ProjectShell; portal/inline covers tests without the shell. */
function renderInstructionTray(
  tray: ReactNode,
  slot: object | null,
  fallbackHost: HTMLElement | null,
): ReactNode {
  if (slot) return null;
  return fallbackHost ? createPortal(tray, fallbackHost) : tray;
}

function isFullDraft(draft: DraftArtifact | DraftArtifactSummary): draft is DraftArtifact {
  return "content_markdown" in draft;
}

/**
 * Prefer newer revisions. Same-version bodies are treated as immutable: if the
 * parent/event poll races with a local confirm and returns divergent markdown,
 * keep the local copy instead of silently discarding the user's edit.
 */
function preferNewerDraft(
  current: DraftArtifact | null,
  incoming: DraftArtifact,
): DraftArtifact {
  if (!current) return incoming;
  if (current.workflow_type !== incoming.workflow_type) return incoming;
  if (current.version > incoming.version) return current;
  if (current.version < incoming.version) return incoming;
  // Same revision: keep the local object so parent polls do not change
  // identity and remount inline editors mid-keystroke.
  return current;
}

/** After a lean delta confirm, adopt the persisted draft body when available. */
async function resolveConfirmedDraft(args: {
  projectId: string;
  workflowType: string;
  snapshot: DraftArtifact;
  delta: ArtefactBlockDelta;
  optimisticMarkdown: string;
  expectedSnippet?: string;
}): Promise<{ draft: DraftArtifact; warning: string | null }> {
  const fallback = applyArtefactBlockDelta(
    args.snapshot,
    args.delta,
    args.optimisticMarkdown,
  );
  try {
    const latest = await api.getLatestDraft(args.projectId, args.workflowType);
    if (!latest || latest.version !== args.delta.version) {
      return { draft: fallback, warning: null };
    }
    const snippet = args.expectedSnippet?.trim();
    if (snippet && !latest.content_markdown.includes(snippet)) {
      return {
        draft: fallback,
        warning:
          "The server draft is missing this change. Your edit was kept locally — retry save or refresh carefully.",
      };
    }
    return { draft: latest, warning: null };
  } catch {
    return { draft: fallback, warning: null };
  }
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
