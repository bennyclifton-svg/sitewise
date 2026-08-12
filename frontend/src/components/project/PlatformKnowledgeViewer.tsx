import { useEffect, useState } from "react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { normalizeDraftMarkdown } from "@/lib/artifact-markdown";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { PlatformKnowledgeDocument } from "@/lib/types/project";

export function PlatformKnowledgeViewer({
  document,
}: {
  document: PlatformKnowledgeDocument | null;
}) {
  const [content, setContent] = useState<string | null>(null);
  const [kind, setKind] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDocument() {
      setError(null);
      setKind(null);
      if (!document) {
        setContent(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const data = await api.getPlatformKnowledgeDocument(document.relative_path);
        if (!cancelled) {
          setContent(data.content);
          setKind(data.kind ?? null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setContent(null);
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load platform knowledge.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadDocument();
    return () => {
      cancelled = true;
    };
  }, [document]);

  if (!document) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          Select a knowledge document from the explorer.
        </div>
      </div>
    );
  }

  const title = document.filename || document.relative_path;

  return (
    <section className="min-w-0 p-4 lg:p-6">
      <article className="mx-auto max-w-4xl">
        <section className="rounded-md border bg-background">
          <header className="space-y-2 border-b px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-sm font-semibold" title={title}>
                {title}
              </h1>
              {kind ? (
                <Badge variant="outline" className="capitalize">
                  {kind}
                </Badge>
              ) : null}
              <Badge variant="secondary">Platform knowledge</Badge>
            </div>
            <p className="break-all text-xs text-muted-foreground">
              {document.relative_path}
            </p>
          </header>
          {error ? (
            <p className="p-4 text-sm text-destructive">{error}</p>
          ) : loading ? (
            <p className="p-4 text-sm text-muted-foreground" role="status">
              Loading document content...
            </p>
          ) : content != null ? (
            <div className="max-h-[65vh] overflow-auto p-4">
              <MarkdownContent markdown={normalizeDraftMarkdown(content)} />
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">No content available.</p>
          )}
        </section>
      </article>
    </section>
  );
}
