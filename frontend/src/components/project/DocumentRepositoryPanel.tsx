import {
  AlertCircle,
  FolderTree,
  Inbox,
  Loader2,
  LoaderCircle,
  Play,
  TableProperties,
  Trash,
  Upload,
} from "lucide-react";
import {
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type MouseEvent,
} from "react";

import { ActivityFeed } from "@/components/project/ActivityFeed";
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
import { ApiError } from "@/lib/http";
import { MARKDOWN_EXTENSIONS } from "@/lib/markdown";
import { useDeleteEvidence } from "@/lib/queries/project-data";
import type {
  EvidencePreview,
  InboxUploadResult,
  PdfAnalyzeResult,
  PlatformKnowledgeStatus,
  WorkspaceTreeNode,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

const COMPLETION_MESSAGE_MS = 2_000;

const SUPPORTED_INBOX_EXTENSIONS = new Set([
  ".pdf",
  ".docx",
  ...MARKDOWN_EXTENSIONS,
]);
const ACCEPT_ATTRIBUTE = Array.from(SUPPORTED_INBOX_EXTENSIONS).join(",");

type SplitProposal = {
  sourceFile: File;
  analysis: PdfAnalyzeResult;
};

type RepositoryPanelView = "schedule" | "tree";
type RepositoryTreeSectionId = "activity" | "skills" | "knowledge" | "admin";

function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".pdf");
}

export function DocumentRepositoryPanel({
  projectId,
  evidence,
  selectedEvidenceId,
  workspaceTree,
  selectedWorkspacePath,
  onSelectEvidence,
  onSelectWorkspacePath,
  onOpenWorkflow,
  onViewWorkbench,
  onViewFolder,
  onUploadComplete,
  onRunSortFiles,
  isRunningSortFiles = false,
  overlayReady = true,
  platformStatus = null,
}: {
  projectId: string;
  evidence: EvidencePreview[];
  selectedEvidenceId: string | null;
  workspaceTree: WorkspaceTreeNode[];
  selectedWorkspacePath: string | null;
  onSelectEvidence: (evidenceId: string) => void;
  onSelectWorkspacePath: (path: string) => void;
  onOpenWorkflow: (tileId: string) => void;
  onViewWorkbench: () => void;
  onViewFolder: () => void;
  onUploadComplete: () => Promise<void>;
  onRunSortFiles?: () => void;
  isRunningSortFiles?: boolean;
  overlayReady?: boolean;
  platformStatus?: PlatformKnowledgeStatus | null;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const deleteEvidence = useDeleteEvidence(projectId);
  const [activePanelView, setActivePanelView] =
    useState<RepositoryPanelView>("schedule");
  const [openTreeSections, setOpenTreeSections] = useState<Set<RepositoryTreeSectionId>>(
    () => new Set(["activity", "admin"]),
  );
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<IngestUploadProgress | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [splitProposals, setSplitProposals] = useState<SplitProposal[]>([]);
  const [resolvingStagingId, setResolvingStagingId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set<string>(),
  );
  const [selectionAnchorId, setSelectionAnchorId] = useState<string | null>(null);
  const [bulkDeletingIds, setBulkDeletingIds] = useState<Set<string>>(
    () => new Set<string>(),
  );
  const dragDepthRef = useRef(0);
  const registerRows = useMemo(() => sortRegisterRows(evidence), [evidence]);
  const registerRowIds = useMemo(
    () => new Set(registerRows.map((row) => row.id)),
    [registerRows],
  );
  const selectedRows = useMemo(
    () => registerRows.filter((row) => selectedIds.has(row.id)),
    [registerRows, selectedIds],
  );
  const inboxCount = useMemo(
    () => evidence.filter((item) => isInboxEvidence(item)).length,
    [evidence],
  );

  function toggleTreeSection(id: RepositoryTreeSectionId) {
    setOpenTreeSections((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  const isDeletingSelection = bulkDeletingIds.size > 0;

  function handleDragEnter(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (isUploading) return;
    dragDepthRef.current += 1;
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (isUploading) return;
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDragging(false);
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (isUploading) return;
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDragging(false);
    if (isUploading) return;
    const dropped = [...event.dataTransfer.files];
    if (dropped.length) {
      void uploadFilesBatch(dropped);
    }
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files ? [...event.target.files] : [];
    event.target.value = "";
    if (selected.length) {
      void uploadFilesBatch(selected);
    }
  }

  function handleRowClick(
    event: MouseEvent<HTMLTableRowElement>,
    row: EvidencePreview,
  ) {
    const additive = event.ctrlKey || event.metaKey;

    if (event.shiftKey) {
      const anchorId =
        selectionAnchorId && registerRowIds.has(selectionAnchorId)
          ? selectionAnchorId
          : selectedEvidenceId && registerRowIds.has(selectedEvidenceId)
            ? selectedEvidenceId
            : row.id;
      const anchorIndex = registerRows.findIndex((item) => item.id === anchorId);
      const rowIndex = registerRows.findIndex((item) => item.id === row.id);
      if (anchorIndex >= 0 && rowIndex >= 0) {
        const start = Math.min(anchorIndex, rowIndex);
        const end = Math.max(anchorIndex, rowIndex);
        const rangeIds = registerRows.slice(start, end + 1).map((item) => item.id);
        setSelectedIds((current) => {
          const next = additive
            ? new Set([...current].filter((id) => registerRowIds.has(id)))
            : new Set<string>();
          for (const id of rangeIds) next.add(id);
          return next;
        });
        onSelectEvidence(row.id);
        return;
      }
    }

    if (additive) {
      setSelectedIds((current) => {
        const next = new Set([...current].filter((id) => registerRowIds.has(id)));
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
    onSelectEvidence(row.id);
  }

  async function handleDelete(row: EvidencePreview) {
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

  async function handleDeleteSelected() {
    if (!selectedRows.length) return;

    const count = selectedRows.length;
    const confirmed = window.confirm(
      `Delete ${count} selected ${count === 1 ? "document" : "documents"}? This removes ${count === 1 ? "it" : "them"} from the document repository and cannot be undone.`,
    );
    if (!confirmed) return;

    setUploadError(null);
    setBulkDeletingIds(new Set(selectedRows.map((row) => row.id)));

    const failedRows: string[] = [];
    const failedIds = new Set<string>();
    try {
      for (const row of selectedRows) {
        try {
          await deleteEvidence.mutateAsync(row.id);
        } catch (error) {
          const detail =
            error instanceof ApiError ? error.message : "Please try again.";
          failedRows.push(`${row.title}: ${detail}`);
          failedIds.add(row.id);
        }
      }
    } finally {
      setBulkDeletingIds(new Set<string>());
    }

    setSelectedIds(failedIds);
    setSelectionAnchorId(failedIds.values().next().value ?? null);
    if (failedRows.length) {
      setUploadError(
        `Could not delete ${failedRows.length} selected ${failedRows.length === 1 ? "document" : "documents"}: ${failedRows.join("; ")}`,
      );
    }
  }

  async function resolveSplit(proposal: SplitProposal, mode: "split" | "single") {
    setResolvingStagingId(proposal.analysis.staging_id);
    setUploadError(null);
    try {
      if (mode === "split") {
        await api.splitStagedPdf(
          projectId,
          proposal.analysis.staging_id,
          proposal.sourceFile.name,
        );
      } else {
        await api.commitStagedPdf(
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
      await onUploadComplete();
    } catch (error) {
      setUploadError(
        `Could not process "${proposal.sourceFile.name}": ${formatUploadError(error)}`,
      );
    } finally {
      setResolvingStagingId(null);
    }
  }

  async function uploadFilesBatch(files: File[]) {
    setUploadError(null);

    const { accepted, rejected } = partitionSupportedFiles(files);
    if (rejected.length) {
      setUploadError(
        `Unsupported file type: ${rejected.join(", ")}. Supported: ${[...SUPPORTED_INBOX_EXTENSIONS].join(", ")}`,
      );
    }
    if (!accepted.length) return;

    // PDFs are analyzed first: drawing sets become split proposals the user
    // confirms; everything else ingests immediately as before.
    const toIngest: File[] = accepted.filter((file) => !isPdfFile(file));
    const analyzeErrors: string[] = [];
    for (const pdf of accepted.filter(isPdfFile)) {
      try {
        const analysis = await api.analyzePdf(projectId, pdf);
        if (analysis.is_drawing_set) {
          setSplitProposals((current) => [
            ...current,
            { sourceFile: pdf, analysis },
          ]);
        } else {
          toIngest.push(pdf);
        }
      } catch (error) {
        analyzeErrors.push(`${pdf.name}: ${formatUploadError(error)}`);
      }
    }
    if (analyzeErrors.length) {
      setUploadError(analyzeErrors.join("; "));
    }
    if (!toIngest.length) return;

    setIsUploading(true);
    setUploadProgress({
      total: toIngest.length,
      completed: 0,
      currentFilename: toIngest[0]?.name ?? null,
      failedCount: 0,
    });

    const failedResults: InboxUploadResult[] = [];
    const uploadErrors: string[] = [];

    try {
      for (let index = 0; index < toIngest.length; index += 1) {
        const file = toIngest[index];
        setUploadProgress({
          total: toIngest.length,
          completed: index,
          currentFilename: file.name,
          failedCount: failedResults.length,
        });

        try {
          const results = await api.uploadInboxFiles(projectId, [file]);
          const outcome = results[0];
          if (outcome?.ingest_status === "failed") {
            failedResults.push(outcome);
          }
          await onUploadComplete();
        } catch (error) {
          uploadErrors.push(`${file.name}: ${formatUploadError(error)}`);
        }

        setUploadProgress({
          total: toIngest.length,
          completed: index + 1,
          currentFilename:
            index + 1 < toIngest.length ? toIngest[index + 1].name : null,
          failedCount: failedResults.length,
        });
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

      await sleep(COMPLETION_MESSAGE_MS);
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
    }
  }

  return (
    <div
      className={cn(
        "relative flex h-full min-h-0 flex-col transition-colors",
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
        disabled={isUploading}
        onChange={handleFileInputChange}
      />

      {isDragging ? (
        <div className="pointer-events-none absolute inset-2 z-10 flex items-center justify-center rounded-md border-2 border-dashed border-primary bg-primary/10 p-6 text-center">
          <div>
            <Upload className="mx-auto size-8 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-medium text-primary">Drop to upload to _inbox/</p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF, DOCX, and Markdown supported
            </p>
          </div>
        </div>
      ) : null}

      <div className="flex shrink-0 items-center justify-between gap-3 border-b px-3 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {activePanelView === "schedule" && selectedRows.length ? (
            <span className="shrink-0 text-xs text-muted-foreground">
              {selectedRows.length} selected
            </span>
          ) : null}
          {isUploading ? (
            <span className="truncate text-xs text-muted-foreground">
              {uploadProgress
                ? `ingesting ${uploadProgress.completed} of ${uploadProgress.total}`
                : "ingesting…"}
            </span>
          ) : (
            <button
              type="button"
              className="inline-flex shrink-0 items-center gap-1 text-xs text-primary hover:underline"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="size-3 shrink-0" aria-hidden />
              upload files
            </button>
          )}
          {inboxCount && onRunSortFiles ? (
            <Button
              type="button"
              size="sm"
              className="h-7 shrink-0 border-amber-400/50 bg-amber-50/80 px-2 text-xs text-amber-900 hover:bg-amber-100/80"
              disabled={!overlayReady || isRunningSortFiles}
              onClick={onRunSortFiles}
            >
              {isRunningSortFiles ? (
                <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
              ) : (
                <Play className="size-3.5" aria-hidden />
              )}
              {isRunningSortFiles ? "Running" : "Sort Files"}
            </Button>
          ) : null}
        </div>
        <div
          className="flex shrink-0 items-center rounded-md border bg-muted/30 p-0.5"
          role="group"
          aria-label="Right panel view"
        >
          <Button
            type="button"
            variant={activePanelView === "schedule" ? "secondary" : "ghost"}
            size="icon-xs"
            aria-label="Document schedule"
            aria-pressed={activePanelView === "schedule"}
            title="Document schedule"
            onClick={() => setActivePanelView("schedule")}
          >
            <TableProperties className="size-3.5" aria-hidden />
          </Button>
          <Button
            type="button"
            variant={activePanelView === "tree" ? "secondary" : "ghost"}
            size="icon-xs"
            aria-label="Tree view"
            aria-pressed={activePanelView === "tree"}
            title="Tree view"
            onClick={() => setActivePanelView("tree")}
          >
            <FolderTree className="size-3.5" aria-hidden />
          </Button>
        </div>
      </div>

      {uploadProgress ? <IngestProgressStrip progress={uploadProgress} /> : null}

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
            className="mx-3 mt-3 rounded-md border border-amber-400/50 bg-amber-50/60 p-3 text-xs dark:bg-amber-950/20"
          >
            <p className="font-medium text-amber-900 dark:text-amber-100">
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

      <div className="cockpit-scroll min-h-0 flex-1 overflow-y-auto">
        {activePanelView === "tree" ? (
          <div className="px-3 py-3">
            <WorkspaceExplorer
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
                <PlatformKnowledgePanel platformStatus={platformStatus} mode="skills" />
              </NavAccordionSection>
              <NavAccordionSection
                label="Knowledge"
                isOpen={openTreeSections.has("knowledge")}
                onToggle={() => toggleTreeSection("knowledge")}
              >
                <PlatformKnowledgePanel platformStatus={platformStatus} mode="knowledge" />
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
        ) : registerRows.length ? (
          <table className="w-full table-fixed border-collapse text-left text-[0.7rem]">
            <colgroup>
              <col className="w-[2.75rem]" />
              <col />
              <col className="w-[2.25rem]" />
              <col className="w-[4.75rem]" />
              <col className="w-[1.75rem]" />
            </colgroup>
            <thead className="sticky top-0 z-[1] border-b bg-background">
              <tr className="text-muted-foreground">
                <th className="px-1 py-2 font-medium">Doc No</th>
                <th className="px-2 py-2 font-medium">Title</th>
                <th className="px-1 py-2 font-medium">Rev</th>
                <th className="px-1.5 py-2 font-medium">Category</th>
                <th className="px-0.5 py-1 text-center" aria-label="Actions">
                  <button
                    type="button"
                    disabled={
                      !selectedRows.length ||
                      isDeletingSelection ||
                      deleteEvidence.isPending
                    }
                    className="inline-flex size-6 items-center justify-center rounded-sm text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-35"
                    aria-label={
                      selectedRows.length
                        ? `Delete ${selectedRows.length} selected ${selectedRows.length === 1 ? "document" : "documents"}`
                        : "Delete selected documents"
                    }
                    title={
                      selectedRows.length
                        ? `Delete ${selectedRows.length} selected`
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
              {registerRows.map((row) => {
                const active = selectedEvidenceId === row.id;
                const selected = selectedIds.has(row.id);
                const inInbox = isInboxEvidence(row);
                const deletingRow =
                  bulkDeletingIds.has(row.id) ||
                  (deleteEvidence.isPending && deleteEvidence.variables === row.id);
                return (
                  <tr
                    key={row.id}
                    className={cn(
                      "cursor-pointer select-none border-b border-l-2 transition-colors hover:bg-muted/60",
                      inInbox
                        ? "border-l-amber-400 bg-amber-50/40 hover:bg-amber-50/70 dark:bg-amber-950/20 dark:hover:bg-amber-950/30"
                        : "border-l-transparent",
                      active &&
                        !selected &&
                        (inInbox ? "bg-amber-50/80 dark:bg-amber-950/35" : "bg-muted"),
                      selected &&
                        (inInbox
                          ? "bg-amber-100/80 dark:bg-amber-900/35"
                          : "border-l-primary bg-primary/10 hover:bg-primary/15"),
                    )}
                    onClick={(event) => handleRowClick(event, row)}
                  >
                    <td className="truncate px-1 py-2 tabular-nums text-muted-foreground">
                      {displayValue(row.document_number)}
                    </td>
                    <td className="max-w-0 truncate px-2 py-2 font-medium" title={row.title}>
                      {row.title}
                    </td>
                    <td className="truncate px-1 py-2 text-muted-foreground">
                      {displayValue(row.revision)}
                    </td>
                    <td
                      className={cn(
                        "truncate px-1.5 py-2",
                        inInbox
                          ? "font-medium text-amber-800 dark:text-amber-200"
                          : "text-muted-foreground",
                      )}
                    >
                      {inInbox ? "Inbox" : displayValue(row.category)}
                    </td>
                    <td className="px-0.5 py-1.5 text-center">
                      <button
                        type="button"
                        disabled={deletingRow}
                        className="inline-flex size-6 items-center justify-center rounded-sm text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-50"
                        aria-label={`Delete ${row.title}`}
                        title="Delete document"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleDelete(row);
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

function displayValue(value: string | null | undefined): string {
  return value?.trim() ? value : "—";
}

function isInboxEvidence(row: EvidencePreview): boolean {
  return row.relative_path.replace("\\", "/").includes("/_inbox/");
}

function sortRegisterRows(evidence: EvidencePreview[]): EvidencePreview[] {
  return [...evidence].sort((left, right) => {
    const docCompare = compareDocumentNumbers(
      left.document_number,
      right.document_number,
    );
    if (docCompare !== 0) return docCompare;
    return left.title.localeCompare(right.title, undefined, { sensitivity: "base" });
  });
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
