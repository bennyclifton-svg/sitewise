import { Download } from "lucide-react";
import { useState } from "react";

import { PdfFileIcon, WordFileIcon } from "@/components/icons/OfficeFileIcons";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api";
import type { DraftArtifact } from "@/lib/types/project";

export function DraftDownloadMenu({ projectId, draft }: { projectId: string; draft: DraftArtifact }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function download(format: "docx" | "pdf") {
    setBusy(true);
    setError(null);
    try {
      const blob = await api.downloadDraftExport(projectId, draft.id, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${draft.title.replace(/[<>:"/\\|?*]/g, "-")}_v${draft.version}.${format}`;
      document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch { setError("Could not download this document. Try again."); }
    finally { setBusy(false); }
  }
  return <div className="flex items-center gap-2">
    {error && <span role="alert" className="text-xs text-destructive">{error}</span>}
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" disabled={busy} aria-label="Download recommendation" title="Download"><Download className={busy ? "size-5 animate-pulse" : "size-5"} aria-hidden /></Button></DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => void download("docx")}><WordFileIcon className="size-6" />Word</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void download("pdf")}><PdfFileIcon className="size-6" />PDF</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>;
}
