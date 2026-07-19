import { AlertCircle, ArrowDown, ArrowUp, FileCheck2, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { EvidencePreview } from "@/lib/types/project";
import type { TenderProjectContext } from "@/lib/types/tender";

type FileDraft = { id: string; title: string; path: string };
type GroupDraft = { key: string; builderName: string; files: FileDraft[] };

export function TenderQuoteSelectionPanel({
  projectId,
  selectedEvidence,
}: {
  projectId: string;
  selectedEvidence: EvidencePreview[];
}) {
  const navigate = useNavigate();
  const [revision, setRevision] = useState(0);
  const [groups, setGroups] = useState<GroupDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [region, setRegion] = useState<"" | NonNullable<TenderProjectContext["region"]>>("");
  const [specLevel, setSpecLevel] = useState<"" | NonNullable<TenderProjectContext["spec_level"]>>("");
  const [storeys, setStoreys] = useState("");
  const intakeTurnId = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api.getTenderQuoteSelection(projectId).then((selection) => {
      if (cancelled) return;
      setRevision(selection.revision);
      setGroups(selection.quote_groups.map((group) => ({
        key: group.group_id,
        builderName: group.builder_name,
        files: group.files.map((file) => ({ id: file.workspace_file_id, title: file.filename, path: file.workspace_path })),
      })));
    }).catch((loadError) => {
      if (!cancelled) setError(loadError instanceof ApiError ? loadError.message : "Could not load quote selection.");
    }).finally(() => {
      if (!cancelled) setIsLoading(false);
    });
    return () => { cancelled = true; };
  }, [projectId]);

  const assigned = useMemo(() => new Set(groups.flatMap((group) => group.files.map((file) => file.id))), [groups]);
  const available = selectedEvidence.filter((item) => item.workspace_file_id && !assigned.has(item.workspace_file_id));
  const canSave = groups.length >= 2 && groups.length <= 5 && groups.every((group) => group.builderName.trim() && group.files.length) && !isSubmitting;

  function addSelectedFiles() {
    setGroups((current) => {
      const next = [...current];
      for (const item of available) {
        const file = { id: item.workspace_file_id!, title: item.title, path: item.relative_path };
        if (next.length < 5) next.push({ key: crypto.randomUUID(), builderName: `Builder ${next.length + 1}`, files: [file] });
        else next[next.length - 1] = { ...next[next.length - 1], files: [...next[next.length - 1].files, file] };
      }
      return next;
    });
  }

  function moveGroup(index: number, offset: number) {
    setGroups((current) => {
      const target = index + offset;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function mergeWithPrevious(index: number) {
    if (index < 1) return;
    setGroups((current) => current.map((group, groupIndex) =>
      groupIndex === index - 1 ? { ...group, files: [...group.files, ...current[index].files] } : group,
    ).filter((_, groupIndex) => groupIndex !== index));
  }

  function moveFile(groupKey: string, index: number, offset: number) {
    setGroups((current) => current.map((group) => {
      if (group.key !== groupKey) return group;
      const target = index + offset;
      if (target < 0 || target >= group.files.length) return group;
      const files = [...group.files];
      [files[index], files[target]] = [files[target], files[index]];
      return { ...group, files };
    }));
  }

  async function saveSelection() {
    if (!canSave) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const saved = await api.replaceTenderQuoteSelection(projectId, {
        expected_revision: revision,
        quote_candidates: groups.map((group) => ({
          builder_name: group.builderName.trim(),
          ordered_workspace_file_ids: group.files.map((file) => file.id),
        })),
      });
      setRevision(saved.revision);
    } catch (saveError) {
      setError(saveError instanceof ApiError ? saveError.message : "Could not save the quote selection.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function startComparison() {
    if (!revision || !region || !specLevel || isSubmitting) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const project = await api.getProject(projectId);
      const contextOverrides = {
        region,
        spec_level: specLevel,
        ...(storeys ? { storeys: Number(storeys) } : {}),
      };
      const input = {
        project_id: projectId,
        expected_profile_revision: project.profile_revision ?? 1,
        expected_selection_revision: revision,
        context_overrides: contextOverrides,
      };
      const prepared = await api.prepareTenderComparison(input);
      if (!prepared.ready) {
        setError([...prepared.unsupported_reasons, ...prepared.missing_fields.map((field) => `Missing ${field}`)].join(". "));
        return;
      }
      intakeTurnId.current ??= crypto.randomUUID();
      const result = await api.startTenderComparison({ ...input, turn_id: intakeTurnId.current });
      intakeTurnId.current = null;
      navigate(`/projects/${projectId}/tender/${result.comparison.id}`);
    } catch (startError) {
      setError(startError instanceof ApiError ? startError.message : "Could not start the tender comparison.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-md border bg-card shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
        <div><p className="cockpit-zone-title">Tender intake</p><h2 className="mt-1 text-lg font-semibold tracking-tight">Quote selection</h2><p className="mt-1 text-xs text-muted-foreground">{groups.length} groups · revision {revision}</p></div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={addSelectedFiles} disabled={!available.length || isLoading}><Plus className="size-4" aria-hidden />Add selected files</Button>
          <Button type="button" onClick={() => void saveSelection()} disabled={!canSave}>{isSubmitting ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : <FileCheck2 className="size-4" aria-hidden />}{isSubmitting ? "Saving" : "Save quote selection"}</Button>
        </div>
      </header>
      {error ? <p className="mx-4 mt-4 flex gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"><AlertCircle className="size-4" aria-hidden />{error}</p> : null}
      <div className="space-y-3 p-4">
        {groups.map((group, index) => (
          <article key={group.key} className="rounded-md border bg-background p-3">
            <div className="flex items-center gap-2">
              <Input aria-label={`Builder ${index + 1}`} value={group.builderName} onChange={(event) => setGroups((current) => current.map((item) => item.key === group.key ? { ...item, builderName: event.target.value } : item))} />
              <Button type="button" size="icon" variant="ghost" aria-label="Move group up" onClick={() => moveGroup(index, -1)} disabled={index === 0}><ArrowUp className="size-4" /></Button>
              <Button type="button" size="icon" variant="ghost" aria-label="Move group down" onClick={() => moveGroup(index, 1)} disabled={index === groups.length - 1}><ArrowDown className="size-4" /></Button>
              {index > 0 ? <Button type="button" variant="ghost" onClick={() => mergeWithPrevious(index)}>Merge above</Button> : null}
            </div>
            <ol className="mt-2 space-y-1 text-sm">{group.files.map((file, fileIndex) => <li key={file.id} className="flex items-center rounded bg-muted/40 px-2 py-1"><span className="min-w-0 flex-1 truncate">{fileIndex + 1}. {file.title}</span><span className="mx-3 min-w-0 flex-1 truncate text-xs text-muted-foreground">{file.path}</span><Button type="button" size="icon" variant="ghost" aria-label={`Move ${file.title} up`} onClick={() => moveFile(group.key, fileIndex, -1)} disabled={fileIndex === 0}><ArrowUp className="size-3" /></Button><Button type="button" size="icon" variant="ghost" aria-label={`Move ${file.title} down`} onClick={() => moveFile(group.key, fileIndex, 1)} disabled={fileIndex === group.files.length - 1}><ArrowDown className="size-3" /></Button></li>)}</ol>
          </article>
        ))}
        {!groups.length && !isLoading ? <p className="rounded-md border border-dashed p-6 text-center text-sm">Select repository rows, then add them as quote groups.</p> : null}
        {revision > 0 ? (
          <div className="grid gap-3 rounded-md border p-3 sm:grid-cols-3">
            <label className="text-xs font-medium">Region<select className="mt-1 h-9 w-full rounded-md border bg-background px-2 text-sm" value={region} onChange={(event) => setRegion(event.target.value as typeof region)}><option value="">Select</option><option value="metro">Metro</option><option value="regional">Regional</option></select></label>
            <label className="text-xs font-medium">Specification<select className="mt-1 h-9 w-full rounded-md border bg-background px-2 text-sm" value={specLevel} onChange={(event) => setSpecLevel(event.target.value as typeof specLevel)}><option value="">Select</option><option value="builder_base">Builder base</option><option value="mid">Mid</option><option value="high">High</option><option value="architectural">Architectural</option></select></label>
            <label className="text-xs font-medium">Storeys (if missing)<Input className="mt-1" type="number" min="1" value={storeys} onChange={(event) => setStoreys(event.target.value)} /></label>
            <div className="sm:col-span-3 flex justify-end"><Button type="button" onClick={() => void startComparison()} disabled={!region || !specLevel || isSubmitting}>{isSubmitting ? "Starting" : "Start comparison"}</Button></div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
