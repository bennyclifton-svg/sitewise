import { useEffect, useMemo, useState } from "react";
import { Check, Download, FileText, Pencil, RefreshCw, RotateCcw, Save, Table2 } from "lucide-react";

import { CopyContentButton } from "@/components/project/CopyContentButton";
import { MarkdownContent } from "@/components/project/MarkdownContent";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { WorkbookGrid } from "@/components/project/WorkbookGrid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { splitMarkdownSections, spliceMarkdownSection } from "@/lib/markdown-sections";
import type {
  DraftArtifact,
  DraftArtifactSummary,
  WorkflowTraceEvent,
} from "@/lib/types/project";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function DraftReviewPanel({
  projectId,
  draft,
  onDraftUpdated,
  workflowType,
  onRunUpdatePmp,
  isRunningUpdatePmp = false,
}: {
  projectId: string;
  draft: DraftArtifact | DraftArtifactSummary | null;
  onDraftUpdated: (draft: DraftArtifact) => void;
  workflowType?: string;
  onRunUpdatePmp?: () => void;
  isRunningUpdatePmp?: boolean;
}) {
  const [loadedDraft, setLoadedDraft] = useState<DraftArtifact | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editorValue, setEditorValue] = useState("");
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [isDownloadingWorkbook, setIsDownloadingWorkbook] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [sectionEditHeading, setSectionEditHeading] = useState<string | null>(null);
  const [sectionEditorValue, setSectionEditorValue] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadDraftContent() {
      setActionError(null);
      if (!draft) {
        setLoadedDraft(null);
        setEditorValue("");
        setIsEditing(false);
        setSectionEditHeading(null);
        setIsLoadingDraft(false);
        return;
      }

      if (isFullDraft(draft)) {
        setLoadedDraft(draft);
        setEditorValue(draft.content_markdown);
        setIsEditing(false);
        setIsLoadingDraft(false);
        return;
      }

      setLoadedDraft(null);
      setEditorValue("");
      setIsEditing(false);
      setIsLoadingDraft(true);
      try {
        const data = await api.getProjectDraft(projectId, draft.id);
        if (!cancelled) {
          setLoadedDraft(data);
          setEditorValue(data.content_markdown);
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

  const sections = useMemo(
    () => (loadedDraft ? splitMarkdownSections(loadedDraft.content_markdown) : []),
    [loadedDraft],
  );

  if (!draft) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          {emptyDraftMessage(workflowType)}
        </div>
      </div>
    );
  }

  const displayDraft = loadedDraft ?? draft;
  const acceptLabel = acceptDraftLabel(displayDraft.workflow_type);

  const seed = metadataList(loadedDraft?.provenance_metadata?.seed_consulted);
  const evidence = metadataList(loadedDraft?.provenance_metadata?.evidence_refs);
  const context = metadataList(loadedDraft?.provenance_metadata?.context_refs);
  const trace = metadataTrace(loadedDraft?.provenance_metadata?.trace);
  const sectionsChanged = metadataStringList(loadedDraft?.provenance_metadata?.sections_changed);
  const evidenceChanged = evidenceChangedSummary(loadedDraft?.provenance_metadata?.evidence_changed);
  const workbook = workbookMetadata(loadedDraft?.provenance_metadata?.workbook);
  const isAccepted = displayDraft.status === "accepted";

  function startSectionEdit(heading: string) {
    if (!loadedDraft) return;
    const section = sections.find((item) => item.heading === heading);
    if (!section) return;
    setSectionEditHeading(heading);
    setSectionEditorValue(loadedDraft.content_markdown.slice(section.start, section.end));
    setIsEditing(false);
    setActionError(null);
  }

  async function saveSectionEdit() {
    if (!loadedDraft || !sectionEditHeading) return;
    const section = sections.find((item) => item.heading === sectionEditHeading);
    if (!section) return;
    const nextMarkdown = spliceMarkdownSection(
      loadedDraft.content_markdown,
      section,
      sectionEditorValue,
    );
    setIsSaving(true);
    setActionError(null);
    try {
      const updated = await api.patchDraft(projectId, loadedDraft.id, nextMarkdown);
      setLoadedDraft(updated);
      onDraftUpdated(updated);
      setSectionEditHeading(null);
      setSectionEditorValue("");
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Could not save section.");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveEdits() {
    if (!loadedDraft) return;
    setIsSaving(true);
    setActionError(null);
    try {
      const updated = await api.patchDraft(projectId, loadedDraft.id, editorValue);
      setLoadedDraft(updated);
      onDraftUpdated(updated);
      setIsEditing(false);
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Could not save draft.");
    } finally {
      setIsSaving(false);
    }
  }

  async function acceptDraft() {
    setIsAccepting(true);
    setActionError(null);
    try {
      const updated = await api.acceptDraft(projectId, displayDraft.id);
      setLoadedDraft(updated);
      onDraftUpdated(updated);
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Could not accept draft.");
    } finally {
      setIsAccepting(false);
    }
  }

  async function downloadWorkbook() {
    if (!workbook) return;
    setIsDownloadingWorkbook(true);
    setActionError(null);
    try {
      const blob = await api.downloadWorkspaceFile(projectId, workbook.workspace_path);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = workbook.file_name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setActionError(
        error instanceof ApiError ? error.message : "Could not download workbook.",
      );
    } finally {
      setIsDownloadingWorkbook(false);
    }
  }

  return (
    <article className="flex w-full min-w-0 flex-col gap-4 p-4 lg:p-6">
      <section className="rounded-md border bg-background">
        {sectionsChanged.length || evidenceChanged ? (
          <div className="space-y-3 border-b px-4 py-3">
            {sectionsChanged.length ? (
              <div>
                <h3 className="text-sm font-semibold">
                  What changed in v{displayDraft.version}
                </h3>
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
                onOpenTrace={() => {
                  document.getElementById("draft-workflow-trace")?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
                }}
              />
            ) : null}
          </div>
        ) : null}
        {isLoadingDraft ? (
          <p className="p-4 text-sm text-muted-foreground" role="status">
            Loading draft content...
          </p>
        ) : !loadedDraft ? (
          <p className="p-4 text-sm text-muted-foreground">
            Draft content could not be loaded.
          </p>
        ) : isEditing ? (
          <textarea
            className="min-h-[38rem] w-full resize-y border-0 bg-transparent p-4 font-mono text-sm leading-relaxed outline-none focus-visible:ring-0"
            value={editorValue}
            onChange={(event) => setEditorValue(event.target.value)}
            spellCheck={false}
          />
        ) : sectionEditHeading ? (
          <div className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold">Editing: {sectionEditHeading}</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSectionEditHeading(null);
                    setSectionEditorValue("");
                  }}
                >
                  Cancel
                </Button>
                <Button size="sm" onClick={() => void saveSectionEdit()} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save section"}
                </Button>
              </div>
            </div>
            <textarea
              className="min-h-[18rem] w-full resize-y rounded-md border bg-transparent p-3 font-mono text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={sectionEditorValue}
              onChange={(event) => setSectionEditorValue(event.target.value)}
              spellCheck={false}
            />
          </div>
        ) : (
          <div className="p-4">
            <MarkdownContent
              markdown={loadedDraft.content_markdown}
              version={displayDraft.version}
              projectId={projectId}
              projectTitle={displayDraft.title}
              readOnly={isAccepted}
              onDraftUpdated={(updated) => {
                setLoadedDraft(updated);
                onDraftUpdated(updated);
              }}
              onEditSection={
                isAccepted || isEditing ? undefined : (heading) => startSectionEdit(heading)
              }
            />
          </div>
        )}
      </section>

      {workbook ? (
        <section className="rounded-md border bg-background">
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

      <header className="rounded-md border bg-background p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <FileText className="size-5 shrink-0 text-muted-foreground" aria-hidden />
              <h2 className="min-w-0 truncate text-xl font-semibold">{displayDraft.title}</h2>
              {loadedDraft ? (
                <CopyContentButton
                  content={isEditing ? editorValue : loadedDraft.content_markdown}
                  label={`Copy ${displayDraft.title}`}
                />
              ) : null}
            </div>
            <p className="mt-1 break-all text-sm text-muted-foreground">
              {displayDraft.workspace_path}
            </p>
          </div>
          <div className="flex gap-2">
            <Badge variant="secondary">v{displayDraft.version}</Badge>
            <Badge variant={isAccepted ? "default" : "outline"}>
              {isAccepted ? "Accepted" : "Draft"}
            </Badge>
          </div>
        </div>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <MetaItem label="Saved" value={dateFormatter.format(new Date(displayDraft.created_at))} />
          <MetaItem label="Model" value={draftModelLabel(displayDraft)} />
          <MetaItem label="Runtime" value={displayDraft.runtime} />
          <MetaItem label="Workflow" value={displayDraft.workflow_type} />
          <MetaItem
            label="Draft mode"
            value={draftModeLabel(loadedDraft?.provenance_metadata?.draft_mode)}
          />
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            variant={isAccepted ? "outline" : "secondary"}
            size="sm"
            onClick={() => void acceptDraft()}
            disabled={isAccepting || isAccepted}
          >
            <Check className="size-4" aria-hidden />
            {isAccepting ? "Accepting..." : isAccepted ? "Accepted" : acceptLabel}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing((current) => !current)}
            disabled={isSaving || isLoadingDraft || !loadedDraft}
          >
            <Pencil className="size-4" aria-hidden />
            {isEditing ? "Preview" : "Edit markdown"}
          </Button>
          {isEditing ? (
            <Button size="sm" onClick={() => void saveEdits()} disabled={isSaving || !loadedDraft}>
              <Save className="size-4" aria-hidden />
              {isSaving ? "Saving..." : "Save edits"}
            </Button>
          ) : null}
          {workbook ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => void downloadWorkbook()}
              disabled={isDownloadingWorkbook}
            >
              <Download className="size-4" aria-hidden />
              {isDownloadingWorkbook ? "Downloading..." : "Download workbook"}
            </Button>
          ) : null}
          {isPmpDraft(displayDraft.workflow_type) && onRunUpdatePmp ? (
            <Button
              variant="outline"
              size="sm"
              onClick={onRunUpdatePmp}
              disabled={isRunningUpdatePmp || isAccepting || isEditing}
            >
              <RefreshCw className="size-4" aria-hidden />
              {isRunningUpdatePmp ? "Refreshing..." : "Refresh PMP from documents"}
            </Button>
          ) : null}
          <Button disabled variant="outline" size="sm">
            <RotateCcw className="size-4" aria-hidden />
            Reopen
          </Button>
        </div>
        {actionError ? (
          <p className="mt-3 text-sm text-destructive">{actionError}</p>
        ) : null}
      </header>

      <div id="draft-workflow-trace">
        <WorkflowTracePanel trace={trace} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ReferenceList title="Seed consulted" items={seed} />
        <ReferenceList title="Evidence refs" items={evidence} />
        <ReferenceList title="Context refs" items={context} />
      </div>
    </article>
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

function acceptDraftLabel(workflowType: string): string {
  if (workflowType === "create_cost_plan") {
    return "Accept cost plan";
  }
  if (workflowType === "create_pmp" || workflowType === "update_pmp") {
    return "Accept PMP";
  }
  return "Accept draft";
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
