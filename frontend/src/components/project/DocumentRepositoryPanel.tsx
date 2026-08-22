import {
  Activity,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  FolderTree,
  Folders,
  Inbox,
  Loader2,
  LoaderCircle,
  TableProperties,
  Trash,
  Upload,
} from "lucide-react";
import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type MouseEvent,
} from "react";

import { ActivityFeed } from "@/components/project/ActivityFeed";
import { attentionHeadline, PulsePanel } from "@/components/project/PulsePanel";
import {
  IngestProgressStrip,
  type IngestUploadProgress,
} from "@/components/project/IngestProgressStrip";
import { NavAccordionSection } from "@/components/project/NavAccordionSection";
import {
  PlatformKnowledgePanel,
  PlatformKnowledgeSummary,
} from "@/components/project/PlatformKnowledgePanel";
import { WorkspaceExplorer } from "@/components/project/WorkspaceExplorer";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { documentCategoryLabel } from "@/lib/classification";
import { ApiError } from "@/lib/http";
import { IngestBatchEstimator, type IngestBatchSnapshot } from "@/lib/ingest-progress";
import { MARKDOWN_EXTENSIONS } from "@/lib/markdown";
import {
  useBatchDeleteEvidence,
  useDeleteDraft,
  useDeleteEvidence,
} from "@/lib/queries/project-data";
import type { ProjectEmailDraft, ProjectEmailMessage } from "@/lib/types/email";
import type {
  PulseAction,
  PulseFeed,
  PulseItem,
  PulseSincePreset,
} from "@/lib/types/pulse";
import type {
  DeleteDraftResponse,
  DocumentUsageMark,
  DraftArtifactSummary,
  EvidencePreview,
  InboxUploadResult,
  PdfAnalyzeResult,
  PlatformKnowledgeDocument,
  PlatformKnowledgeStatus,
  WorkspaceTreeNode,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

const COMPLETION_MESSAGE_MS = 2_000;

const SUPPORTED_INBOX_EXTENSIONS = new Set([
  ".pdf",
  ".docx",
  ".rtf",
  ...MARKDOWN_EXTENSIONS,
]);
const ACCEPT_ATTRIBUTE = Array.from(SUPPORTED_INBOX_EXTENSIONS).join(",");

/** Ghost Button merges className before twMerge, so hover needs ! to win. */
const toolbarIconButtonClass =
  "text-[var(--cockpit-workflow-icon)] hover:!bg-[color-mix(in_oklch,var(--sw-beam)_12%,transparent)] hover:!text-[var(--cockpit-workflow-icon)]";
const toolbarIconButtonActiveClass =
  "bg-[color-mix(in_oklch,var(--sw-beam)_10%,transparent)]";

type SplitProposal = {
  sourceFile: File;
  analysis: PdfAnalyzeResult;
};

type RepositoryPanelView = "schedule" | "tree";
type RepositoryTreeSectionId = "activity" | "skills" | "knowledge" | "admin";
type SelectionUpdater = Set<string> | ((current: Set<string>) => Set<string>);
type ScheduleSortKey = "document_number" | "title" | "revision" | "category";
type SortDirection = "asc" | "desc";

type PendingUploadStage = "queued" | "uploading" | "ingesting";

type PendingUpload = {
  id: string;
  filename: string;
  stage: PendingUploadStage;
  uploadPercent: number | null;
};

type UploadEntry = {
  uid: string;
  file: File;
};

type IngestQueueItem =
  | { kind: "file"; uid: string; file: File }
  | { kind: "staged"; uid: string; stagingId: string; filename: string };

type ScheduleRow =
  | { kind: "artefact"; id: string; draft: DraftArtifactSummary; title: string }
  | { kind: "source"; id: string; evidence: EvidencePreview; title: string };

function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".pdf");
}

function pendingUploadId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

function pendingStageLabel(pending: PendingUpload): string {
  switch (pending.stage) {
    case "queued":
      return "Queued";
    case "uploading":
      return pending.uploadPercent !== null &&
        pending.uploadPercent > 0 &&
        pending.uploadPercent < 100
        ? `Uploading ${pending.uploadPercent}%`
        : "Uploading…";
    case "ingesting":
      return "Ingesting…";
  }
}

export function DocumentRepositoryPanel({
  projectId,
  evidence,
  selectedEvidenceId,
  selectedEvidenceIds,
  workspaceTree,
  selectedWorkspacePath,
  onSelectEvidence,
  onSelectedEvidenceIdsChange,
  onSelectWorkspacePath,
  onOpenWorkflow,
  onViewWorkbench,
  onViewFolder,
  onUploadComplete,
  onRunSortFiles,
  isRunningSortFiles = false,
  overlayReady = true,
  pulseFeed = null,
  pulseSincePreset = "7d",
  onPulseSinceChange,
  onPulseAction,
  pulseEmailDraft = null,
  pulseEmailSending = false,
  onSendPulseEmailDraft,
  pulseEmailThread = null,
  platformStatus = null,
  selectedPlatformKnowledgePath = null,
  onSelectPlatformKnowledge,
  artefactDrafts = [],
  onOpenDraft,
  onArtefactDeleted,
  usageHighlightArtefactId = null,
  transmittalCuration = false,
}: {
  projectId: string;
  evidence: EvidencePreview[];
  selectedEvidenceId: string | null;
  selectedEvidenceIds?: Set<string>;
  workspaceTree: WorkspaceTreeNode[];
  selectedWorkspacePath: string | null;
  onSelectEvidence: (evidenceId: string) => void;
  onSelectedEvidenceIdsChange?: (evidenceIds: Set<string>) => void;
  onSelectWorkspacePath: (path: string) => void;
  onOpenWorkflow: (tileId: string) => void;
  onViewWorkbench: () => void;
  onViewFolder: () => void;
  onUploadComplete: (outcomes?: InboxUploadResult[]) => Promise<void>;
  onRunSortFiles?: () => void;
  isRunningSortFiles?: boolean;
  overlayReady?: boolean;
  pulseFeed?: PulseFeed | null;
  pulseSincePreset?: PulseSincePreset;
  onPulseSinceChange?: (preset: PulseSincePreset) => void;
  onPulseAction?: (item: PulseItem, action: PulseAction) => void;
  pulseEmailDraft?: ProjectEmailDraft | null;
  pulseEmailSending?: boolean;
  onSendPulseEmailDraft?: () => void;
  pulseEmailThread?: ProjectEmailMessage[] | null;
  platformStatus?: PlatformKnowledgeStatus | null;
  selectedPlatformKnowledgePath?: string | null;
  onSelectPlatformKnowledge?: (document: PlatformKnowledgeDocument) => void;
  artefactDrafts?: DraftArtifactSummary[];
  onOpenDraft?: (draft: DraftArtifactSummary) => void;
  onArtefactDeleted?: (result: DeleteDraftResponse) => void;
  /** When set, show source-doc dots only for this displayed artefact (e.g. open PMP). */
  usageHighlightArtefactId?: string | null;
  /** Additive row clicks while curating an RFP/PMP transmittal schedule. */
  transmittalCuration?: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const deleteEvidence = useDeleteEvidence(projectId);
  const batchDeleteEvidence = useBatchDeleteEvidence(projectId);
  const deleteDraft = useDeleteDraft(projectId);
  const [activePanelView, setActivePanelView] =
    useState<RepositoryPanelView>("schedule");
  const [openTreeSections, setOpenTreeSections] = useState<Set<RepositoryTreeSectionId>>(
    () => new Set(["activity", "admin"]),
  );
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<IngestUploadProgress | null>(null);
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const estimatorRef = useRef<IngestBatchEstimator | null>(null);
  const queuedUploadBatchesRef = useRef<UploadEntry[][]>([]);
  const isProcessingUploadsRef = useRef(false);
  const [splitProposals, setSplitProposals] = useState<SplitProposal[]>([]);
  const [resolvingStagingId, setResolvingStagingId] = useState<string | null>(null);
  const [internalSelectedIds, setInternalSelectedIds] = useState<Set<string>>(
    () => new Set<string>(),
  );
  const [selectionAnchorId, setSelectionAnchorId] = useState<string | null>(null);
  const [bulkDeletingIds, setBulkDeletingIds] = useState<Set<string>>(
    () => new Set<string>(),
  );
  const [sortKey, setSortKey] = useState<ScheduleSortKey>("document_number");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [pulseOpen, setPulseOpen] = useState(false);
  const dragDepthRef = useRef(0);
  const scheduleRows = useMemo<ScheduleRow[]>(
    () =>
      sortScheduleRows(
        [
          ...artefactDrafts
            .filter((draft) => draft.workflow_type !== "sort_files")
            .map((draft) => ({
              kind: "artefact" as const,
              id: draft.id,
              draft,
              title: abbreviateArtefactTitle(draft.title),
            })),
          ...evidence.map((item) => ({
            kind: "source" as const,
            id: item.id,
            evidence: item,
            title: item.title,
          })),
        ],
        sortKey,
        sortDirection,
      ),
    [artefactDrafts, evidence, sortDirection, sortKey],
  );
  const scheduleRowIds = useMemo(
    () => new Set(scheduleRows.map((row) => row.id)),
    [scheduleRows],
  );

  function handleSortHeaderClick(key: ScheduleSortKey) {
    if (sortKey === key) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection("asc");
  }
  const selectedIds = selectedEvidenceIds ?? internalSelectedIds;
  const selectedScheduleRows = useMemo(
    () => scheduleRows.filter((row) => selectedIds.has(row.id)),
    [scheduleRows, selectedIds],
  );
  const inboxCount = useMemo(
    () => evidence.filter((item) => isInboxEvidence(item)).length,
    [evidence],
  );

  const getBatchSnapshot = useCallback(
    (): IngestBatchSnapshot =>
      estimatorRef.current?.snapshot() ?? { fraction: 0, etaSeconds: null },
    [],
  );

  function patchPendingUpload(id: string, patch: Partial<PendingUpload>) {
    setPendingUploads((current) =>
      current.map((pending) =>
        pending.id === id ? { ...pending, ...patch } : pending,
      ),
    );
  }

  function removePendingUpload(id: string) {
    setPendingUploads((current) => current.filter((pending) => pending.id !== id));
  }

  function toggleTreeSection(id: RepositoryTreeSectionId) {
    setOpenTreeSections((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  const isDeletingSelection = bulkDeletingIds.size > 0;

  function setSelectedIds(updater: SelectionUpdater) {
    const current = new Set(selectedIds);
    const updated = typeof updater === "function" ? updater(current) : updater;
    const next = new Set([...updated].filter((id) => scheduleRowIds.has(id)));
    if (onSelectedEvidenceIdsChange) {
      onSelectedEvidenceIdsChange(next);
    } else {
      setInternalSelectedIds(next);
    }
  }

  function activateScheduleRow(row: ScheduleRow) {
    if (row.kind === "artefact") {
      onOpenDraft?.(row.draft);
      return;
    }
    onSelectEvidence(row.id);
  }

  function handleDragEnter(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    dragDepthRef.current += 1;
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDragging(false);
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDragging(false);
    const dropped = [...event.dataTransfer.files];
    if (dropped.length) {
      queueFilesForUpload(dropped);
    }
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files ? [...event.target.files] : [];
    event.target.value = "";
    if (selected.length) {
      queueFilesForUpload(selected);
    }
  }

  function handleRowClick(
    event: MouseEvent<HTMLTableRowElement>,
    row: ScheduleRow,
  ) {
    // During Transmittal curation, plain clicks should add/remove without
    // replacing the whole selection (Ctrl/Cmd still works the same way).
    const additive =
      event.ctrlKey || event.metaKey || transmittalCuration;

    if (event.shiftKey) {
      const anchorId =
        selectionAnchorId && scheduleRowIds.has(selectionAnchorId)
          ? selectionAnchorId
          : selectedEvidenceId && scheduleRowIds.has(selectedEvidenceId)
            ? selectedEvidenceId
            : row.id;
      const anchorIndex = scheduleRows.findIndex((item) => item.id === anchorId);
      const rowIndex = scheduleRows.findIndex((item) => item.id === row.id);
      if (anchorIndex >= 0 && rowIndex >= 0) {
        const start = Math.min(anchorIndex, rowIndex);
        const end = Math.max(anchorIndex, rowIndex);
        const rangeIds = scheduleRows.slice(start, end + 1).map((item) => item.id);
        setSelectedIds((current) => {
          const next = additive
            ? new Set([...current].filter((id) => scheduleRowIds.has(id)))
            : new Set<string>();
          for (const id of rangeIds) next.add(id);
          return next;
        });
        activateScheduleRow(row);
        return;
      }
    }

    if (additive) {
      setSelectedIds((current) => {
        const next = new Set([...current].filter((id) => scheduleRowIds.has(id)));
        if (next.has(row.id)) {
          next.delete(row.id);
        } else {
          next.add(row.id);
        }
        return next;
      });
    } else {
      setSelectedIds(new Set([row.id]));
    }
    setSelectionAnchorId(row.id);
    activateScheduleRow(row);
  }

  async function handleDeleteEvidence(row: EvidencePreview) {
    const confirmed = window.confirm(
      `Delete "${row.title}"? This removes it from the document repository and cannot be undone.`,
    );
    if (!confirmed) return;

    setUploadError(null);
    try {
      // Optimistic: the row is removed from the cached list immediately; the
      // network round-trip runs in the background and rolls back on failure.
      await deleteEvidence.mutateAsync(row.id);
      setSelectedIds((current) => {
        if (!current.has(row.id)) return current;
        const next = new Set(current);
        next.delete(row.id);
        return next;
      });
      setSelectionAnchorId((current) => (current === row.id ? null : current));
    } catch (error) {
      const detail =
        error instanceof ApiError ? error.message : "Please try again.";
      setUploadError(`Could not delete "${row.title}": ${detail}`);
    }
  }

  async function handleDeleteArtefact(draft: DraftArtifactSummary) {
    const title = abbreviateArtefactTitle(draft.title);
    const confirmed = window.confirm(
      `Delete "${title}"? This removes it from the document repository and cannot be undone.`,
    );
    if (!confirmed) return;

    setUploadError(null);
    setBulkDeletingIds((current) => new Set(current).add(draft.id));
    try {
      const result = await deleteDraft.mutateAsync(draft.id);
      onArtefactDeleted?.(result);
      setSelectedIds((current) => {
        if (!current.has(draft.id)) return current;
        const next = new Set(current);
        next.delete(draft.id);
        return next;
      });
      setSelectionAnchorId((current) => (current === draft.id ? null : current));
    } catch (error) {
      const detail =
        error instanceof ApiError ? error.message : "Please try again.";
      setUploadError(`Could not delete "${title}": ${detail}`);
    } finally {
      setBulkDeletingIds((current) => {
        const next = new Set(current);
        next.delete(draft.id);
        return next;
      });
    }
  }

  async function handleDeleteSelected() {
    if (!selectedScheduleRows.length) return;

    const count = selectedScheduleRows.length;
    const confirmed = window.confirm(
      `Delete ${count} selected ${count === 1 ? "document" : "documents"}? This removes ${count === 1 ? "it" : "them"} from the document repository and cannot be undone.`,
    );
    if (!confirmed) return;

    setUploadError(null);
    setBulkDeletingIds(new Set(selectedScheduleRows.map((row) => row.id)));

    const failedIds = new Set<string>();
    const errors: string[] = [];
    const selectedEvidence = selectedScheduleRows.flatMap((row) =>
      row.kind === "source" ? [row.evidence] : [],
    );
    const selectedArtefacts = selectedScheduleRows.flatMap((row) =>
      row.kind === "artefact" ? [row.draft] : [],
    );

    if (selectedEvidence.length) {
      try {
        const result = await batchDeleteEvidence.mutateAsync(
          selectedEvidence.map((row) => row.id),
        );
        for (const failure of result.failed) {
          failedIds.add(failure.evidence_id);
        }
        if (result.failed.length) {
          const titles = new Map(selectedEvidence.map((row) => [row.id, row.title]));
          errors.push(
            ...result.failed.map(
              (failure) =>
                `${titles.get(failure.evidence_id) ?? "Document"}: ${failure.detail}`,
            ),
          );
        }
      } catch (error) {
        selectedEvidence.forEach((row) => failedIds.add(row.id));
        errors.push(
          error instanceof ApiError
            ? error.message
            : "Could not delete the selected documents.",
        );
      }
    }

    for (const draft of selectedArtefacts) {
      try {
        const result = await deleteDraft.mutateAsync(draft.id);
        onArtefactDeleted?.(result);
      } catch (error) {
        failedIds.add(draft.id);
        const detail =
          error instanceof ApiError ? error.message : "Please try again.";
        errors.push(`${abbreviateArtefactTitle(draft.title)}: ${detail}`);
      }
    }

    setBulkDeletingIds(new Set<string>());
    if (errors.length) {
      setUploadError(errors.join("; "));
    }
    setSelectedIds(failedIds);
    setSelectionAnchorId(failedIds.values().next().value ?? null);
  }

  async function resolveSplit(proposal: SplitProposal, mode: "split" | "single") {
    setResolvingStagingId(proposal.analysis.staging_id);
    setUploadError(null);
    try {
      let outcomes: InboxUploadResult[];
      if (mode === "split") {
        outcomes = await api.splitStagedPdf(
          projectId,
          proposal.analysis.staging_id,
          proposal.sourceFile.name,
        );
      } else {
        outcomes = await api.commitStagedPdf(
          projectId,
          proposal.analysis.staging_id,
          proposal.sourceFile.name,
        );
      }
      setSplitProposals((current) =>
        current.filter(
          (item) => item.analysis.staging_id !== proposal.analysis.staging_id,
        ),
      );
      await onUploadComplete(outcomes);
    } catch (error) {
      setUploadError(
        `Could not process "${proposal.sourceFile.name}": ${formatUploadError(error)}`,
      );
    } finally {
      setResolvingStagingId(null);
    }
  }

  function queueFilesForUpload(files: File[]) {
    setUploadError(null);

    const { accepted, rejected } = partitionSupportedFiles(files);
    if (rejected.length) {
      setUploadError(
        `Unsupported file type: ${rejected.join(", ")}. Supported: ${[...SUPPORTED_INBOX_EXTENSIONS].join(", ")}`,
      );
    }
    if (!accepted.length) return;

    // Every accepted file is acknowledged in the register immediately. Batches
    // wait their turn so shared progress state always belongs to one batch.
    const entries: UploadEntry[] = accepted.map((file) => ({ uid: pendingUploadId(), file }));
    queuedUploadBatchesRef.current.push(entries);
    setPendingUploads((current) => [
      ...current,
      ...entries.map((entry) => ({
        id: entry.uid,
        filename: entry.file.name,
        stage: "queued" as const,
        uploadPercent: null,
      })),
    ]);
    void processQueuedUploadBatches();
  }

  async function processQueuedUploadBatches() {
    if (isProcessingUploadsRef.current) return;

    isProcessingUploadsRef.current = true;
    setIsUploading(true);
    try {
      while (queuedUploadBatchesRef.current.length) {
        const entries = queuedUploadBatchesRef.current.shift();
        if (entries) await uploadFilesBatch(entries);
      }
    } finally {
      isProcessingUploadsRef.current = false;
      setIsUploading(false);
      setUploadProgress(null);
      estimatorRef.current = null;
    }
  }

  async function uploadFilesBatch(entries: UploadEntry[]) {
    const estimator = new IngestBatchEstimator(
      entries.map((entry) => ({ id: entry.uid, sizeBytes: entry.file.size })),
    );
    estimatorRef.current = estimator;

    let total = entries.length;
    let completed = 0;
    let failedCount = 0;
    const setStrip = (
      currentFilename: string | null,
      stage: IngestUploadProgress["stage"],
    ) =>
      setUploadProgress({ total, completed, currentFilename, stage, failedCount });
    setStrip(entries[0]?.file.name ?? null, null);

    const queue: IngestQueueItem[] = [];
    const failedResults: InboxUploadResult[] = [];
    const completedResults: InboxUploadResult[] = [];
    const uploadErrors: string[] = [];
    const analyzeErrors: string[] = [];

    try {
      // Phase 1 — analyzing a PDF uploads its bytes to staging, so this is the
      // real upload for PDFs. Drawing sets divert to split proposals; other
      // PDFs are ingested from staging later without a second upload.
      await runWithConcurrency(entries, 2, async (entry) => {
        if (!isPdfFile(entry.file)) {
          queue.push({ kind: "file", uid: entry.uid, file: entry.file });
          return;
        }
        patchPendingUpload(entry.uid, { stage: "uploading" });
        setStrip(entry.file.name, "uploading");
        try {
          const analysis = await api.analyzePdf(projectId, entry.file, (loaded, size) => {
            estimator.uploadProgress(entry.uid, loaded);
            patchPendingUpload(entry.uid, {
              uploadPercent: size > 0 ? Math.round((loaded / size) * 100) : null,
            });
          });
          if (analysis.is_drawing_set) {
            estimator.removeFile(entry.uid);
            removePendingUpload(entry.uid);
            total -= 1;
            setSplitProposals((current) => [
              ...current,
              { sourceFile: entry.file, analysis },
            ]);
          } else {
            estimator.uploadProgress(entry.uid, entry.file.size);
            patchPendingUpload(entry.uid, { stage: "queued", uploadPercent: null });
            queue.push({
              kind: "staged",
              uid: entry.uid,
              stagingId: analysis.staging_id,
              filename: entry.file.name,
            });
          }
        } catch (error) {
          estimator.removeFile(entry.uid);
          removePendingUpload(entry.uid);
          total -= 1;
          analyzeErrors.push(`${entry.file.name}: ${formatUploadError(error)}`);
        }
      });
      if (analyzeErrors.length) {
        setUploadError(analyzeErrors.join("; "));
      }

      // This only stores files and queues worker jobs; the browser does not run
      // ingestion, so a small upload burst can be acknowledged quickly.
      await runWithConcurrency(queue, 4, async (item) => {
        const filename = item.kind === "file" ? item.file.name : item.filename;
        try {
          let results: InboxUploadResult[];
          if (item.kind === "staged") {
            patchPendingUpload(item.uid, { stage: "ingesting" });
            estimator.startIngest(item.uid);
            setStrip(filename, "ingesting");
            results = await api.commitStagedPdf(projectId, item.stagingId, filename);
          } else {
            patchPendingUpload(item.uid, { stage: "uploading" });
            setStrip(filename, "uploading");
            let ingestStarted = false;
            results = await api.uploadInboxFiles(
              projectId,
              [item.file],
              undefined,
              (loaded, size) => {
                estimator.uploadProgress(item.uid, loaded);
                if (loaded >= size && !ingestStarted) {
                  ingestStarted = true;
                  estimator.startIngest(item.uid);
                  patchPendingUpload(item.uid, {
                    stage: "ingesting",
                    uploadPercent: null,
                  });
                  setStrip(filename, "ingesting");
                } else if (!ingestStarted) {
                  patchPendingUpload(item.uid, {
                    uploadPercent: size > 0 ? Math.round((loaded / size) * 100) : null,
                  });
                }
              },
            );
          }
          const outcome = results[0];
          completedResults.push(...results);
          if (outcome?.ingest_status === "failed") {
            failedResults.push(outcome);
            failedCount += 1;
          }
          estimator.finishFile(item.uid);
        } catch (error) {
          uploadErrors.push(`${filename}: ${formatUploadError(error)}`);
          estimator.finishFile(item.uid);
          failedCount += 1;
        } finally {
          removePendingUpload(item.uid);
          completed += 1;
          setStrip(null, null);
        }
      });

      if (queue.length) {
        await onUploadComplete(completedResults);
      }

      if (failedResults.length) {
        setUploadError(
          `${failedResults.length} file${failedResults.length === 1 ? "" : "s"} failed ingest. Stored in _inbox/ — retry by re-uploading or check backend logs.`,
        );
      }
      if (uploadErrors.length) {
        const batchError = uploadErrors.join("; ");
        setUploadError((current) =>
          current ? `${current} ${batchError}` : batchError,
        );
      }

      if (total > 0 && !queuedUploadBatchesRef.current.length) {
        await sleep(COMPLETION_MESSAGE_MS);
      }
    } finally {
      setUploadProgress(null);
      estimatorRef.current = null;
    }
  }

  return (
    <div
      className={cn(
        "relative flex h-full min-h-0 min-w-0 flex-col overflow-x-hidden transition-colors",
        isDragging && "bg-primary/5",
      )}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="sr-only"
        multiple
        accept={ACCEPT_ATTRIBUTE}
        onChange={handleFileInputChange}
      />

      {isDragging ? (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center border-2 border-dashed border-primary bg-primary/10 p-6 text-center">
          <div>
            <Upload className="mx-auto size-8 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-medium text-primary">Drop to upload to _inbox/</p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF, DOCX, and Markdown supported
            </p>
          </div>
        </div>
      ) : null}

      <div className="flex shrink-0 items-center justify-between gap-2 border-b px-1.5 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div
            className="flex shrink-0 items-center gap-0.5"
            role="group"
            aria-label="Document repository actions"
          >
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              className={cn(
                toolbarIconButtonClass,
                activePanelView === "schedule" && toolbarIconButtonActiveClass,
              )}
              aria-label="Document schedule"
              aria-pressed={activePanelView === "schedule"}
              title="Document schedule"
              onClick={() => setActivePanelView("schedule")}
            >
              <TableProperties className="size-3.5" aria-hidden />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              className={cn(
                toolbarIconButtonClass,
                activePanelView === "tree" && toolbarIconButtonActiveClass,
              )}
              aria-label="Tree view"
              aria-pressed={activePanelView === "tree"}
              title="Tree view"
              onClick={() => setActivePanelView("tree")}
            >
              <FolderTree className="size-3.5" aria-hidden />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              className={toolbarIconButtonClass}
              aria-label="Upload files"
              title="Upload files"
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="size-3.5" aria-hidden />
            </Button>
            {inboxCount && onRunSortFiles ? (
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                className={toolbarIconButtonClass}
                aria-label="Sort files"
                title="Sort files"
                disabled={!overlayReady || isRunningSortFiles}
                onClick={onRunSortFiles}
              >
                {isRunningSortFiles ? (
                  <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  <Folders className="size-3.5" aria-hidden />
                )}
              </Button>
            ) : null}
            {pulseFeed ? (
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                className={cn(
                  toolbarIconButtonClass,
                  "relative",
                  pulseOpen && toolbarIconButtonActiveClass,
                )}
                aria-label={
                  pulseFeed.attention_count > 0
                    ? `Project pulse, ${attentionHeadline(pulseFeed.attention_count)}`
                    : "Project pulse"
                }
                aria-pressed={pulseOpen}
                title="Project pulse"
                onClick={() => setPulseOpen((open) => !open)}
              >
                <Activity className="size-3.5" aria-hidden />
                {pulseFeed.attention_count > 0 ? (
                  <span className="absolute -right-0.5 -top-0.5 flex size-3 items-center justify-center rounded-full bg-[var(--sw-beam)] text-[0.5rem] leading-none text-[var(--sw-void)]">
                    {pulseFeed.attention_count > 9 ? "9+" : pulseFeed.attention_count}
                  </span>
                ) : null}
              </Button>
            ) : null}
          </div>
          {activePanelView === "schedule" && selectedScheduleRows.length ? (
            <span className="shrink-0 text-xs text-muted-foreground">
              {selectedScheduleRows.length} selected
            </span>
          ) : null}
          {isUploading ? (
            <span className="truncate text-xs text-muted-foreground">
              processing files…
            </span>
          ) : null}
        </div>
      </div>

      {uploadProgress ? (
        <IngestProgressStrip progress={uploadProgress} getSnapshot={getBatchSnapshot} />
      ) : null}

      {uploadError ? (
        <div
          className="mx-3 mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          <span>{uploadError}</span>
        </div>
      ) : null}

      {splitProposals.map((proposal) => {
        const resolving = resolvingStagingId === proposal.analysis.staging_id;
        const { analysis } = proposal;
        return (
          <div
            key={analysis.staging_id}
            className="mx-3 mt-3 border border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_12%,transparent)] p-3 text-xs"
          >
            <p className="font-medium text-[var(--sw-caution)]">
              {proposal.sourceFile.name} — looks like a drawing set
            </p>
            <p className="mt-0.5 text-[0.7rem] text-muted-foreground">
              {analysis.page_count} sheets detected ·{" "}
              {Math.round(analysis.confidence * 100)}% confidence
            </p>
            <ul className="mt-2 max-h-40 overflow-y-auto rounded border bg-background/70">
              {analysis.pages.map((sheet) => (
                <li
                  key={sheet.index}
                  className="flex gap-2 border-b px-2 py-1 last:border-b-0"
                >
                  <span className="tabular-nums text-muted-foreground">
                    {String(sheet.index).padStart(2, "0")}
                  </span>
                  <span className="truncate" title={sheet.proposed_title}>
                    {sheet.proposed_title}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-2.5 flex gap-2">
              <button
                type="button"
                disabled={resolving}
                className="inline-flex items-center gap-1.5 rounded-sm bg-primary px-2.5 py-1.5 font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
                onClick={() => void resolveSplit(proposal, "split")}
              >
                {resolving ? (
                  <Loader2 className="size-3.5 animate-spin" aria-hidden />
                ) : null}
                Split into {analysis.page_count} documents
              </button>
              <button
                type="button"
                disabled={resolving}
                className="inline-flex items-center rounded-sm border px-2.5 py-1.5 font-medium transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                onClick={() => void resolveSplit(proposal, "single")}
              >
                Keep as single PDF
              </button>
            </div>
          </div>
        );
      })}

      <div className="cockpit-scroll min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {pulseOpen && pulseFeed ? (
          <>
            <PulsePanel
              feed={pulseFeed}
              sincePreset={pulseSincePreset}
              onSinceChange={onPulseSinceChange}
              onAction={onPulseAction}
            />
            {pulseEmailDraft ? (
              <aside
                className="border-b border-[var(--border-hair)] px-1.5 py-2"
                data-testid="pulse-email-draft"
              >
                <p className="text-[0.6rem] font-mono uppercase tracking-[0.12em] text-[var(--sw-text-quiet)]">
                  Draft reply
                </p>
                <p
                  className="mt-0.5 truncate text-[0.7rem] text-[var(--sw-text-primary)]"
                  title={pulseEmailDraft.subject}
                >
                  {pulseEmailDraft.subject}
                </p>
                <p className="mt-0.5 text-[0.65rem] text-[var(--sw-text-secondary)]">
                  {pulseEmailDraft.status === "sent"
                    ? "Sent"
                    : pulseEmailDraft.status === "send_failed"
                      ? pulseEmailDraft.send_error || "Send failed"
                      : "Saved as draft — not sent"}
                </p>
                {onSendPulseEmailDraft && pulseEmailDraft.status === "draft" ? (
                  <button
                    type="button"
                    data-testid="pulse-email-send"
                    disabled={pulseEmailSending}
                    className="mt-1.5 inline-flex items-center rounded-sm bg-primary px-2.5 py-1 text-[0.65rem] font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
                    onClick={onSendPulseEmailDraft}
                  >
                    {pulseEmailSending ? "Sending…" : "Send"}
                  </button>
                ) : null}
              </aside>
            ) : null}
            {pulseEmailThread ? (
              <aside
                className="border-b border-[var(--border-hair)] px-1.5 py-2"
                data-testid="pulse-email-thread"
              >
                <p className="text-[0.6rem] font-mono uppercase tracking-[0.12em] text-[var(--sw-text-quiet)]">
                  Thread
                </p>
                <ol className="mt-1 grid gap-1.5">
                  {pulseEmailThread.map((message) => (
                    <li key={message.email_id} className="min-w-0">
                      <p
                        className="truncate text-[0.7rem] text-[var(--sw-text-primary)]"
                        title={message.subject}
                      >
                        {message.subject}
                      </p>
                      <p className="truncate text-[0.65rem] text-[var(--sw-text-secondary)]">
                        {message.from_address}
                      </p>
                    </li>
                  ))}
                </ol>
              </aside>
            ) : null}
          </>
        ) : null}
        {activePanelView === "tree" ? (
          <div className="px-1.5 py-2">
            <WorkspaceExplorer
              key={projectId}
              projectId={projectId}
              tree={workspaceTree}
              selectedPath={selectedWorkspacePath}
              onSelectPath={onSelectWorkspacePath}
              onOpenWorkflow={onOpenWorkflow}
              onViewWorkbench={onViewWorkbench}
              onViewFolder={onViewFolder}
            />
            <div className="mt-1 border-t pt-1">
              <NavAccordionSection
                label="Activity"
                isOpen={openTreeSections.has("activity")}
                onToggle={() => toggleTreeSection("activity")}
              >
                <ActivityFeed projectId={projectId} />
              </NavAccordionSection>
              <NavAccordionSection
                label="Skills"
                isOpen={openTreeSections.has("skills")}
                onToggle={() => toggleTreeSection("skills")}
              >
                <PlatformKnowledgePanel
                  platformStatus={platformStatus}
                  mode="skills"
                  selectedPath={selectedPlatformKnowledgePath}
                  onSelectDocument={onSelectPlatformKnowledge}
                />
              </NavAccordionSection>
              <NavAccordionSection
                label="Knowledge"
                isOpen={openTreeSections.has("knowledge")}
                onToggle={() => toggleTreeSection("knowledge")}
              >
                <PlatformKnowledgePanel
                  platformStatus={platformStatus}
                  mode="knowledge"
                  selectedPath={selectedPlatformKnowledgePath}
                  onSelectDocument={onSelectPlatformKnowledge}
                />
              </NavAccordionSection>
              <NavAccordionSection
                label="Admin"
                isOpen={openTreeSections.has("admin")}
                onToggle={() => toggleTreeSection("admin")}
              >
                <PlatformKnowledgeSummary platformStatus={platformStatus} />
              </NavAccordionSection>
            </div>
          </div>
        ) : scheduleRows.length || pendingUploads.length ? (
          <table className="w-full min-w-0 table-fixed border-collapse text-left text-[0.7rem]">
            <colgroup>
              <col className="w-[5rem]" />
              <col />
              <col className="w-[2rem]" />
              <col className="w-[7.5rem]" />
              <col className="w-5" />
            </colgroup>
            <thead className="sticky top-0 z-[1] border-b bg-[var(--sw-panel)]">
              <tr className="text-muted-foreground">
                <SortableScheduleHeader
                  label="#"
                  accessibleLabel="Document number"
                  columnKey="document_number"
                  sortKey={sortKey}
                  sortDirection={sortDirection}
                  className="px-0.5 py-2"
                  onSort={handleSortHeaderClick}
                />
                <SortableScheduleHeader
                  label="Title"
                  columnKey="title"
                  sortKey={sortKey}
                  sortDirection={sortDirection}
                  className="min-w-0 px-1 py-2"
                  onSort={handleSortHeaderClick}
                />
                <SortableScheduleHeader
                  label="Rev"
                  columnKey="revision"
                  sortKey={sortKey}
                  sortDirection={sortDirection}
                  className="px-0.5 py-2"
                  onSort={handleSortHeaderClick}
                />
                <SortableScheduleHeader
                  label="Cat"
                  accessibleLabel="Category"
                  columnKey="category"
                  sortKey={sortKey}
                  sortDirection={sortDirection}
                  className="px-0.5 py-2"
                  onSort={handleSortHeaderClick}
                />
                <th className="w-5 px-0 py-1 text-center" aria-label="Actions">
                  <button
                    type="button"
                    disabled={
                      !selectedScheduleRows.length ||
                      isDeletingSelection ||
                      deleteEvidence.isPending ||
                      deleteDraft.isPending
                    }
                    className="inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-35"
                    aria-label={
                      selectedScheduleRows.length
                        ? `Delete ${selectedScheduleRows.length} selected ${selectedScheduleRows.length === 1 ? "document" : "documents"}`
                        : "Delete selected documents"
                    }
                    title={
                      selectedScheduleRows.length
                        ? `Delete ${selectedScheduleRows.length} selected`
                        : "Select documents to delete"
                    }
                    onClick={() => void handleDeleteSelected()}
                  >
                    {isDeletingSelection ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <Trash className="size-3.5" aria-hidden />
                    )}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {scheduleRows.map((scheduleRow) => {
                if (scheduleRow.kind === "artefact") {
                  const { draft, title } = scheduleRow;
                  const selected = selectedIds.has(draft.id);
                  const deletingRow = bulkDeletingIds.has(draft.id);
                  return (
                    <tr
                      key={draft.id}
                      className={cn(
                        "sw-table-row group/repo-row cursor-pointer select-none border-b text-muted-foreground hover:text-foreground",
                        selected && "sw-table-row--active",
                      )}
                      onClick={(event) => handleRowClick(event, scheduleRow)}
                    >
                      <td className="truncate px-0.5 py-2 tabular-nums">-</td>
                      <td className="max-w-0 min-w-0 px-1 py-2 font-medium">
                        <span className="block truncate" title={title}>
                          {title}
                        </span>
                      </td>
                      <td className="truncate px-0.5 py-2">v{draft.version}</td>
                      <td className="truncate px-0.5 py-2" title={artefactScheduleLabel(draft.workflow_type)}>
                        {artefactScheduleLabel(draft.workflow_type)}
                      </td>
                      <td className="px-0 py-1.5 text-center">
                        <button
                          type="button"
                          disabled={deletingRow}
                          className={cn(
                            "inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 transition-opacity hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-50",
                            deletingRow
                              ? "opacity-100"
                              : "opacity-0 group-hover/repo-row:opacity-100 focus-visible:opacity-100",
                          )}
                          aria-label={`Delete ${title}`}
                          title="Delete document"
                          onClick={(event) => {
                            event.stopPropagation();
                            void handleDeleteArtefact(draft);
                          }}
                        >
                          {deletingRow ? (
                            <Loader2 className="size-3.5 animate-spin" aria-hidden />
                          ) : (
                            <Trash className="size-3.5" aria-hidden />
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                }

                const row = scheduleRow.evidence;
                const active = selectedEvidenceId === row.id;
                const selected = selectedIds.has(row.id);
                const categoryLabel = documentCategoryLabel({
                  documentSubject: row.document_subject,
                  category: row.category,
                });
                const deletingRow =
                  bulkDeletingIds.has(row.id) ||
                  (deleteEvidence.isPending && deleteEvidence.variables === row.id);
                const highlighted = active || selected;
                return (
                  <tr
                    key={row.id}
                    className={cn(
                      "sw-table-row group/repo-row cursor-pointer select-none border-b text-muted-foreground hover:text-foreground",
                      highlighted && "sw-table-row--active",
                    )}
                    onClick={(event) => handleRowClick(event, scheduleRow)}
                  >
                    <td
                      className="truncate px-0.5 py-2 tabular-nums"
                      title={plainMetadataText(row.document_number) || undefined}
                    >
                      {displayValue(row.document_number)}
                    </td>
                    <td className="max-w-0 min-w-0 px-1 py-2 font-medium">
                      <div className="flex min-w-0 items-center gap-1.5">
                        <span className="min-w-0 flex-1 truncate" title={row.title}>
                          {row.title}
                        </span>
                        <InvoiceStatusMark status={row.invoice_status} />
                        <UsageMarks
                          marks={row.used_by}
                          activeArtefactId={usageHighlightArtefactId}
                        />
                      </div>
                    </td>
                    <td className="truncate px-0.5 py-2">
                      {displayValue(row.revision)}
                    </td>
                    <td
                      className="truncate px-0.5 py-2"
                      title={categoryLabel || undefined}
                    >
                      {displayValue(categoryLabel)}
                    </td>
                    <td className="px-0 py-1.5 text-center">
                      <button
                        type="button"
                        disabled={deletingRow}
                        className={cn(
                          "inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 transition-opacity hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-50",
                          deletingRow
                            ? "opacity-100"
                            : "opacity-0 group-hover/repo-row:opacity-100 focus-visible:opacity-100",
                        )}
                        aria-label={`Delete ${row.title}`}
                        title="Delete document"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleDeleteEvidence(row);
                        }}
                      >
                        {deletingRow ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden />
                        ) : (
                          <Trash className="size-3.5" aria-hidden />
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {pendingUploads.map((pending) => (
                <tr
                  key={pending.id}
                  className="sw-table-row animate-in fade-in border-b text-muted-foreground duration-300"
                >
                  <td className="px-0.5 py-2">
                    <span className="cockpit-skeleton block h-2.5 w-7" aria-hidden />
                  </td>
                  <td
                    className="max-w-0 min-w-0 truncate px-1 py-2 font-medium"
                    title={pending.filename}
                  >
                    {pending.filename}
                  </td>
                  <td className="px-0.5 py-2">
                    <span className="cockpit-skeleton block h-2.5 w-4" aria-hidden />
                  </td>
                  <td
                    className="truncate px-0.5 py-2"
                    title={pendingStageLabel(pending)}
                  >
                    {pendingStageLabel(pending)}
                  </td>
                  <td className="px-0 py-1.5 text-center">
                    <Loader2
                      className="mx-auto size-3.5 animate-spin text-muted-foreground/40 motion-reduce:animate-none"
                      aria-hidden
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <button
            type="button"
            disabled={isUploading}
            className={cn(
              "flex h-full min-h-[18rem] w-full items-center justify-center rounded-md border border-dashed p-6 text-center transition-colors",
              !isUploading && "hover:border-primary hover:bg-muted/40",
              isUploading && "cursor-not-allowed opacity-60",
            )}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="max-w-xs">
              <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden />
              <p className="mt-3 text-sm font-medium">Upload project evidence</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Drag files here or click to browse. Uploads land in <code>_inbox/</code> and ingest
                automatically.
              </p>
              <p className="mt-2 text-xs text-muted-foreground">PDF · DOCX · Markdown</p>
            </div>
          </button>
        )}
      </div>
    </div>
  );
}

function artefactScheduleLabel(workflowType: string): string {
  if (workflowType === "create_pmp") return "PMP";
  if (workflowType === "create_cost_plan") return "Cost";
  if (workflowType.startsWith("consultant_procurement_")) return "RFP";
  if (workflowType.startsWith("contractor_eoi_")) return "EOI";
  if (workflowType.startsWith("trade_rft_")) return "RFT";
  if (workflowType.startsWith("trade_rfq_")) return "RFQ";
  return "Gen";
}

/** Shorten long generated titles so the schedule stays scannable in a narrow rail. */
function abbreviateArtefactTitle(title: string): string {
  return title
    .replace(/^Request for Fee Proposal\b/i, "RFP")
    .replace(/^Request for Proposal\b/i, "RFP")
    .replace(/^Request for Tender\b/i, "RFT")
    .replace(/^Request for Quotation\b/i, "RFQ");
}

function plainMetadataText(value: string | null | undefined): string {
  const trimmed = value?.trim() ?? "";
  return trimmed
    .replace(/^\*\*(.+)\*\*$/, "$1")
    .replace(/^\*(.+)\*$/, "$1")
    .trim();
}

function displayValue(value: string | null | undefined): string {
  return plainMetadataText(value) || "—";
}

function isInboxEvidence(row: EvidencePreview): boolean {
  return row.relative_path.replace("\\", "/").includes("/_inbox/");
}

function SortableScheduleHeader({
  label,
  accessibleLabel,
  columnKey,
  sortKey,
  sortDirection,
  className,
  onSort,
}: {
  label: string;
  accessibleLabel?: string;
  columnKey: ScheduleSortKey;
  sortKey: ScheduleSortKey;
  sortDirection: SortDirection;
  className?: string;
  onSort: (key: ScheduleSortKey) => void;
}) {
  const active = sortKey === columnKey;
  const ariaSort = active
    ? sortDirection === "asc"
      ? "ascending"
      : "descending"
    : "none";
  return (
    <th
      className={cn("font-medium", className)}
      aria-label={accessibleLabel}
      aria-sort={ariaSort}
    >
      <button
        type="button"
        className={cn(
          "inline-flex max-w-full items-center gap-0.5 rounded-sm text-left transition-colors hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
        aria-label={accessibleLabel}
        onClick={() => onSort(columnKey)}
      >
        <span className="truncate">{label}</span>
        {active ? (
          sortDirection === "asc" ? (
            <ChevronUp className="size-3 shrink-0" aria-hidden />
          ) : (
            <ChevronDown className="size-3 shrink-0" aria-hidden />
          )
        ) : null}
      </button>
    </th>
  );
}

const INVOICE_STATUS_PRESENTATION = {
  reading: {
    label: "Reading",
    className: "text-[var(--info-text)]",
    dotClassName: "bg-[var(--info-text)]",
  },
  ready_to_process: {
    label: "Ready",
    className: "text-[var(--warn-text)]",
    dotClassName: "bg-[var(--warn-text)]",
  },
  processing: {
    label: "Processing",
    className: "text-[var(--info-text)]",
    dotClassName: "bg-[var(--info-text)] animate-pulse motion-reduce:animate-none",
  },
  booked: {
    label: "Booked",
    className: "text-[var(--ok-text)]",
    dotClassName: "bg-[var(--ok-text)]",
  },
  needs_review: {
    label: "Review",
    className: "text-[var(--warn-text)]",
    dotClassName: "bg-[var(--warn-text)]",
  },
  failed: {
    label: "Failed",
    className: "text-[var(--alert-text)]",
    dotClassName: "bg-[var(--alert-text)]",
  },
} as const;

function InvoiceStatusMark({
  status,
}: {
  status: EvidencePreview["invoice_status"];
}) {
  if (!status) return null;
  const presentation = INVOICE_STATUS_PRESENTATION[status];
  const description = `Invoice status: ${presentation.label}`;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 text-[0.62rem] font-medium",
        presentation.className,
      )}
      aria-label={description}
      title={description}
    >
      <span
        className={cn("size-1.5 rounded-full", presentation.dotClassName)}
        aria-hidden
      />
      {presentation.label}
    </span>
  );
}

/**
 * Quiet source markers for the artefact currently open in the middle panel.
 * Letter chips clutter the schedule; a single azure dot is enough.
 */
function UsageMarks({
  marks,
  activeArtefactId,
}: {
  marks?: DocumentUsageMark[];
  activeArtefactId?: string | null;
}) {
  if (!activeArtefactId || !marks?.length) return null;
  const visible = marks.filter((mark) => mark.artefact_id === activeArtefactId);
  if (!visible.length) return null;
  return (
    <span className="flex shrink-0 items-center gap-1">
      {visible.map((mark) => (
        <span
          key={mark.artefact_id}
          title={`Used by ${mark.title} v${mark.version}`}
          aria-label={`Used by ${mark.title} v${mark.version}`}
          className="size-1.5 shrink-0 rounded-full bg-[var(--info-text)]"
        />
      ))}
    </span>
  );
}

function sortScheduleRows(
  rows: ScheduleRow[],
  key: ScheduleSortKey,
  direction: SortDirection,
): ScheduleRow[] {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => {
    const primary = compareScheduleSortValues(left, right, key);
    if (primary !== 0) return primary * sign;
    return scheduleSortValue(left, "title").localeCompare(
      scheduleSortValue(right, "title"),
      undefined,
      { sensitivity: "base" },
    );
  });
}

function compareScheduleSortValues(
  left: ScheduleRow,
  right: ScheduleRow,
  key: ScheduleSortKey,
): number {
  if (key === "document_number" || key === "revision") {
    return compareDocumentNumbers(
      scheduleSortValue(left, key),
      scheduleSortValue(right, key),
    );
  }
  return scheduleSortValue(left, key).localeCompare(
    scheduleSortValue(right, key),
    undefined,
    { sensitivity: "base", numeric: true },
  );
}

function scheduleSortValue(row: ScheduleRow, key: ScheduleSortKey): string {
  if (row.kind === "artefact") {
    switch (key) {
      case "document_number":
        return "";
      case "title":
        return row.title;
      case "revision":
        return String(row.draft.version);
      case "category":
        return artefactScheduleLabel(row.draft.workflow_type);
    }
  }

  switch (key) {
    case "document_number":
      return plainMetadataText(row.evidence.document_number);
    case "title":
      return row.title;
    case "revision":
      return plainMetadataText(row.evidence.revision);
    case "category":
      return documentCategoryLabel({
        documentSubject: row.evidence.document_subject,
        category: row.evidence.category,
      });
  }
}

function compareDocumentNumbers(
  left: string | null | undefined,
  right: string | null | undefined,
): number {
  const leftValue = left?.trim() ?? "";
  const rightValue = right?.trim() ?? "";
  if (!leftValue && !rightValue) return 0;
  if (!leftValue) return 1;
  if (!rightValue) return -1;

  const leftParts = leftValue.match(/\d+|\D+/g) ?? [leftValue];
  const rightParts = rightValue.match(/\d+|\D+/g) ?? [rightValue];
  const length = Math.max(leftParts.length, rightParts.length);

  for (let index = 0; index < length; index += 1) {
    const leftPart = leftParts[index] ?? "";
    const rightPart = rightParts[index] ?? "";
    const leftNumber = /^\d+$/.test(leftPart) ? Number(leftPart) : null;
    const rightNumber = /^\d+$/.test(rightPart) ? Number(rightPart) : null;

    if (leftNumber !== null && rightNumber !== null && leftNumber !== rightNumber) {
      return leftNumber - rightNumber;
    }
    const textCompare = leftPart.localeCompare(rightPart, undefined, {
      sensitivity: "base",
      numeric: true,
    });
    if (textCompare !== 0) return textCompare;
  }

  return leftValue.localeCompare(rightValue, undefined, { sensitivity: "base", numeric: true });
}

function partitionSupportedFiles(files: File[]): {
  accepted: File[];
  rejected: string[];
} {
  const accepted: File[] = [];
  const rejected: string[] = [];

  for (const file of files) {
    const extension = fileExtension(file.name);
    if (!file.size) {
      rejected.push(`${file.name} (empty)`);
      continue;
    }
    if (SUPPORTED_INBOX_EXTENSIONS.has(extension)) {
      accepted.push(file);
    } else {
      rejected.push(file.name);
    }
  }

  return { accepted, rejected };
}

function fileExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  if (dot <= 0) return "";
  return filename.slice(dot).toLowerCase();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function runWithConcurrency<T>(
  items: T[],
  concurrency: number,
  run: (item: T) => Promise<void>,
): Promise<void> {
  let nextIndex = 0;
  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    async () => {
      while (nextIndex < items.length) {
        const item = items[nextIndex];
        nextIndex += 1;
        await run(item);
      }
    },
  );
  await Promise.all(workers);
}

function formatUploadError(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body;
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "object" && detail !== null) {
        if ("errors" in detail && Array.isArray((detail as { errors: unknown }).errors)) {
          return (detail as { errors: string[] }).errors.join("; ");
        }
        if ("message" in detail && typeof (detail as { message: unknown }).message === "string") {
          return (detail as { message: string }).message;
        }
      }
      if (typeof detail === "string") return detail;
    }
    return error.message;
  }
  return "Upload failed. Check your connection and try again.";
}
