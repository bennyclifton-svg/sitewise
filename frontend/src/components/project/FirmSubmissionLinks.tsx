import { FileCheck2, Paperclip } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import type { EvidencePreview, ProcurementStrategyCandidate, ProcurementStrategyOperation } from "@/lib/types/project";

export function FirmSubmissionLinks({ candidate, rowId, evidence, selectedIds, disabled, onApply }: {
  candidate: ProcurementStrategyCandidate;
  rowId: string;
  evidence: EvidencePreview[];
  selectedIds: Set<string>;
  disabled: boolean;
  onApply: (operations: ProcurementStrategyOperation[]) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const links = candidate.submission_files ?? [];
  const linked = new Set(links.map((file) => file.workspace_file_id));
  const selected = evidence.filter((file) => selectedIds.has(file.id) && file.workspace_file_id).map((file) => file.workspace_file_id!);
  const files = evidence.filter((file) => file.workspace_file_id && /\.(pdf|docx|xlsx|md|markdown|txt|png|jpe?g)$/i.test(file.filename));
  const available = [...files.map((file) => ({ id: file.workspace_file_id!, filename: file.filename })),
    ...links.filter((link) => !files.some((file) => file.workspace_file_id === link.workspace_file_id)).map((link) => ({ id: link.workspace_file_id, filename: link.filename }))];

  async function apply(ids: string[], link: boolean) {
    setSaving(true);
    setError(null);
    try {
      await onApply([{ operation: link ? "LINK_CANDIDATE_FILES" : "UNLINK_CANDIDATE_FILES", row_id: rowId, candidate_id: candidate.id, workspace_file_ids: ids }]);
    } catch {
      setError("Could not save file links. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="mt-0.5">
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="xs" variant="ghost" className="h-6 max-w-full gap-1 px-1.5 text-xs" disabled={disabled || saving} aria-label={`Quote files for ${candidate.company_name}`}>
          {links.length ? <FileCheck2 className="size-3 text-[var(--sw-beam-hex)]" aria-hidden /> : <Paperclip className="size-3" aria-hidden />}
          {saving ? "Saving…" : links.length ? `${links.length} file${links.length === 1 ? "" : "s"}` : "Link quote"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-80 w-80 overflow-y-auto">
        <DropdownMenuLabel>{candidate.company_name}</DropdownMenuLabel>
        {selected.length > 0 && <DropdownMenuItem disabled={saving} onSelect={() => void apply(selected, true)}>Link {selected.length} selected file{selected.length === 1 ? "" : "s"}</DropdownMenuItem>}
        {available.length === 0 && <DropdownMenuLabel>Upload quote files in the document panel.</DropdownMenuLabel>}
        {available.map((file) => <DropdownMenuCheckboxItem key={file.id} checked={linked.has(file.id)} disabled={saving} onSelect={(event) => event.preventDefault()} onCheckedChange={(checked) => void apply([file.id], Boolean(checked))}>
          <span className="min-w-0 break-words">{file.filename}</span>
        </DropdownMenuCheckboxItem>)}
      </DropdownMenuContent>
    </DropdownMenu>
    {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
  </div>;
}
