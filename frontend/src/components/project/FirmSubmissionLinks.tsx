import { LoaderCircle, Paperclip } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { EvidencePreview, ProcurementStrategyCandidate, ProcurementStrategyOperation } from "@/lib/types/project";

export function FirmSubmissionLinks({ candidate, projectId, slot, cellLabel, rowId, evidence, selectedIds, disabled, onApply }: {
  candidate?: ProcurementStrategyCandidate;
  projectId: string;
  slot: number;
  cellLabel: string;
  rowId: string;
  evidence: EvidencePreview[];
  selectedIds: Set<string>;
  disabled: boolean;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [identifying, setIdentifying] = useState(false);
  const [pending, setPending] = useState<{ ids: string[]; message: string } | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const links = candidate?.submission_files ?? [];
  const linked = new Set(links.map((file) => file.workspace_file_id));
  const selected = evidence.filter((file) => selectedIds.has(file.id) && file.workspace_file_id).map((file) => file.workspace_file_id!);
  const files = evidence.filter((file) => file.workspace_file_id && /\.(pdf|docx|xlsx|md|markdown|txt|png|jpe?g)$/i.test(file.filename));
  const available = [...files.map((file) => ({ id: file.workspace_file_id!, filename: file.filename })),
    ...links.filter((link) => !files.some((file) => file.workspace_file_id === link.workspace_file_id)).map((link) => ({ id: link.workspace_file_id, filename: link.filename }))];

  async function createFirm(ids: string[], name: string) {
    await onApply([{ operation: "CREATE_CANDIDATE_FROM_FILES", row_id: rowId, slot, company_name: name, workspace_file_ids: ids }]);
    setPending(null);
    setCompanyName("");
  }

  async function apply(ids: string[], link: boolean) {
    if (saving || disabled) return;
    setSaving(true);
    setError(null);
    setPending(null);
    try {
      if (candidate) {
        await onApply([{ operation: link ? "LINK_CANDIDATE_FILES" : "UNLINK_CANDIDATE_FILES", row_id: rowId, candidate_id: candidate.id, workspace_file_ids: ids }]);
      } else {
        setIdentifying(true);
        const identity = await api.identifySubmissionFirm(projectId, ids);
        setIdentifying(false);
        if (identity.status === "identified" && identity.company_name) {
          await createFirm(ids, identity.company_name);
        } else if (identity.status === "different_firms") {
          setError(identity.message ?? "Select documents for one firm at a time.");
        } else {
          setPending({ ids, message: identity.message ?? "Enter the firm name to link these documents." });
        }
      }
    } catch (nextError) {
      setError(nextError instanceof ApiError ? nextError.message : "Could not save file links. Try again.");
    } finally {
      setSaving(false);
      setIdentifying(false);
    }
  }

  async function submitName() {
    if (!pending || !companyName.trim() || disabled || saving) return;
    setSaving(true);
    setError(null);
    try {
      await createFirm(pending.ids, companyName.trim());
    } catch (nextError) {
      setError(nextError instanceof ApiError ? nextError.message : "Could not save file links. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="contents">
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="xs" variant="ghost" className="h-8 min-w-8 gap-1 rounded-none px-1 text-xs text-muted-foreground hover:text-foreground" title={links.length ? links.map((file) => file.filename).join("\n") : `Link documents for ${cellLabel}`} disabled={disabled || saving} aria-label={candidate ? `Quote files for ${candidate.company_name}` : `Link documents for ${cellLabel}`}>
          {saving ? <LoaderCircle className="size-3.5 animate-spin" aria-hidden /> : <Paperclip className="size-3.5" aria-hidden />}
          {saving ? <span className="sr-only" role="status">{identifying ? "Identifying firm…" : "Saving…"}</span> : links.length > 0 ? <span>{links.length}</span> : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-80 w-80 overflow-y-auto">
        <DropdownMenuLabel>{candidate?.company_name ?? cellLabel}</DropdownMenuLabel>
        {selected.length > 0 && <DropdownMenuItem disabled={saving} onSelect={() => void apply(selected, true)}>Link {selected.length} selected file{selected.length === 1 ? "" : "s"}</DropdownMenuItem>}
        {available.length === 0 && <DropdownMenuLabel>Upload quote files in the document panel.</DropdownMenuLabel>}
        {available.map((file) => <DropdownMenuCheckboxItem key={file.id} checked={linked.has(file.id)} disabled={disabled || saving} onSelect={(event) => { if (candidate) event.preventDefault(); }} onCheckedChange={(checked) => void apply([file.id], Boolean(checked))}>
          <span className="min-w-0 break-words">{file.filename}</span>
        </DropdownMenuCheckboxItem>)}
      </DropdownMenuContent>
    </DropdownMenu>
    {pending && !candidate && <form className="col-span-2 mt-1 min-w-0 space-y-1" onSubmit={(event) => { event.preventDefault(); void submitName(); }}>
      <p role="status" className="text-xs text-muted-foreground">{pending.message}</p>
      <p className="break-words text-xs text-muted-foreground">{pending.ids.map((id) => available.find((file) => file.id === id)?.filename ?? "Document").join(", ")}</p>
      <Input aria-label={`Firm name for ${cellLabel}`} placeholder="Firm name" value={companyName} maxLength={512} disabled={disabled || saving} onChange={(event) => setCompanyName(event.target.value)} />
      <div className="flex flex-wrap gap-1">
        <Button type="submit" size="xs" disabled={disabled || saving || !companyName.trim()}>Add firm and link</Button>
        <Button type="button" size="xs" variant="ghost" disabled={saving} onClick={() => { setPending(null); setCompanyName(""); setError(null); }}>Cancel</Button>
      </div>
    </form>}
    {error && <p role="alert" className="col-span-2 text-xs text-destructive">{error}</p>}
  </div>;
}
