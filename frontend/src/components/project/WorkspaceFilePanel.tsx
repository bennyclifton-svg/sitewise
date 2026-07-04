import { Inbox } from "lucide-react";
import { useEffect, useState } from "react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { EvidencePreview } from "@/lib/types/project";

export function WorkspaceFilePanel({
  projectId,
  evidence,
}: {
  projectId: string;
  evidence: EvidencePreview | null;
}) {
  const [detail, setDetail] = useState<EvidencePreview | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      setDetailError(null);
      if (!evidence) {
        setDetail(null);
        setLoadingDetail(false);
        return;
      }
      if (evidence.content) {
        setDetail(evidence);
        setLoadingDetail(false);
        return;
      }

      setLoadingDetail(true);
      try {
        const data = await api.getProjectEvidenceDocument(projectId, evidence.id);
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
  }, [projectId, evidence]);

  if (!evidence) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Inbox className="mx-auto mb-3 size-8" aria-hidden />
          Select a file from the explorer.
        </div>
      </div>
    );
  }

  const displayEvidence = detail && detail.id === evidence.id ? detail : evidence;

  return (
    <section className="min-w-0 p-4 lg:p-6">
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
            <MetaItem label="Doc No" value={displayEvidence.document_number?.trim() || "-"} />
            <MetaItem label="Title" value={displayEvidence.title} />
            <MetaItem label="Revision" value={displayEvidence.revision?.trim() || "-"} />
            <MetaItem label="Category" value={displayEvidence.category?.trim() || "-"} />
            <MetaItem label="Filename" value={displayEvidence.filename} />
            <MetaItem label="Source type" value={displayEvidence.source_type ?? "Unknown"} />
          </dl>
        </header>
        <section className="rounded-md border bg-background">
          <header className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">
              {displayEvidence.content ? "Document content" : "Extracted excerpt"}
            </h2>
          </header>
          {detailError ? (
            <p className="p-4 text-sm text-destructive">{detailError}</p>
          ) : loadingDetail ? (
            <p className="p-4 text-sm text-muted-foreground" role="status">
              Loading document content...
            </p>
          ) : displayEvidence.content ? (
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
    </section>
  );
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
