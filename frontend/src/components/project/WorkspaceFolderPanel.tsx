import { Bot, FileText, FolderOpen, Play } from "lucide-react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { isMarkdownFilename } from "@/lib/markdown";
import type { EvidencePreview, WorkspaceTreeNode } from "@/lib/types/project";

export function WorkspaceFolderPanel({
  folder,
  evidence,
  onOpenEvidence,
}: {
  folder: WorkspaceTreeNode | null;
  evidence: EvidencePreview[];
  onOpenEvidence: () => void;
}) {
  if (!folder) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          Select a folder from the explorer.
        </div>
      </div>
    );
  }

  const folderEvidence = evidence.filter((item) =>
    item.relative_path.replaceAll("\\", "/").startsWith(folder.path),
  );

  return (
    <article className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 lg:p-6">
      <header className="rounded-md border bg-background p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <FolderOpen className="size-5 text-muted-foreground" aria-hidden />
              <h1 className="text-xl font-semibold">{folder.name}</h1>
            </div>
            <p className="mt-1 break-all text-sm text-muted-foreground">{folder.path}</p>
          </div>
          <Badge variant="outline">{folder.document_count} documents</Badge>
        </div>
        <p className="mt-4 text-sm leading-relaxed">{folder.description}</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <section className="rounded-md border bg-background">
          <header className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Folder evidence</h2>
          </header>
          <div className="p-4">
            {folderEvidence.length ? (
              <ul className="space-y-3">
                {folderEvidence.map((item) => (
                  <li key={item.id} className="rounded-md border p-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex min-w-0 items-center gap-2 font-medium">
                        <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                        <span className="truncate">{item.title}</span>
                      </span>
                      <Badge variant="outline">{item.document_class}</Badge>
                    </div>
                    {isMarkdownEvidence(item) && item.content ? (
                      <div className="mt-2 text-muted-foreground">
                        <MarkdownContent markdown={item.content} />
                      </div>
                    ) : (
                      <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{item.excerpt}</p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                No indexed evidence has landed in this folder yet.
              </div>
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-md border bg-background p-4">
            <h2 className="text-sm font-semibold">Related workflows</h2>
            {folder.related_workflows.length ? (
              <div className="mt-3 space-y-2">
                {folder.related_workflows.map((workflow) => (
                  <div
                    key={workflow}
                    className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm"
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <Bot className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                      <span className="truncate">{workflow}</span>
                    </span>
                    <Badge variant="outline">mapped</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">No workflow mapped yet.</p>
            )}
          </section>

          <Button variant="outline" className="w-full" onClick={onOpenEvidence}>
            <FileText className="size-4" aria-hidden />
            Open evidence register
          </Button>
          <Button disabled className="w-full">
            <Play className="size-4" aria-hidden />
            Folder workflow
          </Button>
        </aside>
      </div>
    </article>
  );
}

function isMarkdownEvidence(item: EvidencePreview): boolean {
  return isMarkdownFilename(item.filename);
}
