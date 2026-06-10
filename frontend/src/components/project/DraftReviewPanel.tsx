import { useEffect, useState } from "react";
import { Check, FileText, Pencil, RotateCcw, Save } from "lucide-react";

import { CopyContentButton } from "@/components/project/CopyContentButton";
import { MarkdownContent } from "@/components/project/MarkdownContent";
import { WorkflowTracePanel } from "@/components/project/WorkflowTracePanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
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
}: {
  projectId: string;
  draft: DraftArtifact | DraftArtifactSummary | null;
  onDraftUpdated: (draft: DraftArtifact) => void;
  workflowType?: string;
}) {
  const [loadedDraft, setLoadedDraft] = useState<DraftArtifact | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editorValue, setEditorValue] = useState("");
  const [isLoadingDraft, setIsLoadingDraft] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDraftContent() {
      setActionError(null);
      if (!draft) {
        setLoadedDraft(null);
        setEditorValue("");
        setIsEditing(false);
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
        const data = await api.getLatestDraft(projectId, draft.workflow_type);
        if (!cancelled) {
          if (data?.id === draft.id) {
            setLoadedDraft(data);
            setEditorValue(data.content_markdown);
          } else {
            setActionError("Could not load the selected draft content.");
          }
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
  const isAccepted = displayDraft.status === "accepted";

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

  return (
    <article className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 lg:p-6">
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
          <MetaItem label="Model" value={displayDraft.model ?? "Unknown"} />
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
          <Button disabled variant="outline" size="sm">
            <RotateCcw className="size-4" aria-hidden />
            Reopen
          </Button>
        </div>
        {actionError ? (
          <p className="mt-3 text-sm text-destructive">{actionError}</p>
        ) : null}
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <ReferenceList title="Seed consulted" items={seed} />
        <ReferenceList title="Evidence refs" items={evidence} />
        <ReferenceList title="Context refs" items={context} />
      </div>

      <WorkflowTracePanel trace={trace} emptyMessage="No persisted trace recorded for this draft." />

      <section className="rounded-md border bg-background">
        <header className="border-b px-4 py-3">
          <h3 className="text-sm font-semibold">
            {isEditing ? "Edit draft content" : "Draft content"}
          </h3>
        </header>
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
        ) : (
          <div className="max-h-[38rem] overflow-auto p-4">
            <MarkdownContent markdown={loadedDraft.content_markdown} />
          </div>
        )}
      </section>
    </article>
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
