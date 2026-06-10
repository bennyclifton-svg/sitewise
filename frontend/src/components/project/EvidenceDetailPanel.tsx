import { FileText, Inbox } from "lucide-react";
import { useEffect, useState } from "react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { isMarkdownFilename } from "@/lib/markdown";
import type { EvidencePreview } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function EvidenceDetailPanel({
  projectId,
  evidence,
  selectedEvidence,
  onSelectEvidence,
}: {
  projectId: string;
  evidence: EvidencePreview[];
  selectedEvidence: EvidencePreview | null;
  onSelectEvidence: (evidenceId: string) => void;
}) {
  const [detail, setDetail] = useState<EvidencePreview | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      setDetailError(null);
      if (!selectedEvidence) {
        setDetail(null);
        setLoadingDetail(false);
        return;
      }
      if (!isMarkdownEvidence(selectedEvidence) || selectedEvidence.content) {
        setDetail(selectedEvidence);
        setLoadingDetail(false);
        return;
      }

      setLoadingDetail(true);
      try {
        const data = await api.getProjectEvidenceDocument(projectId, selectedEvidence.id);
        if (!cancelled) setDetail(data);
      } catch (error) {
        if (!cancelled) {
          setDetailError(
            error instanceof ApiError ? error.message : "Could not load document content.",
          );
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedEvidence]);

  if (!evidence.length) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Inbox className="mx-auto mb-3 size-8" aria-hidden />
          No project evidence indexed yet.
        </div>
      </div>
    );
  }

  const displayEvidence =
    detail && selectedEvidence && detail.id === selectedEvidence.id ? detail : selectedEvidence;

  return (
    <div className="grid min-h-full gap-0 lg:grid-cols-[19rem_minmax(0,1fr)]">
      <aside className="border-b bg-muted/20 p-3 lg:border-r lg:border-b-0">
        <h2 className="px-1 text-sm font-semibold">Evidence</h2>
        <div className="mt-3 space-y-2">
          {evidence.map((item) => (
            <button
              key={item.id}
              type="button"
              className={cn(
                "flex w-full items-start gap-2 rounded-md border bg-background p-3 text-left text-sm transition-colors hover:bg-muted",
                selectedEvidence?.id === item.id && "border-foreground bg-muted",
              )}
              onClick={() => onSelectEvidence(item.id)}
            >
              <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <span className="min-w-0">
                <span className="block truncate font-medium">{item.title}</span>
                <span className="mt-1 block truncate text-xs text-muted-foreground">
                  {item.document_class}
                </span>
              </span>
            </button>
          ))}
        </div>
      </aside>

      <section className="min-w-0 p-4 lg:p-6">
        {displayEvidence ? (
          <article className="mx-auto max-w-4xl space-y-4">
            <header className="rounded-md border bg-background p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h1 className="text-xl font-semibold">{displayEvidence.title}</h1>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {displayEvidence.relative_path}
                  </p>
                </div>
                <Badge variant="outline">{displayEvidence.document_class}</Badge>
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                <MetaItem
                  label="Doc No"
                  value={displayEvidence.document_number?.trim() || "-"}
                />
                <MetaItem label="Title" value={displayEvidence.title} />
                <MetaItem
                  label="Revision"
                  value={displayEvidence.revision?.trim() || "-"}
                />
                <MetaItem
                  label="Category"
                  value={displayEvidence.category?.trim() || "-"}
                />
                <MetaItem label="Filename" value={displayEvidence.filename} />
                <MetaItem label="Source type" value={displayEvidence.source_type ?? "Unknown"} />
              </dl>
            </header>
            <section className="rounded-md border bg-background">
              <header className="border-b px-4 py-3">
                <h2 className="text-sm font-semibold">
                  {isMarkdownEvidence(displayEvidence) ? "Document content" : "Extracted excerpt"}
                </h2>
              </header>
              {detailError ? (
                <p className="p-4 text-sm text-destructive">{detailError}</p>
              ) : loadingDetail && isMarkdownEvidence(displayEvidence) ? (
                <p className="p-4 text-sm text-muted-foreground" role="status">
                  Loading document content...
                </p>
              ) : isMarkdownEvidence(displayEvidence) && displayEvidence.content ? (
                <div className="p-4">
                  <MarkdownContent markdown={displayEvidence.content} />
                </div>
              ) : (
                <p className="whitespace-pre-wrap p-4 text-sm leading-relaxed">
                  {displayEvidence.excerpt}
                </p>
              )}
            </section>
          </article>
        ) : (
          <div className="flex min-h-full items-center justify-center rounded-md border border-dashed p-6 text-sm text-muted-foreground">
            Select evidence from the repository.
          </div>
        )}
      </section>
    </div>
  );
}

function isMarkdownEvidence(item: EvidencePreview): boolean {
  return isMarkdownFilename(item.filename);
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
