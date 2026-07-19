import { AlertCircle, Check, ExternalLink, FileText, LoaderCircle, RefreshCw } from "lucide-react";
import { useState } from "react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { useTenderReport } from "@/lib/queries/tender";

export function TenderReportPanel({
  projectId,
  comparisonId,
}: {
  projectId: string;
  comparisonId: string;
}) {
  const reportQuery = useTenderReport(comparisonId);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const report = reportQuery.data?.report ?? null;
  const draft = reportQuery.data?.draft ?? null;
  const queryError = reportQuery.error instanceof ApiError ? reportQuery.error.message : reportQuery.error ? "Could not load tender report draft." : null;

  async function buildReport() {
    setIsBuilding(true);
    setError(null);
    try {
      await api.buildTenderReport(comparisonId);
      await reportQuery.refetch();
    } catch (buildError) {
      setError(
        buildError instanceof ApiError
          ? buildError.message
          : "Could not build tender report.",
      );
    } finally {
      setIsBuilding(false);
    }
  }

  async function approveReport() {
    setIsApproving(true);
    setError(null);
    try {
      await api.approveTenderReport(comparisonId);
      await reportQuery.refetch();
    } catch (approveError) {
      setError(
        approveError instanceof ApiError
          ? approveError.message
          : "Could not approve tender report.",
      );
    } finally {
      setIsApproving(false);
    }
  }

  const pdfHref = report?.pdf_path ? browserArtifactSrc(report.pdf_path) : null;

  return (
    <section className="rounded-md border bg-card shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <p className="cockpit-zone-title">Report preview</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Build regenerates structured tables; narrative edits stay in the draft.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {report ? <Badge variant="outline">v{report.version}</Badge> : null}
          {report ? <Badge variant="secondary">{report.status}</Badge> : null}
        </div>
      </header>

      {error || queryError ? (
        <p className="mx-4 mt-4 flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="size-4" aria-hidden />
          {error || queryError}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2 border-b px-4 py-3">
        <Button type="button" onClick={() => void buildReport()} disabled={isBuilding || isApproving}>
          {isBuilding ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <RefreshCw className="size-4" aria-hidden />
          )}
          {draft ? "Rebuild draft" : "Build draft"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => void approveReport()}
          disabled={isApproving || isBuilding || !draft}
        >
          {isApproving ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <Check className="size-4" aria-hidden />
          )}
          Approve
        </Button>
        {pdfHref ? (
          <Button asChild variant="outline">
            <a href={pdfHref} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4" aria-hidden />
              Frozen PDF
            </a>
          </Button>
        ) : null}
      </div>

      {draft?.content_markdown ? (
        <div className="min-w-0 p-4 lg:p-6">
          <MarkdownContent
            markdown={draft.content_markdown}
            version={draft.version}
            projectId={projectId}
            projectTitle={draft.title}
            readOnly
          />
        </div>
      ) : (
        <div className="flex min-h-[30rem] items-center justify-center p-6 text-center">
          <div className="max-w-sm">
            <FileText className="mx-auto size-8 text-muted-foreground" aria-hidden />
            <p className="mt-3 text-sm font-medium">
              {reportQuery.isLoading ? "Loading report draft" : "No report draft yet"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Build the report to generate draft content.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function browserArtifactSrc(path: string): string | null {
  if (/^(https?:|blob:|data:)/.test(path)) return path;
  if (path.startsWith("/")) return path;
  return null;
}
